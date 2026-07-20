"""Image preprocessing layer: quality scoring + face alignment + analysis
color normalization.

`analyze_photo()` is the pipeline's entry point — it wraps the raw
FaceMeasurer with the full preprocessing chain and returns the SAME
(measurements, qc) contract fm.analyze() had, plus an `extras` dict:

    extras = {
        "quality":     blur/exposure/resolution factors + score,
        "align":       what the aligner did (rotation/crop/resize),
        "confidence":  per-measurement confidence 0..1,
        "aligned_rgb": geometry image (roll-corrected, cropped, resized),
        "normalized_rgb": color-normalized copy for segmentation/VLM,
    }

Geometry is always measured on `aligned_rgb` (never color-modified);
`normalized_rgb` exists only for models that care about color constancy.
Every step falls back gracefully — if alignment loses the face, the
original detection is used and the report says so.
"""
import numpy as np

from . import quality as _quality
from . import align as _align
from . import normalize as _normalize

from processors.face_landmarks import (
    ImageReadError, load_image_rgb, measurement_confidence)


def _bbox(det, pad=0.1):
    xy = det["pts"][:, :2]
    x0, y0 = xy.min(axis=0)
    x1, y1 = xy.max(axis=0)
    px, py = (x1 - x0) * pad, (y1 - y0) * pad
    return (x0 - px, y0 - py, x1 + px, y1 + py)


def analyze_photo(fm, image_path, expect_yaw=0.0, yaw_tolerance=18.0):
    """Preprocess + detect + QC + measure one photo.
    Returns (measurements|None, qc, extras)."""
    extras = {"quality": None, "align": None, "confidence": None,
              "aligned_rgb": None, "normalized_rgb": None}
    try:
        rgb = load_image_rgb(str(image_path))
    except ImageReadError as e:
        return None, {"ok": False, "reason": str(e)}, extras

    det = fm.detect(image=rgb)
    if det is None:
        return None, {"ok": False, "reason": "no face detected"}, extras

    # align on the first detection, then re-detect on the aligned image —
    # landmarks are more precise on an upright, well-framed face
    aligned, align_report = _align.align(rgb, det["pts"], det["roll"])
    det2 = fm.detect(image=aligned)
    if det2 is not None:
        det = det2
    else:  # alignment lost the face (rare) — keep original detection
        align_report["fallback"] = "re-detect failed, using original image"
        aligned = rgb
    extras["align"] = align_report
    extras["aligned_rgb"] = aligned

    meas = fm.measure_front(det)
    q = _quality.assess(det["rgb"], face_bbox=_bbox(det),
                        ipd_px=meas["ipd_px"])
    extras["quality"] = q

    qc = {"ok": True, "yaw": det["yaw"], "pitch": det["pitch"],
          "roll": det["roll"], "quality_score": q["score"]}
    if det["yaw"] is not None and abs(det["yaw"] - expect_yaw) > yaw_tolerance:
        qc["ok"] = False
        qc["reason"] = (f"head yaw {det['yaw']:.0f}° too far from "
                        f"expected {expect_yaw:.0f}°")
    if q["score"] < 0.15 and qc["ok"]:
        qc["reason"] = "low photo quality (blur/exposure/face size)"

    extras["confidence"] = measurement_confidence(qc, q, expect_yaw)
    extras["det"] = det
    try:
        extras["normalized_rgb"] = _normalize.normalize(aligned)
    except Exception:  # normalization must never break geometry
        extras["normalized_rgb"] = aligned
    return meas, qc, extras
