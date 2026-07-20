"""
MediaPipe Face Landmarker → scale-invariant facial measurements.

This module MEASURES, it never maps: every function returns raw geometric
ratios. Converting ratios into engine morph parameters is exclusively the
calibration layer's job (calibration/calibration.json), so all systematic
landmarker bias cancels out — the neutral anchors in that file are produced
by running THIS SAME CODE on renders of the neutral base avatar.

All width measurements are normalized by inter-pupillary distance (IPD);
vertical measurements by face height (mesh top ↔ chin). MediaPipe's relative
z is used only for low-confidence depth hints (nose bridge/tip projection).
"""
import math
import os

import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from PIL import Image, ImageOps

try:  # iPhone HEIC support (optional)
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


class ImageReadError(Exception):
    """The photo file could not be decoded."""


def load_image_rgb(image_path):
    """Decode ANY PIL-supported format (JPEG/PNG/WebP/HEIC...), apply EXIF
    rotation (phone photos are usually stored sideways + a rotation tag —
    MediaPipe's own loader ignores it and then fails to find the face).
    Returns an HxWx3 uint8 RGB numpy array."""
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as e:
        raise ImageReadError(
            f"could not read image ({type(e).__name__}) — use JPG/PNG/WebP/HEIC"
        ) from e
    return np.asarray(img).copy()


def load_image(image_path):
    return mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=load_image_rgb(image_path))

_MODEL = os.path.join(os.path.dirname(__file__), "..", "models",
                      "face_landmarker.task")

# ------------------------------------------------------------ landmark ids
# Canonical MediaPipe face-mesh indices (478-point model with iris).
L = {
    "pupil_r": 468, "pupil_l": 473,            # iris centers (subject's R/L)
    "eye_r_inner": 133, "eye_r_outer": 33,
    "eye_l_inner": 362, "eye_l_outer": 263,
    "eye_r_top": 159, "eye_r_bottom": 145,
    "eye_l_top": 386, "eye_l_bottom": 374,
    "brow_r": 105, "brow_l": 334,
    "cheek_r": 234, "cheek_l": 454,            # lateral face extremes
    "gonion_r": 58, "gonion_l": 288,           # jaw corners
    "jaw_mid_r": 172, "jaw_mid_l": 397,
    "chin": 152, "face_top": 10,
    "sellion": 168, "nose_tip": 1, "subnasale": 2,
    "alar_r": 129, "alar_l": 358,              # nose wing outer points
    "mouth_r": 61, "mouth_l": 291,
    "lip_top_outer": 0, "lip_top_inner": 13,
    "lip_bot_inner": 14, "lip_bot_outer": 17,
    "cheek_mid_r": 50, "cheek_mid_l": 280,
}

# Which named landmarks each measurement uses, and its dominant axis:
# "h" horizontal (degrades with yaw), "v" vertical (degrades with pitch),
# "z" relative-depth hint (always low confidence), "angle" mixed.
# Used for per-measurement confidence and the debug overlay; keep in sync
# with measure_front below.
MEASUREMENT_INFO = {
    "face_width": (("cheek_r", "cheek_l"), "h"),
    "face_height": (("face_top", "chin"), "v"),
    "forehead_height": (("face_top", "brow_r"), "v"),
    "jaw_width": (("gonion_r", "gonion_l"), "h"),
    "jaw_mid_width": (("jaw_mid_r", "jaw_mid_l"), "h"),
    "lower_face_height": (("subnasale", "chin"), "v"),
    "chin_height": (("lip_bot_outer", "chin"), "v"),
    "eye_width": (("eye_r_outer", "eye_r_inner", "eye_l_inner", "eye_l_outer"), "h"),
    "eye_openness": (("eye_r_top", "eye_r_bottom", "eye_l_top", "eye_l_bottom"), "v"),
    "eye_inner_distance": (("eye_r_inner", "eye_l_inner"), "h"),
    "eye_tilt_deg": (("eye_r_inner", "eye_r_outer", "eye_l_inner", "eye_l_outer"), "angle"),
    "brow_height": (("brow_r", "eye_r_top", "brow_l", "eye_l_top"), "v"),
    "nose_width": (("alar_r", "alar_l"), "h"),
    "nose_length": (("sellion", "nose_tip"), "v"),
    "nose_bridge_proj": (("sellion", "cheek_mid_r", "cheek_mid_l"), "z"),
    "nose_tip_proj": (("nose_tip", "cheek_mid_r", "cheek_mid_l"), "z"),
    "philtrum_length": (("subnasale", "lip_top_outer"), "v"),
    "mouth_width": (("mouth_r", "mouth_l"), "h"),
    "lip_thickness": (("lip_top_outer", "lip_top_inner", "lip_bot_inner", "lip_bot_outer"), "v"),
    "cheek_mid_width": (("cheek_mid_r", "cheek_mid_l"), "h"),
}


def measurement_confidence(qc, quality=None, expect_yaw=0.0,
                           occlusion=None):
    """Per-measurement confidence 0..1.

    Phase-1 factors: head pose (width measurements suffer under yaw,
    vertical ones under pitch) x face blur x landmark resolution.
    `occlusion` (measurement name -> 0..1 visible fraction, from face
    parsing) multiplies on top when available — that is how beard/hair
    coverage down-weights the measurements it corrupts."""
    yaw = abs((qc.get("yaw") or 0.0) - expect_yaw)
    pitch = abs(qc.get("pitch") or 0.0)
    blur = (quality or {}).get("blur_factor", 1.0)
    res = (quality or {}).get("resolution_factor", 1.0)
    photo = max(0.15, blur) * max(0.25, res)  # soft floors: bad != useless

    def pose(axis):
        if axis == "h":
            return 1.0 - min(1.0, (yaw / 30.0) ** 2 + 0.3 * (pitch / 30.0) ** 2)
        if axis == "v":
            return 1.0 - min(1.0, (pitch / 30.0) ** 2 + 0.3 * (yaw / 30.0) ** 2)
        if axis == "z":  # MediaPipe relative z: never trust it much
            return 0.5 * (1.0 - min(1.0, (yaw / 45.0) ** 2))
        return 1.0 - min(1.0, (yaw / 35.0) ** 2 + (pitch / 35.0) ** 2)

    conf = {}
    for name, (_lms, axis) in MEASUREMENT_INFO.items():
        c = pose(axis) * photo
        if occlusion and name in occlusion:
            c *= occlusion[name]
        conf[name] = round(max(0.02, c), 3)
    return conf


def render_overlay(det, out_path, points_only=False):
    """Landmark debug image: full mesh as small dots, the named points the
    pipeline actually measures as labeled markers, measurement segments as
    lines. This is the ground truth for 'where did the numbers come from' —
    e.g. beard-inflated jaw landmarks are immediately visible here."""
    from PIL import ImageDraw
    img = Image.fromarray(det["rgb"]).convert("RGB")
    dr = ImageDraw.Draw(img)
    pts = det["pts"]
    for x, y, _ in pts:
        dr.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(60, 220, 130))
    if not points_only:
        for name, (lms, axis) in MEASUREMENT_INFO.items():
            if axis in ("h", "v"):
                for a, b in zip(lms[::2], lms[1::2]):
                    pa, pb = pts[L[a]], pts[L[b]]
                    dr.line((pa[0], pa[1], pb[0], pb[1]),
                            fill=(255, 90, 90), width=2)
    for name, idx in L.items():
        x, y, _ = pts[idx]
        dr.ellipse((x - 3, y - 3, x + 3, y + 3), outline=(255, 215, 0),
                   width=2)
    img.save(out_path)
    return out_path


class FaceMeasurer:
    def __init__(self, model_path=_MODEL):
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            output_facial_transformation_matrixes=True,
            num_faces=1)
        self._lm = mp_vision.FaceLandmarker.create_from_options(opts)

    def close(self):
        self._lm.close()

    # -------------------------------------------------------------- detect
    def detect(self, image_path=None, image=None):
        """Returns dict with landmarks (N,3 np array, x/y in image aspect,
        z relative), head pose in degrees, and the RGB array the detection
        ran on (`rgb`, for overlays/preprocessing), or None if no face
        found. Pass either a path or an HxWx3 uint8 RGB array."""
        if image is None:
            image = load_image_rgb(str(image_path))
        img = mp.Image(image_format=mp.ImageFormat.SRGB,
                       data=np.ascontiguousarray(image))
        res = self._lm.detect(img)
        if not res.face_landmarks:
            return None
        pts = np.array([[p.x * img.width, p.y * img.height, p.z * img.width]
                        for p in res.face_landmarks[0]])
        yaw = pitch = roll = None
        if res.facial_transformation_matrixes:
            m = np.array(res.facial_transformation_matrixes[0])[:3, :3]
            # ZYX euler from rotation matrix
            yaw = math.degrees(math.atan2(-m[2, 0],
                                          math.hypot(m[0, 0], m[1, 0])))
            pitch = math.degrees(math.atan2(m[2, 1], m[2, 2]))
            roll = math.degrees(math.atan2(m[1, 0], m[0, 0]))
        return {"pts": pts, "yaw": yaw, "pitch": pitch, "roll": roll,
                "width": img.width, "height": img.height, "rgb": image}

    # ---------------------------------------------------------- measurements
    def measure_front(self, det):
        """All geometric ratios extractable from a near-frontal photo."""
        p = det["pts"]

        def d(a, b):  # 2D distance (x, y only — z is unreliable for lengths)
            return float(np.linalg.norm(p[L[a]][:2] - p[L[b]][:2]))

        ipd = d("pupil_r", "pupil_l")
        face_h = d("face_top", "chin")
        eye_w_r = d("eye_r_inner", "eye_r_outer")
        eye_w_l = d("eye_l_inner", "eye_l_outer")
        eye_h_r = d("eye_r_top", "eye_r_bottom")
        eye_h_l = d("eye_l_top", "eye_l_bottom")

        # canthal tilt: signed angle of outer-vs-inner corner, avg both eyes
        def tilt(inner, outer, sign):
            v = p[L[outer]][:2] - p[L[inner]][:2]
            return sign * math.degrees(math.atan2(-v[1], abs(v[0])))
        eye_tilt = 0.5 * (tilt("eye_r_inner", "eye_r_outer", 1) +
                          tilt("eye_l_inner", "eye_l_outer", 1))

        # brow height above eye top, per side, normalized by IPD
        brow_h = 0.5 * (d("brow_r", "eye_r_top") + d("brow_l", "eye_l_top"))

        # z-projection hints (relative depth, low confidence)
        z_cheeks = 0.5 * (p[L["cheek_mid_r"]][2] + p[L["cheek_mid_l"]][2])
        nose_bridge_proj = float((z_cheeks - p[L["sellion"]][2]) / ipd)
        nose_tip_proj = float((z_cheeks - p[L["nose_tip"]][2]) / ipd)

        return {
            "ipd_px": ipd,
            "face_width": d("cheek_r", "cheek_l") / ipd,
            "face_height": face_h / ipd,
            "forehead_height": d("face_top", "brow_r") / face_h,
            "jaw_width": d("gonion_r", "gonion_l") / ipd,
            "jaw_mid_width": d("jaw_mid_r", "jaw_mid_l") / ipd,
            "lower_face_height": d("subnasale", "chin") / face_h,
            "chin_height": d("lip_bot_outer", "chin") / face_h,
            "eye_width": 0.5 * (eye_w_r + eye_w_l) / ipd,
            "eye_openness": 0.5 * (eye_h_r + eye_h_l) / ipd,
            "eye_inner_distance": d("eye_r_inner", "eye_l_inner") / ipd,
            "eye_tilt_deg": eye_tilt,
            "brow_height": brow_h / ipd,
            "nose_width": d("alar_r", "alar_l") / ipd,
            "nose_length": d("sellion", "nose_tip") / face_h,
            "nose_bridge_proj": nose_bridge_proj,
            "nose_tip_proj": nose_tip_proj,
            "philtrum_length": d("subnasale", "lip_top_outer") / face_h,
            "mouth_width": d("mouth_r", "mouth_l") / ipd,
            "lip_thickness": (d("lip_top_outer", "lip_top_inner") +
                              d("lip_bot_inner", "lip_bot_outer")) / ipd,
            "cheek_mid_width": d("cheek_mid_r", "cheek_mid_l") / ipd,
        }

    def analyze(self, image_path, expect_yaw=0.0, yaw_tolerance=18.0):
        """Detect + QC + measure one photo. Returns (measurements|None, qc)."""
        try:
            det = self.detect(image_path)
        except ImageReadError as e:
            return None, {"ok": False, "reason": str(e)}
        if det is None:
            return None, {"ok": False, "reason": "no face detected"}
        qc = {"ok": True, "yaw": det["yaw"], "pitch": det["pitch"],
              "roll": det["roll"]}
        if det["yaw"] is not None and abs(det["yaw"] - expect_yaw) > yaw_tolerance:
            qc["ok"] = False
            qc["reason"] = (f"head yaw {det['yaw']:.0f}° too far from "
                            f"expected {expect_yaw:.0f}°")
        return self.measure_front(det), qc
