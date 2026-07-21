"""
Weld the lip contact band shut across all identity morphs.

Several generated customization keys (cheek_size, lip_thickness, nose_length,
philtrum_length) move the upper and lower lips' CONTACT SURFACES apart, so
strong slider values tear the closed mouth open (teeth/tongue become visible
through the gap). Fix: inside a thin horizontal slab around the lip contact
line, every vertex is blended toward the LOCAL AVERAGE displacement of the
slab — upper and lower lip edges are forced to move together, while the
weld weight fades to zero toward the visible outer lips so sculpting (lip
thickness, mouth width...) survives everywhere else.

All search windows are anchored to the TEETH mesh bounding box (upper/lower
split by material name, same trick as add_mouth_follow_morphs.py), so the
script is template-agnostic — realistic and toon bases place the mouth at
very different heights/proportions. The anchor ratios reproduce the previous
hardcoded windows exactly on the realistic bases. Within the z search window,
the near-coincident vertex pairs at the mouth corners refine the contact
line (the window is required: eyelids have coincident pairs too).
Averaging is a smoothing operator: re-running is safe.

Usage:
  blender --background --python fix_lip_seal.py -- <in.blend> <out.blend> <body_object>
"""
import bpy
import json
import os
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out, BODY_NAME = argv[0], argv[1], argv[2]

DEFS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "morph_definitions.json")

# keys with no semantic business deforming the lips: their displacement is
# zeroed within GUARD_IN cm of the contact line, fading to full by GUARD_OUT
# (their masks leak into the lip roll and evert the red inner-lip skin)
MOUTH_GUARDED = {"cheek_size", "cheekbone_height", "nose_tip_size",
                 "nose_bridge_height", "nose_length", "eye_size",
                 "eye_distance", "forehead_height"}

bpy.ops.wm.open_mainfile(filepath=blend_in)
body = bpy.data.objects[BODY_NAME]
mesh = body.data
n = len(mesh.vertices)

# --------------------------------------------- teeth-anchored mouth frame
# The teeth bbox is the one mouth landmark that exists at a known place on
# every CC3+ template (realistic AND toon). Ratios are calibrated so the
# realistic male base (half-width 3.04, front y -7.60, z extent 4.8) yields
# the previously hardcoded windows.
teeth_o = next(o for o in bpy.data.objects
               if o.type == 'MESH' and "Teeth" in o.name)
_tm = teeth_o.data
_tn = len(_tm.vertices)
_tc = np.zeros(_tn * 3)
(_tm.shape_keys.key_blocks[0].data if _tm.shape_keys
 else _tm.vertices).foreach_get("co", _tc)
_tc = _tc.reshape(_tn, 3)
_up_slots = {i for i, m in enumerate(_tm.materials) if m and "Upper" in m.name}
_is_up = np.zeros(_tn, dtype=bool)
for _p in _tm.polygons:
    if _p.material_index in _up_slots:
        for _vi in _p.vertices:
            _is_up[_vi] = True
T_CONTACT_Z = float(0.5 * (_tc[_is_up][:, 2].min() + _tc[~_is_up][:, 2].max()))
T_HALF_W = float(np.abs(_tc[:, 0]).max())
T_FRONT_Y = float(_tc[:, 1].min())
# vertical mouth scale vs the realistic base — sizes the band/guard widths
SCALE = float(np.clip((_tc[:, 2].max() - _tc[:, 2].min()) / 4.8, 0.8, 1.6))
print(f"[lipseal] teeth anchor: contact_z={T_CONTACT_Z:.2f} "
      f"half_w={T_HALF_W:.2f} front_y={T_FRONT_Y:.2f} scale={SCALE:.2f}")

HALF_BAND = 0.65 * SCALE   # slab half-height (cm) around the contact line
NBR_R = (0.8 * SCALE, 0.9 * SCALE, 0.7 * SCALE)  # local-average window x/y/z
GUARD_IN, GUARD_OUT = 1.3 * SCALE, 2.5 * SCALE

with open(DEFS) as f:
    defs = json.load(f)
CUSTOM_KEYS = sorted({t["shape_key"] for p in defs["params"].values()
                      for t in p["targets"]})

key_blocks = mesh.shape_keys.key_blocks
basis = np.zeros(n * 3)
key_blocks["Basis"].data.foreach_get("co", basis)
basis = basis.reshape(n, 3)
X, Y, Z = basis[:, 0], basis[:, 1], basis[:, 2]

# ---------------------------------------------------- locate the contact line
# near-coincident opposite-facing pairs at the mouth corners give its height;
# searched only near the teeth contact z (eyelids have coincident pairs too)
region = np.where((np.abs(X) < T_HALF_W * 1.25) & (Y < T_FRONT_Y + 4.6 * SCALE)
                  & (np.abs(Z - T_CONTACT_Z) < 3.0 * SCALE))[0]
pts = basis[region]
pair_z = []
for i in range(len(region)):
    d = np.linalg.norm(pts - pts[i], axis=1)
    d[i] = 9e9
    if d.min() < 0.05:
        pair_z.append(pts[i][2])
CENTER_Z = float(np.median(pair_z)) if pair_z else T_CONTACT_Z
print(f"[lipseal] contact line z = {CENTER_Z:.2f} ({len(pair_z)} corner verts)")

# ------------------------------------------------------------- the weld slab
slab = (np.abs(X) < T_HALF_W * 1.05) & (Y < T_FRONT_Y + 1.8 * SCALE) & \
       (np.abs(Z - CENTER_Z) < HALF_BAND)
slab_idx = np.where(slab)[0]
w = np.clip(1.0 - np.abs(Z[slab_idx] - CENTER_Z) / HALF_BAND, 0.0, 1.0) ** 0.75
print(f"[lipseal] slab verts: {len(slab_idx)}")

# neighbor lists (slab is small — brute force is fine)
sp = basis[slab_idx]
nbrs = []
for i in range(len(slab_idx)):
    d = np.abs(sp - sp[i])
    sel = (d[:, 0] < NBR_R[0]) & (d[:, 1] < NBR_R[1]) & (d[:, 2] < NBR_R[2])
    nbrs.append(np.where(sel)[0])

# ------------------------------------------------- mouth-bag interior verts
# The morph generator's masks leak into the mouth cavity: at strong values
# the red bag interior everts through the lip corners. Detect interior verts
# by ray-casting: a vertex whose outward normal immediately re-hits the body
# is inside the cavity. Their deltas get replaced by the local average of
# the surrounding EXTERIOR skin, so the cavity rides along rigidly.
box = ((np.abs(X) < T_HALF_W * 1.18) & (Y > T_FRONT_Y - 0.9 * SCALE) &
       (Y < T_FRONT_Y + 5.6 * SCALE) &
       (Z > CENTER_Z - 2.8 * SCALE) & (Z < CENTER_Z + 2.8 * SCALE))
box_idx = np.where(box)[0]

normals = np.zeros(n * 3)
mesh.vertices.foreach_get("normal", normals)
normals = normals.reshape(n, 3)

polys = [tuple(p.vertices) for p in mesh.polygons]
bvh = BVHTree.FromPolygons([Vector(v) for v in basis], polys)
interior = np.zeros(n, dtype=bool)
for v in box_idx:
    origin = Vector(basis[v] + normals[v] * 0.03)
    hit, _, _, dist = bvh.ray_cast(origin, Vector(normals[v]), 3.0)
    if hit is not None:
        interior[v] = True
int_idx = np.where(interior)[0]
ext_idx = box_idx[~interior[box_idx]]
ext_pts = basis[ext_idx]
print(f"[lipseal] mouth box: {len(box_idx)} verts "
      f"({len(int_idx)} interior, {len(ext_idx)} exterior)")

int_nbrs = []
for v in int_idx:
    d = np.abs(ext_pts - basis[v])
    for r in (1.2, 2.4, 5.0):
        sel = (d[:, 0] < r) & (d[:, 1] < r) & (d[:, 2] < r)
        if sel.any():
            break
    int_nbrs.append(np.where(sel)[0])

# lip-line point cloud (contact-band core) for the mouth-guard distance
lip_pts = basis[slab_idx[w > 0.7]]
guard_zone = np.where((np.abs(X) < T_HALF_W * 1.38) &
                      (Y < T_FRONT_Y + 3.1 * SCALE) &
                      (np.abs(Z - CENTER_Z) < GUARD_OUT + 0.5 * SCALE))[0]
guard_d = np.array([np.linalg.norm(lip_pts - basis[v], axis=1).min()
                    for v in guard_zone])
guard_w = np.clip((guard_d - GUARD_IN) / (GUARD_OUT - GUARD_IN), 0.0, 1.0)

# ---------------------------------------------------------------- weld keys
tmp = np.zeros(n * 3)
for key_name in CUSTOM_KEYS:
    kb = key_blocks.get(key_name)
    if kb is None:
        continue
    kb.data.foreach_get("co", tmp)
    co = tmp.reshape(n, 3)

    # 0. mouth guard: non-mouth morphs must not deform the lip region
    if key_name in MOUTH_GUARDED:
        d = co[guard_zone] - basis[guard_zone]
        co[guard_zone] = basis[guard_zone] + d * guard_w[:, None]

    delta = co - basis

    # 1. seal the lip contact band (exterior lips move together locally)
    ds = delta[slab_idx]
    avg = np.stack([ds[nb].mean(axis=0) for nb in nbrs])
    spread = float(np.linalg.norm(ds - avg, axis=1).max())
    co[slab_idx] = basis[slab_idx] + ds * (1 - w[:, None]) + avg * w[:, None]

    # 2. mouth-bag interior follows the exterior skin around it
    delta2 = co - basis
    ext_d = delta2[ext_idx]
    for k, v in enumerate(int_idx):
        co[v] = basis[v] + ext_d[int_nbrs[k]].mean(axis=0)

    kb.data.foreach_set("co", co.reshape(-1).astype(np.float32))
    if spread > 0.15:
        print(f"  {key_name:20s} lip-band spread {spread:5.2f}cm -> welded")
mesh.update()

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
