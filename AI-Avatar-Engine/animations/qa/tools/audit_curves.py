"""QA curve-level audit (rubric automated pre-pass) — headless Blender.

Usage:
  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background \
      <master.blend> --python audit_curves.py -- <out.json> <clip_id> [<clip_id> ...]

Read-only: opens the blend, inspects actions + drivers, writes a JSON report.
Never saves the blend. Checks per clip action(s):
  - interpolation modes per channel (linear on bone rotation = rubric fast-reject)
  - loop seam: first/last key value diff + in/out tangent slope diff per channel
  - L/R pair curves (Eye_Blink, Brow_*, Mouth_Smile, Cheek, Eye_Squint):
    identical frames+values detection (fast-reject) and max value delta
  - forbidden targets: never_animate_keys + twist/share helper bones (rig_reference)
  - shape-key value range violations (outside [0, 1])
  - key frame positions for Eye_Blink_L / Eye_L_Look_Down / Jaw_Open (body)
  - drivers on shape keys (e.g. Eyelash follow wiring) per mesh
"""
import json
import re
import sys
from pathlib import Path

import bpy

QA_DIR = Path(__file__).resolve().parents[1]


def load_rig_reference():
    p = QA_DIR / "rig_reference.json"
    with open(p, "r", encoding="utf-8") as fh:
        rig = json.load(fh)
    twist = set(rig.get("bone_regions", {}).get("twist_helpers", {}).get("bones", []))
    never = set(rig.get("never_animate_keys", []))
    return twist, never


BONE_RE = re.compile(r'pose\.bones\["([^"]+)"\]')
KEY_RE = re.compile(r'key_blocks\["([^"]+)"\]')


def iter_fcurves(act):
    """Blender 5.x layered-action API: yield (slot_name, fcurve)."""
    for layer in act.layers:
        for strip in layer.strips:
            if strip.type != "KEYFRAME":
                continue
            for bag in strip.channelbags:
                slot = next((s for s in act.slots
                             if s.handle == bag.slot_handle), None)
                slot_name = slot.name_display if slot else str(bag.slot_handle)
                for fc in bag.fcurves:
                    yield slot_name, fc


def slope(p1, p2):
    dx = p2[0] - p1[0]
    return (p2[1] - p1[1]) / dx if abs(dx) > 1e-9 else 0.0


def analyze_fcurve(fc):
    kps = fc.keyframe_points
    n = len(kps)
    interp = {}
    for kp in kps:
        interp[kp.interpolation] = interp.get(kp.interpolation, 0) + 1
    first, last = kps[0], kps[n - 1]
    out = {
        "data_path": fc.data_path,
        "array_index": fc.array_index,
        "n_keys": n,
        "interpolation": interp,
        "frame_range": [round(first.co[0], 2), round(last.co[0], 2)],
        "first_value": round(float(first.co[1]), 5),
        "last_value": round(float(last.co[1]), 5),
        "loop_value_diff": round(abs(float(first.co[1]) - float(last.co[1])), 5),
        "value_min": round(min(float(k.co[1]) for k in kps), 4),
        "value_max": round(max(float(k.co[1]) for k in kps), 4),
    }
    if n >= 2:
        s_first = slope(first.co, first.handle_right)
        s_last = slope(last.handle_left, last.co)
        out["loop_tangent_diff"] = round(abs(s_first - s_last), 5)
    return out


def curve_key_series(fc):
    return [(round(float(k.co[0]), 2), round(float(k.co[1]), 5))
            for k in fc.keyframe_points]


def pair_name(key_name):
    if key_name.endswith("_L"):
        return key_name[:-2] + "_R"
    return None


def analyze_action(act, twist_bones, never_keys):
    channels, lr_curves = [], {}
    findings = []
    key_positions = {}
    bone_frames = {}
    for slot_name, fc in iter_fcurves(act):
        if not len(fc.keyframe_points):
            continue
        info = analyze_fcurve(fc)
        info["slot"] = slot_name
        channels.append(info)
        m = BONE_RE.search(fc.data_path)
        k = KEY_RE.search(fc.data_path)
        if m:
            bone = m.group(1)
            if bone in twist_bones:
                findings.append(f"FORBIDDEN BONE: {bone} keyed ({fc.data_path})")
            if "rotation" in fc.data_path and info["interpolation"].get("LINEAR"):
                findings.append(
                    f"LINEAR ROTATION: {bone} {fc.data_path}[{fc.array_index}] "
                    f"has {info['interpolation']['LINEAR']} linear keys")
            bone_frames.setdefault(bone, [round(float(kp.co[0]), 1)
                                          for kp in fc.keyframe_points])
        if k:
            key = k.group(1)
            if key in never_keys:
                findings.append(f"NEVER_ANIMATE KEY: {key} keyed")
            if info["value_min"] < -0.001 or info["value_max"] > 1.001:
                findings.append(
                    f"RANGE: {key} value range [{info['value_min']}, {info['value_max']}]")
            if key.endswith(("_L", "_R")):
                lr_curves.setdefault(key, curve_key_series(fc))
            # capture full key timing for shape keys when THIS action targets the
            # body mesh (per-mesh action name, e.g. "<clip>__MetaMale_Body") or a
            # multi-slot action whose slot is the body; drives Duchenne-order /
            # saccade-ballistics / onset-lag judgments.
            if "MetaMale_Body" in act.name or "MetaMale_Body" in slot_name:
                key_positions.setdefault(key, curve_key_series(fc))
    # L/R identity
    lr_report = {}
    for name, series in lr_curves.items():
        rname = pair_name(name)
        if rname and rname in lr_curves:
            rser = lr_curves[rname]
            same_frames = [f for f, _ in series] == [f for f, _ in rser]
            if same_frames:
                max_dv = max((abs(a[1] - b[1]) for a, b in zip(series, rser)), default=0.0)
            else:
                max_dv = None
            identical = same_frames and max_dv is not None and max_dv < 1e-5
            lr_report[f"{name}/{rname}"] = {
                "same_key_frames": same_frames,
                "max_value_delta": round(max_dv, 5) if max_dv is not None else None,
                "identical": identical,
            }
            if identical:
                findings.append(f"IDENTICAL L/R CURVES: {name} == {rname} (fast-reject "
                                f"if eyelids; asymmetry required elsewhere)")
    # loop seam summary (worst offenders)
    seam = sorted(channels, key=lambda c: -c["loop_value_diff"])[:8]
    seam = [{"ch": f"{c['data_path']}[{c['array_index']}]",
             "value_diff": c["loop_value_diff"],
             "tangent_diff": c.get("loop_tangent_diff")} for c in seam]
    return {
        "action": act.name,
        "frame_range": [round(act.frame_range[0], 1), round(act.frame_range[1], 1)],
        "n_fcurves": len(channels),
        "findings": findings,
        "lr_pairs": lr_report,
        "worst_loop_seams": seam,
        "key_positions": key_positions,
        "bone_frames": bone_frames,
        "channels": channels,
    }


def shape_key_drivers():
    """Which meshes have drivers on shape keys (e.g. Eyelash follow wiring)."""
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data.shape_keys:
            continue
        ad = obj.data.shape_keys.animation_data
        if ad and ad.drivers:
            out[obj.name] = sorted({KEY_RE.search(d.data_path).group(1)
                                    for d in ad.drivers if KEY_RE.search(d.data_path)})
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 2:
        print("usage: ... -- <out.json> <clip_id> [<clip_id> ...]")
        sys.exit(1)
    out_path, clip_ids = Path(argv[0]), argv[1:]
    twist_bones, never_keys = load_rig_reference()

    all_actions = [(a.name, sum(1 for _ in iter_fcurves(a)),
                    [round(a.frame_range[0], 1), round(a.frame_range[1], 1)])
                   for a in bpy.data.actions]
    report = {"blend": bpy.data.filepath, "all_actions": all_actions,
              "shape_key_drivers": shape_key_drivers(), "clips": {}}

    for cid in clip_ids:
        matches = [a for a in bpy.data.actions if cid in a.name]
        if not matches:
            report["clips"][cid] = {"error": f"no action matching '{cid}'"}
            continue
        report["clips"][cid] = [analyze_action(a, twist_bones, never_keys)
                                for a in matches]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nAUDIT written: {out_path}")
    for cid, entries in report["clips"].items():
        if isinstance(entries, dict):
            print(f"  {cid}: {entries['error']}")
            continue
        for e in entries:
            print(f"  {cid} :: {e['action']} fcurves={e['n_fcurves']} "
                  f"range={e['frame_range']} findings={len(e['findings'])}")
            for f in e["findings"]:
                print(f"    ! {f}")


main()
