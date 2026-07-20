"""3D anthropometrics from a MICA reconstruction (FLAME topology).

Reads TRUE 3D geometry off the neutral mesh + its iBUG-68 landmarks: face
depth, feature projections, jaw angle, and beard-robust widths — the
quantities 2D landmarks and the silhouette can only approximate, and which
a beard cannot corrupt (MICA reconstructs the same skull with or without
one, verified 0.87mm).

FLAME axes (confirmed on the reconstruction): X = lateral (left +),
Y = up (+), Z = forward (+, out of the face). All linear measurements are
normalized by the outer inter-canthal distance S (a rigid, expression- and
beard-invariant face scale), so every value is a pure shape ratio; the jaw
angle is in degrees. These feed the fusion solver as `face3d_*`
measurements, calibrated against template renders like all the others.
"""
import os

import numpy as np

_REGIONS = os.path.join(os.path.dirname(__file__), "..", "data",
                        "flame_regions.npz")

# iBUG-68 indices used below
_NASION, _NOSE_TIP, _SUBNASALE = 27, 30, 33
_CHIN, _LOWER_LIP = 8, 57
_BROW_R, _BROW_L = 19, 24
_EYE_OUT_R, _EYE_OUT_L = 36, 45
_CHEEK_PTS = (1, 2, 14, 15)      # upper jaw contour ≈ malar width
_JAW_W_PTS = (4, 12)             # jaw-body width
_GONION, _JAW_TOP = 4, 0         # for the jaw-angle wedge


def _load_regions():
    d = np.load(_REGIONS)
    return {k: d[k] for k in d.files}


class Face3DMeasurer:
    def __init__(self):
        self.available = os.path.isfile(_REGIONS)
        self.regions = _load_regions() if self.available else {}

    def _centroid(self, verts, name):
        return verts[self.regions[name]].mean(0)

    def measure(self, rec):
        """rec: {'verts'(5023,3), 'lmk68'(68,3)} from Face3D.reconstruct.
        Returns a dict of face3d_* measurements (already scale-normalized)."""
        v, l = rec["verts"], rec["lmk68"]
        S = float(np.linalg.norm(l[_EYE_OUT_R] - l[_EYE_OUT_L])) or 1e-6
        eye_ctr = 0.5 * (l[_EYE_OUT_R] + l[_EYE_OUT_L])
        ear = 0.5 * (self._centroid(v, "left_ear") +
                     self._centroid(v, "right_ear"))
        cheek = np.mean([l[i] for i in _CHEEK_PTS], axis=0)

        # jaw angle: wedge in the YZ (profile) plane at the gonion between
        # the ramus (toward ear-top) and the body (toward chin)
        g, top, chin = l[_GONION], l[_JAW_TOP], l[_CHIN]
        a, b = (top - g)[1:], (chin - g)[1:]
        cos = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        jaw_angle = float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))

        m = {
            # --- depth / projection (Z), impossible from a front 2D photo ---
            "face3d_nose_proj":   (l[_NOSE_TIP, 2] - l[_NASION, 2]) / S,
            "face3d_nose_bridge": (l[_NASION, 2] - eye_ctr[2]) / S,
            "face3d_nose_tip":    (l[_NOSE_TIP, 2] - l[_SUBNASALE, 2]) / S,
            "face3d_chin_proj":   (l[_CHIN, 2] - l[_LOWER_LIP, 2]) / S,
            "face3d_brow_proj":   (0.5 * (l[_BROW_R, 2] + l[_BROW_L, 2]) - eye_ctr[2]) / S,
            "face3d_face_depth":  (l[_NOSE_TIP, 2] - ear[2]) / S,
            "face3d_cheek_proj":  (cheek[2] - ear[2]) / S,
            # --- angle ---
            "face3d_jaw_angle":   jaw_angle,
            # --- vertical proportion (Y) ---
            "face3d_lowerface":   (l[_SUBNASALE, 1] - l[_CHIN, 1]) /
                                  (l[_NASION, 1] - l[_SUBNASALE, 1] + 1e-9),
            # --- beard-robust widths (X): a beard cannot inflate these ---
            "face3d_bizyg_width": np.linalg.norm(l[_CHEEK_PTS[1]] - l[_CHEEK_PTS[2]]) / S,
            "face3d_jaw_width":   np.linalg.norm(l[_JAW_W_PTS[0]] - l[_JAW_W_PTS[1]]) / S,
        }
        return {k: float(v) for k, v in m.items()}  # never leak numpy scalars

    def landmark_pixels(self, rec):
        """Project the 68 landmarks to front (XY) and side (ZY) orthographic
        pixel coords for the debug view. Returns two (68,2) arrays."""
        l = rec["lmk68"]
        return l[:, [0, 1]], l[:, [2, 1]]
