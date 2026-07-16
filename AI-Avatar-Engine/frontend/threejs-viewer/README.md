# Avatar Sandbox

Developer tool for inspecting and testing the AI-Avatar-Engine: templates,
blendshapes, identity params, and wardrobe assets — before any AI is involved.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

## Tabs

| Tab | What it does |
|---|---|
| **Inspector** | Meshes (verts / morph counts / materials), material list with texture maps, full 101-bone hierarchy |
| **Blendshapes** | One slider per morph target (~286), grouped by category (visemes, brow, eye, mouth, ...), searchable. Same-named targets across meshes are driven together — this mirrors the engine's runtime sync contract |
| **Identity** | The 20 semantic user params (0–1, 0.5 neutral) with per-category sliders **and** a live JSON editor. Uses `public/morph_definitions.json` — the same file as the Blender pipeline; the math is identical to `morph_controller.py` |
| **Display** | Toggles: skeleton overlay, wireframe, vertex normals, UV checker, grid |
| **Assets** | Attach/remove hairstyles, beards, glasses, clothes, accessories from `public/assets_manifest.json`. Assets are parented to the bone configured per category |
| **Export** | Download current scene as GLB (Three.js re-export) or the identity params JSON (the format `export_avatar_glb.py --params` accepts) |

## Avatars

`public/avatars/sandbox_male.glb` / `sandbox_female.glb` are **dev builds**
exported with `export_avatar_glb.py --keep-identity`: identity morphs stay
live (negative weights allowed) so the Identity tab works. Production avatars
bake identity instead.

Regenerate after template changes:

```bash
blender --background --python ../../blender/scripts/export_avatar_glb.py -- \
  ../../blender/templates/male_base.blend public/avatars/sandbox_male.glb --keep-identity
```

## Adding wardrobe assets

1. Drop a `.glb` into `public/assets/<category>/`.
2. Register it in `public/assets_manifest.json`.
3. Author assets in **meters, relative to the target bone's position**
   (glTF Y-up, avatar faces +Z). Example: glasses lenses sit ≈9.8 cm forward
   and ≈7 cm above the `CC_Base_Head` bone.

## Debugging

`window.sandbox` exposes `{ viewer, params, defs }` in the browser console.
