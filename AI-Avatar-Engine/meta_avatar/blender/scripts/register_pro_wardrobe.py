"""
Register the pro wardrobe builds (build_pro_wardrobe.py output) in
assets/shared/catalog.json + per-item item.json, and sync the sandbox copy.

Existing catalog ids get their "styles.meta" variant replaced by the new
meta-native GLB (offsets/scales dropped — the new geometry is authored
in-place on the meta bases). New ids get full entries (style: "meta").

Plain python (no bpy):  python register_pro_wardrobe.py <repo_root>
"""
import json
import os
import shutil
import sys

ROOT = os.path.abspath(sys.argv[1])
ENG = os.path.join(ROOT, "AI-Avatar-Engine")
SHARED = os.path.join(ENG, "assets", "shared")
SANDBOX = os.path.join(ENG, "frontend", "threejs-viewer", "public", "wardrobe")
OUT = os.path.join(ENG, "output", "wardrobe_pro")

with open(os.path.join(OUT, "build_report.json")) as f:
    report = json.load(f)

# id -> (label, slot, category_dir, attach_type, colorable, existing_id)
META = {
    "tshirt":        ("T-Shirt", "top", "clothes", "skinned", True, True),
    "shirt_short":   ("Short Sleeve Shirt", "top", "clothes", "skinned", True, False),
    "shirt_long":    ("Long Sleeve Shirt", "top", "clothes", "skinned", True, False),
    "hoodie":        ("Hoodie", "top", "clothes", "skinned", True, True),
    "sweater":       ("Sweater", "top", "clothes", "skinned", True, False),
    "suit_jacket":   ("Suit Jacket", "top", "clothes", "skinned", True, False),
    "jeans":         ("Jeans", "pants", "clothes", "skinned", True, True),
    "pants_casual":  ("Casual Pants", "pants", "clothes", "skinned", True, False),
    "suit_pants":    ("Suit Pants", "pants", "clothes", "skinned", True, False),
    "shorts":        ("Shorts", "pants", "clothes", "skinned", True, True),
    "sneakers":      ("Sneakers", "shoes", "shoes", "skinned", True, True),
    "boots":         ("Boots", "shoes", "shoes", "skinned", True, False),
    "dress_shoes":   ("Dress Shoes", "shoes", "shoes", "skinned", False, False),
    "dress":         ("Dress", "top", "clothes", "skinned", True, False),
    "hijab":         ("Hijab", "hat", "hats", "skinned", True, False),
    "scarf":         ("Scarf", "neck", "accessories", "skinned", True, False),
    "cap":           ("Cap", "hat", "hats", "bone", True, True),
    "beanie":        ("Beanie", "hat", "hats", "bone", True, True),
    "glasses_round": ("Round Glasses", "glasses", "glasses", "bone", False, True),
    "glasses_square": ("Square Glasses", "glasses", "glasses", "bone", False, True),
}

cat_path = os.path.join(SHARED, "catalog.json")
with open(cat_path) as f:
    catalog = json.load(f)
by_id = {it["id"]: it for it in catalog["items"]}

for gid, rep in report.items():
    if gid not in META:
        print(f"[skip] {gid} not in META table")
        continue
    label, slot, cat, attach, colorable, existing = META[gid]
    glb_rel = rep["glb"].replace("\\", "/")
    item_dir = os.path.join(SHARED, cat, gid)
    os.makedirs(item_dir, exist_ok=True)
    # thumbnail from the persp QA render
    persp = os.path.join(OUT, gid, f"{gid}_persp.png")
    thumb = os.path.join(item_dir, "thumbnail.png")
    if os.path.isfile(persp) and (existing is False or True):
        shutil.copy2(persp, thumb)

    if existing and gid in by_id:
        it = by_id[gid]
        it["styles"] = it.get("styles", {})
        it["styles"]["meta"] = {"glb": glb_rel}    # native fit: no offset/scale
        if rep.get("morph_followers"):
            it["styles"]["meta"]["morphs"] = rep["morph_followers"]
    else:
        it = {
            "id": gid, "label": label, "slot": slot, "category_dir": cat,
            "attach_type": attach,
            "attach_to": "CC_Base_Head" if attach == "bone" else None,
            "colorable_materials": [f"{gid}_mat"] if colorable else [],
            "gender": rep.get("gender", "male"), "style": "meta",
            "source": "build_pro_wardrobe.py (procedural, meta-native)",
            "file": glb_rel,
            "thumb": f"{cat}/{gid}/thumbnail.png",
            "styles": {"meta": {"glb": glb_rel}},
        }
        if rep.get("morph_followers"):
            it["styles"]["meta"]["morphs"] = rep["morph_followers"]
        if gid in by_id:
            by_id[gid].update(it)
            it = by_id[gid]
        else:
            items = catalog["items"]
            anchor = max((i for i, x in enumerate(items)
                          if x["category_dir"] == cat), default=len(items) - 1)
            items.insert(anchor + 1, it)
            by_id[gid] = it
    # item.json
    with open(os.path.join(item_dir, "item.json"), "w") as f:
        json.dump(it, f, indent=2)
    print(f"[cat] {gid}: {'meta variant' if existing else 'new item'} -> {glb_rel}")

with open(cat_path, "w") as f:
    json.dump(catalog, f, indent=2)

# sandbox sync: copy each touched item dir + catalog
for gid, rep in report.items():
    if gid not in META:
        continue
    cat = META[gid][2]
    src = os.path.join(SHARED, cat, gid)
    dst = os.path.join(SANDBOX, cat, gid)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
shutil.copy2(cat_path, os.path.join(SANDBOX, "catalog.json"))
print(f"[done] {len(report)} items registered + sandbox synced")
