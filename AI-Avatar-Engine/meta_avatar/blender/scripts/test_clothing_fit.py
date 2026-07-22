"""
Clothing-fit QA tool for the Meta avatar bodies (Phase 3, T4).

Loads a meta template (meta_male.blend / meta_female.blend), imports one or
more existing wardrobe GLBs (skinned shells authored against the REALISTIC
body), re-binds each to the meta body's own armature by bone name (the exact
technique SandboxViewer.attachSkinned uses at runtime: retarget the Armature
modifier + drop the asset's own imported armature copy — bone names are
identical across every CC3+ base, realistic or toon, per Phase 1), and
renders front + side views of the dressed figure so clipping/floating can be
inspected visually. Read-only against the template: nothing is saved back.

This does NOT modify assets/shared/, the sandbox, or any realistic pipeline
file — it only proves (or disproves) whether the existing shells fit the
toon-proportioned meta body well enough to reuse as-is.

Usage:
  blender --background --python test_clothing_fit.py -- \
      <meta_template.blend> <Prefix> <out_dir> <tag> <item_glb> [<item_glb> ...]

  <Prefix>   MetaMale | MetaFemale (object prefix, see meta_avatar/renderer/style.json)
  <out_dir>  where front_<tag>.png / side_<tag>.png are written
  <tag>      filename tag, e.g. "male_outfit1"

Example (male hoodie+tshirt+jeans+sneakers together):
  blender --background --python meta_avatar/blender/scripts/test_clothing_fit.py -- \
      meta_avatar/blender/base/meta_male.blend MetaMale \
      meta_avatar/blender/clothing_fit male_outfit \
      assets/shared/clothes/hoodie/hoodie.glb \
      assets/shared/clothes/jeans/jeans.glb \
      assets/shared/shoes/sneakers/sneakers.glb
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, PREFIX, OUT_DIR, TAG = argv[0], argv[1], os.path.abspath(argv[2]), argv[3]
ITEM_GLBS = argv[4:]

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(TEMPLATE))
arm = bpy.data.objects[f"{PREFIX}_Armature"]
body = bpy.data.objects[f"{PREFIX}_Body"]

equipped = []
for glb in ITEM_GLBS:
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(glb))
    imported = [o for o in bpy.data.objects if o.name not in before]

    imported_arm = next((o for o in imported if o.type == 'ARMATURE'), None)
    # Blender's gltf importer sometimes adds small placeholder mesh objects
    # (e.g. "Icosphere", no vertex groups) alongside the real skinned shell --
    # drop anything that isn't actually bound to the skeleton. Build both
    # lists before deleting so we never iterate over a freed object.
    junk = [o for o in imported if o.type == 'MESH' and not o.vertex_groups]
    meshes = [o for o in imported if o.type == 'MESH' and o.vertex_groups]
    for o in junk:
        bpy.data.objects.remove(o, do_unlink=True)

    unmatched = set()
    for mesh in meshes:
        vg_names = {vg.name for vg in mesh.vertex_groups}
        arm_bone_names = {b.name for b in arm.data.bones}
        unmatched |= (vg_names - arm_bone_names)
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE':
                mod.object = arm
        # Re-parent to the meta armature WITHOUT touching the mesh's current
        # world transform. mesh.matrix_basis is typically near-identity (the
        # 0.01 import scale lives on the *parent* armature, not the mesh), so
        # naively setting matrix_parent_inverse = arm.matrix_world.inverted()
        # cancels that scale out and blows the mesh up ~100x off-camera.
        # keep_transform=True computes the correct parent-inverse instead.
        with bpy.context.temp_override(active_object=arm,
                                        selected_editable_objects=[mesh, arm]):
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        equipped.append(mesh.name)

    if imported_arm is not None:
        bpy.data.objects.remove(imported_arm, do_unlink=True)

    label = os.path.basename(glb)
    if unmatched:
        print(f"[fit-test] {label}: UNMATCHED bone/vertex-groups -> {sorted(unmatched)}")
    else:
        print(f"[fit-test] {label}: bound cleanly to {arm.name} ({len(meshes)} mesh(es))")

print(f"[fit-test] equipped meshes: {equipped}")

# ---------------------------------------------------------------- render
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
scene.world = world

cam_data = bpy.data.cameras.new("C"); cam_data.lens = 50
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
key = bpy.data.lights.new("Key", 'SUN'); key.energy = 3.0
ko = bpy.data.objects.new("Key", key); scene.collection.objects.link(ko)
ko.rotation_euler = (math.radians(60), 0, math.radians(15))
fill = bpy.data.lights.new("Fill", 'SUN'); fill.energy = 1.5
fo = bpy.data.objects.new("Fill", fill); scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(195))

# full-figure framing (same idea as render_meta_look.py's "body" view)
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
head = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
target = Vector((0, head.y, (min(zs) + max(zs)) / 2))

VIEWS = {
    "front": Vector((0, -2.6, 0.0)),
    "side": Vector((-2.6, 0.0, 0.0)),
}

os.makedirs(OUT_DIR, exist_ok=True)
for name, offset in VIEWS.items():
    cam.location = target + offset
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, f"{name}_{TAG}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[fit-test] rendered {scene.render.filepath}")
