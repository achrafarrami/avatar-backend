# Phase 2 Report — Stylized Morph Library

**Status: DONE.** The meta bases now read as a **moderate cartoon** at neutral,
the 20 identity morphs are tuned for the Meta look, and two new gender-compatible
Meta controls (head size, body build) were added. The AI pipeline and the
realistic engine were not touched.

Direction chosen (with you): **moderate** stylization (believable, not
uncanny) and **tune the 20 + add head/eye/body** morphs.

## 1. Moderate Meta neutral (baked)

Rather than sculpt new base proportions from scratch (uncanny risk), the
stylized neutral is expressed through the 20 *proven* identity morphs and
**baked into the mesh basis**, so 0.5-neutral looks Meta regardless of
identity. Chosen offsets (dialed in on renders, candidate "C moderate"):

`eye_size 0.70, cheek_size 0.60, forehead_height 0.54, jaw_width 0.43,
jaw_angle 0.45, chin_size 0.46, nose_width 0.40, nose_tip_size 0.40,
nose_length 0.45` → bigger eyes, softer/smaller nose, fuller rounder cheeks,
softer jaw.

The bake (`stylize_meta_base.py --neutral`) is **delta-preserving** and — unlike
the export bake — **keeps the identity keys live**, so the sandbox sliders still
work, now centred on the stylized neutral (eye_size 0 pulls back toward
realistic, eye_size 1 goes large). Cross-mesh: the same key values drive the
eye/teeth/tongue/tearline/occlusion/eyebrow followers. Recorded in
`renderer/meta.map.json → stylized_neutral` so it can be re-baked if the morphs
are regenerated.

## 2. Identity exaggeration

`meta.map.json → exaggeration` set to **1.3** (moderate). At the mapper→recipe
stage (`key = (param−0.5)·2·weight·exaggeration`) this amplifies AI-predicted
identity so faces read as characterful cartoons. Verified on renders: a
distinctive face at 1.3 is visibly wider/stronger than at 1.0 while staying
believable (`blender/morphs/exagg_check/`).

## 3. New Meta-only morphs (both genders)

`add_meta_body_morphs.py` — data-driven from armature bones + mesh bounds, so
identical on both bases; **kept out of `morph_definitions.json`** on purpose
(that file is the AI pipeline's 20×20 calibration contract). Declared in
`meta.map.json → meta_morphs`.

- **head_size** — head-to-body ratio; scales the whole head about the head
  centroid, tapering to 0 across the *neck band* (so the entire face scales as
  a rigid unit — an earlier neck-height taper made the teeth outrun the lips and
  popped the mouth open; fixed). Cross-mesh: the same key is added to every head
  sub-mesh so the face rides with the skull; eyeball stays spherical.
- **body_weight** — torso/limb girth (slim ↔ stocky), body mesh only, zero on
  the face.

(The "eye" axis of the request is covered by the enlarged baked neutral plus
the existing `eye_size` slider — no redundant new morph.)

## Verification

- `blender/morphs/look_candidates/` — the neutral-look dial-in (mild→strong,
  both genders, front + three-quarter), moderate chosen.
- `blender/morphs/exagg_check/` — exaggeration 1.0 vs 1.3 demo.
- `blender/morphs/baseline_{male,female}/` + `sweep_{male,female}_front/` —
  neutral + all 20 morph extremes re-rendered on the stylized bases (clean:
  mouths sealed, brows track, teeth contained, no pinches).
- Live sandbox: both meta GLBs load; `head_size` drives all 18 head+body
  primitives together, `body_weight` the 6 body primitives only, identity
  morphs still work (cross-mesh contract holds in Three.js). head_size +1
  gives the iconic Meta big-head with the mouth still sealed.

## New / changed files

- `meta_avatar/blender/scripts/add_meta_body_morphs.py` (new) — head_size + body_weight
- `meta_avatar/blender/scripts/stylize_meta_base.py` — added the neutral-bake pass
- `meta_avatar/blender/scripts/render_meta_look.py` (new) — look/morph QA renders (+raw keys, body view)
- `meta_avatar/renderer/meta.map.json` — exaggeration 1.3, stylized_neutral, meta_morphs
- `meta_avatar/blender/base/meta_{male,female}.blend` + dev GLBs — re-baked/re-exported

## Not done (future)

- `height`/`body_muscle` morphs (height needs a head-translation follower — deferred).
- Wiring meta_morphs into a semantic Identity-tab UI is Phase 7 (they're drivable
  now via the raw Blendshapes tab).
