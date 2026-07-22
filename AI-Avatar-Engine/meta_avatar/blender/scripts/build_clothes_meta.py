"""
Meta-native clothing/shoe shell generator (Phase 3, T4).

Same technique as blender/scripts/build_demo_assets.py's TOP/PANTS/SHOES
section (shells extracted from the body mesh itself via skinning-weight +
geometric masks, offset along normals, solidified — so the shell keeps the
body's own vertex groups/armature and is perfectly fitted/weighted for
free), but:
  - parameterized for the META templates (MetaMale_Body/MetaFemale_Body etc,
    not the hardcoded realistic Male_Body/Male_Armature), so the shell is cut
    from the TOON-proportioned mesh the avatar will actually wear it on —
    this is what guarantees the fit regardless of how the toon body's
    proportions differ from the realistic body (masks are landmark-driven,
    recomputed from whichever body is currently loaded).
  - restricted to only the clothing/shoe items owned by T4 (hoodie, tshirt,
    jacket, jeans, shorts, sneakers) — hair/beard/eyebrows/glasses/hats/
    accessories are T3's (hair-assets) responsibility, not touched here.
  - non-destructive: writes ONLY new "<id>_meta.glb" files (never overwrites
    the existing realistic "<id>.glb"), and only ADDS a "styles.meta" block
    to the matching item.json / catalog.json entries (schema owned by
    hair-assets, relayed via orchestrator: item.json gains an optional
    `"styles": {"meta": {"glb": "<path>"}}` block read by WardrobeManager at
    equip time; hair-assets patches wardrobe.js, not us) — every other field
    and every other item is left untouched. No directory is ever deleted.

Usage:
  blender --background --python build_clothes_meta.py -- \
      <meta_template.blend> <Prefix> <meta_assets_dir> <assets_shared_dir> \
      <sandbox_wardrobe_dir> [item_ids_csv]

  <Prefix>          MetaMale | MetaFemale
  <meta_assets_dir> meta_avatar/assets  -- canonical per-style authoring
                    output lands under <meta_assets_dir>/clothes_meta/<id>/
                    and <meta_assets_dir>/shoes_meta/<id>/ (never overwrites
                    the realistic demo assets in assets/shared)
  item_ids_csv      default "hoodie,tshirt,jacket,jeans,shorts,sneakers"
                    (subset of items to (re)generate, e.g. "hoodie,jeans" for
                    a targeted rebuild after a fit-test showed clipping)

Writes, per item:
  <meta_assets_dir>/<category_dir>_meta/<id>/<id>_meta.glb   (source of truth)
  <assets_shared_dir>/<category_dir>/<id>/<id>_meta.glb       (served copy)
  <sandbox_wardrobe_dir>/<category_dir>/<id>/<id>_meta.glb    (served copy)
and adds (never replacing "file" / other keys):
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
                "hoodie,tshirt,jacket,jeans,shorts,sneakers").split(","))

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


def flat_material(name, hexcolor, roughness=0.65, metallic=0.0):
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


# ---------------------------------------------------------------- masks
# Same weight-region definitions as build_demo_assets.py TOPS/PANTS/SHOES --
# re-evaluated against the meta body's own vertex groups/coordinates.
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
shoe_w = vg_weights(["CC_Base_L_Foot", "CC_Base_R_Foot",
    "CC_Base_L_ToeBase", "CC_Base_R_ToeBase",
    "CC_Base_L_ToeBaseShareBone", "CC_Base_R_ToeBaseShareBone"]) + \
    vg_weights([g for g in vg_index if "Toe1" in g])

SPECS = {
    "tshirt": dict(mask=((torso_w + hip_w * 0.45 > 0.35) |
                   ((upper_arm_w > 0.35) & (np.abs(X) < 32))) & (neck_w < 0.35),
                   offset=0.7, thickness=0.8, color="#e8e8ea",
                   label="T-Shirt", slot="top"),
    "hoodie": dict(mask=((torso_w + hip_w * 0.5 > 0.3) |
                   (upper_arm_w > 0.25) | (lower_arm_w > 0.25)) & (neck_w < 0.5),
                   offset=1.4, thickness=1.5, color="#3d5a99",
                   label="Hoodie", slot="top"),
    "jeans": dict(mask=((hip_w > 0.3) | (leg_w > 0.3)) & (foot_w < 0.4) & (Z > ANKLE_Z + 1),
                  offset=0.6, thickness=0.8, color="#3a4a6b",
                  label="Jeans", slot="pants"),
    "sneakers": dict(mask=(shoe_w > 0.3) & (Z < ANKLE_Z + 4),
                      offset=0.8, thickness=1.0, color="#e8e8ea",
                      label="Sneakers", slot="shoes"),
}
# jacket/shorts depend on the hoodie/jeans masks above (excerpt from
# build_demo_assets.py) -- compute lazily so the base mask is only built once
hoodie_mask = SPECS["hoodie"]["mask"]
SPECS["jacket"] = dict(
    mask=hoodie_mask & ~((np.abs(X) < 1.3) & (Y < -5) & (Z < 148) & (Z > 105)),
    offset=1.1, thickness=1.3, color="#2c2c34", label="Jacket", slot="top")
jeans_mask = SPECS["jeans"]["mask"]
SPECS["shorts"] = dict(mask=jeans_mask & (Z > KNEE_Z - 2), offset=0.7,
                        thickness=0.9, color="#6b6f78", label="Shorts", slot="pants")

CATEGORY_DIR = {"tshirt": "clothes", "hoodie": "clothes", "jacket": "clothes",
                "jeans": "clothes", "shorts": "clothes", "sneakers": "shoes"}

# ================================================================ BUILD
built = []  # (obj, item_id)
for item_id in ITEM_IDS:
    if item_id not in SPECS:
        print(f"[build-clothes-meta] skip unknown item id '{item_id}'")
        continue
    spec = SPECS[item_id]
    obj = make_shell(f"{item_id}_meta", spec["mask"], spec["offset"],
                      spec["thickness"], spec["color"])
    built.append((obj, item_id, spec))

# ================================================================ EXPORT
def merge_styles(item_json_path, item_id, rel_glb):
    """Add/update styles.meta.glb on one item.json, preserving every other key."""
    if not os.path.isfile(item_json_path):
        print(f"[build-clothes-meta] WARNING: missing {item_json_path}, skipping merge")
        return
    with open(item_json_path) as f:
        data = json.load(f)
    data.setdefault("styles", {})
    data["styles"]["meta"] = {"glb": rel_glb}
    with open(item_json_path, "w") as f:
        json.dump(data, f, indent=2)


def merge_catalog(catalog_path, item_id, rel_glb):
    if not os.path.isfile(catalog_path):
        print(f"[build-clothes-meta] WARNING: missing {catalog_path}, skipping merge")
        return
    with open(catalog_path) as f:
        cat = json.load(f)
    hit = next((it for it in cat.get("items", []) if it.get("id") == item_id), None)
    if hit is None:
        print(f"[build-clothes-meta] WARNING: '{item_id}' not found in {catalog_path}")
        return
    hit.setdefault("styles", {})
    hit["styles"]["meta"] = {"glb": rel_glb}
    with open(catalog_path, "w") as f:
        json.dump(cat, f, indent=2)


print(f"\nBuilt {len(built)} meta clothing shells. Exporting...")
for obj, item_id, spec in built:
    category_dir = CATEGORY_DIR[item_id]
    meta_category_dir = f"{category_dir}_meta"          # clothes_meta | shoes_meta
    rel_glb = f"{category_dir}/{item_id}/{item_id}_meta.glb"   # path served from wardrobe root

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

    # 2) served copies, next to the existing realistic default GLB, so
    #    wardrobe.js can actually fetch `wardrobe/<rel_glb>` at runtime
    for base_dir in (SHARED_DIR, SANDBOX_DIR):
        out_dir = os.path.join(base_dir, category_dir, item_id)
        os.makedirs(out_dir, exist_ok=True)
        shutil.copyfile(meta_glb, os.path.join(base_dir, rel_glb))

    merge_styles(os.path.join(SHARED_DIR, category_dir, item_id, "item.json"), item_id, rel_glb)
    merge_styles(os.path.join(SANDBOX_DIR, category_dir, item_id, "item.json"), item_id, rel_glb)
    merge_catalog(os.path.join(SHARED_DIR, "catalog.json"), item_id, rel_glb)
    merge_catalog(os.path.join(SANDBOX_DIR, "catalog.json"), item_id, rel_glb)

print(f"\nDone. {len(built)} meta variant(s):")
print(f"  authoring source -> {META_ASSETS_DIR}/<clothes_meta|shoes_meta>/<id>/<id>_meta.glb")
print(f"  served copies     -> {SHARED_DIR} and {SANDBOX_DIR}")
