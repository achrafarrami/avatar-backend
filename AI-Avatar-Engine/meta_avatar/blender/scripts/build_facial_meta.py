"""
Meta-native beard/eyebrow shell generator (fixes D6: beard/eyebrow shells in
the demo library are cut from the REALISTIC body and reused unmodified on
the Meta/toon skeleton via attach_type "skinned" bone-name rebind. That only
re-binds the mesh's motion to the toon bones -- the shell's REST GEOMETRY
still has the realistic head's proportions, so on the toon head (bigger
eyes, different brow ridge/jaw shape) eyebrows land on the eyeballs and the
beard mask only catches two disconnected wisps near the jaw corners. The
catalog "styles.meta.offset/scale" post-hoc nudge on beard_short does
nothing for skinned items -- attachSkinned() bakes bindMatrix/boneInverses
from the ORIGINAL asset at bind time; runtime translation of the holder is a
verified no-op).

Same technique as build_clothes_meta.py (which fixed the analogous problem
for clothes_meta/shoes_meta): shells are cut directly from the TOON body's
own vertex coordinates via skinning-weight + expression-derived geometric
masks (same recipe as build_demo_assets.py's BEARDS/EYEBROWS section), so
the shell is perfectly fitted to whatever body it's extracted from -- no
offset/scale hack needed afterward.

Usage:
  blender --background --python build_facial_meta.py -- \
      <meta_template.blend> <Prefix> <meta_assets_dir> <assets_shared_dir> \
      <sandbox_wardrobe_dir> [item_ids_csv]

  <Prefix>          MetaMale | MetaFemale
  <meta_assets_dir> meta_avatar/assets -- canonical per-style authoring
                    output lands under <meta_assets_dir>/<category>_meta/<id>/
  item_ids_csv      default "beard_short,goatee,eyebrows_natural,eyebrows_thick"

Writes, per item:
  <meta_assets_dir>/<category_dir>_meta/<id>/<id>_meta.glb   (source of truth)
  <assets_shared_dir>/<category_dir>/<id>/<id>_meta.glb       (served copy)
  <sandbox_wardrobe_dir>/<category_dir>/<id>/<id>_meta.glb    (served copy)
and adds/replaces (never touching "file" / other keys):
  "styles": {"meta": {"glb": "<category_dir>/<id>/<id>_meta.glb"}}
to:
  <assets_shared_dir>/<category_dir>/<id>/item.json
  <sandbox_wardrobe_dir>/<category_dir>/<id>/item.json
  <assets_shared_dir>/catalog.json            (matching "items" entry)
  <sandbox_wardrobe_dir>/catalog.json         (matching "items" entry)
"""
import bpy
import bmesh
import json
import os
import shutil
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE = argv[0]
PREFIX = argv[1]
META_ASSETS_DIR = os.path.abspath(argv[2])
SHARED_DIR = os.path.abspath(argv[3])
SANDBOX_DIR = os.path.abspath(argv[4])
ITEM_IDS = set((argv[5] if len(argv) > 5 else
                "beard_short,goatee,eyebrows_natural,eyebrows_thick").split(","))

BODY_NAME, ARM_NAME = f"{PREFIX}_Body", f"{PREFIX}_Armature"

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(TEMPLATE))
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

vg_index = {g.name: g.index for g in body.vertex_groups}


def vg_weights(names):
    idx = {vg_index[nm] for nm in names if nm in vg_index}
    w = np.zeros(n)
    for v in mesh.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w


# expression-derived region magnitudes -- same trick as build_demo_assets.py
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


def flat_material(name, hexcolor, roughness=0.9, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    c = tuple(int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def make_shell(item_id, mask, offset, thickness, color):
    """Duplicate the (meta) body, keep only masked verts, offset along
    normals, solidify. Result keeps vertex groups + armature modifier =
    skinned, perfectly fitted to whichever body is currently loaded."""
    obj = body.copy()
    obj.data = body.data.copy()
    obj.name = item_id
    bpy.context.scene.collection.objects.link(obj)
    obj.shape_key_clear()
    me = obj.data

    new_co = co + normals * offset
    me.vertices.foreach_set("co", new_co.reshape(-1).astype(np.float32))

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    doomed = [v for v in bm.verts if mask[v.index] < 0.5]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    # cutting islands out of the body leaves some faces wound inward —
    # they render as pale flipped-normal chunks after solidify
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
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
    for p in me.polygons:   # flat facets read as pale broken chunks
        p.use_smooth = True
    return obj


# ---------------------------------------------------------------- masks
# Same region definitions as build_demo_assets.py's BEARDS/EYEBROWS section,
# re-evaluated against the meta body's own vertex groups/coordinates/keys.
HAIR = "#3b2a1e"
beard_full = (head_w > 0.3) & (Y < -1.0) & (Z > MOUTH_Z - 4.5) & (
    (Z < MOUTH_Z - 0.8) |
    ((np.abs(X) > 2.8) & (Z < MOUTH_Z + 1.2)) |
    ((Z > MOUTH_Z + 0.55) & (Z < MOUTH_Z + 1.3) & (np.abs(X) < 3.2))  # mustache, ABOVE the lip line (0.3 sat on the lip and hid the mouth)
)
goatee_mask = beard_full & (np.abs(X) < 2.6)

brow_region = (brow_mag > 0.72) & (normals[:, 1] < -0.45) & \
              (np.abs(Z - BROW_Z) < 1.3) & (np.abs(X) > 1.2) & (np.abs(X) < 6.0)

SPECS = {
    "beard_short": dict(mask=beard_full, offset=0.45, thickness=0.55, color=HAIR,
                         label="Short Beard", slot="beard"),
    "goatee": dict(mask=goatee_mask, offset=0.5, thickness=0.6, color=HAIR,
                    label="Goatee", slot="beard"),
    "eyebrows_natural": dict(mask=brow_region, offset=0.10, thickness=0.22,
                              color="#2f2318", label="Natural", slot="eyebrows"),
    "eyebrows_thick": dict(mask=brow_region, offset=0.2, thickness=0.38,
                            color="#2f2318", label="Thick", slot="eyebrows"),
}
CATEGORY_DIR = {"beard_short": "beards", "goatee": "beards",
                "eyebrows_natural": "eyebrows", "eyebrows_thick": "eyebrows"}

# ================================================================ BUILD
built = []  # (obj, item_id, spec)
for item_id in ITEM_IDS:
    if item_id not in SPECS:
        print(f"[build-facial-meta] skip unknown item id '{item_id}'")
        continue
    spec = SPECS[item_id]
    obj = make_shell(f"{item_id}_meta", spec["mask"], spec["offset"],
                      spec["thickness"], spec["color"])
    built.append((obj, item_id, spec))
    print(f"[build-facial-meta] {item_id}: {len(obj.data.vertices)} verts")

# ================================================================ EXPORT
def merge_styles(item_json_path, item_id, rel_glb):
    """Add/replace styles.meta on one item.json, preserving every other key."""
    if not os.path.isfile(item_json_path):
        print(f"[build-facial-meta] WARNING: missing {item_json_path}, skipping merge")
        return
    with open(item_json_path) as f:
        data = json.load(f)
    data.setdefault("styles", {})
    data["styles"]["meta"] = {"glb": rel_glb}
    with open(item_json_path, "w") as f:
        json.dump(data, f, indent=2)


def merge_catalog(catalog_path, item_id, rel_glb):
    if not os.path.isfile(catalog_path):
        print(f"[build-facial-meta] WARNING: missing {catalog_path}, skipping merge")
        return
    with open(catalog_path) as f:
        cat = json.load(f)
    hit = next((it for it in cat.get("items", []) if it.get("id") == item_id), None)
    if hit is None:
        print(f"[build-facial-meta] WARNING: '{item_id}' not found in {catalog_path}")
        return
    hit.setdefault("styles", {})
    hit["styles"]["meta"] = {"glb": rel_glb}
    with open(catalog_path, "w") as f:
        json.dump(cat, f, indent=2)


print(f"\nBuilt {len(built)} meta facial shells. Exporting...")
for obj, item_id, spec in built:
    category_dir = CATEGORY_DIR[item_id]
    meta_category_dir = f"{category_dir}_meta"  # beards_meta | eyebrows_meta
    rel_glb = f"{category_dir}/{item_id}/{item_id}_meta.glb"

    # 1) canonical authoring output under meta_avatar/assets/<cat>_meta/<id>/
    meta_out_dir = os.path.join(META_ASSETS_DIR, meta_category_dir, item_id)
    os.makedirs(meta_out_dir, exist_ok=True)
    meta_glb = os.path.join(meta_out_dir, f"{item_id}_meta.glb")

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=meta_glb, export_format='GLB',
        use_selection=True, export_skins=True, export_morph=False,
        export_animations=False, export_yup=True)
    size = os.path.getsize(meta_glb) / 1e6
    print(f"  {item_id}_meta  {size:5.1f} MB -> {meta_glb}")

    # 2) served copies, next to the existing realistic default GLB
    for base_dir in (SHARED_DIR, SANDBOX_DIR):
        out_dir = os.path.join(base_dir, category_dir, item_id)
        os.makedirs(out_dir, exist_ok=True)
        shutil.copyfile(meta_glb, os.path.join(base_dir, rel_glb))

    merge_styles(os.path.join(SHARED_DIR, category_dir, item_id, "item.json"), item_id, rel_glb)
    merge_styles(os.path.join(SANDBOX_DIR, category_dir, item_id, "item.json"), item_id, rel_glb)
    merge_catalog(os.path.join(SHARED_DIR, "catalog.json"), item_id, rel_glb)
    merge_catalog(os.path.join(SANDBOX_DIR, "catalog.json"), item_id, rel_glb)

print(f"\nDone. {len(built)} meta variant(s):")
print(f"  authoring source -> {META_ASSETS_DIR}/<beards_meta|eyebrows_meta>/<id>/<id>_meta.glb")
print(f"  served copies     -> {SHARED_DIR} and {SANDBOX_DIR}")
