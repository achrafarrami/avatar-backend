"""
Demo wardrobe library builder for the Avatar Asset System.

Generates every demo asset deterministically from the male template:
  - "skinned" assets (hair, beard, eyebrows, tops, pants, shoes) are SHELLS
    extracted from the actual body mesh via skinning-weight + geometric masks,
    offset along normals and solidified. They keep the body's vertex groups
    and armature, so they deform with the skeleton exactly like the body —
    no hand-weighting, perfect fit, zero base-mesh modification.
  - "bone" assets (glasses, hats, watch, earrings, necklace, backpack) are
    primitive-based rigid meshes authored RELATIVE TO THEIR ATTACH BONE
    (runtime parents them to that bone; see SandboxViewer.attachAsset).

Outputs, per item:
  assets/shared/<category>/<id>/<id>.glb + item.json + thumbnail.png
plus an aggregated assets/shared/catalog.json, and a copy of the whole tree
into frontend/threejs-viewer/public/wardrobe/ for the sandbox.

Usage:
  blender --background --python build_demo_assets.py -- \
      <template.blend> <assets_shared_dir> <sandbox_wardrobe_dir>
"""
import bpy
import bmesh
import json
import math
import os
import shutil
import sys
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE = argv[0]
SHARED_DIR = argv[1]
SANDBOX_DIR = argv[2]

BODY_NAME, ARM_NAME, EYE_NAME = "Male_Body", "Male_Armature", "CC_Base_Eye"

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
body = bpy.data.objects[BODY_NAME]
arm = bpy.data.objects[ARM_NAME]
mesh = body.data
n = len(mesh.vertices)

# ---------------------------------------------------------------- landmarks
co = np.zeros(n * 3)
key_blocks = mesh.shape_keys.key_blocks
key_blocks["Basis"].data.foreach_get("co", co)
co = co.reshape(n, 3)
X, Y, Z = co[:, 0], co[:, 1], co[:, 2]

normals = np.zeros(n * 3)
mesh.vertices.foreach_get("normal", normals)
normals = normals.reshape(n, 3)

bones = arm.data.bones
HEAD_Z = bones["CC_Base_Head"].head_local.z

def bone_world_m(name):
    return arm.matrix_world @ bones[name].head_local

# vertex-group weight reader
vg_index = {g.name: g.index for g in body.vertex_groups}

def vg_weights(names):
    idx = {vg_index[nm] for nm in names if nm in vg_index}
    w = np.zeros(n)
    for v in mesh.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w

# expression-derived region magnitudes (same trick as the morph generator)
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
mouth_mag = expr_mask(["Mouth_"])
brow_sel = brow_mag > 0.3
BROW_Z = float((Z[brow_sel] * brow_mag[brow_sel]).sum() / brow_mag[brow_sel].sum())
mouth_sel = mouth_mag > 0.3
MOUTH_Z = float((Z[mouth_sel] * mouth_mag[mouth_sel]).sum() / mouth_mag[mouth_sel].sum())

head_w = vg_weights(["CC_Base_Head"])

# ear region + earlobe landmarks (used for exclusions and earring placement)
ear_region = (head_w > 0.3) & (np.abs(X) > 6.2) & (Z < 168.5) & (Z > 155)
def earlobe(side):
    sel = ear_region & ((X > 0) if side > 0 else (X < 0))
    i = np.where(sel)[0][np.argmin(Z[sel])]
    return co[i]

# scalp mask (shared by all hair styles)
scalp = (head_w > 0.4) & (Z > 169.5) & ~ear_region & \
        ((Y > -5.5) | (Z > BROW_Z + 4.0))
SCALP_TOP_Z = float(Z[scalp].max())          # crown height, used by hats

# ---------------------------------------------------------------- helpers
built = []   # (obj, meta)

def flat_material(name, hexcolor, roughness=0.65, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    c = tuple(int(hexcolor[i:i+2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def make_shell(item_id, mask, offset, thickness, color, displace_noise=0.0):
    """Duplicate the body, keep only masked verts, offset along normals,
    solidify. Result keeps vertex groups + armature modifier = skinned."""
    obj = body.copy()
    obj.data = body.data.copy()
    obj.name = item_id
    bpy.context.scene.collection.objects.link(obj)
    obj.shape_key_clear()
    me = obj.data

    disp = offset + (displace_noise *
        (0.5 + 0.5 * np.sin(X * 2.1) * np.sin(Z * 2.7) * np.cos(Y * 1.9))
        if displace_noise else 0.0)
    new_co = co + normals * (np.asarray(disp).reshape(-1, 1) if displace_noise else disp)
    me.vertices.foreach_set("co", new_co.reshape(-1).astype(np.float32))

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    doomed = [v for v in bm.verts if mask[v.index] < 0.5]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(me)
    bm.free()

    me.materials.clear()
    me.materials.append(flat_material(f"{item_id}_mat", color))

    sol = obj.modifiers.new("Sol", 'SOLIDIFY')
    sol.thickness = thickness
    sol.offset = 1.0
    with bpy.context.temp_override(object=obj, active_object=obj,
                                   selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier="Sol")
    return obj


def join(objs, name):
    with bpy.context.temp_override(active_object=objs[0],
                                   selected_editable_objects=objs,
                                   selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def finalize_rigid(objs, item_id, color, bone_name, roughness=0.5, metallic=0.0):
    """Join primitives, recenter geometry relative to the attach bone."""
    obj = join(objs, item_id)
    obj.data.materials.clear()
    obj.data.materials.append(flat_material(f"{item_id}_mat", color, roughness, metallic))
    origin = bone_world_m(bone_name)
    for v in obj.data.vertices:
        v.co = (obj.matrix_world @ v.co) - origin
    obj.matrix_world.identity()
    return obj


def add(obj, item_id, label, slot, category_dir, attach_type,
        attach_to=None, colorable=True):
    built.append((obj, {
        "id": item_id, "label": label, "slot": slot,
        "category_dir": category_dir, "attach_type": attach_type,
        "attach_to": attach_to,
        "colorable_materials": [f"{item_id}_mat"] if colorable else [],
    }))

# ================================================================ HAIR
# Hair items are NOT generated here anymore. The shell-based hair looked like
# helmets and was retired (2026-07-20); hairstyles come from build_hair_style.py
# (procedural) or import_hair_pack.py (external packs) and merge into the
# catalog this script produces. The scalp mask above is still used by hats.
HAIR = "#3b2a1e"

# ================================================================ BEARDS
beard_full = (head_w > 0.3) & (Y < -1.0) & (Z > 149) & (
    (Z < MOUTH_Z - 1.2) |
    ((np.abs(X) > 2.8) & (Z < MOUTH_Z + 1.2)) |
    ((Z > MOUTH_Z + 0.3) & (Z < MOUTH_Z + 1.3) & (np.abs(X) < 3.2))  # mustache, on the lip not the nose
)
add(make_shell("beard_short", beard_full, 0.45, 0.55, HAIR),
    "beard_short", "Short Beard", "beard", "beards", "skinned")
goatee = beard_full & (np.abs(X) < 2.6)
add(make_shell("goatee", goatee, 0.5, 0.6, HAIR),
    "goatee", "Goatee", "beard", "beards", "skinned")

# ================================================================ EYEBROWS
# Brow_Raise_* keys drag the whole forehead, so a loose expression mask bleeds
# far above the brow line — require a tight Z band + strongly front-facing +
# lateral limits, and a higher magnitude cut.
brow_region = (brow_mag > 0.72) & (normals[:, 1] < -0.45) & \
              (np.abs(Z - BROW_Z) < 1.3) & (np.abs(X) > 1.2) & (np.abs(X) < 6.0)
add(make_shell("eyebrows_natural", brow_region, 0.10, 0.22, "#2f2318"),
    "eyebrows_natural", "Natural", "eyebrows", "eyebrows", "skinned")
add(make_shell("eyebrows_thick", brow_region, 0.2, 0.38, "#2f2318"),
    "eyebrows_thick", "Thick", "eyebrows", "eyebrows", "skinned")

# ================================================================ GLASSES
def build_glasses(item_id, lens_rx, lens_rz, color):
    head = bone_world_m("CC_Base_Head")
    # lenses must clear the brow/nose: ~11.5cm in front of the head bone
    LZ, LY, LX = head.z + 0.068, head.y - 0.115, 0.033
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.024, minor_radius=0.0032,
            location=(side * LX, LY, LZ), rotation=(math.radians(90), 0, 0))
        o = bpy.context.object
        o.scale = (lens_rx, 1, lens_rz)
        with bpy.context.temp_override(active_object=o, selected_editable_objects=[o]):
            bpy.ops.object.transform_apply(scale=True)
        parts.append(o)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0028,
        depth=LX * 2 - 0.024 * 2 * lens_rx + 0.004,
        location=(0, LY, LZ + 0.004), rotation=(0, math.radians(90), 0))
    parts.append(bpy.context.object)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0028, depth=0.115,
            location=(side * (LX + 0.024 * lens_rx), LY + 0.055, LZ + 0.004),
            rotation=(math.radians(90), 0, 0))
        parts.append(bpy.context.object)
    return finalize_rigid(parts, item_id, color, "CC_Base_Head", roughness=0.3)

add(build_glasses("glasses_round", 1.0, 1.0, "#17181c"),
    "glasses_round", "Round", "glasses", "glasses", "bone", "CC_Base_Head", colorable=False)
add(build_glasses("glasses_square", 1.18, 0.88, "#3a2c20"),
    "glasses_square", "Square", "glasses", "glasses", "bone", "CC_Base_Head", colorable=False)

# ================================================================ HATS
def build_cap():
    head = bone_world_m("CC_Base_Head")
    crown_z = SCALP_TOP_Z * 0.01
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.112,
        location=(0, head.y + 0.008, crown_z - 0.052), segments=24, ring_count=16)
    dome = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(dome.data)
    doomed = [v for v in bm.verts if v.co.z < 0.005]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(dome.data); bm.free()
    parts.append(dome)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.085, depth=0.006,
        location=(0, head.y - 0.085, crown_z - 0.048))
    brim = bpy.context.object
    brim.scale = (0.75, 1.1, 1)
    with bpy.context.temp_override(active_object=brim, selected_editable_objects=[brim]):
        bpy.ops.object.transform_apply(scale=True)
    parts.append(brim)
    return finalize_rigid(parts, "cap", "#b33a2f", "CC_Base_Head")

def build_beanie():
    head = bone_world_m("CC_Base_Head")
    crown_z = SCALP_TOP_Z * 0.01
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.117,
        location=(0, head.y + 0.008, crown_z - 0.06), segments=24, ring_count=16)
    dome = bpy.context.object
    dome.scale = (1, 1, 1.15)
    with bpy.context.temp_override(active_object=dome, selected_editable_objects=[dome]):
        bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(dome.data)
    doomed = [v for v in bm.verts if v.co.z < -0.045]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(dome.data); bm.free()
    return finalize_rigid([dome], "beanie", "#3d5a99", "CC_Base_Head")

add(build_cap(), "cap", "Cap", "hat", "hats", "bone", "CC_Base_Head")
add(build_beanie(), "beanie", "Beanie", "hat", "hats", "bone", "CC_Base_Head")

# ================================================================ TOPS
torso_w = vg_weights(["CC_Base_Spine01", "CC_Base_Spine02", "CC_Base_Waist",
    "CC_Base_L_Clavicle", "CC_Base_R_Clavicle", "CC_Base_L_RibsTwist",
    "CC_Base_R_RibsTwist", "CC_Base_L_Breast", "CC_Base_R_Breast"])
upper_arm_w = vg_weights(["CC_Base_L_Upperarm", "CC_Base_R_Upperarm",
    "CC_Base_L_UpperarmTwist01", "CC_Base_R_UpperarmTwist01",
    "CC_Base_L_UpperarmTwist02", "CC_Base_R_UpperarmTwist02"])
lower_arm_w = vg_weights(["CC_Base_L_Forearm", "CC_Base_R_Forearm",
    "CC_Base_L_ForearmTwist01", "CC_Base_R_ForearmTwist01",
    "CC_Base_L_ForearmTwist02", "CC_Base_R_ForearmTwist02",
    "CC_Base_L_ElbowShareBone", "CC_Base_R_ElbowShareBone"])
hip_w = vg_weights(["CC_Base_Hip", "CC_Base_Pelvis"])
neck_w = vg_weights(["CC_Base_NeckTwist01", "CC_Base_NeckTwist02", "CC_Base_Head"])

tshirt_mask = ((torso_w + hip_w * 0.45 > 0.35) |
               ((upper_arm_w > 0.35) & (np.abs(X) < 32))) & (neck_w < 0.35)
add(make_shell("tshirt", tshirt_mask, 0.7, 0.8, "#e8e8ea"),
    "tshirt", "T-Shirt", "top", "clothes", "skinned")

hoodie_mask = ((torso_w + hip_w * 0.5 > 0.3) |
               (upper_arm_w > 0.25) | (lower_arm_w > 0.25)) & (neck_w < 0.5)
add(make_shell("hoodie", hoodie_mask, 1.4, 1.5, "#3d5a99"),
    "hoodie", "Hoodie", "top", "clothes", "skinned")

jacket_mask = hoodie_mask & ~((np.abs(X) < 1.3) & (Y < -5) & (Z < 148) & (Z > 105))
add(make_shell("jacket", jacket_mask, 1.1, 1.3, "#2c2c34"),
    "jacket", "Jacket", "top", "clothes", "skinned")

# ================================================================ PANTS
leg_w = vg_weights(["CC_Base_L_Thigh", "CC_Base_R_Thigh",
    "CC_Base_L_ThighTwist01", "CC_Base_R_ThighTwist01",
    "CC_Base_L_ThighTwist02", "CC_Base_R_ThighTwist02",
    "CC_Base_L_Calf", "CC_Base_R_Calf",
    "CC_Base_L_CalfTwist01", "CC_Base_R_CalfTwist01",
    "CC_Base_L_CalfTwist02", "CC_Base_R_CalfTwist02",
    "CC_Base_L_KneeShareBone", "CC_Base_R_KneeShareBone"])
foot_w = vg_weights(["CC_Base_L_Foot", "CC_Base_R_Foot"])
KNEE_Z = bones["CC_Base_L_KneeShareBone"].head_local.z
ANKLE_Z = bones["CC_Base_L_Foot"].head_local.z

jeans_mask = ((hip_w > 0.3) | (leg_w > 0.3)) & (foot_w < 0.4) & (Z > ANKLE_Z + 1)
add(make_shell("jeans", jeans_mask, 0.6, 0.8, "#3a4a6b"),
    "jeans", "Jeans", "pants", "clothes", "skinned")
shorts_mask = jeans_mask & (Z > KNEE_Z - 2)
add(make_shell("shorts", shorts_mask, 0.7, 0.9, "#6b6f78"),
    "shorts", "Shorts", "pants", "clothes", "skinned")

# ================================================================ SHOES
shoe_w = vg_weights(["CC_Base_L_Foot", "CC_Base_R_Foot",
    "CC_Base_L_ToeBase", "CC_Base_R_ToeBase",
    "CC_Base_L_ToeBaseShareBone", "CC_Base_R_ToeBaseShareBone"]) + \
    vg_weights([g for g in vg_index if "Toe1" in g])
sneaker_mask = (shoe_w > 0.3) & (Z < ANKLE_Z + 4)
add(make_shell("sneakers", sneaker_mask, 0.8, 1.0, "#e8e8ea"),
    "sneakers", "Sneakers", "shoes", "shoes", "skinned")

# ================================================================ ACCESSORIES
def build_watch():
    hand = bones["CC_Base_L_Hand"].head_local
    forearm = bones["CC_Base_L_Forearm"].head_local
    axis = (Vector(hand) - Vector(forearm)).normalized()
    pos = (arm.matrix_world @ (Vector(hand) - axis * 2.0))
    rot = axis.to_track_quat('Z', 'Y').to_euler()
    parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.007,
        location=pos, rotation=rot)
    parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.019, depth=0.009, location=pos,
        rotation=rot)
    face = bpy.context.object
    face.location += Vector((0, 0, 0.017))  # sit on top of the wrist
    parts.append(face)
    return finalize_rigid(parts, "watch", "#17181c", "CC_Base_L_Hand", roughness=0.3, metallic=0.4)

add(build_watch(), "watch", "Watch", "wrist", "accessories", "bone",
    "CC_Base_L_Hand", colorable=False)

def build_earrings():
    parts = []
    for side in (-1, 1):
        lobe = earlobe(side) * 0.01
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006,
            location=(lobe[0], lobe[1], lobe[2] - 0.008))
        parts.append(bpy.context.object)
    return finalize_rigid(parts, "earrings", "#c9a54a", "CC_Base_Head",
                          roughness=0.2, metallic=0.9)

add(build_earrings(), "earrings", "Earrings", "ears", "accessories", "bone",
    "CC_Base_Head", colorable=False)

def build_necklace():
    neck = bone_world_m("CC_Base_NeckTwist01")
    parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.0035,
        location=(0, neck.y - 0.015, neck.z - 0.035),
        rotation=(math.radians(25), 0, 0))
    parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009,
        location=(0, neck.y - 0.088, neck.z - 0.065))
    parts.append(bpy.context.object)
    return finalize_rigid(parts, "necklace", "#c9a54a", "CC_Base_NeckTwist01",
                          roughness=0.2, metallic=0.9)

add(build_necklace(), "necklace", "Necklace", "neck", "accessories", "bone",
    "CC_Base_NeckTwist01", colorable=False)

def build_backpack():
    spine = bone_world_m("CC_Base_Spine02")
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, spine.y + 0.13, spine.z + 0.02))
    pack = bpy.context.object
    pack.scale = (0.14, 0.055, 0.19)
    with bpy.context.temp_override(active_object=pack, selected_editable_objects=[pack]):
        bpy.ops.object.transform_apply(scale=True)
    bev = pack.modifiers.new("Bev", 'BEVEL')
    bev.width = 0.02
    bev.segments = 3
    with bpy.context.temp_override(object=pack, active_object=pack, selected_objects=[pack]):
        bpy.ops.object.modifier_apply(modifier="Bev")
    return finalize_rigid([pack], "backpack", "#4a5d3a", "CC_Base_Spine02")

add(build_backpack(), "backpack", "Backpack", "back", "accessories", "bone",
    "CC_Base_Spine02")

# ================================================================ EXPORT
print(f"\nBuilt {len(built)} assets. Exporting...")

for obj, meta in built:
    out_dir = os.path.join(SHARED_DIR, meta["category_dir"], meta["id"])
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, meta["id"] + ".glb")

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    skinned = meta["attach_type"] == "skinned"
    if skinned:
        arm.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
        use_selection=True, export_skins=skinned, export_morph=False,
        export_animations=False, export_yup=True)
    meta["file"] = f"{meta['category_dir']}/{meta['id']}/{meta['id']}.glb"
    meta["thumb"] = f"{meta['category_dir']}/{meta['id']}/thumbnail.png"
    size = os.path.getsize(glb_path) / 1e6
    print(f"  {meta['id']:22s} {size:5.1f} MB -> {glb_path}")

# ---------------------------------------------------------------- thumbnails
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 256
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

body.hide_render = True
arm.hide_render = True
for o in bpy.data.objects:
    if o.type == 'MESH' and o not in (body,):
        o.hide_render = True

for obj, meta in built:
    obj.hide_render = False
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, size = (lo + hi) / 2, max((hi - lo).length, 0.05)
    cam.location = center + Vector((0.45, -1.0, 0.35)).normalized() * size * 1.6
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(SHARED_DIR, meta["category_dir"],
                                         meta["id"], "thumbnail.png")
    bpy.ops.render.render(write_still=True)
    obj.hide_render = True

# ---------------------------------------------------------------- catalog
catalog = {
    "version": 1,
    "palettes": {
        "hair": ["#0f0f12", "#241a14", "#3b2a1e", "#55371f", "#6a4a2f", "#7a3f24",
                 "#8c6239", "#a67c48", "#c9a06a", "#e6d6b8", "#9a9ea6", "#e8e6e2",
                 "#a34a26", "#b3402e"],
        "cloth": ["#e8e8ea", "#17181c", "#3d5a99", "#b33a2f", "#3f6b43", "#6b6f78", "#7a4a8f"],
    },
    "slots": {
        "hair":     {"label": "Hair",     "tab": "appearance", "palette": "hair"},
        "beard":    {"label": "Beard",    "tab": "appearance", "palette": "hair"},
        "eyebrows": {"label": "Eyebrows", "tab": "appearance", "palette": "hair"},
        "glasses":  {"label": "Glasses",  "tab": "appearance"},
        "hat":      {"label": "Hat",      "tab": "appearance", "palette": "cloth"},
        "top":      {"label": "Top",      "tab": "clothing",   "palette": "cloth"},
        "pants":    {"label": "Pants",    "tab": "clothing",   "palette": "cloth"},
        "shoes":    {"label": "Shoes",    "tab": "clothing",   "palette": "cloth"},
        "wrist":    {"label": "Watch",    "tab": "accessories"},
        "ears":     {"label": "Earrings", "tab": "accessories"},
        "neck":     {"label": "Necklace", "tab": "accessories"},
        "back":     {"label": "Backpack", "tab": "accessories", "palette": "cloth"},
    },
    "items": [meta for _, meta in built],
}
with open(os.path.join(SHARED_DIR, "catalog.json"), "w") as f:
    json.dump(catalog, f, indent=2)
for _, meta in built:
    item_dir = os.path.join(SHARED_DIR, meta["category_dir"], meta["id"])
    with open(os.path.join(item_dir, "item.json"), "w") as f:
        json.dump(meta, f, indent=2)

# ---------------------------------------------------------------- sandbox copy
if os.path.isdir(SANDBOX_DIR):
    shutil.rmtree(SANDBOX_DIR)
shutil.copytree(SHARED_DIR, SANDBOX_DIR)
print(f"\nCatalog: {len(built)} items -> {SHARED_DIR}")
print(f"Sandbox copy -> {SANDBOX_DIR}")
