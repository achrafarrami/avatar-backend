"""Idle clips (Tier 1, owner: body) — 8 loops per library_spec.json.

Every idle bakes its own breath layer (motion.breathing, per-clip
phase/period so clips never breathe in unison) — glTF has no additive
blending. Weight shifts translate CC_Base_Hip AND counter-rotate the
thighs so the feet stay planted (hip-only translation slides the whole
character). Arm-contact poses (clasp front / behind back / phone) were
solved by world-space probe sweeps against the template rig.

Conventions: pitch+ down, yaw+ character-left, roll+ toward left
shoulder; clavicle_raise+ lifts; finger_curl+ toward palm; hip loc in
armature cm (x+ left, y+ back, z+ up).
"""
from anim_framework.clips import clip
from anim_framework import motion

# planted-feet constants (measured: thigh 15 deg moves foot 22.5 cm)
K_LAT = 0.667  # thigh z deg per cm hip x
K_FA = 0.667   # thigh x deg per cm hip y


def _ev(fn, f0, pts):
    """Key (frame_offset, value) pairs through fn(frame, value)."""
    for off, v in pts:
        fn(f0 + off, v)


def _hip(ctx, keys, layer='weight', counter=1.0):
    """Weight-stance keys [(f, x_cm, y_cm, z_cm)]: Hip loc + thigh
    counter-rotation (feet planted) + spine counter-lean lagged 2 f +
    head re-level + trailing-shoulder drop lagged 3 f."""
    for f, x, y, z in keys:
        ctx.key_bone_loc_world("Hip", f, (x, y, z), layer=layer)
        for s in ('L', 'R'):
            ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f, 'z', -K_LAT * x,
                              layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Thigh", f, 'x', K_FA * y,
                              layer=layer)
    for f, x, y, z in keys:
        ctx.roll("CC_Base_Spine01", f + 2, -0.9 * x * counter, layer=layer)
        ctx.roll("CC_Base_Spine02", f + 2, -0.5 * x * counter, layer=layer)
        ctx.roll("CC_Base_NeckTwist01", f + 2, 0.25 * x * counter, layer=layer)
        ctx.roll("CC_Base_Head", f + 2, 0.5 * x * counter, layer=layer)
        ctx.clavicle_raise('R', f + 3, -0.30 * max(0.0, x), layer=layer + 'c')
        ctx.clavicle_raise('L', f + 3, -0.30 * max(0.0, -x), layer=layer + 'c')


# Relaxed-hand baseline (SHARED CONTRACT with gestures.py _FING and
# locomotion.py _FING — the three must stay identical or idle<->gesture
# blends pop at the fingers). KNUCKLE-LED: real resting fingers bend most
# at the MCP (joint 1), moderately at PIP, barely at DIP — an even falloff
# reads as a flat scoop from the front. Falloff _JFALL (1.0/0.7/0.4);
# totals: Index ~34, Mid ~42, Ring ~50, Pinky ~59 deg, pinky deepest.
# History: 4/5.5/7/8.5 and 6/8/11.5/14.5 read mannequin-flat; 10/13/16.5/
# 19.5 at (1/.85/.6) still too even.
_FING = (("Index", 16.0), ("Mid", 20.0), ("Ring", 24.0), ("Pinky", 28.0))
_JFALL = ((1, 1.0), (2, 0.7), (3, 0.4))
_TH1, _TH2, _TH3 = 6.0, 10.0, 6.0  # relaxed thumb, ~22 deg total


def _arms_hang(ctx, fx=12.0, uz=58.0, layer='pose', curl=1.0):
    """Relaxed arms-at-sides baseline (probe-solved). The armature REST is
    a wide A-pose — every idle must author the natural hang or the arms
    read as a mannequin. Slight L/R asymmetry baked in (never mirrored)."""
    F, E = ctx.frame_start, ctx.frame_end
    sides = (('L', 8.0, -10.0, -uz, fx, -3.0, 1.0),
             ('R', 7.5, 9.0, uz * 0.985, fx * 0.92, 3.0, 0.94))
    for s, ux, uy, uzz, fxx, fz, csc in sides:
        # slight wrist relax: forearm pronation (palm drifts toward the
        # thigh, +y pronates on L / -y on R) + soft palm droop. Idle-only
        # channels — gestures never key Hand/forearm-y in their hang, so
        # crossfades simply carry these values through.
        pron = 3.0 if s == 'L' else -2.5
        droop = 4.0 if s == 'L' else 3.5
        for f in (F, E):
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'x', ux, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'y', uy, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Upperarm", f, 'z', uzz, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'x', fxx, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'z', fz, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Forearm", f, 'y', pron, layer=layer)
            ctx.key_bone_axis(f"CC_Base_{s}_Hand", f, 'x', droop, layer=layer)
        if curl > 0.0:
            for fng, a in _FING:
                for j, ja in _JFALL:
                    for f in (F, E):
                        ctx.finger_curl(s, fng, j, f, a * ja * curl * csc,
                                        layer=layer)
            # subtle splay — fingers fan apart slightly (never glued);
            # render-verified: finger z frames mirror L/R like the thumb
            for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
                spread = (i - 1.5) * 2.5  # -3.75, -1.25, +1.25, +3.75
                zs = spread if s == 'L' else -spread
                for f in (F, E):
                    ctx.key_bone_axis(f"CC_Base_{s}_{fng}1", f, 'z', zs,
                                      layer=layer + 'spl')
            for f in (F, E):
                ctx.finger_curl(s, "Thumb", 1, f, _TH1 * curl, layer=layer)
                ctx.finger_curl(s, "Thumb", 2, f, _TH2 * curl, layer=layer)
                ctx.finger_curl(s, "Thumb", 3, f, _TH3 * curl, layer=layer)


def _arm_sway(ctx, amp=0.35):
    """Passive slow arm drift — arms are never dead."""
    for side in ('L', 'R'):
        a = amp * ctx.rng.uniform(0.85, 1.15)
        motion.loop_noise(
            ctx, lambda f, v, s=side: ctx.key_bone_axis(
                f"CC_Base_{s}_Upperarm", f, 'x', v, layer='armsway'),
            amp=a, cycles=(1, 2, 3), step=6)
        motion.loop_noise(
            ctx, lambda f, v, s=side: ctx.key_bone_axis(
                f"CC_Base_{s}_Forearm", f, 'x', v, layer='armsway'),
            amp=a * 0.5, cycles=(2, 3), step=6)


def _finger_ripple(ctx, f0, side='R', amp=6.0, gap=2):
    """One index-to-pinky curl-relax cascade (2 f phase per finger)."""
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        for joint, ja in ((1, 1.0), (2, 0.8), (3, 0.6)):
            _ev(lambda f, v, fn=fng, j=joint: ctx.finger_curl(
                side, fn, j, f, v, layer='ev_fingers'),
                f0 + i * gap, [(0, 0.0), (7, amp * ja), (11, amp * ja * 0.85),
                               (18, 0.0)])


def _thumb_rub(ctx, f0, side='R', amp=8.0, cycles=2, period=12):
    """Thumb pad rubs along the index — small oscillation + index yield."""
    fn2 = lambda f, v: ctx.finger_curl(side, "Thumb", 2, f, v, layer='ev_fingers')
    fn3 = lambda f, v: ctx.finger_curl(side, "Thumb", 3, f, v, layer='ev_fingers')
    fnI = lambda f, v: ctx.finger_curl(side, "Index", 1, f, v, layer='ev_fingers')
    fn2(f0, 0.0); fn3(f0, 0.0); fnI(f0, 0.0)
    f = f0
    for c in range(cycles):
        p = period + ctx.rng.randint(-2, 2)
        fn2(f + p // 2, amp); fn3(f + p // 2, amp * 0.7)
        fnI(f + p // 2 + 1, 2.0)
        fn2(f + p, amp * 0.25); fn3(f + p, amp * 0.2); fnI(f + p, 0.6)
        f += p
    fn2(f + 6, 0.0); fn3(f + 6, 0.0); fnI(f + 5, 0.0)


# ---------------------------------------------------------------------------
@clip("idle_01", "idle", 10.0, loop=True, framing='body', still_frame=0.44,
      description="Primary idle: weight LEFT, one shift to RIGHT f116-160 "
                  "with hip overshoot, head micro-turn right f75-210, "
                  "finger ripple f160, R shoulder rides 1 deg low")
def idle_01(ctx):
    F = ctx.frame_start
    motion.breathing(ctx, period=4.1, amp=0.95, phase=0.13)
    _arms_hang(ctx)
    # stance: LEFT at f0, antic counter-sway further left f110-116, commit
    # RIGHT f116-140 with 8 % overshoot, settle f160, drift back f270-300
    _hip(ctx, [(F, 1.8, 0.0, 0.0), (F + 60, 1.9, 0.0, 0.0),
               (F + 110, 1.8, 0.0, 0.0), (F + 116, 2.8, 0.0, -0.1),
               (F + 128, -0.4, 0.0, -0.3), (F + 140, -2.16, 0.0, -0.05),
               (F + 152, -1.9, 0.0, 0.0), (F + 160, -2.0, 0.0, 0.0),
               (F + 230, -2.1, 0.0, 0.0), (F + 270, -2.0, 0.0, 0.0),
               (F + 300, 1.8, 0.0, 0.0)])
    # right shoulder rides ~1 deg lower than left throughout
    ctx.clavicle_raise('R', F, -1.0, layer='pose')
    ctx.clavicle_raise('R', F + 150, -1.15, layer='pose')
    ctx.clavicle_raise('R', F + 300, -1.0, layer='pose')
    # head micro-turn 2.5 deg right at f75, back at f210 — eyes lead 3 f
    motion.gaze_to(ctx, F + 72, -0.18, 0.0)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='turn'),
        F, [(0, 0.0), (75, 0.0), (87, -2.5), (150, -2.2), (207, -2.4),
            (219, 0.3), (228, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='turn'),
        F, [(0, 0.0), (77, 0.0), (90, -1.1), (209, -1.0), (224, 0.0)])
    motion.gaze_to(ctx, F + 206, 0.0, 0.0, from_dx=-0.18)
    _ev(lambda f, v: ctx.key_shape("Eye_L_Look_R", f, v, layer='gz2'),
        F, [(150, 0.0), (168, 0.045), (186, 0.015), (200, 0.0)])  # drift
    _ev(lambda f, v: ctx.key_shape("Eye_R_Look_R", f, v, layer='gz2'),
        F, [(151, 0.0), (169, 0.042), (187, 0.014), (201, 0.0)])
    # finger relaxation ripple at f160 (right hand), baseline curls alive
    motion.finger_relax(ctx, amp_deg=1.6)
    _finger_ripple(ctx, F + 160, side='R', amp=6.0)
    # never-frozen drift
    motion.head_micro_sway(ctx, amp_deg=0.55)
    motion.loop_noise(ctx, lambda f, v: ctx.roll("CC_Base_Spine02", f, v,
                                                 layer='sway'),
                      amp=0.3, cycles=(2, 3), step=5)
    _arm_sway(ctx)


@clip("idle_02", "idle", 12.0, loop=True, framing='body', still_frame=0.31,
      description="Idle B: weight RIGHT, fore-aft rock (toes f90-130, "
                  "heels f200-240), chin raise f150, L wrist supination "
                  "f180, R shoulder roll f260 — not a mirror of idle_01")
def idle_02(ctx):
    F = ctx.frame_start
    motion.breathing(ctx, period=4.4, amp=0.9, phase=0.57)
    _arms_hang(ctx, fx=11.0)
    # stance RIGHT throughout; fore-aft rock via hip y (feet planted,
    # thighs counter) — toes f90-130, back to heels f200-240, neutral late
    _hip(ctx, [(F, -1.7, 0.0, 0.0), (F + 90, -1.7, 0.0, 0.0),
               (F + 112, -1.75, -1.1, -0.1), (F + 130, -1.7, -1.0, -0.05),
               (F + 175, -1.65, -0.9, 0.0), (F + 200, -1.7, -0.6, 0.0),
               (F + 225, -1.75, 0.7, -0.1), (F + 240, -1.7, 0.6, 0.0),
               (F + 290, -1.68, 0.2, 0.0), (F + 360, -1.7, 0.0, 0.0)],
         counter=0.92)
    # spine rides the rock: 1.5 deg forward on toes, slight back on heels
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, layer='rock'),
        F, [(0, 0.0), (92, 0.0), (116, 0.9), (132, 0.85), (178, 0.6),
            (204, 0.1), (228, -0.35), (244, -0.3), (300, -0.1), (360, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='rock'),
        F, [(0, 0.0), (94, 0.0), (118, 0.6), (134, 0.55), (180, 0.4),
            (206, 0.05), (230, -0.25), (246, -0.2), (302, -0.05),
            (360, 0.0)])
    # left shoulder rides low this time (vary the asymmetry, not mirror it)
    ctx.clavicle_raise('L', F, -0.8, layer='pose')
    ctx.clavicle_raise('L', F + 190, -0.95, layer='pose')
    ctx.clavicle_raise('L', F + 360, -0.8, layer='pose')
    # chin raise 2 deg at f150 held ~1.5 s, eased down over 20 f
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='chin'),
        F, [(0, 0.0), (148, 0.0), (158, -2.0), (176, -1.85), (195, -1.95),
            (215, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='chin'),
        F, [(0, 0.0), (150, 0.0), (161, -0.7), (197, -0.65), (218, 0.0)])
    # left hand supinates 8 deg at f180, wrist leads fingers by 2 f
    _ev(lambda f, v: ctx.key_bone_axis("CC_Base_L_Forearm", f, 'y', v,
                                       layer='ev'),
        F, [(0, 0.0), (178, 0.0), (190, -8.0), (215, -7.4), (235, 0.0)])
    for j, ja in ((1, 1.0), (2, 0.7)):
        _ev(lambda f, v, jj=j: ctx.finger_curl('L', "Mid", jj, f, v,
                                               layer='ev_fingers'),
            F, [(180, 0.0), (194, 3.0 * ja), (218, 2.6 * ja), (238, 0.0)])
    # one right shoulder roll at f260 (up - over - settle)
    _ev(lambda f, v: ctx.clavicle_raise('R', f, v, layer='ev'),
        F, [(0, 0.0), (256, 0.0), (263, 1.3), (271, -0.45), (280, 0.0)])
    motion.finger_relax(ctx, amp_deg=1.7, period=9.0)
    motion.head_micro_sway(ctx, amp_deg=0.5)
    _arm_sway(ctx)


@clip("idle_relaxed", "idle", 12.0, loop=True, framing='body',
      still_frame=0.5,
      description="Relaxed idle: soft spine flexion, elbows bent, hands "
                  "in natural curl, 70% tempo, head sway on 6 s breath "
                  "cadence (pairs with breathing_deep)")
def idle_relaxed(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=6.0, amp=1.0, chest=1.25, shoulders=0.8,
                     head=1.5, phase=0.31)
    # softened posture (chest cave < 3 deg total incl. breath)
    for f in (F, E):
        ctx.pitch("CC_Base_Spine01", f, 1.1, layer='pose')
        ctx.pitch("CC_Base_Spine02", f, 0.8, layer='pose')
        ctx.pitch("CC_Base_Head", f, 1.8, layer='pose')
        ctx.pitch("CC_Base_NeckTwist01", f, 0.6, layer='pose')
    _arms_hang(ctx, fx=17.0, curl=0.0)  # deeper elbow bend; own curl below
    # hands in soft natural curl, pinky deepest (never paddle-flat) —
    # a touch deeper than the shared hang: this is the sleepy idle
    for s, sc in (('L', 1.0), ('R', 0.9)):
        for fng, a in (("Index", 18.0), ("Mid", 22.5), ("Ring", 27.0),
                       ("Pinky", 31.5)):
            for j, ja in _JFALL:
                for f in (F, E):
                    ctx.finger_curl(s, fng, j, f, a * ja * sc, layer='pose')
        for f in (F, E):
            ctx.finger_curl(s, "Thumb", 1, f, _TH1 * sc, layer='pose')
            ctx.finger_curl(s, "Thumb", 2, f, 11.0 * sc, layer='pose')
            ctx.finger_curl(s, "Thumb", 3, f, 7.0 * sc, layer='pose')
    # ONE lazy weight shift at f180 over ~30 f (70 % tempo), return late
    _hip(ctx, [(F, 0.9, 0.0, 0.0), (F + 175, 0.9, 0.0, 0.0),
               (F + 192, -0.2, 0.0, -0.2), (F + 208, -1.3, 0.0, 0.0),
               (F + 290, -1.35, 0.0, 0.0), (F + 330, -0.6, 0.0, 0.0),
               (F + 360, 0.9, 0.0, 0.0)], counter=0.85)
    # continuous wrist rotation drift +-1.5 deg, decorrelated hands
    for s in ('L', 'R'):
        motion.loop_noise(ctx, lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Forearm", f, 'y', v, layer='wrist'),
            amp=1.5, cycles=(1, 2), step=6)
    motion.finger_relax(ctx, amp_deg=2.0, period=10.0)
    motion.head_micro_sway(ctx, amp_deg=0.45)
    _arm_sway(ctx, amp=0.3)


@clip("idle_confident", "idle", 10.0, loop=True, framing='body',
      still_frame=0.28,
      description="Confident idle: chest lifted 3 deg, half sway, "
                  "deliberate head sweep L-R f60-120 with mid dwell, "
                  "chin-up f150, one clean weight transfer f210-250")
def idle_confident(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.3, amp=0.85, shoulders=0.7, phase=0.71)
    # chest lift WITHOUT backward lean (spine02 extension + head level)
    for f in (F, E):
        ctx.pitch("CC_Base_Spine02", f, -1.9, layer='pose')
        ctx.pitch("CC_Base_Spine01", f, -0.5, layer='pose')
        ctx.pitch("CC_Base_Head", f, 0.6, layer='pose')  # chin level, not up
        ctx.clavicle_raise('L', f, 0.3, layer='pose')
        ctx.clavicle_raise('R', f, 0.12, layer='pose')  # asym, near-level
    _arms_hang(ctx, fx=9.0)  # arms a touch straighter — composed
    # slow deliberate survey sweep with a 6 f dwell mid-sweep; eyes lead
    motion.gaze_to(ctx, F + 56, 0.28, 0.02)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='sweep'),
        F, [(0, 0.0), (58, 0.0), (74, 8.5), (84, 8.8), (90, 8.6),
            (106, -7.5), (116, -8.2), (132, -7.8), (150, 0.0)])
    motion.gaze_to(ctx, F + 100, -0.3, 0.0, from_dx=0.28)
    motion.gaze_to(ctx, F + 146, 0.0, 0.0, from_dx=-0.3)
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='sweep'),
        F, [(0, 0.0), (60, 0.0), (78, 3.6), (92, 3.7), (110, -3.2),
            (134, -3.3), (154, 0.0)])
    # micro chin-up 1.5 deg at f150 (pride beat), ease out
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='chin'),
        F, [(0, 0.0), (148, 0.0), (156, -1.5), (170, -1.35), (186, 0.0)])
    # one slow weight transfer f210-250, almost no upper-body wobble
    _hip(ctx, [(F, 1.1, 0.0, 0.0), (F + 205, 1.1, 0.0, 0.0),
               (F + 228, 0.0, 0.0, -0.15), (F + 250, -1.15, 0.0, 0.0),
               (F + 278, -1.2, 0.0, 0.0), (F + 300, 1.1, 0.0, 0.0)],
         counter=0.55)
    # single thumb rub at f90 — the only hand event, calm otherwise
    _thumb_rub(ctx, F + 88, side='R', amp=7.0, cycles=2)
    motion.finger_relax(ctx, amp_deg=1.2, period=9.5)
    motion.head_micro_sway(ctx, amp_deg=0.3)   # half sway: stillness
    motion.loop_noise(ctx, lambda f, v: ctx.roll("CC_Base_Spine02", f, v,
                                                 layer='sway'),
                      amp=0.15, cycles=(2, 3), step=6)
    _arm_sway(ctx, amp=0.2)


@clip("idle_hands_together", "idle", 12.0, loop=True, framing='body',
      still_frame=0.5,
      description="Hands loosely held at pelvis, L OVER R (no interleave); "
                  "thumb rubs f90/f250, elbows breathe out 1 cm, micro-nods "
                  "f120/f300, one weight shift f180")
def idle_hands_together(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.0, amp=0.9, shoulders=0.55, phase=0.44)
    # hand-over-hand hold (L on top of R, Meta-avatar style): the deep
    # finger interleave read as a fused ball of fingertips on camera —
    # a loose stack with soft curls reads clean from every angle. R hand
    # sits slightly lower/deeper (forearm x), L drapes over its back.
    pose = {"CC_Base_L_Upperarm": (26.0, 40.0, -30.0),
            "CC_Base_R_Upperarm": (27.5, -40.0, 30.0),
            "CC_Base_L_Forearm": (52.0, 0.0, -10.0),
            "CC_Base_R_Forearm": (57.0, 0.0, 10.0),
            "CC_Base_L_Hand": (26.0, 0.0, -6.0),
            "CC_Base_R_Hand": (14.0, 0.0, 8.0)}
    for bone, (x, y, z) in pose.items():
        for f in (F, E):
            ctx.key_bone_axis(bone, f, 'x', x, layer='pose')
            ctx.key_bone_axis(bone, f, 'y', y, layer='pose')
            ctx.key_bone_axis(bone, f, 'z', z, layer='pose')
    # L fingers drape over the back of the R hand (moderate curl, no
    # fingertip jut: joint-3 kept shallow); R fingers relax underneath
    for s, base, j3 in (('L', 24.0, 0.35), ('R', 16.0, 0.5)):
        for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
            for j, ja in ((1, 1.0), (2, 0.75), (3, j3)):
                for f in (F, E):
                    ctx.finger_curl(s, fng, j, f, (base + i * 1.5) * ja,
                                    layer='pose')
        # thumbs tucked flat along the hands (render-calibrated): thumb x+
        # RAISES the thumb in this palm-down pose — adduction is Thumb1 z
        # (mirrored sign per side), with a small negative x to drop the base
        zadd = 25.0 if s == 'L' else -25.0
        for f in (F, E):
            ctx.finger_curl(s, "Thumb", 1, f, -10.0, layer='pose')
            ctx.key_bone_axis(f"CC_Base_{s}_Thumb1", f, 'z', zadd,
                              layer='pose_z')
            ctx.finger_curl(s, "Thumb", 2, f, 12.0, layer='pose')
            ctx.finger_curl(s, "Thumb", 3, f, 8.0, layer='pose')
    # attentive head, micro-nods 0.5 deg at f120 / f300
    for f0 in (120, 300):
        _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='nods'),
            F, [(f0 - 3, 0.0), (f0 + 2, 0.5), (f0 + 6, -0.1), (f0 + 10, 0.0)])
    # elbows drift out ~1 cm with the breath (period 4.0 = 3 cycles/12 s);
    # L and R in phase so the clasp never slides — R at 92 %
    n_keys = 24
    import math as _m
    for i in range(n_keys + 1):
        f = F + (E - F) * i / n_keys
        v = 1.2 * (0.5 - 0.5 * _m.cos(2 * _m.pi * (3.0 * i / n_keys + 0.44)))
        ctx.key_bone_axis("CC_Base_L_Upperarm", f, 'z', v, layer='elbow')
        ctx.key_bone_axis("CC_Base_R_Upperarm", f, 'z', -v * 0.92,
                          layer='elbow')
    # thumb rubs at f90 and f250 — unequal size and spacing on purpose
    _thumb_rub(ctx, F + 90, side='L', amp=8.0, cycles=2)
    _thumb_rub(ctx, F + 250, side='L', amp=6.0, cycles=3, period=10)
    # one weight shift at f180, return near the end
    _hip(ctx, [(F, 0.7, 0.0, 0.0), (F + 175, 0.7, 0.0, 0.0),
               (F + 196, -0.35, 0.0, -0.15), (F + 212, -1.1, 0.0, 0.0),
               (F + 296, -1.15, 0.0, 0.0), (F + 336, 0.7, 0.0, 0.0)],
         counter=0.8)
    motion.finger_relax(ctx, amp_deg=0.9, period=8.5)  # subtle inside clasp
    motion.head_micro_sway(ctx, amp_deg=0.4)


@clip("idle_hands_behind_back", "idle", 12.0, loop=True, framing='body',
      still_frame=0.44,
      description="Hands clasped at sacrum (L grips R wrist), chest open; "
                  "heel-toe rock f150 (feet articulate), head scan left "
                  "f60-110, visible re-grip f220, torso yaw drift")
def idle_hands_behind_back(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=4.6, amp=0.95, shoulders=0.9, phase=0.82)
    # behind-back pose (probe-solved), chest naturally open
    pose = {"CC_Base_L_Upperarm": (-45.0, -50.0, -38.0),
            "CC_Base_R_Upperarm": (-45.0, 50.0, 38.0),
            "CC_Base_L_Forearm": (25.0, 0.0, -45.0),
            "CC_Base_R_Forearm": (25.0, 0.0, 45.0),
            "CC_Base_L_Hand": (10.0, 0.0, -6.0),
            "CC_Base_R_Hand": (4.0, 0.0, 4.0),
            "CC_Base_Spine02": (-1.5, 0.0, 0.0)}
    for bone, (x, y, z) in pose.items():
        for f in (F, E):
            ctx.key_bone_axis(bone, f, 'x', x, layer='pose')
            ctx.key_bone_axis(bone, f, 'y', y, layer='pose')
            ctx.key_bone_axis(bone, f, 'z', z, layer='pose')
    # L fingers wrap the R wrist; R hand hangs relaxed
    for fng, a in (("Index", 38.0), ("Mid", 42.0), ("Ring", 45.0),
                   ("Pinky", 47.0)):
        for j, ja in ((1, 1.0), (2, 0.9), (3, 0.6)):
            for f in (F, E):
                ctx.finger_curl('L', fng, j, f, a * ja, layer='pose')
    for fng, a in (("Index", 10.0), ("Mid", 12.0), ("Ring", 14.0),
                   ("Pinky", 16.0)):
        for j in (1, 2, 3):
            for f in (F, E):
                ctx.finger_curl('R', fng, j, f, a * 0.8, layer='pose')
    for f in (F, E):
        ctx.finger_curl('L', "Thumb", 2, f, 20.0, layer='pose')
    # heel-toe rock at f150: heels rise (feet plantarflex + hip up), toes
    # stay planted (ToeBase counter-extends), settle over 12 f
    for s in ('L', 'R'):
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_Foot", f, 'x', v, layer='rock'),
            F, [(0, 0.0), (146, 0.0), (158, -5.0), (176, -4.6),
                (188, 0.6), (196, 0.0)])
        _ev(lambda f, v, ss=s: ctx.key_bone_axis(
            f"CC_Base_{ss}_ToeBase", f, 'x', v, layer='rock'),
            F, [(0, 0.0), (147, 0.0), (159, -4.0), (177, -3.7), (194, 0.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, 0.0, v),
                                            layer='rockz'),
        F, [(0, 0.0), (146, 0.0), (158, 1.0), (176, 0.9), (189, -0.15),
            (196, 0.0)])
    _ev(lambda f, v: ctx.key_bone_loc_world("Hip", f, (0.0, v, 0.0),
                                            layer='rocky'),
        F, [(0, 0.0), (147, 0.0), (159, -0.6), (177, -0.55), (196, 0.0)])
    # head scan left f60 (eyes lead 3 f), return f110
    motion.gaze_to(ctx, F + 57, 0.35, 0.03)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='scan'),
        F, [(0, 0.0), (60, 0.0), (72, 12.0), (88, 11.2), (104, 11.6),
            (110, 10.5), (124, -0.8), (132, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='scan'),
        F, [(0, 0.0), (62, 0.0), (75, 5.0), (108, 4.6), (127, 0.0)])
    motion.gaze_to(ctx, F + 106, 0.0, 0.0, from_dx=0.35)
    # visible re-grip squeeze at f220 (cascade, then settle deeper 1 deg)
    for i, fng in enumerate(("Index", "Mid", "Ring", "Pinky")):
        _ev(lambda f, v, fn=fng: ctx.finger_curl('L', fn, 2, f, v,
                                                 layer='ev_fingers'),
            F + 220 + i, [(0, 0.0), (6, 8.0), (10, 6.5), (16, 1.0),
                          (30, 1.0), (44, 0.0)])
    # slight continuous torso yaw drift +-1 deg
    motion.loop_noise(ctx, lambda f, v: ctx.yaw("CC_Base_Spine02", f, v,
                                                layer='sway'),
                      amp=1.0, cycles=(1, 2), step=6)
    _hip(ctx, [(F, 0.8, 0.0, 0.0), (F + 100, 0.9, 0.0, 0.0),
               (F + 240, 0.7, 0.0, 0.0), (F + 360, 0.8, 0.0, 0.0)],
         counter=0.7)
    motion.finger_relax(ctx, amp_deg=1.0, period=9.0)
    motion.head_micro_sway(ctx, amp_deg=0.45)


@clip("idle_looking_around", "idle", 14.0, loop=True, framing='body',
      still_frame=0.45,
      description="Three gaze targets (left-high f40, right f180, front "
                  "f330): eyes saccade first, head 3-5 f later, torso "
                  "only on the right look, blink masks each departure")
def idle_looking_around(ctx):
    F = ctx.frame_start
    motion.breathing(ctx, period=4.2, amp=0.9, phase=0.05)
    _arms_hang(ctx, fx=12.5)
    # --- target 1: LEFT-HIGH at f40 (eyes -> head; no torso) ---
    # r_offset=1: inter-eye lag capped at 1 f (QA wink-freeze defect class;
    # amplitude asymmetry inside add_blink is kept)
    motion.add_blink(ctx, F + 36, r_offset=1)
    motion.gaze_to(ctx, F + 40, 0.5, 0.32)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(0, 0.0), (44, 0.0), (56, 13.5), (90, 12.6), (130, 13.2),
            (170, 12.8)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='look'),
        F, [(0, 0.0), (44, 0.0), (56, -4.5), (100, -4.0), (170, -4.2)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(0, 0.0), (46, 0.0), (59, 5.5), (172, 5.2)])
    # fixation micro-drift on target 1
    _ev(lambda f, v: ctx.key_shape("Eye_L_Look_L", f, v, layer='fix'),
        F, [(70, 0.0), (95, 0.03), (130, -0.02), (160, 0.02)])
    _ev(lambda f, v: ctx.key_shape("Eye_R_Look_L", f, v, layer='fix'),
        F, [(71, 0.0), (96, 0.028), (131, -0.02), (161, 0.018)])
    # --- target 2: RIGHT at f180 (eyes -> head -> torso 2 f later) ---
    motion.add_blink(ctx, F + 174, r_offset=1)
    motion.gaze_to(ctx, F + 179, -0.55, -0.04, from_dx=0.5, from_dy=0.32)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(183, 12.8), (196, -15.5), (240, -14.4), (290, -15.0),
            (326, -14.6)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='look'),
        F, [(183, -4.2), (196, 1.2), (280, 0.8), (326, 1.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(185, 5.2), (198, -6.0), (328, -5.6)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine02", f, v, layer='torso'),
        F, [(0, 0.0), (185, 0.0), (200, -4.0), (300, -3.7), (334, -3.9),
            (352, -0.4), (360, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_Spine01", f, v, layer='torso'),
        F, [(0, 0.0), (187, 0.0), (203, -2.0), (330, -1.9), (356, 0.0)])
    # weight adjusts under the torso turn at f185
    _hip(ctx, [(F, 0.6, 0.0, 0.0), (F + 180, 0.6, 0.0, 0.0),
               (F + 205, -1.4, 0.0, -0.15), (F + 320, -1.5, 0.0, 0.0),
               (F + 352, -0.2, 0.0, 0.0), (F + 420, 0.6, 0.0, 0.0)],
         counter=0.8)
    # fixation drift on target 2
    _ev(lambda f, v: ctx.key_shape("Eye_L_Look_R", f, v, layer='fix'),
        F, [(215, 0.0), (245, 0.03), (285, -0.015), (315, 0.02)])
    _ev(lambda f, v: ctx.key_shape("Eye_R_Look_R", f, v, layer='fix'),
        F, [(216, 0.0), (246, 0.027), (286, -0.015), (316, 0.018)])
    # --- target 3: FRONT settle at f330 ---
    motion.add_blink(ctx, F + 326, r_offset=1)
    motion.gaze_to(ctx, F + 331, 0.0, 0.0, from_dx=-0.55, from_dy=-0.04)
    _ev(lambda f, v: ctx.yaw("CC_Base_Head", f, v, layer='look'),
        F, [(334, -14.6), (348, 1.1), (358, -0.2), (368, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='look'),
        F, [(334, 1.0), (350, -0.2), (366, 0.0)])
    _ev(lambda f, v: ctx.yaw("CC_Base_NeckTwist01", f, v, layer='look'),
        F, [(336, -5.6), (352, 0.3), (370, 0.0)])
    motion.finger_relax(ctx, amp_deg=1.5)
    motion.head_micro_sway(ctx, amp_deg=0.4)
    _arm_sway(ctx)


@clip("idle_phone", "idle", 12.0, loop=True, framing='body', still_frame=0.5,
      description="Phone loop body (enter/exit live in phone_raise/lower): "
                  "R hand holds phone at chest, head down 15 deg, gaze "
                  "down 0.4, irregular thumb scrolls f40/95/180/230, "
                  "chuckle f200 (facial hook: soft_smile)")
def idle_phone(ctx):
    F, E = ctx.frame_start, ctx.frame_end
    motion.breathing(ctx, period=3.9, amp=0.85, phase=0.66)
    # phone-hold pose (probe-solved): R hand at lower chest, palm up-ish
    pose = {"CC_Base_R_Upperarm": (30.0, -30.0, 40.0),
            "CC_Base_R_Forearm": (75.0, -20.0, -25.0),
            "CC_Base_R_Hand": (-10.0, 0.0, 10.0),
            "CC_Base_L_Upperarm": (8.0, -10.0, -58.0),   # relaxed hang
            "CC_Base_L_Forearm": (14.0, 0.0, -3.0)}
    for bone, (x, y, z) in pose.items():
        for f in (F, E):
            ctx.key_bone_axis(bone, f, 'x', x, layer='pose')
            ctx.key_bone_axis(bone, f, 'y', y, layer='pose')
            ctx.key_bone_axis(bone, f, 'z', z, layer='pose')
    # R fingers cradle the phone (thumb hovers free for scrolling);
    # L hand keeps a soft relaxed curl
    for fng, a in (("Index", 40.0), ("Mid", 48.0), ("Ring", 52.0),
                   ("Pinky", 55.0)):
        for j, ja in ((1, 1.0), (2, 1.1), (3, 0.6)):
            for f in (F, E):
                ctx.finger_curl('R', fng, j, f, a * ja, layer='pose')
    for fng, a in _FING:
        for j, ja in _JFALL:
            for f in (F, E):
                ctx.finger_curl('L', fng, j, f, a * ja, layer='pose')
    for f in (F, E):  # relaxed L thumb (R thumb is the scroll thumb)
        ctx.finger_curl('L', "Thumb", 1, f, _TH1, layer='pose')
        ctx.finger_curl('L', "Thumb", 2, f, _TH2, layer='pose')
        ctx.finger_curl('L', "Thumb", 3, f, _TH3, layer='pose')
    # head pitched WELL down (~21 deg through the chain), neck curved
    for f in (F, E):
        ctx.pitch("CC_Base_Head", f, 12.0, layer='pose')
        ctx.pitch("CC_Base_NeckTwist01", f, 5.0, layer='pose')
        ctx.pitch("CC_Base_NeckTwist02", f, 4.0, layer='pose')
        ctx.pitch("CC_Base_Spine02", f, 1.5, layer='pose')
        ctx.key_shape("Eye_L_Look_Down", f, 0.45, layer='gaze')
        ctx.key_shape("Eye_R_Look_Down", f, 0.45, layer='gaze')
    # reading micro-saccades (small L/R jumps at irregular gaps)
    for f0, dx in ((30, 0.06), (55, -0.05), (85, 0.08), (128, -0.04),
                   (162, 0.05), (238, 0.07), (268, -0.06), (300, 0.03)):
        for s in ('L', 'R'):
            _ev(lambda f, v, ss=s: ctx.key_shape(
                f"Eye_{ss}_Look_L", f, max(0.0, v), layer='read'),
                F + f0, [(0, 0.0), (2, dx if dx > 0 else 0.0),
                         (16, (dx if dx > 0 else 0.0) * 0.8), (20, 0.0)])
            _ev(lambda f, v, ss=s: ctx.key_shape(
                f"Eye_{ss}_Look_R", f, max(0.0, v), layer='read'),
                F + f0, [(0, 0.0), (2, -dx if dx < 0 else 0.0),
                         (16, (-dx if dx < 0 else 0.0) * 0.8), (20, 0.0)])
    # thumb scroll flicks at f40/95/180/230 — 12 deg over 4 f, 1 f overshoot
    for f0, a in ((40, 12.0), (95, 10.0), (180, 13.0), (230, 11.0)):
        for j, ja in ((2, 1.0), (3, 0.7)):
            _ev(lambda f, v, jj=j: ctx.finger_curl('R', "Thumb", jj, f, v,
                                                   layer='scroll'),
                F + f0, [(-2, 0.0), (2, -a * ja), (3, -a * ja * 0.85),
                         (10, a * 0.25 * ja), (16, 0.0)])
    # micro chuckle at f200: single chest bounce + head tip 1 deg
    _ev(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='chuckle'),
        F, [(0, 0.0), (196, 0.0), (200, 0.75), (204, -0.1), (210, 0.0)])
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='chuckle'),
        F, [(0, 0.0), (197, 0.0), (202, 1.0), (209, -0.15), (215, 0.0)])
    _ev(lambda f, v: ctx.clavicle_raise('R', f, v, layer='chuckle'),
        F, [(0, 0.0), (198, 0.0), (202, 0.5), (208, 0.0)])
    # head re-adjusts reading distance twice (slow, small)
    _ev(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='adjust'),
        F, [(0, 0.0), (116, 0.0), (130, -1.1), (150, -0.95), (168, 0.0),
            (276, 0.0), (290, 0.8), (312, 0.0)])
    # one weight shift at f150; left arm stays alive via relax + sway
    _hip(ctx, [(F, -0.9, 0.0, 0.0), (F + 145, -0.9, 0.0, 0.0),
               (F + 166, 0.2, 0.0, -0.15), (F + 182, 1.0, 0.0, 0.0),
               (F + 296, 1.05, 0.0, 0.0), (F + 336, -0.9, 0.0, 0.0)],
         counter=0.75)
    motion.finger_relax(ctx, amp_deg=1.6, period=7.5)
    motion.head_micro_sway(ctx, amp_deg=0.35)
    motion.loop_noise(ctx, lambda f, v: ctx.key_bone_axis(
        "CC_Base_L_Upperarm", f, 'x', v, layer='armsway'),
        amp=0.4, cycles=(1, 2), step=6)
