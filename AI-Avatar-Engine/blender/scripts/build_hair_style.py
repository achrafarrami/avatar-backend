"""
Strand-clump hair style generator for the Avatar Asset System.

Unlike build_demo_assets.py's hair (inflated scalp shells that read as
helmets), this grows REAL hair geometry: tapered, wavy clump tubes rooted on
the scalp, combed along a per-style flow field (swept back, fringe up, short
sides...), collision-pushed so they hug the skull, over a thin scalp
under-shell that hides skin between clumps. The result reads like sculpted
real-time game hair.

Output (same contract as build_demo_assets.py):
  assets/shared/hair/<id>/{<id>.glb, item.json, thumbnail.png}
  + merged into assets/shared/catalog.json
  + whole item copied to the sandbox wardrobe dir + sandbox catalog updated
  + verification renders (front / three-quarter, hair ON the head) into
    the directory given as 5th arg.

Usage:
  blender --background --python build_hair_style.py -- \
      <template.blend> <assets_shared_dir> <sandbox_wardrobe_dir> \
      <style_id> <preview_out_dir>
"""
import bpy
import bmesh
import json
import math
import os
import random
import shutil
import sys
import numpy as np
from mathutils import Vector, kdtree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, SHARED_DIR, SANDBOX_DIR, STYLE_ID, PREVIEW_DIR = \
    [os.path.abspath(a) for a in argv[:3]] + [argv[3], os.path.abspath(argv[4])]

BODY_NAME, ARM_NAME = "Male_Body", "Male_Armature"

# ---------------------------------------------------------------- styles
# All vectors/lengths in template units (cm). Character faces -Y, up is +Z.
# flow = comb direction per scalp region; lengths are strand lengths.
STYLES = {
    "hair_swept": {
        "label": "Swept Back",
        "seed": 7,
        "clump_spacing": 0.72,       # min distance between clump roots (cm)
        "clump_radius": (0.36, 0.55),
        "segments": 11,
        "wave_amp": (0.08, 0.22),    # lateral wave amplitude (cm)
        "wave_freq": (0.8, 1.6),     # wave cycles along the strand
        "lift": (0.03, 0.20),        # clearance above scalp (cm), varied per
                                     # clump so locks layer over each other
        "regions": {
            #          flow (x=right, y=back, z=up)   length cm   gravity
            "front": {"flow": (0.30, 0.80, 0.45), "len": (6.0, 8.0), "grav": 0.30},
            "top":   {"flow": (0.35, 1.0, -0.15), "len": (6.0, 8.5), "grav": 0.35},
            "side":  {"flow": (0.0, 0.8, -0.65), "len": (2.6, 3.6), "grav": 0.12,
                      "r_scale": 0.6},
            "back":  {"flow": (0.0, 0.55, -1.0), "len": (3.2, 4.2), "grav": 0.12,
                      "r_scale": 0.8},
        },
    },
}

style = STYLES[STYLE_ID]
rng = random.Random(style["seed"])

# ---------------------------------------------------------------- template
bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
body = bpy.data.objects[BODY_NAME]
arm = bpy.data.objects[ARM_NAME]
mesh = body.data
n = len(mesh.vertices)

co = np.zeros(n * 3)
key_blocks = mesh.shape_keys.key_blocks
key_blocks["Basis"].data.foreach_get("co", co)
co = co.reshape(n, 3)
X, Y, Z = co[:, 0], co[:, 1], co[:, 2]

normals = np.zeros(n * 3)
mesh.vertices.foreach_get("normal", normals)
normals = normals.reshape(n, 3)

bones = arm.data.bones
vg_index = {g.name: g.index for g in body.vertex_groups}

def vg_weights(names):
    idx = {vg_index[nm] for nm in names if nm in vg_index}
    w = np.zeros(n)
    for v in mesh.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w

def expr_mask(prefixes):
    mag = np.zeros(n)
    tmp = np.zeros(n * 3)
    for kb in key_blocks:
        if any(kb.name.startswith(p) for p in prefixes) and "Eyelash" not in kb.name:
            kb.data.foreach_get("co", tmp)
            d = np.linalg.norm(tmp.reshape(n, 3) - co, axis=1)
            mag = np.maximum(mag, d)
    nz = mag[mag > 1e-6]
    if len(nz):
        mag = np.clip(mag / np.percentile(nz, 99), 0, 1)
    return mag

brow_mag = expr_mask(["Brow_"])
brow_sel = brow_mag > 0.3
BROW_Z = float((Z[brow_sel] * brow_mag[brow_sel]).sum() / brow_mag[brow_sel].sum())

head_w = vg_weights(["CC_Base_Head"])
ear_region = (head_w > 0.3) & (np.abs(X) > 6.2) & (Z < 168.5) & (Z > 155)
scalp = (head_w > 0.4) & (Z > 169.5) & ~ear_region & \
        ((Y > -5.5) | (Z > BROW_Z + 4.0))
scalp_idx = np.where(scalp)[0]
CROWN_Z = float(Z[scalp].max())
SCALP_CY = float(Y[scalp].mean())

# head collision surface: every head-region vertex + its normal
head_sel = np.where((head_w > 0.2) & (Z > 158))[0]
kd = kdtree.KDTree(len(head_sel))
for i, vi in enumerate(head_sel):
    kd.insert(Vector(co[vi]), i)
kd.balance()
head_normals = normals[head_sel]
head_cos = co[head_sel]

def push_out(p, clearance):
    """Keep point `clearance` outside the head surface — and ATTRACT it back
    when it drifts too far, so locks wrap around the skull's curvature
    instead of flying off tangentially at the back/behind the ears."""
    for _ in range(2):
        _, i, _ = kd.find(Vector(p))
        nrm = head_normals[i]
        signed = float(np.dot(p - head_cos[i], nrm))
        if signed < clearance:
            p = p + nrm * (clearance - signed)
        elif signed > clearance + 0.35:
            p = p - nrm * ((signed - clearance - 0.35) * 0.75)
    return p

# ---------------------------------------------------------------- roots
# Poisson-ish sampling of clump roots over the scalp
EAR_Y = float(Y[ear_region].mean())

order = list(range(len(scalp_idx)))
rng.shuffle(order)
roots = []
min_d2 = style["clump_spacing"] ** 2
for oi in order:
    vi = scalp_idx[oi]
    p = co[vi]
    # hairline notch directly above the ears: strands rooted there funnel
    # over the ear bulge and twist into knots
    if abs(X[vi]) > 5.5 and Z[vi] < 171.5 and abs(Y[vi] - EAR_Y) < 2.0:
        continue
    if all(((p - co[r]) ** 2).sum() >= min_d2 for r in roots):
        roots.append(vi)
print(f"[hair] {len(roots)} clump roots (spacing {style['clump_spacing']}cm)")

def classify(vi):
    # position-first: forehead-hairline normals point forward, not up, so
    # normal-only classification would comb them DOWN the face
    nrm = normals[vi]
    if abs(nrm[0]) > 0.6 and nrm[2] < 0.45:
        return "side"
    if Y[vi] < SCALP_CY - 0.5 and nrm[2] < 0.55:
        return "front"          # forehead hairline -> sweep up & back
    if nrm[2] > 0.5:
        return "front" if Y[vi] < SCALP_CY - 1.5 else "top"
    return "back"

def norm(v):
    l = np.linalg.norm(v)
    return v / l if l > 1e-9 else v

# ---------------------------------------------------------------- strands
segs = style["segments"]
splines_data = []   # (points list, radii list)

for vi in roots:
    region = classify(vi)
    cfg = style["regions"][region]
    length = rng.uniform(*cfg["len"])
    if region in ("side", "back"):
        # taper toward the hairline: low roots (near ears/nape) grow shorter
        length *= min(1.0, max(0.45, (Z[vi] - 167.0) / (CROWN_Z - 167.0) + 0.35))
    r0 = rng.uniform(*style["clump_radius"]) * cfg.get("r_scale", 1.0)
    lift = rng.uniform(*style["lift"])
    amp = rng.uniform(*style["wave_amp"])
    freq = rng.uniform(*style["wave_freq"])
    phase = rng.uniform(0, math.tau)
    grav = cfg["grav"]

    flow = np.array(cfg["flow"], dtype=float)
    # small per-clump variation, kept coherent so locks comb together
    flow = norm(flow + np.array([rng.gauss(0, 0.06), rng.gauss(0, 0.05),
                                 rng.gauss(0, 0.06)]))
    nrm = normals[vi].astype(float)
    # short sides/back: comb direction dominates immediately, or roots around
    # the ears radiate along their own normals into starburst clumps
    w_n = 0.15 if region in ("side", "back") else 0.3
    d0 = norm(flow * (1.0 - w_n) + nrm * w_n)

    # jitter roots off the body-topology vertex grid so clump rows don't align
    t1 = norm(np.cross(nrm, np.array([0.0, 0.0, 1.0])))
    if np.linalg.norm(t1) < 1e-6:
        t1 = np.array([1.0, 0.0, 0.0])
    t2 = norm(np.cross(nrm, t1))
    root = co[vi] + t1 * rng.uniform(-0.35, 0.35) + t2 * rng.uniform(-0.35, 0.35)

    # comb the strand flat along the skull: at each step the direction is
    # projected onto the local scalp tangent plane (strong near the root,
    # relaxing toward the tip so ends can lift/fall naturally)
    p = root - nrm * 0.25            # embed root slightly under the shell
    step = length / segs
    pts = [p.copy()]
    for s in range(1, segs + 1):
        t = s / segs
        blend = min(1.0, t * 3.5)
        d = norm(d0 * (1 - blend) + flow * blend)
        d = d + np.array([0.0, 0.0, -grav * t])
        _, i, _ = kd.find(Vector(p))
        n_loc = np.asarray(head_normals[i], dtype=float)
        k = 0.9 if t < 0.5 else max(0.55, 0.9 - (t - 0.5) * 0.8)
        d = norm(d - n_loc * float(np.dot(d, n_loc)) * k)
        p = p + d * step
        p = push_out(p, lift * (1.0 - 0.4 * t) + 0.05)
        pts.append(p.copy())

    # lateral wave for texture (zero at root, grows along strand)
    axis = norm(pts[-1] - pts[0])
    side_v = norm(np.cross(axis, np.array([0.0, 0.0, 1.0])))
    if np.linalg.norm(side_v) < 1e-6:
        side_v = np.array([1.0, 0.0, 0.0])
    for s in range(1, segs + 1):
        t = s / segs
        pts[s] = pts[s] + side_v * (amp * math.sin(freq * math.tau * t + phase) * t)

    # full-bodied clump: fat through the middle, tapering only near the tip
    radii = []
    for s in range(segs + 1):
        t = s / segs
        if t < 0.15:
            r = r0 * (0.7 + 0.3 * (t / 0.15))
        elif t < 0.55:
            r = r0
        else:
            r = r0 * (1.0 - 0.88 * ((t - 0.55) / 0.45) ** 1.3)
        radii.append(max(r, 0.05))
    splines_data.append((pts, radii))

# ---------------------------------------------------------------- curve->mesh
curve = bpy.data.curves.new(f"{STYLE_ID}_strands", 'CURVE')
curve.dimensions = '3D'
curve.bevel_depth = 1.0          # per-point radius carries the real size (cm)
curve.bevel_resolution = 1       # 8-sided tubes
curve.use_fill_caps = True
for pts, radii in splines_data:
    sp = curve.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, (p, r) in enumerate(zip(pts, radii)):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
        sp.points[i].radius = r

strand_obj = bpy.data.objects.new(f"{STYLE_ID}_strands", curve)
strand_obj.matrix_world = body.matrix_world.copy()
bpy.context.scene.collection.objects.link(strand_obj)
with bpy.context.temp_override(active_object=strand_obj,
                               selected_objects=[strand_obj],
                               selected_editable_objects=[strand_obj]):
    bpy.ops.object.convert(target='MESH')
strand_obj = bpy.data.objects[f"{STYLE_ID}_strands"]
strand_obj.data.polygons.foreach_set(
    "use_smooth", [True] * len(strand_obj.data.polygons))
vg = strand_obj.vertex_groups.new(name="CC_Base_Head")
vg.add(range(len(strand_obj.data.vertices)), 1.0, 'REPLACE')

# ---------------------------------------------------------------- under-shell
shell = body.copy()
shell.data = body.data.copy()
shell.name = STYLE_ID
bpy.context.scene.collection.objects.link(shell)
shell.shape_key_clear()
me = shell.data
new_co = co + normals * 0.06
me.vertices.foreach_set("co", new_co.reshape(-1).astype(np.float32))
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
doomed = [v for v in bm.verts if not scalp[v.index]]
bmesh.ops.delete(bm, geom=doomed, context='VERTS')
bm.to_mesh(me)
bm.free()
sol = shell.modifiers.new("Sol", 'SOLIDIFY')
sol.thickness = 0.15
sol.offset = 1.0
with bpy.context.temp_override(object=shell, active_object=shell,
                               selected_objects=[shell]):
    bpy.ops.object.modifier_apply(modifier="Sol")

# ---------------------------------------------------------------- material+join
mat = bpy.data.materials.new(f"{STYLE_ID}_mat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
c = tuple(int("3b2a1e"[i:i+2], 16) / 255 for i in (0, 2, 4))
bsdf.inputs["Base Color"].default_value = (*c, 1)
bsdf.inputs["Roughness"].default_value = 0.55

for o in (shell, strand_obj):
    o.data.materials.clear()
    o.data.materials.append(mat)

with bpy.context.temp_override(active_object=shell,
                               selected_editable_objects=[shell, strand_obj],
                               selected_objects=[shell, strand_obj]):
    bpy.ops.object.join()
hair = shell
hair.name = STYLE_ID
print(f"[hair] joined mesh: {len(hair.data.vertices)} verts, "
      f"{len(hair.data.polygons)} faces")

# ---------------------------------------------------------------- export GLB
meta = {
    "id": STYLE_ID, "label": style["label"], "slot": "hair",
    "category_dir": "hair", "attach_type": "skinned", "attach_to": None,
    "colorable_materials": [f"{STYLE_ID}_mat"],
    "file": f"hair/{STYLE_ID}/{STYLE_ID}.glb",
    "thumb": f"hair/{STYLE_ID}/thumbnail.png",
}
out_dir = os.path.join(SHARED_DIR, "hair", STYLE_ID)
os.makedirs(out_dir, exist_ok=True)
glb_path = os.path.join(out_dir, STYLE_ID + ".glb")

bpy.ops.object.select_all(action='DESELECT')
hair.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
    use_selection=True, export_skins=True, export_morph=False,
    export_animations=False, export_yup=True)
print(f"[hair] GLB {os.path.getsize(glb_path)/1e6:.1f} MB -> {glb_path}")

# ---------------------------------------------------------------- renders
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
world = bpy.data.worlds.new("ThumbWorld")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.17, 0.20, 1)
scene.world = world

cam_data = bpy.data.cameras.new("ThumbCam")
cam = bpy.data.objects.new("ThumbCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun = bpy.data.lights.new("ThumbSun", 'SUN')
sun.energy = 3.5
sun_obj = bpy.data.objects.new("ThumbSun", sun)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(55), 0, math.radians(20))
fill = bpy.data.lights.new("Fill", 'SUN')
fill.energy = 1.2
fill_obj = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fill_obj)
fill_obj.rotation_euler = (math.radians(70), 0, math.radians(200))

for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = True

# thumbnail: hair alone, matching the demo-asset thumbnail style
hair.hide_render = False
scene.render.resolution_x = scene.render.resolution_y = 256
pts = [hair.matrix_world @ v.co for v in hair.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center, size = (lo + hi) / 2, max((hi - lo).length, 0.05)
cam.location = center + Vector((0.45, -1.0, 0.35)).normalized() * size * 1.6
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(out_dir, "thumbnail.png")
bpy.ops.render.render(write_still=True)

# verification renders: hair ON the head
body.hide_render = False
os.makedirs(PREVIEW_DIR, exist_ok=True)
head_world = arm.matrix_world @ bones["CC_Base_Head"].head_local
target = Vector((0, head_world.y, head_world.z + 0.09))
scene.render.resolution_x = scene.render.resolution_y = 640
for tag, offset in (("front", Vector((0, -0.62, 0.02))),
                    ("threequarter", Vector((0.42, -0.46, 0.06))),
                    ("side", Vector((0.62, 0.0, 0.02))),
                    ("back", Vector((0, 0.62, 0.02)))):
    cam.location = target + offset
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"{STYLE_ID}_{tag}.png")
    bpy.ops.render.render(write_still=True)
print(f"[hair] previews -> {PREVIEW_DIR}")

# ---------------------------------------------------------------- catalog+item
with open(os.path.join(SHARED_DIR, "catalog.json")) as f:
    catalog = json.load(f)
items = [it for it in catalog["items"] if it["id"] != STYLE_ID]
last_hair = max((i for i, it in enumerate(items)
                 if it["category_dir"] == "hair"), default=-1)
items.insert(last_hair + 1, meta)
catalog["items"] = items
with open(os.path.join(SHARED_DIR, "catalog.json"), "w") as f:
    json.dump(catalog, f, indent=2)
with open(os.path.join(out_dir, "item.json"), "w") as f:
    json.dump(meta, f, indent=2)

# sandbox copy (item dir + catalog)
sb_item = os.path.join(SANDBOX_DIR, "hair", STYLE_ID)
if os.path.isdir(sb_item):
    shutil.rmtree(sb_item)
shutil.copytree(out_dir, sb_item)
shutil.copy2(os.path.join(SHARED_DIR, "catalog.json"),
             os.path.join(SANDBOX_DIR, "catalog.json"))
print(f"[hair] catalog updated, sandbox copy -> {sb_item}")
