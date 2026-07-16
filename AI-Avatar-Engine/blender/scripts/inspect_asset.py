"""
Asset inspection tool for the AI-Avatar-Engine template files.

Dumps a complete machine-readable inventory of a template .blend:
meshes, bones, materials, textures, UV maps, shape keys — plus an
ARKit-52 compatibility check against the embedded mapping table.

Usage:
  blender --background --python inspect_asset.py -- <template.blend> <out_report.json>
"""
import bpy
import json
import sys

# ---------------------------------------------------------------------------
# ARKit 52 -> CC4 Extended blendshape mapping.
# Most targets are 1:1; a few ARKit shapes are composites of two or four
# CC keys (each listed entry is driven at weight 1.0 unless noted).
# ---------------------------------------------------------------------------
ARKIT_TO_CC = {
    # --- Eyes (14) ---
    "eyeBlinkLeft":       ["Eye_Blink_L"],
    "eyeLookDownLeft":    ["Eye_L_Look_Down"],
    "eyeLookInLeft":      ["Eye_L_Look_R"],   # "in" = toward nose
    "eyeLookOutLeft":     ["Eye_L_Look_L"],
    "eyeLookUpLeft":      ["Eye_L_Look_Up"],
    "eyeSquintLeft":      ["Eye_Squint_L"],
    "eyeWideLeft":        ["Eye_Wide_L"],
    "eyeBlinkRight":      ["Eye_Blink_R"],
    "eyeLookDownRight":   ["Eye_R_Look_Down"],
    "eyeLookInRight":     ["Eye_R_Look_L"],
    "eyeLookOutRight":    ["Eye_R_Look_R"],
    "eyeLookUpRight":     ["Eye_R_Look_Up"],
    "eyeSquintRight":     ["Eye_Squint_R"],
    "eyeWideRight":       ["Eye_Wide_R"],
    # --- Jaw (4) ---
    "jawForward":         ["Jaw_Forward"],
    "jawLeft":            ["Jaw_L"],
    "jawRight":           ["Jaw_R"],
    "jawOpen":            ["Jaw_Open"],
    # --- Mouth (23) ---
    "mouthClose":         ["Mouth_Close"],
    "mouthFunnel":        ["Mouth_Funnel_Up_L", "Mouth_Funnel_Up_R",
                           "Mouth_Funnel_Down_L", "Mouth_Funnel_Down_R"],
    "mouthPucker":        ["Mouth_Pucker_Up_L", "Mouth_Pucker_Up_R",
                           "Mouth_Pucker_Down_L", "Mouth_Pucker_Down_R"],
    "mouthLeft":          ["Mouth_L"],
    "mouthRight":         ["Mouth_R"],
    "mouthSmileLeft":     ["Mouth_Smile_L"],
    "mouthSmileRight":    ["Mouth_Smile_R"],
    "mouthFrownLeft":     ["Mouth_Frown_L"],
    "mouthFrownRight":    ["Mouth_Frown_R"],
    "mouthDimpleLeft":    ["Mouth_Dimple_L"],
    "mouthDimpleRight":   ["Mouth_Dimple_R"],
    "mouthStretchLeft":   ["Mouth_Stretch_L"],
    "mouthStretchRight":  ["Mouth_Stretch_R"],
    "mouthRollLower":     ["Mouth_Roll_In_Lower_L", "Mouth_Roll_In_Lower_R"],
    "mouthRollUpper":     ["Mouth_Roll_In_Upper_L", "Mouth_Roll_In_Upper_R"],
    "mouthShrugLower":    ["Mouth_Shrug_Lower"],
    "mouthShrugUpper":    ["Mouth_Shrug_Upper"],
    "mouthPressLeft":     ["Mouth_Press_L"],
    "mouthPressRight":    ["Mouth_Press_R"],
    "mouthLowerDownLeft": ["Mouth_Down_Lower_L"],
    "mouthLowerDownRight":["Mouth_Down_Lower_R"],
    "mouthUpperUpLeft":   ["Mouth_Up_Upper_L"],
    "mouthUpperUpRight":  ["Mouth_Up_Upper_R"],
    # --- Brows (5) ---
    "browDownLeft":       ["Brow_Drop_L"],
    "browDownRight":      ["Brow_Drop_R"],
    "browInnerUp":        ["Brow_Raise_Inner_L", "Brow_Raise_Inner_R"],
    "browOuterUpLeft":    ["Brow_Raise_Outer_L"],
    "browOuterUpRight":   ["Brow_Raise_Outer_R"],
    # --- Cheeks (3) ---
    "cheekPuff":          ["Cheek_Puff_L", "Cheek_Puff_R"],
    "cheekSquintLeft":    ["Cheek_Raise_L"],
    "cheekSquintRight":   ["Cheek_Raise_R"],
    # --- Nose (2) ---
    "noseSneerLeft":      ["Nose_Sneer_L"],
    "noseSneerRight":     ["Nose_Sneer_R"],
    # --- Tongue (1) ---
    "tongueOut":          ["Tongue_Out"],
}

# Our generated user-customization morphs (identity, not expression).
CUSTOMIZATION_MORPHS = [
    "face_width", "jaw_width", "jaw_height", "chin_size", "nose_width",
    "nose_length", "eye_size", "eye_distance", "lip_thickness", "mouth_width",
    "cheek_size", "forehead_height", "eyebrow_height", "eye_tilt",
    "nose_bridge_height", "nose_tip_size", "ear_size", "jaw_angle",
    "cheekbone_height", "philtrum_length",
]


def classify_shape_key(name):
    """Classify a shape key by purpose."""
    if name == "Basis":
        return "basis"
    if name in CUSTOMIZATION_MORPHS:
        return "customization"
    if name.startswith("V_"):
        return "viseme"
    if name.startswith(("TL ", "EO ")):
        return "utility_depth_tuning"   # tearline / eye-occlusion fitting shapes
    if name.startswith(("Head_", "Neck_")):
        return "corrective"             # fired alongside bone rotations
    if name.startswith("Eyelash_"):
        return "secondary_animation"
    return "expression"                 # ARKit-style facial animation


def inspect(blend_path, out_path):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    report = {"file": blend_path, "objects": [], "armatures": [],
              "materials": {}, "arkit": {}, "shape_key_classification": {}}

    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            bones = []
            for b in obj.data.bones:
                bones.append({
                    "name": b.name,
                    "parent": b.parent.name if b.parent else None,
                    "head": [round(v, 3) for v in b.head_local],
                    "use_deform": b.use_deform,
                })
            report["armatures"].append({"name": obj.name, "bone_count": len(bones), "bones": bones})

        elif obj.type == 'MESH':
            mesh = obj.data
            entry = {
                "name": obj.name,
                "data_name": mesh.name,
                "vertices": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "uv_maps": [uv.name for uv in mesh.uv_layers],
                "vertex_groups": len(obj.vertex_groups),
                "modifiers": [m.type for m in obj.modifiers],
                "materials": [s.material.name if s.material else None for s in obj.material_slots],
                "shape_keys": [],
            }
            if mesh.shape_keys:
                for kb in mesh.shape_keys.key_blocks:
                    entry["shape_keys"].append({
                        "name": kb.name,
                        "min": kb.slider_min, "max": kb.slider_max,
                        "class": classify_shape_key(kb.name),
                    })
            report["objects"].append(entry)

            for slot in obj.material_slots:
                mat = slot.material
                if mat is None or mat.name in report["materials"]:
                    continue
                textures = []
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            textures.append({
                                "image": node.image.name,
                                "size": list(node.image.size),
                                "packed": node.image.packed_file is not None,
                                "filepath": node.image.filepath,
                            })
                report["materials"][mat.name] = {"textures": textures}

    # ARKit compatibility: check every mapped CC key exists on the body mesh
    body = next((o for o in report["objects"] if "Body" in o["name"]), None)
    tongue = next((o for o in report["objects"] if "Tongue" in o["data_name"]), None)
    available = set()
    for src in (body, tongue):
        if src:
            available |= {k["name"] for k in src["shape_keys"]}

    ok, missing = {}, {}
    for arkit_name, cc_keys in ARKIT_TO_CC.items():
        absent = [k for k in cc_keys if k not in available]
        if absent:
            missing[arkit_name] = absent
        else:
            ok[arkit_name] = cc_keys
    report["arkit"] = {
        "supported": len(ok), "total": len(ARKIT_TO_CC),
        "mapping_ok": ok, "missing": missing,
    }

    # classification tally
    tally = {}
    if body:
        for k in body["shape_keys"]:
            tally.setdefault(k["class"], []).append(k["name"])
    report["shape_key_classification"] = {c: {"count": len(v), "keys": v} for c, v in tally.items()}

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nARKit compatibility: {report['arkit']['supported']}/{len(ARKIT_TO_CC)} supported")
    if missing:
        print("Missing:", json.dumps(missing, indent=2))
    print("\nShape key classes (body):")
    for c, v in report["shape_key_classification"].items():
        print(f"  {c}: {v['count']}")
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    inspect(argv[0], argv[1])
