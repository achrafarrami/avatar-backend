"""
Deformation QA for pro-wardrobe garments: imports each exported GLB,
re-binds it to the template armature BY BONE NAME (the exact runtime
contract of SandboxViewer.attachSkinned), applies test poses and renders.

Usage:
  blender --background --python pose_test_wardrobe.py -- <repo_root> <gender> <ids...>
Renders -> output/wardrobe_pro/<id>/pose_<pose>.png
"""
import bpy
import math
import os
import sys
import json
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.abspath(argv[0])
GENDER = argv[1]
IDS = argv[2:]
ENG = os.path.join(ROOT, "AI-Avatar-Engine")
OUT = os.path.join(ENG, "output", "wardrobe_pro")
TPL = os.path.join(ENG, "meta_avatar", "blender", "base", f"meta_{GENDER}.blend")
PREFIX = {"male": "MetaMale", "female": "MetaFemale"}[GENDER]

with open(os.path.join(OUT, "build_report.json")) as f:
    REPORT = json.load(f)
SHARED = os.path.join(ENG, "assets", "shared")

bpy.ops.wm.open_mainfile(filepath=TPL)
body = bpy.data.objects[f"{PREFIX}_Body"]
arm = bpy.data.objects[f"{PREFIX}_Armature"]
arm.animation_data_clear()   # FBX bind-pose action re-evaluates on every
# render frame and silently wipes matrix_basis poses

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 560
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.72, 0.72, 0.75, 1)
scene.world = world
key = bpy.data.lights.new("Key", 'SUN')
key.energy = 3.2
ko = bpy.data.objects.new("Key", key)
scene.collection.objects.link(ko)
ko.rotation_euler = (math.radians(55), 0, math.radians(25))
fill = bpy.data.lights.new("Fill", 'SUN')
fill.energy = 1.1
fo = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(70), 0, math.radians(200))
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 60
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def rot_bone(name, axis, deg):
    pb = arm.pose.bones.get(name)
    if not pb:
        return
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    ml = pb.bone.matrix_local.to_3x3().to_4x4()
    pb.matrix_basis = pb.matrix_basis @ (ml.inverted() @ R @ ml)


def clear_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()


POSES = {   # signs verified empirically: +Y on the LEFT upperarm = down
    "idle": [],
    "arms_down": [("CC_Base_L_Upperarm", 'Y', 42), ("CC_Base_R_Upperarm", 'Y', -42)],
    "arms_up": [("CC_Base_L_Upperarm", 'Y', -55), ("CC_Base_R_Upperarm", 'Y', 55)],
    "elbow_bend": [("CC_Base_L_Upperarm", 'Y', 30), ("CC_Base_R_Upperarm", 'Y', -30),
                   ("CC_Base_L_Forearm", 'Z', -70), ("CC_Base_R_Forearm", 'Z', 70)],
    "sit": [("CC_Base_L_Thigh", 'X', -80), ("CC_Base_R_Thigh", 'X', -80),
            ("CC_Base_L_Calf", 'X', 85), ("CC_Base_R_Calf", 'X', 85)],
}

report = {}
for gid in IDS:
    rep = REPORT.get(gid)
    if not rep:
        print(f"[skip] {gid}: not in build report")
        continue
    glb = os.path.join(SHARED, rep["glb"])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = set(bpy.data.objects) - before
    gobj = next((o for o in new if o.type == 'MESH' and gid in o.name), None)
    if gobj is None:
        gobj = next((o for o in new if o.type == 'MESH'
                     and len(o.data.vertices) > 100), None)
    # runtime contract: discard the asset's armature copy, bind to ours
    for o in list(new):
        if o is not gobj and o.type in ('ARMATURE', 'EMPTY'):
            continue
    for m in list(gobj.modifiers):
        if m.type == 'ARMATURE':
            gobj.modifiers.remove(m)
    mod = gobj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    mw = gobj.matrix_world.copy()   # unparent but HOLD the world transform
    gobj.parent = None              # (identity here = 100x giant, invisible)
    gobj.matrix_world = mw
    for o in list(new):
        if o is not gobj and o.type == 'MESH' and len(o.data.vertices) <= 100:
            bpy.data.objects.remove(o, do_unlink=True)
        elif o is not gobj and o.type in ('ARMATURE', 'EMPTY'):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = True
    for o in (body, gobj):
        o.hide_render = False
    for extra in bpy.data.objects:      # show the template's face parts
        if extra.type == 'MESH' and extra.name.startswith(("CC_Base", "Toon")):
            extra.hide_render = False
    outs = {}
    for pose, ops in POSES.items():
        clear_pose()
        for name, axis, deg in ops:
            rot_bone(name, axis, deg)
        bpy.context.view_layer.update()
        target = Vector((0, 0, 1.05 if pose == "sit" else 1.15))
        for tag, d in (("f", Vector((0, -1, 0.15))), ("q", Vector((0.8, -0.8, 0.25)))):
            cam.location = target + d.normalized() * 2.3
            cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(OUT, gid, f"pose_{pose}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            outs[f"{pose}_{tag}"] = scene.render.filepath
    clear_pose()
    gobj.hide_render = True
    report[gid] = list(outs)
    print(f"[pose] {gid}: {len(outs)} renders")

print("[done] pose tests:", ", ".join(report))
