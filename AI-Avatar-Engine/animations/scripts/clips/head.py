"""Head clips (Tier 1, owner: body) — 6 per library_spec.json.

One-shots (nod_small/big, shake_no, tilt_left/right) + the additive
head_micro loop. Shared rules: rotation split across Head + NeckTwist01
(neck 35-40 %), neck trails 1-2 f; humans never move on a single axis —
every clip carries whisper off-axis motion; eyes counter-rotate against
the head (vestibulo-ocular reflex) so the gaze stays on the viewer;
anticipation before, overshoot + settle after. tilt_right is re-authored
with different timings/amplitudes — NOT a mirror of tilt_left.
"""
from anim_framework.clips import clip
from anim_framework import motion

HEAD = "CC_Base_Head"
NECK = "CC_Base_NeckTwist01"
NECK2 = "CC_Base_NeckTwist02"


def _ev(fn, f0, pts):
    for off, v in pts:
        fn(f0 + off, v)


def _vor_updown(ctx, pts, r_lag=1, r_scale=0.95, layer='vor'):
    """Vertical eye counter-look: +v = eyes look UP (head pitched down)."""
    for off_fn, key_up, key_dn in ((0, "Eye_L_Look_Up", "Eye_L_Look_Down"),
                                   (r_lag, "Eye_R_Look_Up", "Eye_R_Look_Down")):
        sc = 1.0 if off_fn == 0 else r_scale
        for off, v in pts:
            ctx.key_shape(key_up, off + off_fn, max(0.0, v) * sc, layer)
            ctx.key_shape(key_dn, off + off_fn, max(0.0, -v) * sc, layer)


def _vor_lr(ctx, pts, r_lag=1, r_scale=0.95, layer='vor'):
    """Horizontal eye counter-look: +v = eyes look LEFT (head yawed right)."""
    for off_fn in (0, r_lag):
        sc = 1.0 if off_fn == 0 else r_scale
        for s in ('L', 'R'):
            if (off_fn == 0) != (s == 'L'):
                continue
            for off, v in pts:
                ctx.key_shape(f"Eye_{s}_Look_L", off + off_fn,
                              max(0.0, v) * sc, layer)
                ctx.key_shape(f"Eye_{s}_Look_R", off + off_fn,
                              max(0.0, -v) * sc, layer)


@clip("nod_small", "head", 0.8, loop=False, framing='face', still_frame=0.4,
      description="Small yes-nod: 1 deg chin-up anticipation, 8 deg drop "
                  "(head 60/neck 40), overshoot 1.5 deg past neutral, "
                  "settle by f24; eyes hold the viewer (VOR)")
def nod_small(ctx):
    F = ctx.frame_start
    # head 60 % — anticipation UP, drop, overshoot past neutral, settle
    _ev(lambda f, v: ctx.pitch(HEAD, f, v, layer='nod'),
        F, [(0, 0.0), (3, -0.65), (8, 4.9), (11, 4.6), (14, -0.95),
            (18, 0.3), (24, 0.0)])
    # neck 40 %, trailing 1-2 f
    _ev(lambda f, v: ctx.pitch(NECK, f, v, layer='nod'),
        F, [(0, 0.0), (4, -0.35), (10, 3.2), (13, 3.0), (16, -0.55),
            (20, 0.15), (24, 0.0)])
    # never on-axis: whisper of yaw + roll drift
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='drift'),
        F, [(0, 0.0), (9, 0.5), (16, -0.25), (24, 0.0)])
    _ev(lambda f, v: ctx.roll(HEAD, f, v, layer='drift'),
        F, [(0, 0.0), (10, 0.3), (24, 0.0)])
    # VOR: eyes counter-look up while the chin is down, tiny down on the
    # overshoot; right eye lags 1 f at 95 % (never identical L/R)
    _vor_updown(ctx, [(F, 0.0), (F + 3, -0.02), (F + 8, 0.13),
                      (F + 11, 0.12), (F + 14, -0.03), (F + 19, 0.0)])


@clip("nod_big", "head", 1.3, loop=False, framing='face', still_frame=0.28,
      description="Emphatic yes: two nods 15 deg then 60 %, chin leads, "
                  "spine02 rides 2 deg, jaw inertia at each bottom, "
                  "eyes hold target, full settle")
def nod_big(ctx):
    F = ctx.frame_start
    # nod #1 15 deg total (head ~9.3 / neck ~5.7), nod #2 at 60 %, quicker
    _ev(lambda f, v: ctx.pitch(HEAD, f, v, layer='nod'),
        F, [(0, 0.0), (3, -1.3), (9, 9.3), (12, 8.6), (17, -1.5),
            (21, 5.6), (24, 5.2), (29, -0.8), (34, 0.25), (39, 0.0)])
    _ev(lambda f, v: ctx.pitch(NECK, f, v, layer='nod'),
        F, [(0, 0.0), (4, -0.7), (11, 5.7), (14, 5.3), (19, -0.8),
            (23, 3.4), (26, 3.1), (31, -0.4), (39, 0.0)])
    # energy passes through the torso on the big one (spine02 ~2 deg)
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='nod'),
        F, [(0, 0.0), (5, -0.3), (11, 2.0), (18, 0.5), (24, 1.0),
            (32, 0.15), (39, 0.0)])
    # jaw inertia: mouth cracks open ~0.7 deg for 2 f at each nod bottom
    _ev(lambda f, v: ctx.jaw_open(f, v),
        F, [(7, 0.0), (10, 0.7), (13, 0.05), (20, 0.0), (23, 0.45),
            (26, 0.0)])
    # off-axis whisper — slightly different arc per nod
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='drift'),
        F, [(0, 0.0), (10, -0.6), (22, 0.4), (31, -0.2), (39, 0.0)])
    _vor_updown(ctx, [(F, 0.0), (F + 4, -0.03), (F + 9, 0.24),
                      (F + 13, 0.22), (F + 17, -0.04), (F + 22, 0.13),
                      (F + 26, 0.12), (F + 31, -0.02), (F + 36, 0.0)],
                r_lag=2, r_scale=0.93)


@clip("shake_no", "head", 1.2, loop=False, framing='face', still_frame=0.3,
      description="No: 3 f opposite anticipation then 2.5 decaying "
                  "oscillations 12-7-3 deg, period ~10 f varying, eyes "
                  "counter-sweep to stay on target, ends centered")
def shake_no(ctx):
    F = ctx.frame_start
    # anticipation LEFT +2.5, then swings R -12, L +7, R -3, settle 0
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='shake'),
        F, [(0, 0.0), (3, 2.5), (9, -12.0), (18, 7.0), (27, -3.0),
            (33, 0.8), (36, 0.0)])
    # neck 35 %, trailing 2 f
    _ev(lambda f, v: ctx.yaw(NECK, f, v, layer='shake'),
        F, [(0, 0.0), (5, 0.9), (11, -4.2), (20, 2.45), (29, -1.05),
            (36, 0.0)])
    # chin drops half a degree during the shakes, recovers
    _ev(lambda f, v: ctx.pitch(HEAD, f, v, layer='drift'),
        F, [(0, 0.0), (8, 0.5), (26, 0.35), (36, 0.0)])
    _ev(lambda f, v: ctx.roll(HEAD, f, v, layer='drift'),
        F, [(0, 0.0), (12, -0.35), (24, 0.25), (36, 0.0)])
    # VOR horizontal: eyes counter every swing (stay on the viewer) —
    # this is what reads as a communicative "no", not a scan
    _vor_lr(ctx, [(F, 0.0), (F + 3, -0.06), (F + 9, 0.30), (F + 18, -0.18),
                  (F + 27, 0.08), (F + 33, -0.02), (F + 36, 0.0)],
            r_lag=1, r_scale=0.96)


@clip("tilt_left", "head", 1.0, loop=False, framing='face', still_frame=0.55,
      description="Curious tilt: 9 deg roll left over 10 f + coupled 2 deg "
                  "yaw, 1 deg overshoot, 8 f settle, ends HOLDING the "
                  "tilt; eyes counter-roll ~50 % (L up / R down); "
                  "shoulder stays DOWN")
def tilt_left(ctx):
    F = ctx.frame_start
    # roll 9 total: head ~6 / neck ~3 (35 %); overshoot to 10, settle, HOLD
    _ev(lambda f, v: ctx.roll(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (2, -0.4), (10, 6.7), (14, 5.8), (18, 6.15),
            (26, 6.0), (30, 6.05)])
    _ev(lambda f, v: ctx.roll(NECK, f, v, layer='tilt'),
        F, [(0, 0.0), (3, -0.2), (12, 3.3), (16, 2.9), (20, 3.05),
            (30, 3.0)])
    # pure roll looks robotic: coupled same-side yaw + tiny pitch-in
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (11, 2.0), (16, 1.75), (30, 1.85)])
    _ev(lambda f, v: ctx.pitch(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (12, 0.9), (30, 0.85)])
    # eyes counter-roll read (~50 %): no torsion keys on the rig, so the
    # conjugate proxy is a small vertical DIFFERENTIAL — L eye up, R down
    _ev(lambda f, v: ctx.key_shape("Eye_L_Look_Up", f, v, layer='vor'),
        F, [(0, 0.0), (11, 0.09), (16, 0.08), (30, 0.08)])
    _ev(lambda f, v: ctx.key_shape("Eye_R_Look_Down", f, v, layer='vor'),
        F, [(1, 0.0), (12, 0.085), (17, 0.075), (30, 0.075)])
    # micro drift in the hold so it never freezes
    _ev(lambda f, v: ctx.roll(NECK2, f, v, layer='drift'),
        F, [(0, 0.0), (20, 0.25), (26, 0.1), (30, 0.18)])


@clip("tilt_right", "head", 1.0, loop=False, framing='face',
      still_frame=0.6,
      description="Tilt right, re-authored (NOT mirrored tilt_left): "
                  "8 deg over 12 f slower onset, softer overshoot, "
                  "coupled 1.5 deg yaw, ends holding")
def tilt_right(ctx):
    F = ctx.frame_start
    # 8 deg total, 12 f slower onset, gentler overshoot, later settle
    _ev(lambda f, v: ctx.roll(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (3, 0.3), (12, -5.9), (17, -5.15), (22, -5.45),
            (30, -5.35)])
    _ev(lambda f, v: ctx.roll(NECK, f, v, layer='tilt'),
        F, [(0, 0.0), (4, 0.15), (14, -2.9), (19, -2.6), (30, -2.7)])
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (13, -1.5), (19, -1.3), (30, -1.4)])
    _ev(lambda f, v: ctx.pitch(HEAD, f, v, layer='tilt'),
        F, [(0, 0.0), (14, 0.7), (30, 0.65)])
    # counter-roll proxy mirrored the other way, slightly weaker + later
    _ev(lambda f, v: ctx.key_shape("Eye_R_Look_Up", f, v, layer='vor'),
        F, [(0, 0.0), (13, 0.08), (19, 0.07), (30, 0.07)])
    _ev(lambda f, v: ctx.key_shape("Eye_L_Look_Down", f, v, layer='vor'),
        F, [(2, 0.0), (15, 0.075), (21, 0.065), (30, 0.065)])
    _ev(lambda f, v: ctx.roll(NECK2, f, v, layer='drift'),
        F, [(0, 0.0), (22, -0.2), (28, -0.08), (30, -0.14)])


@clip("head_micro", "head", 8.0, loop=True, framing='face', still_frame=0.54,
      description="ADDITIVE head life layer: 0.3-0.8 deg non-repeating "
                  "3-axis drift (neck carries 30 %), one 2 deg attention "
                  "micro-turn ~f130 with eyes leading, zero-delta seams")
def head_micro(ctx):
    F = ctx.frame_start
    # band-limited drift, decorrelated per axis, faded to ZERO at both
    # boundaries (additive stacking contract) — prime-ish cycle mixes so
    # no visible repeat inside the 8 s window
    specs = (('y', 0.72, (2, 3, 5)), ('x', 0.45, (3, 4, 7)),
             ('z', 0.30, (2, 5, 7)))
    for axis, amp, cycles in specs:
        motion.loop_noise(
            ctx, lambda f, v, a=axis: ctx.key_bone_axis(HEAD, f, a, v,
                                                        layer='drift'),
            amp=amp, cycles=cycles, step=4, fade=0.08)
        motion.loop_noise(
            ctx, lambda f, v, a=axis: ctx.key_bone_axis(NECK, f, a, v,
                                                        layer='driftn'),
            amp=amp * 0.43, cycles=cycles, step=4, fade=0.08)
    # one 2 deg attention micro-turn at ~f130, eyes lead by 4 f, 10 f return
    for s, sc, lag in (('L', 1.0, 0), ('R', 0.94, 1)):
        _ev(lambda f, v, ss=s: ctx.key_shape(f"Eye_{ss}_Look_L", f,
                                             max(0.0, v), layer='gaze'),
            F + lag, [(120, 0.0), (123, 0.14), (136, 0.12), (146, 0.0)])
    _ev(lambda f, v: ctx.yaw(HEAD, f, v, layer='turn'),
        F, [(0, 0.0), (126, 0.0), (132, 2.0), (138, 1.8), (148, -0.2),
            (152, 0.0)])
    _ev(lambda f, v: ctx.yaw(NECK, f, v, layer='turn'),
        F, [(0, 0.0), (128, 0.0), (134, 0.85), (140, 0.75), (152, 0.0)])
