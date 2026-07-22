"""
Automated regression test for a Meta avatar template. This is the Phase-3
regression gate: run it on both meta_male.blend and meta_female.blend after
ANY change to the meta templates or morph-generation scripts.

Checks (fail loudly, collect ALL failures, exit nonzero if any):
  1. Armature: 101 bones, all named CC_Base_*, spot-check CC_Base_Head /
     CC_Base_JawRoot / CC_Base_NeckTwist02.
  2. Body identity keys: the 20 shape keys referenced by
     blender/scripts/morph_definitions.json targets, plus the meta-only
     head_size / body_weight keys — all with slider_min=-1, slider_max=1.
  3. ARKit 52/52 coverage, reusing (not duplicating) the ARKIT_TO_CC table
     from blender/scripts/inspect_asset.py.
  4. Cross-mesh follower contract: every mesh has head_size; the eye/tearline/
     occlusion meshes have eye_size + eye_distance; Toon_Eyebrows has >=8
     identity follower keys; CC_Toon_Teeth_01 / CC_Base_Tongue have >=8
     mouth-region follower keys including the jaw/chin/lip core.
  5. Extremes smoke test: every identity key driven to +1 then -1 (via
     key.value, on every mesh that carries it — the real cross-mesh usage
     pattern) must produce finite vertex positions with max per-vertex
     displacement under 25cm.
  6. Render smoke: one 512px front render at neutral and one with
     head_size=1 (camera pattern from render_meta_look.py) for manual visual
     review (mouth must stay closed, no exploded geometry).

Read-only against the template: never saves the .blend.

Usage:
  blender --background --python test_meta_templates.py -- \
      <template.blend> <Prefix> <out_report.json>

Templates / prefixes:
  meta_avatar/blender/base/meta_male.blend    MetaMale
  meta_avatar/blender/base/meta_female.blend  MetaFemale
"""
import bpy
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.normpath(os.path.join(HERE, "..", "..", "..", "blender", "scripts"))
sys.path.insert(0, SHARED)
from inspect_asset import ARKIT_TO_CC  # noqa: E402  (reuse, do not duplicate)

with open(os.path.join(SHARED, "morph_definitions.json")) as _f:
    _DEFS = json.load(_f)
CUSTOM_KEYS = sorted({t["shape_key"] for p in _DEFS["params"].values()
                      for t in p["targets"]})               # the 20 AI-contract keys
EXTRA_BODY_KEYS = ["head_size", "body_weight"]               # meta-only, on the body

MOUTH_FOLLOW_CORE = {"jaw_height", "jaw_width", "chin_size", "lip_thickness"}
MIN_FOLLOWER_COUNT = 8

OBJ_NAMES = {
    "eye": "CC_Base_Eye",
    "tearline": "CC_Base_TearLine",
    "occlusion": "CC_Base_EyeOcclusion",
    "tongue": "CC_Base_Tongue",
    "teeth": "CC_Toon_Teeth_01",
    "eyebrows": "Toon_Eyebrows",
}

MAX_DISPLACEMENT_CM = 25.0
RENDER_RES = 512


class Failures(list):
    def add(self, msg):
        self.append(msg)
        print(f"[FAIL] {msg}")


# --------------------------------------------------------------------------- 1
def check_bones(arm_obj, fails):
    names = [b.name for b in arm_obj.data.bones]
    count = len(names)
    if count != 101:
        fails.add(f"bone count {count} != 101")
    non_prefixed = [n for n in names if not n.startswith("CC_Base_")]
    if non_prefixed:
        fails.add(f"{len(non_prefixed)} bones not prefixed CC_Base_*: {non_prefixed[:5]}")
    for spot in ("CC_Base_Head", "CC_Base_JawRoot", "CC_Base_NeckTwist02"):
        if spot not in names:
            fails.add(f"missing spot-check bone {spot}")
    return {"bone_count": count, "non_prefixed": non_prefixed}


# --------------------------------------------------------------------------- 2
def check_identity_keys(body_obj, fails):
    ks = body_obj.data.shape_keys
    key_blocks = ks.key_blocks if ks else {}
    report = {}
    for name in CUSTOM_KEYS + EXTRA_BODY_KEYS:
        kb = key_blocks.get(name)
        if kb is None:
            fails.add(f"body missing identity key '{name}'")
            continue
        if abs(kb.slider_min - (-1.0)) > 1e-6 or abs(kb.slider_max - 1.0) > 1e-6:
            fails.add(f"body key '{name}' slider range ({kb.slider_min},{kb.slider_max}) != (-1,1)")
        report[name] = {"min": kb.slider_min, "max": kb.slider_max}
    return report


# --------------------------------------------------------------------------- 3
def check_arkit(body_obj, tongue_obj, fails):
    available = set()
    for obj in (body_obj, tongue_obj):
        if obj is not None and obj.data.shape_keys:
            available |= {kb.name for kb in obj.data.shape_keys.key_blocks}
    ok, missing = {}, {}
    for arkit_name, cc_keys in ARKIT_TO_CC.items():
        absent = [k for k in cc_keys if k not in available]
        if absent:
            missing[arkit_name] = absent
        else:
            ok[arkit_name] = cc_keys
    if len(ok) != len(ARKIT_TO_CC):
        fails.add(f"ARKit coverage {len(ok)}/{len(ARKIT_TO_CC)} != full; missing={missing}")
    return {"supported": len(ok), "total": len(ARKIT_TO_CC), "missing": missing}


# --------------------------------------------------------------------------- 4
def check_followers(objs, fails):
    report = {}

    # every mesh has head_size
    for label, obj in objs.items():
        kbs = obj.data.shape_keys.key_blocks if obj.data.shape_keys else {}
        has = "head_size" in kbs
        report.setdefault(obj.name, {})["head_size"] = has
        if not has:
            fails.add(f"{obj.name} missing head_size follower")

    # eye / tearline / occlusion: eye_size + eye_distance
    for label in ("eye", "tearline", "occlusion"):
        obj = objs[label]
        kbs = obj.data.shape_keys.key_blocks if obj.data.shape_keys else {}
        for key in ("eye_size", "eye_distance"):
            present = key in kbs
            report[obj.name][key] = present
            if not present:
                fails.add(f"{obj.name} missing {key} follower")

    # eyebrows: >=8 identity follower keys
    brow = objs["eyebrows"]
    brow_keys = {kb.name for kb in brow.data.shape_keys.key_blocks} if brow.data.shape_keys else set()
    brow_follow = sorted(brow_keys & set(CUSTOM_KEYS))
    report[brow.name]["identity_follower_count"] = len(brow_follow)
    report[brow.name]["identity_followers"] = brow_follow
    if len(brow_follow) < MIN_FOLLOWER_COUNT:
        fails.add(f"{brow.name} has only {len(brow_follow)} identity follower keys "
                  f"(need >={MIN_FOLLOWER_COUNT}): {brow_follow}")

    # teeth / tongue: mouth-region follower keys
    for label in ("teeth", "tongue"):
        obj = objs[label]
        keys = {kb.name for kb in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else set()
        follow = sorted(keys & set(CUSTOM_KEYS))
        report[obj.name]["mouth_follower_count"] = len(follow)
        report[obj.name]["mouth_followers"] = follow
        missing_core = MOUTH_FOLLOW_CORE - set(follow)
        if missing_core:
            fails.add(f"{obj.name} missing core mouth-follower keys: {sorted(missing_core)}")
        if len(follow) < MIN_FOLLOWER_COUNT:
            fails.add(f"{obj.name} has only {len(follow)} mouth-region follower keys "
                      f"(need >={MIN_FOLLOWER_COUNT})")

    return report


# --------------------------------------------------------------------------- 5
def _basis_positions(obj):
    mesh = obj.data
    n = len(mesh.vertices)
    kb = mesh.shape_keys.key_blocks[0]  # Basis
    co = np.zeros(n * 3, dtype=np.float64)
    kb.data.foreach_get("co", co)
    return co.reshape(n, 3)


def check_extremes(objs, fails):
    report = {}
    keys_to_test = CUSTOM_KEYS + EXTRA_BODY_KEYS
    basis_cache = {label: _basis_positions(obj) for label, obj in objs.items()}
    depsgraph = bpy.context.evaluated_depsgraph_get()

    for key_name in keys_to_test:
        meshes_with_key = [(label, obj) for label, obj in objs.items()
                           if obj.data.shape_keys and key_name in obj.data.shape_keys.key_blocks]
        if not meshes_with_key:
            continue
        key_report = {}
        for extreme in (1.0, -1.0):
            for label, obj in meshes_with_key:
                obj.data.shape_keys.key_blocks[key_name].value = extreme
            depsgraph.update()
            for label, obj in meshes_with_key:
                eval_obj = obj.evaluated_get(depsgraph)
                eval_mesh = eval_obj.to_mesh()
                n = len(eval_mesh.vertices)
                co = np.zeros(n * 3, dtype=np.float64)
                eval_mesh.vertices.foreach_get("co", co)
                eval_obj.to_mesh_clear()
                co = co.reshape(n, 3)
                basis = basis_cache[label]
                if co.shape[0] != basis.shape[0]:
                    fails.add(f"{obj.name}/{key_name}={extreme:+.0f}: vertex count changed "
                              f"({co.shape[0]} vs {basis.shape[0]})")
                    continue
                if not np.all(np.isfinite(co)):
                    fails.add(f"{obj.name}/{key_name}={extreme:+.0f}: NaN/Inf in evaluated vertices")
                    continue
                disp = float(np.linalg.norm(co - basis, axis=1).max())
                prev = key_report.get(label, {}).get("max_displacement_cm", 0.0)
                key_report.setdefault(label, {})["max_displacement_cm"] = round(max(prev, disp), 3)
                if disp >= MAX_DISPLACEMENT_CM:
                    fails.add(f"{obj.name}/{key_name}={extreme:+.0f}: max displacement "
                              f"{disp:.2f}cm >= {MAX_DISPLACEMENT_CM}cm")
            for label, obj in meshes_with_key:
                obj.data.shape_keys.key_blocks[key_name].value = 0.0
        report[key_name] = key_report
    return report


# --------------------------------------------------------------------------- 6
def render_smoke(prefix, out_dir, fails):
    arm = bpy.data.objects[f"{prefix}_Armature"]

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = RENDER_RES
    world = bpy.data.worlds.new("TestW")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.58, 1)
    scene.world = world

    cam_data = bpy.data.cameras.new("TestCam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("TestCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    key = bpy.data.lights.new("TestKey", 'SUN')
    key.energy = 3.0
    ko = bpy.data.objects.new("TestKey", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(60), 0, math.radians(15))
    fill = bpy.data.lights.new("TestFill", 'SUN')
    fill.energy = 1.5
    fo = bpy.data.objects.new("TestFill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(75), 0, math.radians(195))

    head = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
    target = Vector((0, head.y, head.z + 0.075))
    cam.location = target + Vector((0, -0.85, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

    os.makedirs(out_dir, exist_ok=True)
    renders = {}

    def render_to(tag):
        path = os.path.join(out_dir, f"{prefix}_{tag}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        renders[tag] = path

    render_to("neutral_front")

    hits = 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        kb = obj.data.shape_keys.key_blocks.get("head_size")
        if kb is not None:
            kb.value = 1.0
            hits += 1
    print(f"[render] head_size=1 applied to {hits} meshes")
    render_to("head_size1_front")

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.data.shape_keys:
            continue
        kb = obj.data.shape_keys.key_blocks.get("head_size")
        if kb is not None:
            kb.value = 0.0

    for tag, path in renders.items():
        if not os.path.isfile(path) or os.path.getsize(path) < 1024:
            fails.add(f"render '{tag}' missing or suspiciously small: {path}")

    return renders


# --------------------------------------------------------------------------- main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 3:
        raise SystemExit(
            "usage: blender --background --python test_meta_templates.py -- "
            "<template.blend> <Prefix> <out_report.json>")
    template_path, prefix, out_report = os.path.abspath(argv[0]), argv[1], os.path.abspath(argv[2])

    fails = Failures()
    bpy.ops.wm.open_mainfile(filepath=template_path)

    arm = bpy.data.objects.get(f"{prefix}_Armature")
    body = bpy.data.objects.get(f"{prefix}_Body")
    if arm is None:
        fails.add(f"armature '{prefix}_Armature' not found")
    if body is None:
        fails.add(f"body '{prefix}_Body' not found")

    objs = {}
    if body is not None:
        objs["body"] = body
    for label, name in OBJ_NAMES.items():
        o = bpy.data.objects.get(name)
        if o is None:
            fails.add(f"object '{name}' not found")
        else:
            objs[label] = o

    report = {"template": template_path, "prefix": prefix}

    if arm is not None:
        report["bones"] = check_bones(arm, fails)
        head_world = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
        report["head_world_position"] = [round(v, 4) for v in head_world]

    if body is not None:
        report["identity_keys"] = check_identity_keys(body, fails)
        report["arkit"] = check_arkit(body, objs.get("tongue"), fails)

    if len(objs) == 7:   # body + the 6 named cross-mesh objects
        report["followers"] = check_followers(objs, fails)
        report["extremes"] = check_extremes(objs, fails)
    else:
        fails.add(f"skipping follower/extremes checks: only {len(objs)}/7 required objects present")

    if arm is not None and body is not None:
        out_dir = os.path.join(os.path.dirname(out_report), "test_renders")
        report["renders"] = render_smoke(prefix, out_dir, fails)

    report["failures"] = list(fails)
    report["status"] = "PASS" if not fails else "FAIL"

    os.makedirs(os.path.dirname(out_report), exist_ok=True)
    with open(out_report, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== {prefix}: {report['status']} ({len(fails)} failure(s)) ===")
    for msg in fails:
        print(" -", msg)
    print(f"Report written to {out_report}")

    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
