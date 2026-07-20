"""
Integrate an external women's-hair pack (hair_women.blend) into the Avatar
Asset System.

Pack layout (inspected 2026-07-20): 10 hairstyles displayed on 10 mannequin
head busts, one pair per grid slot, no collections, generic names ("1"/"111",
"6."/"666"...), Arabic default material names, ~850 packed textures of which
only the hair ones are used. NEVER run this on the original file — pass a
working copy (the original stays pristine).

Per style this script:
  - identifies hair vs display-head within each co-located pair (heads share
    a common dims fingerprint ~0.15 x 0.18 x 0.29m)
  - applies transforms, renames object+mesh+material to hair_wNN
  - auto-fits to the female avatar: the pack's own bust registers each hair,
    so mapping bust-crown -> female-crown (uniform scale by head width)
    places the hair correctly; per-style TWEAKS allow manual refinement
  - re-centers geometry relative to CC_Base_Head (bone-rigid attachment =
    follows the head bone in animation, same contract as hats/glasses)
  - exports GLB (only textures actually used by that hair travel with it),
    renders thumbnail + on-head front/side verification renders
  - writes item.json metadata and merges everything into catalog.json,
    then copies to the sandbox wardrobe

Usage:
  blender --background --python import_hair_pack.py -- \
      <pack_working_copy.blend> <female_template.blend> \
      <assets_shared_dir> <sandbox_wardrobe_dir> <preview_dir>
"""
import bpy
import json
import math
import os
import shutil
import sys
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PACK, TEMPLATE, SHARED_DIR, SANDBOX_DIR, PREVIEW_DIR = \
    [os.path.abspath(a) for a in argv[:5]]

# id -> label, named from the first verification render pass (2026-07-20)
STYLE_NAMES = {
    "hair_w01": "Low Pigtails", "hair_w02": "High Ponytail",
    "hair_w03": "Long Sweep", "hair_w04": "Side Sweep",
    "hair_w05": "Loose Updo", "hair_w06": "Low Bun",
    "hair_w07": "Spiky Fringe", "hair_w08": "Slick Pixie",
    "hair_w09": "Wavy Bob", "hair_w10": "Side Ponytail",
}
# per-style manual fit refinement (meters / extra scale), applied after autofit
TWEAKS = {
    "hair_w01": {"dz": -0.001, "s": 1.06},   # tight autofit — scalp clipped through
    "hair_w04": {"dz": -0.004},
    "hair_w07": {"dz": -0.008, "s": 0.90},   # autofit overscaled (1.165) — spikes floated
}

# pack materials are plain untextured Principled colors (verified: uniform
# blonde, no image nodes) -> restyle to our standard hair default + palette.
# sRGB->linear so the exported baseColorFactor matches palette hex #3b2a1e
def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
HAIR_DEFAULT = tuple(_srgb_to_linear(v / 255) for v in (0x3b, 0x2a, 0x1e)) + (1.0,)

HEAD_DIMS = Vector((0.153, 0.183, 0.293))   # display-bust fingerprint

# ------------------------------------------------------------ 1. the pack
bpy.ops.wm.open_mainfile(filepath=PACK)

pairs = {}
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    key = (round(o.location.x, 2), round(o.location.z, 2))
    pairs.setdefault(key, []).append(o)

def head_score(o):
    return sum(abs(o.dimensions[i] - HEAD_DIMS[i]) for i in range(3))

# order styles reading the grid: top row first, left to right
ordered = sorted(pairs.items(), key=lambda kv: (-kv[0][1], kv[0][0]))
styles = []          # (style_id, hair_obj, bust_anchor(world), bust_width)
for i, (key, objs) in enumerate(ordered, 1):
    if len(objs) != 2:
        sys.exit(f"grid slot {key}: expected 2 objects, got {[o.name for o in objs]}")
    head, hair = sorted(objs, key=head_score)
    sid = f"hair_w{i:02d}"

    # apply transforms on the hair, rename everything
    with bpy.context.temp_override(active_object=hair, selected_objects=[hair],
                                   selected_editable_objects=[hair]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    hair.name = sid
    hair.data.name = sid
    for slot in hair.material_slots:
        if slot.material:
            slot.material.name = f"{sid}_mat"
            slot.material.use_backface_culling = False
            if slot.material.use_nodes:
                for nd in slot.material.node_tree.nodes:
                    if nd.type == 'BSDF_PRINCIPLED':
                        nd.inputs["Base Color"].default_value = HAIR_DEFAULT
                        nd.inputs["Roughness"].default_value = 0.55

    # bust registration anchor: top-center of the display head
    mw = head.matrix_world
    hco = np.array([list(mw @ v.co) for v in head.data.vertices])
    top = hco[:, 2].max()
    crown = hco[hco[:, 2] > top - 0.01]
    anchor = Vector((float(crown[:, 0].mean()), float(crown[:, 1].mean()), float(top)))
    styles.append((sid, sid, anchor, float(hco[:, 0].max() - hco[:, 0].min())))

print(f"[pack] {len(styles)} styles identified")

# delete busts + everything that is not a hair object
keep = {s[1] for s in styles}
for o in list(bpy.data.objects):
    if o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)

WORK2 = PACK.replace(".blend", "_clean.blend")
bpy.ops.wm.save_as_mainfile(filepath=WORK2)
meta_styles = [(sid, name, list(anchor), w) for sid, name, anchor, w in styles]

# ---------------------------------------------- 2. female template + fit
bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
body = bpy.data.objects["Female_Body"]
arm = bpy.data.objects["Female_Armature"]
bones = arm.data.bones

# female head measurements (world meters)
mesh = body.data
n = len(mesh.vertices)
co = np.zeros(n * 3)
mesh.shape_keys.key_blocks["Basis"].data.foreach_get("co", co)
co = co.reshape(n, 3)
vg_index = {g.name: g.index for g in body.vertex_groups}
head_idx = vg_index["CC_Base_Head"]
head_w = np.zeros(n)
for v in mesh.vertices:
    for g in v.groups:
        if g.group == head_idx:
            head_w[v.index] = g.weight
mw = np.array(body.matrix_world)
world = co @ mw[:3, :3].T + mw[:3, 3]
hsel = (head_w > 0.5) & (world[:, 2] > float(
    (arm.matrix_world @ bones["CC_Base_Head"].head_local).z) + 0.02)
hw = world[hsel]
fem_top = hw[:, 2].max()
crown = hw[hw[:, 2] > fem_top - 0.01]
fem_anchor = Vector((0.0, float(crown[:, 1].mean()), float(fem_top)))
fem_width = float(hw[:, 0].max() - hw[:, 0].min())
head_origin = arm.matrix_world @ bones["CC_Base_Head"].head_local
print(f"[fit] female head width {fem_width:.3f}m crown {fem_anchor}")

# append cleaned hair objects
with bpy.data.libraries.load(WORK2) as (src, dst):
    dst.objects = [s[0] for s in meta_styles]
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)

built = []
for sid, _, anchor, bust_width in meta_styles:
    hair = bpy.data.objects[sid]
    tw = TWEAKS.get(sid, {})
    s = (fem_width / bust_width) * tw.get("s", 1.0)
    off = Vector((0, tw.get("dy", 0.0), tw.get("dz", 0.0)))
    a = Vector(anchor)
    for v in hair.data.vertices:
        p = (Vector(v.co) - a) * s + fem_anchor + off
        v.co = p - head_origin          # bone-relative, ready for runtime parent
    hair.matrix_world.identity()
    built.append((hair, {
        "id": sid, "label": STYLE_NAMES.get(sid, sid), "slot": "hair",
        "category_dir": "hair", "attach_type": "bone",
        "attach_to": "CC_Base_Head",
        "colorable_materials": [f"{sid}_mat"],
        "gender": "female", "style": "realistic",
        "source": "hair_women.blend pack",
        "file": f"hair/{sid}/{sid}.glb", "thumb": f"hair/{sid}/thumbnail.png",
    }))
    print(f"[fit] {sid}: scale {s:.3f}")

# --------------------------------------------------------- 3. export GLBs
# geometry is bone-relative with identity transforms (authoring convention
# for attach_type "bone" — runtime parents the node to CC_Base_Head)
for hair, meta in built:
    out_dir = os.path.join(SHARED_DIR, "hair", meta["id"])
    os.makedirs(out_dir, exist_ok=True)
    glb = os.path.join(out_dir, meta["id"] + ".glb")
    bpy.ops.object.select_all(action='DESELECT')
    hair.select_set(True)
    bpy.context.view_layer.objects.active = hair
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB',
        use_selection=True, export_skins=False, export_morph=False,
        export_animations=False, export_yup=True)
    print(f"[glb] {meta['id']:10s} {os.path.getsize(glb)/1e6:5.1f} MB")

# ------------------------------------------------------------- 4. renders
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
world_dat = bpy.data.worlds.new("W")
world_dat.use_nodes = True
world_dat.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.17, 0.20, 1)
scene.world = world_dat
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
fill.energy = 1.2
fo = bpy.data.objects.new("Fill", fill)
scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(195))

for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = True

os.makedirs(PREVIEW_DIR, exist_ok=True)
target = Vector((0, head_origin.y, head_origin.z + 0.075))
for hair, meta in built:
    hair.matrix_world.translation = head_origin
    hair.hide_render = False
    # thumbnail: hair alone
    scene.render.resolution_x = scene.render.resolution_y = 256
    pts = [hair.matrix_world @ v.co for v in hair.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, size = (lo + hi) / 2, max((hi - lo).length, 0.05)
    cam.location = center + Vector((0.45, -1.0, 0.35)).normalized() * size * 1.6
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(SHARED_DIR, "hair", meta["id"], "thumbnail.png")
    bpy.ops.render.render(write_still=True)
    # on-head verification: front + side, with the female body visible
    for b in bpy.data.objects:
        if b.type == 'MESH' and b.name.startswith(("Female_", "CC_Base")):
            b.hide_render = False
    scene.render.resolution_x = scene.render.resolution_y = 512
    for tag, off in (("front", Vector((0, -0.6, 0.02))),
                     ("side", Vector((0.6, 0, 0.02)))):
        cam.location = target + off
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(PREVIEW_DIR, f"{meta['id']}_{tag}.png")
        bpy.ops.render.render(write_still=True)
    for b in bpy.data.objects:
        if b.type == 'MESH':
            b.hide_render = True
print(f"[render] previews -> {PREVIEW_DIR}")

# ------------------------------------------------- 5. catalog + item.json
with open(os.path.join(SHARED_DIR, "catalog.json")) as f:
    catalog = json.load(f)
new_ids = {meta["id"] for _, meta in built}
items = [it for it in catalog["items"] if it["id"] not in new_ids]
last_hair = max((i for i, it in enumerate(items)
                 if it["category_dir"] == "hair"), default=-1)
for k, (_, meta) in enumerate(built):
    items.insert(last_hair + 1 + k, meta)
catalog["items"] = items
with open(os.path.join(SHARED_DIR, "catalog.json"), "w") as f:
    json.dump(catalog, f, indent=2)

for _, meta in built:
    item_dir = os.path.join(SHARED_DIR, "hair", meta["id"])
    with open(os.path.join(item_dir, "item.json"), "w") as f:
        json.dump(meta, f, indent=2)
    sb = os.path.join(SANDBOX_DIR, "hair", meta["id"])
    if os.path.isdir(sb):
        shutil.rmtree(sb)
    shutil.copytree(item_dir, sb)
shutil.copy2(os.path.join(SHARED_DIR, "catalog.json"),
             os.path.join(SANDBOX_DIR, "catalog.json"))
print(f"[done] {len(built)} hairstyles integrated")
