"""Face alignment: EXIF-upright photo -> roll-corrected, consistently
cropped, standard-size analysis image.

Purely geometric (rotate / crop / resize) — facial features are never
modified. Alignment matters because the calibration anchors were measured
on renders with zero roll and a centered face; normalizing photos toward
those conditions removes a systematic landmark bias, and MediaPipe itself
places landmarks better on upright faces.
"""
import cv2
import numpy as np

MAX_SIDE = 1280
# crop margins as fractions of the landmark bbox size: sides, top, bottom.
# Top is generous on purpose — hairline/forehead analysis (face parsing)
# needs the hair fully in frame.
MARGINS = (0.55, 0.90, 0.40)
ROLL_EPS = 1.0  # degrees below which rotation is skipped (not worth resampling)


def align(rgb, pts, roll_deg):
    """rgb HxWx3 uint8, pts (N,3) landmark array in pixel coords, roll in
    degrees (MediaPipe head pose). Returns (aligned_rgb, report_dict).
    The transform is: rotate by -roll around the face center, crop the
    face bbox + margins, downscale to MAX_SIDE."""
    h, w = rgb.shape[:2]
    xy = pts[:, :2]
    cx, cy = float(xy[:, 0].mean()), float(xy[:, 1].mean())

    report = {"roll_in": round(float(roll_deg or 0.0), 2),
              "rotated": False, "cropped": False, "resized": False}

    out = rgb
    if roll_deg is not None and abs(roll_deg) > ROLL_EPS:
        # Rotate by the NEGATIVE of MediaPipe's roll to cancel it —
        # verified empirically: a +12° rolled image comes back at ~0°
        # after this (with +roll it doubled to 24°). Don't flip blindly.
        m = cv2.getRotationMatrix2D((cx, cy), -roll_deg, 1.0)
        out = cv2.warpAffine(rgb, m, (w, h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_REPLICATE)
        ones = np.ones((len(xy), 1))
        xy = (np.hstack([xy, ones]) @ m.T)
        report["rotated"] = True

    x0, y0 = xy[:, 0].min(), xy[:, 1].min()
    x1, y1 = xy[:, 0].max(), xy[:, 1].max()
    bw, bh = x1 - x0, y1 - y0
    ms, mt, mb = MARGINS
    cx0 = int(max(0, x0 - ms * bw))
    cx1 = int(min(w, x1 + ms * bw))
    cy0 = int(max(0, y0 - mt * bh))
    cy1 = int(min(h, y1 + mb * bh))
    if cx1 - cx0 > 32 and cy1 - cy0 > 32 and (cx1 - cx0 < w or cy1 - cy0 < h):
        out = out[cy0:cy1, cx0:cx1]
        report["cropped"] = True
        report["crop_px"] = [cx0, cy0, cx1, cy1]

    ch, cw = out.shape[:2]
    if max(ch, cw) > MAX_SIDE:
        s = MAX_SIDE / max(ch, cw)
        out = cv2.resize(out, (int(cw * s), int(ch * s)),
                         interpolation=cv2.INTER_AREA)
        report["resized"] = True
    report["out_size"] = [out.shape[1], out.shape[0]]
    return np.ascontiguousarray(out), report
