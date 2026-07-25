"""Breathing layer clips (Tier 1, owner: body).

Four ADDITIVE loops per library_spec.json: breathing_normal / deep /
excited / tired. Hand-authored curves (not motion.breathing) so every
channel is EXACTLY zero at both loop boundaries — the additive-stacking
contract — while keeping the spec beats: inhale faster than exhale,
clavicles lagging the chest, per-clip signatures (settle dip, sigh slump,
clavicular attack). Channel budget per spec `layers`: spine (01/02),
clavicles, slight neck/head. Shoulders never translate — clavicle
rotation only. L/R clavicles differ in lag AND amplitude (asymmetry rule).

These double as pure layers for additive runtimes; base clips bake their
own breath via motion.breathing (different phases) — see idle.py.
"""
from anim_framework.clips import clip


def _curve(fn, f0, pts):
    """Key a list of (frame_offset, value) through `fn(frame, value)`."""
    for off, v in pts:
        fn(f0 + off, v)


@clip("breathing_normal", "breathing", 4.5, loop=True, framing='bust',
      still_frame=0.38,
      description="Additive normal breath, one 4.5 s cycle (~13/min); "
                  "inhale 40%/exhale 60%, clavicles lag chest 3-4 f, "
                  "zero-delta seams")
def breathing_normal(ctx):
    F = ctx.frame_start
    # chest: spine02 extension (-x = inhale), rounded top, slower release
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='breath'),
           F, [(0, 0.0), (22, -0.30), (46, -0.74), (56, -0.80),
               (80, -0.55), (105, -0.22), (135, 0.0)])
    # clavicles ride the chest with lag; R weaker and later than L
    _curve(lambda f, v: ctx.clavicle_raise('L', f, v, layer='breath'),
           F, [(0, 0.0), (24, 0.16), (57, 0.50), (92, 0.30),
               (112, 0.12), (135, 0.0)])
    _curve(lambda f, v: ctx.clavicle_raise('R', f, v, layer='breath'),
           F, [(0, 0.0), (27, 0.13), (61, 0.44), (95, 0.26),
               (115, 0.10), (135, 0.0)])


@clip("breathing_deep", "breathing", 6.0, loop=True, framing='bust',
      still_frame=0.45,
      description="Additive deep breath, 6 s cycle; fuller ribcage "
                  "(spine01+02), head rides inhale top, below-neutral "
                  "settle dip at f150, zero-delta seams")
def breathing_deep(ctx):
    F = ctx.frame_start
    # belly leads (spine01 fuller), chest follows slightly behind
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, layer='breath'),
           F, [(0, 0.0), (30, -0.55), (65, -1.32), (83, -1.50),
               (115, -1.05), (145, -0.45), (152, 0.05), (165, 0.02),
               (180, 0.0)])
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='breath'),
           F, [(0, 0.0), (33, -0.35), (68, -0.88), (85, -1.00),
               (118, -0.68), (147, -0.28), (154, 0.035), (168, 0.015),
               (180, 0.0)])
    # clavicles rise then drop, 3-5 f behind the chest, tiny negative settle
    _curve(lambda f, v: ctx.clavicle_raise('L', f, v, layer='breath'),
           F, [(0, 0.0), (40, 0.35), (86, 0.90), (120, 0.50),
               (152, -0.06), (168, -0.02), (180, 0.0)])
    _curve(lambda f, v: ctx.clavicle_raise('R', f, v, layer='breath'),
           F, [(0, 0.0), (44, 0.30), (91, 0.81), (124, 0.44),
               (156, -0.05), (171, -0.02), (180, 0.0)])
    # slight head pitch-back rides the TOP of the inhale (<=1 deg cap)
    _curve(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='breath'),
           F, [(0, 0.0), (55, -0.12), (85, -0.50), (125, -0.15),
               (165, 0.0), (180, 0.0)])
    _curve(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='breath'),
           F, [(0, 0.0), (57, -0.04), (87, -0.15), (128, -0.05),
               (168, 0.0), (180, 0.0)])


@clip("breathing_excited", "breathing", 2.6, loop=True, framing='bust',
      still_frame=0.42,
      description="Additive fast shallow breath (~23/min), clavicular "
                  "dominant, sharp 3-4 f inhale attack, zero-delta seams")
def breathing_excited(ctx):
    F = ctx.frame_start
    # shallow chest — clavicles carry MORE than the spine (excitement
    # breathes high); spine amplitude deliberately under breathing_normal
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='breath'),
           F, [(0, 0.0), (4, -0.28), (16, -0.50), (33, -0.60),
               (52, -0.35), (66, -0.12), (78, 0.0)])
    _curve(lambda f, v: ctx.clavicle_raise('L', f, v, layer='breath'),
           F, [(0, 0.0), (5, 0.34), (20, 0.62), (36, 0.70),
               (58, 0.30), (78, 0.0)])
    _curve(lambda f, v: ctx.clavicle_raise('R', f, v, layer='breath'),
           F, [(0, 0.0), (7, 0.29), (23, 0.55), (38, 0.64),
               (61, 0.26), (78, 0.0)])
    # tiny sympathetic head bob (<= 0.3 deg)
    _curve(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='breath'),
           F, [(0, 0.0), (6, 0.22), (20, 0.05), (38, -0.10),
               (60, 0.04), (78, 0.0)])


@clip("breathing_tired", "breathing", 7.0, loop=True, framing='bust',
      still_frame=0.75,
      description="Additive tired sigh-breath: two-stage catch inhale, "
                  "8 f pause, collapsing exhale with shoulders slumping "
                  "1.5 deg below neutral + head drop, slow crawl recovery")
def breathing_tired(ctx):
    F = ctx.frame_start
    # two-stage (catch) inhale f0-45, pause to f53, collapse to ~f165,
    # nonlinear crawl back to zero by f210
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine01", f, v, layer='breath'),
           F, [(0, 0.0), (18, -0.78), (26, -0.82), (45, -1.30),
               (53, -1.28), (85, -0.60), (120, -0.05), (150, 0.28),
               (165, 0.32), (185, 0.18), (200, 0.06), (210, 0.0)])
    _curve(lambda f, v: ctx.pitch("CC_Base_Spine02", f, v, layer='breath'),
           F, [(0, 0.0), (20, -0.55), (28, -0.58), (46, -0.94),
               (54, -0.92), (88, -0.42), (122, -0.02), (152, 0.22),
               (167, 0.25), (188, 0.13), (202, 0.04), (210, 0.0)])
    # shoulders: rise with inhale then slump an EXTRA 1.5 deg below rest —
    # the slump IS the read; R lags 4 f at 90 %
    _curve(lambda f, v: ctx.clavicle_raise('L', f, v, layer='breath'),
           F, [(0, 0.0), (20, 0.62), (27, 0.66), (46, 1.05), (54, 1.00),
               (95, 0.20), (130, -0.90), (162, -1.50), (185, -0.90),
               (200, -0.35), (210, 0.0)])
    _curve(lambda f, v: ctx.clavicle_raise('R', f, v, layer='breath'),
           F, [(0, 0.0), (24, 0.55), (31, 0.59), (50, 0.95), (58, 0.90),
               (99, 0.16), (134, -0.80), (166, -1.35), (188, -0.80),
               (203, -0.30), (210, 0.0)])
    # head sinks with the collapse (0.8 deg, under the 1.5 sleep cap)
    _curve(lambda f, v: ctx.pitch("CC_Base_Head", f, v, layer='breath'),
           F, [(0, 0.0), (45, -0.22), (53, -0.20), (110, 0.35),
               (163, 0.80), (188, 0.45), (210, 0.0)])
    _curve(lambda f, v: ctx.pitch("CC_Base_NeckTwist01", f, v, layer='breath'),
           F, [(0, 0.0), (47, -0.07), (55, -0.06), (112, 0.11),
               (165, 0.24), (190, 0.13), (210, 0.0)])
