# Avatar Factory — Pipeline Documentation

End-to-end flow from Reallusion source FBX to a final rigged GLB avatar.

```
Reallusion FBX                                (assets/reallusion_base/)
      │
      │  import_template.py       — import, rename <Prefix>_Armature/_Body
      ▼
Template .blend                               (blender/templates/)
      │
      │  generate_customization_morphs.py   — 20 identity shape keys (-1..1)
      │  add_eye_follow_morphs.py           — eye_size/eye_distance followers
      │                                       on eyeball/tearline/occlusion
      ▼
Master template (male_base.blend / female_base.blend)
      │
      │  morph_controller.py + morph_definitions.json
      │      user params (0..1, 0.5 = neutral)  →  shape key values
      │
      │  export_avatar_glb.py --params '{...}'
      │      1. translate params via morph layer
      │      2. BAKE identity into mesh basis (delta-preserving)
      │      3. remove identity keys, keep 148 animation targets
      │      4. export GLB (skeleton + skinning + morphs + textures)
      ▼
Final avatar .glb                             (blender/exports/)
      │
      │  verify_glb.py            — re-import, count check, preview render
      ▼
Three.js runtime (future)
```

## Scripts (blender/scripts/)

| Script | Role |
|---|---|
| `import_template.py` | FBX → template .blend (parameterized prefix) |
| `generate_customization_morphs.py` | Generates the 20 identity morphs. Landmarks computed dynamically from bones + expression-mask centroids → works on any CC3+ base (male/female/toon) without retuning |
| `add_eye_follow_morphs.py` | Adds `eye_size`/`eye_distance` keys to CC_Base_Eye/TearLine/EyeOcclusion so separate eye objects track the face morphs |
| `morph_definitions.json` | **Single source of truth** for user-facing params (labels, categories, target weights). Also to be consumed by AI output + backend + Three.js |
| `morph_controller.py` | Param → shape key translation engine; headless CLI with preview render |
| `export_avatar_glb.py` | Bakes identity, exports final GLB |
| `verify_glb.py` | Re-import verification + preview |
| `inspect_asset.py` | Full template audit incl. ARKit-52 check (`ARKIT_TO_CC` mapping table lives here) |

## Templates

- `blender/templates/male_base.blend` — Neutral_M, 169 body keys (149 CC + 20 identity), eye-follow keys on 3 secondary meshes
- `blender/templates/female_base.blend` — Neutral_F, same structure

## Design decisions

1. **Identity is baked at export.** The runtime never adjusts identity morphs — it only drives the 148 animation targets (ARKit expressions, visemes, correctives). This keeps GLBs glTF-legal (0..1 weights), smaller, and matches the Meta Avatars model.
2. **Same-named keys across meshes are the sync contract.** Body, eyeball, tearline and occlusion all carry `eye_size`/`eye_distance`; the controller (and later the runtime for animation keys like `Eye_Blink_L`) must set same-named keys to the same value on every mesh.
3. **Midline ramp on lateral morphs** (`face_width`, `jaw_width`, `nose_width`, `mouth_width`, `eye_distance`): displacement scales to zero at X=0 so the narrowing direction can never push vertices across the center line (this was a real bug caught in female verification — inside-out pinch seam).
4. **Philtrum excludes the nose mask** so the columella stays anchored.

## Verified end-to-end (2026-07-15)

- Male GLB (71 MB) with baked test identity: 101 bones, 148 body targets, 17 materials — smile/blink/jaw-open render correctly from the re-imported GLB.
- Female GLB (68 MB), neutral identity: identical structure.
- Note: Blender's glTF *importer* adds a display `Icosphere` for armatures on re-import; it is **not** in the exported files (verified by parsing the GLB JSON chunk).

## Known limitations / next steps

- Combined extreme minima (`eye_size`≈0 + `eye_distance`≈0) show a minor tearline artifact at the inner eye corner.
- GLB size (~70 MB) is dominated by 148 morph targets × ~15.6k verts with normals; production trims: drop corrective/rarely-used targets at export, quantize (KHR_mesh_quantization), Draco, and texture downsizing per quality tier.
- Roughness/AO/SSS maps from the source package are not yet wired into export materials.
- Toon bases (04/05) can be templated with the same 3 commands if a stylized tier is ever wanted.
