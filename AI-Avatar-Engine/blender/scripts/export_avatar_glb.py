"""
Avatar GLB exporter — turns a template + user morph params into a final
rigged GLB.

Pipeline:
  1. Load template (male_base.blend / female_base.blend).
  2. Translate user params (0..1, 0.5 neutral) via the morph layer.
  3. BAKE the resulting identity into the mesh basis:
       new_basis = basis + sum(value_i * delta_i)  over customization keys,
     shifting every animation key by the same field so their deltas are
     preserved relative to the new face. Customization keys are then removed.
  4. Export GLB: skeleton + skinning + all animation blendshapes (0..1,
     glTF-legal) + packed textures.

Baking at export is the production pattern: identity is fixed per-avatar,
the runtime only ever drives animation (ARKit/viseme) morph targets.

Usage:
  blender --background --python export_avatar_glb.py -- \
      <template.blend> <out.glb> [--params <json-string-or-file>] \
      [--keep-identity]

--keep-identity skips the bake and exports the customization keys as live
morph targets (dev/sandbox builds; glTF morph weights may be negative, and
Three.js honors negative influences).
"""
import bpy
import json
import numpy as np
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from morph_controller import MorphController  # noqa: E402


def customization_key_names(mc):
    names = set()
    for spec in mc.params_spec.values():
        for t in spec["targets"]:
            names.add(t["shape_key"])
    return names


def bake_identity(mc, params):
    """Bake computed key values into every mesh's basis, preserving all
    animation key deltas, then delete the customization keys."""
    key_values = mc.compute_key_values(params)
    custom_names = customization_key_names(mc)

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        mesh = obj.data
        kbs = mesh.shape_keys.key_blocks
        present = [kb for kb in kbs if kb.name in custom_names]
        if not present:
            continue

        n = len(mesh.vertices)
        basis = kbs[0]
        basis_co = np.zeros(n * 3, dtype=np.float64)
        basis.data.foreach_get("co", basis_co)

        # displacement field D = sum(value * (key - basis))
        D = np.zeros(n * 3, dtype=np.float64)
        for kb in present:
            v = key_values.get(kb.name, 0.0)
            v = max(kb.slider_min, min(kb.slider_max, v))
            if abs(v) < 1e-6:
                continue
            co = np.zeros(n * 3, dtype=np.float64)
            kb.data.foreach_get("co", co)
            D += v * (co - basis_co)

        # shift basis + every non-customization key by D (delta-preserving)
        for kb in kbs:
            if kb.name in custom_names:
                continue
            co = np.zeros(n * 3, dtype=np.float64)
            kb.data.foreach_get("co", co)
            kb.data.foreach_set("co", (co + D).astype(np.float32))

        # keep raw mesh vertices in sync with the new basis
        verts = np.zeros(n * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", verts)
        mesh.vertices.foreach_set("co", (verts + D).astype(np.float32))

        # remove customization keys and zero all animation keys
        for kb in present:
            obj.shape_key_remove(kb)
        for kb in mesh.shape_keys.key_blocks:
            kb.value = 0.0
        mesh.update()
        print(f"  baked {len(present)} identity keys into {obj.name} "
              f"({len(mesh.shape_keys.key_blocks)} animation keys kept)")


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    template, out_glb = argv[0], argv[1]
    params = {}
    keep_identity = "--keep-identity" in argv
    if "--params" in argv:
        raw = argv[argv.index("--params") + 1]
        params = json.load(open(raw)) if os.path.isfile(raw) else json.loads(raw)

    bpy.ops.wm.open_mainfile(filepath=template)
    mc = MorphController()

    if keep_identity:
        print("Keeping identity keys as live morph targets (dev build)")
        mc.reset()
    else:
        print(f"Baking identity from {len(params)} user params...")
        bake_identity(mc, params)

    os.makedirs(os.path.dirname(os.path.abspath(out_glb)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format='GLB',
        export_morph=True,
        export_morph_normal=True,
        export_skins=True,
        export_animations=False,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_yup=True,
    )
    size_mb = os.path.getsize(out_glb) / 1e6
    print(f"Exported: {out_glb} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
