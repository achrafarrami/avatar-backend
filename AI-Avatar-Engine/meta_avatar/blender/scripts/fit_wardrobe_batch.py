"""
T3 (hair-assets): batch-render bone-attach wardrobe items on a Meta template
with a candidate per-style "meta" transform override, so the fit can be
verified visually before it's written into item.json. Mirrors, at render
time, the runtime placement math in frontend/threejs-viewer/src/viewer.js
attachAsset() (item authored bone-relative -> placed at the bone's world
position) plus the additive offset/scale WardrobeManager.equip() applies
for a "styles.meta" override -- so what's rendered here is what the engine
is *intended* to show once offset/scale are semantically in world meters
(see the offset-application defect reported separately to main; this script
still verifies the CORRECT target geometry regardless of that bug).

Same camera/lighting as render_meta_look.py (85mm portrait, key+fill suns)
for "head"-region jobs so results are comparable to other Phase-3 renders.
"hand"-region jobs (wrist accessories) use a closer wrist-framed camera.

Usage:
  blender --background --python fit_wardrobe_batch.py -- \
      <template.blend> <Prefix> <out_dir> '<jobs_json>'

jobs_json: list of objects, each:
  {
    "id": "hair_w01",
    "glb": "<absolute or repo-relative path to the item's .glb>",
    "attach_bone": "CC_Base_Head",
    "region": "head" | "hand",           # camera framing choice
    "offset": [x,y,z],                    # Blender-frame meters, candidate fit
    "scale": 1.0,
    "tag": "hair_w01_female",
    "render_unfitted": true               # also render offset=0/scale=1 for comparison
  }
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, PREFIX, OUT_DIR = os.path.abspath(argv[0]), argv[1], os.path.abspath(argv[2])
JOBS = json.loads(argv[3])

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]
body_obj = bpy.data.objects[f"{PREFIX}_Body"]
bones = arm.data.bones

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

head_origin = arm.matrix_world @ bones["CC_Base_Head"].head_local
head_target = Vector((0, head_origin.y, head_origin.z + 0.075))
tq = math.radians(35)
HEAD_OFFSETS = {
    "front": Vector((0, -0.85, 0.0)),
    "three_quarter": Vector((-0.85 * math.sin(tq), -0.85 * math.cos(tq), 0.0)),
}


def render_head(tag):
    for v, off in HEAD_OFFSETS.items():
        cam.location = head_target + off
        cam.rotation_euler = (head_target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(OUT_DIR, f"{tag}_{v}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[fit] rendered {scene.render.filepath}")


def render_hand(tag, hand_origin):
    target = hand_origin
    offs = {"front": Vector((0.05, -0.28, 0.05)),
            "three_quarter": Vector((-0.22, -0.18, 0.05))}
    for v, off in offs.items():
        cam.location = target + off
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(OUT_DIR, f"{tag}_{v}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[fit] rendered {scene.render.filepath}")


os.makedirs(OUT_DIR, exist_ok=True)

for job in JOBS:
    glb = os.path.abspath(job["glb"])
    bone_name = job["attach_bone"]
    region = job.get("region", "head")
    tag = job["tag"]

    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_scene.gltf(filepath=glb)
    new_objs = [o for o in bpy.data.objects if o not in before]
    if not new_objs:
        print(f"[fit] WARNING: no objects imported for {tag} ({glb})")
        continue
    roots = [o for o in new_objs if o.parent is None or o.parent not in new_objs]

    rig = bpy.data.objects.new(f"FitRig_{tag}", None)
    scene.collection.objects.link(rig)
    for r in roots:
        r.parent = rig
        # keep each root's own current world transform when reparenting
        r.matrix_parent_inverse = rig.matrix_world.inverted()

    bone = bones[bone_name]
    bone_origin = arm.matrix_world @ bone.head_local

    if region == "hand":
        render_fn = lambda t: render_hand(t, bone_origin)
    else:
        render_fn = render_head

    if job.get("render_unfitted"):
        rig.location = bone_origin
        rig.scale = (1.0, 1.0, 1.0)
        render_fn(f"{tag}_unfitted")

    off = Vector(job.get("offset", [0, 0, 0]))
    s = float(job.get("scale", 1.0))
    rig.location = bone_origin + off
    rig.scale = (s, s, s)
    render_fn(tag)
    print(f"[fit] {tag}: scale={s:.4f} offset={list(off)} bone_origin={list(bone_origin)}")

    # cleanup: remove this job's objects before the next import
    to_remove = new_objs + [rig]
    meshes = {o.data for o in new_objs if o.type == 'MESH' and o.data}
    armatures = {o.data for o in new_objs if o.type == 'ARMATURE' and o.data}
    for o in to_remove:
        bpy.data.objects.remove(o, do_unlink=True)
    for m in meshes:
        if m.users == 0:
            bpy.data.meshes.remove(m)
    for a in armatures:
        if a.users == 0:
            bpy.data.armatures.remove(a)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)

print("[done] batch complete")
