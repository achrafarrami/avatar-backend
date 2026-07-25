"""Talking clips — Tier 1 (lipsync owner).

talk_idle        6 s  non-phonemic murmur: syllabic jaw + viseme hints
talking_neutral  8 s  THE reference viseme chain (library_spec ruleset)
talking_happy    8 s  neutral chain + co-articulated smile + exhale beat

All three are SELF-SUFFICIENT base clips (per lead ruling): baked breathing,
phrase-boundary blinks, light head/brow emphasis included. Loop seams sit
mid-pause (jaw + visemes at rest) with value+velocity-matched channels.
Sequencer core: _speech_sequencer.py (skipped by the clip loader).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _speech_sequencer as seq                       # noqa: E402

from anim_framework.clips import clip                 # noqa: E402
from anim_framework import motion                     # noqa: E402

# Baked blink START frames per clip (absolute; frame_start is always 1).
# Single source of truth: scripts/patch_talking_meta.py reads this dict via
# ast to stamp previews/<cid>/meta.json with baked_blinks + runtime_notes
# (runtime blink scheduler must suppress procedural blinks for these clips).
BAKED_BLINKS = {
    "talk_idle": [51, 127, 158],
    "talking_neutral": [60, 145, 218],
    "talking_happy": [63, 147, 215],
}


def _blink(ctx, f):
    """Blink with the R-lid lag capped at 1 frame (QA dim6 fix: a 2 f lag
    freeze-frames as a WINK on the chunky toon lids). Peak-value asymmetry
    is kept (r_scale inside add_blink). The draws below mirror add_blink's
    original RNG order so every non-blink curve stays byte-identical."""
    close = ctx.rng.randint(3, 4)
    open_ = ctx.rng.randint(5, 7)
    ctx.rng.randint(1, 2)          # discarded: the old r_offset draw
    motion.add_blink(ctx, f, close=close, open_=open_, r_offset=1)


def _smile_channel(ctx, plan, base_l=0.32, base_r=0.27, dip=0.11,
                   blooms=(), layer='emote'):
    """Co-articulated smile: baseline that reduces toward `dip` during
    rounded/open visemes and bilabial closures (lips must reach the shape),
    rebounding after — the smile breathes with speech (library_spec happy
    beats). `blooms` = [(f_peak, value)] moments that push ABOVE baseline."""
    dips = []
    for s in plan["syllables"]:
        if s.nucleus in ("V_Open", "V_Tight_O"):
            dips.append(s.f_nuc)
        if s.onset == "V_Explosive":
            dips.append(s.f_on)
    for side, base in (("L", base_l), ("R", base_r)):
        keys = {ctx.frame_start: base, ctx.frame_end: base}
        for f in dips:
            d = dip * ctx.rng.uniform(0.9, 1.25)
            for df, v in ((-5, base), (0, d), (6, base)):
                fk = f + df
                if ctx.frame_start < fk < ctx.frame_end:
                    keys[fk] = min(keys.get(fk, base), v)
        for f, v in blooms:
            for df, vv in ((-6, base), (0, v), (10, base)):
                fk = f + df
                if ctx.frame_start < fk < ctx.frame_end:
                    keys[fk] = max(keys.get(fk, base), vv)
        for f in sorted(keys):
            ctx.key_shape(f"Mouth_Smile_{side}", f, keys[f], layer=layer)


def _emphasis(ctx, plan, per_phrase_nods=2, nod_deg=1.5, brow_amp=0.22,
              brow_extra=0):
    """Brow raises + head nods on stressed syllables: `per_phrase_nods` nods
    per phrase (spec), brows on a rotating subset. Gestures alternate so no
    two consecutive accents are identical."""
    margin = 16
    lo = ctx.frame_start + margin
    hi = ctx.frame_end - margin
    for p0, p1 in plan["phrases"]:
        stressed = [s for s in plan["stressed"]
                    if p0 <= s.f_nuc <= p1 and lo <= s.f_nuc <= hi]
        if not stressed:
            continue
        stressed = sorted(stressed, key=lambda s: s.f_nuc)
        step = max(1, len(stressed) // max(1, per_phrase_nods))
        picks = stressed[::step][:per_phrase_nods + brow_extra]
        for i, s in enumerate(picks):
            kind = i % 3     # rotate: nod / brow / both
            if kind in (0, 2) and i < per_phrase_nods:
                seq.emphasis_nod(ctx, s.f_nuc,
                                 deg=nod_deg * ctx.rng.uniform(0.8, 1.2))
            if kind in (1, 2):
                seq.emphasis_brow(ctx, s.f_nuc,
                                  amp=brow_amp * ctx.rng.uniform(0.85, 1.15))


# ---------------------------------------------------------------------------
# talk_idle — 6 s non-phonemic murmur (library_spec: talk_idle)
# ---------------------------------------------------------------------------
@clip("talk_idle", "talking", 6.0, loop=True, framing='face', seed=101,
      still_frame=0.5,
      description="Non-phonemic conversational mouth: syllabic jaw ~4.3/s, "
                  "V_Wide/V_Tight_O hints, 3 unequal phrases, seam mid-pause")
def talk_idle(ctx):
    F = ctx.frame_start          # 1 .. 181
    # head-rest 7f | P1 41f | pause 18f | P2 58f | pause 14f | P3 34f | tail 9f
    phrases = [(F + 7, F + 48), (F + 66, F + 124), (F + 138, F + 172)]
    style = {
        "hint_mode": True, "syllable_rate": 4.3, "rate_jitter": 0.32,
        "hint_prob": 0.55, "hint_peak": (0.08, 0.13),
        "hint_jaw_units": (0.08, 0.22), "stress_every_s": 1.1,
    }
    plan = seq.speak(ctx, phrases, style)
    # brow accents 0.1 on ~4 stressed beats, micro-nods on 2 (spec beats)
    safe = [s for s in plan["stressed"]
            if F + 16 <= s.f_nuc <= ctx.frame_end - 18]
    picks = safe[:: max(1, len(safe) // 4)][:4]
    for i, s in enumerate(picks):
        seq.emphasis_brow(ctx, s.f_nuc, amp=0.10)
        if i % 2 == 0:
            seq.emphasis_nod(ctx, s.f_nuc, deg=0.9)
    # breath in each internal pause; blink at each phrase boundary
    seq.pause_breath(ctx, F + 50, depth=0.8)
    seq.pause_breath(ctx, F + 126, depth=0.7)
    for f in BAKED_BLINKS["talk_idle"]:     # last ends ~F+171, tail clean
        _blink(ctx, f)
    motion.breathing(ctx, period=3.0, amp=0.75, phase=0.15, head=0.6)
    motion.head_micro_sway(ctx, amp_deg=0.45)


# ---------------------------------------------------------------------------
# talking_neutral — 8 s reference viseme chain (library_spec ruleset)
# ---------------------------------------------------------------------------
@clip("talking_neutral", "talking", 8.0, loop=True, framing='face', seed=202,
      still_frame=0.4,
      description="Reference viseme sequencing: 55/70/75f phrases, "
                  "coarticulated visemes 0.6-0.8, jaw 30-50% under, "
                  "bilabial Mouth_Close holds, tongue on dentals")
def talking_neutral(ctx):
    F = ctx.frame_start          # 1 .. 241
    # head 9f | P1 55f | pause 14f | P2 70f | pause 12f | P3 75f | tail 6f
    phrases = [(F + 9, F + 63), (F + 78, F + 147), (F + 160, F + 234)]
    style = {
        "syllable_rate": 3.4, "rate_jitter": 0.30,
        "viseme_energy": 1.0, "jaw_amplitude": 1.0,
    }
    plan = seq.speak(ctx, phrases, style)
    _emphasis(ctx, plan, per_phrase_nods=2, nod_deg=1.5, brow_amp=0.22,
              brow_extra=1)
    # breath intake at each internal pause start (nostril + chest)
    seq.pause_breath(ctx, F + 64, depth=1.0)
    seq.pause_breath(ctx, F + 148, depth=0.85)
    # blink near each phrase end (P3's early enough to clear the seam)
    for f in BAKED_BLINKS["talking_neutral"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=4.0, amp=0.85, phase=0.55, head=0.5)
    motion.head_micro_sway(ctx, amp_deg=0.5)


# ---------------------------------------------------------------------------
# talking_happy — 8 s neutral chain + co-articulated smile (library_spec)
# ---------------------------------------------------------------------------
@clip("talking_happy", "talking", 8.0, loop=True, framing='face', seed=303,
      still_frame=0.63,
      description="Viseme chain + breathing smile 0.3 (dips on rounded "
                  "visemes), cheeks 0.25 stable, bright brows, laugh-adjacent"
                  " exhale at ~f155, lighter/more frequent nods")
def talking_happy(ctx):
    F = ctx.frame_start          # 1 .. 241
    # head 8f | P1 58f | pause 16f | P2 66f | pause 20f (exhale) | P3 62f | tail 11f
    phrases = [(F + 8, F + 65), (F + 82, F + 147), (F + 168, F + 229)]
    style = {
        "syllable_rate": 3.55, "rate_jitter": 0.30,
        "viseme_energy": 1.0, "jaw_amplitude": 1.0,
        "vowel_weights": {"V_Open": 0.28, "V_Wide": 0.34,
                          "V_Tight_O": 0.16, "schwa": 0.22},
    }
    plan = seq.speak(ctx, phrases, style)

    # persistent smile 0.3 that co-articulates + blooms on the exhale beat
    _smile_channel(ctx, plan, base_l=0.32, base_r=0.27, dip=0.11,
                   blooms=[(F + 159, 0.48)])
    # cheeks stable (spec: cheeks do NOT animate per-viseme)
    for side, v in (("L", 0.26), ("R", 0.23)):
        ctx.key_shape(f"Cheek_Raise_{side}", F, v, layer='emote')
        ctx.key_shape(f"Cheek_Raise_{side}", ctx.frame_end, v, layer='emote')
    # bright brows: constant +0.1 under the accent raises; soft eye warmth
    for pat, v in (("Brow_Raise_Inner_{S}", 0.10), ("Eye_Squint_{S}", 0.06)):
        ctx.key_shape_lr(pat, F, v, layer='emote', r_scale=0.9)
        ctx.key_shape_lr(pat, ctx.frame_end, v, layer='emote', r_scale=0.9)

    # laugh-adjacent exhale in pause 2 (~f155): jaw pulse + squint + chest
    for f, deg in ((F + 154, 0.0), (F + 158, 3.8), (F + 162, 1.0),
                   (F + 166, 0.0)):
        ctx.jaw_open(f, deg, layer='jaw')
        ctx.key_shape("Jaw_Open", f, deg / 15.0, layer='jaw')
    for df, v in ((4, 0.06), (9, 0.32), (15, 0.14), (24, 0.06)):
        ctx.key_shape_lr("Eye_Squint_{S}", F + 150 + df, v, layer='emote',
                         r_scale=0.92)
    for df, v in ((4, 0.0), (7, 0.55), (12, -0.35), (18, 0.0)):
        ctx.key_bone_axis("CC_Base_Spine02", F + 150 + df, 'x', v,
                          layer='breath2')
    ctx.pitch("CC_Base_Head", F + 152, 0.0, layer='emph_head')
    ctx.pitch("CC_Base_Head", F + 158, -1.1, layer='emph_head')
    ctx.pitch("CC_Base_Head", F + 168, 0.0, layer='emph_head')

    # lighter, more frequent nods than neutral (spec)
    _emphasis(ctx, plan, per_phrase_nods=3, nod_deg=1.0, brow_amp=0.18,
              brow_extra=1)
    seq.pause_breath(ctx, F + 66, depth=0.9)
    for f in BAKED_BLINKS["talking_happy"]:
        _blink(ctx, f)
    motion.breathing(ctx, period=8.0 / 3.0, amp=0.9, phase=0.35, head=0.5)
    motion.head_micro_sway(ctx, amp_deg=0.5)
