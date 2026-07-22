"""
Render a synthetic front/left/right PHOTO SET (identity params applied,
optional hair) for feeding the AI photo pipeline (`ai/photo_analyzer/pipeline.py`)
when no real photo sets are available.

This is test-data tooling only — it does not touch the pipeline, the AI
models, or morph_definitions.json. It combines two already-validated
techniques used by the calibration loop:
  - identity params applied via MorphController (as render_avatar_params.py
    does for its "front" view)
  - true left/right PROFILE camera placement identical to
    render_head_views.py (render_avatar_params.py only offers a 35-degree
    "three_quarter" view, which is too shallow for the pipeline's expected
    profile yaw window of ~30-100 degrees — see pipeline.py's
    expect_yaw=-65/+65, yaw_tolerance=35 for the left/right photos)
  - optional hair equip identical to render_hairline_calib.py (bone-relative
    GLB import, crown/head-anchored uniform scale, dark recolor so the
    segmentation model reads it reliably)

Usage:
  blender --background --python render_synthetic_photoset.py -- \
      <template.blend> <out_dir> <Prefix> <params.json> [<hair_id>] [<hair_scale>]

Prefix: "Male" or "Female" (selects <Prefix>_Armature / <Prefix>_Body).
params.json: flat snake_case engine params, e.g. {"face_width": 0.8}.
hair_id: optional wardrobe hair asset id (e.g. "hair_w03"); omit or pass
         "none" to render bald. hair_scale: uniform scale for the hair mesh,
         default 1.0 (male heads are wider — use ~1.09 per
         render_hairline_calib.py's measured note).

Outputs <out_dir>/front.png, left.png, right.png (1024x1024).
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
PREFIX = argv[2]
PARAMS_PATH = os.path.abspath(argv[3])
HAIR_ID = argv[4] if len(argv) > 4 and argv[4].lower() != "none" else None
HAIR_SCALE = float(argv[5]) if len(argv) > 5 else 1.0

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
from morph_controller import MorphController
import json

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]
mc = MorphController(os.path.join(SCRIPTS, "morph_definitions.json"))

with open(PARAMS_PATH) as f:
    params = json.load(f)
known = mc.list_params()
unknown = [k for k in params if k not in known]
if unknown:
    print(f"[synth] WARNING: dropping unknown morph parameters: {unknown}")
    params = {k: v for k, v in params.items() if k in known}
applied = mc.apply(params)
print(f"[synth] applied {len(params)} params -> {len(applied)} shape keys")

head_origin = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local

# ---- optional hair equip, identical approach to render_hairline_calib.py --
if HAIR_ID:
    ENGINE_ROOT = os.path.dirname(SCRIPTS.rstrip(os.sep))  # .../blender
    ENGINE_ROOT = os.path.dirname(ENGINE_ROOT)             # .../AI-Avatar-Engine
    hair_glb = os.path.join(ENGINE_ROOT, "frontend", "threejs-viewer", "public",
                            "wardrobe", "hair", HAIR_ID, f"{HAIR_ID}.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=hair_glb)
    new = [o for o in bpy.data.objects if o not in before]
    for ob in new:
        if ob.type == 'MESH':
            mw = ob.matrix_world.copy()
            ob.parent = None
            ob.matrix_world = mw
            ob.matrix_world.translation = ob.matrix_world.translation + head_origin
            ob.scale = (HAIR_SCALE, HAIR_SCALE, HAIR_SCALE)
            for slot in ob.material_slots:
                mat = slot.material
                if mat and mat.use_nodes:
                    for n in mat.node_tree.nodes:
                        if n.type == 'BSDF_PRINCIPLED':
                            n.inputs["Base Color"].default_value = (0.06, 0.04, 0.025, 1)
                            n.inputs["Roughness"].default_value = 0.8
    for ob in new:
        if ob.type == 'ARMATURE':
            bpy.data.objects.remove(ob, do_unlink=True)
    print(f"[synth] equipped hair '{HAIR_ID}' (scale {HAIR_SCALE})")

# ---- camera/lights identical to render_head_views.py ---------------------
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024

world = bpy.data.worlds.new("SynthWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
scene.world = world

cam_data = bpy.data.cameras.new("SynthCam")
cam_data.lens = 85
cam = bpy.data.objects.new("SynthCam", cam_data)
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

target = Vector((0, head_origin.y, head_origin.z + 0.075))

os.makedirs(OUT_DIR, exist_ok=True)
for tag, offset in (("front", Vector((0, -0.85, 0.0))),
                    ("left", Vector((-0.85, 0.0, 0.0))),
                    ("right", Vector((0.85, 0.0, 0.0)))):
    cam.location = target + offset
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[synth] rendered {scene.render.filepath}")

print(f"[synth] done -> {OUT_DIR}")
