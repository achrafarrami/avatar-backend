# Meta Avatar System

Second avatar style ("Meta") next to the realistic engine — clean, modern,
expressive cartoon, Meta-Avatars-inspired, built for mobile/WebGL. Both styles
consume the **same universal avatar parameters JSON** produced by the AI photo
pipeline; only the rendering layer differs (`docs/architecture_v2_proposal.md`
is the governing design — this folder is its "meta style" half, implemented
additively without touching the realistic pipeline).

## Foundation decision

The meta bases are the **Reallusion CC3+ Toon Neutral M/F** figures
(`assets/reallusion_base/CC Character Base/FBX/04_Toon Neutral_F`,
`05_Toon Neutral_M`). All CC3+ characters — realistic and toon — share
identical topology (15 602 body verts), skeleton (101 bones, `CC_Base_*`
names), and animation shape keys (149: 118 expression / 8 viseme /
14 corrective / 8 eyelash, ARKit 52/52 via `inspect_asset.py`). That makes
every hard Phase-1 requirement (identical topology / skeleton / morph names /
ARKit, forever) true **by construction**, and the entire existing template
tooling runs on them unmodified.

Toon-only differences vs the realistic bases:
- `Toon_Eyebrows` — a separate floating eyebrow mesh (realistic brows are
  texture-only). Identity morphs need follower keys on it:
  `blender/scripts/add_brow_follow_morphs.py` (this folder) samples the body
  skin's motion under each identity key via KNN and bakes matching keys.
- `CC_Toon_Teeth_01` replaces `CC_Base_Teeth` (still found by substring,
  still Upper/Lower material split, but much larger cartoon teeth).
- Mouth sits lower & proportionally larger → the shared
  `fix_lip_seal.py` / `add_mouth_follow_morphs.py` are now TEETH-ANCHORED
  (windows derived from the teeth bbox; ratios reproduce the old hardcoded
  values exactly on the realistic bases — regression-checked).

## Layout

```
meta_avatar/
  blender/base/       meta_male.blend, meta_female.blend  (finished templates)
  blender/morphs/     QA renders: neutral baselines, 20-param sweeps + contact sheets
  blender/scripts/    add_brow_follow_morphs.py, stylize_meta_base.py
  blender/exports/    sandbox_meta_{male,female}.glb  (dev GLBs, --keep-identity)
  assets/             meta wardrobe variants (Phase 3+; catalog stays shared)
  renderer/           meta.map.json (universal params -> meta morphs), style.json
  documentation/      this file, inspection JSONs, phase reports
```

## Rebuild recipe (per gender)

```bash
blender --background --python blender/scripts/import_template.py -- <toon.fbx> meta_<g>.blend Meta<G>
blender --background --python blender/scripts/generate_customization_morphs.py -- meta_<g>.blend meta_<g>.blend Meta<G>_Body Meta<G>_Armature CC_Base_Eye
blender --background --python blender/scripts/fix_lip_seal.py -- meta_<g>.blend meta_<g>.blend Meta<G>_Body
blender --background --python blender/scripts/add_mouth_follow_morphs.py -- meta_<g>.blend meta_<g>.blend Meta<G>_Body
blender --background --python blender/scripts/add_eye_follow_morphs.py -- meta_<g>.blend meta_<g>.blend
blender --background --python meta_avatar/blender/scripts/add_brow_follow_morphs.py -- meta_<g>.blend meta_<g>.blend Meta<G>_Body
blender --background --python meta_avatar/blender/scripts/stylize_meta_base.py -- meta_<g>.blend meta_<g>.blend
blender --background --python blender/scripts/export_avatar_glb.py -- meta_<g>.blend sandbox_meta_<g>.glb --keep-identity
```
(paths abbreviated; shared scripts live in `blender/scripts/`, meta-only ones
in `meta_avatar/blender/scripts/`)

## Parameter mapping

`renderer/meta.map.json` — generated from `morph_definitions.json`; same
20 left-hand universal params, per-style targets + global `exaggeration`
(1.0 in v1, tuned in Phase 2). `renderer/style.json` is the style manifest.
Copies are served from the sandbox `public/`. The AI pipeline is untouched
and knows nothing about styles.

## Meta look (Phase 2)

The neutral face is a **moderate cartoon**, baked into the mesh basis via the
20 identity morphs (`stylize_meta_base.py --neutral`, offsets recorded in
`renderer/meta.map.json → stylized_neutral`) — bigger eyes, softer/smaller
nose, rounder cheeks — so 0.5-neutral reads Meta regardless of identity, while
the identity sliders stay live around it. `meta.map.json → exaggeration` (1.3)
amplifies AI-predicted identity into characterful cartoons. Two Meta-only
controls (`head_size`, `body_weight`) are added by `add_meta_body_morphs.py`
and declared in `meta.map.json → meta_morphs` — deliberately NOT in the shared
`morph_definitions.json` (that is the AI pipeline's contract).

## Phase status

- **Phase 1 (base characters): DONE** — see `phase1_report.md`.
- **Phase 2 (stylized morph library): DONE** — see `phase2_report.md`.
- Phase 3 hair, Phase 4 accessories, Phase 5 clothing, Phase 6 animation
  validation, Phase 7 sandbox style switcher: pending.
