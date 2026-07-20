"""
Photo → avatar_parameters.json pipeline (Phase A: geometry only).

  python pipeline.py <front> [<left> <right>] [--out output/]

- front photo drives all geometric parameters (profiles are QC'd and their
  measurements recorded in raw_analysis.json for later phases)
- every parameter goes through calibration/calibration.json — the AI layer
  never writes an engine value directly
- outputs: output/raw_analysis.json (debugging) and
           output/avatar_parameters.json (the engine-facing contract)
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from processors.face_landmarks import (FaceMeasurer, render_overlay, L,
                                       MEASUREMENT_INFO, load_image_rgb,
                                       ImageReadError)
from processors.appearance_analyzer import analyze_appearance
from processors import face_parsing
from processors import profile_analyzer
from processors import identity_embedding
from processors.face3d import Face3D
from processors.face3d_measure import Face3DMeasurer
from preprocessing.normalize import normalize as normalize_colors
import preprocessing
import fusion

HERE = os.path.dirname(os.path.abspath(__file__))
CALIB = os.path.join(HERE, "calibration", "calibration.json")

# engine snake_case -> output camelCase (the agreed contract format)
CAMEL = {
    "face_width": "faceWidth", "forehead_height": "foreheadHeight",
    "cheek_size": "cheekSize", "cheekbone_height": "cheekboneHeight",
    "jaw_width": "jawWidth", "jaw_height": "faceLength",
    "jaw_angle": "jawAngle", "chin_size": "chinSize",
    "nose_width": "noseWidth", "nose_length": "noseLength",
    "nose_bridge_height": "noseBridgeHeight", "nose_tip_size": "noseTipSize",
    "eye_size": "eyeSize", "eye_distance": "eyeDistance",
    "eye_tilt": "eyeTilt", "eyebrow_height": "eyebrowHeight",
    "mouth_width": "mouthWidth", "lip_thickness": "lipThickness",
    "philtrum_length": "philtrumLength", "ear_size": "earSize",
}


def _save_face3d_debug(debug_dir, m3d, rec):
    """Front (XY) + side (ZY) orthographic scatter of the MICA mesh with the
    68 landmarks highlighted — proof of what the 3D stage measured."""
    import cv2
    verts, lmk = rec["verts"], rec["lmk68"]
    try:
        canvas = np.full((360, 640, 3), 30, np.uint8)
        # front (X,Y) left half, side (Z,Y) right half; Y up -> invert
        for half, (ax, ay) in ((0, (0, 1)), (320, (2, 1))):
            P = verts[:, [ax, ay]].copy()
            Lp = lmk[:, [ax, ay]].copy()
            allp = np.vstack([P, Lp])
            mn, mx = allp.min(0), allp.max(0)
            sc = 300.0 / max(mx[1] - mn[1], 1e-6)
            def to_px(q):
                x = half + 160 + (q[:, 0] - (mn[0] + mx[0]) / 2) * sc
                y = 30 + (mx[1] - q[:, 1]) * sc
                return np.stack([x, y], 1).astype(int)
            for x, y in to_px(P):
                if 0 <= x < 640 and 0 <= y < 360:
                    canvas[y, x] = (90, 90, 90)
            for x, y in to_px(Lp):
                cv2.circle(canvas, (int(x), int(y)), 2, (0, 220, 255), -1)
        cv2.imwrite(os.path.join(debug_dir, "front_face3d.png"), canvas)
    except Exception as e:
        print(f"[debug] face3d debug image failed: {e}", file=sys.stderr)


def analyze_front_parsing(fp, front_x):
    """Run face parsing on the (color-normalized) front photo and derive
    the fusion inputs: per-measurement occlusion, beard coverage, hairline.
    Returns a dict; {"available": False} when the parser can't run."""
    if fp is None or not fp.available:
        return {"available": False,
                "why": None if fp is None else fp.why}
    det = front_x["det"]
    labels = fp.parse(front_x["normalized_rgb"])
    occ, lm_vis = fp.measurement_occlusion(labels, det, L, MEASUREMENT_INFO)
    beard = fp.beard_analysis(labels, det)
    hl = fp.hairline(labels, det)
    out = {"available": True, "labels": labels, "occlusion": occ,
           "landmark_visibility": lm_vis, "beard_coverage": beard["coverage"],
           "beard_mask": beard["mask"],
           "hairline_y": None if hl is None else hl["y"],
           "hat_fraction": 0.0 if hl is None else hl["hat_fraction"]}
    if hl is not None:
        pts = det["pts"]
        brow_y = 0.5 * (pts[L["brow_r"]][1] + pts[L["brow_l"]][1])
        chin_y = pts[L["chin"]][1]
        if chin_y - brow_y > 1:
            # forehead in facial-thirds terms: hairline->brow over
            # brow->chin. Anchored per-gender by calibrate.py
            # --hairline-renders (renders of the template WEARING hair —
            # bald neutral renders can't provide this one)
            out["forehead_hairline"] = round(
                float((brow_y - hl["y"]) / (chin_y - brow_y)), 4)
    return out


class FrontPhotoError(Exception):
    """Raised when the front photo can't drive the pipeline."""


def _save_debug_images(debug_dir, tag, extras):
    """Write the preprocessing/debug images for one photo (best effort)."""
    if not debug_dir or extras.get("det") is None:
        return
    from PIL import Image as PILImage
    os.makedirs(debug_dir, exist_ok=True)
    try:
        PILImage.fromarray(extras["aligned_rgb"]).save(
            os.path.join(debug_dir, f"{tag}_aligned.jpg"), quality=92)
        PILImage.fromarray(extras["normalized_rgb"]).save(
            os.path.join(debug_dir, f"{tag}_normalized.jpg"), quality=92)
        render_overlay(extras["det"],
                       os.path.join(debug_dir, f"{tag}_landmarks.jpg"))
    except Exception as e:  # debug output must never kill an analysis
        print(f"[debug] could not write {tag} debug images: {e}",
              file=sys.stderr)


def analyze_photos(front, left=None, right=None, with_appearance=True,
                   fm=None, fp=None, ie=None, f3d=None, m3d=None,
                   gender_hint=None, beard_hint=None, debug_dir=None):
    """Shared core for the CLI and the sandbox server.
    Returns (result, raw, engine_params, warnings).
    Pass a FaceMeasurer as `fm` / FaceParser as `fp` to reuse loaded models
    (the server does this). `gender_hint` / `beard_hint` carry the
    detected gender and beard style when appearance analysis is skipped —
    the sandbox runs the VLM as a separate earlier request, and without
    the beard hint the beard-aware down-weighting would silently not fire
    in the sandbox flow. `debug_dir` writes the debug image set."""
    with open(CALIB) as f:
        calib = json.load(f)

    own_fm = fm is None
    if own_fm:
        fm = FaceMeasurer()
    photos, raw, warnings = [], {"photos": {}}, []

    front_meas, front_qc, front_x = preprocessing.analyze_photo(
        fm, front, expect_yaw=0.0)
    raw["photos"]["front"] = {"file": os.path.basename(front),
                              "qc": front_qc, "measurements": front_meas,
                              "quality": front_x["quality"],
                              "align": front_x["align"],
                              "confidence": front_x["confidence"]}
    photos.append(os.path.basename(front))
    if front_meas is None:
        if own_fm:
            fm.close()
        raise FrontPhotoError(f"front photo unusable: {front_qc.get('reason')}")
    if not front_qc["ok"]:
        warnings.append(f"front photo QC: {front_qc.get('reason')} — "
                        "results will be less accurate")
    _save_debug_images(debug_dir, "front", front_x)

    if fp is None:
        fp = face_parsing.FaceParser()

    # profiles: silhouette depth analysis (MediaPipe cannot see faces past
    # ~60° yaw, so geometry comes from the face-parsing silhouette; the
    # MediaPipe pass still runs for QC + a yaw estimate when it works)
    profile_sides, profile_faces = [], {}
    for tag, path, yaw in (("left", left, -65.0), ("right", right, 65.0)):
        if not path:
            continue
        meas, qc, x = preprocessing.analyze_photo(
            fm, path, expect_yaw=yaw, yaw_tolerance=35.0)
        if meas is not None:
            profile_faces[tag] = (x["aligned_rgb"], x["det"])
        raw["photos"][tag] = {"file": os.path.basename(path), "qc": qc,
                              "measurements": meas,
                              "quality": x["quality"], "align": x["align"],
                              "confidence": x["confidence"]}
        photos.append(os.path.basename(path))
        _save_debug_images(debug_dir, tag, x)

        if fp.available:
            if x.get("normalized_rgb") is not None:
                rgb_n = x["normalized_rgb"]
                yaw_est = qc.get("yaw") if qc.get("yaw") is not None else yaw
            else:  # true side view: no landmarks — parse the raw photo
                try:
                    rgb_n = normalize_colors(load_image_rgb(path))
                except ImageReadError:
                    rgb_n = None
                yaw_est = 90.0 if yaw > 0 else -90.0
            if rgb_n is not None:
                pmeas, pinfo = profile_analyzer.analyze_profile(
                    fp.parse(rgb_n), yaw_deg=yaw_est)
                raw["photos"][tag]["profile"] = (
                    {"measurements": pmeas, **{k: pinfo[k] for k in
                     ("facing_right", "y0", "ear", "points",
                      "foreshorten_scale") if k in pinfo}}
                    if pmeas else {"failed": pinfo.get("reason")})
                if pmeas:
                    profile_sides.append(pmeas)
                    if debug_dir:
                        os.makedirs(debug_dir, exist_ok=True)
                        profile_analyzer.render_debug(
                            rgb_n, pinfo,
                            os.path.join(debug_dir, f"{tag}_profile.png"))
                elif meas is None:
                    warnings.append(f"{tag} profile unusable: "
                                    f"{pinfo.get('reason')}")
        elif meas is None:
            warnings.append(f"{tag} profile: {qc.get('reason')}")
    if own_fm:
        fm.close()

    # identity check (ArcFace): are the photos the same person? Embeddings
    # are an auxiliary signal only — never converted into morphs. The
    # front embedding is stored for the future offline eval loop
    # (photo <-> avatar-render similarity).
    if ie is None:
        ie = identity_embedding.IdentityEmbedder()
    if ie.available:
        emb_front = ie.embed(front_x["aligned_rgb"], front_x["det"])
        ident = {"available": True,
                 "front_embedding": None if emb_front is None else
                 [round(float(v), 5) for v in emb_front]}
        for tag, (rgb_p, det_p) in profile_faces.items():
            sim = ie.similarity(emb_front, ie.embed(rgb_p, det_p))
            if sim is None:
                continue
            ident[f"similarity_{tag}"] = round(sim, 3)
            if sim < 0.25:
                warnings.append(
                    f"{tag} photo may show a DIFFERENT person than the "
                    f"front photo (identity similarity {sim:.2f}) — "
                    "check the uploads")
        raw["identity"] = ident
    else:
        raw["identity"] = {"available": False, "why": ie.why}

    # MICA 3D reconstruction on the front photo: metric neutral head ->
    # true 3D anthropometrics (depth, jaw angle, beard-robust widths). This
    # is a measurement source only; the mesh never becomes a morph.
    if f3d is None:
        f3d = Face3D()
    if m3d is None:
        m3d = Face3DMeasurer()
    face3d_meas = None
    face3d_rec = None
    if f3d.available and m3d.available:
        face3d_rec = f3d.reconstruct(front_x["aligned_rgb"], front_x["det"])
        if face3d_rec is not None:
            face3d_meas = m3d.measure(face3d_rec)
        raw["face3d"] = {"available": True, "measurements": face3d_meas}
        if debug_dir and face3d_rec is not None:
            os.makedirs(debug_dir, exist_ok=True)
            _save_face3d_debug(debug_dir, m3d, face3d_rec)
    else:
        raw["face3d"] = {"available": False,
                         "why": f3d.why or (None if m3d.available
                                            else "flame_regions.npz missing")}

    # face parsing on the front photo: occlusion, beard, hairline
    parsing = analyze_front_parsing(fp, front_x)
    raw["parsing"] = {k: v for k, v in parsing.items()
                      if k not in ("labels", "beard_mask")}
    if not parsing["available"] and parsing.get("why"):
        warnings.append(f"face parsing unavailable ({parsing['why']}) — "
                        "beard/hairline correction disabled")
    if debug_dir and parsing["available"]:
        os.makedirs(debug_dir, exist_ok=True)
        face_parsing.render_debug(
            front_x["aligned_rgb"], parsing["labels"],
            os.path.join(debug_dir, "front_parsing.png"),
            hairline_y=parsing.get("hairline_y"),
            beard_mask=parsing.get("beard_mask"))

    # appearance runs BEFORE the solve: detected gender selects the anchor
    # set, and the beard label drives the lower-face down-weighting (the
    # second beard channel besides parsing — segmentation misses smooth or
    # sparse beards)
    appearance, gender, body_type, app_conf = None, gender_hint, "average", None
    if with_appearance:
        appearance, app_warn = analyze_appearance(front, (left, right))
        if app_warn:
            warnings.append(app_warn)
        raw["appearance"] = appearance
        if appearance:
            gender = appearance["gender"] or gender
            body_type = appearance["bodyType"] or body_type
            app_conf = appearance["confidence"]

    beard_style = ((appearance or {}).get("beard", {}).get("style")
                   or beard_hint)
    raw["beard_style_used"] = beard_style
    extra = {}
    if parsing.get("forehead_hairline") is not None:
        fh_conf = 0.9 * front_x["confidence"].get("forehead_height", 0.8)
        if parsing.get("hat_fraction", 0.0) > 0.25:
            fh_conf *= 0.6   # boundary may be a hat brim, not the hairline
        extra["forehead_hairline"] = fusion.FeatureValue(
            value=parsing["forehead_hairline"],
            confidence=fh_conf, source="face_parsing")
    extra.update(fusion.profile_features(profile_sides,
                                         beard_style=beard_style))
    extra.update(fusion.face3d_features(face3d_meas))
    engine_params, face_meta, feats, notes = fusion.fuse(
        front_meas, front_x["confidence"], calib, gender=gender or "male",
        occlusion=parsing.get("occlusion"), beard_style=beard_style,
        beard_coverage=parsing.get("beard_coverage", 0.0),
        extra_features=extra)
    raw["calibration_notes"] = notes
    raw["calibration_gender"] = gender or "male"
    raw["engine_params"] = engine_params
    raw["features"] = {k: v.as_dict() for k, v in feats.items()}
    raw["face_meta"] = face_meta

    result = {
        "version": 1,
        "gender": gender,
        "face": {CAMEL[k]: v for k, v in engine_params.items()},
        # per-parameter provenance — additive, the engine contract above
        # is unchanged
        "faceMeta": {CAMEL[k]: v for k, v in face_meta.items()
                     if k in CAMEL},
        "appearance": {
            "skinTone": appearance["skinTone"] if appearance else None,
            "hair": appearance["hair"] if appearance
            else {"style": None, "color": None},
            "beard": appearance["beard"] if appearance
            else {"style": None, "color": None},
            "glasses": appearance["glasses"] if appearance else None,
        },
        "body": {"bodyType": body_type},
        "meta": {
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "phase": "B-geometry+appearance" if appearance else "A-geometry-only",
            "confidence": {
                "geometry": round(float(np.mean(
                    list(front_x["confidence"].values()))), 3)
                if front_x["confidence"] else 0.4,
                "appearance": app_conf},
            "source_photos": photos,
            "front_qc": {k: (round(v, 1) if isinstance(v, float) else v)
                         for k, v in front_qc.items()},
        },
    }
    return result, raw, engine_params, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("front")
    ap.add_argument("left", nargs="?")
    ap.add_argument("right", nargs="?")
    ap.add_argument("--out", default=os.path.join(HERE, "output"))
    ap.add_argument("--debug", action="store_true",
                    help="write aligned/normalized/landmark-overlay images "
                         "to <out>/debug/")
    args = ap.parse_args()

    try:
        result, raw, engine_params, warnings = analyze_photos(
            args.front, args.left, args.right,
            debug_dir=os.path.join(args.out, "debug") if args.debug else None)
    except FrontPhotoError as e:
        sys.exit(str(e))
    for w in warnings:
        print(f"[warn] {w}", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    raw_path = os.path.join(args.out, "raw_analysis.json")
    out_path = os.path.join(args.out, "avatar_parameters.json")
    paste_path = os.path.join(args.out, "identity_paste.json")
    with open(raw_path, "w") as f:
        json.dump(raw, f, indent=2)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    with open(paste_path, "w") as f:
        # snake_case engine params — paste directly into the Sandbox's
        # Identity tab JSON box to see the result (until Phase C automates it)
        json.dump(engine_params, f, indent=2)

    print(f"\n[pipeline] raw analysis -> {raw_path}")
    print(f"[pipeline] avatar parameters -> {out_path}")
    print(f"[pipeline] sandbox paste file -> {paste_path}\n")
    for k, v in result["face"].items():
        bar = int((v - 0.0) * 40)
        print(f"  {k:18s} {v:5.2f}  |{'#' * bar}{'.' * (40 - bar)}|")

    app = result["appearance"]
    if app["hair"]["style"] is not None:
        print(f"\n  appearance: gender={result['gender']} "
              f"skin={app['skinTone']} hair={app['hair']['style']}"
              f"/{app['hair']['color']} beard={app['beard']['style']}"
              f"/{app['beard']['color']} glasses={app['glasses']} "
              f"body={result['body']['bodyType']}")


if __name__ == "__main__":
    main()
