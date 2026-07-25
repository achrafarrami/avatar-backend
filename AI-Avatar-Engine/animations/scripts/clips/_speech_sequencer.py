"""Procedural gibberish-speech sequencer (pure Python, no bpy).

Turns phrase windows + a style dict into coarticulated viseme / jaw / tongue
keyframes on a ClipContext. Design: plans/lipsync_plan.md. Ruleset source:
library_spec.json -> talking_neutral beats.

Mechanics encoded here:
- syllables with log-normal duration jitter; the inter-syllable interval CV
  is forced >= 0.25 (anti-metronome; QA autocorrelates motion energy)
- viseme events: attack 3-5 f, release overlapping the next event's attack
  by >= 2 f (never A -> zero -> B inside a phrase); same-key events merge
  without interior zeros
- jaw is solved UNDER the visemes: 30-50 % of the active nucleus openness,
  peaks 1 f behind the lips, dips only to a floor between syllables, closes
  fully only into pauses; bilabials force a near-closed dip + a full
  Mouth_Close hold (1-2 f)
- the JawRoot BONE is the opener (lower teeth/tongue ride it); the Jaw_Open
  shape key is added at deg/15 for lip-skin shaping only
- tongue visemes (V_Tongue_up / V_Tongue_Raise) flick on dental/affricate
  onsets
- a governor rescales viseme peaks if the frame-wise sum of face visemes
  would exceed SUM_CAP (mouth blow-out guard)

The leading underscore keeps the clip loader from importing this as a
recipe module; talking.py imports it explicitly.
"""
import math
from dataclasses import dataclass

# openness factor per viseme (how much mouth aperture the shape implies)
OPENNESS = {
    "V_Open": 1.0, "V_Lip_Open": 0.55, "V_Tight_O": 0.5, "V_Wide": 0.45,
    "V_Affricate": 0.30, "V_Tight": 0.22, "V_Dental_Lip": 0.15,
    "V_Explosive": 0.05,
}
FACE_VISEMES = tuple(OPENNESS)

# onset consonant table: (viseme, weight, peak_lo, peak_hi)
ONSETS = [
    ("V_Explosive",  0.22, 0.75, 0.95),
    ("V_Dental_Lip", 0.12, 0.60, 0.80),
    ("V_Affricate",  0.16, 0.55, 0.75),
    ("V_Tight",      0.28, 0.40, 0.60),
    ("V_Lip_Open",   0.22, 0.40, 0.60),
]
# nucleus vowels: name -> (peak_lo, peak_hi); 'schwa' is a composite
NUCLEI = {
    "V_Open":    (0.62, 0.80),
    "V_Wide":    (0.55, 0.75),
    "V_Tight_O": (0.55, 0.75),
    "schwa":     (0.30, 0.42),   # V_Open low + V_Lip_Open under
}
TONGUE_FOR_ONSET = {"V_Affricate": "V_Tongue_up", "V_Tight": "V_Tongue_Raise"}

SUM_CAP = 1.30

DEFAULT_STYLE = {
    "syllable_rate": 3.4,      # mean syllables / s
    "rate_jitter": 0.30,       # sigma of log-normal duration jitter
    "viseme_energy": 1.0,      # scales all viseme peaks
    "jaw_amplitude": 1.0,      # scales jaw openness units
    "jaw_max_deg": 12.0,       # units 1.0 -> this many JawRoot degrees
    "jaw_key_per_deg": 1.0 / 15.0,   # Jaw_Open key value per JawRoot degree
    "jaw_under": (0.30, 0.50), # jaw = under * nucleus openness * peak
    "jaw_floor": 0.45,         # fraction of neighbor level kept between syls
    "onset_prob": 0.85,
    "coda_prob": 0.20,
    "vowel_weights": {"V_Open": 0.32, "V_Wide": 0.22,
                      "V_Tight_O": 0.20, "schwa": 0.26},
    "stress_every_s": 0.95,    # ~1 stressed syllable per this interval
    "declination": 0.18,       # amplitude decay across each phrase
    "tongue_amp": (0.24, 0.38),
    # articulation shaping (tier-2). Defaults reproduce tier-1 behavior with
    # an IDENTICAL rng draw order — do not change the defaults.
    "cons_attack": (2, 4), "cons_release": (3, 5),
    "nuc_attack": (3, 5), "nuc_release": (4, 6),
    "bilabial_hold": (1, 2),   # Mouth_Close hold frames on V_Explosive
    "min_overlap": 2,          # coarticulation overlap floor (frames)
    "peak_cap": None,          # hard cap on any viseme peak (talking_fast)
    "plateau_thresh": 9,       # syllable frames needed for a vowel plateau
    "plateau_max": 4, "plateau_frac": 0.25,
    "plateau_waver": 0.0,      # +-value waver on long holds (talking_slow)
    "hint_visemes": ("V_Wide", "V_Tight_O"),
    # hint mode (talk_idle): no consonants, sparse low viseme flickers,
    # jaw oscillation with directly-specified unit range
    "hint_mode": False,
    "hint_prob": 0.55,
    "hint_peak": (0.08, 0.13),
    "hint_jaw_units": (0.08, 0.22),
}


@dataclass
class Syl:
    f_on: int          # onset peak frame (== f_nuc if no onset)
    f_nuc: int         # nucleus peak frame
    f_end: int         # syllable end frame
    dur_f: float
    onset: str         # viseme name or ""
    nucleus: str       # viseme name, "schwa", or "" (hint-mode jaw-only)
    coda: str          # viseme name or ""
    amp: float         # 0..1 amplitude after stress/envelope
    stress: bool


def _style(overrides):
    s = dict(DEFAULT_STYLE)
    if overrides:
        s.update(overrides)
    return s


def _weighted(rng, pairs):
    """pairs: [(item, weight), ...] -> item"""
    total = sum(w for _, w in pairs)
    r = rng.uniform(0.0, total)
    for item, w in pairs:
        r -= w
        if r <= 0.0:
            return item
    return pairs[-1][0]


# ---------------------------------------------------------------------------
# syllable planning
# ---------------------------------------------------------------------------
def _phrase_syllables(ctx, style, f0, f1):
    """Fill [f0, f1] with jittered syllables. Retries the draw until the
    duration CV clears 0.25 (usually first try at sigma 0.3)."""
    fps = ctx.fps
    base_f = fps / style["syllable_rate"]
    span = f1 - f0
    taper = min(6, span // 8)      # frames reserved to taper into the pause
    for _attempt in range(24):
        durs = []
        total = 0.0
        while total + base_f * 0.6 < span - taper:
            d = base_f * math.exp(ctx.rng.gauss(0.0, style["rate_jitter"]))
            d = max(4.0, min(d, base_f * 2.4))
            durs.append(d)
            total += d
        if len(durs) < 3:
            continue
        mean = sum(durs) / len(durs)
        var = sum((d - mean) ** 2 for d in durs) / len(durs)
        if math.sqrt(var) / mean >= 0.25:
            break
    # stress marks: phrase-initial region + ~every stress_every_s
    stress_gap = style["stress_every_s"] * fps
    stressed_idx = set()
    acc = stress_gap * 0.35        # front-loaded first stress
    for i, d in enumerate(durs):
        acc += d
        if acc >= stress_gap:
            stressed_idx.add(i)
            acc = ctx.rng.uniform(-0.15, 0.15) * stress_gap
    if 0 not in stressed_idx and 1 not in stressed_idx:
        stressed_idx.add(0)

    syls = []
    cursor = float(f0)
    n = len(durs)
    for i, d in enumerate(durs):
        stress = i in stressed_idx
        # phrase envelope: quick rise over 2 syllables, declination to end
        rise = min(1.0, 0.72 + 0.14 * i)
        decl = 1.0 - style["declination"] * (i / max(1, n - 1))
        amp = (1.0 if stress else ctx.rng.uniform(0.55, 0.85)) * rise * decl
        f_nuc = int(round(cursor + d * 0.42))
        f_on = f_nuc
        onset = nucleus = coda = ""
        if style["hint_mode"]:
            if ctx.rng.random() < style["hint_prob"]:
                nucleus = ctx.rng.choice(style["hint_visemes"])
        else:
            if ctx.rng.random() < style["onset_prob"]:
                onset = _weighted(ctx.rng, [(o[0], o[1]) for o in ONSETS])
                f_on = max(f0, f_nuc - max(3, int(round(d * 0.30))))
            nucleus = _weighted(
                ctx.rng, list(style["vowel_weights"].items()))
            if ctx.rng.random() < style["coda_prob"] and d >= 8:
                coda = _weighted(ctx.rng, [(o[0], o[1] * 0.7)
                                           for o in ONSETS])
        syls.append(Syl(f_on=f_on, f_nuc=f_nuc,
                        f_end=int(round(cursor + d)), dur_f=d,
                        onset=onset, nucleus=nucleus, coda=coda,
                        amp=amp, stress=stress))
        cursor += d
    return syls


# ---------------------------------------------------------------------------
# viseme event assembly
# ---------------------------------------------------------------------------
def _onset_peak(rng, name, energy):
    for v, _w, lo, hi in ONSETS:
        if v == name:
            return rng.uniform(lo, hi) * energy
    return 0.5 * energy


def _phrase_events(ctx, style, syls):
    """-> list of (key, f_start, [(frame, value)...], f_end), un-merged."""
    rng = ctx.rng
    energy = style["viseme_energy"]
    events = []

    cap = style["peak_cap"]
    waver = style["plateau_waver"]

    def ev(key, f_peak, value, attack, release, plateau=0):
        if cap is not None:
            value = min(value, cap)
        pts = [(f_peak, value)]
        if plateau:
            if waver > 1e-4 and plateau >= 5:   # long hold stays alive
                pts.append((f_peak + int(plateau * 0.45),
                            value * (0.88 + rng.uniform(-waver, waver))))
                pts.append((f_peak + plateau,
                            value * (0.88 + rng.uniform(-waver, waver))))
            else:
                pts.append((f_peak + plateau, value * 0.88))
        end = pts[-1][0] + release
        events.append((key, f_peak - attack, pts, end))
        return end

    for s in syls:
        if s.onset:
            v = _onset_peak(rng, s.onset, energy) * (0.85 + 0.15 * s.amp)
            ev(s.onset, s.f_on, v, rng.randint(*style["cons_attack"]),
               rng.randint(*style["cons_release"]))
            tongue = TONGUE_FOR_ONSET.get(s.onset)
            if tongue:
                ev(tongue, s.f_on, rng.uniform(*style["tongue_amp"]),
                   2, rng.randint(*style["cons_release"]))
            if s.onset == "V_Explosive":     # bilabial: full lip closure hold
                hold = rng.randint(*style["bilabial_hold"])
                events.append(("Mouth_Close", s.f_on - 2,
                               [(s.f_on, 1.0), (s.f_on + hold, 1.0)],
                               s.f_on + hold + 3))
        if s.nucleus:
            plateau = (min(style["plateau_max"],
                           int(s.dur_f * style["plateau_frac"]))
                       if s.dur_f >= style["plateau_thresh"] else 0)
            if s.nucleus == "schwa":
                v = rng.uniform(*NUCLEI["schwa"]) * energy * s.amp
                ev("V_Open", s.f_nuc, v, rng.randint(*style["nuc_attack"]),
                   rng.randint(*style["nuc_release"]), plateau)
                ev("V_Lip_Open", s.f_nuc + 1, v * 0.8,
                   rng.randint(*style["nuc_attack"]),
                   rng.randint(*style["nuc_release"]))
            else:
                if style["hint_mode"]:      # hint visemes may be non-nuclei
                    lo, hi = style["hint_peak"]
                else:
                    lo, hi = NUCLEI[s.nucleus]
                v = rng.uniform(lo, hi) * energy * (0.7 + 0.3 * s.amp)
                ev(s.nucleus, s.f_nuc, v, rng.randint(*style["nuc_attack"]),
                   rng.randint(*style["nuc_release"]), plateau)
        if s.coda:
            v = _onset_peak(rng, s.coda, energy) * 0.6 * s.amp
            ev(s.coda, int(s.f_nuc + s.dur_f * 0.45), v,
               rng.randint(*style["cons_attack"]),
               rng.randint(*style["cons_release"]))

    # coarticulation guarantee: consecutive events overlap by >= min_overlap
    events.sort(key=lambda e: e[1])
    ovl = style["min_overlap"]
    for i in range(len(events) - 1):
        key, fs, pts, fe = events[i]
        nxt_start = events[i + 1][1]
        if fe < nxt_start + ovl:
            events[i] = (key, fs, pts, nxt_start + ovl)
    return events


def _merge_channels(events):
    """Per key: merge overlapping events into segments with NO interior
    zeros (coarticulation), zeros only at segment boundaries.
    -> {key: {frame: value}}"""
    per_key = {}
    for key, fs, pts, fe in events:
        per_key.setdefault(key, []).append([fs, list(pts), fe])
    channels = {}
    for key, evs in per_key.items():
        evs.sort(key=lambda e: e[0])
        merged = [evs[0]]
        for ev in evs[1:]:
            last = merged[-1]
            if ev[0] <= last[2]:            # overlap -> one segment
                last[1].extend(ev[1])
                last[2] = max(last[2], ev[2])
            else:
                merged.append(ev)
        chan = {}
        for fs, pts, fe in merged:
            for f, v in ((fs, 0.0), (fe, 0.0)):
                chan[f] = max(chan.get(f, 0.0), 0.0) if f in chan else 0.0
            for f, v in pts:
                chan[f] = max(chan.get(f, 0.0), v)
        channels[key] = chan
    return channels


def _governor(channels):
    """Scale all face-viseme peaks down if the frame-wise linear-interp sum
    would exceed SUM_CAP."""
    def sample(chan, f):
        frames = sorted(chan)
        if not frames or f <= frames[0] or f >= frames[-1]:
            return 0.0
        import bisect
        i = bisect.bisect_right(frames, f)
        f0, f1 = frames[i - 1], frames[i]
        t = (f - f0) / (f1 - f0)
        return chan[f0] * (1 - t) + chan[f1] * t

    face = {k: c for k, c in channels.items() if k in FACE_VISEMES}
    if not face:
        return 1.0
    all_frames = sorted({f for c in face.values() for f in c})
    if not all_frames:
        return 1.0
    peak = 0.0
    for f in range(all_frames[0], all_frames[-1] + 1):
        peak = max(peak, sum(sample(c, f) for c in face.values()))
    if peak <= SUM_CAP:
        return 1.0
    scale = SUM_CAP / peak
    for c in face.values():
        for f in c:
            c[f] *= scale
    return scale


# ---------------------------------------------------------------------------
# jaw solving
# ---------------------------------------------------------------------------
def _jaw_units(ctx, style, s):
    """Openness units (0..1) contributed by one syllable's nucleus."""
    if style["hint_mode"]:
        u = ctx.rng.uniform(*style["hint_jaw_units"])
        return u * (1.25 if s.stress else 1.0) * s.amp
    if not s.nucleus:
        return 0.0
    under = ctx.rng.uniform(*style["jaw_under"])
    if s.nucleus == "schwa":
        openness, peak = 0.45, 0.36
    else:
        openness = OPENNESS[s.nucleus]
        peak = sum(NUCLEI[s.nucleus]) / 2.0
    return under * openness * peak * s.amp * style["jaw_amplitude"]


def _emit_jaw(ctx, style, syls, f0, f1, layer):
    """Jaw polyline: peaks 1 f behind the lips, floor dips between
    syllables, bilabial near-closures, full close only into the pause."""
    if not syls:
        return
    keys = {max(ctx.frame_start, f0 - 3): 0.0}
    prev_u, prev_f = None, None
    for s in syls:
        u = _jaw_units(ctx, style, s)
        f = s.f_nuc + 1
        if prev_f is not None and f - prev_f >= 5:
            dip = style["jaw_floor"] * min(prev_u, u)
            keys[(prev_f + f) // 2] = dip
        if s.onset == "V_Explosive":   # lips must touch: jaw nearly closes
            keys[s.f_on] = min(keys.get(s.f_on, 1.0), 0.05)
        keys[f] = u
        prev_u, prev_f = u, f
    keys[min(f1 + 5, ctx.frame_end - 1)] = 0.0
    per_deg = style["jaw_key_per_deg"]
    for f in sorted(keys):
        deg = keys[f] * style["jaw_max_deg"]
        ctx.jaw_open(f, deg, layer=layer)
        ctx.key_shape("Jaw_Open", f, deg * per_deg, layer=layer)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def speak(ctx, phrases, style=None, layer_viseme='viseme', layer_jaw='jaw'):
    """Author gibberish speech over `phrases` = [(f_start, f_end), ...]
    (absolute frames; gaps between windows are the pauses). Returns a plan:
    {"syllables": [Syl...], "stressed": [Syl...], "phrases": phrases,
     "cv": duration CV, "governor_scale": float}"""
    style = _style(style)
    all_syls, all_events = [], []
    for f0, f1 in phrases:
        syls = _phrase_syllables(ctx, style, f0, f1)
        all_events.extend(_phrase_events(ctx, style, syls))
        _emit_jaw(ctx, style, syls, f0, f1, layer_jaw)
        all_syls.extend(syls)

    channels = _merge_channels(all_events)
    gov = _governor(channels)
    for key, chan in channels.items():
        for f in sorted(chan):
            ctx.key_shape(key, f, chan[f], layer=layer_viseme)

    durs = [s.dur_f for s in all_syls]
    mean = sum(durs) / len(durs)
    cv = math.sqrt(sum((d - mean) ** 2 for d in durs) / len(durs)) / mean
    print(f"  [sequencer] {ctx.clip_id}: {len(all_syls)} syllables, "
          f"duration CV {cv:.2f}, governor x{gov:.2f}")
    return {"syllables": all_syls,
            "stressed": [s for s in all_syls if s.stress],
            "phrases": phrases, "cv": cv, "governor_scale": gov}


def pause_breath(ctx, f, depth=1.0, nostril=True, layer='breath2'):
    """Visible breath intake at a pause start: chest bump layered on top of
    the baked breathing cycle (+ optional nostril flare)."""
    for df, v in ((0, 0.0), (6, -0.95 * depth), (16, -0.30 * depth),
                  (26, 0.0)):
        ctx.key_bone_axis("CC_Base_Spine02", f + df, 'x', v, layer=layer)
    if nostril:
        for side in 'LR':
            k = f"Nose_Nostril_Dilate_{side}"
            ctx.key_shape(k, f + 1, 0.0, layer=layer)
            ctx.key_shape(k, f + 6, 0.13 * depth, layer=layer)
            ctx.key_shape(k, f + 15, 0.0, layer=layer)


def emphasis_nod(ctx, f, deg=1.5, layer='emph_head'):
    """Small speech-emphasis head nod peaking just after `f` (brows lead the
    voice, the head lands with it)."""
    ctx.pitch("CC_Base_Head", f - 4, 0.0, layer=layer)
    ctx.pitch("CC_Base_Head", f + 1, deg, layer=layer)
    ctx.pitch("CC_Base_Head", f + 6, -0.25 * deg, layer=layer)
    ctx.pitch("CC_Base_Head", f + 11, 0.0, layer=layer)
    ctx.pitch("CC_Base_NeckTwist01", f - 2, 0.0, layer=layer)
    ctx.pitch("CC_Base_NeckTwist01", f + 3, deg * 0.35, layer=layer)
    ctx.pitch("CC_Base_NeckTwist01", f + 12, 0.0, layer=layer)


def emphasis_brow(ctx, f, amp=0.22, layer='emph'):
    """Brow raise anticipating a stressed syllable by ~2 f."""
    r_scale = ctx.rng.uniform(0.8, 1.0)
    for pat, scale in (("Brow_Raise_Inner_{S}", 1.0),
                       ("Brow_Raise_Outer_{S}", 0.6)):
        ctx.key_shape_lr(pat, f - 6, 0.0, layer=layer, r_scale=r_scale)
        ctx.key_shape_lr(pat, f - 1, amp * scale, layer=layer,
                         r_scale=r_scale)
        ctx.key_shape_lr(pat, f + 11, 0.0, layer=layer, r_scale=r_scale)
