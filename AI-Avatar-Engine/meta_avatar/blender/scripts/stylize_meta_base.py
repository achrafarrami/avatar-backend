"""
Meta-look stylization pass for the toon templates.

Two parts, both light-touch — the Reallusion toon bases already carry the
stylized geometry and painted-diffuse look:

  1. MATERIAL pass: soft matte skin (roughness up, spec + normal-map strength
     down) for the "Meta Avatars" shading. Eyes/brows/lashes/teeth untouched.

  2. NEUTRAL pass (--neutral '<params>'): bakes a set of identity-morph offsets
     into the mesh basis so the 0.5-neutral face reads as a moderate cartoon
     (bigger eyes, softer/smaller nose, rounder cheeks) REGARDLESS of identity.
     Reuses the 20 proven identity morphs as the stylization vocabulary — no
     new sculpting risk. The bake is delta-preserving (every remaining key is
     shifted by the same field, so all animation + identity deltas stay
     correct relative to the new basis) and — unlike the export bake — KEEPS
     the identity keys live, so the sandbox sliders still work, now centred on
     the stylized neutral. Cross-mesh: the same key values drive the eye /
     tearline / occlusion / teeth meshes via their same-named follower keys.

Packs all textures into the .blend (templates must be dependency-free).

Usage:
  blender --background --python stylize_meta_base.py -- \
      <in.blend> <out.blend> [--neutral '<params_json>'] [--no-material]
"""
import bpy
import json
import os
import sys
import numpy as np

SHARED = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "blender", "scripts"))
sys.path.insert(0, SHARED)
from morph_controller import MorphController  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out = argv[0], argv[1]
neutral = {}
if "--neutral" in argv:
    neutral = json.loads(argv[argv.index("--neutral") + 1])
do_material = "--no-material" not in argv

SKIN_ROUGHNESS = 0.72
SKIN_SPECULAR = 0.20
NORMAL_STRENGTH = 0.5
SKIN_PREFIXES = ("Std_Skin_", "Std_Nails")

bpy.ops.wm.open_mainfile(filepath=blend_in)

# ---------------------------------------------------------------- material
if do_material:
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

# ------------------------------------------------------------- neutral bake
if neutral:
    mc = MorphController(os.path.join(SHARED, "morph_definitions.json"))
    known = set(mc.list_params())
    bad = [k for k in neutral if k not in known]
    if bad:
        sys.exit(f"[stylize] unknown neutral params: {bad}")
    key_values = mc.compute_key_values(neutral)   # shape_key name -> value
    custom = set(key_values)
    print(f"[stylize] baking stylized neutral from {len(neutral)} params "
          f"-> {len(custom)} keys")

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        mesh = obj.data
        kbs = mesh.shape_keys.key_blocks
        present = [kb for kb in kbs if kb.name in custom]
        if not present:
            continue
        n = len(mesh.vertices)
        basis_co = np.zeros(n * 3)
        kbs[0].data.foreach_get("co", basis_co)

        # displacement field D = sum(value * (key - basis))
        D = np.zeros(n * 3)
        for kb in present:
            v = float(np.clip(key_values.get(kb.name, 0.0),
                              kb.slider_min, kb.slider_max))
            if abs(v) < 1e-6:
                continue
            co = np.zeros(n * 3)
            kb.data.foreach_get("co", co)
            D += v * (co - basis_co)

        # shift basis + EVERY key (identity keys kept, deltas preserved) by D
        for kb in kbs:
            co = np.zeros(n * 3)
            kb.data.foreach_get("co", co)
            kb.data.foreach_set("co", (co + D).astype(np.float32))
        verts = np.zeros(n * 3)
        mesh.vertices.foreach_get("co", verts)
        mesh.vertices.foreach_set("co", (verts + D).astype(np.float32))
        for kb in kbs:
            kb.value = 0.0
        mesh.update()
        print(f"  baked into {obj.name} ({len(present)} identity keys kept live)")

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
