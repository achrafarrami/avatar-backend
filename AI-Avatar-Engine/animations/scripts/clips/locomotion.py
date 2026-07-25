"""Locomotion / full-body clips (Tier 3, owner: body) — 18 per library_spec.

The hard-won rig facts (calibrated on meta_male by world-space probe sweeps
against the template, see qa/rig_reference.json):

- Legs (foot-planting kinematics): +thigh-x swings the whole leg FORWARD-up
  (foot travels toward -Y and rises); -calf-x flexes the knee (shin drops
  back); +foot-x dorsiflexes (heel down / toe up). Seated pose that keeps
  BOTH FEET FLAT on the floor (foot world-z ~= rest 0.05 m): Hip world
  (0, +18, -45) cm, thigh +92, calf -98, foot +12 -> hip at seat height
  0.475 m, knees level, feet planted. This ONE seated pose is shared by
  sit_down (end), sit_idle (hold) and stand_up (start) so the chain contract
  holds (sit_down end == sit_idle f0; stand_up start == sit_idle pose).
- Root convention: CC_Base_BoneRoot is NEVER keyed; loops are IN PLACE (the
  legs treadmill under a stationary hip, a runtime root-motion curve drives
  real advance). CC_Base_Hip carries turn-yaw, vertical (sit/bob) and lateral
  (sway) translation + pelvis yaw/roll rotation.
- NeckTwist01/02 ARE the neck chain (legit to key). Twist/Share bones are
  never keyed by authors.

Conventions (keying.py): pitch+ = tip forward/down, yaw+ = character-LEFT,
roll+ = tilt toward LEFT shoulder; clavicle_raise+ lifts; finger_curl+ toward
palm; hip loc in armature cm (x+ left, y+ back, z+ up). Layers SUM at flush —
all ABSOLUTE posing goes on ONE layer 'B'; only genuine additive micro-life
(breathing, finger_relax, loop_noise) rides its own layers.
"""
from anim_framework.clips import clip
from anim_framework import motion

B = 'base'  # single absolute-pose layer (see gestures.py layering contract)

# idle-compatible standing hang (probe-matched to idle_01 f0 / gestures _HANG)
# side -> (Upperarm x,y,z, Forearm x, Forearm z, finger_scale)
_HANG = {
    'L': (8.0, -10.0, -58.0, 12.0, -3.0, 1.0),
    'R': (7.5, 9.0, 57.13, 11.04, 3.0, 0.94),
}
_FING = (("Index", 4.0), ("Mid", 5.5), ("Ring", 7.0), ("Pinky", 8.5))

# planted-feet constants for hip translation (measured: thigh 15deg -> foot
# 22.5 cm); used when a clip translates the hip and the feet must not skate.
K_LAT = 0.667   # thigh z deg per cm hip x
K_FA = 0.667    # thigh x deg per cm hip y

# shared seated pose (feet-planted, probe-verified)
SEAT_HIP = (0.0, 18.0, -45.0)          # Hip world cm
SEAT_LEG = {'thigh': 92.0, 'calf': -98.0, 'foot': 12.0}
# hands resting on the thighs (probe-verified: fingertips land on the thigh-top
# mesh ~y-0.35/z0.56, forward-down straight-ish arm). L mirrors R (z, y negate).
SEAT_ARM = {'L': ((54.0, 8.0, -46.0), (20.0, 0.0)),
            'R': ((54.0, -8.0, 46.0), (20.0, 0.0))}


def _ev(fn, f0, pts):
    for off, v in pts:
        fn(f0 + off, v)


def _beats(fn, table, n, beat, F=1):
    """Key a per-beat pattern at EVERY beat across a long loop clip. Use this
    (not _cyc) when the sub-cycle period is shorter than the clip length —
    _cyc only fills one period and loop-closure would flatten the remainder.
    Emits matched phase-0 keys at F and F+n*beat (the clip seam) so the loop
    closes with equal value AND tangent (no force-snap warning)."""
    pts = sorted((o % beat, float(v)) for o, v in table)

    def interp(x):
        for i in range(len(pts)):
            t0, v0 = pts[i]
            t1, v1 = pts[(i + 1) % len(pts)]
            span = (t1 - t0) % beat or beat
            d = (x - t0) % beat
            if d <= span + 1e-6:
                return v0 + (v1 - v0) * (d / span)
        return pts[0][1]

    v_seam = interp(0.0)
    span_f = n * beat
    fn(F, v_seam)
    for b in range(n):
        for off, v in table:
            t = b * beat + off
            if 0 < t < span_f:
                fn(F + t, v)
    fn(F + span_f, v_seam)


def _beats_scaled(fn, table, scales, beat, F=1):
    """Like _beats but each beat's amplitude is multiplied by scales[b] so no
    two beats carry identical energy (kills the per-beat metronome). The seam
    matches beat-0's scaled phase-0 value so the loop still closes cleanly."""
    n = len(scales)
    pts = sorted((o % beat, float(v)) for o, v in table)

    def interp(x):
        for i in range(len(pts)):
            t0, v0 = pts[i]
            t1, v1 = pts[(i + 1) % len(pts)]
            span = (t1 - t0) % beat or beat
            d = (x - t0) % beat
            if d <= span + 1e-6:
                return v0 + (v1 - v0) * (d / span)
        return pts[0][1]

    v_seam = interp(0.0) * scales[0]
    span_f = n * beat
    fn(F, v_seam)
    for b in range(n):
        for off, v in table:
            t = b * beat + off
            if 0 < t < span_f:
                fn(F + t, v * scales[b])
    fn(F + span_f, v_seam)


def _cyc(fn, table, phase=0, period=36, F=1):
    """Key a PERIODIC channel from control points and guarantee loop closure.

    `table` = [(offset_in_period, value)] with offsets in [0, period). `phase`
    shifts the pattern right (a lagging limb passes phase=+18 on a 36f cycle).
    Emits a key at every control point plus matched keys at f0 and f0+period
    (value linearly interpolated across the seam) so the auto-CYCLES modifier
    closes without a flat spot."""
    pts = sorted(((off + phase) % period, float(v)) for off, v in table)

    def interp(x):
        for i in range(len(pts)):
            t0, v0 = pts[i]
            t1, v1 = pts[(i + 1) % len(pts)]
            span = (t1 - t0) % period or period
            d = (x - t0) % period
            if d <= span + 1e-6:
                return v0 + (v1 - v0) * (d / span)
        return pts[0][1]

    v_seam = interp(0.0)
    fn(F, v_seam)
    for t, v in pts:
        if 0 < t < period:
            fn(F + t, v)
    fn(F + period, v_seam)


# --- pose primitives ------------------------------------------------------
def _hang_arm(ctx, side, frames, layer=B, fingers=True, scale=1.0):
    ux, uy, uz, fx, fz, csc = _HANG[side]
    for f in frames:
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'x', ux, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'y', uy, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'z', uz, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Forearm", f, 'x', fx, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Forearm", f, 'z', fz, layer=layer)
        if fingers:
            _hang_fingers(ctx, side, [f], layer=layer)


def _hang_fingers(ctx, side, frames, layer=B, scale=1.0):
    csc = _HANG[side][5] * scale
    for f in frames:
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
                ctx.finger_curl(side, fng, j, f, a * ja * csc, layer=layer)
        ctx.finger_curl(side, "Thumb", 2, f, 3.0, layer=layer)


def _both_hang(ctx, frames, layer=B):
    for s in ('L', 'R'):
        _hang_arm(ctx, s, frames, layer=layer)


def _stand_legs(ctx, frames, layer=B):
    """Legs at standing rest (0) — the idle-compatible base for one-shots."""
    for f in frames:
        for s in ('L', 'R'):
            for bn in ('Thigh', 'Calf', 'Foot'):
                ctx.key_bone_axis(f"CC_Base_{s}_{bn}", f, 'x', 0.0, layer=layer)


def _seated_pose(ctx, frames, layer=B, arms=True, hip=True):
    """Author the shared seated pose (feet planted) at each frame. Pass
    hip=False when the caller drives CC_Base_Hip on its own separate layers
    (stand_up ramps hip via hz/hy) — otherwise the two hip sources SUM."""
    for f in frames:
        if hip:
            ctx.key_bone_loc_world("Hip", f, SEAT_HIP, layer=layer)
        for s in ('L', 'R'):
            # tiny R/L asymmetry so the two legs aren't byte-identical
            a = 1.0 if s == 'L' else 0.97
            ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f, 'x',
                              SEAT_LEG['thigh'] * a, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Calf", f, 'x',
                              SEAT_LEG['calf'] * a, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Foot", f, 'x',
                              SEAT_LEG['foot'], layer=layer)
        # torso: soft C-curve, slight relaxed slump (not military)
        ctx.pitch("CC_Base_Spine01", f, 3.0, layer=layer)
        ctx.pitch("CC_Base_Spine02", f, 2.2, layer=layer)
        ctx.pitch("CC_Base_NeckTwist01", f, -1.5, layer=layer)  # lift chin level
        ctx.pitch("CC_Base_Head", f, -1.0, layer=layer)
        if arms:
            _seated_arms(ctx, [f], layer=layer)


def _seated_arms(ctx, frames, layer=B):
    """Hands resting on the thighs (seated). Probe-verified reach — hands sit
    a touch proud of the thigh-top mesh (safe, no interpenetration)."""
    for f in frames:
        for s, (ua, fa) in SEAT_ARM.items():
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'x', ua[0], layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'y', ua[1], layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'z', ua[2], layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'x', fa[0], layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'z', fa[1], layer=layer)
            for fng, a in _FING:  # soft natural curl resting on the thigh
                for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
                    ctx.finger_curl(s, fng, j, f, (a + 6.0) * ja, layer=layer)
            ctx.finger_curl(s, "Thumb", 2, f, 4.0, layer=layer)


# ===========================================================================
# WALK  — 36f cycle, in place, loop
# ===========================================================================
# L-leg phase tables over one 36f cycle (R = same, phase +18, x0.98 amplitude)
_W_THIGH = [(0, 22), (4, 13), (9, 2), (13, -12), (17, -20), (22, -12),
            (28, 6), (33, 18)]
_W_CALF = [(0, -10), (4, -18), (9, -6), (13, -8), (17, -22), (22, -47),
           (28, -38), (33, -16)]
_W_FOOT = [(0, 16), (4, 0), (9, -3), (13, -14), (17, -26), (22, -4),
           (28, 6), (33, 14)]
_W_TOE = [(0, 0), (9, 0), (13, -8), (17, -24), (20, -10), (24, 0)]


@clip("walk", "locomotion", 1.2, loop=True, framing='body', still_frame=0.25,
      description="In-place walk, 36f/2-step cycle. Contact f0/f18, down "
                  "f4/f22 (hips lowest), passing f9/f27 (hips highest), "
                  "toe-off f17/f35. Pelvis yaw/roll+sway, spine counter 2f "
                  "behind, opposite-arm swing 28deg w/ elbow bend on "
                  "backswing, heel->toe foot roll w/ toe articulation, head "
                  "counter-stabilizes bob. R stride 2% shorter (asymmetry).")
def walk(ctx):
    F = ctx.frame_start
    motion.breathing(ctx, period=4.0, amp=0.3, phase=0.4, shoulders=0.5)
    # --- legs (treadmill) ---
    for s, ph, sc in (('L', 0, 1.0), ('R', 18, 0.98)):
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _W_THIGH], ph, 36, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Calf", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _W_CALF], ph, 36, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _W_FOOT], ph, 36, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_ToeBase", f,
             'x', v, layer=B), _W_TOE, ph, 36, F)
    # --- hip: bob (z, 2/cycle), lateral sway (x, 1/cycle), fore-aft settle ---
    _cyc(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
         layer='hipz'),
         [(0, 0), (4, -2.0), (9, 0.6), (13, 1.9), (17, 0.4), (22, -2.0),
          (27, 0.6), (31, 1.9), (35, 0.4)], 0, 36, F)
    _cyc(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
         layer='hipx'),
         [(0, 1.4), (6, 1.8), (13, 1.0), (18, -1.4), (24, -1.8), (31, -1.0)],
         0, 36, F)
    # --- pelvis yaw (leads swing leg) + roll (drops on swing side) ---
    _cyc(lambda f, v: ctx.yaw("CC_Base_Hip", f, v, layer='pyaw'),
         [(0, 0), (9, 4), (18, 0), (27, -4)], 0, 36, F)
    _cyc(lambda f, v: ctx.roll("CC_Base_Hip", f, v, layer='proll'),
         [(0, -2), (9, -3), (17, 0), (22, 3), (27, 2), (31, 0)], 0, 36, F)
    # --- spine counter-rotates opposite pelvis, ~2f behind ---
    _cyc(lambda f, v: ctx.yaw("CC_Base_Spine01", f, v, layer='syaw'),
         [(2, 0), (11, -3.2), (20, 0), (29, 3.2)], 0, 36, F)
    _cyc(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='syaw'),
         [(2, 0), (11, -2.0), (20, 0), (29, 2.0)], 0, 36, F)
    # --- arms swing opposite the legs (R fwd at f0), elbow bends on backswing
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
         [(0, 34), (9, 7.5), (18, -16), (27, 7.5)], 0, 36, F)
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
         [(0, -14), (9, 8), (18, 34), (27, 8)], 0, 36, F)
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
         [(0, 15), (9, 22), (18, 36), (27, 22)], 0, 36, F)
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'x', v, B),
         [(0, 36), (9, 22), (18, 15), (27, 22)], 0, 36, F)
    # keep the wing angles + relaxed fingers at the hang baseline
    for s in ('L', 'R'):
        ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", F, 'y', _HANG[s][1], B)
        ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", F + 36, 'y', _HANG[s][1], B)
        ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", F, 'z', _HANG[s][2], B)
        ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", F + 36, 'z', _HANG[s][2], B)
    _hang_fingers(ctx, 'L', [F, F + 36])
    _hang_fingers(ctx, 'R', [F, F + 36])
    # --- head counter-stabilizes the hip bob (net eyeline steady) ---
    _cyc(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='hstab'),
         [(0, 0), (4, 0.6), (9, -0.3), (13, -0.5), (22, 0.6), (31, -0.5)],
         0, 36, F)
    _cyc(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='hstab'),
         [(0, 0.5), (9, 0.6), (18, -0.5), (27, -0.6)], 0, 36, F)
    motion.finger_relax(ctx, amp_deg=1.2, period=6.0)


# ===========================================================================
# RUN — 24f cycle, in place, airborne, loop
# ===========================================================================
_R_THIGH = [(0, 30), (3, 18), (7, -8), (10, -26), (13, -20), (17, 20),
            (20, 34)]
_R_CALF = [(0, -30), (3, -40), (7, -20), (10, -70), (13, -95), (17, -80),
           (20, -45)]
_R_FOOT = [(0, 8), (3, -6), (7, -28), (10, -10), (13, 6), (17, 4), (20, 10)]


@clip("run", "locomotion", 0.8, loop=True, framing='body', still_frame=0.2,
      description="In-place run, 24f/2-stride cycle w/ AIRBORNE phases "
                  "(both feet off f5-7, f17-19). Contact f0/f12 mid-foot w/ "
                  "2f knee-absorb dip (hips 7cm range), spine leans 8deg fwd, "
                  "arms pump at 90deg elbows soft-fisted (35deg drive), "
                  "shoulders drive 4deg, head 1cm residual bounce. R stride "
                  "3% shorter (asymmetry).")
def run(ctx):
    F = ctx.frame_start
    motion.breathing(ctx, period=2.0, amp=0.2, phase=0.6, shoulders=0.4)
    for s, ph, sc in (('L', 0, 1.0), ('R', 12, 0.97)):
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _R_THIGH], ph, 24, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Calf", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _R_CALF], ph, 24, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
             'x', v, layer=B), [(o, v * sc) for o, v in _R_FOOT], ph, 24, F)
        _cyc(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_ToeBase", f,
             'x', v, layer=B),
             [(0, 0), (7, -22), (10, -6), (13, 0)], ph, 24, F)
    # hip: big vertical (lowest at contact-absorb f2/f14, highest airborne
    # f6/f18), slight sway
    _cyc(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
         layer='hipz'),
         [(0, 0.5), (2, -3.5), (6, 3.5), (10, 0.0), (14, -3.5), (18, 3.5),
          (22, 0.0)], 0, 24, F)
    _cyc(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
         layer='hipx'),
         [(0, 1.0), (6, 1.3), (12, -1.0), (18, -1.3)], 0, 24, F)
    _cyc(lambda f, v: ctx.yaw("CC_Base_Hip", f, v, layer='pyaw'),
         [(0, 0), (6, 5), (12, 0), (18, -5)], 0, 24, F)
    _cyc(lambda f, v: ctx.roll("CC_Base_Hip", f, v, layer='proll'),
         [(0, -3), (6, -4), (12, 3), (18, 4)], 0, 24, F)
    # forward lean (constant 8deg) + spine counter-yaw 1f lag
    for f in (F, F + 24):
        ctx.pitch("CC_Base_Spine02", f, 8.0, layer='lean')
        ctx.pitch("CC_Base_Spine01", f, 4.0, layer='lean')
    _cyc(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='syaw'),
         [(1, 0), (7, -4), (13, 0), (19, 4)], 0, 24, F)
    # arms: 90deg elbows, drive 35deg opposite legs, shoulders 4deg
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
         [(0, 42), (6, 5), (12, -30), (18, 5)], 0, 24, F)
    _cyc(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
         [(0, -28), (6, 5), (12, 42), (18, 5)], 0, 24, F)
    for s in ('L', 'R'):
        for f in (F, F + 24):
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'y', _HANG[s][1], B)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'z',
                              _HANG[s][2] * 0.62, B)  # arms in closer for pump
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'x', 92.0, B)  # 90deg
        _cyc(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='clav'),
             [(0, 2), (12, -2)] if s == 'R' else [(0, -2), (12, 2)], 0, 24, F)
        # soft fists
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 1.0), (3, 0.85)):
                for f in (F, F + 24):
                    ctx.finger_curl(s, fng, j, f, 55.0 * ja, layer=B)
        for f in (F, F + 24):
            ctx.finger_curl(s, "Thumb", 2, f, 20.0, layer=B)
    # head: small residual bounce, gaze locked forward
    _cyc(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='hstab'),
         [(0, 1.0), (2, 1.6), (6, 0.4), (14, 1.6), (18, 0.4)], 0, 24, F)


# ===========================================================================
# TURN LEFT / RIGHT — one-shots, hip carries yaw, gaze leads, idle-compatible
# ===========================================================================
def _turn(ctx, sign, step_f):
    """sign +1 = turn to character's LEFT (yaw+). step_f = frame the lead
    foot steps out. Gaze leads, body is step-driven, ends idle-compatible
    but facing the new direction (hip yawed 90*sign)."""
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.0, amp=0.4, phase=0.2)
    _both_hang(ctx, [F])
    lead = 'L' if sign > 0 else 'R'      # inside foot steps out first
    trail = 'R' if sign > 0 else 'L'
    # eyes saccade to the new heading at f0 (lead the whole chain)
    motion.gaze_to(ctx, F + 0, 0.5 * sign, 0.0)
    motion.gaze_to(ctx, E - 6, 0.0, 0.0, from_dx=0.5 * sign)  # settle center
    # head leads the body: arrives ahead of the hips (f2-8), then holds w/ body
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (2, 8 * sign), (8, 22 * sign), (16, 10 * sign),
            (22, 2 * sign), (28, 0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='head'),
        F, [(0, 0), (4, 5 * sign), (16, 4 * sign), (24, 0)])
    # hips carry the 90deg turn (step-driven ramp), 2deg overshoot + settle
    _ev(lambda f, v: ctx.yaw("CC_Base_Hip", f, v, layer='turn'),
        F, [(0, 0), (step_f, 12 * sign), (14, 55 * sign), (22, 92 * sign),
            (26, 90 * sign), (30, 90 * sign)])
    # lead foot steps out + pivots (lift-plant), trail foot pivots through
    _ev(lambda f, v, s=lead: ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f, 'x',
        v, layer=B), F, [(0, 0), (step_f, 24), (step_f + 6, 6), (22, 0), (30, 0)])
    _ev(lambda f, v, s=lead: ctx.key_bone_axis(f"CC_Base_{s}_Calf", f, 'x',
        v, layer=B), F, [(0, 0), (step_f, -34), (step_f + 6, -10), (22, 0), (30, 0)])
    _ev(lambda f, v, s=lead: ctx.key_bone_axis(f"CC_Base_{s}_Foot", f, 'x',
        v, layer=B), F, [(0, 0), (step_f, 18), (step_f + 6, 0), (22, 0), (30, 0)])
    _ev(lambda f, v, s=trail: ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f, 'x',
        v, layer=B), F, [(0, 0), (14, -8), (18, 20), (22, 4), (30, 0)])
    _ev(lambda f, v, s=trail: ctx.key_bone_axis(f"CC_Base_{s}_Calf", f, 'x',
        v, layer=B), F, [(0, 0), (16, -30), (20, -8), (30, 0)])
    # weight passes L->R->balanced via hip lateral
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
        layer='wt'), F, [(0, 0), (step_f + 2, 2.0 * sign), (16, -1.5 * sign),
                         (24, 0.4 * sign), (30, 0)])
    # arms counter-swing naturally with the turn, back to hang by the settle
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (12, 7.5 + 14 * sign), (24, 7.5), (30, 7.5)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
        F, [(0, 8.0), (12, 8.0 - 14 * sign), (24, 8.0), (30, 8.0)])
    _stand_legs(ctx, [E])
    _both_hang(ctx, [E])


@clip("turn_left", "locomotion", 1.0, loop=False, framing='body',
      still_frame=0.6,
      description="90deg left turn, gaze-led (eyes f0, head arrives before "
                  "body), L foot steps out f5 + pivots, R foot pivots "
                  "through, hips carry the yaw to +90 by f22 w/ 2deg "
                  "overshoot-settle, arms counter-swing. Ends idle-compatible "
                  "facing the new heading.")
def turn_left(ctx):
    _turn(ctx, +1, step_f=5)


@clip("turn_right", "locomotion", 1.0, loop=False, framing='body',
      still_frame=0.6,
      description="90deg right turn — mirror of turn_left with fresh timing "
                  "(step at f6 not f5), not byte-mirrored. Gaze leads, "
                  "step-driven, idle-compatible exit facing new heading.")
def turn_right(ctx):
    _turn(ctx, -1, step_f=6)


# ===========================================================================
# STEP BACK — one-shot, unload first, gaze holds target
# ===========================================================================
@clip("step_back", "locomotion", 1.0, loop=False, framing='body',
      still_frame=0.5,
      description="Weight rocks back over heels f0-4 (anticipation — cannot "
                  "step back without unloading), R foot steps back f4-12, L "
                  "follows to close f12-20, arms rise 2deg out for balance "
                  "then settle, head STAYS on the forward target (counter the "
                  "retreating body). Settles idle-compatible f20-30.")
def step_back(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.2, amp=0.4, phase=0.5)
    _both_hang(ctx, [F, E])
    _stand_legs(ctx, [F, E])
    # unload: weight rocks back over the heels (hip back + slight down), lean
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
        layer='wt'), F, [(0, 0), (4, 3.0), (12, 2.0), (20, 0.5), (30, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='lean'),
        F, [(0, 0), (4, -2.0), (14, -1.0), (30, 0)])   # brace back a touch
    # R foot steps back (thigh back = -x, lift-plant), then L closes
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Thigh", f, 'x', v, B),
        F, [(0, 0), (4, 2), (8, -22), (12, -10), (20, 0), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Calf", f, 'x', v, B),
        F, [(0, 0), (8, -30), (12, -6), (20, 0), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Foot", f, 'x', v, B),
        F, [(0, 0), (8, 16), (12, 0), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Thigh", f, 'x', v, B),
        F, [(0, 0), (12, 2), (16, -20), (20, -8), (26, 0), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Calf", f, 'x', v, B),
        F, [(0, 0), (16, -28), (20, -6), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Foot", f, 'x', v, B),
        F, [(0, 0), (16, 14), (20, 0), (30, 0)])
    # arms rise 2deg outward for balance, then settle
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='bal'),
            F, [(0, 0), (10, 2.0), (18, 2.0), (28, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
            f, 'z', v, B),
            F, [(0, _HANG[s][2]), (10, _HANG[s][2] * 0.9),
                (20, _HANG[s][2] * 0.9), (30, _HANG[s][2])])
    # head HOLDS the forward target: counter-pitch as the torso rocks back
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='hold'),
        F, [(0, 0), (5, 2.0), (14, 1.2), (24, 0.2), (30, 0)])
    motion.gaze_to(ctx, F + 2, 0.0, -0.06)   # eyes stay down-forward on target
    motion.gaze_to(ctx, E - 4, 0.0, 0.0, from_dy=-0.06)


# ===========================================================================
# LEAN LEFT / RIGHT — one-shot, hip jut IS the pose, holdable end
# ===========================================================================
def _lean(ctx, sign, jut, timing):
    """sign +1 = lean onto the character's LEFT leg (hip juts +x). Hip jut is
    the pose; shoulder line counter-tilts so the head stays ~level (counters
    70%). Ends HELD in the lean (holdable). timing = frame the lean peaks."""
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.4, amp=0.6, phase=0.3)
    _both_hang(ctx, [F])
    _stand_legs(ctx, [F])
    tp = timing
    # weight pours onto the support leg: hip juts sideways (+ down a touch)
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, -abs(v) * 0.1),
        layer='jut'),
        F, [(0, 0), (tp - 4, jut * sign * 1.08), (tp, jut * sign),
            (E - F, jut * sign)])   # 1 overshoot bounce then hold
    # planted-feet counter-rotation so the support foot doesn't skate
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
            'z', v, layer='jut'),
            F, [(0, 0), (tp, -K_LAT * jut * sign), (E - F, -K_LAT * jut * sign)])
    # unloaded foot goes light — heel lifts ~1cm (foot plantarflex a touch)
    light = 'R' if sign > 0 else 'L'
    _ev(lambda f, v, s=light: ctx.key_bone_axis(f"CC_Base_{s}_Foot", f, 'x',
        v, layer='light'), F, [(0, 0), (tp, -8), (E - F, -8)])
    _ev(lambda f, v, s=light: ctx.key_bone_axis(f"CC_Base_{s}_Calf", f, 'x',
        v, layer='light'), F, [(0, 0), (tp, -6), (E - F, -6)])
    # spine arcs, shoulders counter-tilt so the head only follows ~30%
    _ev(lambda f, v: ctx.roll("CC_Base_Spine01", f, v, layer='arc'),
        F, [(0, 0), (tp, -3.4 * sign), (E - F, -3.4 * sign)])
    _ev(lambda f, v: ctx.roll("CC_Base_Spine02", f, v, layer='arc'),
        F, [(0, 0), (tp, -2.6 * sign), (E - F, -2.6 * sign)])
    _ev(lambda f, v: ctx.roll("CC_Base_NeckTwist01", f, v, layer='arc'),
        F, [(0, 0), (tp, 1.4 * sign), (E - F, 1.4 * sign)])
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='arc'),
        F, [(0, 0), (tp, 1.6 * sign), (E - F, 1.6 * sign)])  # ~30% of the lean
    # trailing (right, when leaning left) arm gains a soft swing-space bend
    swing = 'R' if sign > 0 else 'L'
    _ev(lambda f, v, s=swing: ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f,
        'x', v, B),
        F, [(0, _HANG[swing][3]), (tp, _HANG[swing][3] + 12),
            (E - F, _HANG[swing][3] + 12)])
    _both_hang(ctx, [E], layer='hangE')  # keep the other arm alive at hang
    # continuous micro-drift through the HOLD (no fade — a held pose stays
    # alive, not frozen): head roll + a slow forearm sway on the free arm
    motion.loop_noise(ctx, lambda f, v: ctx.roll("CC_Base_Head", f, v,
                      layer='drift'), amp=0.6, cycles=(1, 2, 3), step=5)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis(
        f"CC_Base_{swing}_Forearm", f, 'x', v, layer='hlife'), amp=0.8,
        cycles=(1, 2), step=6)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_loc_world("Hip", f,
                      (v, 0.0, 0.0), layer='jdrift'), amp=0.35,
                      cycles=(1, 2), step=6)
    motion.finger_relax(ctx, amp_deg=1.2, period=6.0)


@clip("lean_left", "locomotion", 1.2, loop=False, framing='body',
      still_frame=0.85,
      description="Weight pours onto the LEFT leg f0-14, left hip juts 3cm "
                  "(the hip jut IS the pose), right foot goes light (heel "
                  "lifts), shoulder line counter-tilts so the head stays "
                  "near-level (~70% counter). Right arm soft swing-bend. 1 "
                  "overshoot bounce; holdable end pose.")
def lean_left(ctx):
    _lean(ctx, +1, jut=3.0, timing=14)


@clip("lean_right", "locomotion", 1.2, loop=False, framing='body',
      still_frame=0.85,
      description="Mirror of lean_left with fresh timing (peak f16) and 10% "
                  "less hip jut (2.7cm — this avatar favours its left lean); "
                  "same counter-tilt rules. Not byte-mirrored.")
def lean_right(ctx):
    _lean(ctx, -1, jut=2.7, timing=16)


# ===========================================================================
# LOOK AROUND (full body) — one-shot, gaze->head->shoulders->torso chain
# ===========================================================================
@clip("look_around", "locomotion", 4.0, loop=False, framing='body',
      still_frame=0.5,
      description="3 targets (left, hard-right, front). Per target chain: "
                  "eyes(2f)->head(+3f)->shoulders(+2f)->torso. Hard-right "
                  "look adds a right-foot adjust step at f60 (torso >25deg "
                  "needs foot support). Dwells 0.8-1.4s, blink on each "
                  "departure. Ends front, idle-compatible.")
def look_around(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.3, amp=0.7, phase=0.1)
    _both_hang(ctx, [F, E])
    _stand_legs(ctx, [F, E])
    # --- target 1: LEFT (moderate, no torso/foot) f18 ---
    motion.add_blink(ctx, F + 14, r_offset=1)
    motion.gaze_to(ctx, F + 18, 0.45, 0.05)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(0, 0), (21, 0), (33, 15), (60, 14)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(0, 0), (23, 0), (36, 6), (60, 5.6)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(0, 0), (38, 0), (50, 4.0), (66, 3.6)])   # shoulders follow left
    # --- target 2: HARD RIGHT f70 (torso >25deg -> right foot adjust f60...
    # here the step supports the big turn as the torso arrives) ---
    motion.add_blink(ctx, F + 64, r_offset=1)
    motion.gaze_to(ctx, F + 70, -0.6, -0.03, from_dx=0.45, from_dy=0.05)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(74, 12), (86, -20), (120, -18.5), (150, -19)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(76, 5), (88, -7), (150, -6.6)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(66, 3.6), (80, 0), (92, -12), (150, -11.4)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine01", f, v, layer='torso'),
        F, [(68, 0), (94, -6), (150, -5.6)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Hip", f, v, layer='torso'),
        F, [(70, 0), (96, -5), (150, -4.6)])   # pelvis joins the big turn
    # right-foot adjust step supporting the >25deg turn (f84-98)
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Thigh", f, 'x', v, B),
        F, [(0, 0), (84, 0), (90, 16), (98, 4), (150, 4)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Calf", f, 'x', v, B),
        F, [(0, 0), (86, -22), (94, -8), (150, -8)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Foot", f, 'x', v, B),
        F, [(0, 0), (88, 14), (98, 2), (150, 2)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
        layer='wt'), F, [(0, 0), (92, -2.0), (150, -1.6)])
    # --- target 3: FRONT settle f150 (everything unwinds to neutral) ---
    motion.add_blink(ctx, F + 146, r_offset=1)
    motion.gaze_to(ctx, F + 150, 0.0, 0.0, from_dx=-0.6, from_dy=-0.03)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(150, -19), (164, 1.5), (176, -0.3), (E - F, 0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(150, -6.6), (168, 0.4), (E - F, 0)])
    # torso + pelvis unwind from their held target-2 values to neutral
    for bone, held in (("CC_Base_Spine02", -11.4), ("CC_Base_Spine01", -5.6),
                       ("CC_Base_Hip", -4.6)):
        _ev(lambda f, v, b=bone: ctx.yaw(b, f, v, layer='torso'),
            F, [(152, held), (172, 0.6), (E - F, 0)])
    # unwind the foot adjust from its held values
    for bn, held in (("Thigh", 4.0), ("Calf", -8.0), ("Foot", 2.0)):
        _ev(lambda f, v, b=bn: ctx.key_bone_axis(f"CC_Base_R_{b}", f, 'x', v,
            B), F, [(152, held), (178, 0), (E - F, 0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
        layer='wt'), F, [(152, -1.6), (178, 0), (E - F, 0)])
    motion.head_micro_sway(ctx, amp_deg=0.4)
    motion.finger_relax(ctx, amp_deg=1.3, period=7.0)


# ===========================================================================
# SEATED CHAIN — sit_down -> sit_idle <-> stand_up (shared _seated_pose)
# ===========================================================================
# seated per-channel targets (must match _seated_pose exactly for the pose
# contract: sit_down end == sit_idle f0; stand_up start == sit_idle f0)
_ST_SP1, _ST_SP2, _ST_NECK, _ST_HEAD = 3.0, 2.2, -1.5, -1.0
_ST_ARM = SEAT_ARM   # sit_down/stand_up arm targets == the seated hold pose


@clip("sit_down", "locomotion", 1.5, loop=False, framing='body',
      still_frame=0.5,
      description="Stand->seat. Hips reach BACK first f0-6 (finding the "
                  "seat), knees bend, ECCENTRIC descent f6-20 (decelerating "
                  "into contact), torso counter-leans forward (nose over "
                  "toes), soft 3f contact compression f20-23, then re-stacks "
                  "to the sit_idle posture f24-45. End matches sit_idle f0.")
def sit_down(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 45f
    motion.breathing(ctx, period=4.0, amp=0.4, phase=0.6)
    _both_hang(ctx, [F])
    _stand_legs(ctx, [F])
    # hip: reach back (y+) first, THEN descend (z-), decelerating into contact
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
        layer='hy'), F, [(0, 0), (6, 12), (16, 18), (23, 18), (45, 18)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
        layer='hz'), F, [(0, 0), (6, -8), (16, -38), (20, -46), (23, -47),
                         (26, -44.5), (45, -45)])   # 3f compression past seat
    # legs fold: thigh up, calf tucks, foot dorsiflexes to stay flat
    for s in ('L', 'R'):
        a = 1.0 if s == 'L' else 0.97
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
            'x', v, B), F, [(0, 0), (6, 30 * a), (16, 82 * a), (23, 95 * a),
                            (26, 92 * a), (45, 92 * a)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Calf", f,
            'x', v, B), F, [(0, 0), (6, -34 * a), (16, -92 * a),
                            (23, -100 * a), (26, -98 * a), (45, -98 * a)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
            'x', v, B), F, [(0, 0), (10, 6), (20, 12), (45, 12)])
    # torso counter-leans forward (balance) then re-stacks upright to the slump
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, B),
        F, [(0, 0), (12, 14), (20, 15), (28, 5), (36, _ST_SP2), (45, _ST_SP2)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, B),
        F, [(0, 0), (12, 9), (20, 10), (28, 4), (36, _ST_SP1), (45, _ST_SP1)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, B),
        F, [(0, 0), (16, 4), (28, 0), (40, _ST_NECK), (45, _ST_NECK)])  # head up (look ahead) then level
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, B),
        F, [(0, 0), (16, -3), (28, -1), (40, _ST_HEAD), (45, _ST_HEAD)])
    # arms: hands brace toward thighs during descent, settle onto thighs
    for s in ('L', 'R'):
        ua, fa = _ST_ARM[s]
        for ax, i in (('x', 0), ('y', 1), ('z', 2)):
            _ev(lambda f, v, ss=s, a=ax: ctx.key_bone_axis(
                f"CC_Base_{ss}_Upperarm", f, a, v, B),
                F, [(0, _HANG[s][{'x':0,'y':1,'z':2}[ax]]), (12, ua[i] * 0.7),
                    (26, ua[i]), (45, ua[i])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm", f,
            'x', v, B), F, [(0, _HANG[s][3]), (12, fa[0] * 0.8), (26, fa[0]),
                            (45, fa[0])])
        _hang_fingers(ctx, s, [F])
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
                ctx.finger_curl(s, fng, j, F + 26, (a + 6.0) * ja, B)
                ctx.finger_curl(s, fng, j, E, (a + 6.0) * ja, B)


@clip("sit_idle", "locomotion", 10.0, loop=True, framing='body',
      still_frame=0.5,
      description="Seated loop, hands on thighs, soft C-curve spine. Weight "
                  "shift on the sit-bones f150 (lateral 1cm, 20f, pelvis "
                  "roll). Right foot taps 3x f100 (heel-led, irregular 7,9f). "
                  "Fingers drift on thighs f200. One posture re-stack f250 "
                  "(spine +2deg then relaxes). Breathing in shoulders. "
                  "Seam-clean.")
def sit_idle(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 300f
    # breathing reads CLEARLY in the shoulders/chest (chair carries the weight)
    motion.breathing(ctx, period=4.3, amp=1.15, phase=0.2, chest=1.5,
                     shoulders=1.4, head=1.4)
    _seated_pose(ctx, [F, E])
    # sit-bone weight shift f150 (lateral 1cm via hip x + pelvis roll)
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
        layer='ws'), F, [(0, 0), (150, 0), (162, 1.0), (185, 0.9),
                         (205, 0.0), (300, 0.0)])
    _ev(lambda f, v: ctx.roll("CC_Base_Spine01", f, v, layer='ws'),
        F, [(0, 0), (152, 0), (165, -1.6), (188, -1.4), (208, 0), (300, 0)])
    _ev(lambda f, v: ctx.clavicle_raise('R', f, v, layer='ws'),
        F, [(0, 0), (155, 0), (170, -0.8), (200, 0), (300, 0)])
    # R foot taps 3x at f100 (heel-led, irregular spacing 7,9f) + a knee lift
    # so the tap reads at body framing
    for tf in (100, 107, 116):
        _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Foot", f, 'x', v,
            layer='tap'),
            F + tf, [(-2, 0.0), (0, 16.0), (3, -3.0), (5, 0.0)])
        _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Calf", f, 'x', v,
            layer='tap'),
            F + tf, [(-2, 0.0), (0, 6.0), (5, 0.0)])
    # a relaxed shoulder roll + hand lift-and-resettle around f215 (fills the
    # late quiet stretch; irregular vs the f150 shift)
    _ev(lambda f, v: ctx.clavicle_raise('L', f, v, layer='ev'),
        F, [(0, 0), (210, 0), (217, 1.4), (225, -0.5), (234, 0)])
    for ax, amp in (('x', 26.0), ('z', -8.0)):
        _ev(lambda f, v, a=ax: ctx.key_bone_axis("CC_Base_R_Forearm", f, a,
            v, layer='handlift'),
            F, [(0, 0), (212, 0), (222, amp * 0.5), (230, amp), (244, 0)])
    # fingers drift on the thighs f200 (soft re-settle ripple, R hand)
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        _ev(lambda f, v, fn=fng: ctx.finger_curl('R', fn, 2, f, v,
            layer='fdrift'),
            F + 200 + i * 2, [(0, 0.0), (7, 5.0), (13, 4.0), (24, 0.0)])
    # posture re-stack f250: spine straightens 2deg then relaxes back
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='restack'),
        F, [(0, 0), (248, 0), (258, -2.0), (272, -1.8), (288, 0), (300, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='restack'),
        F, [(0, 0), (250, 0), (260, -1.0), (290, 0), (300, 0)])
    # subtle seated head look-away around f60 (breaks the early quiet stretch)
    motion.gaze_to(ctx, F + 58, -0.16, 0.02)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(0, 0), (60, 0), (72, -4.0), (110, -3.6), (124, 0.3), (134, 0)])
    motion.gaze_to(ctx, F + 120, 0.0, 0.0, from_dx=-0.16)
    # continuous never-still life (matched to the shipped standing idles)
    motion.finger_relax(ctx, amp_deg=1.5, period=8.0)
    motion.head_micro_sway(ctx, amp_deg=0.55)
    motion.loop_noise(ctx, lambda f, v: ctx.roll("CC_Base_Spine02", f, v,
                      layer='sway'), amp=0.5, cycles=(2, 3), step=5)
    # (no continuous hip-lateral drift here: sit_down/stand_up meet sit_idle f0
    # at hip-x=0, so the seated weight-life stays in the spine/shoulders above)
    # resting hands micro-drift on the thighs (forearm sway, decorrelated)
    for s in ('L', 'R'):
        motion.loop_noise(ctx, lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Forearm", f, 'x', v, layer='armdrift'),
            amp=0.7, cycles=(1, 2, 3), step=6)


@clip("stand_up", "locomotion", 1.5, loop=False, framing='body',
      still_frame=0.55,
      description="Seat->stand. f0-8 weight forward (nose over toes), hands "
                  "press thighs, spine flexes fwd 15deg + feet pull back. "
                  "f8-24 legs drive up, arms swing back-to-front for "
                  "momentum, spine UNROLLS BOTTOM-UP (pelvis->lumbar->chest->"
                  "head). 5% overshoot past vertical f28, settle f28-45 into "
                  "an idle-compatible stance. Starts on sit_idle f0.")
def stand_up(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 45f
    motion.breathing(ctx, period=4.0, amp=0.4, phase=0.8)
    _seated_pose(ctx, [F], hip=False)            # start seated; hip on hz/hy
    # weight forward first (torso pitches fwd, nose over toes), then rise
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, B),
        F, [(0, _ST_SP2), (8, 17), (16, 14), (24, -2), (30, -3), (38, 0.5),
            (45, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, B),
        F, [(0, _ST_SP1), (8, 12), (18, 6), (26, -1.5), (32, -2), (45, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, B),
        F, [(0, _ST_NECK), (10, 4), (22, 2), (34, -1), (45, 0)])   # head lags (unrolls last)
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, B),
        F, [(0, _ST_HEAD), (10, 5), (24, 3), (36, -1.2), (45, 0)])
    # hip rises up+forward (pelvis leads the unroll), 5% overshoot high
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
        layer='hz'), F, [(0, -45), (8, -44), (18, -14), (26, 0.8), (30, 1.0),
                         (38, 0), (45, 0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
        layer='hy'), F, [(0, 18), (6, 20), (16, 8), (26, 0), (45, 0)])
    # legs extend (thigh/calf unfold), feet pull back 5cm early
    for s in ('L', 'R'):
        a = 1.0 if s == 'L' else 0.97
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
            'x', v, B), F, [(0, 92 * a), (8, 96 * a), (18, 40), (26, -2),
                            (32, 0), (45, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Calf", f,
            'x', v, B), F, [(0, -98 * a), (8, -104 * a), (18, -44), (26, 3),
                            (32, 0), (45, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
            'x', v, B), F, [(0, 12), (6, 18), (18, 6), (28, 0), (45, 0)])
    # arms swing back-to-front for momentum, leave thighs f18, settle to hang
    for s in ('L', 'R'):
        ua, fa = _ST_ARM[s]
        for ax, i in (('x', 0), ('y', 1), ('z', 2)):
            hng = _HANG[s][{'x': 0, 'y': 1, 'z': 2}[ax]]
            _ev(lambda f, v, ss=s, a=ax: ctx.key_bone_axis(
                f"CC_Base_{ss}_Upperarm", f, a, v, B),
                F, [(0, ua[i]), (10, ua[i]), (20, (ua[i] + hng) * 0.5),
                    (30, hng), (45, hng)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm", f,
            'x', v, B), F, [(0, fa[0]), (10, fa[0]), (22, 30), (32, _HANG[s][3]),
                            (45, _HANG[s][3])])
        # forearm z returns to the hang wrist angle (idle-compatible exit)
        ctx.key_bone_axis(f"CC_Base_{s}_Forearm", F + 32, 'z', _HANG[s][4], B)
        ctx.key_bone_axis(f"CC_Base_{s}_Forearm", E, 'z', _HANG[s][4], B)
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
                ctx.finger_curl(s, fng, j, F, (a + 6.0) * ja, B)
        _hang_fingers(ctx, s, [E])


# ===========================================================================
# STRETCH — one-shot, arms overhead, arch, peak tremble, exhale-collapse
# ===========================================================================
@clip("stretch", "locomotion", 3.5, loop=False, framing='body',
      still_frame=0.4,
      description="Arms sweep overhead f0-20, spine extends into an 8deg "
                  "back-arch, head drops back, heels rise. PEAK HOLD f20-50 "
                  "w/ isometric tremble (0.3deg) + eyes squeezed. RELEASE "
                  "f50-75 is the payoff: big exhale (breathing_deep), "
                  "shoulders DROP 3deg below neutral, arms fall w/ drag+"
                  "bounce, spine settles fwd past neutral then back. Ends "
                  "more relaxed than the start.")
def stretch(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 105f
    motion.breathing(ctx, period=6.0, amp=0.5, phase=0.0, chest=1.3)
    _both_hang(ctx, [F])
    _stand_legs(ctx, [F])
    # arms sweep up overhead (celebrate-V geometry, straighter), L 1f late
    for s, sy, lag in (('L', 1.0, 0), ('R', -1.0, 1)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
            f, 'x', v, B),
            F, [(0, _HANG[s][0]), (20 + lag, 120), (50, 118), (62, 40),
                (78, 18), (90, _HANG[s][0] - 4), (E - F, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (20 + lag, -12 * sy), (50, -12 * sy),
                (62, _HANG[s][1]), (E - F, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (20 + lag, _HANG[s][2] * 0.32), (50,
                _HANG[s][2] * 0.32), (66, _HANG[s][2]), (E - F, _HANG[s][2])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm", f,
            'x', v, B), F, [(0, _HANG[s][3]), (20 + lag, 14), (50, 12),
                            (60, 40), (74, 20), (E - F, _HANG[s][3])])
        for fng, a in _FING:   # fingers spread (interlace-imply) up top
            _ev(lambda f, v, ss=s, ff=fng: ctx.finger_curl(ss, ff, 1, f, v, B),
                F, [(0, a * _HANG[s][5]), (22, -4), (50, -4), (66, a),
                    (E - F, a * _HANG[s][5])])
            for j, ja in ((2, 0.85), (3, 0.6)):
                ctx.finger_curl(s, fng, j, F, a * ja * _HANG[s][5], B)
                ctx.finger_curl(s, fng, j, E, a * ja * _HANG[s][5], B)
    # spine extends into a back arch (extension = -pitch), collapse fwd on
    # release past neutral, then settle
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, B),
        F, [(0, 0), (20, -6), (50, -6), (62, 4), (72, 2), (E - F, 0.5)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, B),
        F, [(0, 0), (20, -3), (50, -3), (62, 3), (E - F, 0.8)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, B),
        F, [(0, 0), (20, -8), (50, -8), (60, 4), (72, 2), (E - F, 1.5)])
    # heels rise at f18 (foot plantarflex), drop at f62 (release)
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
            'x', v, layer='heel'),
            F, [(0, 0), (18, -12), (50, -12), (62, 2), (70, 0), (E - F, 0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
        layer='heelz'), F, [(0, 0), (18, 1.5), (50, 1.4), (62, -0.4),
                            (70, 0), (E - F, 0)])
    # shoulders DROP 3deg below neutral on the release (the payoff)
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='shdrop'),
            F, [(0, 0), (50, 0), (62, -3.0), (78, -2.4), (E - F, -1.2)])
    # peak isometric tremble f20-50 (tiny, high-freq), eyes squeezed
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm",
        f, 'z', v, layer='tremble'), start=F + 22, end=F + 50, amp=0.35,
        cycles=(5, 8, 11), step=2, fade=0.1)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm",
        f, 'z', v, layer='tremble'), start=F + 22, end=F + 50, amp=0.32,
        cycles=(6, 9, 12), step=2, fade=0.1)
    _ev(lambda f, v: ctx.key_shape_lr("Eye_Blink_{S}", f, v, layer='squeeze',
        r_offset=1, r_scale=0.96),
        F, [(0, 0.0), (20, 0.45), (50, 0.42), (60, 0.0)])
    # two loose arm shake-out swings in the tail (pendulum decay)
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm", f,
            'z', v, layer='shake'),
            F, [(80, 0), (86, 8), (92, -6), (98, 3), (E - F, 0)])


# ===========================================================================
# HANDS IN POCKETS — one-shot, staggered, thumbs out, holdable
# ===========================================================================
@clip("hands_in_pockets", "locomotion", 2.0, loop=False, framing='body',
      still_frame=0.85,
      description="Hands slide into front pockets: RIGHT first f0-12, LEFT "
                  "f8-20 (staggered), THUMBS STAY OUT hooked on the pocket "
                  "edge (the readable detail), elbows settle back, shoulders "
                  "drop 2deg, weight rocks back, spine eases 1deg. Holdable "
                  "end pose (pairs w/ a pocket exit). Wardrobe-dependent "
                  "(assumes pants geometry).")
def hands_in_pockets(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 60f
    D = E - F
    motion.breathing(ctx, period=4.4, amp=0.5, phase=0.35, shoulders=0.6)
    _both_hang(ctx, [F])
    _stand_legs(ctx, [F, E])
    # pocket pose per hand (low-front hip, elbow back). RIGHT leads.
    pocket = {'R': ((20.0, -8.0, -42.0), (46.0, 0.0), 0),
              'L': ((20.0, 8.0, 42.0), (46.0, 0.0), 8)}
    for s, (ua, fa, lag) in pocket.items():
        for ax, i in (('x', 0), ('y', 1), ('z', 2)):
            _ev(lambda f, v, ss=s, a=ax: ctx.key_bone_axis(
                f"CC_Base_{ss}_Upperarm", f, a, v, B),
                F, [(0, _HANG[s][{'x':0,'y':1,'z':2}[ax]]), (lag, _HANG[s][
                    {'x':0,'y':1,'z':2}[ax]]), (lag + 12, ua[i]), (D, ua[i])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm", f,
            'x', v, B), F, [(0, _HANG[s][3]), (lag, _HANG[s][3]),
                            (lag + 12, fa[0]), (D, fa[0])])
        # fingers curl INTO the pocket; THUMB STAYS OUT (extended, low curl)
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 0.9), (3, 0.7)):
                _ev(lambda f, v, ss=s, ff=fng, jj=j: ctx.finger_curl(
                    ss, ff, jj, f, v, B),
                    F, [(0, dict(_FING)[fng] * ja * _HANG[s][5]),
                        (lag + 12, (24.0 + a) * ja), (D, (24.0 + a) * ja)])
        _ev(lambda f, v, ss=s: ctx.finger_curl(ss, "Thumb", 1, f, v, B),
            F, [(0, 3.0), (lag + 12, -8.0), (D, -8.0)])   # thumb hooks OUT
        ctx.finger_curl(s, "Thumb", 2, F, 3.0, B)
        ctx.finger_curl(s, "Thumb", 2, E, 2.0, B)
    # shoulders drop 2deg (relaxed), weight rocks back, spine eases 1deg
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='sh'),
            F, [(0, 0), (16, -2.0), (D, -2.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
        layer='wt'), F, [(0, 0), (18, 1.5), (D, 1.5)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='ease'),
        F, [(0, 0), (18, 1.0), (D, 1.0)])
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='ease'),
        F, [(0, 0), (14, 1.5), (30, -0.5), (D, 0.0)])   # slight easy head tilt
    # continuous micro-life through the held pose (alive, not frozen):
    # relaxed head sway + a tiny shifting weight drift on the hips
    motion.loop_noise(ctx, lambda f, v: ctx.yaw("CC_Base_Head", f, v,
                      layer='hsway'), amp=0.8, cycles=(1, 2, 3), step=5)
    motion.loop_noise(ctx, lambda f, v: ctx.roll("CC_Base_Head", f, v,
                      layer='hsway'), amp=0.5, cycles=(2, 3), step=6)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_loc_world("Hip", f,
                      (v, 0.0, 0.0), layer='wdrift'), amp=0.5,
                      cycles=(1, 2), step=6)


# ===========================================================================
# ADJUST GLASSES — one-shot contact, precision pinch on the bridge
# ===========================================================================
@clip("adjust_glasses", "locomotion", 2.0, loop=False, framing='bust',
      still_frame=0.2,
      description="R hand rises f0-10 (elbow leads), index+thumb form the "
                  "precision pinch DURING the rise (not before/after). Pinch "
                  "lands on the nose bridge f12 (no face clip; glasses asset "
                  "may be absent). Micro push 1cm up-and-in over 3f; head "
                  "tips DOWN 2deg into the push then re-levels. Hand returns "
                  "f20-35 via a LOWER path (never retraces). Blink at the "
                  "push. L arm alive.")
def adjust_glasses(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 60f
    motion.breathing(ctx, period=4.0, amp=0.5, phase=0.5)
    _both_hang(ctx, [F, E])
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm",
        f, 'x', v, layer='life'), amp=0.35, cycles=(1, 2), step=6, fade=0.12)
    # R arm: elbow leads up (upperarm x rises before forearm), pinch to bridge
    # RETURN via a LOWER path -> mid-return upperarm/forearm differ from rise
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (10, 78), (12, 82), (18, 82), (26, 48), (35, 22),
            (44, 7.5)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', v, B),
        F, [(0, 9.0), (12, -20), (18, -20), (30, -2), (44, 9.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', v, B),
        F, [(0, 57.13), (12, 4), (18, 4), (26, 30), (44, 57.13)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, [(0, 11.04), (10, 110), (12, 124), (15, 128), (18, 124),
            (28, 96), (44, 11.04)])   # push 1cm up-in at f15
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
        F, [(0, 3.0), (12, -4), (18, -4), (44, 3.0)])
    # hand curls so the index/thumb pinch meets the bridge (right nose-pad)
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Hand", f, 'x', v, B),
        F, [(0, 0), (12, -25), (18, -25), (30, 0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Hand", f, 'z', v, B),
        F, [(0, 0), (12, -15), (18, -15), (30, 0)])
    # index + thumb pinch forms DURING the rise (f4-12), releases on return
    _ev(lambda f, v: ctx.finger_curl('R', "Index", 1, f, v, B),
        F, [(0, 4.0 * 0.94), (6, 20), (12, 34), (18, 34), (28, 12),
            (40, 4.0 * 0.94)])
    _ev(lambda f, v: ctx.finger_curl('R', "Index", 2, f, v, B),
        F, [(0, 3.4), (6, 20), (12, 38), (18, 38), (28, 10), (40, 3.4)])
    _ev(lambda f, v: ctx.finger_curl('R', "Thumb", 1, f, v, B),
        F, [(0, 3.0), (6, 16), (12, 26), (18, 26), (28, 8), (40, 3.0)])
    ctx.finger_curl('R', "Thumb", 2, F, 3.0, B)
    ctx.finger_curl('R', "Thumb", 2, F + 12, 20.0, B)
    ctx.finger_curl('R', "Thumb", 2, F + 40, 3.0, B)
    for fng, a in (("Mid", 5.5), ("Ring", 7.0), ("Pinky", 8.5)):
        for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f,
                v, B), F, [(0, a * ja * 0.94), (12, (a + 20) * ja),
                           (18, (a + 20) * ja), (40, a * ja * 0.94)])
    # head tips DOWN 2deg into the push (glasses wearers push against a nod),
    # then re-levels
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (12, 0.5), (15, 2.2), (20, 1.0), (30, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='head'),
        F, [(0, 0), (15, 1.0), (30, 0)])
    motion.add_blink(ctx, F + 14, r_offset=1)   # blink on the push


# ===========================================================================
# SCRATCH HEAD — one-shot contact, finger-led scratch, sheepish
# ===========================================================================
@clip("scratch_head", "locomotion", 2.5, loop=False, framing='bust',
      still_frame=0.4,
      description="R hand rises to the back-right of the head f0-14 (elbow "
                  "high, arm wraps, 2cm proud of the scalp). THREE scratch "
                  "oscillations f14-32: FINGER-led (fingers 60%, wrist 30%, "
                  "arm 10%), spacings 6,5,7f. Head tilts 4deg INTO the "
                  "scratch and yields 1deg per stroke. Left shoulder rises "
                  "1deg (counterbalance). Facial hook: sheepish + gaze aside. "
                  "Hand drops w/ drag, head re-levels last.")
def scratch_head(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 75f
    motion.breathing(ctx, period=4.2, amp=0.5, phase=0.3)
    _both_hang(ctx, [F, E])
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm",
        f, 'x', v, layer='life'), amp=0.35, cycles=(1, 2), step=6, fade=0.12)
    # R arm wraps up to the back-right of the head (elbow high, wrist by the
    # ear, fingertips reach the upper crown ~z1.58 proud of the scalp), drop
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (14, 118), (32, 118), (52, 40), (66, 7.5)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', v, B),
        F, [(0, 9.0), (14, -52), (32, -52), (52, -10), (66, 9.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', v, B),
        F, [(0, 57.13), (14, -24), (32, -24), (52, 30), (66, 57.13)])
    # forearm: bent to reach the scalp + the wrist part of the scratch (~30%)
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, [(0, 11.04), (14, 142), (18, 136), (23, 144), (28, 138),
            (32, 142), (52, 11.04)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
        F, [(0, 3.0), (14, -22), (32, -22), (52, 3.0)])
    # hand curls toward the scalp (palm to head) so fingers meet the crown
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Hand", f, 'z', v, B),
        F, [(0, 0), (14, -22), (32, -22), (52, 0)])
    # fingers = 60% of the scratch: flex/extend, spacings 6,5,7f (irregular)
    scratch_fr = [14, 20, 25, 32]
    for fng, a in (("Index", 30.0), ("Mid", 34.0), ("Ring", 32.0),
                   ("Pinky", 28.0)):
        pts = [(0, dict(_FING)[fng] * 0.94), (14, a)]
        for k in range(3):
            c0, c1 = scratch_fr[k], scratch_fr[k + 1]
            pts += [((c0 + c1) // 2, a - 22), (c1, a)]
        pts += [(52, dict(_FING)[fng] * 0.94)]
        for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f,
                v * ja, B), F, pts)
    ctx.finger_curl('R', "Thumb", 2, F, 3.0, B)
    ctx.finger_curl('R', "Thumb", 2, F + 14, 24.0, B)
    ctx.finger_curl('R', "Thumb", 2, F + 52, 3.0, B)
    # head tilts 4deg INTO the scratch (toward the hand = right = -roll... use
    # roll toward RIGHT shoulder = -roll) and yields 1deg per stroke
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (14, -4), (20, -3), (25, -4.2), (32, -3.2), (52, -3.5),
            (66, 0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (14, 3), (32, 2.6), (52, 2.8), (66, 0)])   # away from hand
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (14, 5), (32, 4.6), (66, 0)])
    # left shoulder rises 1deg (sheepish counterbalance)
    _ev(lambda f, v: ctx.clavicle_raise('L', f, v, layer='sh'),
        F, [(0, 0), (16, 1.2), (50, 1.0), (66, 0)])
    # gaze aside (sheepish) — eyes lead, look down-left
    motion.gaze_to(ctx, F + 8, 0.25, -0.2)
    motion.gaze_to(ctx, E - 8, 0.0, 0.0, from_dx=0.25, from_dy=-0.2)


# ===========================================================================
# CHECK WATCH — one-shot, L forearm up, gaze drops AFTER the arm
# ===========================================================================
@clip("check_watch", "locomotion", 2.2, loop=False, framing='bust',
      still_frame=0.4,
      description="L forearm rotates up and IN toward the ribs f0-10 (wrist "
                  "supinates to show the watch), gaze drops to the wrist f4 "
                  "(AFTER the arm starts moving). Head pitches down 8deg. "
                  "READING f14-40: brow micro-knit, eyes make 2 tiny "
                  "fixation shifts. Then arm lowers + gaze returns to front, "
                  "arriving together f40-58. Micro nod at the end (time "
                  "acknowledged).")
def check_watch(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 66f
    motion.breathing(ctx, period=4.2, amp=0.5, phase=0.6)
    _both_hang(ctx, [F, E])
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm",
        f, 'x', v, layer='life'), amp=0.35, cycles=(1, 2), step=6, fade=0.12)
    # L forearm raises across/up toward the ribs, wrist supinates (y) to face
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
        F, [(0, 8.0), (10, 42), (40, 42), (52, 8.0), (58, 8.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'y', v, B),
        F, [(0, -10.0), (10, 40), (40, 40), (52, -10.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'z', v, B),
        F, [(0, -58.0), (10, -34), (40, -34), (52, -58.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'x', v, B),
        F, [(0, 12.0), (10, 104), (34, 106), (40, 104), (52, 12.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'y', v, B),
        F, [(0, 0.0), (10, 40), (40, 40), (52, 0.0)])   # supinate (watch up)
    _hang_fingers(ctx, 'L', [F, E])
    for fng, a in _FING:   # soft cradle curl while reading
        for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
            ctx.finger_curl('L', fng, j, F + 12, (a + 8) * ja, B)
            ctx.finger_curl('L', fng, j, F + 40, (a + 8) * ja, B)
    # head pitches down 8deg to the wrist; gaze DROPS at f4 (after the arm)
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (10, 8), (40, 7.5), (52, 0), (58, 0.8), (62, 0)])  # end micro-nod
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='head'),
        F, [(0, 0), (10, 4), (40, 3.8), (52, 0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (10, 6), (40, 5.6), (52, 0)])   # down-and-left to the wrist
    motion.gaze_to(ctx, F + 4, 0.18, -0.4)          # gaze drops AFTER arm start
    # 2 tiny reading fixation shifts f18-34
    for f0, dx in ((18, 0.06), (30, -0.05)):
        for s in ('L', 'R'):
            _ev(lambda f, v, ss=s: ctx.key_shape(f"Eye_{ss}_Look_L", f,
                max(0.0, v), layer='read'),
                F + f0, [(0, 0.18 + (dx if dx > 0 else 0)), (2, 0.18 + dx),
                         (10, 0.18 + dx * 0.6), (14, 0.18)])
    motion.gaze_to(ctx, E - 8, 0.0, 0.0, from_dx=0.18, from_dy=-0.4)
    # brow micro-knit (reading) — cross-mesh fan-out handled by key_shape
    _ev(lambda f, v: ctx.key_shape("Brow_Compress_L", f, v, layer='brow'),
        F, [(0, 0), (16, 0.15), (38, 0.13), (46, 0)])
    _ev(lambda f, v: ctx.key_shape("Brow_Compress_R", f, v, layer='brow'),
        F, [(0, 0), (17, 0.14), (38, 0.12), (46, 0)])


# ===========================================================================
# CELEBRATE BIG — one-shot, jump + fist pumps + recovery breath
# ===========================================================================
@clip("celebrate_big", "locomotion", 3.0, loop=False, framing='body',
      still_frame=0.12,
      description="Full-body celebrate WITH a jump: crouch f0-6 (spine "
                  "12deg, arms cocked), launch f6-10 (full extension "
                  "airborne, arms punch overhead, head back), LAND f14-18 w/ "
                  "2-stage knee absorb (impact + rebound), then two fist "
                  "pumps f20-45 (decaying, off-mirror), weight settles "
                  "through a bounce. big_smile + breathing_excited hooks. "
                  "Recovery breath visible f60-90.")
def celebrate_big(ctx):
    F, E = ctx.frame_start, ctx.frame_end       # 90f
    _both_hang(ctx, [F])
    _stand_legs(ctx, [F])
    # hip vertical: crouch (-12) -> launch (+20 airborne apex f10) -> land
    # absorb (-12) -> rebound -> settle
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
        layer='hop'), F, [(0, 0), (6, -12), (10, 20), (14, 8), (16, -12),
                          (20, -4), (24, 2), (30, 0), (E - F, 0)])
    # legs: crouch bend, extend at launch, tuck in air, absorb on land
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Thigh", f,
            'x', v, layer='legs'),
            F, [(0, 0), (6, 34), (10, 6), (13, 24), (16, 42), (22, 8),
                (30, 0), (E - F, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Calf", f,
            'x', v, layer='legs'),
            F, [(0, 0), (6, -40), (10, -6), (13, -30), (16, -50), (22, -10),
                (30, 0), (E - F, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
            'x', v, layer='legs'),
            F, [(0, 0), (6, 8), (10, -24), (14, 6), (18, 0), (E - F, 0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_ToeBase", f,
            'x', v, layer='legs'),
            F, [(0, 0), (9, -24), (12, -6), (16, 0), (E - F, 0)])
    # both arms: cock back (antic) then punch overhead into a V, R 1f late +
    # higher (off-mirror), then 2 decaying fist pumps
    for s, sy, lag, hi in (('L', 1.0, 0, 118), ('R', -1.0, 1, 124)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
            f, 'x', v, B),
            F, [(0, _HANG[s][0]), (6, -8), (10 + lag, hi + 6), (16, hi),
                (45, hi), (60, hi * 0.5), (E - F, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (10 + lag, -14 * sy), (45, -14 * sy),
                (E - F, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (6, _HANG[s][2]), (10 + lag, 24 * (1 if
                s == 'R' else -1)), (45, 24 * (1 if s == 'R' else -1)),
                (E - F, _HANG[s][2])])
        # forearm: 2 fist pumps (elbow), decaying + off-phase per side
        p0 = 22 if s == 'R' else 20     # off-mirror pump timing
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
            f, 'x', v, B),
            F, [(0, _HANG[s][3]), (10 + lag, 28), (p0, 12), (p0 + 9, 26),
                (p0 + 17, 16), (45, 22), (E - F, _HANG[s][3])])
        # fists (closed at launch, relax in the tail)
        for fng in ("Index", "Mid", "Ring", "Pinky"):
            for j in (1, 2, 3):
                _ev(lambda f, v, ss=s, ff=fng, jj=j: ctx.finger_curl(
                    ss, ff, jj, f, v, B),
                    F, [(0, dict(_FING)[fng] * 0.94), (10, 95), (45, 95),
                        (58, dict(_FING)[fng] * 0.94)])
        for j in (1, 2, 3):
            ctx.finger_curl(s, "Thumb", j, F + 10, 70, B)
            ctx.finger_curl(s, "Thumb", j, F + 58, 3.0, B)
        _hang_arm(ctx, s, [E])
    # torso: crouch flex, chest opens on launch (extension), head back, settle
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='spine'),
        F, [(0, 0), (6, 12), (10, -9), (16, 6), (22, -6), (30, 0),
            (E - F, 0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0), (6, 4), (10, -8), (16, 5), (22, -4), (30, 0), (E - F, 0)])
    # recovery breath visible f60-90 (deep, in shoulders/chest)
    motion.breathing(ctx, start=F + 58, end=E, period=2.6, amp=1.4,
                     chest=1.4, shoulders=1.3, phase=0.0)
    _ev(lambda f, v: ctx.key_shape_lr("Eye_Blink_{S}", f, v, layer='blink',
        r_offset=1), F, [(14, 0.0), (16, 0.5), (20, 0.0)])   # land blink


# ===========================================================================
# DANCE SMALL — loop, offset groove, hips lead, shoulders opposite
# ===========================================================================
@clip("dance_small", "locomotion", 4.0, loop=True, framing='body',
      still_frame=0.3,
      description="120bpm groove (15f/beat, 8 beats/loop). Weight rocks "
                  "side-to-side on alternate beats (hips LEAD), shoulders "
                  "alternate OPPOSITE the hips, head bobs offset +2f from the "
                  "hip hit (the groove IS the offset). Arms loose at low "
                  "guard, elbows ride the bounce. Bounce is in the knees "
                  "(8deg flex pulse/beat). Beat 6 hip hit 20% bigger. Seam "
                  "matches beat 1.")
def dance_small(ctx):
    F = ctx.frame_start                          # 120f, period 120
    motion.breathing(ctx, period=4.0, amp=0.4, phase=0.5, shoulders=0.5)
    _both_hang(ctx, [F, F + 120])
    # per-beat energy AND timing vary so the groove never metronomes: amplitude
    # accents (beat 1 strong, beat 6 biggest per spec) + a +-2-3f cadence jitter
    # off the strict 15f grid (carry-forward lesson: no motion on a rigid grid).
    # beat 0 stays on the grid so the loop seam is clean.
    BEAT_SC = [1.0, 0.62, 0.82, 0.68, 0.94, 1.22, 0.72, 0.58]  # per-beat accent
    BEAT_PH = [0, 3, -3, 4, -2, 3, -4, 2]        # per-beat frame jitter (swing)

    def _groove(fn, dip, rec, dipf, recf, amps, n, spacing, span=120):
        for b in range(n):
            bf = F + b * spacing + BEAT_PH[b % 8]
            fn(bf + dipf, dip * amps[b])
            fn(bf + recf, rec * amps[b])
        fn(F, dip * amps[0]); fn(F + span, dip * amps[0])   # clean seam

    # The dip lands when the WEIGHT PLANTS (every 2 beats, synced to the lateral
    # rock) not on every beat — a subtle body groove, and it keeps the dominant
    # vertical energy on the 2-beat rhythm instead of a 1-beat metronome pulse.
    PLANT_SC = [1.0, 0.78, 1.15, 0.7]   # 4 weight plants over the loop
    # bounce lives in the KNEES (spec); both knees dip on the plant, R lags 2f
    _groove(lambda f, v: ctx.key_bone_axis("CC_Base_L_Calf", f, 'x', v,
            layer='bounce'), -9, 1, 0, 13, PLANT_SC, 4, 30)
    _groove(lambda f, v: ctx.key_bone_axis("CC_Base_R_Calf", f, 'x', v,
            layer='bounce'), -8, 1, 2, 15,
            [x * 1.08 for x in PLANT_SC], 4, 30)   # R lags L by 2f
    # small hip vertical dip on each weight plant
    _groove(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
            layer='hz'), -2.2, 0.5, 0, 13, PLANT_SC, 4, 30)
    # weight rocks side to side on EVERY beat (+-3cm nominal, hips LEAD). This
    # is the lead groove element and MUST NOT metronome: each beat carries its
    # own amplitude accent (spec 0.7-1.15x, beat 6 the 1.2x emphasis hit) AND an
    # off-grid timing jitter (BEAT_PH, +-4f) so no two swings are identical and
    # no peak lands on the strict 15f grid. Beat 0 stays on the grid at nominal
    # amplitude so the loop seam is value+tangent clean (it's a local extremum ->
    # AUTO_CLAMPED flattens the seam handle regardless of neighbour placement).
    # (predecessor bug: this rode plain _beats = constant amplitude, on the grid;
    # BEAT_SC/BEAT_PH were only wired into the secondary _groove elements.)
    ROCK_SC = [1.0, 0.85, 1.1, 0.78, 1.05, 1.2, 0.92, 0.72]  # beat 6 (idx5)=1.2x

    def _rock(fn, amp, s0):
        fn(F, amp * s0 * ROCK_SC[0])                 # seam: beat 0, on grid
        for b in range(1, 8):
            sgn = s0 if b % 2 == 0 else -s0
            fn(F + b * 15 + BEAT_PH[b], amp * sgn * ROCK_SC[b])
        fn(F + 120, amp * s0 * ROCK_SC[0])           # loop close == beat 0 value

    _rock(lambda f, v: ctx.key_bone_loc_world("Hip", f, (v, 0.0, 0.0),
          layer='hx'), 3.0, +1.0)
    # pelvis roll accompanies the lateral rock (weight tilts the pelvis) — same
    # per-beat accent+jitter so it tracks the rock and doesn't reintroduce an
    # on-grid 15f pulse of its own. Beat-0 sign is -1 (matches the old table).
    _rock(lambda f, v: ctx.roll("CC_Base_Hip", f, v, layer='proll'), 3.0, -1.0)
    # SYNCOPATED pelvis yaw — decoupled from the hip hit: accents land on the
    # '&' offbeats with IRREGULAR spacing and per-accent magnitude (1.5-4.0deg,
    # not a constant-amplitude sine), some beats skipped in energy. Seam keys are
    # 0 with antisymmetric neighbours (f+9=+3.4 / f+111=-3.4) so the wrap tangent
    # is continuous. Strongest accent (f85=-4.0) syncs to the beat-6 region but
    # offset+opposite the hip. (predecessor bug: rode plain _beats = flat sine.)
    for off, deg in [(0, 0.0), (9, 3.4), (23, -1.8), (41, 2.9), (54, -3.6),
                     (71, 1.5), (85, -4.0), (99, 2.6), (111, -3.4), (120, 0.0)]:
        ctx.yaw("CC_Base_Hip", F + off, deg, layer='pyaw')
    # shoulders pop OPPOSITE the hip, alternating shoulder each PLANT (R on
    # plants 0,2 / L on plants 1,3) -> a 2-beat sway accent, not a per-beat pop
    for p in range(4):
        bf = F + p * 30 + BEAT_PH[p]
        s = 'R' if p % 2 == 0 else 'L'
        amp = 4.0 * (1.1 if s == 'L' else 1.0) * PLANT_SC[p]
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='pop'),
            bf, [(-3, 0), (3, amp), (12, -0.6), (22, 0)])
    # head bobs on the plant (offset +2f from the hip hit), 2-beat, jittered amp
    for p in range(4):
        bf = F + p * 30 + BEAT_PH[p]
        _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='bob'),
            bf, [(2, 4.5 * PLANT_SC[p]), (10, -1.2 * PLANT_SC[p]), (18, 0)])
    ctx.pitch("CC_Base_Head", F, 0.0, layer='bob')            # seam=0
    ctx.pitch("CC_Base_Head", F + 120, 0.0, layer='bob')
    _cyc(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='bobroll'),
         [(0, 1.5), (30, -1.5), (60, 1.5), (90, -1.5)], 0, 120, F)  # loose drift
    # arms loose at low guard, elbows RIDE THE BOUNCE (2-beat plant rhythm, 2f
    # drag) — not a per-beat pump (that was a metronome source)
    for s, off in (('L', 0), ('R', 2)):
        for f in (F, F + 120):
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'x', 18.0, B)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'y', _HANG[s][1], B)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'z',
                              _HANG[s][2] * 0.85, B)
        _groove(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
                f, 'x', v, layer='guard'), 42, 30, off, off + 13, PLANT_SC,
                4, 30)
        # a slow continuous arm sway so the arms are never dead between plants
        motion.loop_noise(ctx, lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Forearm", f, 'z', v, layer='armsway'),
            amp=4.0, cycles=(2, 3), step=5)
        _hang_fingers(ctx, s, [F, F + 120])
    # beat 6 hip hit 20% bigger (localized bump, returns before the seam)
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
        layer='b6'), F, [(83, 0), (90, -1.0), (98, 0)])   # extra dip on beat6
    motion.finger_relax(ctx, amp_deg=1.0, period=7.5)
