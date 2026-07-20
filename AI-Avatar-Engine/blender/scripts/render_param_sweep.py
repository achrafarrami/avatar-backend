"""
Render a head view of the template at LOW (0.2) and HIGH (0.8) values of
every identity parameter — the input for calibrate.py --fit-gains (front
view, MediaPipe measurements) and --fit-profile (left view, silhouette
measurements), which fit each parameter's calibration response from the
avatar's actual morph behavior (no hand-guessed gains anywhere).

Usage:
  blender --background --python render_param_sweep.py -- \
      <template.blend> <out_dir> [<Prefix>=Male] [<view>=front|left|right]
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
PREFIX = argv[2] if len(argv) > 2 else "Male"
VIEW = argv[3] if len(argv) > 3 else "front"
VIEW_OFFSETS = {"front": Vector((0, -0.85, 0)),
                "left": Vector((-0.85, 0, 0)),
                "right": Vector((0.85, 0, 0))}

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
from morph_controller import MorphController

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]
mc = MorphController(os.path.join(SCRIPTS, "morph_definitions.json"))

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 800
world = bpy.data.worlds.new("SweepWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
scene.world = world
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 85
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
key = bpy.data.lights.new("Key", 'SUN')
key.energy = 3.0
ko = bpy.data.objects.new("Key", key)
scene.collection.objects.link(ko)
ko.rotation_euler = (math.radians(60), 0, math.radians(15))
fill = bpy.data.lights.new("Fill", 'SUN')
fill.energy = 1.5
fo = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(195))

head = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
target = Vector((0, head.y, head.z + 0.075))
cam.location = target + VIEW_OFFSETS[VIEW]
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

os.makedirs(OUT_DIR, exist_ok=True)
params = list(mc.list_params())
for pname in params:
    for tag, val in (("lo", 0.2), ("hi", 0.8)):
        mc.apply({pname: val})           # reset_first=True -> isolated param
        scene.render.filepath = os.path.join(OUT_DIR, f"{pname}_{tag}.png")
        bpy.ops.render.render(write_still=True)
    print(f"[sweep] {pname}")
mc.reset()
print(f"[sweep] {len(params) * 2} renders -> {OUT_DIR}")
