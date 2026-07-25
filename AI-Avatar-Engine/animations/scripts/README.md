# Animation framework — authoring guide

Procedural clip library for the meta avatar (CC3+ toon rig). You write a
**recipe** (a Python function against `ClipContext`), the framework turns it
into Bézier-keyed Blender actions on NLA tracks, and the exporter ships every
clip as a **named glTF animation**.

```
scripts/
  anim_framework/   rig.py keying.py motion.py clips.py   (the framework)
  clips/            *.py recipe modules (yours go here)
  build_animations.py  render_previews.py  export_animations.py
  verify_animations.py  probe_pose.py
```

## CLI (Blender 5.2, always headless)

```bash
B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
"$B" --background --python scripts/build_animations.py  -- all        # or: cid [cid ...]
"$B" --background --python scripts/render_previews.py   -- all        # [--no-mp4]
"$B" --background --python scripts/export_animations.py               # [--skip-fbx] [--only-full]
"$B" --background --python scripts/verify_animations.py -- exports/avatar_animated_meta_male.glb
"$B" --background --python scripts/probe_pose.py -- nod_small 20 Head L_Hand   # world positions (m)
```

`build_animations.py` creates `blender/anim_master_meta_male.blend` from the
template on first run (30 fps forced, template never touched) and afterwards
**rebuilds only the clip ids you pass** — safe to iterate on one clip.
Previews land in `previews/<clip_id>/` (front/side/persp/wireframe/strip.png,
`<clip_id>.mp4` H.264, meta.json with fps + frame_count — QA reads these).

## Writing a clip

```python
# scripts/clips/my_clips.py
from anim_framework.clips import clip
from anim_framework import motion

@clip("head_shake_no", "gesture", 2.2, loop=False, framing='face',
      description="Emphatic no: 3 diminishing head shakes")
def head_shake_no(ctx):
    motion.breathing(ctx, amp=0.5, phase=ctx.rng.random())   # bake a light breath layer
    for i, (t, deg) in enumerate([(0.35, -9), (0.7, 8), (1.0, -5.5),
                                  (1.3, 3), (1.7, 0)]):
        ctx.yaw("CC_Base_Head", ctx.at(t), deg, layer='shake')
        ctx.yaw("CC_Base_NeckTwist01", ctx.at(t) + 2, deg * 0.35, layer='shake')
    ctx.yaw("CC_Base_Head", ctx.at(0.0), 0.0, layer='shake')
    motion.add_blink(ctx, ctx.at(1.5))                        # blink on the settle
```

`@clip(cid, category, seconds, loop=, framing='face'|'bust'|'body',
still_frame=, description=)`. `category` drives per-category GLB grouping
(idle/gesture/emotion/...). `ctx.at(seconds)` -> frame; `ctx.sec(s)` -> frame
count; `ctx.rng` is a per-clip seeded RNG (deterministic rebuilds).

### Keying API (ctx.*)

- `key_shape(name, frame, value, layer=, interp=, handle=)` — fans out
  automatically to EVERY mesh carrying that key (body, eyebrows, tearline,
  occlusion, teeth, tongue, eye). Names resolve against the union of all
  meshes: `Eye_Pupil_Dilate`/`Contract` live ONLY on the eye mesh, visemes on
  body+eyebrows(+tongue/teeth followers), and names are case-sensitive
  (`V_Tongue_up`!). Per-mesh availability map:
  `blender/key_inventory.json` (regenerated on every build).
- `key_shape_lr("Eye_Blink_{S}", frame, v, r_offset=1, r_scale=0.95)` — L/R
  pair with built-in asymmetry ({S} -> L/R).
- `key_bone_axis(bone, frame, 'x'|'y'|'z', degrees, layer=)` — local-axis
  rotation in degrees; layers on the same bone SUM at flush and become
  quaternion keys (Euler XYZ composition; keep angles < ~30° per axis).
- Semantic helpers (calibrated, head/neck/spine family):
  `pitch(bone, f, +down)` · `yaw(bone, f, +character's-left)` ·
  `roll(bone, f, +tilt-toward-LEFT-shoulder)`
- `jaw_open(frame, deg)` — JawRoot +z opens. `clavicle_raise('L'|'R', f, deg)`
  (+ = lift, mirrored signs handled). `finger_curl(side, finger, joint, f, deg)`
  (+ = toward palm).
- `key_bone_loc_world("Hip", frame, (x_cm, y_cm, z_cm))` — armature-space cm
  (+x = character's left, +z = up). **Hip only.**
- `key_bone_scale(bone, frame, s)` — bone scale; VERIFIED to survive the GLB
  export→reimport round trip, so chest expansion MAY use subtle scale.
- Identity morphs (the 20 + head_size/body_weight) are refused with an
  exception. Never work around it.

### Motion generators (motion.*)

- `breathing(ctx, period=4.0, amp=1.0, phase=0.0, chest=, shoulders=, head=)`
  — layered chest/spine/clavicle/head cycle, inhale-fast/exhale-slow, per-cycle
  amplitude jitter, R clavicle lags 2 f at 92 %. glTF has NO additive blending:
  **bake a breathing layer into every base clip** (vary `phase`/`amp` so clips
  don't breathe in unison); the standalone `breathing_*` clips double as pure
  layers for additive-capable runtimes.
- `add_blink(ctx, frame, double=, eye_down=)` / `blink_schedule(ctx, gap=(2,6))`
  — close 3–4 f, hold, open 5–7 f, right eye lags 1–2 f, conjugate eye dip.
  `Eye_Blink_*` already carries the eyelashes on this rig — do NOT add
  `Eyelash_*` keys on top.
- `gaze_to(ctx, f, dx, dy)` / `gaze_wander(ctx, magnitude=, head_follow=)` —
  saccades 1–4 f via the `Eye_*_Look_*` keys (dx + = their left, dy + = up),
  fixation micro-drift, head trails eyes by 2–5 f when `head_follow>0`.
- `weight_shift(ctx, f0, f1, side=, lateral_cm=)` — hip over supporting foot +
  spine counter-lean + trailing-shoulder drop.
- `finger_relax(ctx)` — slow curl ripple, both hands decorrelated.
- `loop_noise(ctx, apply_fn, amp=, cycles=(2,3,5), step=3, fade=)` — noise from
  integer-cycle sinusoids: EXACTLY periodic, cannot break loop closure. For
  one-shots pass `fade=0.12` (blends to zero at both ends).
  `head_micro_sway(ctx)` = ready-made never-still head.
- `aos_keys(f0, f1, v1)` / `swing_aos(ctx, bone, axis, f0, f1, deg)` —
  anticipation → overshoot → settle profiles.

### Loops

`loop=True` gives frames `1..1+seconds*30`. Every keyed channel is forced to
end == start and gets a cyclic modifier (cycle-aware handle tangents). Rules:
periodic generators fit integer cycle counts automatically; transient events
(blinks, saccades) must keep ~15 frames of rest margin at both boundaries
(`blink_schedule`/`gaze_wander` already do).

## Rig facts (calibrated on meta_male — don't rediscover)

- 101 bones `CC_Base_*`, cm units, armature scaled 0.01; character faces **−Y**;
  A-pose (arms ~30° below horizontal). No plain `CC_Base_Neck` — neck =
  `NeckTwist01/02`. `*Twist01/02` limb bones stay unkeyed by authors.
  `CC_Base_BoneRoot` is NEVER keyed; all loops in-place; `CC_Base_Hip` carries
  turn yaw, vertical (sit/crouch) and lateral shift.
- **Jaw**: mouth opening is the JawRoot BONE (+z; lower teeth/tongue ride it —
  `CC_Toon_Teeth_01` has no jaw followers). Chin drop ≈ 0.65 / 1.04 / 1.72 /
  2.0 cm at 6/10/18/22°. The `Jaw_Open` KEY at 1.0 leaves the lips essentially
  CLOSED on this toon (skin-shaping only). Convention for speech/visemes:
  drive JawRoot 0–12° (15° = maximum wide), and add `Jaw_Open` ≈ angle/15 for
  lip shaping — do NOT treat key 1.0 as an open mouth.
- Head +x pitch nods DOWN; inhale = spine02 −x (extension). Eye look keys move
  both eyes conjugately; darts stay ≤ ~0.35 for idle.
- Blink at mid-values shows a chunky toon lid-fold in freeze frames
  (template-authored shape, fine at speed) — don't fight it in recipes.
- Scene fps is forced to 30 in the master (template ships at 60).

## Export

`export_animations.py` → `exports/avatar_animated_meta_male.glb` (all clips,
named animations via NLA tracks; same-named tracks across objects merge into
ONE animation), per-category GLBs, best-effort baked FBX + `export_log.txt`.
Identity keys are removed by the delta-preserving bake before export — the
GLB ships 148 animation targets on the body and zero identity morphs
(`verify_animations.py` asserts this and the clip durations).
