# Photo → Meta Avatar: color + likeness pass (2026-07-27)

Goal: a Meta avatar that looks like the photo in PROPORTIONS and COLORS —
always smooth (no wrinkles/detail), always dressed. Validated on the 16
usable photos in `test_photos/` (17th has no detectable face).

## What was added/changed

### Measured colors (Phase A)
- `ai/photo_analyzer/processors/color_sampler.py` (NEW): samples real pixel
  colors from the ALIGNED front photo through the BiSeNet parsing masks —
  skin (lit-half of the face, 10-60 luminance band), hair (above brow line),
  brows, iris (annulus around the MediaPipe iris centers). Continuous tones,
  no palette. Output rides in `appearance.colors` of
  `avatar_parameters.json` ({hex, coverage_px} per region).
  - Aligned (NOT gray-world-normalized) image: normalization desaturates
    (redhead → brown, dark skin → gray). Verified on test photos.
  - Lit-half rule: a directional shadow side otherwise drags fair skin
    toward tan.
- `backend/generate_avatar.py`: measured hair hex beats the VLM label
  palette for hair/beard; skin/brows/iris go into the assembly manifest as
  a `_template_colors` entry.
- `meta_avatar/blender/scripts/assemble_avatar.py`: `recolor_template()`
  applies them to the template textures in place:
  - skin: LINEAR-space multiplicative tint of the 4 Std_Skin_* diffuse maps
    (sRGB-space multiply under-darkens dark targets);
  - iris: hue/sat/value replacement on saturated (ring) pixels of BOTH
    Std_Eye_* and Std_Cornea_* diffuse maps — the cornea is a 0.55-alpha
    copy stacked on the eyeball; both need the identical recolor;
  - brows: flat Base Color on Toon_Eyebrows_Transparency (texture-space
    recolors fail — the strip UVs sample background regions).
  - `set_color()` (hair/beard/clothes): prefix-matches material names
    (meta GLBs carry `<id>_meta_mat`) and unlinks Base Color inputs
    (vertex-color chains silently override the flat color).
- `blender/scripts/verify_glb.py`: preview renders use the **Standard**
  view transform — AgX (default) desaturates and made correct colors look
  broken; three.js (sRGB, no tone mapping) shows textures as-is.

### Beard refit + shape (Phase A)
- `build_facial_meta.py`: beard floor is now mouth-relative
  (`Z > MOUTH_Z - 4.5`, was hardcoded 149 — broke when the male chin was
  reshaped); mustache band starts at `MOUTH_Z + 0.55` so the mouth stays
  visible; flat_material roughness 0.9; shells shade smooth.
  Rebuilt `beard_short_meta.glb` / `goatee_meta.glb` against the current
  male template. **Re-run this script whenever the male face changes.**

### Likeness mapping (Phase B)
- Global meta exaggeration 1.3 → **1.45** (meta.map.json); focus params
  (eye_size/eye_distance/eye_tilt/mouth_width) keep their own 1.5 gain
  with the ±0.28 deviation cap. A/B-verified on 4 faces: more identity,
  style intact. Parameter spread across the 16-photo batch is healthy
  (eye_distance 0.22-0.78, face_width 0.37-0.84, nose_width 0.27-0.69).

### Females (Phase C)
- Already-existing flow verified end-to-end: gender detection routes to the
  female template, hair auto-picks from the 10-style pack via the VLM style
  label (updo→hair_w05, long→hair_w03 confirmed), measured hair color
  applies, default outfit (tshirt+jeans+sneakers) always attaches — never
  nude. All 10 hair styles have meta fits in the catalog.

## QA results (Phase D)
- 6 full generations (african bald / redhead+beard / asian woman updo /
  girl long-hair / walter-white glasses+beard / young bearded): all
  attached, colored, dressed, exported, verified. Lineup + per-case
  side-by-sides in the session scratchpad (`phaseD_lineup.png`).
- Both template regression gates PASS (bones, keys, ARKit 52/52,
  followers, extremes, renders).

## Follow-up fixes (same day)
- Beard color now sampled from the parser's HAIR pixels BELOW the nose
  line (`colors.beard`) — Walter White's gray beard comes out gray under
  dark scalp hair. Preference order in generate_avatar.py: measured beard
  → measured hair → VLM label palette.
- Beard pale chunks fixed: `recalc_face_normals` in build_facial_meta.py
  after cutting the shell (island faces were wound inward). Verified on
  both bearded QA cases.
- Iris ring mask widened (both implementations): strongly saturated pixels
  OR blue-hued (H 0.45-0.80) pixels at mild saturation — the old
  saturation-only threshold left the ring's pale scalloped edge blue
  (visible as blue fragments around the recolored iris in three.js).
  Hue-gating keeps warm sclera shading untouched.
- Sandbox Photos flow now applies measured colors LIVE, INCLUDING the
  iris: `recolorIrisTexture()` (canvas-space port of iris_fn) rebuilds the
  eye + cornea textures with the measured eye color. Also:
  `applyMeasuredTemplateColors()` in avatar-frontend/src/main.js — skin =
  linear target/texture-mean ratio as material.color on Std_Skin_*/
  Std_Nails (texture mean constant `SKIN_TEX_MEAN_SRGB`, re-measure if the
  skin textures are re-authored), brows = flat color (map dropped), hair/
  beard = measured hex through wardrobe.setColor. Iris stays
  generation-only (needs a texture edit). Verified live in the sandbox.

## Known limits / ceilings
- Strong indoor color casts bake into sampled colors (no photo WB);
  sclera-anchored white balance is the upgrade path.
- Face-width measurement can disagree with perception (african test face
  measured narrow); that's calibration/fusion territory, not the mapper.
- `render_meta_look.py` applies raw params (no exaggeration) — pre-apply
  `apply_exaggeration` when using it to preview AI outputs.

## Re-run
```bash
ai/.venv/Scripts/python backend/generate_avatar.py <photos_dir> <out.glb> --style meta
```
