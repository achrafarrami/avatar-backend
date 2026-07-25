"""Eyes — 10 Tier-1 clips (owner: facial). Spec: animations/library_spec.json.

blink / double_blink / slow_blink        lid one-shots (runtime blink layer)
eye_left / eye_right / eye_up / eye_down directed saccades, end holding gaze
focus / lose_focus                       attention in / attention out
eye_dart                                 3-saccade nervous/scanning pattern

GAZE CALIBRATION (probed on this rig, verified by pixel-measuring iris
centroids in renders): the Eye_*_Look_* SHAPE keys move lid/socket skin
only; the IRIS does not move (CC_Base_Eye carries no horizontal/up look
keys). Gross gaze is the CC_Base_L/R_Eye BONES: local +x pitches the iris
DOWN, local +z yaws it toward the character's LEFT. Mapping (1.0 gaze unit
== the spec's key value): horizontal 16 deg/unit (left = +z), up 12
deg/unit (= -x), down 13 deg/unit (= +x). Look shape keys stay keyed as
the lid-follow layer.

Rubric: saccades ballistic 2-3f with 1-2% overshoot; fixation micro-drift;
lids follow vertical gaze; L/R never byte-identical; no HEAD keys here.
"""
from anim_framework.clips import clip
from anim_framework import motion

EYE_L, EYE_R = "CC_Base_L_Eye", "CC_Base_R_Eye"


def _aim(ctx, frame, dx, dy, r_scale=1.0, layer='eye_bones'):
    """Aim both irises via the eye bones. dx + = character's left,
    dy + = up, in gaze units (see calibration above)."""
    z = dx * 16.0
    x = -dy * (12.0 if dy >= 0 else 13.0)
    for bone, s in ((EYE_L, 1.0), (EYE_R, r_scale)):
        ctx.key_bone_axis(bone, frame, 'z', z * s, layer=layer)
        ctx.key_bone_axis(bone, frame, 'x', x * s, layer=layer)


# ---------------------------------------------------------------------------
# lid one-shots
# ---------------------------------------------------------------------------
@clip("blink", "eyes", 0.37, loop=False, framing='face', still_frame=0.27,
      description="Natural blink: close 3f / open 6f, R lid lags 1f, "
                  "conjugate eye dip, 0.05 squint rides the close")
def blink(ctx):
    f0 = ctx.frame_start
    motion.add_blink(ctx, f0, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1, eye_down=0.10)
    ctx.key_shape_lr("Eye_Squint_{S}", f0, 0.0, layer='squint',
                     r_offset=1, r_scale=0.88)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 3, 0.05, layer='squint',
                     r_offset=1, r_scale=0.88)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 9, 0.0, layer='squint',
                     r_offset=1, r_scale=0.88)


@clip("double_blink", "eyes", 0.6, loop=False, framing='face',
      still_frame=0.2,
      description="Reflexive doublet: full blink, lids only ~re-open to 0.12, "
                  "second blink at 80% with faster open, brow residue after")
def double_blink(ctx):
    f0 = ctx.frame_start
    for f, v, h in [(0, 0.0, 'AUTO_CLAMPED'), (3, 1.0, 'VECTOR'),
                    (4, 1.0, 'AUTO_CLAMPED'), (8, 0.12, 'AUTO_CLAMPED'),
                    (11, 0.80, 'VECTOR'), (12, 0.80, 'AUTO_CLAMPED'),
                    (17, 0.0, 'AUTO_CLAMPED')]:
        ctx.key_shape_lr("Eye_Blink_{S}", f0 + f, v, layer='blink',
                         r_offset=1, r_scale=0.96, handle=h)
    for f, v in [(0, 0.0), (4, 0.10), (8, 0.04), (12, 0.08), (18, 0.0)]:
        ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + f, v, layer='blink',
                         r_offset=1, r_scale=0.95)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 12, 0.0, layer='brow',
                     r_offset=1, r_scale=0.8)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 16, 0.05, layer='brow',
                     r_offset=1, r_scale=0.8)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 18, 0.04, layer='brow',
                     r_offset=1, r_scale=0.8)


@clip("slow_blink", "eyes", 0.8, loop=False, framing='face', still_frame=0.4,
      description="Heavy blink: close 8f, hold 3f, open 11f; brows drop 0.1 "
                  "and recover after the lids (tired/affectionate)")
def slow_blink(ctx):
    f0 = ctx.frame_start
    # QA batch-1: inter-eye lid offsets > 1f freeze-frame as WINKS on this
    # toon — offset capped at 1f (asymmetry kept via r_scale amplitude).
    for f, v, h in [(0, 0.0, 'AUTO_CLAMPED'), (8, 1.0, 'VECTOR'),
                    (11, 1.0, 'AUTO_CLAMPED'), (22, 0.0, 'AUTO_CLAMPED')]:
        ctx.key_shape_lr("Eye_Blink_{S}", f0 + f, v, layer='blink',
                         r_offset=1, r_scale=0.97, handle=h)
    for f, v in [(0, 0.0), (9, 0.12), (23, 0.0)]:
        ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + f, v, layer='blink',
                         r_offset=1, r_scale=0.95)
    for f, v in [(1, 0.0), (9, 0.10), (13, 0.10), (24, 0.0)]:
        ctx.key_shape_lr("Brow_Drop_{S}", f0 + f, v, layer='brow',
                         r_offset=1, r_scale=0.9)


# ---------------------------------------------------------------------------
# directed gaze one-shots (end holding the gaze; runtime crossfades out)
# ---------------------------------------------------------------------------
def _dir_gaze(ctx, pattern, keys, r_scale, dx=0.0, dy=0.0):
    """Directed conjugate gaze: iris via eye bones (dx/dy pick direction,
    scaled by each key's value), lid/socket follow via the Look keys."""
    for f, v in keys:
        ctx.key_shape_lr(pattern, ctx.frame_start + f, v, layer='gaze',
                         r_scale=r_scale)
        _aim(ctx, ctx.frame_start + f, dx * v, dy * v, r_scale=r_scale)


@clip("eye_left", "eyes", 0.5, loop=False, framing='face', still_frame=0.5,
      description="Ballistic saccade left to 0.8 (3f, 2% overshoot), "
                  "fixation micro-drift, ends holding")
def eye_left(ctx):
    _dir_gaze(ctx, "Eye_{S}_Look_L",
              [(0, 0.0), (3, 0.816), (5, 0.80), (8, 0.79),
               (11, 0.812), (13, 0.795), (15, 0.802)],
              r_scale=0.97, dx=+1.0)


@clip("eye_right", "eyes", 0.5, loop=False, framing='face', still_frame=0.5,
      description="Ballistic saccade right to 0.8; drift pattern differs "
                  "from eye_left (not a mirror)")
def eye_right(ctx):
    _dir_gaze(ctx, "Eye_{S}_Look_R",
              [(0, 0.0), (3, 0.814), (6, 0.80), (10, 0.786),
               (12, 0.808), (15, 0.797)],
              r_scale=0.95, dx=-1.0)


@clip("eye_up", "eyes", 0.5, loop=False, framing='face', still_frame=0.5,
      description="Saccade up to 0.7; upper lids lift with the gaze "
                  "(Eye_Wide 0.15, 1f behind), brows drift up over 6f")
def eye_up(ctx):
    _dir_gaze(ctx, "Eye_{S}_Look_Up",
              [(0, 0.0), (3, 0.714), (5, 0.70), (9, 0.69),
               (12, 0.706), (15, 0.697)],
              r_scale=0.96, dy=+1.0)
    for f, v in [(1, 0.0), (4, 0.15), (10, 0.14), (15, 0.15)]:
        ctx.key_shape_lr("Eye_Wide_{S}", ctx.frame_start + f, v,
                         layer='lids', r_offset=1, r_scale=0.9)
    for pat, amp in (("Brow_Raise_Inner_{S}", 0.10),
                     ("Brow_Raise_Outer_{S}", 0.08)):
        ctx.key_shape_lr(pat, ctx.at(0.0) + 2, 0.0, layer='brow',
                         r_offset=1, r_scale=0.9)
        ctx.key_shape_lr(pat, ctx.at(0.0) + 8, amp, layer='brow',
                         r_offset=1, r_scale=0.9)


@clip("eye_down", "eyes", 0.5, loop=False, framing='face', still_frame=0.5,
      description="Saccade down to 0.7; upper lids follow ~20% "
                  "(partial Blink, settles without bounce)")
def eye_down(ctx):
    _dir_gaze(ctx, "Eye_{S}_Look_Down",
              [(0, 0.0), (3, 0.71), (5, 0.70), (9, 0.708),
               (12, 0.692), (15, 0.70)],
              r_scale=0.96, dy=-1.0)
    for f, v in [(1, 0.0), (5, 0.22), (9, 0.20), (15, 0.20)]:
        ctx.key_shape_lr("Eye_Blink_{S}", ctx.frame_start + f, v,
                         layer='lids', r_offset=1, r_scale=0.95)


# ---------------------------------------------------------------------------
# attention
# ---------------------------------------------------------------------------
@clip("focus", "eyes", 1.0, loop=False, framing='face', still_frame=0.6,
      description="Converge slightly nasal (bones ~2.4deg), pupils contract "
                  "0.3, lids narrow 0.12, stiller fixation, re-fix at f22")
def focus(ctx):
    f0 = ctx.frame_start
    # nasal convergence: each iris rotates toward the nose via its bone,
    # lid/socket follow via the Look keys. Toward-nose = character-RIGHT
    # (-z) for the L eye, character-LEFT (+z) for the R eye.
    for f, v in [(0, 0.0), (4, 0.15), (17, 0.145), (21, 0.145),
                 (23, 0.158), (26, 0.15), (30, 0.152)]:
        ctx.key_shape("Eye_L_Look_R", f0 + f, v, layer='gaze')
        ctx.key_bone_axis(EYE_L, f0 + f, 'z', -v * 16.0, layer='eye_bones')
    for f, v in [(0, 0.0), (4, 0.14), (18, 0.137), (21, 0.137),
                 (23, 0.148), (27, 0.141), (30, 0.143)]:
        ctx.key_shape("Eye_R_Look_L", f0 + f, v, layer='gaze')
        ctx.key_bone_axis(EYE_R, f0 + f, 'z', v * 16.0, layer='eye_bones')
    ctx.key_shape("Eye_Pupil_Contract", f0 + 1, 0.0, layer='pupil')
    ctx.key_shape("Eye_Pupil_Contract", f0 + 9, 0.30, layer='pupil')
    ctx.key_shape("Eye_Pupil_Contract", f0 + 30, 0.30, layer='pupil')
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 2, 0.0, layer='lids',
                     r_offset=1, r_scale=0.92)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 12, 0.12, layer='lids',
                     r_offset=1, r_scale=0.92)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 30, 0.115, layer='lids',
                     r_offset=1, r_scale=0.92)
    ctx.key_shape_lr("Brow_Drop_{S}", f0 + 3, 0.0, layer='brow',
                     r_offset=2, r_scale=0.9)
    ctx.key_shape_lr("Brow_Drop_{S}", f0 + 13, 0.10, layer='brow',
                     r_offset=2, r_scale=0.9)


@clip("lose_focus", "eyes", 1.5, loop=False, framing='face', still_frame=0.75,
      description="Attention leaves: smooth-pursuit drift down-left over "
                  "25f, pupils dilate, lids go heavy, soft non-alerting blink")
def lose_focus(ctx):
    f0 = ctx.frame_start
    # smooth pursuit (the one legitimate SLOW eye move) down-left:
    # irises via bones along the same curve as the lid-follow keys
    for f, down, left in [(0, 0.0, 0.0), (8, 0.07, 0.02), (16, 0.16, 0.10),
                          (26, 0.28, 0.19), (45, 0.285, 0.19)]:
        ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + f, down, layer='gaze',
                         r_scale=0.95)
        ctx.key_shape_lr("Eye_{S}_Look_L", f0 + f, left, layer='gaze',
                         r_scale=0.95)
        _aim(ctx, f0 + f, dx=left, dy=-down, r_scale=0.95)
    ctx.key_shape("Eye_Pupil_Dilate", f0, 0.0, layer='pupil')
    ctx.key_shape("Eye_Pupil_Dilate", f0 + 26, 0.25, layer='pupil')
    ctx.key_shape("Eye_Pupil_Dilate", f0 + 45, 0.25, layer='pupil')
    ctx.key_shape_lr("Eye_Blink_{S}", f0, 0.0, layer='lid_tone',
                     r_offset=1, r_scale=0.94)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 30, 0.12, layer='lid_tone',
                     r_offset=1, r_scale=0.94)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 45, 0.12, layer='lid_tone',
                     r_offset=1, r_scale=0.94)
    motion.add_blink(ctx, f0 + 34, amp=0.75, close=3, hold=1, open_=6,
                     r_offset=1, eye_down=0.05)


@clip("eye_dart", "eyes", 1.2, loop=False, framing='face', still_frame=0.42,
      description="3 unequal ballistic darts (right, up-left, down-right) "
                  "with unequal dwells; lids react on vertical legs only")
def eye_dart(ctx):
    f0 = ctx.frame_start
    # legs (dx + = character's left); dwell gaps unequal by design.
    # Iris: eye bones. Lid/socket follow: framework gaze_to (Look keys).
    motion.gaze_to(ctx, f0 + 2, -0.50, 0.04, 0.0, 0.0, dart=2)
    _aim(ctx, f0 + 2, 0.0, 0.0)
    _aim(ctx, f0 + 4, -0.50, 0.04, r_scale=0.97)
    ctx.key_shape_lr("Eye_{S}_Look_R", f0 + 9, 0.48, layer='gaze',
                     r_scale=0.97)
    _aim(ctx, f0 + 9, -0.48, 0.06, r_scale=0.97)      # fixation micro-drift
    motion.gaze_to(ctx, f0 + 15, 0.42, 0.42, -0.48, 0.05, dart=2)
    _aim(ctx, f0 + 15, -0.48, 0.06, r_scale=0.97)
    _aim(ctx, f0 + 17, 0.42, 0.42, r_scale=0.96)
    ctx.key_shape_lr("Eye_{S}_Look_Up", f0 + 22, 0.44, layer='gaze',
                     r_scale=0.96)
    _aim(ctx, f0 + 22, 0.40, 0.44, r_scale=0.96)      # drift in dwell 2
    motion.gaze_to(ctx, f0 + 26, -0.28, -0.21, 0.40, 0.44, dart=2)
    _aim(ctx, f0 + 26, 0.40, 0.44, r_scale=0.96)
    _aim(ctx, f0 + 28, -0.28, -0.21, r_scale=0.95)
    motion.gaze_to(ctx, f0 + 34, 0.02, -0.02, -0.28, -0.21, dart=2)
    _aim(ctx, f0 + 34, -0.28, -0.21, r_scale=0.95)
    _aim(ctx, f0 + 36, 0.02, -0.02)
    # lids: micro-react on the vertical components only
    for f, v in [(15, 0.0), (18, 0.08), (24, 0.0)]:
        ctx.key_shape_lr("Eye_Wide_{S}", f0 + f, v, layer='lids',
                         r_offset=1, r_scale=0.9)
    for f, v in [(26, 0.0), (29, 0.07), (33, 0.0)]:
        ctx.key_shape_lr("Eye_Blink_{S}", f0 + f, v, layer='lids',
                         r_offset=1, r_scale=0.9)
