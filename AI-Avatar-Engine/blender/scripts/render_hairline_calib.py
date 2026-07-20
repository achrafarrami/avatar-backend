"""
Render the template WEARING HAIR for the AI pipeline's hairline
calibration (forehead_hairline measurement).

The templates are bald, so the anchor for the photo-side hairline
measurement can't come from the standard neutral renders. These renders
equip a wardrobe hair asset (rigid, bone-attached — exactly how hair
behaves on the runtime avatar: identity morphs move the forehead skin
while the hair stays put) and calibrate.py --hairline-renders measures
them through the same preprocessing + face-parsing code as user photos,
so landmarker/parser bias cancels.

Renders: neutral + lo/hi (0.2/0.8) for the parameters that measurably
move the hairline ratio (identified by a mesh response probe: jaw_height,
forehead_height, cheekbone_height, eyebrow_height, chin_size). Other
params' hairline responses are below noise and treated as zero.

Usage:
  blender --background --python render_hairline_calib.py -- \
      <template.blend> <out_dir> [<Prefix>=Male] [<hair_id>=hair_w06] [<scale>=1.0]

NOTE: there are no male hair assets yet, so the male template also wears
the (female-fitted) style — only the front hairline band matters for this
measurement. Pass scale 1.09 for the male head (probe-measured: male head
width 18.46cm vs female 16.93cm), otherwise the hairline sits falsely
receded on the bigger skull.
"""
import bpy
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
TEMPLATE = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
PREFIX = argv[2] if len(argv) > 2 else "Male"
HAIR_ID = argv[3] if len(argv) > 3 else "hair_w06"
HAIR_SCALE = float(argv[4]) if len(argv) > 4 else 1.0

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
from morph_controller import MorphController

ENGINE_ROOT = os.path.dirname(SCRIPTS.rstrip(os.sep))  # .../AI-Avatar-Engine/blender
ENGINE_ROOT = os.path.dirname(ENGINE_ROOT)             # .../AI-Avatar-Engine
HAIR_GLB = os.path.join(ENGINE_ROOT, "frontend", "threejs-viewer", "public",
                        "wardrobe", "hair", HAIR_ID, f"{HAIR_ID}.glb")

SWEEP_PARAMS = ["forehead_height", "jaw_height", "cheekbone_height",
                "eyebrow_height", "chin_size"]

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
arm = bpy.data.objects[f"{PREFIX}_Armature"]
mc = MorphController(os.path.join(SCRIPTS, "morph_definitions.json"))

# ---- equip hair (translation-only bone-relative, see import_hair_pack) --
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HAIR_GLB)
new = [o for o in bpy.data.objects if o not in before]
head_origin = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
for ob in new:
    if ob.type == 'MESH':
        mw = ob.matrix_world.copy()
        ob.parent = None
        ob.matrix_world = mw
        # object origin sits at the head origin after this translation, so
        # the uniform head-size scale below pivots correctly around it
        ob.matrix_world.translation = ob.matrix_world.translation + head_origin
        ob.scale = (HAIR_SCALE, HAIR_SCALE, HAIR_SCALE)
        # natural dark hair so the segmentation model reads it reliably
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

# ---- camera/lights identical to render_head_views.py -------------------
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 1024
world = bpy.data.worlds.new("HairCalibWorld")
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
target = Vector((0, head_origin.y, head_origin.z + 0.075))
cam.location = target + Vector((0, -0.85, 0))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

os.makedirs(OUT_DIR, exist_ok=True)


def render(name):
    scene.render.filepath = os.path.join(OUT_DIR, name)
    bpy.ops.render.render(write_still=True)
    print(f"[hairline-calib] rendered {name}")


mc.reset()
render("neutral_haired.png")
for pname in SWEEP_PARAMS:
    for tag, val in (("lo", 0.2), ("hi", 0.8)):
        mc.apply({pname: val})
        render(f"{pname}_{tag}.png")
mc.reset()
print(f"[hairline-calib] done -> {OUT_DIR}")
