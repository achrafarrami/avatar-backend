"""
Measure head geometry (world-space width/depth + crown height, both in
absolute world coords and relative to the CC_Base_Head bone's own world
position) on the realistic and Meta templates, for both genders. This feeds
the T3 wardrobe-fit math: the ratio of Meta head width to realistic head
width tells us how much bigger a realistic-authored bone-attached item
(hair/glasses/hats/accessories) needs to be scaled to sit correctly on the
bigger Meta head; the crown-Z/Y delta (relative to the bone origin) tells us
the extra positional nudge needed on top of the runtime's existing
bone-anchored placement (see frontend/threejs-viewer/src/viewer.js
attachAsset()).

Same head-selection technique as blender/scripts/import_hair_pack.py's
autofit: vertices carrying the CC_Base_Head vertex group with weight > 0.5,
restricted to above the head bone's own Z (excludes the neck). Measured off
the mesh's CURRENT basis (shape-key "Basis" if present) — for the Meta
bodies this is the post-Phase-2 stylized-neutral bake, per the correction
from main: the Phase-1 inspection JSONs predate that bake and are not a
reliable source for head size.

Usage:
  blender --background --python measure_heads.py -- <out_json>
"""
import bpy
import json
import os
import sys
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_JSON = os.path.abspath(argv[0])

AI_ENGINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

TEMPLATES = [
    ("realistic_male", os.path.join(AI_ENGINE, "blender", "templates", "male_base.blend"),
     "Male_Body", "Male_Armature"),
    ("realistic_female", os.path.join(AI_ENGINE, "blender", "templates", "female_base.blend"),
     "Female_Body", "Female_Armature"),
    ("meta_male", os.path.join(AI_ENGINE, "meta_avatar", "blender", "base", "meta_male.blend"),
     "MetaMale_Body", "MetaMale_Armature"),
    ("meta_female", os.path.join(AI_ENGINE, "meta_avatar", "blender", "base", "meta_female.blend"),
     "MetaFemale_Body", "MetaFemale_Armature"),
]


REGIONS = ["CC_Base_Head", "CC_Base_L_Hand", "CC_Base_JawRoot"]


def measure_region(body, arm, co, vg_index, region):
    if region not in vg_index:
        return None
    bones = arm.data.bones
    if region not in bones:
        return None
    idx = vg_index[region]
    n = co.shape[0]
    w = np.zeros(n)
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == idx:
                w[v.index] = g.weight
    mw = np.array(body.matrix_world)
    world = co @ mw[:3, :3].T + mw[:3, 3]
    origin = arm.matrix_world @ bones[region].head_local
    sel = w > 0.5
    if region == "CC_Base_Head":
        # exclude the neck: keep only verts above the bone's own Z
        sel = sel & (world[:, 2] > float(origin.z) + 0.02)
    pts = world[sel]
    if len(pts) == 0:
        return None
    top = float(pts[:, 2].max())
    bottom = float(pts[:, 2].min())
    crown = pts[pts[:, 2] > top - 0.01]
    width = float(pts[:, 0].max() - pts[:, 0].min())
    depth = float(pts[:, 1].max() - pts[:, 1].min())
    return {
        "bone_origin_world": [float(origin.x), float(origin.y), float(origin.z)],
        "width": width,
        "depth": depth,
        "height_above_bone": top - float(origin.z),
        "top_z_world": top,
        "top_z_rel": top - float(origin.z),
        "top_y_world": float(crown[:, 1].mean()),
        "top_y_rel": float(crown[:, 1].mean()) - float(origin.y),
        "bottom_z_rel": bottom - float(origin.z),
        "vert_count": int(sel.sum()),
    }


def measure(template, body_name, arm_name):
    bpy.ops.wm.open_mainfile(filepath=template)
    body = bpy.data.objects[body_name]
    arm = bpy.data.objects[arm_name]
    mesh = body.data
    n = len(mesh.vertices)
    co = np.zeros(n * 3)
    if mesh.shape_keys and "Basis" in mesh.shape_keys.key_blocks:
        mesh.shape_keys.key_blocks["Basis"].data.foreach_get("co", co)
    else:
        mesh.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    vg_index = {g.name: g.index for g in body.vertex_groups}

    out = {}
    for region in REGIONS:
        m = measure_region(body, arm, co, vg_index, region)
        if m is not None:
            out[region] = m
    return out


results = {}
for name, path, body_name, arm_name in TEMPLATES:
    if not os.path.isfile(path):
        print(f"[measure] SKIP {name}: {path} not found")
        continue
    results[name] = measure(path, body_name, arm_name)
    for region, r in results[name].items():
        print(f"[measure] {name:16s} {region:16s} width={r['width']:.4f}m depth={r['depth']:.4f}m "
              f"top_z_rel={r['top_z_rel']:.4f}m origin={r['bone_origin_world']}")

ratios = {}
for region in REGIONS:
    for g in ("male", "female"):
        mkey, rkey = f"meta_{g}", f"realistic_{g}"
        if mkey in results and rkey in results and region in results[mkey] and region in results[rkey]:
            ratios.setdefault(region, {})[g] = results[mkey][region]["width"] / results[rkey][region]["width"]
results["ratios"] = ratios

for region, rr in ratios.items():
    for g, r in rr.items():
        print(f"[measure] {region} width ratio meta/{g} = {r:.4f}")

with open(OUT_JSON, "w") as f:
    json.dump(results, f, indent=2)
print(f"[done] -> {OUT_JSON}")
