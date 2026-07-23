"""
Render dressed meta avatars (one per outfit) for the wardrobe showcase
lineup. Each outfit is assembled from the EXPORTED GLBs exactly the way the
runtime does it: skinned items re-bound to the template armature by name,
rigid items placed at their attach bone.

Usage:
  blender --background --python lineup_render.py -- <repo_root> <spec.json>
spec.json: [{"tag": "casual", "gender": "male", "items": ["tshirt", ...]}, ...]
Renders -> output/wardrobe_pro/lineup/<tag>.png
"""
import bpy
import json
import math
import os
import sys
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.abspath(argv[0])
SPEC = json.load(open(argv[1]))
ENG = os.path.join(ROOT, "AI-Avatar-Engine")
OUT = os.path.join(ENG, "output", "wardrobe_pro", "lineup")
SHARED = os.path.join(ENG, "assets", "shared")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ENG, "output", "wardrobe_pro", "build_report.json")) as f:
    REPORT = json.load(f)
RIGID = {"cap", "beanie", "glasses_round", "glasses_square"}
PREFIX = {"male": "MetaMale", "female": "MetaFemale"}

for outfit in SPEC:
    gender = outfit["gender"]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(
        ENG, "meta_avatar", "blender", "base", f"meta_{gender}.blend"))
    body = bpy.data.objects[f"{PREFIX[gender]}_Body"]
    arm = bpy.data.objects[f"{PREFIX[gender]}_Armature"]
    for gid in outfit["items"]:
        rep = REPORT.get(gid)
        if not rep:
            print(f"[skip] {gid}")
            continue
        glb = os.path.join(SHARED, rep["glb"])
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=glb)
        new = set(bpy.data.objects) - before
        gobj = max((o for o in new if o.type == 'MESH'),
                   key=lambda o: len(o.data.vertices), default=None)
        # cleanup FIRST: unparent (world preserved), then drop the imported
        # rig/empties — deleting a parent AFTER placing re-evaluates the
        # child transform and flings the item out of frame
        mw = gobj.matrix_world.copy()
        gobj.parent = None
        gobj.matrix_world = mw
        for o in list(new):
            if o is not gobj and o.type in ('ARMATURE', 'EMPTY'):
                bpy.data.objects.remove(o, do_unlink=True)
            elif o is not gobj and o.type == 'MESH' and len(o.data.vertices) <= 100:
                bpy.data.objects.remove(o, do_unlink=True)
        if gid in RIGID:
            b = arm.data.bones["CC_Base_Head"]
            head_w = arm.matrix_world @ b.head_local
            # keep the importer's Y-up axis-conversion rotation — replacing
            # the whole matrix lays hats sideways and hides glasses in the head
            rot = gobj.matrix_world.to_quaternion().to_matrix().to_4x4()
            gobj.matrix_world = Matrix.Translation(head_w) @ rot
        else:
            for m in list(gobj.modifiers):
                if m.type == 'ARMATURE':
                    gobj.modifiers.remove(m)
            mod = gobj.modifiers.new("Armature", 'ARMATURE')
            mod.object = arm

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 540
    scene.render.resolution_y = 1080
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bgc = outfit.get("bg", [0.78, 0.76, 0.80])
    world.node_tree.nodes["Background"].inputs[0].default_value = (*bgc, 1)
    scene.world = world
    for name, loc, rot, e, size in (
            ("Key", (2.2, -2.6, 3.2), (0.9, 0, 0.65), 300, 3.5),
            ("Fill", (-2.8, -1.8, 2.0), (1.1, 0, -0.9), 130, 3.5),
            ("Rim", (0.4, 3.0, 2.9), (-1.0, 0, 0.1), 200, 2.5)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = e
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = rot
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 70
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    target = Vector((0, 0, 0.95))
    cam.location = Vector((0.12, -3.6, 1.15))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, f"{outfit['tag']}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[lineup] {outfit['tag']} -> {scene.render.filepath}")

print("[done] lineup renders")
