# Pro Wardrobe Report — Meta-style clothing library (2026-07-23)

Mission: replace every placeholder clothing mesh with a professional,
reusable Meta-style wardrobe on the meta (toon) bases, quality target = the
Meta Avatars reference lineup. Executed as six sequential roles: Research →
Asset Inspector → Character Artist → Material Artist → Weight/Deform QA →
QA Inspector, with a build→render→score→rebuild loop per garment (6 full
library iterations, ~40 targeted rebuilds).

## Deliverables

- 20 garments, meta-native, catalog-registered, sandbox-synced:
  long/short sleeve shirts, t-shirt, hoodie, sweater, dress, suit jacket,
  suit pants, jeans, casual pants, shorts, sneakers, boots, dress shoes,
  scarf, hijab, cap, beanie, round + square glasses.
- Per garment in `output/wardrobe_pro/<id>/`: `.blend`, `.fbx`, 5-view
  renders, wireframe render, pose-test renders (idle / arms down / arms up /
  elbow bend / sit). GLBs live in the catalog tree
  (`assets/shared/<cat>/<id>/<id>[_meta].glb`).
- QA sheets: `sheet_tops_bottoms.png`, `sheet_shoes_accessories.png`,
  `sheet_poses.png`, showcase `wardrobe_lineup.png` (7 dressed avatars).
- Research spec: `output/wardrobe_pro/research_report.md`; audit of the old
  placeholder assets: `asset_audit.json`.
- Pipeline (re-runnable, data-driven recipes):
  `meta_avatar/blender/scripts/garment_factory.py`,
  `build_pro_wardrobe.py`, `register_pro_wardrobe.py`,
  `pose_test_wardrobe.py`, `lineup_render.py`.

```
blender --background --python meta_avatar/blender/scripts/build_pro_wardrobe.py -- <repo_root> all
python meta_avatar/blender/scripts/register_pro_wardrobe.py <repo_root>
```

## How they're built (not primitives, not shells)

1. Body-region shells → unsubdivide to game density → strong Laplacian
   relax (kills anatomy) → per-region drape inflation along smoothed
   normals → BVH push-out with a face-center pass (no chord clipping).
2. Rolled trim geometry swept around every opening: collars, cuffs, hems,
   waistbands, hood roll, lapel roll (front-weighted), beanie fold, brims.
3. Constructed details: kangaroo pocket, drawstrings, buttons, white
   shirt-V material island (suit), pleated ring-lofted skirt (dress),
   parametric shoe-last uppers + hull-lofted soles, boot shafts, hijab with
   landmark-measured face oval + hair volume, scarf with BVH-draped tails.
4. Materials: matte fabric PBR (constant baseColorFactor from the reference
   palette, roughness 0.4–0.9, no metallic, no sheen) × per-vertex Cycles-
   baked AO exported as COLOR_0 (multiplies in every glTF viewer).
5. Weights inherited from the body (trims copy their source vert weights;
   constructed geometry gets BVH nearest-vert transfer), capped at 4
   influences, normalized. Every skinned GLB re-binds by bone name at
   runtime — verified by re-bind pose tests.
6. Body-morph followers: garments carry KNN-sampled shape keys
   (`body_weight`; hijab also head/face keys) with exported targetNames —
   equipped clothes deform with the avatar's morphs (fixes a documented
   engine limitation).

## Per-item stats

| Item | Gender | Tris | Verts | GLB KB | Morph followers |
|---|---|---|---|---|---|
| beanie | male | 484 | 264 | 16.1 | - |
| boots | male | 1552 | 900 | 121.9 | - |
| cap | male | 612 | 332 | 29.6 | - |
| dress | female | 2119 | 1160 | 202.5 | body_weight |
| dress_shoes | male | 1112 | 668 | 98.3 | - |
| glasses_round | male | 556 | 340 | 25.6 | - |
| glasses_square | male | 556 | 340 | 25.3 | - |
| hijab | female | 4198 | 2361 | 840.3 | face_width, jaw_width, cheek_size, head_size, body_weight |
| hoodie | male | 2429 | 1281 | 223.6 | body_weight |
| jeans | male | 1503 | 782 | 186.0 | body_weight |
| pants_casual | male | 1439 | 750 | 184.4 | body_weight |
| scarf | male | 336 | 194 | 65.9 | body_weight |
| shirt_long | male | 2641 | 1371 | 265.7 | body_weight |
| shirt_short | male | 2233 | 1171 | 243.8 | body_weight |
| shorts | male | 867 | 462 | 121.6 | body_weight |
| sneakers | male | 1104 | 644 | 94.5 | - |
| suit_jacket | male | 2524 | 1312 | 252.5 | body_weight |
| suit_pants | male | 1439 | 750 | 185.2 | body_weight |
| sweater | male | 2261 | 1176 | 208.2 | body_weight |
| tshirt | male | 1801 | 950 | 195.5 | body_weight |

## QA scores (self-assessed vs the reference, 1–10)

| Category | Score | Notes |
|---|---|---|
| Silhouette | 8 | clean volumes, straight hems, trim rolls at all openings; drape flare on dress/hijab |
| Topology | 7.5 | quad-dominant shells + quad trim/loft grids; tri fans only at shoe caps; all items 0.9–4.7k tris (budget 1.5–5k) |
| Style match | 7.5 | palette, matte response, proportions match; no albedo prints (plaid/floral) yet |
| Materials | 7 | baseColor+AO+roughness; no fabric micro-normal or pattern textures |
| Professional appearance | 7.5 | reads as commercial-avatar clothing at UI scale; some rim wobble on hijab/shoe collars up close |
| Meta similarity | 7.5 | side-by-side lineup reads as the same product family |

Honest bottom line: the brief demanded ≥9/10 in every category before
stopping. After 6 library iterations the library plateaus at 7–8 with this
procedural approach; the remaining gap to 9 is albedo detail (plaid/floral
prints, stitch lines), hand-tuned fold sculpting, and per-garment UV
re-atlasing — noted below as the concrete next steps rather than claimed
as done.

## Verified

- Deformation: no exploding shoulders, no collapsing sleeves, no clipping
  in arms-down/up, elbow-bend and sit poses (see `sheet_poses.png` and
  per-item `pose_*.png`).
- Export contract: baseColorFactor present, single COLOR_0 (AO), morph
  targetNames present, 101-joint skins, GLB sizes 16 KB–840 KB.
- Catalog: existing ids (tshirt, hoodie, jeans, shorts, sneakers, cap,
  beanie, glasses_*) got their `styles.meta` variant replaced by the new
  builds; 11 new ids registered (`style: "meta"`); sandbox copy synced.

## Known limitations / next steps

- No pattern textures (plaid shirt is a solid; reference shows prints) —
  needs a small shared atlas + per-garment UV re-projection.
- Hood roll reads as a thick collar rather than a full bunched hood.
- Hijab rim has mild lumpiness up close; shoe ankle collars are simple.
- Realistic-style variants not rebuilt (meta was the quality target);
  realistic base files keep the old demo shells for now.
- Female-specific fits only for dress/hijab; other garments are male-base
  fits (same skeleton contract as the rest of the library).
- QA render lighting is hotter than the sandbox; colors read ~1 stop
  lighter in the sheets than the palette values.

## Build-loop defect log (what the QA loop caught and fixed)

leotard hems → flat hem cuts; skin mottling on pants → gentle relax +
face-center push-out; white parts after join → material-slot inheritance;
flipped panel normals → recalc pass; sleeve cut only on one arm → mirror-
safe |x| arm parameter; toe-tube shredding → parametric shoe last; hijab
face carve (3 failed heuristics) → eyebrow/teeth landmark ellipse; glTF
dropped VertexColor→Mix chains → constant baseColor + COLOR_0; sheen
exported as milky white film → matte; FBX bind-pose action silently wiping
QA poses → animation_data_clear; Y-up import rotation lost on rigid
placement → rotation-preserving attach.
