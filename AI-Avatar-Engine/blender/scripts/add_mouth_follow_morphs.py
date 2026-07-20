"""
Add follower shape keys to the TEETH and TONGUE meshes for every identity
morph that moves the mouth region of the body — same cross-mesh contract as
add_eye_follow_morphs.py. Without these, identity sliders (thin lips, short
jaw, long philtrum...) move the lips but the teeth stay put and poke through
the skin.

Data-driven, no hardcoded magnitudes: for each customization key we measure
the body's own displacement around the maxilla (skin above the upper lip) and
the mandible (chin skin), then bake that motion into the teeth as a rigid
translation + a small symmetric lateral scale. Upper teeth follow the
maxilla, lower teeth + tongue follow the mandible. Works unmodified on both
templates because anchors derive from the teeth bounding boxes at runtime.

Usage:
  blender --background --python add_mouth_follow_morphs.py -- \
      <in.blend> <out.blend> <body_object>
"""
import bpy
import json
import os
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out, BODY_NAME = argv[0], argv[1], argv[2]

DEFS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "morph_definitions.json")
MIN_FOLLOW = 0.02   # cm at slider 1.0 — skip keys that barely move the anchors

bpy.ops.wm.open_mainfile(filepath=blend_in)
body = bpy.data.objects[BODY_NAME]
mesh = body.data
n = len(mesh.vertices)

with open(DEFS) as f:
    defs = json.load(f)
CUSTOM_KEYS = sorted({t["shape_key"] for p in defs["params"].values()
                      for t in p["targets"]})

key_blocks = mesh.shape_keys.key_blocks
basis = np.zeros(n * 3)
key_blocks["Basis"].data.foreach_get("co", basis)
basis = basis.reshape(n, 3)

# ---------------------------------------------------------------- teeth objs
def obj_basis(obj):
    m = obj.data
    if m.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    co = np.zeros(len(m.vertices) * 3)
    m.shape_keys.key_blocks[0].data.foreach_get("co", co)
    return co.reshape(-1, 3)

teeth_obj = next((o for o in bpy.data.objects
                  if o.type == 'MESH' and "Teeth" in o.name), None)
tongue = next((o for o in bpy.data.objects
               if o.type == 'MESH' and "Tongue" in o.name), None)
if teeth_obj is None:
    sys.exit("no teeth mesh found")

# one mesh, two material slots (Upper/Lower) — split verts by material
tm = teeth_obj.data
upper_slots = {i for i, mslot in enumerate(tm.materials)
               if mslot and "Upper" in mslot.name}
tn = len(tm.vertices)
is_upper = np.zeros(tn, dtype=bool)
for poly in tm.polygons:
    if poly.material_index in upper_slots:
        for vi in poly.vertices:
            is_upper[vi] = True
print(f"[mouth] teeth={teeth_obj.name} (upper {is_upper.sum()} / "
      f"lower {(~is_upper).sum()} verts) "
      f"tongue={tongue.name if tongue else 'NONE'}")

# ------------------------------------------------------------- anchor regions
# EXTERIOR skin over the bone the teeth sit in: philtrum band for the
# maxilla, chin for the mandible. Two guards keep the mouth-bag interior out
# of the anchors (its verts share the z-band and move with unrelated morphs):
# only verts near the teeth's frontmost plane, and only outward-facing ones.
X, Y, Z = basis[:, 0], basis[:, 1], basis[:, 2]
v_normals = np.zeros(n * 3)
mesh.vertices.foreach_get("normal", v_normals)
NY = v_normals.reshape(n, 3)[:, 1]

def anchor_mask(teeth_co, above):
    lo, hi = teeth_co.min(axis=0), teeth_co.max(axis=0)
    front_y = float(teeth_co[:, 1].min())   # most forward point of the teeth
    if above:   # band of skin just above the upper teeth (below the nose)
        zsel = (Z > hi[2]) & (Z < hi[2] + 1.6)
    else:       # chin skin just below the lower teeth
        zsel = (Z < lo[2]) & (Z > lo[2] - 1.8)
    return (zsel & (np.abs(X) < 3.2) & (Y < front_y + 1.8) & (NY < -0.2))

teeth_basis = obj_basis(teeth_obj)
up_co, lo_co = teeth_basis[is_upper], teeth_basis[~is_upper]
masks = {"upper": anchor_mask(up_co, True), "lower": anchor_mask(lo_co, False)}
print(f"[mouth] anchor verts: upper={masks['upper'].sum()} "
      f"lower={masks['lower'].sum()}")

def set_key(obj, name, new_co):
    kb = obj.data.shape_keys.key_blocks.get(name) or \
         obj.shape_key_add(name=name, from_mix=False)
    kb.slider_min, kb.slider_max, kb.value = -1.0, 1.0, 0.0
    kb.data.foreach_set("co", new_co.reshape(-1).astype(np.float32))
    obj.data.update()

# ---------------------------------------------------------------- build keys
tongue_basis = obj_basis(tongue) if tongue is not None else None

# idempotency: drop any follower keys from previous runs first
for obj in filter(None, (teeth_obj, tongue)):
    for key_name in CUSTOM_KEYS:
        kb_old = obj.data.shape_keys.key_blocks.get(key_name)
        if kb_old is not None:
            obj.shape_key_remove(kb_old)

def region_follow(delta, region):
    """(translation, lateral-scale) of the anchor skin for one morph key."""
    m = masks[region]
    d = delta[m]
    trans = d.mean(axis=0)
    # symmetric lateral squeeze (jaw/face width) cancels in the mean —
    # recover it as a scale factor about the midline
    lat = float((d[:, 0] * np.sign(X[m])).mean() /
                max(np.abs(X[m]).mean(), 1e-6))
    return trans, lat

tmp = np.zeros(n * 3)
added = 0
for key_name in CUSTOM_KEYS:
    kb = key_blocks.get(key_name)
    if kb is None:
        continue
    kb.data.foreach_get("co", tmp)
    delta = tmp.reshape(n, 3) - basis

    follow = {r: region_follow(delta, r) for r in ("upper", "lower")}
    significant = any(np.linalg.norm(t) >= MIN_FOLLOW or abs(l) >= 0.01
                      for t, l in follow.values())
    if not significant:
        continue

    # teeth: one key, upper verts follow the maxilla, lower the mandible
    new_co = teeth_basis.copy()
    for region, sel in (("upper", is_upper), ("lower", ~is_upper)):
        trans, lat = follow[region]
        new_co[sel] += trans
        new_co[sel, 0] += teeth_basis[sel, 0] * lat
    set_key(teeth_obj, key_name, new_co)
    added += 1
    tu, lu = follow["upper"], follow["lower"]
    print(f"  {key_name:20s} up=({tu[0][0]:+.3f},{tu[0][1]:+.3f},{tu[0][2]:+.3f})"
          f" lat={tu[1]:+.3f}  lo=({lu[0][0]:+.3f},{lu[0][1]:+.3f},{lu[0][2]:+.3f})"
          f" lat={lu[1]:+.3f}")

    if tongue is not None:
        trans, lat = follow["lower"]
        t_co = tongue_basis + trans
        t_co[:, 0] += tongue_basis[:, 0] * lat
        set_key(tongue, key_name, t_co)
        added += 1

print(f"[mouth] {added} follower keys added")
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
