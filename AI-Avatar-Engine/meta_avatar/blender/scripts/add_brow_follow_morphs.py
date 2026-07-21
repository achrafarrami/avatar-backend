"""
Add follower shape keys to the Toon_Eyebrows mesh for every identity morph
that moves the brow-region skin of the body — same cross-mesh contract as
add_eye_follow_morphs.py / add_mouth_follow_morphs.py. The toon bases (unlike
the realistic ones, whose brows are texture-only) ship eyebrows as a separate
floating mesh: without followers, eyebrow_height / forehead_height /
face_width move the skin and leave the eyebrows hovering in place.

Data-driven like the mouth script: each eyebrow vertex samples the motion of
its K nearest body-skin vertices (inverse-distance weighted), so any body
morph — present or future — transfers without per-morph tuning. The eyebrow
mesh hovers ~mm above the brow skin, so nearest-neighbour sampling always
lands on the correct skin patch.

Usage:
  blender --background --python add_brow_follow_morphs.py -- \
      <in.blend> <out.blend> <body_object> [brow_object]
"""
import bpy
import json
import os
import sys
import numpy as np
from mathutils import kdtree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out, BODY_NAME = argv[0], argv[1], argv[2]
BROW_NAME = argv[3] if len(argv) > 3 else "Toon_Eyebrows"

K = 6           # body verts sampled per eyebrow vert
MIN_FOLLOW = 0.02   # skip keys whose sampled motion never exceeds this (cm)

# canonical morph list lives with the style-agnostic tooling
DEFS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "blender", "scripts", "morph_definitions.json"))

bpy.ops.wm.open_mainfile(filepath=blend_in)
body = bpy.data.objects[BODY_NAME]
brow = bpy.data.objects.get(BROW_NAME)
if brow is None:
    sys.exit(f"no eyebrow mesh '{BROW_NAME}' found")

with open(DEFS) as f:
    defs = json.load(f)
CUSTOM_KEYS = sorted({t["shape_key"] for p in defs["params"].values()
                      for t in p["targets"]})

mesh = body.data
n = len(mesh.vertices)
key_blocks = mesh.shape_keys.key_blocks
basis = np.zeros(n * 3)
key_blocks["Basis"].data.foreach_get("co", basis)
basis = basis.reshape(n, 3)

bm = brow.data
if bm.shape_keys is None:
    brow.shape_key_add(name="Basis", from_mix=False)
bn = len(bm.vertices)
brow_basis = np.zeros(bn * 3)
bm.shape_keys.key_blocks[0].data.foreach_get("co", brow_basis)
brow_basis = brow_basis.reshape(bn, 3)

# ------------------------------------------------- knn brow -> body (once)
kd = kdtree.KDTree(n)
for i, co in enumerate(basis):
    kd.insert(co, i)
kd.balance()

nn_idx = np.zeros((bn, K), dtype=np.int64)
nn_w = np.zeros((bn, K))
for i, co in enumerate(brow_basis):
    hits = kd.find_n(co, K)
    for j, (_, idx, dist) in enumerate(hits):
        nn_idx[i, j] = idx
        nn_w[i, j] = 1.0 / (dist + 1e-4)
nn_w /= nn_w.sum(axis=1, keepdims=True)

# idempotency: drop follower keys from previous runs
for key_name in CUSTOM_KEYS:
    kb_old = bm.shape_keys.key_blocks.get(key_name)
    if kb_old is not None:
        brow.shape_key_remove(kb_old)

tmp = np.zeros(n * 3)
added = 0
for key_name in CUSTOM_KEYS:
    kb = key_blocks.get(key_name)
    if kb is None:
        continue
    kb.data.foreach_get("co", tmp)
    delta = tmp.reshape(n, 3) - basis

    brow_delta = (delta[nn_idx] * nn_w[:, :, None]).sum(axis=1)
    peak = float(np.linalg.norm(brow_delta, axis=1).max())
    if peak < MIN_FOLLOW:
        continue

    new_kb = brow.shape_key_add(name=key_name, from_mix=False)
    new_kb.slider_min, new_kb.slider_max, new_kb.value = -1.0, 1.0, 0.0
    new_kb.data.foreach_set(
        "co", (brow_basis + brow_delta).reshape(-1).astype(np.float32))
    bm.update()
    added += 1
    print(f"  {key_name:20s} peak={peak:.3f}")

print(f"[brow] {added} follower keys added on {BROW_NAME}")
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
