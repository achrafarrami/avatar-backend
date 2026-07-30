"""
Measured appearance colors: photo -> {skin, hair, brows, iris} hex.

Samples REAL pixel colors from the aligned front photo using the BiSeNet
parsing masks (skin/hair/brows) and the MediaPipe iris centers — exact
tones (any ethnicity, tan, dyed hair...) instead of the VLM's closed label
vocabulary. Labels remain the fallback when a region is too small (bald
head, covered brows) — each sample carries its pixel coverage so the
caller can decide.

Median-based and highlight/shadow-trimmed, so lighting glare and shadow
pockets don't skew the tone. Samples the ALIGNED (pre-normalization) image:
gray-world WB demonstrably desaturates real tones (verified on test
photos: redhead hair -> brown, dark skin -> gray). The parsing masks come
from the normalized image but align pixel-for-pixel (no warp).

No engine parameters here — colors only.
"""
import numpy as np

from processors.face_parsing import SKIN, L_BROW, R_BROW, HAIR


def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(int(round(c)) for c in rgb))


def _luma(px):
    return 0.299 * px[:, 0] + 0.587 * px[:, 1] + 0.114 * px[:, 2]


def _robust_median(px, lo_pct=25, hi_pct=90):
    """Median color of the pixels whose luminance sits between the two
    percentiles — drops specular highlights and shadow pockets."""
    if len(px) < 20:
        return None
    y = _luma(px)
    lo, hi = np.percentile(y, lo_pct), np.percentile(y, hi_pct)
    sel = px[(y >= lo) & (y <= hi)]
    if len(sel) < 10:
        sel = px
    return np.median(sel, axis=0)


def _region(rgb, labels, classes, y_range=None):
    mask = np.isin(labels, classes)
    if y_range is not None:
        m2 = np.zeros_like(mask)
        y0, y1 = max(0, int(y_range[0])), min(mask.shape[0], int(y_range[1]))
        m2[y0:y1] = mask[y0:y1]
        mask = m2
    return rgb[mask], int(mask.sum())


def sample_colors(rgb, labels, det, L):
    """rgb: normalized front image (HxWx3 uint8), labels: parsing map (same
    size), det: preprocessing detection dict (has 'pts'), L: landmark-index
    table from face_landmarks. Returns
    {name: {"hex", "coverage_px"} | None}."""
    pts = det["pts"]
    out = {}

    # --- skin: mid-face band (brow line -> chin), LIT HALF only — a
    # directional shadow side otherwise drags the median several shades
    # dark (fair test photo sampled as tan). Within the lit half, a
    # slightly dark band (10-60) counters bright studio exposure.
    brow_y = 0.5 * (pts[L["brow_r"]][1] + pts[L["brow_l"]][1])
    chin_y = pts[L["chin"]][1]
    mid_x = 0.5 * (pts[L["pupil_r"]][0] + pts[L["pupil_l"]][0])
    band = np.zeros_like(labels, dtype=bool)
    band[int(max(0, brow_y)):int(chin_y)] = \
        (labels == SKIN)[int(max(0, brow_y)):int(chin_y)]
    ys, xs = np.where(band)
    px = rgb[ys, xs].astype(np.float64)
    cov = len(px)
    med = None
    if cov >= 40:
        y = _luma(px)
        left = xs < mid_x
        if left.any() and (~left).any():
            lit = left if np.median(y[left]) >= np.median(y[~left]) else ~left
            px, y = px[lit], y[lit]
        lo, hi = np.percentile(y, 10), np.percentile(y, 60)
        sel = px[(y >= lo) & (y <= hi)]
        med = np.median(sel if len(sel) >= 10 else px, axis=0)
    out["skin"] = None if med is None else {"hex": _hex(med),
                                            "coverage_px": cov}

    # --- hair: above the brow line only (a beard also classes as HAIR)
    px, cov = _region(rgb, labels, [HAIR], (0, brow_y))
    med = _robust_median(px, lo_pct=10, hi_pct=90)
    out["hair"] = None if med is None else {"hex": _hex(med),
                                            "coverage_px": cov}

    # --- beard: HAIR pixels BELOW the nose line — a gray beard under dark
    # scalp hair must not inherit the scalp tone
    nose_y = pts[L["nose_tip"]][1] if "nose_tip" in L else \
        0.5 * (brow_y + chin_y)
    px, cov = _region(rgb, labels, [HAIR], (nose_y, chin_y + 0.3 *
                                            (chin_y - nose_y)))
    med = _robust_median(px, lo_pct=10, hi_pct=90)
    out["beard"] = None if med is None else {"hex": _hex(med),
                                             "coverage_px": cov}

    # --- brows: darkest 60% of brow pixels (skin shows between hairs)
    px, cov = _region(rgb, labels, [L_BROW, R_BROW])
    if len(px) >= 20:
        y = _luma(px)
        sel = px[y <= np.percentile(y, 60)]
        out["brows"] = {"hex": _hex(np.median(sel, axis=0)),
                        "coverage_px": cov}
    else:
        out["brows"] = None

    # --- iris: annulus around each MediaPipe iris center; drop the black
    # pupil core and white sclera by luminance, then median both eyes
    iris_px = []
    eye_pairs = [("pupil_r", "eye_r_inner", "eye_r_outer"),
                 ("pupil_l", "eye_l_inner", "eye_l_outer")]
    h, w = rgb.shape[:2]
    for pupil, inner, outer in eye_pairs:
        if pupil not in L or inner not in L or outer not in L:
            continue
        c = pts[L[pupil]]
        eye_w = np.linalg.norm(pts[L[inner]][:2] - pts[L[outer]][:2])
        r = max(2.0, eye_w * 0.22)
        y0, y1 = int(max(0, c[1] - r)), int(min(h, c[1] + r + 1))
        x0, x1 = int(max(0, c[0] - r)), int(min(w, c[0] + r + 1))
        if y1 <= y0 or x1 <= x0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt((yy - c[1]) ** 2 + (xx - c[0]) ** 2)
        ring = (d >= r * 0.45) & (d <= r)          # skip pupil core
        px = rgb[y0:y1, x0:x1][ring].reshape(-1, 3).astype(np.float64)
        if len(px):
            y = _luma(px)
            px = px[(y > 35) & (y < 210)]           # drop pupil + sclera
            iris_px.append(px)
    iris_px = np.concatenate(iris_px) if iris_px else np.empty((0, 3))
    if len(iris_px) >= 12:
        out["iris"] = {"hex": _hex(np.median(iris_px, axis=0)),
                       "coverage_px": int(len(iris_px))}
    else:
        out["iris"] = None
    return out
