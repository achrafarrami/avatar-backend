"""Photo quality metrics: blur, exposure, resolution -> factors + score.

Measured on the FACE region only (a sharp face on a bokeh background must
not be penalized). Every factor is a 0..1 multiplier; `score` is their
product. The factors feed per-measurement confidence in face_landmarks —
they never gate the pipeline (a bad photo still produces a result, with
low confidence).
"""
import cv2
import numpy as np


def _clamp01(x):
    return float(min(1.0, max(0.0, x)))


def assess(rgb, face_bbox=None, ipd_px=None):
    """rgb: HxWx3 uint8. face_bbox: (x0, y0, x1, y1) in pixels (landmark
    extremes); None = whole image. ipd_px: inter-pupillary distance in px
    (landmark-resolution proxy). Returns a dict of raw metrics + factors."""
    h, w = rgb.shape[:2]
    if face_bbox is not None:
        x0, y0, x1, y1 = [int(v) for v in face_bbox]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        crop = rgb[y0:y1, x0:x1] if (x1 - x0 > 8 and y1 - y0 > 8) else rgb
    else:
        crop = rgb
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)

    # Blur: variance of the Laplacian on a fixed-width (256px) copy of the
    # face crop, making the number resolution-independent. Calibrated
    # empirically (scratch blur_experiment): sharp faces (CG render and
    # noisy 'camera' version) read 42-63, gaussian sigma=2 reads ~15,
    # sigma=4 reads ~4 — thresholds 5..35 separate them cleanly.
    ch, cw = gray.shape
    small = cv2.resize(gray, (256, max(32, int(ch * 256.0 / cw))),
                       interpolation=cv2.INTER_AREA)
    blur_var = float(cv2.Laplacian(small, cv2.CV_64F).var())
    blur_factor = _clamp01((blur_var - 5.0) / 30.0)

    # Exposure: penalize only strong under/over-exposure of the face.
    mean = float(gray.mean())
    exposure_factor = _clamp01(1.0 - max(0.0, abs(mean - 118.0) - 45.0) / 60.0)
    clipped = float(np.mean((gray < 8) | (gray > 247)))
    exposure_factor *= _clamp01(1.0 - (clipped - 0.05) / 0.25)

    # Resolution: IPD in pixels is the honest proxy for landmark precision
    # (image megapixels mean nothing if the face is small in frame).
    if ipd_px is None:
        resolution_factor = 1.0
    else:
        resolution_factor = _clamp01((float(ipd_px) - 25.0) / 55.0)

    return {
        "blur_var": round(blur_var, 1),
        "blur_factor": round(blur_factor, 3),
        "face_mean_brightness": round(mean, 1),
        "clipped_fraction": round(clipped, 4),
        "exposure_factor": round(exposure_factor, 3),
        "ipd_px": None if ipd_px is None else round(float(ipd_px), 1),
        "resolution_factor": round(resolution_factor, 3),
        "score": round(blur_factor * exposure_factor * resolution_factor, 3),
    }
