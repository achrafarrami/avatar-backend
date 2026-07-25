"""Talking clips — Tier 2 (lipsync owner). 12 clips per library_spec.json.

talk_soft/fast/excited/serious/whisper (6 s, non-phonemic hint mode) and
talking_angry/excited/serious/fast/slow/laughing/thinking (8 s, full viseme
chain). Self-sufficient base clips: baked breathing (distinct phase/seed),
1-frame-lag blinks (project standard), seams mid-pause. Sequencer core:
_speech_sequencer.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _speech_sequencer as seq                       # noqa: E402

from anim_framework.clips import clip                 # noqa: E402
from anim_framework import motion                     # noqa: E402

# Baked blink START frames (absolute). patch_talking_meta.py reads this via
# ast (merged with tier-1's dict in talking.py) to stamp meta.json.
BAKED_BLINKS = {
    "talk_soft": [50, 120],
    "talk_fast": [50, 111, 150],
    "talk_excited": [56, 126, 152],
    "talk_serious": [58, 137],
    "talk_whisper": [54, 128],
    "talking_angry": [118],                 # rage suppresses blinking
    "talking_excited": [63, 148, 210],
    "talking_serious": [88, 205],
    "talking_fast": [79, 140, 216],
    "talking_slow": [68, 160, 216],
    "talking_laughing": [100, 196],
    "talking_thinking": [48, 91, 169],      # 91/169 mask the gaze returns
}


def _blink(ctx, f):
    """Project-standard blink: R-lid lag capped at 1 frame (QA dim6),
    value asymmetry kept. Same draw order as tier-1's wrapper."""
    close = ctx.rng.randint(3, 4)
    open_ = ctx.rng.randint(5, 7)
    ctx.rng.randint(1, 2)          # discarded legacy r_offset draw
    motion.add_blink(ctx, f, close=close, open_=open_, r_offset=1)


def _hold(ctx, key, v, layer='emote'):
    """Constant-value channel across the whole clip (loop-safe)."""
    ctx.key_shape(key, ctx.frame_start, v, layer=layer)
    ctx.key_shape(key, ctx.frame_end, v, layer=layer)


def _smile(ctx, plan, base_l, base_r, dip, blooms=(), layer='emote'):
    """Co-articulated smile baseline (see tier-1): reduced (never zeroed)
    through rounded/open visemes + bilabials, rebounds after."""
    dips = [s.f_nuc for s in plan["syllables"]
            if s.nucleus in ("V_Open", "V_Tight_O")]
    dips += [s.f_on for s in plan["syllables"] if s.onset == "V_Explosive"]
    for side, base in (("L", base_l), ("R", base_r)):
        keys = {ctx.frame_start: base, ctx.frame_end: base}
        for f in dips:
            d = dip * ctx.rng.uniform(0.9, 1.25)
            for df, v in ((-5, base), (0, d), (6, base)):
                if ctx.frame_start < f + df < ctx.frame_end:
                    keys[f + df] = min(keys.get(f + df, base), v)
        for f, v in blooms:
            for df, vv in ((-6, base), (0, v), (10, base)):
                if ctx.frame_start < f + df < ctx.frame_end:
                    keys[f + df] = max(keys.get(f + df, base), vv)
        for f in sorted(keys):
            ctx.key_shape(f"Mouth_Smile_{side}", f, keys[f], layer=layer)


def _press(ctx, f, amp=0.28, dur=12):
    """Pressed-lips beat in a pause (asymmetric, rise-hold-release)."""
    for df, v in ((0, 0.0), (4, amp), (dur - 2, amp * 0.9), (dur + 4, 0.0)):
        ctx.key_shape_lr("Mouth_Press_{S}", f + df, v, layer='press',
                         r_scale=0.85)


def _gasp(ctx, f, depth=1.0):
    """Quick intake breath (sharper than seq.pause_breath)."""
    for df, v in ((0, 0.0), (3, -1.1 * depth), (9, -0.35 * depth), (16, 0.0)):
        ctx.key_bone_axis("CC_Base_Spine02", f + df, 'x', v, layer='breath2')
    for s in 'LR':
        k = f"Nose_Nostril_Dilate_{s}"
        ctx.key_shape(k, f, 0.0, layer='breath2')
        ctx.key_shape(k, f + 3, 0.16 * depth, layer='breath2')
        ctx.key_shape(k, f + 10, 0.0, layer='breath2')


def _slow_nod(ctx, f, deg=2.2):
    ctx.pitch("CC_Base_Head", f - 8, 0.0, layer='emph_head')
    ctx.pitch("CC_Base_Head", f + 1, deg, layer='emph_head')
    ctx.pitch("CC_Base_Head", f + 9, -0.2 * deg, layer='emph_head')
    ctx.pitch("CC_Base_Head", f + 19, 0.0, layer='emph_head')
    ctx.pitch("CC_Base_NeckTwist01", f - 6, 0.0, layer='emph_head')
    ctx.pitch("CC_Base_NeckTwist01", f + 3, deg * 0.35, layer='emph_head')
    ctx.pitch("CC_Base_NeckTwist01", f + 20, 0.0, layer='emph_head')


def _accents(ctx, plan, n, nod_deg=1.2, brow=(0.18, 0.30), tilt=0.0,
             margin=18):
    """n accents on stressed syllables, gestures rotating (nod/brow/both);
    tilt != 0 adds alternating-side head rolls (talk/talking_excited)."""
    safe = [s for s in plan["stressed"]
            if ctx.frame_start + margin <= s.f_nuc <= ctx.frame_end - margin]
    if not safe:
        return
    picks = safe[:: max(1, len(safe) // n)][:n]
    side = 1.0
    for i, s in enumerate(picks):
        kind = i % 3
        if kind in (0, 2):
            seq.emphasis_nod(ctx, s.f_nuc,
                             deg=nod_deg * ctx.rng.uniform(0.8, 1.2))
        if kind in (1, 2):
            seq.emphasis_brow(ctx, s.f_nuc, amp=ctx.rng.uniform(*brow))
        if tilt > 1e-4:
            f = s.f_nuc
            ctx.roll("CC_Base_Head", f - 4, 0.0, layer='tilt')
            ctx.roll("CC_Base_Head", f + 2, side * tilt, layer='tilt')
            ctx.roll("CC_Base_Head", f + 12, 0.0, layer='tilt')
            side = -side


# ===================== 6 s non-phonemic (talk_*) ==========================

@clip("talk_soft", "talking", 6.0, loop=True, framing='face', seed=404,
      still_frame=0.55, description="talk_idle at 60%: jaw <=0.1, long "
      "pauses, relaxed lids, quiet brows, near-still head")
def talk_soft(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 47), (F + 74, F + 117), (F + 143, F + 170)]
    plan = seq.speak(ctx, phrases, {
        "hint_mode": True, "syllable_rate": 3.9, "rate_jitter": 0.32,
        "hint_prob": 0.5, "hint_peak": (0.06, 0.10),
        "hint_jaw_units": (0.05, 0.13), "stress_every_s": 1.3})
    del plan
    _hold(ctx, "Eye_Blink_L", 0.10)          # relaxed lid tone
    _hold(ctx, "Eye_Blink_R", 0.09)
    seq.pause_breath(ctx, F + 49, depth=0.6)
    seq.pause_breath(ctx, F + 119, depth=0.55)
    for f in BAKED_BLINKS["talk_soft"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=3.0, amp=0.65, phase=0.7, head=0.4)
    motion.head_micro_sway(ctx, amp_deg=0.25)


@clip("talk_fast", "talking", 6.0, loop=True, framing='face', seed=405,
      still_frame=0.3, description="6+/s syllabic murmur, 2f jaw attacks, "
      "undershoot amplitudes, compressed pauses, catch-breath mid-loop")
def talk_fast(ctx):
    F = ctx.frame_start
    phrases = [(F + 6, F + 47), (F + 55, F + 107), (F + 118, F + 163)]
    plan = seq.speak(ctx, phrases, {
        "hint_mode": True, "syllable_rate": 6.3, "rate_jitter": 0.26,
        "hint_prob": 0.5, "hint_peak": (0.06, 0.11),
        "hint_jaw_units": (0.05, 0.12), "stress_every_s": 0.8})
    _accents(ctx, plan, 4, nod_deg=0.7, brow=(0.10, 0.16))
    _gasp(ctx, F + 109, depth=0.7)           # the 6f catch-breath mid-loop
    for f in BAKED_BLINKS["talk_fast"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.0, amp=0.7, phase=0.25, head=0.4)
    motion.head_micro_sway(ctx, amp_deg=0.4)


@clip("talk_excited", "talking", 6.0, loop=True, framing='face', seed=406,
      still_frame=0.45, description="talk_idle at 130%: smile 0.25 "
      "co-articulating, leaping brows, alternating head tilts, gasps")
def talk_excited(ctx):
    F = ctx.frame_start
    phrases = [(F + 7, F + 52), (F + 65, F + 122), (F + 133, F + 167)]
    plan = seq.speak(ctx, phrases, {
        "hint_mode": True, "syllable_rate": 4.5, "rate_jitter": 0.30,
        "hint_prob": 0.65, "hint_peak": (0.10, 0.17),
        "hint_jaw_units": (0.10, 0.28), "stress_every_s": 0.85})
    _smile(ctx, plan, 0.26, 0.22, 0.10)      # reduced, never zeroed
    _accents(ctx, plan, 5, nod_deg=1.1, brow=(0.20, 0.40), tilt=2.0)
    _gasp(ctx, F + 57, depth=1.0)            # pauses END with intake gasps
    _gasp(ctx, F + 126, depth=0.9)
    for f in BAKED_BLINKS["talk_excited"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.0, amp=1.0, phase=0.45, head=0.6)
    motion.head_micro_sway(ctx, amp_deg=0.55)


@clip("talk_serious", "talking", 6.0, loop=True, framing='face', seed=407,
      still_frame=0.52, description="Measured 3.7/s, pressed-lip pauses, "
      "0.2 furrow, two slow nods, weighted downbeat ~f95")
def talk_serious(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 55), (F + 78, F + 133), (F + 154, F + 171)]
    plan = seq.speak(ctx, phrases, {
        "hint_mode": True, "syllable_rate": 3.7, "rate_jitter": 0.28,
        "hint_prob": 0.55, "hint_peak": (0.08, 0.12),
        "hint_jaw_units": (0.12, 0.18), "stress_every_s": 1.0,
        "declination": 0.08})
    _hold(ctx, "Brow_Drop_L", 0.20)
    _hold(ctx, "Brow_Drop_R", 0.18)
    _press(ctx, F + 59, amp=0.30, dur=14)    # pauses PRESS, not just close
    _press(ctx, F + 138, amp=0.26, dur=12)
    # two head events only: one mid-P1 nod + the f95 weighted downbeat
    early = [s for s in plan["stressed"] if F + 20 <= s.f_nuc <= F + 50]
    if early:
        _slow_nod(ctx, early[0].f_nuc, deg=1.6)
    beat = min((s for s in plan["stressed"] if F + 80 <= s.f_nuc <= F + 130),
               key=lambda s: abs(s.f_nuc - (F + 94)), default=None)
    if beat:                                  # jaw+brow+nod land together
        _slow_nod(ctx, beat.f_nuc, deg=2.3)
        seq.emphasis_brow(ctx, beat.f_nuc, amp=0.26)
        ctx.jaw_open(beat.f_nuc - 4, 0.0, layer='accent')
        ctx.jaw_open(beat.f_nuc + 1, 1.3, layer='accent')
        ctx.jaw_open(beat.f_nuc + 8, 0.0, layer='accent')
    for f in BAKED_BLINKS["talk_serious"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=3.0, amp=0.75, phase=0.9, head=0.35)
    motion.head_micro_sway(ctx, amp_deg=0.3)


@clip("talk_whisper", "talking", 6.0, loop=True, framing='face', seed=408,
      still_frame=0.5, description="Jaw nearly shut; lips articulate "
      "(pucker/tight hints), shoulders high, lean-in, lookout eye-dart")
def talk_whisper(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 51), (F + 76, F + 125), (F + 148, F + 171)]
    plan = seq.speak(ctx, phrases, {
        "hint_mode": True, "syllable_rate": 3.2, "rate_jitter": 0.30,
        "hint_prob": 0.8, "hint_peak": (0.12, 0.18),
        "hint_visemes": ("V_Tight", "V_Tight_O"),
        "hint_jaw_units": (0.02, 0.05), "stress_every_s": 1.2})
    # lip-forward articulation: pucker flickers ride the syllables
    for i, s in enumerate(plan["syllables"]):
        if s.nucleus and i % 2 == 0:
            v = ctx.rng.uniform(0.10, 0.16)
            for pat in ("Mouth_Pucker_Up_{S}", "Mouth_Pucker_Down_{S}"):
                ctx.key_shape_lr(pat, s.f_nuc - 3, 0.0, layer='whisper',
                                 r_scale=0.9)
                ctx.key_shape_lr(pat, s.f_nuc, v, layer='whisper',
                                 r_scale=0.9)
                ctx.key_shape_lr(pat, s.f_nuc + 5, 0.0, layer='whisper',
                                 r_scale=0.9)
    _hold(ctx, "Eye_Wide_L", 0.15)
    _hold(ctx, "Eye_Wide_R", 0.13)
    for side, d in (('L', 1.0), ('R', 0.9)):  # conspiratorial shoulders
        ctx.clavicle_raise(side, F, d, layer='lean')
        ctx.clavicle_raise(side, ctx.frame_end, d, layer='lean')
    for bone, d in (("CC_Base_Spine02", 1.3), ("CC_Base_NeckTwist01", 1.6),
                    ("CC_Base_Head", -1.0)):  # lean in, face stays up
        ctx.pitch(bone, F, d, layer='lean')
        ctx.pitch(bone, ctx.frame_end, d, layer='lean')
    # lookout dart mid-loop (~f90): eyes only, quick out and back
    motion.gaze_to(ctx, F + 87, -0.30, 0.05, layer='gaze')
    motion.gaze_to(ctx, F + 103, 0.0, 0.0, from_dx=-0.30, from_dy=0.05,
                   layer='gaze')
    seq.pause_breath(ctx, F + 53, depth=1.0)   # breathy pauses
    seq.pause_breath(ctx, F + 127, depth=0.9)
    for f in BAKED_BLINKS["talk_whisper"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=3.0, amp=0.9, phase=0.05, head=0.3)
    motion.head_micro_sway(ctx, amp_deg=0.3)


# ===================== 8 s viseme chain (talking_*) =======================

@clip("talking_angry", "talking", 8.0, loop=True, framing='face', seed=409,
      still_frame=0.35, description="Punchy visemes +15%, pinned 0.5 brow, "
      "sneer flickers, hard pressed pauses, 3 head thrusts, 1 blink")
def talking_angry(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 69), (F + 86, F + 155), (F + 170, F + 231)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 3.5, "rate_jitter": 0.30, "viseme_energy": 1.15,
        "cons_attack": (2, 3), "nuc_attack": (2, 4),
        "bilabial_hold": (2, 4), "declination": 0.12})
    _hold(ctx, "Brow_Drop_L", 0.50)          # rage brow stays PINNED
    _hold(ctx, "Brow_Drop_R", 0.44)
    _hold(ctx, "Brow_Compress_L", 0.30)
    _hold(ctx, "Brow_Compress_R", 0.27)
    _hold(ctx, "Eye_Squint_L", 0.15)
    _hold(ctx, "Eye_Squint_R", 0.13)
    safe = [s for s in plan["stressed"]
            if F + 18 <= s.f_nuc <= ctx.frame_end - 20]
    for s in safe[:: max(1, len(safe) // 4)][:4]:   # sneer on stresses
        ctx.key_shape_lr("Nose_Sneer_{S}", s.f_nuc - 3, 0.0, layer='emote2',
                         r_scale=0.85)
        ctx.key_shape_lr("Nose_Sneer_{S}", s.f_nuc, 0.15, layer='emote2',
                         r_scale=0.85)
        ctx.key_shape_lr("Nose_Sneer_{S}", s.f_nuc + 8, 0.0, layer='emote2',
                         r_scale=0.85)
    # 3 head thrusts, asymmetric timing: fast jut, slower return
    thrusts = [safe[i].f_nuc for i in (0, len(safe) // 2, -1)] if len(
        safe) >= 3 else [s.f_nuc for s in safe]
    for f in thrusts:
        for bone, d in (("CC_Base_NeckTwist01", 2.0), ("CC_Base_Head", -0.9)):
            ctx.pitch(bone, f - 3, 0.0, layer='thrust')
            ctx.pitch(bone, f + 1, d, layer='thrust')
            ctx.pitch(bone, f + 13, 0.0, layer='thrust')
    _press(ctx, F + 73, amp=0.40, dur=12)    # swallowed-rage pauses
    _press(ctx, F + 158, amp=0.40, dur=10)
    for f in BAKED_BLINKS["talking_angry"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.67, amp=0.9, phase=0.6, head=0.4)
    motion.head_micro_sway(ctx, amp_deg=0.35)


@clip("talking_excited", "talking", 8.0, loop=True, framing='face', seed=410,
      still_frame=0.42, description="Over-articulated +20% visemes, leaping "
      "brows, co-articulated smile, stumble beat ~f120, alternating tilts")
def talking_excited(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 65), (F + 79, F + 116), (F + 121, F + 149),
               (F + 162, F + 225)]           # 4f catch-pause = the stumble
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 3.9, "rate_jitter": 0.30, "viseme_energy": 1.2,
        "peak_cap": 0.95, "stress_every_s": 0.85})
    # stumble beat: two rushed viseme flicks crash into the catch-pause
    for f, k, v in ((F + 109, "V_Wide", 0.5), (F + 113, "V_Open", 0.55)):
        ctx.key_shape(k, f - 3, 0.0, layer='accent')
        ctx.key_shape(k, f, v, layer='accent')
        ctx.key_shape(k, f + 4, 0.0, layer='accent')
        ctx.jaw_open(f - 3, 0.0, layer='accent')
        ctx.jaw_open(f, v * 4.5, layer='accent')
        ctx.jaw_open(f + 4, 0.0, layer='accent')
    _smile(ctx, plan, 0.26, 0.22, 0.10)
    _accents(ctx, plan, 6, nod_deg=1.1, brow=(0.20, 0.45), tilt=1.8)
    _gasp(ctx, F + 117, depth=0.8)           # the catch after the stumble
    seq.pause_breath(ctx, F + 67, depth=0.9)
    for f in BAKED_BLINKS["talking_excited"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.3, amp=1.0, phase=0.3, head=0.55)
    motion.head_micro_sway(ctx, amp_deg=0.55)


@clip("talking_serious", "talking", 8.0, loop=True, framing='face', seed=411,
      still_frame=0.4, description="Measured 3/s, held closures, 25-30f "
      "pressed pauses, 0.15 furrow, 2 nods synced to phrase-final stresses")
def talking_serious(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 63), (F + 91, F + 155), (F + 182, F + 229)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 3.0, "rate_jitter": 0.29, "viseme_energy": 1.0,
        "plateau_frac": 0.35, "plateau_max": 6, "bilabial_hold": (2, 3),
        "declination": 0.10, "stress_every_s": 1.1})
    _hold(ctx, "Brow_Drop_L", 0.15)
    _hold(ctx, "Brow_Drop_R", 0.13)
    _press(ctx, F + 66, amp=0.30, dur=16)
    _press(ctx, F + 158, amp=0.28, dur=14)
    # two slow nods landing WITH the phrase-final stressed syllables
    for p0, p1 in (phrases[0], phrases[1]):
        finals = [s for s in plan["stressed"] if p0 <= s.f_nuc <= p1]
        if finals:
            _slow_nod(ctx, finals[-1].f_nuc, deg=2.0)
    for f in BAKED_BLINKS["talking_serious"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=4.0, amp=0.6, phase=0.15, head=0.35)
    motion.head_micro_sway(ctx, amp_deg=0.35)      # micro at ~70%


@clip("talking_fast", "talking", 8.0, loop=True, framing='face', seed=412,
      still_frame=0.25, description="6+/s slurred visemes capped 0.5, two "
      "15-syllable sprints with gasps, very short pauses, stiller head")
def talking_fast(ctx):
    F = ctx.frame_start
    phrases = [(F + 6, F + 75), (F + 86, F + 135), (F + 144, F + 213)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 6.2, "rate_jitter": 0.26, "viseme_energy": 0.62,
        "peak_cap": 0.5, "min_overlap": 3, "onset_prob": 0.75,
        "coda_prob": 0.10, "jaw_amplitude": 0.75, "stress_every_s": 0.8})
    _accents(ctx, plan, 2, nod_deg=0.6, brow=(0.10, 0.15))
    _gasp(ctx, F + 77, depth=1.2)            # big gasps after the sprints
    _gasp(ctx, F + 215, depth=1.15)
    _gasp(ctx, F + 137, depth=0.6)           # quick catch between
    for f in BAKED_BLINKS["talking_fast"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.0, amp=0.85, phase=0.8, head=0.3)
    motion.head_micro_sway(ctx, amp_deg=0.3)       # energy is in the mouth


@clip("talking_slow", "talking", 8.0, loop=True, framing='face', seed=413,
      still_frame=0.45, description="2.7/s, peaks to 0.9 with wavering "
      "vowel holds, deliberate closures, teaching-cadence nods, 30f pauses")
def talking_slow(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 65), (F + 96, F + 157), (F + 187, F + 232)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 2.7, "rate_jitter": 0.33, "viseme_energy": 1.15,
        "peak_cap": 0.92, "plateau_thresh": 7, "plateau_max": 12,
        "plateau_frac": 0.6, "plateau_waver": 0.05, "bilabial_hold": (2, 3),
        "nuc_release": (5, 7), "stress_every_s": 1.2})
    # teaching cadence: a nod lands on each phrase-final word
    for p0, p1 in phrases:
        in_p = [s for s in plan["syllables"] if p0 <= s.f_nuc <= p1]
        if in_p:
            _slow_nod(ctx, in_p[-1].f_nuc, deg=1.9)
    seq.pause_breath(ctx, F + 67, depth=1.1)     # visible breaths
    seq.pause_breath(ctx, F + 159, depth=1.0)
    for f in BAKED_BLINKS["talking_slow"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=4.0, amp=0.9, phase=0.4, head=0.45)
    motion.head_micro_sway(ctx, amp_deg=0.4)


def _laugh_burst(ctx, f0, amps, head_toss=False):
    """Laugh burst: decaying jaw pulses w/ jittered spacing, V_Open+V_Wide
    held mix, eye squeeze, clavicle/chest bounce phase-locked to the jaw.
    Everything on the 'laugh' layer (sums over sequencer channels)."""
    L = 'laugh'
    ctx.jaw_open(f0 - 2, 0.0, layer=L)
    ctx.key_shape("Jaw_Open", f0 - 2, 0.0, layer=L)
    fp, pulse_frames = f0 + 3, []
    for a in amps:
        deg = a * 12.0
        ctx.jaw_open(fp, deg, layer=L)
        ctx.key_shape("Jaw_Open", fp, deg / 15.0, layer=L)
        ctx.jaw_open(fp + 4, deg * 0.38, layer=L)
        ctx.key_shape("Jaw_Open", fp + 4, deg * 0.38 / 15.0, layer=L)
        pulse_frames.append(fp)
        fp += 7 + ctx.rng.randint(-1, 1)
    end = fp + 2
    ctx.jaw_open(end, 0.0, layer=L)
    ctx.key_shape("Jaw_Open", end, 0.0, layer=L)
    for k, v in (("V_Open", 0.50), ("V_Wide", 0.32)):
        ctx.key_shape(k, f0, 0.0, layer=L)
        ctx.key_shape(k, f0 + 4, v, layer=L)
        ctx.key_shape(k, end - 3, v * 0.8, layer=L)
        ctx.key_shape(k, end + 4, 0.0, layer=L)
    ctx.key_shape_lr("Eye_Squint_{S}", f0, 0.0, layer=L, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 5, 0.5, layer=L, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", end + 6, 0.0, layer=L, r_scale=0.9)
    for fp2 in pulse_frames:                 # one physical event: same phase
        for side, s in (('L', 1.0), ('R', 0.85)):
            ctx.clavicle_raise(side, fp2 - 3, 0.0, layer=L)
            ctx.clavicle_raise(side, fp2, 0.8 * s, layer=L)
            ctx.clavicle_raise(side, fp2 + 4, 0.0, layer=L)
        ctx.key_bone_axis("CC_Base_Spine02", fp2, 'x', 0.5, layer=L)
        ctx.key_bone_axis("CC_Base_Spine02", fp2 + 4, 'x', 0.0, layer=L)
    if head_toss:
        ctx.pitch("CC_Base_Head", f0, 0.0, layer='toss')
        ctx.pitch("CC_Base_Head", f0 + 7, -3.2, layer='toss')
        ctx.pitch("CC_Base_Head", end, -2.2, layer='toss')
        ctx.pitch("CC_Base_Head", end + 12, 0.0, layer='toss')
        ctx.roll("CC_Base_Head", f0 + 4, 0.0, layer='toss')
        ctx.roll("CC_Base_Head", f0 + 10, 0.6, layer='toss')
        ctx.roll("CC_Base_Head", end + 8, 0.0, layer='toss')
    return end


@clip("talking_laughing", "talking", 8.0, loop=True, framing='face',
      seed=414, still_frame=0.27, description="Speech broken TWICE by laugh "
      "bursts (3 pulses then 2), wobbled resumes, head toss on burst 1 only")
def talking_laughing(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 57), (F + 92, F + 165), (F + 190, F + 227)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 3.5, "rate_jitter": 0.30, "viseme_energy": 1.0,
        "vowel_weights": {"V_Open": 0.30, "V_Wide": 0.30,
                          "V_Tight_O": 0.16, "schwa": 0.24}})
    _smile(ctx, plan, 0.50, 0.44, 0.22,
           blooms=[(F + 70, 0.72), (F + 176, 0.66)])
    # burst 1 (~f60, 3 pulses, head toss) / burst 2 (~f170, 2, no toss)
    e1 = _laugh_burst(ctx, F + 59, (0.55, 0.44, 0.30), head_toss=True)
    e2 = _laugh_burst(ctx, F + 168, (0.48, 0.30), head_toss=False)
    for f0 in (e1 + 2, e2 + 2):              # recovery breath after each
        _gasp(ctx, f0, depth=1.1)
    for p_start in (F + 92, F + 190):        # giggle-wobbled resumes
        ctx.jaw_open(p_start - 1, 0.0, layer='laugh')
        ctx.jaw_open(p_start + 3, 0.9, layer='laugh')
        ctx.jaw_open(p_start + 6, 0.3, layer='laugh')
        ctx.jaw_open(p_start + 9, 0.7, layer='laugh')
        ctx.jaw_open(p_start + 13, 0.0, layer='laugh')
    for f in BAKED_BLINKS["talking_laughing"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=2.67, amp=0.95, phase=0.55, head=0.5)
    motion.head_micro_sway(ctx, amp_deg=0.5)


@clip("talking_thinking", "talking", 8.0, loop=True, framing='face',
      seed=415, still_frame=0.24, description="Fragmented: two unequal "
      "stalls with held 'uh', gaze up-left, lip press; eyes return first")
def talking_thinking(ctx):
    F = ctx.frame_start
    phrases = [(F + 8, F + 51), (F + 94, F + 147), (F + 172, F + 225)]
    plan = seq.speak(ctx, phrases, {
        "syllable_rate": 3.1, "rate_jitter": 0.31, "viseme_energy": 0.9,
        "declination": 0.22,
        "vowel_weights": {"V_Open": 0.30, "V_Wide": 0.16,
                          "V_Tight_O": 0.14, "schwa": 0.40}})
    del plan

    def stall(f_break, f_resume, uh_amp, uh_len, tilt_deg, knit,
              press_at, press_dur):
        # gaze breaks away, 'uh' hangs with slack jaw, lips press,
        # eyes return 3f BEFORE speech resumes (thought found)
        dx = 0.30 if tilt_deg > 0 else -0.20
        motion.gaze_to(ctx, f_break + 1, dx, 0.26, layer='gaze')
        motion.gaze_to(ctx, f_resume - 3, 0.0, 0.0, from_dx=dx,
                       from_dy=0.26, layer='gaze')
        f_uh = f_break + 5
        ctx.key_shape("V_Open", f_uh - 4, 0.0, layer='stall')
        ctx.key_shape("V_Open", f_uh, uh_amp, layer='stall')
        ctx.key_shape("V_Open", f_uh + int(uh_len * 0.6), uh_amp * 0.9,
                      layer='stall')
        ctx.key_shape("V_Open", f_uh + uh_len, uh_amp * 0.95, layer='stall')
        ctx.key_shape("V_Open", f_uh + uh_len + 6, 0.0, layer='stall')
        ctx.jaw_open(f_uh - 4, 0.0, layer='stall')
        ctx.jaw_open(f_uh + 2, 0.85, layer='stall')      # slack jaw hangs
        ctx.jaw_open(f_uh + uh_len, 0.7, layer='stall')
        ctx.jaw_open(f_uh + uh_len + 7, 0.0, layer='stall')
        _press(ctx, press_at, amp=0.24, dur=press_dur)
        ctx.key_shape_lr("Brow_Compress_{S}", f_break, 0.0, layer='stall',
                         r_scale=0.9)
        ctx.key_shape_lr("Brow_Compress_{S}", f_break + 8, knit,
                         layer='stall', r_scale=0.9)
        ctx.key_shape_lr("Brow_Compress_{S}", f_resume + 2, 0.0,
                         layer='stall', r_scale=0.9)
        ctx.roll("CC_Base_Head", f_break, 0.0, layer='tilt')
        ctx.roll("CC_Base_Head", f_break + 14, tilt_deg, layer='tilt')
        ctx.roll("CC_Base_Head", f_resume + 4, 0.0, layer='tilt')

    stall(F + 52, F + 94, uh_amp=0.20, uh_len=12, tilt_deg=2.5, knit=0.28,
          press_at=F + 78, press_dur=9)      # keys clear f_resume
    stall(F + 148, F + 172, uh_amp=0.15, uh_len=7, tilt_deg=-1.8, knit=0.18,
          press_at=F + 161, press_dur=7)     # ends as P3 speech starts
    for f in BAKED_BLINKS["talking_thinking"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=4.0, amp=0.8, phase=0.85, head=0.45)
    motion.head_micro_sway(ctx, amp_deg=0.4)
