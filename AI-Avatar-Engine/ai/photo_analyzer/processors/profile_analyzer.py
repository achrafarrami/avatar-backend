"""Profile-photo depth measurements from the segmentation silhouette.

MediaPipe cannot land landmarks past ~60° yaw (and fails outright at the
90° calibration renders), so profile geometry comes from the FACE
SILHOUETTE instead: the face-parsing mask is reduced to an outer contour
curve x(y), whose classic anthropometric extrema are detected:

        sellion   (nose root notch,  local min)
        pronasale (nose tip,         global max)
        subnasale (under the nose,   local min)
        labrale   (upper lip,        local max)
        sulcus    (chin notch,       local min)
        pogonion  (chin,             local max)

All horizontal projections are normalized by H = sellion->chin-bottom
vertical distance (hair-independent) and corrected for foreshortening by
1/sin(yaw) when a yaw estimate exists (user photos are often ~60°, the
calibration renders are 90°).

Outputs (prefix `profile_`) are measurements like any other: anchored from
the neutral left/right renders and given response slopes by the profile
sweep (calibrate.py --fit-profile), then solved jointly. This module never
maps to engine parameters directly.
"""
import numpy as np

from .face_parsing import (SKIN, NOSE, L_BROW, R_BROW, L_EYE, R_EYE,
                           U_LIP, L_LIP, MOUTH, L_EAR, R_EAR)

_FACE_CLASSES = [SKIN, NOSE, L_BROW, R_BROW, L_EYE, R_EYE, U_LIP, L_LIP,
                 MOUTH, L_EAR, R_EAR]


def _largest_component(mask):
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return mask
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == biggest


def _smooth(a, k=7):
    pad = k // 2
    ap = np.pad(a.astype(float), pad, mode="edge")
    return np.array([np.median(ap[i:i + k]) for i in range(len(a))])


def _local_extreme(f, lo, hi, mode):
    """Index of min/max of f in [lo, hi); None if the range is empty."""
    lo, hi = int(max(0, lo)), int(min(len(f), hi))
    if hi - lo < 3:
        return None
    seg = f[lo:hi]
    i = int(np.argmin(seg) if mode == "min" else np.argmax(seg))
    return lo + i


def _nearest_extreme(f, start, stop, mode, win=6, prominence=2.5):
    """Walk from `start` toward `stop` and return the FIRST index that is
    a local min/max within +/-win AND prominent by at least `prominence`
    pixels — e.g. the nose ROOT is the first real notch above the nose
    tip, not the (deeper) eye-socket notch a global argmin would grab.
    The prominence requirement skips the flat micro-plateaus the median
    smoothing produces, which would otherwise all qualify as extrema."""
    step = 1 if stop >= start else -1
    lo_b, hi_b = win, len(f) - win - 1
    for i in range(int(start), int(np.clip(stop, 0, len(f))), step):
        if not (lo_b <= i <= hi_b):
            continue
        w = f[i - win:i + win + 1]
        if mode == "min":
            if f[i] <= w.min() + 1e-9 and w.max() - f[i] >= prominence:
                return i
        else:
            if f[i] >= w.max() - 1e-9 and f[i] - w.min() >= prominence:
                return i
    return None


def analyze_profile(labels, yaw_deg=None):
    """labels: face-parsing map of a profile photo.
    Returns (measurements dict | None, info dict). Measurements are
    already mirrored (facing direction handled) and foreshortening-
    corrected. info carries contour points for the debug page.

    The vertical frame is anchored on the EAR — the one region BiSeNet
    segments reliably at 90° (verified on the calibration renders, where
    every width/fraction-based framing scheme proved unstable). Anatomy:
    ear top ~ brow level, ear bottom ~ nose-base level, ear height ~ the
    middle third of the face — so all search windows and the measurement
    scale derive from it. No ear (covered by hair) -> profile unusable."""
    h, w = labels.shape
    face = np.isin(labels, _FACE_CLASSES)
    if face.sum() < 2500:
        return None, {"reason": "face mask too small"}
    face = _largest_component(face)

    ear = _largest_component(np.isin(labels, [L_EAR, R_EAR]) & face)
    if ear.sum() < 200:
        return None, {"reason": "no ear visible (covered by hair?) — "
                                 "profile needs a visible ear"}
    eys, exs = np.where(ear)
    ear_top, ear_bot = int(eys.min()), int(eys.max())
    ear_h = float(ear_bot - ear_top)
    ear_cx = float(exs.mean())
    if ear_h < 30:
        return None, {"reason": "ear too small in frame"}

    # facing: the face points away from the ear
    cx = float(np.where(face)[1].mean())
    facing_right = ear_cx < cx

    # outer profile contour f(y), mirrored so the face always points +x,
    # over the ear-anchored vertical range (brow-ish down to below chin)
    y0 = max(0, int(ear_top - 1.2 * ear_h))          # forehead
    y1 = min(h - 1, int(ear_bot + 1.6 * ear_h))      # below the chin
    ys = np.arange(y0, y1 + 1)
    f = np.array([(np.where(face[y])[0].max() if facing_right
                   else w - 1 - np.where(face[y])[0].min())
                  if face[y].any() else np.nan for y in ys])
    valid = ~np.isnan(f)
    if valid.sum() < 0.6 * len(f):
        return None, {"reason": "profile contour too fragmented"}
    f[~valid] = np.interp(np.where(~valid)[0], np.where(valid)[0], f[valid])
    f = _smooth(f)

    def rel(y_abs):  # absolute row -> contour index
        return int(np.clip(y_abs - y0, 0, len(f) - 1))

    # nose tip: strongest protrusion between ear top and just below ear
    # bottom (the nose occupies the middle third, like the ear)
    i_nose = _local_extreme(f, rel(ear_top), rel(ear_bot + 0.25 * ear_h),
                            "max")
    if i_nose is None:
        return None, {"reason": "no nose apex found"}
    i_sell = _local_extreme(f, i_nose - 0.75 * ear_h, i_nose - 0.15 * ear_h,
                            "min")
    i_sub = _local_extreme(f, i_nose + 0.06 * ear_h, i_nose + 0.45 * ear_h,
                           "min")
    if i_sell is None or i_sub is None:
        return None, {"reason": "nose root/base notches not found"}
    i_lip = _local_extreme(f, i_sub + 2, i_sub + 0.5 * ear_h, "max")
    i_sulcus = _local_extreme(f, i_lip + 2, i_lip + 0.5 * ear_h, "min") \
        if i_lip is not None else None
    i_chin = _local_extreme(f, i_sulcus + 2,
                            min(len(f), i_sulcus + 0.7 * ear_h), "max") \
        if i_sulcus is not None else None

    # foreshortening: horizontal depth projects with sin(yaw)
    s = 1.0
    if yaw_deg is not None and 25.0 <= abs(yaw_deg) < 88.0:
        s = 1.0 / max(0.5, abs(np.sin(np.radians(yaw_deg))))

    E = ear_h  # scale unit: hair/beard-independent, stable across trims

    # facial plane x: MEDIAN of the contour over the brow->eye band. A
    # band median is far more repeatable than any single detected notch
    # (the sellion jumps between the nose root and the eye-socket notch
    # from image to image and skewed nose projection by up to 2x).
    plane = float(np.median(f[rel(ear_top):rel(ear_top + 0.35 * ear_h)]))

    meas = {
        "profile_nose_proj": s * float(f[i_nose] - plane) / E,
        "profile_nose_drop": float((y0 + i_nose) - ear_top) / E,
    }
    if i_lip is not None:
        meas["profile_lip_proj"] = s * float(f[i_lip] - f[i_sub]) / E
    if i_chin is not None and i_sulcus is not None:
        meas["profile_chin_forward"] = s * float(f[i_chin] - plane) / E
        meas["profile_chin_drop"] = float(i_chin - i_sub) / E
    # ear-to-nose depth (ear center x in mirrored space)
    ear_cx_m = ear_cx if facing_right else w - 1 - ear_cx
    meas["profile_face_depth"] = s * float(f[i_nose] - ear_cx_m) / E

    # forehead slope: line fit on the contour above the sellion
    lo, hi = int(max(0, i_sell - 0.9 * ear_h)), int(i_sell - 0.2 * ear_h)
    if hi - lo > 8:
        yy = np.arange(lo, hi)
        coef = np.polyfit(yy, f[lo:hi], 1)
        # dx/dy in mirrored space; positive = forehead leans back going up
        meas["profile_forehead_slope"] = s * float(-coef[0])

    # jaw slope: line fit on the mask underside between the rear (below
    # the ear) and the chin — the jawline IS the bottom silhouette edge
    if i_chin is not None:
        y_chin_abs = y0 + i_chin
        bys, bxs = [], []
        x_chin_m = f[i_chin]                      # mirrored x of the chin
        x_back_m = (ear_cx if facing_right else w - 1 - ear_cx)
        lo_m, hi_m = sorted((x_back_m, x_chin_m))
        for xm in range(int(lo_m), int(hi_m)):
            x = int(xm if facing_right else w - 1 - xm)
            col = np.where(face[:y1 + 1, x])[0]
            if col.size and col.max() > ear_bot:
                bys.append(float(col.max()))
                bxs.append(float(xm))
        if len(bxs) > 12:
            coef = np.polyfit(np.array(bxs), np.array(bys), 1)
            # dy/dx in mirrored space (+x = forward): more positive =
            # jawline descends more steeply toward the chin
            meas["profile_jaw_slope"] = s * float(coef[0])

    info = {"facing_right": bool(facing_right), "y0": int(y0),
            "contour": f.tolist(), "ear": [int(ear_top), int(ear_bot)],
            "points": {k: (int(v) if v is not None else None) for k, v in
                       (("sellion", i_sell), ("nose", i_nose),
                        ("subnasale", i_sub), ("lip", i_lip),
                        ("sulcus", i_sulcus), ("chin", i_chin))},
            "foreshorten_scale": round(s, 3)}
    return meas, info


def render_debug(rgb, info, out_path):
    """Draw the mirrored contour, anthropometric points and ear box onto
    the photo — the debug page's proof of where profile numbers came from."""
    import cv2
    vis = rgb.copy()
    h, w = vis.shape[:2]
    y0 = info["y0"]
    f = info["contour"]
    fr = info["facing_right"]
    for i, x in enumerate(f):
        xx = int(x if fr else w - 1 - x)
        if 0 <= xx < w and y0 + i < h:
            vis[y0 + i, max(0, xx - 1):xx + 2] = [255, 60, 60]
    for name, idx in info["points"].items():
        if idx is None:
            continue
        xx = int(f[idx] if fr else w - 1 - f[idx])
        cv2.circle(vis, (xx, y0 + idx), 6, (0, 255, 255), 2)
        cv2.putText(vis, name, (xx + 10 if fr else xx - 70, y0 + idx + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    et, eb = info["ear"]
    cv2.rectangle(vis, (8, et), (34, eb), (0, 220, 80), 2)
    cv2.imwrite(out_path, cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    return out_path
