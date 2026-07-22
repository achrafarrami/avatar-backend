"""
T3 (hair-assets): verify the beard fit on the Meta male template.

Unlike the bone-attach items (fit_wardrobe_batch.py), the beard is
attach_type "skinned" at runtime -- WardrobeManager.attachSkinned() drops
the asset's OWN imported armature entirely and rebinds its skinned mesh to
the AVATAR's bones by name (see viewer.js). A rigid parent+translate (what
fit_wardrobe_batch.py does for bone items) is wrong here: the beard glb
carries its own full copy of the realistic male's armature, in that rig's
own world position, so translating the whole thing on top double-counts
the position. This script instead reproduces the true runtime behavior:
delete the beard's own imported armature, retarget its Armature modifier +
reparent the mesh directly onto the Meta template's own armature (matched
by bone name -- same topology/bone names on every CC3+ base, confirmed
project-wide), then apply the offset/scale candidate directly as the
mesh's own object-local transform (its parent -- the armature object -- has
an identity world transform, same as the runtime's holder Group parented to
avatarRoot, verified empirically: no bone-rest-transform distortion here).

Usage:
  blender --background --python fit_beard_meta.py -- \
      <meta_template.blend> <Prefix> <beard.glb> <out_dir> <tag> \
      '<offset_json>' <scale>
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, PREFIX, GLB, OUT_DIR, TAG = argv[0], argv[1], os.path.abspath(argv[2]), os.path.abspath(argv[3]), argv[4]
OFFSET = json.loads(argv[5])
SCALE = float(argv[6])

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
scene.world = world
cam_data = bpy.data.cameras.new("C"); cam_data.lens = 85
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
key = bpy.data.lights.new("Key", 'SUN'); key.energy = 3.0
ko = bpy.data.objects.new("Key", key); scene.collection.objects.link(ko)
ko.rotation_euler = (math.radians(60), 0, math.radians(15))
fill = bpy.data.lights.new("Fill", 'SUN'); fill.energy = 1.5
fo = bpy.data.objects.new("Fill", fill); scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(195))

head_origin = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
target = Vector((0, head_origin.y, head_origin.z + 0.075))
tq = math.radians(35)
OFFSETS = {"front": Vector((0, -0.85, 0.0)),
           "three_quarter": Vector((-0.85 * math.sin(tq), -0.85 * math.cos(tq), 0.0))}


def render(tag):
    for v, off in OFFSETS.items():
        cam.location = target + off
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(OUT_DIR, f"{tag}_{v}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[fit-beard] rendered {scene.render.filepath}")


def import_and_rebind():
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=GLB)
    new_objs = [o for o in bpy.data.objects if o.name not in before]
    own_arm = next((o for o in new_objs if o.type == 'ARMATURE'), None)
    # Blender's gltf importer sometimes adds small placeholder mesh objects
    # (e.g. "Icosphere", no vertex groups) alongside the real skinned shell.
    junk = [o for o in new_objs if o.type == 'MESH' and not o.vertex_groups]
    meshes = [o for o in new_objs if o.type == 'MESH' and o.vertex_groups]
    for o in junk:
        print(f"[fit-beard] removing stray non-deform object from glb: {o.name} ({o.type})")
        bpy.data.objects.remove(o, do_unlink=True)

    mesh = meshes[0]
    vg_names = {vg.name for vg in mesh.vertex_groups}
    arm_bone_names = {b.name for b in arm.data.bones}
    unmatched = vg_names - arm_bone_names
    if unmatched:
        print(f"[fit-beard] WARNING unmatched vertex groups: {unmatched}")
    for m in mesh.modifiers:
        if m.type == 'ARMATURE':
            m.object = arm
    # Re-parent to the meta armature WITHOUT touching the mesh's current
    # world transform -- the 0.01 import scale lives on the parent armature,
    # not the mesh, so naively setting matrix_parent_inverse =
    # arm.matrix_world.inverted() cancels that scale out and blows the mesh
    # up ~100x off-camera. keep_transform=True via parent_set computes the
    # correct parent-inverse instead. NOTE: temp_override(active_object=...,
    # selected_editable_objects=[...]) silently no-ops for this operator in
    # --background mode (verified: mesh.parent stayed unchanged) -- use real
    # selection state instead.
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    result = bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    if mesh.parent != arm:
        print(f"[fit-beard] WARNING parent_set result={result} but mesh.parent={mesh.parent} (expected {arm.name})")
    if own_arm:
        bpy.data.objects.remove(own_arm, do_unlink=True)
    return mesh


os.makedirs(OUT_DIR, exist_ok=True)

mesh = import_and_rebind()
render(f"{TAG}_unfitted")

# NOTE: this Blender template's armature carries a 0.01 "import scale" (CC/
# FBX-era authoring convention, confirmed via arm.matrix_world.to_scale());
# naively setting mesh.location/mesh.scale (matrix_basis) gets pre-multiplied
# by that parent scale+rotation before reaching world space, crushing any
# offset to ~1% of its intended size -- the same class of distortion found
# (and fixed) in the bone-attach runtime path. This is a Blender-authoring
# artifact only: the exported GLB / three.js runtime has no such lingering
# scale (verified empirically in the live sandbox -- the beard holder's
# parent has an identity transform there), so it does not affect the actual
# item.json fit values, only how this *verification* script must apply them
# to preview correctly. Fix: set matrix_world directly (world-space offset,
# scale about the mesh's own current transform) so Blender back-solves the
# correct matrix_basis against the 0.01-scaled parent.
base_matrix = mesh.matrix_world.copy()
from mathutils import Matrix
mesh.matrix_world = Matrix.Translation(Vector(OFFSET)) @ base_matrix @ Matrix.Scale(SCALE, 4)
render(TAG)
print(f"[fit-beard] {TAG}: scale={SCALE:.4f} offset={OFFSET}")
print("[done] beard fit complete")
