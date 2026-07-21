"""
Real-photo validation harness: pipeline -> Blender render -> metrics -> sheets.

Everything before this was validated on CG renders; this runs the full
photo->avatar loop on REAL photos and scores the result so a human (and
the offline eval loop) can judge identity preservation.

Input layout (documented contract):
    ai/photo_analyzer/input/<set_name>/front.(jpg|jpeg|png|webp|heic)
                                       [left.*] [right.*]     (optional)
    A loose front.* directly in input/ is treated as a set named "default".

For each set, writes to ai/photo_analyzer/output/validation/<set_name>/:
    avatar_parameters.json / identity_paste.json  - pipeline outputs
    debug/                                        - pipeline stage images
    avatar_front.png / avatar_three_quarter.png   - Blender renders
    side_by_side.png                              - photo|render sheet
    report.md                                     - params + metrics
plus output/validation/summary.md across all sets.

Metrics per set (each degrades to n/a if its model is unavailable):
    identity_similarity - ArcFace cosine, aligned front photo vs
                          avatar_front.png (>0.5 = strong same-person
                          signal when one side is a CG render)
    shape3d_mm          - MICA mean vertex distance between the two
                          reconstructions (same face ~0.9mm, different
                          people ~4.9mm)
    recovered params    - how far the solve moved from neutral 0.5

Run with the venv python:
    ai/.venv/Scripts/python.exe validate_real.py
        [--input DIR] [--out DIR] [--skip-render] [--sets name1,name2]

Rendering calls Blender headless with
blender/scripts/render_avatar_params.py (built in parallel — a missing
script is reported, never fatal). Console output is ASCII-only: the
Windows cp1252 console crashes on anything else.
"""
import argparse
import json
import os
import subprocess
import sys
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import analyze_photos, FrontPhotoError
import preprocessing
from processors.face_landmarks import FaceMeasurer
from processors import face_parsing
from processors.identity_embedding import IdentityEmbedder
from processors.face3d import Face3D
from processors.face3d_measure import Face3DMeasurer

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(os.path.dirname(HERE))   # AI-Avatar-Engine/
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
RENDER_SCRIPT = os.path.join(ENGINE_ROOT, "blender", "scripts",
                             "render_avatar_params.py")
IMG_EXTS = ("jpg", "jpeg", "png", "webp", "heic")


# ---------------------------------------------------------------- discovery

def _find_photo(dirpath, stem):
    """dirpath/stem.<ext> for the first extension that exists, else None."""
    for ext in IMG_EXTS:
        p = os.path.join(dirpath, f"{stem}.{ext}")
        if os.path.isfile(p):
            return p
    return None


def discover_sets(input_dir):
    """Scan the input layout -> ordered {set_name: {front, left, right}}.
    Sets without a front photo are skipped with a console note."""
    sets = {}
    if not os.path.isdir(input_dir):
        return sets
    loose = _find_photo(input_dir, "front")
    if loose:
        sets["default"] = {"front": loose,
                           "left": _find_photo(input_dir, "left"),
                           "right": _find_photo(input_dir, "right")}
    for name in sorted(os.listdir(input_dir)):
        d = os.path.join(input_dir, name)
        if not os.path.isdir(d):
            continue
        front = _find_photo(d, "front")
        if front is None:
            print(f"[skip] {name}: no front.* photo")
            continue
        sets[name] = {"front": front, "left": _find_photo(d, "left"),
                      "right": _find_photo(d, "right")}
    return sets


# ---------------------------------------------------------------- rendering

def render_avatar(paste_path, set_out, gender):
    """Headless Blender render of the solved avatar. Returns a report dict
    {ok, why?}; never raises — a broken render must not kill the run."""
    if not os.path.isfile(RENDER_SCRIPT):
        return {"ok": False, "why": "render_avatar_params.py not present "
                                    "yet (being built in parallel)"}
    if not os.path.isfile(BLENDER):
        return {"ok": False, "why": f"Blender not found at {BLENDER}"}
    cmd = [BLENDER, "--background", "--python", RENDER_SCRIPT, "--",
           paste_path, set_out, gender]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=300, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "Blender render timed out (300s)"}
    except OSError as e:
        return {"ok": False, "why": f"could not launch Blender: {e}"}
    front = os.path.join(set_out, "avatar_front.png")
    if p.returncode != 0 or not os.path.isfile(front):
        tail = "\n".join(((p.stderr or "") + "\n" +
                          (p.stdout or "")).strip().splitlines()[-8:])
        return {"ok": False,
                "why": f"Blender exited {p.returncode}, "
                       f"avatar_front.png {'missing' if not os.path.isfile(front) else 'ok'}",
                "log_tail": tail}
    return {"ok": True}


# ------------------------------------------------------------------ metrics

def photo_face(fm, path):
    """Detect + align one image for metric use.
    Returns (aligned_rgb, det) or (None, reason)."""
    try:
        meas, qc, x = preprocessing.analyze_photo(fm, path)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if x.get("det") is None or x.get("aligned_rgb") is None:
        return None, qc.get("reason", "no face detected")
    return (x["aligned_rgb"], x["det"]), None


def compute_metrics(models, photo_fd, render_png):
    """ArcFace similarity + MICA vertex distance between the front photo
    and the avatar render. Every sub-metric is independently graceful."""
    m = {"identity_similarity": None, "shape3d_mm": None, "notes": []}
    fm, ie, f3d = models["fm"], models["ie"], models["f3d"]
    if photo_fd is None:
        m["notes"].append("front photo face unavailable for metrics")
        return m
    if not os.path.isfile(render_png):
        m["notes"].append("avatar_front.png missing - render metrics n/a")
        return m
    render_fd, why = photo_face(fm, render_png)
    if render_fd is None:
        m["notes"].append(f"no face detected on avatar render ({why})")
        return m

    if ie.available:
        sim = ie.similarity(ie.embed(*photo_fd), ie.embed(*render_fd))
        if sim is None:
            m["notes"].append("ArcFace alignment failed on one side")
        else:
            m["identity_similarity"] = round(sim, 3)
    else:
        m["notes"].append(f"ArcFace unavailable ({ie.why})")

    if f3d.available:
        ra = f3d.reconstruct(*photo_fd)
        rb = f3d.reconstruct(*render_fd)
        if ra is None or rb is None:
            m["notes"].append("MICA reconstruction failed on one side")
        else:  # both meshes are canonical FLAME neutral -> direct distance
            d = np.linalg.norm(ra["verts"] - rb["verts"], axis=1)
            m["shape3d_mm"] = round(float(d.mean()) * 1000.0, 2)
    else:
        m["notes"].append(f"MICA unavailable ({f3d.why})")
    return m


def param_deviations(engine_params, face_meta):
    """(count of params moved off neutral 0.5, top-5 largest deviations
    with their solver confidence + source)."""
    devs = sorted(((abs(v - 0.5), k, v) for k, v in engine_params.items()),
                  reverse=True)
    moved = sum(1 for d, _, _ in devs if d > 1e-3)
    top = [{"param": k, "value": round(v, 3), "dev": round(d, 3),
            "confidence": (face_meta.get(k) or {}).get("confidence"),
            "source": (face_meta.get(k) or {}).get("source")}
           for d, k, v in devs[:5]]
    return moved, top


# ---------------------------------------------------------------- rendering (sheet)

def _tile(img_or_path, height=512):
    """-> PIL image resized to the target height (aspect kept), or a gray
    placeholder captioned with why it is missing."""
    from PIL import Image, ImageDraw
    img = None
    if isinstance(img_or_path, np.ndarray):
        img = Image.fromarray(img_or_path)
    elif img_or_path and os.path.isfile(img_or_path):
        try:
            img = Image.open(img_or_path).convert("RGB")
        except Exception:
            img = None
    if img is None:
        ph = Image.new("RGB", (height, height), (60, 60, 60))
        ImageDraw.Draw(ph).text((height // 2 - 40, height // 2),
                                "(missing)", fill=(200, 200, 200))
        return ph
    w = max(1, round(img.width * height / img.height))
    return img.resize((w, height), Image.LANCZOS)


def compose_sheet(out_png, photo_rgb, avatar_front, avatar_tq, caption):
    """side_by_side.png: [aligned photo | front render | 3/4 render] with a
    caption strip. Best-effort; returns True on success."""
    try:
        from PIL import Image, ImageDraw
        tiles = [_tile(photo_rgb), _tile(avatar_front), _tile(avatar_tq)]
        pad, strip = 8, 44
        w = sum(t.width for t in tiles) + pad * (len(tiles) + 1)
        h = 512 + strip + pad * 2
        sheet = Image.new("RGB", (w, h), (25, 25, 28))
        x = pad
        for t in tiles:
            sheet.paste(t, (x, pad))
            x += t.width + pad
        ImageDraw.Draw(sheet).text((pad + 4, 512 + pad + 14), caption,
                                   fill=(235, 235, 235))
        sheet.save(out_png)
        return True
    except Exception as e:
        print(f"[warn] side_by_side failed: {e}")
        return False


# ------------------------------------------------------------------ reports

def _fmt(v, suffix=""):
    return "n/a" if v is None else f"{v}{suffix}"


def write_report(set_out, rec, engine_params, face_meta, warnings):
    """Per-set report.md: metrics, top deviations, full params table."""
    lines = [f"# Validation: {rec['set']}", "",
             f"- gender: **{rec['gender']}**",
             f"- identity_similarity: **{_fmt(rec['identity_similarity'])}**"
             " (ArcFace cosine, photo vs avatar_front render)",
             f"- shape3d_mm: **{_fmt(rec['shape3d_mm'])}**"
             " (MICA mean vertex distance; ~1mm excellent, >5mm poor)",
             f"- params moved off neutral: **{_fmt(rec['params_moved'])}"
             f" / {len(engine_params) if engine_params else 0}**", ""]
    if rec.get("render") and not rec["render"].get("ok"):
        lines += [f"- render: SKIPPED/FAILED - {rec['render'].get('why')}", ""]
        if rec["render"].get("log_tail"):
            lines += ["```", rec["render"]["log_tail"], "```", ""]
    if rec.get("error"):
        lines += [f"- pipeline error: `{rec['error']}`", ""]
    if warnings:
        lines += ["## Warnings", ""] + [f"- {w}" for w in warnings] + [""]
    if rec.get("metric_notes"):
        lines += ["## Metric notes", ""] + \
                 [f"- {n}" for n in rec["metric_notes"]] + [""]
    if rec.get("top_devs"):
        lines += ["## Largest deviations from neutral", "",
                  "| param | value | dev | confidence | source |",
                  "|---|---|---|---|---|"]
        lines += [f"| {d['param']} | {d['value']} | {d['dev']} | "
                  f"{_fmt(d['confidence'])} | {_fmt(d['source'])} |"
                  for d in rec["top_devs"]] + [""]
    if engine_params:
        lines += ["## All parameters", "",
                  "| param | value | confidence | source |", "|---|---|---|---|"]
        for k in sorted(engine_params):
            fmk = face_meta.get(k) or {}
            lines.append(f"| {k} | {round(engine_params[k], 3)} | "
                         f"{_fmt(fmk.get('confidence'))} | "
                         f"{_fmt(fmk.get('source'))} |")
        lines.append("")
    lines += ["## Images", "", "![side by side](side_by_side.png)", "",
              "Renders: [avatar_front.png](avatar_front.png) - "
              "[avatar_three_quarter.png](avatar_three_quarter.png) - "
              "debug stages in [debug/](debug/)", ""]
    with open(os.path.join(set_out, "report.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_summary(out_root, records):
    lines = ["# Real-photo validation summary", "",
             "| set | gender | identity_similarity | shape3d_mm | warnings |",
             "|---|---|---|---|---|"]
    for r in records:
        lines.append(f"| [{r['set']}]({r['set']}/report.md) | "
                     f"{_fmt(r['gender'])} | "
                     f"{_fmt(r['identity_similarity'])} | "
                     f"{_fmt(r['shape3d_mm'])} | {r['n_warnings']} |")
    lines += ["",
              "**Reading the metrics** - `identity_similarity` is the ArcFace "
              "cosine between the real photo and the CG avatar render; the "
              "photo->render domain gap depresses it, so >0.5 is a strong "
              "same-person signal, 0.3-0.5 promising, <0.2 weak. "
              "`shape3d_mm` is the MICA mean vertex distance between the two "
              "reconstructions: ~1mm is excellent (same-face reference is "
              "0.9mm), 2-4mm partial identity capture, >5mm poor (different-"
              "people reference is 4.9mm). Neither metric replaces looking "
              "at side_by_side.png - they rank sets, a human judges them.", ""]
    with open(os.path.join(out_root, "summary.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))


# --------------------------------------------------------------------- main

def process_set(name, paths, out_root, models, skip_render):
    """Full loop for one photo set. Never raises: one bad set is recorded
    and the run continues."""
    set_out = os.path.join(out_root, name)
    os.makedirs(set_out, exist_ok=True)
    rec = {"set": name, "gender": None, "identity_similarity": None,
           "shape3d_mm": None, "params_moved": None, "top_devs": None,
           "n_warnings": 0, "render": None, "metric_notes": [], "error": None}
    engine_params, face_meta, warnings = {}, {}, []

    print(f"[set] {name}: analyzing {os.path.basename(paths['front'])}"
          + ("" if not paths.get("left") else " + profiles"))
    try:
        result, raw, engine_params, warnings = analyze_photos(
            paths["front"], paths.get("left"), paths.get("right"),
            fm=models["fm"], fp=models["fp"], ie=models["ie"],
            f3d=models["f3d"], m3d=models["m3d"],
            debug_dir=os.path.join(set_out, "debug"))
    except (FrontPhotoError, Exception) as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        if not isinstance(e, FrontPhotoError):
            traceback.print_exc()
        write_report(set_out, rec, engine_params, face_meta, warnings)
        return rec
    face_meta = raw.get("face_meta") or {}
    rec["gender"] = result.get("gender")
    rec["n_warnings"] = len(warnings)
    rec["params_moved"], rec["top_devs"] = \
        param_deviations(engine_params, face_meta)

    # same dump contract as pipeline.py main()
    with open(os.path.join(set_out, "avatar_parameters.json"), "w") as f:
        json.dump(result, f, indent=2)
    paste_path = os.path.join(set_out, "identity_paste.json")
    with open(paste_path, "w") as f:
        json.dump(engine_params, f, indent=2)

    gender = rec["gender"] or "male"
    if skip_render:
        rec["render"] = {"ok": False, "why": "render skipped (--skip-render)"}
    else:
        print(f"[set] {name}: rendering avatar ({gender})")
        rec["render"] = render_avatar(paste_path, set_out, gender)
    if not rec["render"]["ok"]:
        print(f"[set] {name}: no render - {rec['render']['why']}")

    # metrics need the photo's aligned face regardless of the render (the
    # sheet uses it too)
    photo_fd, why = photo_face(models["fm"], paths["front"])
    if photo_fd is None:
        rec["metric_notes"].append(f"front photo metric face failed: {why}")
    front_png = os.path.join(set_out, "avatar_front.png")
    tq_png = os.path.join(set_out, "avatar_three_quarter.png")
    m = compute_metrics(models, photo_fd, front_png)
    rec["identity_similarity"] = m["identity_similarity"]
    rec["shape3d_mm"] = m["shape3d_mm"]
    rec["metric_notes"] += m["notes"]

    caption = (f"{name}   identity_similarity={_fmt(rec['identity_similarity'])}"
               f"   shape3d={_fmt(rec['shape3d_mm'], ' mm')}   gender={gender}")
    compose_sheet(os.path.join(set_out, "side_by_side.png"),
                  photo_fd[0] if photo_fd else None, front_png, tq_png,
                  caption)
    write_report(set_out, rec, engine_params, face_meta, warnings)
    print(f"[set] {name}: identity_similarity="
          f"{_fmt(rec['identity_similarity'])} "
          f"shape3d={_fmt(rec['shape3d_mm'], 'mm')} "
          f"params_moved={rec['params_moved']}")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--input", default=os.path.join(HERE, "input"))
    ap.add_argument("--out",
                    default=os.path.join(HERE, "output", "validation"))
    ap.add_argument("--skip-render", action="store_true",
                    help="skip the Blender render (render metrics -> n/a)")
    ap.add_argument("--sets", default=None,
                    help="comma-separated subset of set names to run")
    args = ap.parse_args()

    sets = discover_sets(args.input)
    if args.sets:
        want = [s.strip() for s in args.sets.split(",") if s.strip()]
        missing = [s for s in want if s not in sets]
        if missing:
            print(f"[warn] not found in {args.input}: {', '.join(missing)}")
        sets = {k: v for k, v in sets.items() if k in want}
    if not sets:
        sys.exit(f"no photo sets found under {args.input} "
                 "(expected input/<set>/front.jpg|png|... )")

    print(f"[validate] {len(sets)} set(s): {', '.join(sets)}")
    # load every model once, share across sets (same trick as server.py)
    models = {"fm": FaceMeasurer(), "fp": face_parsing.FaceParser(),
              "ie": IdentityEmbedder(), "f3d": Face3D(),
              "m3d": Face3DMeasurer()}
    for key, label in (("fp", "face parsing"), ("ie", "ArcFace"),
                       ("f3d", "MICA")):
        if not models[key].available:
            print(f"[warn] {label} unavailable ({models[key].why})")

    os.makedirs(args.out, exist_ok=True)
    records = [process_set(name, paths, args.out, models,
                           args.skip_render)
               for name, paths in sets.items()]
    models["fm"].close()

    write_summary(args.out, records)
    print(f"[validate] summary -> {os.path.join(args.out, 'summary.md')}")


if __name__ == "__main__":
    main()
