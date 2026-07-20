# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AI-Avatar-Engine: a from-scratch avatar generation pipeline (Meta Avatars /
Ready Player Me style). The end goal is photos → AI-predicted parameters →
rigged, animatable GLB avatar. **No AI or backend work has started yet** —
current work is entirely the "Avatar Factory": Blender-based template
authoring, a JSON morph parameter layer, and a browser dev tool to validate
both before any AI integration begins.

Everything lives under `AI-Avatar-Engine/`.

## Commands

**Avatar Sandbox (frontend/threejs-viewer/):**
```bash
npm install
npm run dev       # Vite dev server at http://localhost:5173
npm run build
npm run preview
```
No test suite or linter exists yet in this repo.

**AI photo analyzer (`ai/photo_analyzer/`)** — photos → `avatar_parameters.json`
(multi-model fusion pipeline; architecture in `docs/ai_photo_pipeline_architecture.md`,
full recalibration recipe in `ai/photo_analyzer/README.md`):
```bash
ai/.venv/Scripts/python ai/photo_analyzer/pipeline.py <front.jpg> [<left.jpg> <right.jpg>] [--debug]
# after morph/template changes, regenerate the whole calibration (see README
# for the full 12-command sequence): head views + front sweep + LEFT-view
# sweep (view arg) + haired renders, then calibrate.py --renders /
# --fit-gains / --fit-profile / --hairline-renders per gender.
```
Python 3.11 venv at `ai/.venv` (`mediapipe`, `opencv-contrib-python`,
`onnxruntime`; ONNX models in `models/`, gitignored, URLs in the README).
Pipeline stages: `preprocessing/` (quality score, roll alignment, color
normalization) → `processors/face_landmarks.py` (MediaPipe frontal
proportions + per-measurement confidence) + `processors/face_parsing.py`
(BiSeNet segmentation: beard/hairline/occlusion) +
`processors/profile_analyzer.py` (ear-anchored silhouette depth from the
side photos — MediaPipe can't see faces past ~60° yaw) +
`processors/identity_embedding.py` (ArcFace same-person check, never
morphs) + `processors/appearance_analyzer.py` (VLM labels only) →
`fusion/` (every signal carries {value, confidence, source}; beards
down-weight the lower-face measurements — triggered by parser coverage OR
the VLM beard label) → `fusion/solver.py` (confidence-weighted joint ridge
solve). Calibration in `calibration/calibration.json` is fully measured,
never hand-guessed: per-gender anchors from template renders, response
matrix from sweeps, hairline anchor from renders of the template WEARING
hair (`render_hairline_calib.py` — bald neutral renders can't provide it).
Detected gender selects the avatar base AND the anchor set. Output `face`
map is the unchanged engine contract; `faceMeta` adds per-parameter
confidence + source. Debug: `--debug` (CLI) or the Photos tab Debug
checkbox (sandbox) show stage images + measurement/parameter provenance.
The AI layer only produces parameters — it never touches meshes.

**Blender pipeline scripts** (`blender/scripts/`) are run headless, not imported as a package:
```bash
blender --background --python <script.py> -- <args...>
```
Blender executable on this machine: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.
Render engine enum in this Blender version is `BLENDER_EEVEE` (not `BLENDER_EEVEE_NEXT`).

Key scripts and their invocation (see each file's docstring for full arg lists):
- `import_template.py <source.fbx> <out.blend> <Prefix>` — FBX → template `.blend`, renames armature/body to `<Prefix>_Armature`/`<Prefix>_Body`
- `generate_customization_morphs.py <in.blend> <out.blend> <body_obj> <armature_obj> <eye_obj>` — (re)generates the 20 identity shape keys on a template
- `add_eye_follow_morphs.py <in.blend> <out.blend>` — adds matching `eye_size`/`eye_distance` keys to the eyeball/tearline/occlusion meshes so they track the body morph
- `add_mouth_follow_morphs.py <in.blend> <out.blend> <body_obj>` — adds follower keys to the teeth/tongue meshes for every identity morph that moves the mouth region (measured from the body's own maxilla/chin skin displacement); without them teeth poke through morphed lips
- `fix_lip_seal.py <in.blend> <out.blend> <body_obj>` — repairs the generated identity morphs around the mouth: welds the lip contact band (locally averaged motion so lips can't tear open), makes the mouth-bag interior follow the surrounding skin, and suppresses non-mouth morphs (cheek_size etc.) near the lip line whose masks leak into the lip roll. Run BEFORE `add_mouth_follow_morphs.py` whenever morphs are regenerated; both are idempotent
- `export_avatar_glb.py <template.blend> <out.glb> [--params '<json>'] [--keep-identity]` — bakes identity params into the mesh basis and exports GLB; `--keep-identity` skips baking (used for sandbox dev builds, where identity sliders must stay live)
- `verify_glb.py <avatar.glb> [preview.png]` — re-imports a GLB into a clean scene and reports mesh/bone/material counts, optionally renders a preview
- `inspect_asset.py <template.blend> <out_report.json>` — full audit of a template: shape key classification, ARKit-52 compatibility check (`ARKIT_TO_CC` mapping table lives here)
- `build_demo_assets.py <template.blend> <assets_shared_dir> <sandbox_wardrobe_dir>` — regenerates the entire demo wardrobe library (22 items: GLBs + thumbnails + item.json + catalog.json) and copies it into the sandbox
- `build_hair_style.py <template.blend> <assets_shared_dir> <sandbox_wardrobe_dir> <style_id> <preview_dir>` — strand-clump hair generator (real combed locks, not shells); styles are data in its `STYLES` dict, output merges into the existing catalog and renders on-head verification previews
- `import_hair_pack.py <pack_copy.blend> <female_template.blend> <assets_shared_dir> <sandbox_wardrobe_dir> <preview_dir>` — integrates an external hair pack (run it on a COPY, never the original): identifies hair-vs-display-bust pairs, auto-fits each hair to the female head via the pack's own bust registration (crown-anchored uniform scale; per-style `TWEAKS` for refinement), exports bone-attached GLBs + metadata + catalog merge + sandbox copy

## Architecture

### The morph layer is the core abstraction

Users (and eventually the AI) never touch raw Blender shape keys directly.
`blender/scripts/morph_definitions.json` defines ~20 semantic identity
parameters (`face_width`, `jaw_angle`, `nose_width`, ...) on a **0–1 scale
where 0.5 = neutral**. Each parameter maps to one or more underlying shape
keys with a weight:

```
key_value = (param - 0.5) * 2 * weight        # -> -1..1, summed if multiple params hit the same key
```

`morph_controller.py` (`MorphController` class) implements this translation
in Python for Blender; `frontend/threejs-viewer/src/main.js` (`computeKeyValues`)
implements the *identical* math in JS for the sandbox. **These two
implementations must stay in sync** — if the formula changes in one, change
it in the other. Both currently read their own copy of `morph_definitions.json`
(Blender's canonical copy under `blender/scripts/`, a duplicate served to the
sandbox under `frontend/threejs-viewer/public/`).

### Shape key classification (on the body mesh, ~169 keys total)

Only some of the ~169 shape keys on the body mesh are user-facing identity
morphs — the rest are animation. Never conflate them:
- `expression` (118) — ARKit-style FACS units (blink, smile, sneer...), animation-only
- `viseme` (8, prefixed `V_`) — lip-sync targets
- `corrective` (14, prefixed `Head_`/`Neck_`) — fire alongside bone rotation, not user-facing
- `secondary_animation` (8, prefixed `Eyelash_`) — follow eyelid motion
- `customization` (20) — the identity morphs users/AI control, listed in `morph_definitions.json`

All CC3+ characters (male/female/toon) share the same topology, skeleton, and
these same key names, which is what makes one morph generator/mapper scheme
work across styles.

### Morph generation is data-driven, not hand-sculpted

`generate_customization_morphs.py` builds each of the 20 customization morphs
by reusing the vertex regions Reallusion already sculpted for the expression
shape keys (masks derived from `Nose_*`, `Cheek_*`, `Mouth_*`, `Jaw_*`,
`Brow_*`, `Eye_*` keys), rather than guessing vertex selections by hand.
Regions with no expression analog (ears, forehead, philtrum) use geometric
masks anchored to armature bone positions and mask centroids computed at
runtime — this is why the same script works unmodified on both the male and
female base (landmarks are never hardcoded per-character).

Two non-obvious fixes baked into this script, don't regress them:
- **Lateral morphs need a midline ramp** (`lateral_dir()` helper). Without it,
  a "narrower" slider pushes vertices *past* the center line and the face
  pinches inside-out — this was a real bug found via visual verification on
  the female base.
- **`face_width` dampens near the eyeballs** via a geometric radius, because
  the eyeball/tearline/occlusion meshes are separate objects from the body;
  shifting the eye socket without moving them creates a cross-eyed look.

### Cross-mesh shape key sync contract

The body is one of 6 meshes (body, eyes, teeth, tongue, tearline, eye
occlusion) skinned to the same armature. Same-named shape keys across these
meshes must always be driven together (e.g. `eye_size` exists on the body
*and* on the eyeball/tearline/occlusion meshes as followers, added by
`add_eye_follow_morphs.py`). Both `MorphController.apply()` (Python) and
`SandboxViewer.setMorph()` (JS) already implement this by iterating every
mesh that has a matching key name — any new code driving morphs must do the
same rather than assuming a single mesh.

### Identity baking at GLB export time

Production GLBs must not ship the 20 identity keys as live morph targets —
glTF morph weights are conventionally 0–1 and runtimes shouldn't need to
re-derive identity. `export_avatar_glb.py` instead **bakes** the params into
the mesh basis (computing a per-vertex displacement field from the weighted
identity keys, applying it to the basis *and* to every remaining animation
key so their deltas are preserved, then deleting the identity keys). The
result: exported GLBs carry only the ~148 animation-purpose shape keys, all
0–1, all glTF-legal. The `--keep-identity` flag skips this for sandbox/dev
builds where live identity sliders are the point.

### ARKit compatibility

Verified 52/52 — `blender/scripts/inspect_asset.py` contains the
`ARKIT_TO_CC` mapping table (46 map 1:1, 6 are composites of 2–4 CC keys).
Note the eye direction naming mismatch: ARKit's "In/Out" corresponds to CC's
"L/R" crosswise (`eyeLookInLeft` → `Eye_L_Look_R`).

### Multi-style architecture (proposed, not yet implemented)

`docs/architecture_v2_proposal.md` is the design for supporting multiple
avatar styles (realistic, future Meta-style cartoon, anime, etc.) off the
same universal parameter JSON. Key point for future work: a new `schema/`
layer will split today's single `morph_definitions.json` into a
style-agnostic parameter schema plus per-style "mapper" files (same
left-hand parameter names, different target weights per style) — read this
doc before restructuring folders or changing parameter semantics, since it's
the intended target shape of the project.

### Avatar Asset System (wardrobe)

Modular equip/remove without touching the base mesh — see
`docs/asset_system.md`. Core rule: there are NO per-category manager classes;
`frontend/threejs-viewer/src/wardrobe.js` (`WardrobeManager`) is the single
engine and every category/slot/item is data in `assets/shared/catalog.json`.
Two attach types only: `bone` (rigid, authored bone-relative, parented at
runtime) and `skinned` (mesh skinned to the CC skeleton, re-bound to the
avatar's bones by name at equip time — this is why the shared skeleton/bone
naming must never change). Demo assets are generated deterministically by
`build_demo_assets.py` (skinned items are shells cut from the body mesh via
skinning-weight masks — they inherit fit and weights for free). Canonical
asset tree: `assets/shared/<category>/<id>/{<id>.glb, item.json,
thumbnail.png}`; the sandbox serves a copy under `public/wardrobe/`.

### Avatar Sandbox (frontend/threejs-viewer/)

Vanilla Three.js + Vite (deliberately no framework — a long-lived internal
dev tool). Three files carry all logic: `src/viewer.js` (`SandboxViewer` class:
Three.js scene, GLB loading, morph driving, debug helpers for
skeleton/wireframe/normals/UV, bone + skinned asset attachment, GLB export),
`src/wardrobe.js` (`WardrobeManager`), and `src/main.js`
(DOM panels: Inspector, Blendshapes, Identity, Appearance, Clothing,
Accessories, Display, Export). See
`frontend/threejs-viewer/README.md` for the tab-by-tab breakdown and the
wardrobe-asset authoring convention (meters, bone-relative, avatar faces +Z).

`window.sandbox` is exposed in the browser console (`{ viewer, params, defs }`)
for debugging.

Sandbox avatars (`public/avatars/sandbox_*.glb`) are dev builds exported with
`--keep-identity` — they are not representative of production export size or
shape-key count.

## Data/asset notes

- All textures are packed inside the `.blend` template files (no external
  file dependencies) — confirmed via `inspect_asset.py`'s material dump.
- Large binaries (Reallusion source FBX/textures, `.blend` templates,
  exported GLBs) are committed as plain git blobs, not Git LFS. All
  individual files stay under GitHub's 100MB hard limit, but several exceed
  the 50MB soft-warning threshold — be aware repo clone size grows with every
  binary change since there's no LFS deduplication.
- Known accepted limitation: `eye_size`/`eye_distance` sliders move the
  eyeball/tearline/occlusion via matched shape keys, but at extreme combined
  minima there's a minor tearline seam artifact — not yet fixed.
