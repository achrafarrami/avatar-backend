"""Facial expressions — 6 Tier-1 clips (owner: facial).

neutral_alive  10 s loop   the anti-frozen default face (aliveness benchmark)
happy           2 s        Duchenne smile (cheeks BEFORE corners)
soft_smile      2.5 s      closed-lip warmth (lower lid carries it)
surprised       1.2 s      speed is the read; brows -> lids -> jaw order
thinking        4 s loop   gaze aversion up-left + lip/jaw activity cycles
sad             3 s        slow onset, oblique brows, face before head

Spec: animations/library_spec.json (beats/quality gates). Head motion is
keyed directly here within the <=2.5 deg facial-clip allowance; the full
body hooks (e.g. sad 5 deg sink) stay noted in clip descriptions.
Mouth opening always drives the JawRoot BONE (ctx.jaw_open) + Jaw_Open key
at angle/15 — the key alone leaves toon lips closed (README jaw standard).
"""
from anim_framework.clips import clip
from anim_framework import motion

EYE_L, EYE_R = "CC_Base_L_Eye", "CC_Base_R_Eye"


def _aim(ctx, frame, dx, dy, r_scale=1.0, layer='eye_bones'):
    """Aim both irises via the eye bones (the Look SHAPE keys move lids
    only — probed calibration, see eyes.py). dx + = character's left,
    dy + = up; horizontal 16 deg/unit (+z left), up 12 (-x), down 13 (+x)."""
    z = dx * 16.0
    x = -dy * (12.0 if dy >= 0 else 13.0)
    for bone, s in ((EYE_L, 1.0), (EYE_R, r_scale)):
        ctx.key_bone_axis(bone, frame, 'z', z * s, layer=layer)
        ctx.key_bone_axis(bone, frame, 'x', x * s, layer=layer)


def _event_lr(ctx, pattern, f_start, rise, fall, amp, layer,
              r_offset=1, r_scale=0.85):
    """Transient bilateral micro-event: 0 -> amp -> 0 (asymmetric L/R)."""
    ctx.key_shape_lr(pattern, f_start, 0.0, layer, r_offset=r_offset,
                     r_scale=r_scale)
    ctx.key_shape_lr(pattern, f_start + rise, amp, layer, r_offset=r_offset,
                     r_scale=r_scale)
    ctx.key_shape_lr(pattern, f_start + rise + fall, 0.0, layer,
                     r_offset=r_offset, r_scale=r_scale)


# ---------------------------------------------------------------------------
@clip("neutral_alive", "facial", 10.0, loop=True, framing='face',
      still_frame=0.47,
      description="Anti-frozen default face: irregular sub-expression events "
                  "+ breathing lid tone; no baked blinks (runtime layer)")
def neutral_alive(ctx):
    f0 = ctx.frame_start
    m = 'micro'
    # --- irregular event schedule (spec frames; all deltas <= 0.08) ------
    _event_lr(ctx, "Brow_Raise_Inner_{S}", f0 + 29, 6, 9, 0.04, m,
              r_offset=2, r_scale=0.75)                      # f35 brow
    _event_lr(ctx, "Nose_Sneer_{S}", f0 + 84, 3, 5, 0.02, m,
              r_offset=1, r_scale=0.8)                       # f88 nostril
    # f140 unilateral lip compression, 8f in / 14f out
    for f, v in [(132, 0.0), (140, 0.07), (154, 0.0)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, m)
        ctx.key_shape("Mouth_Press_R", f0 + f + 2, v * 0.7, m)
    _event_lr(ctx, "Cheek_Raise_{S}", f0 + 195, 5, 8, 0.05, m,
              r_offset=2, r_scale=0.6)                       # f200 cheek
    _event_lr(ctx, "Nose_Sneer_{S}", f0 + 251, 3, 6, 0.018, m,
              r_offset=1, r_scale=0.85)                      # f255 nostril
    # f260 swallow suggestion: lip press + tiny jaw (bone + key, 12f)
    for f, v in [(254, 0.0), (260, 0.08), (266, 0.0)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'swallow')
        ctx.key_shape("Mouth_Press_R", f0 + f + 1, v * 0.85, 'swallow')
    for f, d in [(254, 0.0), (260, 0.45), (266, 0.0)]:
        ctx.jaw_open(f0 + f, d)
    for f, v in [(254, 0.0), (260, 0.03), (266, 0.0)]:
        ctx.key_shape("Jaw_Open", f0 + f, v, 'swallow')
    # --- continuous tone (exactly periodic => seamless) ------------------
    # lid tone breathes 0.02-0.05, L/R decorrelated
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Eye_Blink_L", f, 0.035 + v, 'lid_tone'),
        amp=0.015, cycles=(2, 3), step=5)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Eye_Blink_R", f, 0.033 + v, 'lid_tone'),
        amp=0.013, cycles=(3, 4), step=5)
    # sub-visible brow drift so no span is ever static
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_L", f, 0.015 + v, 'brow_drift'),
        amp=0.012, cycles=(2, 5), step=6)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_R", f, 0.013 + v, 'brow_drift'),
        amp=0.010, cycles=(3, 5), step=6)


# ---------------------------------------------------------------------------
@clip("happy", "facial", 2.0, loop=False, framing='face', still_frame=0.5,
      description="Duchenne smile: cheeks f0-6 FIRST, corners +2f, squint "
                  "0.3 completes; alive hold with corner waver + cheek "
                  "re-raise; ends holding")
def happy(ctx):
    f0 = ctx.frame_start
    # cheeks FIRST (Duchenne order), left leads
    for f, v in [(0, 0.0), (6, 0.45), (29, 0.43), (34, 0.51),
                 (41, 0.45), (60, 0.44)]:                    # re-raise @f35
        ctx.key_shape("Cheek_Raise_L", f0 + f, v, 'cheeks')
    for f, v in [(1, 0.0), (8, 0.40), (40, 0.39), (60, 0.38)]:
        ctx.key_shape("Cheek_Raise_R", f0 + f, v, 'cheeks')
    # corners follow 2f behind cheeks; L 1.0 : R 0.85 ratio
    for f, v in [(2, 0.0), (10, 0.62), (60, 0.60)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(3, 0.0), (12, 0.53), (60, 0.51)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    # eye squint completes it (dead-eye smile = uncanny #1)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 4, 0.0, 'squint',
                     r_offset=1, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 12, 0.30, 'squint',
                     r_offset=1, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 60, 0.29, 'squint',
                     r_offset=1, r_scale=0.9)
    # brows soften/lift a touch
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 6, 0.0, 'brow',
                     r_offset=2, r_scale=0.85)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 16, 0.08, 'brow',
                     r_offset=2, r_scale=0.85)
    # the hold is ALIVE: corner amplitude wavers +-0.05
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_L", f, v, 'waver'),
        start=f0 + 12, end=f0 + 60, amp=0.05, cycles=(2, 3), step=4,
        fade=0.2)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_R", f, v, 'waver'),
        start=f0 + 12, end=f0 + 60, amp=0.04, cycles=(3, 4), step=4,
        fade=0.2)


# ---------------------------------------------------------------------------
@clip("soft_smile", "facial", 2.5, loop=False, framing='face',
      still_frame=0.5,
      description="Closed-lip warmth: slow 12f onset to 0.35, lower-lid "
                  "raise 0.15, smile breathes (fade-and-return at f45)")
def soft_smile(ctx):
    f0 = ctx.frame_start
    # corners: slow onset, one corner 20% stronger; micro fade @f45, return
    for f, v in [(0, 0.0), (12, 0.35), (38, 0.34), (45, 0.28),
                 (56, 0.34), (75, 0.33)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(1, 0.0), (14, 0.28), (46, 0.23), (58, 0.27),
                 (75, 0.27)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    # cheeks (gentle) — still before corners' peak
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 1, 0.0, 'cheeks',
                     r_offset=1, r_scale=0.85)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 13, 0.20, 'cheeks',
                     r_offset=1, r_scale=0.85)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 75, 0.19, 'cheeks',
                     r_offset=1, r_scale=0.85)
    # warmth lives in the lower lid: squint-as-lid-raise
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 3, 0.0, 'lids',
                     r_offset=2, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 16, 0.15, 'lids',
                     r_offset=2, r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 75, 0.145, 'lids',
                     r_offset=2, r_scale=0.9)


# ---------------------------------------------------------------------------
@clip("surprised", "facial", 1.2, loop=False, framing='face',
      still_frame=0.35,
      description="Speed is the read: 1deg forward antic, brows 0.9 in 3f "
                  "(3% overshoot), lids stagger 1f, jaw 7.5deg lags 1f, "
                  "head jerks back 2.5deg; brow tremor in hold")
def surprised(ctx):
    f0 = ctx.frame_start
    head = "CC_Base_Head"
    # micro forward anticipation, then the jerk back (<=2.5 deg allowance)
    for f, d in [(0, 0.0), (2, 1.0), (7, -2.5), (11, -2.2), (29, -1.8),
                 (36, -1.6)]:
        ctx.pitch(head, f0 + f, d, layer='head')
    # brows rocket up with 3% overshoot (L leads, R -4% 1f later)
    for pat, amp in (("Brow_Raise_Inner_{S}", 0.90),
                     ("Brow_Raise_Outer_{S}", 0.80)):
        ctx.key_shape_lr(pat, f0 + 2, 0.0, 'brow', r_offset=1, r_scale=0.96)
        ctx.key_shape_lr(pat, f0 + 5, amp * 1.03, 'brow',
                         r_offset=1, r_scale=0.96)
        ctx.key_shape_lr(pat, f0 + 8, amp, 'brow', r_offset=1, r_scale=0.96)
        ctx.key_shape_lr(pat, f0 + 30, amp, 'brow', r_offset=1, r_scale=0.96)
        ctx.key_shape_lr(pat, f0 + 36, amp * 0.93, 'brow',
                         r_offset=1, r_scale=0.96)
    # lids: peak 1f after the brows (staggered, not identical curves)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 3, 0.0, 'lids',
                     r_offset=1, r_scale=0.95)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 6, 0.82, 'lids',
                     r_offset=1, r_scale=0.95)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 9, 0.78, 'lids',
                     r_offset=1, r_scale=0.95)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 30, 0.78, 'lids',
                     r_offset=1, r_scale=0.95)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 36, 0.72, 'lids',
                     r_offset=1, r_scale=0.95)
    # jaw drops with 1f lag (heavier than brows): BONE opens, key shapes lips
    for f, d in [(3, 0.0), (8, 7.5), (30, 7.2), (36, 6.8)]:
        ctx.jaw_open(f0 + f, d)
    for f, v in [(3, 0.0), (8, 0.50), (30, 0.48), (36, 0.45)]:
        ctx.key_shape("Jaw_Open", f0 + f, v, 'jaw')
    # hold micro tremor on the brows (never a frozen apex)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_L", f, v, 'tremor'),
        start=f0 + 9, end=f0 + 30, amp=0.02, cycles=(3, 5), step=3,
        fade=0.2)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_R", f, v, 'tremor'),
        start=f0 + 9, end=f0 + 30, amp=0.017, cycles=(2, 5), step=3,
        fade=0.2)


# ---------------------------------------------------------------------------
@clip("thinking", "facial", 4.0, loop=True, framing='face', still_frame=0.5,
      description="Loop: gaze held up-left with recompute micro-shifts, "
                  "furrow breathes 0.25-0.35, purse->press lip cycles, jaw "
                  "slide at f60, micro nod at f94")
def thinking(ctx):
    f0 = ctx.frame_start
    # gaze aversion up-LEFT, held for the whole loop (crossfade-in covers
    # the entry saccade); micro-shifts at f40/f75 = recomputing
    for f, up, left in [(0, 0.45, 0.30), (39, 0.48, 0.27), (54, 0.45, 0.30),
                        (74, 0.42, 0.33), (88, 0.45, 0.30)]:
        ctx.key_shape_lr("Eye_{S}_Look_Up", f0 + f, up, 'gaze', r_scale=0.96)
        ctx.key_shape_lr("Eye_{S}_Look_L", f0 + f, left, 'gaze', r_scale=0.96)
        _aim(ctx, f0 + f, dx=left, dy=up, r_scale=0.96)
    # lids follow the up-gaze a touch
    ctx.key_shape_lr("Eye_Wide_{S}", f0, 0.08, 'lids', r_scale=0.9)
    # furrow baseline 0.3, breathing 0.25-0.35 (exactly periodic)
    ctx.key_shape("Brow_Drop_L", f0, 0.30, 'furrow')
    ctx.key_shape("Brow_Drop_R", f0, 0.27, 'furrow')
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_L", f, v, 'furrow_breathe'),
        amp=0.05, cycles=(2, 3), step=5)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_R", f, v, 'furrow_breathe'),
        amp=0.04, cycles=(3, 4), step=5)
    # lip activity cycle 1: purse f30-55 (rounded, asymmetric)
    for pat, amp in (("Mouth_Pucker_Up_{S}", 0.20),
                     ("Mouth_Pucker_Down_{S}", 0.12)):
        for f, s in [(28, 0.0), (36, 1.0), (50, 0.9), (57, 0.0)]:
            ctx.key_shape_lr(pat, f0 + f, amp * s, 'lips',
                             r_offset=1, r_scale=0.85)
    # lip activity cycle 2: press f70-90
    for f, s in [(68, 0.0), (75, 1.0), (86, 0.85), (93, 0.0)]:
        ctx.key_shape_lr("Mouth_Press_{S}", f0 + f, 0.15 * s, 'lips',
                         r_offset=1, r_scale=0.85)
    # jaw slides sideways at f60, held ~20f (chewing on the thought)
    for f, v in [(55, 0.0), (62, 0.15), (80, 0.14), (92, 0.0)]:
        ctx.key_shape("Jaw_L", f0 + f, v, 'jaw')
    # micro nod (head <=2.5 deg, off-axis wobble, inside loop margins)
    for f, d in [(87, 0.0), (93, 1.3), (101, 0.0)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='nod')
    for f, d in [(89, 0.0), (95, -0.35), (103, 0.0)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='nod')


# ---------------------------------------------------------------------------
@clip("sad", "facial", 3.0, loop=False, framing='face', still_frame=0.75,
      description="Slow 20f onset: oblique brows 0.6, corners 0.4 lag 4f, "
                  "heavy lids, gaze drops; head sinks 2.5deg LAST (body hook "
                  "completes to 5deg); slow blink f60, lip tremble f75")
def sad(ctx):
    f0 = ctx.frame_start
    # oblique brows: inner raise + pinch, slow (sadness arrives)
    for f, v in [(0, 0.0), (21, 0.60), (89, 0.60)]:
        ctx.key_shape("Brow_Raise_Inner_L", f0 + f, v, 'brow')
    for f, v in [(2, 0.0), (23, 0.55), (89, 0.55)]:
        ctx.key_shape("Brow_Raise_Inner_R", f0 + f, v, 'brow')
    ctx.key_shape_lr("Brow_Compress_{S}", f0 + 3, 0.0, 'brow',
                     r_offset=2, r_scale=0.87)
    ctx.key_shape_lr("Brow_Compress_{S}", f0 + 23, 0.15, 'brow',
                     r_offset=2, r_scale=0.87)
    # corners drop with 4f lag, asymmetric frown
    for f, v in [(5, 0.0), (25, 0.40), (89, 0.40)]:
        ctx.key_shape("Mouth_Frown_L", f0 + f, v, 'mouth')
    for f, v in [(7, 0.0), (27, 0.34), (89, 0.34)]:
        ctx.key_shape("Mouth_Frown_R", f0 + f, v, 'mouth')
    # heavy lids + gaze drop
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 6, 0.0, 'lids',
                     r_offset=1, r_scale=0.94)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 24, 0.30, 'lids',
                     r_offset=1, r_scale=0.94)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 89, 0.30, 'lids',
                     r_offset=1, r_scale=0.94)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 9, 0.0, 'gaze', r_scale=0.95)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 20, 0.30, 'gaze',
                     r_scale=0.95)
    _aim(ctx, f0 + 9, 0.0, 0.0, r_scale=0.95)
    _aim(ctx, f0 + 20, 0.0, -0.30, r_scale=0.95)
    # head sinks LAST (starts after the face is committed); 2.5deg is the
    # facial allowance — body layer completes the 5deg spec hook
    for f, d in [(19, 0.0), (50, 2.5), (89, 2.5)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(22, 0.0), (52, 0.4), (89, 0.4)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')  # never on-axis
    # one slow heavy blink (sums over the 0.3 lid baseline -> full closure)
    # QA batch-1: inter-eye offset capped at 1f (2f froze as a wink)
    motion.add_blink(ctx, f0 + 58, amp=0.7, close=6, hold=2, open_=9,
                     r_offset=1, eye_down=0.06)
    # lip tremble near f75: uneven amplitudes and spacing (not a metronome)
    for f, v in [(72, 0.0), (74, 0.05), (76, 0.01), (79, 0.03),
                 (81, 0.0), (85, 0.045), (88, 0.0)]:
        ctx.key_shape("Mouth_Frown_L", f0 + f, v, 'tremble')
    # brow micro-waver so the long hold never freezes
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_L", f, v, 'waver'),
        start=f0 + 25, end=f0 + 89, amp=0.02, cycles=(2, 3), step=5,
        fade=0.15)
