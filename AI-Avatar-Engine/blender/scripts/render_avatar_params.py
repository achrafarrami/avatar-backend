"""
Apply AI-predicted engine parameters to a template avatar and render it.

Used for side-by-side photo <-> avatar validation: the pipeline predicts
avatar parameters from photos, this script renders what those parameters
actually look like on the template. The front camera is IDENTICAL to
render_head_views.py (same lens/distance/target/lighting), so the renders
are directly comparable with the pipeline's calibration anchors.

Accepts either params format the pipeline produces:
  - flat snake_case engine params, e.g. {"face_width": 0.62, ...}
    (the identity_paste.json format)
  - full avatar_parameters.json (has a "face" key with camelCase names;
    converted back to snake_case via the pipeline's CAMEL contract table)

Usage:
  blender --background --python render_avatar_params.py -- \
      <params.json> <out_dir> [gender] [views]
gender: "male" (default) or "female" — selects the template.
views:  comma list, default "front,three_quarter". front = same camera as
        render_head_views.py; three_quarter = camera orbited 35 degrees
        horizontally around the head (same target/distance).
Outputs <out_dir>/avatar_<view>.png at 1024x1024.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)
from morph_controller import MorphController

# camelCase (avatar_parameters.json "face" contract) -> engine snake_case.
# Inverse of the CAMEL table in ai/photo_analyzer/pipeline.py — note
# faceLength -> jaw_height is a deliberate rename, not mechanical.
CAMEL_TO_SNAKE = {
    "faceWidth": "face_width", "foreheadHeight": "forehead_height",
    "cheekSize": "cheek_size", "cheekboneHeight": "cheekbone_height",
    "jawWidth": "jaw_width", "faceLength": "jaw_height",
    "jawAngle": "jaw_angle", "chinSize": "chin_size",
    "noseWidth": "nose_width", "noseLength": "nose_length",
    "noseBridgeHeight": "nose_bridge_height", "noseTipSize": "nose_tip_size",
    "eyeSize": "eye_size", "eyeDistance": "eye_distance",
    "eyeTilt": "eye_tilt", "eyebrowHeight": "eyebrow_height",
    "mouthWidth": "mouth_width", "lipThickness": "lip_thickness",
    "philtrumLength": "philtrum_length", "earSize": "ear_size",
}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PARAMS_PATH = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
GENDER = argv[2].lower() if len(argv) > 2 else "male"
VIEWS = [v.strip() for v in (argv[3] if len(argv) > 3
                             else "front,three_quarter").split(",") if v.strip()]

with open(PARAMS_PATH, encoding="utf-8-sig") as f:  # tolerate Windows BOM
    data = json.load(f)
if "face" in data:  # full avatar_parameters.json -> engine snake_case
    params = {CAMEL_TO_SNAKE[k]: v for k, v in data["face"].items()
              if k in CAMEL_TO_SNAKE}
    dropped = [k for k in data["face"] if k not in CAMEL_TO_SNAKE]
    if dropped:
        print(f"[render] WARNING: ignoring unknown face params: {dropped}")
else:
    params = {k: v for k, v in data.items() if isinstance(v, (int, float))}

PREFIX = GENDER.capitalize()
TEMPLATE = os.path.join(SCRIPTS_DIR, "..", "templates", f"{GENDER}_base.blend")
bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]

mc = MorphController(os.path.join(SCRIPTS_DIR, "morph_definitions.json"))
known = mc.list_params()
unknown = [k for k in params if k not in known]
if unknown:
    print(f"[render] WARNING: dropping unknown morph parameters: {unknown}")
    params = {k: v for k, v in params.items() if k in known}
applied = mc.apply(params)
print(f"[render] applied {len(params)} params -> {len(applied)} shape keys")

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

# camera distance ~0.85m: head fills the frame like a portrait photo.
# three_quarter = the front offset orbited 35 degrees around the vertical axis
tq = math.radians(35)
OFFSETS = {
    "front": Vector((0, -0.85, 0.0)),
    "three_quarter": Vector((-0.85 * math.sin(tq), -0.85 * math.cos(tq), 0.0)),
}

os.makedirs(OUT_DIR, exist_ok=True)
for tag in VIEWS:
    if tag not in OFFSETS:
        print(f"[render] WARNING: unknown view '{tag}' "
              f"(valid: {sorted(OFFSETS)}), skipping")
        continue
    cam.location = target + OFFSETS[tag]
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, f"avatar_{tag}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[render] rendered {scene.render.filepath}")
