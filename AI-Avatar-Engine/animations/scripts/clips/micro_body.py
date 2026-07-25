"""micro_body_layer — Tier-1 additive body-life loop (owner: body).

ADDITIVE over any standing base. Contract (library_spec):
- fingers: slow 0.5-2 deg curl/uncurl waves, phase-offset per finger
  (motion.finger_relax — per-hand random phase + per-finger 0.12 offset,
  so fingers are never in unison and hands are decorrelated)
- full-hand soft curl ripples at f100 (R) and f290 (L) — different side,
  size and spacing on purpose (anti-metronome)
- wrist rotation noise <= 1.5 deg both hands, decorrelated L/R (different
  cycle mixes AND independent random phases — never mirrored)
- shoulder micro <= 0.5 deg (clavicles, decorrelated L/R)
- pelvis weight micro-adjust x2 (Hip translation 0.35 / -0.25 cm with the
  planted-feet thigh counter from idle.py and a tiny Spine01/02 roll
  counter-lean; unequal spacing/amplitude/direction)
- HEAD EXCLUDED — head_micro owns head/neck; stacking two head layers
  doubles amplitude. No head or neck keys anywhere in this clip.
- additive zero-delta seams: all noise channels fade to zero at both
  boundaries (fade=0.08); all events live >= 15 f inside the loop.
This layer should be sensed, not seen: nothing here exceeds ~1.5 deg /
0.35 cm.
"""
from anim_framework.clips import clip
from anim_framework import motion

K_LAT = 0.667  # thigh z deg per cm hip x (measured; keeps feet planted)


def _ev(fn, f0, pts):
    for off, v in pts:
        fn(f0 + off, v)


def _ripple(ctx, f0, side, amp, gap=2):
    """Soft full-hand curl ripple: index-to-pinky cascade, then relax."""
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        for joint, ja in ((1, 1.0), (2, 0.8), (3, 0.6)):
            _ev(lambda f, v, fn=fng, j=joint: ctx.finger_curl(
                side, fn, j, f, v, layer='ev_ripple'),
                f0 + i * gap, [(0, 0.0), (7, amp * ja), (12, amp * ja * 0.8),
                               (20, 0.0)])
    _ev(lambda f, v: ctx.finger_curl(side, "Thumb", 2, f, v,
                                     layer='ev_ripple'),
        f0 + 3, [(0, 0.0), (8, amp * 0.4), (18, 0.0)])


def _weight_micro(ctx, f0, x_cm, dur):
    """One barely-there weight re-settle: Hip x + thigh counter (feet stay
    planted) + tiny spine roll counter lagged 2 f. Returns to exact zero."""
    pts = [(0, 0.0), (int(dur * 0.35), x_cm * 1.12),   # soft overshoot
           (int(dur * 0.55), x_cm * 0.96), (dur, x_cm),
           (dur + 34, x_cm * 0.9), (dur + 58, 0.0)]
    for off, v in pts:
        ctx.key_bone_loc_world("Hip", f0 + off, (v, 0.0, 0.0),
                               layer='wmicro')
        for s in ('L', 'R'):
            ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f0 + off, 'z',
                              -K_LAT * v, layer='wmicro')
    for off, v in pts:
        ctx.roll("CC_Base_Spine01", f0 + off + 2, -0.55 * v, layer='wmicro')
        ctx.roll("CC_Base_Spine02", f0 + off + 2, -0.30 * v, layer='wmicro')


@clip("micro_body_layer", "micro_layer", 12.0, loop=True, framing='body',
      still_frame=0.28,
      description="Additive body life: phase-offset finger drift, full-hand "
                  "ripples f100(R)/f290(L), decorrelated wrist noise "
                  "<=1.5 deg, shoulder micro <=0.5 deg, two pelvis weight "
                  "micro-adjusts; HEAD/NECK excluded (head_micro owns "
                  "them); zero-delta seams")
def micro_body_layer(ctx):
    F = ctx.frame_start
    # finger relaxation drift — 0.5-2 deg waves, never in unison
    motion.finger_relax(ctx, amp_deg=1.25, period=8.5)
    # full-hand soft ripples: R at f100 (bigger), L at f290 (smaller,
    # slower cascade) — different side/size/gap, unequal spacing
    _ripple(ctx, F + 100, 'R', 4.0, gap=2)
    _ripple(ctx, F + 290, 'L', 3.0, gap=3)
    # wrist rotation noise <= 1.5 deg, decorrelated L/R (different cycle
    # mixes + independent phases), zero at seams
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis(
        "CC_Base_L_Forearm", f, 'y', v, layer='wrist'),
        amp=1.25, cycles=(1, 2, 3), step=6, fade=0.08)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis(
        "CC_Base_R_Forearm", f, 'y', v, layer='wrist'),
        amp=1.05, cycles=(2, 3, 5), step=6, fade=0.08)
    # shoulder micro <= 0.5 deg, decorrelated, zero at seams
    motion.loop_noise(ctx, lambda f, v: ctx.clavicle_raise('L', f, v,
                                                           layer='shmicro'),
        amp=0.32, cycles=(1, 3), step=7, fade=0.08)
    motion.loop_noise(ctx, lambda f, v: ctx.clavicle_raise('R', f, v,
                                                           layer='shmicro'),
        amp=0.26, cycles=(2, 5), step=7, fade=0.08)
    # pelvis weight micro-adjust x2 — unequal spacing, size and direction
    _weight_micro(ctx, F + 58, 0.35, 22)    # ends ~F+138
    _weight_micro(ctx, F + 228, -0.25, 28)  # ends ~F+314 (>= 15 f margin)
