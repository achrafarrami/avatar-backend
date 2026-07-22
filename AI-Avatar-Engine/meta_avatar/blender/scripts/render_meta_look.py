"""
Render front + three-quarter views of a meta template with a set of identity
params applied. Same camera/lighting as blender/scripts/render_avatar_params.py
(portrait 85mm, key+fill suns, head-framed) so meta and realistic renders are
directly comparable. Used to dial in the Meta stylization look and to verify
new morphs.

Usage:
  blender --background --python render_meta_look.py -- \
      <template.blend> <Prefix> <out_dir> '<params_json>' [views] [tag] \
      [--raw '<raw_keys_json>']
params_json: flat snake_case engine params (0..1). {} for neutral.
views: comma list of front,three_quarter,body (default front,three_quarter).
tag:   filename suffix, default "look".
--raw: shape-key name -> value (-1..1) driven directly on EVERY mesh that has
       the key (the cross-mesh contract) — for meta-only morphs like head_size
       / body_weight that aren't in morph_definitions.json.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

SHARED = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "blender", "scripts"))
sys.path.insert(0, SHARED)
from morph_controller import MorphController  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
raw = {}
if "--raw" in argv:
    i = argv.index("--raw")
    raw = json.loads(argv[i + 1])
    argv = argv[:i] + argv[i + 2:]
TEMPLATE, PREFIX, OUT_DIR = os.path.abspath(argv[0]), argv[1], os.path.abspath(argv[2])
params = json.loads(argv[3]) if len(argv) > 3 else {}
VIEWS = [v.strip() for v in (argv[4] if len(argv) > 4
                             else "front,three_quarter").split(",") if v.strip()]
TAG = argv[5] if len(argv) > 5 else "look"

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]

mc = MorphController(os.path.join(SHARED, "morph_definitions.json"))
if params:
    applied = mc.apply(params)
    print(f"[meta-look] applied {len(params)} params -> {len(applied)} keys")

# raw meta-only keys: drive on every mesh that has them (cross-mesh contract)
for name, val in raw.items():
    hits = 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        kb = obj.data.shape_keys.key_blocks.get(name)
        if kb is not None:
            kb.value = float(val)
            hits += 1
    print(f"[meta-look] raw {name}={val} on {hits} meshes")

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

head = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
target = Vector((0, head.y, head.z + 0.075))
tq = math.radians(35)
OFFSETS = {"front": Vector((0, -0.85, 0.0)),
           "three_quarter": Vector((-0.85 * math.sin(tq), -0.85 * math.cos(tq), 0.0))}

# full-body view: frame the whole figure (target mid-torso, camera pulled back)
body_obj = bpy.data.objects[f"{PREFIX}_Body"]
zs = [(body_obj.matrix_world @ v.co).z for v in body_obj.data.vertices]
body_target = Vector((0, head.y, (min(zs) + max(zs)) / 2))
body_offset = Vector((0, -2.6, 0.0))

os.makedirs(OUT_DIR, exist_ok=True)
for v in VIEWS:
    if v == "body":
        cam.location = body_target + body_offset
        cam.rotation_euler = (body_target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    elif v in OFFSETS:
        cam.location = target + OFFSETS[v]
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        continue
    scene.render.filepath = os.path.join(OUT_DIR, f"{TAG}_{v}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[meta-look] rendered {scene.render.filepath}")
