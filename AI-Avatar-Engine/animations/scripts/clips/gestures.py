"""Gesture clips (Tier 2, owner: body) — 18 one-shots per library_spec.json.

Every gesture is a one-shot with anticipation -> action -> overshoot ->
settle and a return-to-neutral tail so the runtime can crossfade out any
time after the hold. The neutral is the SAME idle-compatible arm hang the
idle clips author (probe-matched to idle_01 f0), so idle->gesture->idle
blends are seamless. A light breathing layer is baked per clip with a
distinct phase.

LAYERING CONTRACT (learned the hard way — layers SUM at flush):
- ALL absolute bone posing (both-arm hang endpoints + the working arm's
  articulation waypoints) goes on ONE layer `B` so each (bone,axis) is a
  single continuous fcurve. Never split an absolute pose across two layers.
- Only genuine ADDITIVE micro-deltas ride separate layers: breathing
  ('breath'), resting-arm micro-life ('life', keyed as a delta on top of
  the hang). Gaze/VOR are shape keys (separate channels, no conflict).
Facial expressions (smile/brow) are HOOKS noted in each description — the
facial layer owns expression shape keys; body bakes head/neck/spine/arm
motion + gaze (eyes lead head). Reach poses are calibrated from a probe
sweep of the arm envelope; contact gestures are probe-verified for
clearance.

Conventions (keying.py): pitch+ down, yaw+ character-left, roll+ toward
LEFT shoulder; clavicle_raise+ lifts; finger_curl+ toward palm.
"""
from anim_framework.clips import clip
from anim_framework import motion

B = 'base'  # the single absolute-pose layer (see contract above)

# side -> (Upperarm x,y,z, Forearm x, Forearm z, finger_scale) idle hang
_HANG = {
    'L': (8.0, -10.0, -58.0, 12.0, -3.0, 1.0),
    'R': (7.5, 9.0, 57.13, 11.04, 3.0, 0.94),
}
_FING = (("Index", 4.0), ("Mid", 5.5), ("Ring", 7.0), ("Pinky", 8.5))


def _ev(fn, f0, pts):
    for off, v in pts:
        fn(f0 + off, v)


def _hang_side(ctx, side, frames, layer=B, fingers=True):
    """Author the idle hang for one arm at each frame in `frames`."""
    ux, uy, uz, fx, fz, csc = _HANG[side]
    for f in frames:
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'x', ux, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'y', uy, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Upperarm", f, 'z', uz, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Forearm", f, 'x', fx, layer=layer)
        ctx.key_bone_axis(f"CC_Base_{side}_Forearm", f, 'z', fz, layer=layer)
        if fingers:
            _hang_fingers(ctx, side, [f], layer=layer)


def _hang_fingers(ctx, side, frames, layer=B):
    csc = _HANG[side][5]
    for f in frames:
        for fng, a in _FING:
            for j, ja in ((1, 1.0), (2, 0.85), (3, 0.6)):
                ctx.finger_curl(side, fng, j, f, a * ja * csc, layer=layer)
        ctx.finger_curl(side, "Thumb", 2, f, 3.0, layer=layer)


def _both_hang(ctx, frames):
    for s in ('L', 'R'):
        _hang_side(ctx, s, frames)


def _rest_life(ctx, side='L', amp=0.35):
    """Additive micro-life on a resting arm (delta on top of the hang)."""
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis(
        f"CC_Base_{side}_Upperarm", f, 'x', v, layer='life'),
        amp=amp, cycles=(1, 2), step=6, fade=0.12)


# ===========================================================================
# PILOT SET: wave, point, clap, arms_crossed (contact)
# ===========================================================================

@clip("wave", "gesture", 2.5, loop=False, framing='body', still_frame=0.24,
      description="R-hand wave: drag-chain raise (elbow leads, wrist+fingers "
                  "trail), 3 decaying waves 100/85/60%, shoulder stays DOWN "
                  "(clavicle<=5deg), torso counter-rot 3deg, head tilt toward "
                  "wave; HOOK soft_smile; lower slower than raise; L arm alive")
def wave(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.2, amp=0.7, phase=0.2)
    _both_hang(ctx, [F, E])            # both arms hang at both ends
    _rest_life(ctx, 'L')               # left arm micro-alive (additive)
    # RIGHT ARM raise: elbow stays low (upperarm z high), lift via fwd flex
    # (x) + forearm bend; drag chain (forearm trails 2f). Calibrated apex.
    # elbow OUT to the character's right (upperarm z low ~12), moderate
    # flex -> hand out at shoulder height on the RIGHT side (this rig sweeps
    # the hand to center on high flex, so a shoulder-height SIDE wave reads
    # cleaner than a raised one and never occludes the face).
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (12, 54.0), (48, 54.0), (66, 30.0), (74, 7.5)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', v, B),
        F, [(0, 57.13), (12, 8.0), (48, 8.0), (74, 57.13)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', v, B),
        F, [(0, 9.0), (12, -16.0), (48, -16.0), (74, 9.0)])
    # forearm near-straight so the hand stays EXTENDED OUT at shoulder height
    # (like the point pose); the wave is the forearm-z oscillation below
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, [(0, 11.04), (14, 18.0), (50, 18.0), (68, 14.0), (74, 11.04)])
    # wave: forearm z oscillates, decaying 100/85/60 %, ~10-11 f period
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
        F, [(0, 3.0), (16, 0.0), (20, 22.0), (26, -22.0), (32, 18.7),
            (37, -18.7), (43, 13.2), (48, -8.0), (52, 3.0), (74, 3.0)])
    # fingers: soft splay while up, whip 2 f behind the wrist, back to hang
    for i, (fng, base) in enumerate((("Index", 4.0), ("Mid", 5.5),
                                     ("Ring", 7.0), ("Pinky", 8.5))):
        hang1 = base * 0.94
        _ev(lambda f, v, ff=fng: ctx.finger_curl('R', ff, 1, f, v, layer=B),
            F, [(0, hang1), (18 + i, -6.0), (50 + i, -6.0), (74, hang1)])
        for j, ja in ((2, 0.85), (3, 0.6)):  # keep joints 2/3 at hang curl
            ctx.finger_curl('R', fng, j, F, base * ja * 0.94, layer=B)
            ctx.finger_curl('R', fng, j, E, base * ja * 0.94, layer=B)
    ctx.finger_curl('R', "Thumb", 2, F, 3.0, layer=B)
    ctx.finger_curl('R', "Thumb", 2, E, 3.0, layer=B)
    # torso counter-rotates 3 deg away from the wave; shoulder stays DOWN
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(0, 0.0), (12, 3.0), (48, 3.0), (66, 0.0)])
    _ev(lambda f, v: ctx.clavicle_raise('R', f, v, layer='sh'),
        F, [(0, 0.0), (12, 3.5), (48, 3.5), (74, 0.0)])   # <=5 deg
    # head tilts 4 deg toward the wave (character's right = +roll here)
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (16, 4.0), (48, 3.6), (66, -0.4), (74, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (16, -3.0), (48, -2.7), (74, 0.0)])


@clip("point", "gesture", 1.8, loop=False, framing='body', still_frame=0.42,
      description="R-hand point: GAZE leads (eyes f0, head f2), DISTAL-FIRST "
                  "arm (index extends, then wrist/elbow/shoulder), full "
                  "extension f14 with 5% overshoot at shoulder height, torso "
                  "rot 4deg, hold on target 15f, retract w/ drag, gaze LAST")
def point(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.0, amp=0.6, phase=0.5)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # gaze leads: eyes saccade to the front target at f0, head follows f2,
    # both return at the very end (gaze LAST)
    motion.gaze_to(ctx, F + 1, 0.30, -0.05)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (2, 0.0), (10, 7.0), (34, 6.6), (46, 0.5), (52, 0.0)])
    motion.gaze_to(ctx, F + 47, 0.0, 0.0, from_dx=0.30, from_dy=-0.05)
    # DISTAL-FIRST: index straightens first, then the arm extends. Full arm
    # extension f14, 5% overshoot at f13. Calibrated forward-point apex.
    _ev(lambda f, v: ctx.finger_curl('R', "Index", 1, f, v, layer=B),
        F, [(0, 4.0 * 0.94), (7, -16.0), (10, -18.0), (34, -17.0),
            (48, 4.0 * 0.94)])
    for fng, a in (("Mid", 42.0), ("Ring", 46.0), ("Pinky", 48.0)):
        for j in (1, 2, 3):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, a * 0.35 * 0.94), (9, a * 0.9), (34, a * 0.9),
                    (48, a * 0.35 * 0.94)])
    _ev(lambda f, v: ctx.finger_curl('R', "Thumb", 2, f, v, layer=B),
        F, [(0, 3.0), (9, 18.0), (34, 18.0), (48, 3.0)])
    # index joints 2/3 stay near-straight through the point
    for j in (2, 3):
        _ev(lambda f, v, jj=j: ctx.finger_curl('R', "Index", jj, f, v,
                                               layer=B),
            F, [(0, 4.0 * (0.85 if j == 2 else 0.6) * 0.94), (10, 2.0),
                (34, 2.0), (48, 4.0 * (0.85 if j == 2 else 0.6) * 0.94)])
    # upperarm: straight-arm forward point at shoulder height (x high),
    # distal-first so it starts a touch after the finger; overshoot f13
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (8, 40.0), (13, 60.0), (14, 56.0), (34, 56.0),
            (50, 7.5)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', v, B),
        F, [(0, 57.13), (8, 28.0), (14, 6.0), (34, 6.0), (50, 57.13)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', v, B),
        F, [(0, 9.0), (14, -8.0), (34, -8.0), (50, 9.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, [(0, 11.04), (11, 16.0), (13, 10.0), (14, 12.0), (34, 13.0),
            (50, 11.04)])
    ctx.key_bone_axis("CC_Base_R_Forearm", F, 'z', 3.0, layer=B)
    ctx.key_bone_axis("CC_Base_R_Forearm", E, 'z', 3.0, layer=B)
    # torso supports 4 deg rotation
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(0, 0.0), (12, 4.0), (34, 3.7), (48, 0.0)])


@clip("clap", "gesture", 2.5, loop=False, framing='body', still_frame=0.36,
      description="Both hands rise to chest, FOUR claps at 8/7/9/8f "
                  "(irregular, off-15f-grid), each a 1f impact hold, contact "
                  "left-of-center (R dominant), shoulders bounce 1deg/clap, "
                  "head micro-nod beats 2+4, release with 2 relax bounces")
def clap(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.0, amp=0.4, phase=0.7)   # ducked
    _both_hang(ctx, [F, E])
    # upperarms: high flexion so bent forearms bring the hands to center;
    # hold the raised base f8..f40, return to hang by the tail
    for s, uy1, uz1 in (('L', -20.0, -8.0), ('R', 20.0, 8.0)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][0]), (8, 56.0), (40, 56.0), (72, _HANG[s][0])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (8, uy1), (40, uy1), (72, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (8, uz1), (40, uz1), (72, _HANG[s][2])])
    # forearm x pulses = the claps. frames 8,16,23,32 -> gaps 8,7,9,8.
    claps = [8, 16, 23, 32]
    l_open, l_hit = 44.0, 74.0     # anvil moves less
    r_open, r_hit = 48.0, 80.0     # hammer moves more (contact left-of-center)
    lpts = [(0, 11.04), (8, l_open)]
    rpts = [(0, 11.04), (8, r_open)]
    for k, cf in enumerate(claps):
        lpts += [(cf, l_hit), (cf + 1, l_hit)]      # 1 f impact hold
        rpts += [(cf, r_hit), (cf + 1, r_hit)]
        if k < len(claps) - 1:
            mid = (cf + claps[k + 1]) // 2 + 1
            lpts += [(mid, l_open)]
            rpts += [(mid, r_open)]
    lpts += [(42, l_open), (54, l_open * 0.4), (72, 11.04)]   # 2 relax bounces
    rpts += [(42, r_open), (52, r_open * 0.45), (72, 11.04)]
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'x', v, B),
        F, lpts)
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, rpts)
    # fingers flex soft on each contact (R splays a touch more), else hang
    for s, sc in (('L', 1.0), ('R', 1.15)):
        _hang_fingers(ctx, s, [F, E])
        for cf in claps:
            for fng, a in (("Index", 6.0), ("Mid", 7.0), ("Ring", 7.5),
                           ("Pinky", 8.0)):
                base = dict(_FING)[fng] * (0.85) * _HANG[s][5]  # joint2 hang
                _ev(lambda f, v, ss=s, ff=fng: ctx.finger_curl(
                    ss, ff, 2, f, v, layer=B),
                    F + cf, [(-2, base), (0, base + a * sc),
                             (3, base + a * sc * 0.4), (6, base)])
    # shoulders bounce 1 deg per clap; head micro-nod on beats 2 and 4
    for cf in claps:
        for s in ('L', 'R'):
            _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='sh'),
                F + cf, [(-1, 0.0), (1, 1.0), (5, 0.0)])
        _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='sbounce'),
            F + cf, [(-1, 0.0), (1, 0.8), (6, 0.0)])
    for cf in (claps[1], claps[3]):
        _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='nod'),
            F + cf, [(-1, 0.0), (2, 1.6), (5, -0.2), (9, 0.0)])


@clip("arms_crossed", "gesture", 2.0, loop=False, framing='body',
      still_frame=0.85,
      description="CONTACT entry: LEFT arm crosses first f0-12, RIGHT tucks "
                  "OVER it f6-20 (staggered), L hand grips R upper arm, R "
                  "fingers tuck under L elbow; shoulders roll fwd 2deg, "
                  "weight back 1cm, chin level; END POSE HOLDABLE (pairs with "
                  "arms_crossed_exit)")
def arms_crossed(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    D = E - F
    motion.breathing(ctx, period=4.5, amp=0.5, phase=0.33)   # <=0.5 clearance
    _both_hang(ctx, [F])          # start at hang; END holds the crossed pose
    # LEFT arm crosses the torso FIRST (f0-12): forearm sweeps across, hand
    # ends gripping the R upper arm. Probe-tuned for chest clearance.
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
        F, [(0, 8.0), (12, 40.0), (D, 40.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'y', v, B),
        F, [(0, -10.0), (12, 40.0), (D, 40.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'z', v, B),
        F, [(0, -58.0), (12, -18.0), (D, -18.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'x', v, B),
        F, [(0, 12.0), (12, 108.0), (D, 108.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'z', v, B),
        F, [(0, -3.0), (12, -30.0), (D, -30.0)])
    # RIGHT arm tucks OVER, staggered f6-20, fingers slide under L elbow
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', v, B),
        F, [(0, 7.5), (6, 7.5), (20, 40.0), (D, 40.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', v, B),
        F, [(0, 9.0), (6, 9.0), (20, -40.0), (D, -40.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', v, B),
        F, [(0, 57.13), (6, 57.13), (20, 18.0), (D, 18.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', v, B),
        F, [(0, 11.04), (6, 11.04), (20, 116.0), (D, 116.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
        F, [(0, 3.0), (6, 3.0), (20, 32.0), (D, 32.0)])
    # fingers: L grips (curl around R bicep), R tucks soft
    for fng, a in (("Index", 34.0), ("Mid", 38.0), ("Ring", 40.0),
                   ("Pinky", 42.0)):
        for j, ja in ((1, 1.0), (2, 0.9), (3, 0.6)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('L', ff, jj, f, v,
                                                           layer=B),
                F, [(0, a * ja * 0.15), (12, a * ja), (D, a * ja)])
    for fng, a in (("Index", 20.0), ("Mid", 24.0), ("Ring", 26.0),
                   ("Pinky", 28.0)):
        for j in (1, 2, 3):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, a * 0.15), (20, a * 0.8), (D, a * 0.8)])
    ctx.finger_curl('L', "Thumb", 2, F, 3.0, layer=B)
    ctx.finger_curl('L', "Thumb", 2, F + 12, 16.0, layer=B)
    ctx.finger_curl('L', "Thumb", 2, E, 16.0, layer=B)
    ctx.finger_curl('R', "Thumb", 2, F, 3.0, layer=B)
    ctx.finger_curl('R', "Thumb", 2, E, 8.0, layer=B)
    # shoulders roll forward 2 deg, weight back 1 cm, chin level (slight round)
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='sh'),
            F, [(0, 0.0), (16, -2.0), (D, -2.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
                                            layer='wt'),
        F, [(0, 0.0), (18, 1.0), (D, 1.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='sbend'),
        F, [(0, 0.0), (14, 1.0), (D, 1.0)])


# ===========================================================================
# calibrated single-R-arm waypoint helpers (from the reach sweep + pilots)
# ===========================================================================
def _r_arm(ctx, pts_ua, pts_faz):
    """Key the R upperarm (x,y,z) and forearm (x,z) from lists of
    (off, (ux,uy,uz)) and (off, (fx,fz)) waypoints on layer B."""
    for off, (ux, uy, uz) in pts_ua:
        f = ctx.frame_start + off
        ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'x', ux, B)
        ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'y', uy, B)
        ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', uz, B)
    for off, (fx, fz) in pts_faz:
        f = ctx.frame_start + off
        ctx.key_bone_axis("CC_Base_R_Forearm", f, 'x', fx, B)
        ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', fz, B)


def _r_fist(ctx, frames, amp=90.0, thumb=None):
    """Curl R fingers into a fist at each frame (thumb handled separately)."""
    for f in frames:
        for fng in ("Index", "Mid", "Ring", "Pinky"):
            for j, ja in ((1, 1.0), (2, 1.0), (3, 0.85)):
                ctx.finger_curl('R', fng, j, f, amp * ja, layer=B)
        if thumb is not None:
            for j in (1, 2, 3):
                ctx.finger_curl('R', "Thumb", j, f, thumb, layer=B)


# ===========================================================================
# hello / goodbye  (wave family variations)
# ===========================================================================
@clip("hello", "gesture", 2.0, loop=False, framing='body', still_frame=0.4,
      description="Short greeting: single open-palm arc raise to shoulder "
                  "(drag chain), palm shows 12f softly splayed, simultaneous "
                  "head nod at f14 (baked), lower f30-50; HOOKS brow_raise + "
                  "soft_smile. Snappier/smaller than wave, an arc not a wave")
def hello(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.1, amp=0.6, phase=0.15)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # single arc raise, hold, lower (no oscillation) — arm out at shoulder
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (14, (52.0, -14.0, 12.0)),
                 (30, (52.0, -14.0, 12.0)), (48, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (16, (20.0, -8.0)), (30, (20.0, -8.0)),
            (48, (11.04, 3.0))])
    # fingers softly splayed while up (not board-flat), back to hang
    for fng, a in _FING:
        _ev(lambda f, v, ff=fng: ctx.finger_curl('R', ff, 1, f, v, layer=B),
            F, [(0, a * 0.94), (16, -3.0), (30, -3.0), (48, a * 0.94)])
        for j, ja in ((2, 0.85), (3, 0.6)):
            ctx.finger_curl('R', fng, j, F, a * ja * 0.94, layer=B)
            ctx.finger_curl('R', fng, j, E, a * ja * 0.94, layer=B)
    ctx.finger_curl('R', "Thumb", 2, F, 3.0, layer=B)
    ctx.finger_curl('R', "Thumb", 2, E, 3.0, layer=B)
    # baked head nod synced to the palm-show (body owns head)
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='nod'),
        F, [(0, 0.0), (14, -1.0), (18, 5.0), (23, -1.2), (28, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='nod'),
        F, [(0, 0.0), (16, 3.0), (24, 0.0)])
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (16, 2.5), (30, 2.2), (44, 0.0)])


@clip("goodbye", "gesture", 2.5, loop=False, framing='body', still_frame=0.5,
      description="Slower warmer wave: raise w/ 1cm forward lean, TWO slow "
                  "big-arc waves, hand HOLDS raised 10f (lingering), head "
                  "tilt + fading soft_smile HOOK, lower over 20f on a sigh-"
                  "timed settle (breathing exhale)")
def goodbye(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=5.2, amp=0.8, phase=0.6)   # slow, warm
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # raise (slower, 16f), two big slow waves, lingering hold, slow lower
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (16, (54.0, -16.0, 10.0)),
                 (58, (54.0, -16.0, 10.0)), (74, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (18, (20.0, 3.0)), (58, (20.0, 3.0)),
            (74, (11.04, 3.0))])
    # two big slow waves then a lingering hold (bigger arc than hello/wave)
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
        F, [(0, 3.0), (18, 3.0), (24, 30.0), (33, -26.0), (42, 26.0),
            (50, -6.0), (58, 8.0), (74, 3.0)])   # 2 waves, then hold ~8
    for fng, a in _FING:
        _ev(lambda f, v, ff=fng: ctx.finger_curl('R', ff, 1, f, v, layer=B),
            F, [(0, a * 0.94), (20, -4.0), (58, -4.0), (74, a * 0.94)])
        for j, ja in ((2, 0.85), (3, 0.6)):
            ctx.finger_curl('R', fng, j, F, a * ja * 0.94, layer=B)
            ctx.finger_curl('R', fng, j, E, a * ja * 0.94, layer=B)
    # forward lean 1 cm on the raise, settle back on the (sigh) lower
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
                                            layer='lean'),
        F, [(0, 0.0), (18, -1.0), (58, -1.0), (74, 0.0)])
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (20, 3.5), (58, 3.0), (74, 0.0)])


# ===========================================================================
# thumbs_up / thumbs_down
# ===========================================================================
@clip("thumbs_up", "gesture", 1.8, loop=False, framing='body',
      still_frame=0.5,
      description="Forearm raises to chest f0-8 as fingers curl to a fist "
                  "(1f cascade); thumb POPS up f8-10 w/ 15% overshoot + 3f "
                  "settle, forearm supinates 20deg, 2cm punch-forward accent; "
                  "baked head nod on the pop; hold w/ thumb waver, retract")
def thumbs_up(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.0, amp=0.5, phase=0.4)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # forearm up to chest, supinated (palm inward), then punch-forward 2cm
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (8, (34.0, -30.0, 42.0)),
                 (10, (34.0, -34.0, 42.0)), (35, (34.0, -34.0, 42.0)),
                 (52, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (8, (86.0, -18.0)), (10, (90.0, -22.0)),
            (35, (88.0, -22.0)), (52, (11.04, 3.0))])
    # fingers curl to fist 1f cascade f2-8; thumb pops up f8-10 overshoot
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        for j, ja in ((1, 1.0), (2, 1.0), (3, 0.85)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, dict(_FING)[fng] * (0.85 if j != 1 else 1.0) * 0.94),
                    (4 + i, 92.0 * ja), (35, 92.0 * ja),
                    (50, dict(_FING)[fng] * 0.94)])
    _ev(lambda f, v: ctx.finger_curl('R', "Thumb", 1, f, v, layer=B),
        F, [(0, 3.0), (8, 30.0), (9, -6.0), (10, -8.0), (13, -3.0),
            (35, -3.0), (50, 3.0)])
    for j in (2, 3):
        _ev(lambda f, v, jj=j: ctx.finger_curl('R', "Thumb", jj, f, v, B),
            F, [(0, 3.0), (9, 2.0), (10, -2.0), (35, -1.0), (50, 3.0)])
    # baked head nod synced to the thumb pop
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='nod'),
        F, [(0, 0.0), (8, -0.8), (11, 4.0), (16, -0.5), (22, 0.0)])


@clip("thumbs_down", "gesture", 1.8, loop=False, framing='body',
      still_frame=0.5,
      description="Inverted thumbs_up: fist cascade, forearm PRONATES, thumb "
                  "rotates DOWN with a slower heavier 5f arrival (disapproval "
                  "has weight, not snap); single small head shake (baked) + "
                  "brow_drop HOOK; hold, retract")
def thumbs_down(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.3, amp=0.5, phase=0.2)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # same across-chest fist as thumbs_up (upper arm tucked in, y=-30) but
    # forearm PRONATES (z positive = palm down) so the extended thumb points
    # DOWN; heavier 5f arrival (no snap)
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (8, (34.0, -30.0, 42.0)),
                 (14, (34.0, -34.0, 42.0)), (36, (34.0, -34.0, 42.0)),
                 (52, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (8, (84.0, 16.0)), (14, (88.0, 24.0)),
            (36, (88.0, 24.0)), (52, (11.04, 3.0))])
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        for j, ja in ((1, 1.0), (2, 1.0), (3, 0.85)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, dict(_FING)[fng] * (0.85 if j != 1 else 1.0) * 0.94),
                    (5 + i, 92.0 * ja), (36, 92.0 * ja),
                    (50, dict(_FING)[fng] * 0.94)])
    # thumb extends DOWN with a slow 5f heavy arrival (no snap)
    _ev(lambda f, v: ctx.finger_curl('R', "Thumb", 1, f, v, layer=B),
        F, [(0, 3.0), (14, -6.0), (19, -8.0), (36, -8.0), (50, 3.0)])
    for j in (2, 3):
        ctx.finger_curl('R', "Thumb", j, F, 3.0, layer=B)
        ctx.finger_curl('R', "Thumb", j, F + 19, -2.0, layer=B)
        ctx.finger_curl('R', "Thumb", j, E, 3.0, layer=B)
    # single small head shake (baked) — ONE swing only, not a full 'no'
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='shake'),
        F, [(0, 0.0), (14, 4.0), (22, -3.0), (30, 0.0)])


# ===========================================================================
# celebrate (both arms)
# ===========================================================================
@clip("celebrate", "gesture", 2.5, loop=False, framing='body',
      still_frame=0.32,
      description="Anticipation crouch f0-5 (spine flex, arms cock back), "
                  "EXPLODE f5-11 both fists up w/ 8% overshoot, chest opens, "
                  "head back 6deg, heels rise; TWO pumps f11-30 (2nd smaller, "
                  "R higher +1f offset, NOT mirrored); settle f30-60 heels "
                  "down, arms drag, 2 diminishing shoulder bounces. big_smile "
                  "HOOK")
def celebrate(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=3.6, amp=0.3, phase=0.5)   # ducked
    _both_hang(ctx, [F])
    _both_hang(ctx, [E])
    # both upperarms: hang -> cock down-back (antic) -> throw UP into a V
    for s, sy in (('L', 1.0), ('R', -1.0)):
        hi = 92.0 if s == 'R' else 88.0     # R fists higher (asymmetry)
        lag = 1 if s == 'R' else 0          # R 1f late
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][0]), (5, -6.0), (11 + lag, hi + 7),
                (16, hi), (30, hi), (44, hi * 0.5), (60, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (11 + lag, -28.0 * sy), (30, -28.0 * sy),
                (60, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (5, _HANG[s][2]), (11 + lag, 34.0 * (1 if s == 'R' else -1)),
                (30, 34.0 * (1 if s == 'R' else -1)), (60, _HANG[s][2])])
        # forearm: bent up, 2 pumps (elbow), 2nd smaller
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][3]), (11 + lag, 30.0), (16 + lag, 12.0),
                (21 + lag, 28.0), (26 + lag, 16.0), (30, 22.0),
                (60, _HANG[s][3])])
        _r_fist(ctx, [F + 11, F + 30], amp=95.0, thumb=70.0) if s == 'R' \
            else None
        # L fist
        if s == 'L':
            for fng in ("Index", "Mid", "Ring", "Pinky"):
                for j in (1, 2, 3):
                    ctx.finger_curl('L', fng, j, F + 11, 95.0, layer=B)
                    ctx.finger_curl('L', fng, j, F + 30, 95.0, layer=B)
            for j in (1, 2, 3):
                ctx.finger_curl('L', "Thumb", j, F + 11, 70.0, layer=B)
    # crouch antic then chest opens + head back; heels rise (hip up + feet)
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='spine'),
        F, [(0, 0.0), (5, 5.0), (11, -8.0), (30, -6.0), (44, 1.0),
            (60, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (5, 3.0), (11, -6.0), (30, -5.0), (60, 0.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
                                            layer='hop'),
        F, [(0, 0.0), (5, -3.0), (12, 3.0), (18, 0.5), (30, 0.0),
            (60, 0.0)])
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Foot", f,
                                                 'x', v, layer='heel'),
            F, [(0, 0.0), (12, -10.0), (24, -6.0), (34, 0.0)])
    # 2 diminishing shoulder bounces in the settle
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='bounce'),
            F, [(30, 0.0), (36, 1.5), (42, -0.5), (48, 0.6), (54, 0.0)])


# ===========================================================================
# shrug (both arms + clavicles)
# ===========================================================================
@clip("shrug", "gesture", 1.8, loop=False, framing='body', still_frame=0.5,
      description="4f antic dip, rise: L clavicle LEADS R by 1-2f, shoulders "
                  "up 8deg, elbows flare out, forearms supinate palms-up w/ "
                  "finger splay cascade f8-14, head tilt 5deg; brow_raise "
                  "HOOK peaks WITH the shoulders; hold 12f palm waver; release "
                  "DOWN slower than rise, fingers relax last")
def shrug(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.2, amp=0.4, phase=0.3)
    _both_hang(ctx, [F, E])
    # clavicles: 4f antic dip then up 8 deg, L leads R by 2f (asymmetry)
    for s, lag, amp in (('L', 0, 8.5), ('R', 2, 8.0)):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='clav'),
            F, [(0, 0.0), (4, -1.0), (8 + lag, amp), (14 + lag, amp),
                (28, amp), (46, 0.0)])
    # upperarms flare out, forearms supinate palms-up
    for s, sy in (('L', 1.0), ('R', -1.0)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][0]), (10, 26.0), (28, 26.0), (46, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (10, -18.0 * sy), (28, -18.0 * sy),
                (46, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (10, _HANG[s][2] * 0.55), (28, _HANG[s][2] * 0.55),
                (46, _HANG[s][2])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][3]), (12, 70.0), (28, 70.0), (46, _HANG[s][3])])
        # palms-up = forearm supinate (z); finger splay cascade f8-14
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Forearm", f, 'z', v, B),
            F, [(0, _HANG[s][4]), (12, 45.0 * sy), (28, 45.0 * sy),
                (46, _HANG[s][4])])
        for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
            a = dict(_FING)[fng]
            _ev(lambda f, v, ss=s, ff=fng: ctx.finger_curl(ss, ff, 1, f, v,
                                                           layer=B),
                F, [(0, a), (8 + i + (0 if s == 'L' else 2), -8.0),
                    (28, -8.0), (46, a)])
            for j, ja in ((2, 0.85), (3, 0.6)):
                ctx.finger_curl(s, fng, j, F, a * ja, layer=B)
                ctx.finger_curl(s, fng, j, F + 28, a * ja - 4.0, layer=B)
                ctx.finger_curl(s, fng, j, E, a * ja, layer=B)
    # head tilt 5 deg (peaks with shoulders), small pitch up
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (12, 5.0), (28, 4.5), (46, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (12, -2.0), (28, -1.8), (46, 0.0)])


# ===========================================================================
# hands_together (clasp entry) — reuses the idle_hands_together pose
# ===========================================================================
@clip("hands_together", "gesture", 1.5, loop=False, framing='body',
      still_frame=0.85,
      description="Entry INTO the idle_hands_together pose: both hands rise "
                  "and meet at pelvis f0-16, fingers interleave (3f "
                  "choreography, R slides between L, staggered per finger), "
                  "6f settle squeeze. End pose = idle_hands_together f0")
def hands_together(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    D = E - F
    motion.breathing(ctx, period=4.0, amp=0.45, phase=0.44)
    _both_hang(ctx, [F])
    # target clasp pose (probe-matched to idle_hands_together)
    clasp = {"CC_Base_L_Upperarm": (26.0, 40.0, -30.0),
             "CC_Base_R_Upperarm": (26.0, -40.0, 30.0),
             "CC_Base_L_Forearm": (55.0, 0.0, -10.0),
             "CC_Base_R_Forearm": (55.0, 0.0, 10.0)}
    for bone, (x, y, z) in clasp.items():
        _ev(lambda f, v, bb=bone: ctx.key_bone_axis(bb, f, 'x', v, B),
            F, [(0, _HANG[bone.split('_')[2]][0]
                 if 'Upperarm' in bone else _HANG[bone.split('_')[2]][3]),
                (16, x), (D, x)])
        _ev(lambda f, v, bb=bone: ctx.key_bone_axis(bb, f, 'y', v, B),
            F, [(0, _HANG[bone.split('_')[2]][1] if 'Upperarm' in bone
                 else 0.0), (16, y), (D, y)])
        _ev(lambda f, v, bb=bone: ctx.key_bone_axis(bb, f, 'z', v, B),
            F, [(0, _HANG[bone.split('_')[2]][2] if 'Upperarm' in bone
                 else _HANG[bone.split('_')[2]][4]), (16, z), (D, z)])
    # interleaved finger curls — L deeper than R so hands mesh; staggered
    # per finger (3f choreography), then a 6f settle squeeze
    for s, base in (('L', 40.0), ('R', 30.0)):
        for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
            for j, ja in ((1, 1.0), (2, 0.8), (3, 0.5)):
                _ev(lambda f, v, ss=s, ff=fng, jj=j: ctx.finger_curl(
                    ss, ff, jj, f, v, layer=B),
                    F, [(0, dict(_FING)[fng] * ja * _HANG[s][5]),
                        (10 + i + (0 if s == 'L' else 2), (base + i * 2) * ja),
                        (16, (base + i * 2) * ja + 3.0),   # settle squeeze
                        (22, (base + i * 2) * ja), (D, (base + i * 2) * ja)])
        ctx.finger_curl(s, "Thumb", 2, F, 3.0, layer=B)
        ctx.finger_curl(s, "Thumb", 2, F + 16, 12.0, layer=B)
        ctx.finger_curl(s, "Thumb", 2, E, 12.0, layer=B)


# ===========================================================================
# CONTACT: thinking_pose, face_palm, heart_gesture (probe-verified)
# ===========================================================================
@clip("thinking_pose", "gesture", 2.2, loop=False, framing='body',
      still_frame=0.7,
      description="CONTACT: LEFT arm crosses first (the shelf) f0-10, RIGHT "
                  "elbow lands on L wrist f8-14, R hand rises to chin (index "
                  "along cheek, thumb under chin, others curled) f14-20; head "
                  "tilts 4deg toward the hand + pitches down 2deg (leans IN "
                  "after contact); thinking facial + gaze-up-left HOOKS; index "
                  "taps cheek x2 at f50")
def thinking_pose(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    D = E - F
    motion.breathing(ctx, period=4.6, amp=0.4, phase=0.5)
    _both_hang(ctx, [F])
    # LEFT arm crosses low = the shelf under the R elbow
    _r_like_L = None
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'x', v, B),
        F, [(0, 8.0), (10, 34.0), (D, 34.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'y', v, B),
        F, [(0, -10.0), (10, 40.0), (D, 40.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'z', v, B),
        F, [(0, -58.0), (10, -14.0), (D, -14.0)])
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'x', v, B),
        F, [(0, 12.0), (10, 100.0), (D, 100.0)])
    # RIGHT arm: upper arm tucks in (elbow rests on L shelf), forearm up so
    # the hand reaches the chin; staggered after the shelf
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (8, (7.5, 9.0, 57.13)),
                 (14, (44.0, -18.0, 30.0)), (20, (52.0, -20.0, 26.0)),
                 (D, (52.0, -20.0, 26.0))],
           [(0, (11.04, 3.0)), (8, (11.04, 3.0)), (14, (95.0, 0.0)),
            (20, (118.0, 0.0)), (D, (118.0, 0.0))])
    # R fingers: index along cheek (extended), others curled soft, thumb under
    _ev(lambda f, v: ctx.finger_curl('R', "Index", 1, f, v, layer=B),
        F, [(0, 4.0 * 0.94), (20, 6.0), (D, 6.0)])
    for fng, a in (("Mid", 40.0), ("Ring", 44.0), ("Pinky", 46.0)):
        for j in (1, 2, 3):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, dict(_FING)[fng] * 0.94), (20, a * 0.9), (D, a * 0.9)])
    ctx.finger_curl('R', "Thumb", 1, F, 3.0, layer=B)
    ctx.finger_curl('R', "Thumb", 1, F + 20, 30.0, layer=B)
    ctx.finger_curl('R', "Thumb", 1, E, 30.0, layer=B)
    # L fingers grip its own forearm-ish (soft curl)
    _hang_fingers(ctx, 'L', [F])
    for fng in ("Index", "Mid", "Ring", "Pinky"):
        for j in (1, 2, 3):
            ctx.finger_curl('L', fng, j, F + 10, 22.0, layer=B)
            ctx.finger_curl('L', fng, j, E, 22.0, layer=B)
    # head tilts toward the hand + pitches down; leans IN 1.5deg MORE after
    # contact (weight into the hand), then two index taps (f50)
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (18, 4.0), (24, 5.5), (D, 5.2)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (18, 2.0), (24, 3.0), (D, 2.8)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (20, 3.0), (D, 2.8)])
    # gaze up-left (thinking aversion) — eyes lead
    motion.gaze_to(ctx, F + 16, 0.3, 0.35)
    # index taps cheek x2 around f50 (extended-play micro-life)
    for tf in (48, 56):
        _ev(lambda f, v: ctx.finger_curl('R', "Index", 2, f, v, layer=B),
            F + tf, [(-2, 4.0), (0, 12.0), (4, 4.0)])


@clip("face_palm", "gesture", 2.2, loop=False, framing='body',
      still_frame=0.6,
      description="CONTACT: head STARTS dropping before the hand (despair "
                  "leads, 3f). Palm meets forehead f12 SOFT (fingers spread "
                  "over brow), head sinks INTO the hand 4f more (hand yields "
                  "1deg), shoulders slump 3deg; eyes-closed + exhale HOOKS; "
                  "hold 20f; release hand drags down 6f, head recovers LAST")
def face_palm(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=5.0, amp=0.5, phase=0.7)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # R hand rises to the forehead: high flex + very bent forearm brings the
    # hand back to the brow (probe-verified for clearance)
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (12, (70.0, -18.0, 6.0)),
                 (16, (72.0, -18.0, 4.0)), (40, (72.0, -18.0, 4.0)),
                 (46, (40.0, 0.0, 30.0)), (56, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (12, (120.0, -10.0)), (16, (124.0, -10.0)),
            (40, (124.0, -10.0)), (46, (90.0, -6.0)), (56, (11.04, 3.0))])
    # fingers spread over the brow (soft splay, not fist)
    for fng, a in (("Index", 12.0), ("Mid", 10.0), ("Ring", 12.0),
                   ("Pinky", 16.0)):
        for j, ja in ((1, 1.0), (2, 0.7), (3, 0.5)):
            _ev(lambda f, v, ff=fng, jj=j: ctx.finger_curl('R', ff, jj, f, v,
                                                           layer=B),
                F, [(0, dict(_FING)[fng] * ja * 0.94), (14, a * ja),
                    (44, a * ja), (56, dict(_FING)[fng] * ja * 0.94)])
    # head drops FIRST (3f antic), sinks into the hand, recovers LAST
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (3, 3.0), (12, 9.0), (16, 11.0), (44, 10.5),
            (52, 3.0), (56, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='head'),
        F, [(0, 0.0), (12, 4.0), (16, 5.0), (44, 4.8), (54, 0.0)])
    # shoulders slump 3 deg, spine rounds
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='slump'),
            F, [(0, 0.0), (16, -3.0), (44, -3.0), (56, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, layer='slump'),
        F, [(0, 0.0), (16, 2.0), (44, 2.0), (56, 0.0)])


@clip("heart_gesture", "gesture", 2.5, loop=False, framing='body',
      still_frame=0.55,
      description="CONTACT: both hands rise to sternum f0-14 converging, "
                  "fingers form a heart f14-24 (thumbs tip-to-tip down, index "
                  "fingers arc to meet at top); shape pulses TWICE like a "
                  "heartbeat (lub-dub, unequal f30/f42); head tilt 5deg + "
                  "soft_smile HOOK; release hands part downward softly")
def heart_gesture(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.4, amp=0.4, phase=0.6)
    _both_hang(ctx, [F, E])
    # both hands to the sternum, converging (R staggered 1f from L)
    for s, sy, lag in (('L', 1.0, 0), ('R', -1.0, 1)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Upperarm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][0]), (14 + lag, 52.0), (56, 52.0),
                (70, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (14 + lag, 22.0 * sy), (56, 22.0 * sy),
                (70, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (14 + lag, 10.0 * (1 if s == 'R' else -1)),
                (56, 10.0 * (1 if s == 'R' else -1)), (70, _HANG[s][2])])
        # forearm bent so the hands meet at the sternum; pulse in/out x2
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][3]), (14 + lag, 74.0), (30, 78.0), (36, 74.0),
                (42, 77.0), (48, 74.0), (56, 74.0), (70, _HANG[s][3])])
        # fingers: index extended to arc to the top, others curled, thumb down
        _ev(lambda f, v, ss=s: ctx.finger_curl(ss, "Index", 1, f, v, layer=B),
            F, [(0, dict(_FING)["Index"] * _HANG[s][5]), (22, 34.0),
                (56, 34.0), (70, dict(_FING)["Index"] * _HANG[s][5])])
        ctx.finger_curl(s, "Index", 2, F + 22, 30.0, layer=B)
        ctx.finger_curl(s, "Index", 2, F + 56, 30.0, layer=B)
        for fng in ("Mid", "Ring", "Pinky"):
            for j in (1, 2, 3):
                ctx.finger_curl(s, fng, j, F + 22, 60.0, layer=B)
                ctx.finger_curl(s, fng, j, F + 56, 60.0, layer=B)
        ctx.finger_curl(s, "Thumb", 1, F + 22, -8.0, layer=B)
        ctx.finger_curl(s, "Thumb", 1, F + 56, -8.0, layer=B)
    # head tilt 5 deg
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (22, 5.0), (56, 4.6), (70, 0.0)])


# ===========================================================================
# come_here / stop_gesture / question_gesture / presentation_gesture
# ===========================================================================
@clip("come_here", "gesture", 2.0, loop=False, framing='body',
      still_frame=0.5,
      description="R arm half-extends palm-up f0-10 (elbow STAYS bent — full "
                  "extension reads as 'stop'); THREE finger curls f10-34 "
                  "(fingers lead, wrist follows 1f, amp 100/90/70%, spacing "
                  "8/7f); baked beckon head-tilt on curl 2; brow+smile HOOKS; "
                  "hand lowers fingers still half-curled")
def come_here(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.1, amp=0.5, phase=0.3)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # half-extend forward, palm-up (forearm supinated), elbow stays bent
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (10, (46.0, -16.0, 22.0)),
                 (40, (46.0, -16.0, 22.0)), (54, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (10, (58.0, -40.0)), (40, (58.0, -40.0)),
            (54, (11.04, 3.0))])
    # three beckon curls: fingers lead, spacing 8/7 f, amp 100/90/70 %
    for ci, (cf, amp) in enumerate([(12, 1.0), (20, 0.9), (27, 0.7)]):
        for fng in ("Index", "Mid", "Ring", "Pinky"):
            base = dict(_FING)[fng] * 0.94
            for j, ja in ((1, 1.0), (2, 0.9), (3, 0.7)):
                _ev(lambda f, v, ss='R', ff=fng, jj=j: ctx.finger_curl(
                    ss, ff, jj, f, v, layer=B),
                    F + cf, [(-2, base + (18.0 if ci else 0.0)),
                             (2, base + 60.0 * amp * ja),
                             (6, base + 18.0 * ja)])
        # wrist follows 1 f behind the fingers
        _ev(lambda f, v: ctx.key_bone_axis("CC_Base_R_Forearm", f, 'z', v, B),
            F + cf, [(-1, -40.0), (3, -30.0), (7, -40.0)])
    # leave fingers half-curled at the end (relaxed residue), then hang
    for fng in ("Index", "Mid", "Ring", "Pinky"):
        for j in (1, 2, 3):
            ctx.finger_curl('R', fng, j, F + 40, 20.0, layer=B)
    # baked beckon head-tilt synced to curl 2 (~f20), weight back 1cm
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (18, 3.0), (24, 3.2), (40, 2.5), (52, 0.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
                                            layer='wt'),
        F, [(0, 0.0), (12, 1.0), (40, 1.0), (54, 0.0)])


@clip("stop_gesture", "gesture", 1.5, loop=False, framing='body',
      still_frame=0.55,
      description="SHARP: arm extends palm-forward in 5f (fastest in the "
                  "library), fingers splay in a 2f tail AFTER the palm plants; "
                  "shoulders square 3deg, chin drops 2deg, weight sinks 1cm; "
                  "hand holds ABSOLUTELY still (0.02 tremor) 18f; release is "
                  "the contrast — slow 15f melt down. brow_drop HOOK")
def stop_gesture(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=3.8, amp=0.35, phase=0.2)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # SHARP raise, hand comes UP in front palm-forward (forearm bent up ~78
    # so the hand is vertical / fingers up = 'halt'), 5f; slow 15f release
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (3, (7.5, 9.0, 40.0)),
                 (7, (56.0, -12.0, 18.0)), (26, (56.0, -12.0, 18.0)),
                 (44, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (5, (78.0, 3.0)), (26, (78.0, 3.0)),
            (44, (11.04, 3.0))])
    # fingers splay AFTER the palm plants (2f tail at f5-9), hold splayed
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        a = dict(_FING)[fng] * 0.94
        _ev(lambda f, v, ff=fng: ctx.finger_curl('R', ff, 1, f, v, layer=B),
            F, [(0, a), (5, a), (7 + i, -12.0), (26, -12.0), (40, a)])
        for j, ja in ((2, 0.85), (3, 0.6)):
            ctx.finger_curl('R', fng, j, F, a * ja, layer=B)
            ctx.finger_curl('R', fng, j, F + 8, -4.0, layer=B)
            ctx.finger_curl('R', fng, j, E, a * ja, layer=B)
    # square the shoulders 3 deg, chin drop 2 deg, weight sink 1 cm
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (7, 2.0), (26, 2.0), (44, 0.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
                                            layer='sink'),
        F, [(0, 0.0), (7, -1.0), (26, -1.0), (44, 0.0)])
    # micro tension tremor during the hold (0.02 deg on the wrist)
    for tf in range(10, 26, 3):
        ctx.key_bone_axis("CC_Base_R_Hand", F + tf, 'x',
                          0.02 * (1 if tf % 2 else -1), layer='tremor')


@clip("question_gesture", "gesture", 2.0, loop=False, framing='body',
      still_frame=0.5,
      description="Both palms rotate UP and spread outward f0-12, elbows near "
                  "ribs, RIGHT hand 3cm higher than L (asymmetry); shoulder "
                  "shrug HINT 3deg (half a shrug); head tilt 6deg + brow_raise "
                  "HOOKS peak w/ the palms; fingers loose, micro-waver in the "
                  "12f hold; small outward pulse f30 ('well??'); recover soft")
def question_gesture(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.2, amp=0.4, phase=0.5)
    _both_hang(ctx, [F, E])
    # both forearms out + supinate palms-up; R ends 3 cm higher (asym)
    for s, sy, hi in (('L', 1.0, 30.0), ('R', -1.0, 38.0)):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'x', v, B),
            F, [(0, _HANG[s][0]), (12, hi), (24, hi), (30, hi + 3),
                (36, hi), (52, _HANG[s][0])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'y', v, B),
            F, [(0, _HANG[s][1]), (12, -16.0 * sy), (36, -16.0 * sy),
                (52, _HANG[s][1])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Upperarm", f, 'z', v, B),
            F, [(0, _HANG[s][2]), (12, _HANG[s][2] * 0.5),
                (36, _HANG[s][2] * 0.5), (52, _HANG[s][2])])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(f"CC_Base_{ss}_Forearm",
                                                 f, 'x', v, B),
            F, [(0, _HANG[s][3]), (12, 46.0), (24, 46.0), (30, 40.0),
                (36, 46.0), (52, _HANG[s][3])])
        _ev(lambda f, v, ss=s, yy=sy: ctx.key_bone_axis(
            f"CC_Base_{ss}_Forearm", f, 'z', v, B),
            F, [(0, _HANG[s][4]), (12, 55.0 * sy), (36, 55.0 * sy),
                (52, _HANG[s][4])])
        # loose open fingers with a micro-waver in the hold
        for fng in ("Index", "Mid", "Ring", "Pinky"):
            a = dict(_FING)[fng] * _HANG[s][5]
            _ev(lambda f, v, ss=s, ff=fng: ctx.finger_curl(ss, ff, 1, f, v,
                                                           layer=B),
                F, [(0, a), (12, -2.0), (22, 1.0), (30, -3.0), (52, a)])
            for j, ja in ((2, 0.85), (3, 0.6)):
                ctx.finger_curl(s, fng, j, F, a * ja, layer=B)
                ctx.finger_curl(s, fng, j, E, a * ja, layer=B)
    # shrug HINT (clavicles 3 deg) + head tilt 6 deg, peak with the palms
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.clavicle_raise(ss, f, v, layer='clav'),
            F, [(0, 0.0), (12, 3.0), (36, 3.0), (52, 0.0)])
    _ev(lambda f, v: ctx.roll("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (12, 6.0), (36, 5.4), (52, 0.0)])


@clip("presentation_gesture", "gesture", 2.5, loop=False, framing='body',
      still_frame=0.6,
      description="R arm sweeps open L-to-R across 15f, palm rotating UP "
                  "DURING the sweep (wrist trails arm 3f), fingers trail soft; "
                  "torso follows 4deg; gaze TRACKS the sweeping hand then "
                  "returns to front 5f after the arm plants; hold open 15f "
                  "w/ breathing drift; L hand alive; recover w/ drag")
def presentation_gesture(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.3, amp=0.5, phase=0.4)
    _both_hang(ctx, [F, E])
    _rest_life(ctx, 'L')
    # sweep the arm open across the front: start tucked-in (across body),
    # end extended out to the R; palm rotates up during the sweep (fa z)
    _r_arm(ctx, [(0, (7.5, 9.0, 57.13)), (6, (44.0, 6.0, 34.0)),
                 (21, (52.0, -12.0, 10.0)), (40, (52.0, -12.0, 10.0)),
                 (54, (7.5, 9.0, 57.13))],
           [(0, (11.04, 3.0)), (6, (30.0, -5.0)), (24, (24.0, -45.0)),
            (40, (24.0, -45.0)), (54, (11.04, 3.0))])   # wrist trails 3f
    # fingers soft-open, trailing
    for fng in ("Index", "Mid", "Ring", "Pinky"):
        a = dict(_FING)[fng] * 0.94
        _ev(lambda f, v, ff=fng: ctx.finger_curl('R', ff, 1, f, v, layer=B),
            F, [(0, a), (10, -2.0), (40, -2.0), (54, a)])
        for j, ja in ((2, 0.85), (3, 0.6)):
            ctx.finger_curl('R', fng, j, F, a * ja, layer=B)
            ctx.finger_curl('R', fng, j, E, a * ja, layer=B)
    # torso follows 4 deg; gaze tracks the hand then returns front 5f after
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(0, 0.0), (10, -1.5), (21, -4.0), (40, -3.7), (52, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='head'),
        F, [(0, 0.0), (8, 3.0), (21, -6.0), (34, -5.5), (46, 2.0),
            (52, 0.0)])
    # gaze tracks the sweeping hand (character's right = negative dx), then
    # returns to front ~5 f after the arm plants (f21 -> f26)
    motion.gaze_to(ctx, F + 4, 0.15, 0.0)
    motion.gaze_to(ctx, F + 20, -0.35, -0.05, from_dx=0.15)
    motion.gaze_to(ctx, F + 40, 0.0, 0.0, from_dx=-0.35, from_dy=-0.05)
