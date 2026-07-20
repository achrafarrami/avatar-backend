"""
Render neutral head views (front / left / right) of a template avatar.

Used by the AI photo pipeline's calibration system: the pipeline runs
MediaPipe on these renders and records the measurements as the "0.5 neutral"
anchors in ai/photo_analyzer/calibration/calibration.json. Because photo and
render go through the identical measurement code, systematic landmarker bias
cancels out of the photo-vs-avatar comparison.

Usage:
  blender --background --python render_head_views.py -- \
      <template.blend> <out_dir> [<Prefix>]
Prefix defaults to "Male" (objects <Prefix>_Armature / <Prefix>_Body).
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
PREFIX = argv[2] if len(argv) > 2 else "Male"

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024

world = bpy.data.worlds.new("CalibWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
scene.world = world

cam_data = bpy.data.cameras.new("CalibCam")
cam_data.lens = 85  # portrait lens: minimal perspective distortion
cam = bpy.data.objects.new("CalibCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

key = bpy.data.lights.new("Key", 'SUN')
key.energy = 3.0
key_obj = bpy.data.objects.new("Key", key)
scene.collection.objects.link(key_obj)
key_obj.rotation_euler = (math.radians(60), 0, math.radians(15))
fill = bpy.data.lights.new("Fill", 'SUN')
fill.energy = 1.5
fill_obj = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fill_obj)
fill_obj.rotation_euler = (math.radians(75), 0, math.radians(195))

head_world = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
target = Vector((0, head_world.y, head_world.z + 0.075))

os.makedirs(OUT_DIR, exist_ok=True)
# camera distance ~0.85m: head fills the frame like a portrait photo
for tag, offset in (("front", Vector((0, -0.85, 0.0))),
                    ("left", Vector((-0.85, 0.0, 0.0))),
                    ("right", Vector((0.85, 0.0, 0.0)))):
    cam.location = target + offset
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, f"neutral_{tag}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[calib] rendered {scene.render.filepath}")
