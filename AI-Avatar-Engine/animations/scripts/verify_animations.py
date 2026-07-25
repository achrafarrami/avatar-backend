"""Verify an exported animated GLB by re-importing it into a clean scene.

Asserts:
  - every expected clip exists as a named animation (NLA track on import)
  - durations match the master's metadata within tolerance
  - NO identity morph targets shipped
  - reports whether bone-scale animation survived the round trip

Usage:
  blender --background --python verify_animations.py -- <avatar.glb>
      [--expect '<json: {cid: seconds, ...}>'] [--master <path.blend>]

Without --expect, expectations are read from the master's stored clip
metadata (scene['anim_clips']).
"""
import bpy
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework.rig import IDENTITY_KEYS             # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_MASTER = os.path.join(ANIM_ROOT, "blender",
                              "anim_master_meta_male.blend")


def expectations_from_master(master):
    bpy.ops.wm.open_mainfile(filepath=master)
    meta = json.loads(bpy.context.scene.get("anim_clips", "{}"))
    return {cid: m["seconds"] for cid, m in meta.items()}


def preview_expectations(previews_dir):
    """Per-clip {frame_count, fps, seconds} read from previews/<cid>/meta.json
    (an independent cross-check on the master's stored seconds)."""
    out = {}
    if not os.path.isdir(previews_dir):
        return out
    for cid in os.listdir(previews_dir):
        mpath = os.path.join(previews_dir, cid, "meta.json")
        if not os.path.isfile(mpath):
            continue
        try:
            with open(mpath) as f:
                m = json.load(f)
        except (OSError, ValueError):
            continue
        fc, fp = m.get("frame_count"), m.get("fps")
        sec = (fc / fp) if (fc and fp) else m.get("duration_s")
        out[cid] = {"frame_count": fc, "fps": fp, "seconds": sec}
    return out


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    glb, expect, master = None, None, DEFAULT_MASTER
    report_path = None
    previews_dir = os.path.join(ANIM_ROOT, "previews")
    i = 0
    while i < len(argv):
        if argv[i] == "--expect":
            expect = json.loads(argv[i + 1]); i += 2
        elif argv[i] == "--master":
            master = argv[i + 1]; i += 2
        elif argv[i] == "--report":
            report_path = argv[i + 1]; i += 2
        elif argv[i] == "--previews":
            previews_dir = argv[i + 1]; i += 2
        else:
            glb = argv[i]; i += 1
    if not glb:
        raise SystemExit("Usage: ... -- <avatar.glb> [--expect json] "
                         "[--report path] [--previews dir]")

    prev = preview_expectations(previews_dir)
    if expect is None:
        expect = expectations_from_master(master)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base

    print(f"\n=== ANIMATION VERIFICATION: {os.path.basename(glb)} ===")
    print(f"scene fps after import: {fps}")

    # collect animations: NLA track names -> frame spans (importer puts each
    # glTF animation on its own track per object)
    spans = {}
    datablocks = []
    for obj in scene.objects:
        datablocks.append(obj)
        if obj.type == 'MESH' and obj.data.shape_keys:
            datablocks.append(obj.data.shape_keys)
    for db in datablocks:
        adt = getattr(db, "animation_data", None)
        if not adt:
            continue
        for t in adt.nla_tracks:
            for s in t.strips:
                lo, hi = spans.get(t.name, (1e9, -1e9))
                spans[t.name] = (min(lo, s.frame_start), max(hi, s.frame_end))

    failures, notes, rows = [], [], []
    for cid, seconds in sorted(expect.items()):
        pv = prev.get(cid, {})
        pv_sec = pv.get("seconds")
        if cid not in spans:
            failures.append(f"MISSING animation '{cid}' "
                            f"(found: {sorted(spans)})")
            rows.append({"cid": cid, "present": False, "dur": None,
                         "expected": seconds, "preview": pv_sec, "ok": False})
            continue
        lo, hi = spans[cid]
        dur = (hi - lo) / fps
        ok = abs(dur - seconds) <= max(2.5 / fps, seconds * 0.02)
        pv_ok = (pv_sec is None or
                 abs(dur - pv_sec) <= max(2.5 / fps, pv_sec * 0.02))
        line = (f"  {cid}: frames {lo:.0f}-{hi:.0f} -> {dur:.3f}s "
                f"(expected {seconds:.3f}s) {'OK' if ok else 'FAIL'}"
                + ("" if pv_ok else f"  PREVIEW MISMATCH ({pv_sec:.3f}s)"))
        print(line)
        rows.append({"cid": cid, "present": True, "dur": dur,
                     "expected": seconds, "preview": pv_sec,
                     "frame_count": pv.get("frame_count"), "ok": ok and pv_ok})
        if not ok:
            failures.append(line.strip())
        if not pv_ok:
            failures.append(f"{cid}: GLB {dur:.3f}s vs preview "
                            f"meta.json {pv_sec:.3f}s")

    # identity keys must not ship
    shipped_identity = []
    n_targets = {}
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.data.shape_keys:
            names = [kb.name for kb in obj.data.shape_keys.key_blocks[1:]]
            n_targets[obj.name] = len(names)
            shipped_identity += [f"{obj.name}.{n}" for n in names
                                 if n in IDENTITY_KEYS]
    print(f"morph target counts: {n_targets}")
    if shipped_identity:
        failures.append(f"IDENTITY KEYS SHIPPED: {shipped_identity}")
    else:
        print("identity keys shipped: none  OK")

    # scale-channel round trip (report, not assert)
    scale_curves = 0
    for act in bpy.data.actions:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        if fc.data_path.endswith(".scale"):
                            vals = [kp.co[1] for kp in fc.keyframe_points]
                            if vals and (max(vals) - min(vals)) > 1e-4:
                                scale_curves += 1
    notes.append(f"bone-scale fcurves with variation after reimport: "
                 f"{scale_curves} "
                 f"({'scale animation SURVIVES' if scale_curves else 'scale animation NOT preserved'})")
    for n in notes:
        print("NOTE:", n)

    # ---- optional report file -----------------------------------------
    if report_path:
        body = next((o for o in scene.objects if o.type == 'MESH'
                     and o.data.shape_keys and o.name.endswith("_Body")), None)
        body_keys = n_targets.get(body.name) if body else None
        rep = []
        rep.append(f"Animation verify report — {os.path.basename(glb)}")
        rep.append("=" * 60)
        rep.append(f"GLB: {glb}")
        rep.append(f"GLB size: {os.path.getsize(glb) / 1e6:.1f} MB")
        rep.append(f"scene fps after import: {fps:g}")
        rep.append(f"expected clips: {len(expect)}   "
                   f"animations found in GLB: {len(spans)}")
        present = sum(1 for r in rows if r["present"])
        rep.append(f"present: {present}   "
                   f"missing: {len(expect) - present}")
        rep.append(f"morph-target counts per mesh: {n_targets}")
        if body_keys is not None:
            rep.append(f"body ({body.name}) animation shape keys: {body_keys}")
        rep.append("identity keys shipped: "
                   + ("NONE (OK)" if not shipped_identity
                      else f"SHIPPED {shipped_identity}"))
        rep.append(notes[-1] if notes else "")
        rep.append("")
        rep.append(f"{'clip':32} {'present':8} {'glb_s':>8} "
                   f"{'master_s':>9} {'preview_s':>10} {'frames':>7} result")
        rep.append("-" * 90)
        for r in sorted(rows, key=lambda x: x["cid"]):
            dur = f"{r['dur']:.3f}" if r["dur"] is not None else "-"
            pvs = f"{r['preview']:.3f}" if r.get("preview") else "-"
            fc = r.get("frame_count")
            rep.append(f"{r['cid']:32} {str(r['present']):8} {dur:>8} "
                       f"{r['expected']:>9.3f} {pvs:>10} "
                       f"{(fc if fc else '-'):>7} "
                       f"{'OK' if r['ok'] else 'FAIL'}")
        rep.append("")
        rep.append("RESULT: " + ("PASS" if not failures
                                 else f"FAIL ({len(failures)} issue(s))"))
        if failures:
            rep.append("issues:")
            rep += [f"  - {f}" for f in failures]
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w") as f:
            f.write("\n".join(rep) + "\n")
        print(f"REPORT: {report_path}")

    if failures:
        print("\nVERIFY FAILED:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"\nVERIFY PASSED: {len(expect)} animations OK in {glb}")


if __name__ == "__main__":
    main()
