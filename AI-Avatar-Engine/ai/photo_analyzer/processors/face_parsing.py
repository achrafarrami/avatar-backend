"""BiSeNet face parsing (CelebAMask-HQ, 19 classes) via onnxruntime.

Model: models/face_parsing_resnet18.onnx — yakhyo/face-parsing weights
(MIT license), input 512x512 RGB ImageNet-normalized BCHW, output
(1,19,512,512) logits. Class indices follow the CelebAMask-HQ convention
(verified empirically in the Phase-2 self-test: skin/nose/brows/lips land
where expected on the neutral render).

This module SEGMENTS and derives region signals; it never produces engine
parameters directly. Its three jobs:
  1. `measurement_occlusion()` — per-measurement visibility factors: a
     landmark sitting on beard/hair/hat/glasses pixels is not on skin, so
     the measurement that uses it is corrupted and gets down-weighted in
     the calibration solve. This is the beard fix.
  2. `hairline()` — real forehead extent (MediaPipe's mesh-top point is a
     fixed mesh vertex, NOT the hairline).
  3. masks for the debug page.

Degrades gracefully: if the model file is missing or onnxruntime is not
installed, FaceParser.available is False and the pipeline continues with
Phase-1 confidences.
"""
import os

import cv2
import numpy as np

_MODEL = os.path.join(os.path.dirname(__file__), "..", "models",
                      "face_parsing_resnet18.onnx")

# CelebAMask-HQ label indices
BG, SKIN, L_BROW, R_BROW, L_EYE, R_EYE, EYE_G, L_EAR, R_EAR, EAR_R, \
    NOSE, MOUTH, U_LIP, L_LIP, NECK, NECK_L, CLOTH, HAIR, HAT = range(19)

CLASS_NAMES = ["background", "skin", "l_brow", "r_brow", "l_eye", "r_eye",
               "glasses", "l_ear", "r_ear", "earring", "nose", "mouth",
               "u_lip", "l_lip", "neck", "necklace", "cloth", "hair", "hat"]

# Occlusion is defined by BAD classes only — things that displace the
# visible silhouette away from the skull (beard/fringe read as HAIR, hats,
# high collars). Requiring specific "good" classes instead would falsely
# flag silhouette landmarks (cheek/jaw/chin), whose patches legitimately
# contain background. Glasses (EYE_G) are a soft occluder for eye
# landmarks only (lens refraction shifts corners slightly).
_HARD_OCCLUDERS = (HAIR, HAT, CLOTH)
_EYE_LANDMARKS = {"eye_r_inner", "eye_r_outer", "eye_l_inner", "eye_l_outer",
                  "eye_r_top", "eye_r_bottom", "eye_l_top", "eye_l_bottom",
                  "pupil_r", "pupil_l"}
# face_top may legitimately touch the fringe — never treat it as occluded
_OCCLUSION_EXEMPT = {"face_top"}

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class FaceParser:
    def __init__(self, model_path=_MODEL):
        self.available = False
        self.why = None
        try:
            import onnxruntime as ort
        except ImportError:
            self.why = "onnxruntime not installed"
            return
        if not os.path.isfile(model_path):
            self.why = f"model missing: {model_path}"
            return
        self._sess = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"])
        self._input = self._sess.get_inputs()[0].name
        self.available = True

    # ------------------------------------------------------------ core
    def parse(self, rgb):
        """rgb HxWx3 uint8 -> label map HxW uint8 (same size, nearest)."""
        h, w = rgb.shape[:2]
        x = cv2.resize(rgb, (512, 512), interpolation=cv2.INTER_LINEAR)
        x = (x.astype(np.float32) / 255.0 - _MEAN) / _STD
        x = x.transpose(2, 0, 1)[None]
        logits = self._sess.run(None, {self._input: x})[0][0]  # (19,512,512)
        labels = logits.argmax(axis=0).astype(np.uint8)
        return cv2.resize(labels, (w, h), interpolation=cv2.INTER_NEAREST)

    # ------------------------------------------------- derived signals
    @staticmethod
    def _sample(labels, x, y, r=4):
        h, w = labels.shape
        x0, x1 = max(0, int(x) - r), min(w, int(x) + r + 1)
        y0, y1 = max(0, int(y) - r), min(h, int(y) + r + 1)
        patch = labels[y0:y1, x0:x1]
        return patch.reshape(-1) if patch.size else np.array([BG])

    def measurement_occlusion(self, labels, det, landmark_ids,
                              measurement_info):
        """Returns ({measurement: visible_factor 0..1}, {landmark: fraction}).
        For every named landmark: fraction of a small patch around it whose
        class is in the landmark's expected set. A measurement's factor is
        the MINIMUM of its landmarks' visibility (one corrupted endpoint
        corrupts the whole distance), softened so it down-weights rather
        than hard-kills."""
        pts = det["pts"]
        lm_vis = {}
        for name, idx in landmark_ids.items():
            if name in _OCCLUSION_EXEMPT:
                lm_vis[name] = 1.0
                continue
            x, y = pts[idx][0], pts[idx][1]
            patch = self._sample(labels, x, y)
            bad = float(np.isin(patch, _HARD_OCCLUDERS).mean())
            if name in _EYE_LANDMARKS:
                bad += 0.4 * float((patch == EYE_G).mean())
            lm_vis[name] = round(max(0.0, 1.0 - bad), 3)
        occ = {}
        for meas, (lms, _axis) in measurement_info.items():
            vis = [lm_vis[n] for n in lms if n in lm_vis]
            if not vis:
                continue
            v = min(vis)
            # soften: fully visible -> 1.0, fully covered -> 0.15 (a beard
            # displaces the silhouette but the landmark still carries SOME
            # information; zero would make the solve blind, not robust)
            occ[meas] = round(0.15 + 0.85 * v, 3)
        return occ, lm_vis

    def beard_analysis(self, labels, det):
        """Beard = hair-class pixels below the nose inside the face bbox.
        Returns coverage stats (0..1 of the lower-face area) + the mask."""
        pts = det["pts"]
        xs, ys = pts[:, 0], pts[:, 1]
        x0, x1 = int(xs.min()), int(xs.max())
        nose_y = int(pts[2][1])          # subnasale landmark (id 2)
        chin_y = int(ys.max())
        h, w = labels.shape
        y1 = min(h, chin_y + int(0.35 * (chin_y - nose_y)))  # beard hangs low
        region = np.zeros_like(labels, dtype=bool)
        region[nose_y:y1, max(0, x0):min(w, x1)] = True
        beard_mask = region & (labels == HAIR)
        lower_face = region & np.isin(labels, [SKIN, HAIR, NOSE, MOUTH,
                                               U_LIP, L_LIP])
        area = int(lower_face.sum())
        return {
            "coverage": round(float(beard_mask.sum()) / area, 3) if area else 0.0,
            "mask": beard_mask,
        }

    def hairline(self, labels, det):
        """Hairline at the face midline: for the columns around the nose
        x-position, the LOWEST hair-like pixel above the brows; median
        across columns. Returns {"y", "hat_fraction"} or None when there
        is no hair-like boundary (bald / shaved / hair fully pulled back).

        HAT pixels count as hair-like on purpose: segmentation reads some
        hairstyles (buns, tight updos) as 'hat', and a real hat brim sits
        near the hairline anyway — callers use hat_fraction to LOWER the
        measurement's confidence instead of dropping it."""
        pts = det["pts"]
        # brow y: average of the two brow landmarks (105/334)
        brow_y = float(0.5 * (pts[105][1] + pts[334][1]))
        nose_x = float(pts[1][0])
        ipd = float(np.linalg.norm(pts[468][:2] - pts[473][:2]))
        x0 = max(0, int(nose_x - 0.6 * ipd))
        x1 = min(labels.shape[1], int(nose_x + 0.6 * ipd))
        ys = []
        for cx in range(x0, x1, 2):
            col = labels[: int(brow_y), cx]
            rows = np.where((col == HAIR) | (col == HAT))[0]
            if rows.size:
                ys.append(int(rows.max()))
        if len(ys) < max(3, (x1 - x0) // 8):   # too few columns -> no hairline
            return None
        band = labels[: int(brow_y), x0:x1]
        return {"y": float(np.median(ys)),
                "hat_fraction": round(float((band == HAT).mean()), 3)}


# 19-class color palette for debug visualizations (fixed, not random, so
# debug images are comparable across runs)
_PALETTE = np.array([
    [0, 0, 0], [255, 204, 153], [255, 153, 51], [255, 153, 51],
    [51, 153, 255], [51, 153, 255], [204, 102, 255], [102, 255, 178],
    [102, 255, 178], [255, 255, 102], [255, 102, 102], [153, 51, 255],
    [255, 51, 153], [204, 0, 102], [153, 204, 255], [255, 255, 153],
    [96, 96, 96], [102, 51, 0], [160, 160, 160]], dtype=np.uint8)


def render_debug(rgb, labels, out_path, hairline_y=None, beard_mask=None):
    """Blend the label map over the photo; mark the hairline (cyan line)
    and beard pixels (red tint) if present."""
    vis = (0.55 * rgb + 0.45 * _PALETTE[labels]).astype(np.uint8)
    if beard_mask is not None and beard_mask.any():
        vis[beard_mask] = (0.35 * vis[beard_mask] +
                           0.65 * np.array([255, 40, 40])).astype(np.uint8)
    if hairline_y is not None:
        y = int(hairline_y)
        vis[max(0, y - 1):y + 2, :] = [0, 255, 255]
    cv2.imwrite(out_path, cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    return out_path
