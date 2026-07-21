"""
Meta-look stylization pass for the toon templates.

v1 is deliberately light-touch — the Reallusion toon bases already carry the
stylized geometry and painted-diffuse look, so this pass only pushes the
shading toward the soft matte "Meta Avatars" aesthetic:

  - skin/nail materials: matte roughness, low specular, halved normal-map
    strength (no skin pores / plastic sheen)
  - eyes, brows, lashes, teeth: untouched (their gloss is part of the look)
  - packs all textures into the .blend (template files must be dependency-free)

Geometry proportion knobs (head/eye scale) are scaffolded but DEFAULT OFF —
they apply the same affine transform to the basis AND every shape key so
morph deltas stay consistent (the delta-preserving rule from
export_avatar_glb.py). Tune only via render review, never blind.

Usage:
  blender --background --python stylize_meta_base.py -- \
      <in.blend> <out.blend> [--props '{"head_scale": 1.0, "eye_scale": 1.0}']
"""
import bpy
import json
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out = argv[0], argv[1]
props = {"head_scale": 1.0, "eye_scale": 1.0}
if "--props" in argv:
    props.update(json.loads(argv[argv.index("--props") + 1]))

SKIN_ROUGHNESS = 0.72
SKIN_SPECULAR = 0.20
NORMAL_STRENGTH = 0.5
SKIN_PREFIXES = ("Std_Skin_", "Std_Nails")

bpy.ops.wm.open_mainfile(filepath=blend_in)

for mat in bpy.data.materials:
    if not mat.name.startswith(SKIN_PREFIXES) or not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            node.inputs["Roughness"].default_value = SKIN_ROUGHNESS
            if "Specular IOR Level" in node.inputs:
                node.inputs["Specular IOR Level"].default_value = SKIN_SPECULAR
        elif node.type == 'NORMAL_MAP':
            node.inputs["Strength"].default_value = min(
                node.inputs["Strength"].default_value, NORMAL_STRENGTH)
    print(f"[stylize] matte skin: {mat.name}")

if any(abs(v - 1.0) > 1e-6 for v in props.values()):
    sys.exit("[stylize] geometry knobs are scaffolded but not enabled in v1 — "
             "tune materials first, enable knobs deliberately")

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
