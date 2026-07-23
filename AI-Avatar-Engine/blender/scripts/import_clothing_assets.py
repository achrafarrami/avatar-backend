"""
Integrate external, unrigged clothing meshes into the Avatar Asset System as
"skinned" wardrobe items (same contract as the demo tops: mesh skinned to the
CC skeleton, runtime re-binds to the avatar's bones by name).

Sources handled (one item id per run, config in ITEMS below):
  - school_uniform    assets/"Female School Uniform.blend" — one-piece dress,
                      cm data at object scale 1.0, plain gray, no rig.
  - tshirt_oversized  assets/fbx.fbx — CLO/Marvelous "male oversized tshirt",
                      ASCII FBX (needs Blender 5.x ufbx importer), ~1M verts
                      (decimated here), textures live in
                      uploads_files_4849582_fbx.rar (extract fbx_diffuse_1001
                      .png + fbx_normal_1001.png and pass their dir).

Per item this script:
  - loads the garment into the gendered template scene, normalizes it to the
    template convention (mesh data in cm, Z-up, object scale 0.01)
  - auto-fits: collar-top -> neck-base height, x/y centering against the
    template torso, optional extra scale; bends each sleeve about the
    shoulder to match the template's rest-pose arm angle (measured from the
    garment's own sleeve centerline, so a T-pose source and an A-pose source
    both converge to the template pose)
  - pushes garment verts out of the body (BVH nearest-surface) to kill
    interpenetration after the fit
  - transfers skinning weights from the body mesh (nearest-poly interp,
    capped at 4 influences for glTF), parents to the armature
  - exports the GLB, renders thumbnail + on-body verification views, writes
    item.json, merges catalog.json, copies to the sandbox wardrobe

Usage:
  blender --background --python import_clothing_assets.py -- \
      <item_id> <garment_file> <template.blend> <assets_shared_dir> \
      <sandbox_wardrobe_dir> <preview_dir> [texture_dir] [work_dir]

work_dir caches the prepped (imported+decimated) heavy FBX as a .blend so
fit iterations don't pay the ASCII-FBX import cost every run.
"""
import bpy
import bmesh
import json
import math
import os
import shutil
import sys
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ITEM_ID = argv[0]
GARMENT, TEMPLATE, SHARED_DIR, SANDBOX_DIR, PREVIEW_DIR = \
    [os.path.abspath(a) for a in argv[1:6]]
TEX_DIR = os.path.abspath(argv[6]) if len(argv) > 6 else None
WORK_DIR = os.path.abspath(argv[7]) if len(argv) > 7 else PREVIEW_DIR

ITEMS = {
    "school_uniform": {
        "label": "School Uniform", "gender": "female",
        "body": "Female_Body", "armature": "Female_Armature",
        "source_object": "Female_School_Uniform",
        "source": "uploads_files_6237525_Female+School+Uniform+BLEND.rar",
        "color": "#2e3a55", "colorable": True,
        "collar_rise": 5.0,          # standing collar tops out above neck base (cm)
        "decimate_faces": None,
        "tweaks": {},                # {"s": extra scale, "dz": cm, "dy": cm}
    },
    "tshirt_oversized": {
        "label": "Oversized Tee", "gender": "male",
        "body": "Male_Body", "armature": "Male_Armature",
        "source_object": "fbx",
        "source": "uploads_files_4849582_fbx.rar (CLO male oversized tshirt)",
        "color": None, "colorable": False,
        "textures": {"diffuse": "fbx_diffuse_1001.png",
                     "normal": "fbx_normal_1001.png"},
        "collar_rise": 1.5,          # crew neck sits at the neck base
        "decimate_faces": 45000,
        # drop-shoulder short sleeves end where the oversized torso is just
        # as wide — the sleeve-centerline fit can't tell them apart, and the
        # CLO drape is already near-A-pose, so skip the bend entirely
        "sleeve_fit": "none",
        "clearance": 0.45,           # CC traps ride higher than the CLO bust
        "tweaks": {},
    },
}
CFG = ITEMS[ITEM_ID]

# ----------------------------------------------------------- 1. template
bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
body = bpy.data.objects[CFG["body"]]
arm = bpy.data.objects[CFG["armature"]]
bones = arm.data.bones
mesh = body.data
nb = len(mesh.vertices)
bco = np.zeros(nb * 3)
mesh.shape_keys.key_blocks["Basis"].data.foreach_get("co", bco)
bco = bco.reshape(nb, 3)                       # template data space = cm, Z-up

NECK_Z = bones["CC_Base_NeckTwist01"].head_local.z
ua, fa = bones["CC_Base_L_Upperarm"].head_local, bones["CC_Base_L_Forearm"].head_local
SHOULDER_X, SHOULDER_Z = abs(ua.x), ua.z
ARM_XZ = math.atan2(fa.z - ua.z, fa.x - ua.x)   # rest-pose arm slope (L side, +x)
ARM_XY = math.atan2(fa.y - ua.y, fa.x - ua.x)
band = (bco[:, 2] > NECK_Z - 20) & (bco[:, 2] < NECK_Z - 8) & (np.abs(bco[:, 0]) < 12)
BODY_Y_MID = float((bco[band, 1].max() + bco[band, 1].min()) / 2)
print(f"[template] neck_z={NECK_Z:.1f} shoulder=({SHOULDER_X:.1f},{SHOULDER_Z:.1f}) "
      f"arm_xz={math.degrees(ARM_XZ):.1f}deg arm_xy={math.degrees(ARM_XY):.1f}deg "
      f"torso_y_mid={BODY_Y_MID:.1f}")

# ----------------------------------------------------------- 2. garment in
prepped = os.path.join(WORK_DIR, f"prepped_{ITEM_ID}.blend")

def load_garment():
    if os.path.isfile(prepped):
        with bpy.data.libraries.load(prepped) as (src, dst):
            dst.objects = [ITEM_ID]
        obj = dst.objects[0]
        bpy.context.scene.collection.objects.link(obj)
        print(f"[load] reused prepped {prepped}")
        return obj
    if GARMENT.lower().endswith(".blend"):
        with bpy.data.libraries.load(GARMENT) as (src, dst):
            dst.objects = [CFG["source_object"]]
        obj = dst.objects[0]
        bpy.context.scene.collection.objects.link(obj)
    else:
        before = set(bpy.data.objects)
        bpy.ops.wm.fbx_import(filepath=GARMENT)   # ufbx importer (ASCII-capable)
        new = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
        obj = next((o for o in new if o.name.startswith(CFG["source_object"])), new[0])
        for o in set(bpy.data.objects) - before:
            if o is not obj:
                bpy.data.objects.remove(o, do_unlink=True)
    # normalize transforms: bake rotation/location into the data, then force
    # the template object convention (data cm, object scale 0.01)
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
    if abs(obj.scale.x - 1.0) < 1e-4:            # data already cm at scale 1
        obj.scale = (0.01, 0.01, 0.01)
    dims = np.array([list(v.co) for v in obj.data.vertices])
    ext = dims.max(0) - dims.min(0)
    if ext[1] > ext[2]:                          # Y-up source: stand it up
        obj.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
        print("[load] rotated Y-up source to Z-up")
    obj.name = obj.data.name = ITEM_ID
    obj.matrix_world = arm.matrix_world.copy()   # same 0.01-scale convention
    # heavy CLO meshes: single material, weld the unwelded panel seams
    # (CLO exports every garment panel as a separate island — thousands of
    # boundary loops; decimation + smoothing then pull the seams open into
    # visible tears), then decimate
    restyle_material(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bverts = [v for v in bm.verts
              if any(len(e.link_faces) == 1 for e in v.link_edges)]
    if bverts:
        bmesh.ops.remove_doubles(bm, verts=bverts, dist=0.15)
        bm.to_mesh(obj.data)
        print(f"[prep] welded panel seams ({len(bverts)} boundary verts)")
    bm.free()
    if CFG["decimate_faces"] and len(obj.data.polygons) > CFG["decimate_faces"]:
        mod = obj.modifiers.new("Dec", 'DECIMATE')
        mod.ratio = CFG["decimate_faces"] / len(obj.data.polygons)
        with bpy.context.temp_override(object=obj, active_object=obj,
                                       selected_objects=[obj]):
            bpy.ops.object.modifier_apply(modifier="Dec")
        print(f"[prep] decimated -> {len(obj.data.polygons)} faces")
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.object.shade_smooth()
    os.makedirs(WORK_DIR, exist_ok=True)
    bpy.data.libraries.write(prepped, {obj}, path_remap='ABSOLUTE')
    print(f"[prep] cached -> {prepped}")
    return obj


def restyle_material(obj):
    me = obj.data
    me.materials.clear()
    mat = bpy.data.materials.new(f"{ITEM_ID}_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.75
    if CFG.get("color"):
        c = tuple(int(CFG["color"][i:i + 2], 16) / 255 for i in (1, 3, 5))
        def lin(v):
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        bsdf.inputs["Base Color"].default_value = (*[lin(v) for v in c], 1.0)
    if CFG.get("textures") and TEX_DIR:
        nt = mat.node_tree
        for kind, fname in CFG["textures"].items():
            path = os.path.join(TEX_DIR, fname)
            img = bpy.data.images.load(path)
            try:
                if max(img.size) > 2048:
                    img.scale(2048, 2048)
                img.pack()
            except RuntimeError:
                img = bpy.data.images.load(path)
                img.pack()
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            if kind == "diffuse":
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            else:
                img.colorspace_settings.name = "Non-Color"
                nm = nt.nodes.new("ShaderNodeNormalMap")
                nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
                nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.use_backface_culling = False
    me.materials.append(mat)
    for p in me.polygons:
        p.material_index = 0

garment = load_garment()
garment.data.validate(verbose=False)   # weld+decimate can leave degenerate
gme = garment.data                     # loops the glTF exporter warns about
ng = len(gme.vertices)
V = np.zeros(ng * 3)
gme.vertices.foreach_get("co", V)
V = V.reshape(ng, 3)

# ----------------------------------------------------------- 3. fit (cm)
tw = CFG["tweaks"]
s = tw.get("s", 1.0)
V *= s
top_z = V[:, 2].max()
V[:, 2] += (NECK_Z + CFG["collar_rise"] + tw.get("dz", 0.0)) - top_z
V[:, 0] -= (V[:, 0].max() + V[:, 0].min()) / 2
gband = (V[:, 2] > NECK_Z - 20) & (V[:, 2] < NECK_Z - 8) & (np.abs(V[:, 0]) < 12)
if gband.sum() > 20:
    V[:, 1] += BODY_Y_MID + tw.get("dy", 0.0) - \
        (V[gband, 1].max() + V[gband, 1].min()) / 2
print(f"[fit] s={s} placed top_z={V[:, 2].max():.1f} "
      f"bbox_x=({V[:, 0].min():.1f},{V[:, 0].max():.1f}) "
      f"bbox_z=({V[:, 2].min():.1f},{V[:, 2].max():.1f})")

# sleeve bend: rotate each sleeve so its centerline matches the rest-pose
# arm direction. The centerline is fitted on the OUTER half of the lateral
# extent (pure sleeve — skirts/hems never reach that far out); only verts
# within SLEEVE_R of that line rotate, so a dress skirt is never dragged
# along. One proper axis-angle rotation (not per-plane angles, which
# mis-compose for steep sleeves), blended in over the first 6 cm.
SLEEVE_R = 14.0
arm_dir = np.array([fa.x - ua.x, fa.y - ua.y, fa.z - ua.z])
arm_dir /= np.linalg.norm(arm_dir)             # +x side, mirrored space below
for side in ((1.0, -1.0) if CFG.get("sleeve_fit", "auto") == "auto" else ()):
    ax_all = V[:, 0] * side
    cut = (SHOULDER_X + ax_all.max()) / 2
    meas = ax_all > max(cut, SHOULDER_X + 5.0)
    if meas.sum() < 50:
        print(f"[fit] side {side:+.0f}: no sleeve beyond shoulder, skip bend")
        continue
    ax = ax_all[meas]
    fz = np.polyfit(ax, V[meas, 2], 1)
    fy = np.polyfit(ax, V[meas, 1], 1)
    g = np.array([1.0, fy[0], fz[0]])
    g /= np.linalg.norm(g)
    axis = np.cross(g, arm_dir)
    angle = math.atan2(np.linalg.norm(axis), float(g @ arm_dir))
    if np.linalg.norm(axis) < 1e-6:
        continue
    axis /= np.linalg.norm(axis)
    piv = np.array([SHOULDER_X, fy[0] * SHOULDER_X + fy[1],
                    fz[0] * SHOULDER_X + fz[1]])
    line_z = fz[0] * ax_all + fz[1]
    line_y = fy[0] * ax_all + fy[1]
    near = (V[:, 2] - line_z) ** 2 + (V[:, 1] - line_y) ** 2 < SLEEVE_R ** 2
    sel = (ax_all > SHOULDER_X) & near
    p = np.column_stack((ax_all[sel] - piv[0], V[sel, 1] - piv[1],
                         V[sel, 2] - piv[2]))
    t = np.clip((ax_all[sel] - SHOULDER_X) / 6.0, 0, 1)[:, None]
    th = t * angle
    c, sn = np.cos(th), np.sin(th)
    p2 = p * c + np.cross(np.broadcast_to(axis, p.shape), p) * sn + \
        axis[None, :] * (p @ axis)[:, None] * (1 - c)
    # recenter the sleeve tube onto the bone axis: rotation only makes the
    # centerline parallel to the arm — without this the arm can ride above
    # or below the sleeve and poke through it. Ramped over a longer span
    # than the rotation so the shoulder doesn't read as a puffed hump.
    t_rec = np.clip((ax_all[sel] - SHOULDER_X) / 16.0, 0, 1)[:, None]
    p2 += t_rec * np.array([0.0, ua.y - piv[1], SHOULDER_Z - piv[2]])[None, :]
    V[sel, 0] = side * (piv[0] + p2[:, 0])
    V[sel, 1] = piv[1] + p2[:, 1]
    V[sel, 2] = piv[2] + p2[:, 2]
    print(f"[fit] side {side:+.0f}: sleeve rotated {math.degrees(angle):.1f}deg, "
          f"recentered dy={ua.y - piv[1]:+.1f} dz={SHOULDER_Z - piv[2]:+.1f} "
          f"({sel.sum()} verts)")

# push out of the body (only actual penetration, keeps cloth layering), then
# relax the moved verts against their neighbors and push once more — the
# smooth pass removes the spikes/tears single-vert projection leaves behind
bvh = BVHTree.FromPolygons([Vector(v) for v in bco],
                           [tuple(p.vertices) for p in mesh.polygons])
ne = len(gme.edges)
edges = np.zeros(ne * 2, dtype=np.int64)
gme.edges.foreach_get("vertices", edges)
edges = edges.reshape(ne, 2)

def push_out(clear):
    moved = np.zeros(ng, dtype=bool)
    for i in range(ng):
        loc, nrm, _, dist = bvh.find_nearest(Vector(V[i]))
        if loc is None or dist > 3.0:
            continue
        if (Vector(V[i]) - loc).dot(nrm) < clear:
            V[i] = list(loc + nrm * clear)
            moved[i] = True
    return moved

def smooth(sel_mask, iters=2, lam=0.5):
    for _ in range(iters):
        acc = np.zeros_like(V)
        cnt = np.zeros(ng)
        for a, b in ((0, 1), (1, 0)):
            np.add.at(acc, edges[:, a], V[edges[:, b]])
            np.add.at(cnt, edges[:, a], 1)
        ok = sel_mask & (cnt > 0)
        V[ok] = V[ok] * (1 - lam) + acc[ok] / cnt[ok, None] * lam

CLR = CFG.get("clearance", 0.3)
counts = []
moved = push_out(CLR)
counts.append(int(moved.sum()))
for _ in range(3):                 # relax/push until the surface settles
    smooth(moved)
    moved = push_out(CLR)
    counts.append(int(moved.sum()))
print(f"[fit] push-out rounds (clear {CLR}cm): {counts}")

gme.vertices.foreach_set("co", V.reshape(-1).astype(np.float32))
gme.update()

# ----------------------------------------------------------- 4. skinning
bpy.ops.object.select_all(action='DESELECT')
garment.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.data_transfer(use_create=True, data_type='VGROUP_WEIGHTS',
    vert_mapping='POLYINTERP_NEAREST', layers_select_src='ALL',
    layers_select_dst='NAME', mix_mode='REPLACE')
body.select_set(False)
bpy.context.view_layer.objects.active = garment
bpy.ops.object.vertex_group_limit_total(limit=4, group_select_mode='ALL')
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',
                                          lock_active=False)
mod = garment.modifiers.new("Armature", 'ARMATURE')
mod.object = arm
garment.parent = arm
garment.matrix_parent_inverse = arm.matrix_world.inverted()
print(f"[skin] {len(garment.vertex_groups)} vertex groups transferred")

# ----------------------------------------------------------- 5. export
out_dir = os.path.join(SHARED_DIR, "clothes", ITEM_ID)
os.makedirs(out_dir, exist_ok=True)
glb_path = os.path.join(out_dir, f"{ITEM_ID}.glb")
bpy.ops.object.select_all(action='DESELECT')
garment.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = garment
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
    use_selection=True, export_skins=True, export_morph=False,
    export_animations=False, export_yup=True)
print(f"[glb] {os.path.getsize(glb_path) / 1e6:.1f} MB -> {glb_path}")

meta = {
    "id": ITEM_ID, "label": CFG["label"], "slot": "top",
    "category_dir": "clothes", "attach_type": "skinned", "attach_to": None,
    "colorable_materials": [f"{ITEM_ID}_mat"] if CFG["colorable"] else [],
    "gender": CFG["gender"], "style": "realistic", "source": CFG["source"],
    "file": f"clothes/{ITEM_ID}/{ITEM_ID}.glb",
    "thumb": f"clothes/{ITEM_ID}/thumbnail.png",
}

# ----------------------------------------------------------- 6. renders
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.17, 0.20, 1)
scene.world = world
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
for nm, (rx, rz, e) in {"Key": (60, 15, 3.0), "Fill": (75, 195, 1.2)}.items():
    ld = bpy.data.lights.new(nm, 'SUN')
    ld.energy = e
    lo = bpy.data.objects.new(nm, ld)
    scene.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(rx), 0, math.radians(rz))

for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = True
garment.hide_render = False
scene.render.resolution_x = scene.render.resolution_y = 256
wpts = V * 0.01                                # world = data cm * 0.01 scale
lo_v = Vector(wpts.min(0))
hi_v = Vector(wpts.max(0))
center, size = (lo_v + hi_v) / 2, max((hi_v - lo_v).length, 0.05)
cam.location = center + Vector((0.45, -1.0, 0.35)).normalized() * size * 1.6
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(out_dir, "thumbnail.png")
bpy.ops.render.render(write_still=True)

os.makedirs(PREVIEW_DIR, exist_ok=True)
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = False
scene.render.resolution_x = scene.render.resolution_y = 640
target = Vector((0, 0, (NECK_Z - 35) * 0.01))
for tag, off in (("front", Vector((0, -1.7, 0.05))),
                 ("three_q", Vector((1.2, -1.2, 0.1))),
                 ("side", Vector((1.7, 0, 0.05)))):
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"{ITEM_ID}_{tag}.png")
    bpy.ops.render.render(write_still=True)
print(f"[render] previews -> {PREVIEW_DIR}")

# ----------------------------------------- 7. item.json + catalog + sandbox
with open(os.path.join(out_dir, "item.json"), "w") as f:
    json.dump(meta, f, indent=2)
cat_path = os.path.join(SHARED_DIR, "catalog.json")
with open(cat_path) as f:
    catalog = json.load(f)
items = [it for it in catalog["items"] if it["id"] != ITEM_ID]
last = max((i for i, it in enumerate(items)
            if it["category_dir"] == "clothes"), default=len(items) - 1)
items.insert(last + 1, meta)
catalog["items"] = items
with open(cat_path, "w") as f:
    json.dump(catalog, f, indent=2)

sb = os.path.join(SANDBOX_DIR, "clothes", ITEM_ID)
if os.path.isdir(sb):
    shutil.rmtree(sb)
shutil.copytree(out_dir, sb)
shutil.copy2(cat_path, os.path.join(SANDBOX_DIR, "catalog.json"))
print(f"[done] {ITEM_ID} integrated ({meta['file']})")
