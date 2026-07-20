"""ArcFace identity embeddings via onnxruntime (no insightface package —
it needs C++ build tools on Windows; the raw ONNX gives identical
embeddings).

Model: models/arcface_w600k_r50.onnx (buffalo_l recognition model,
insightface project, mirrored by immich-app on HuggingFace). Input:
1x3x112x112 BGR-ish (insightface uses RGB with (x-127.5)/127.5), aligned
by similarity transform to the standard 5-point template.

Role in the pipeline (per architecture decision):
  - verify the 3 uploaded photos show the SAME person (warn if not)
  - store the front embedding in raw_analysis for the future offline
    eval loop (photo <-> avatar-render similarity as a tuning metric)
It NEVER produces morph parameters.

Degrades gracefully when the model file is missing.
"""
import os

import cv2
import numpy as np

_MODEL = os.path.join(os.path.dirname(__file__), "..", "models",
                      "arcface_w600k_r50.onnx")

# ArcFace canonical 5-point template (112x112): both eyes, nose tip,
# both mouth corners — the standard alignment used at training time
_ARC_TEMPLATE = np.array([
    [38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
    [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)

# MediaPipe landmark ids for the same 5 points
_FIVE = {"eye_r": 468, "eye_l": 473, "nose": 1, "mouth_r": 61,
         "mouth_l": 291}


def align_arcface(rgb, det, size=112):
    """Similarity-warp the face to the ArcFace 5-point template.
    Returns an (size, size, 3) uint8 RGB crop, or None if the fit fails.
    Shared by the identity embedder AND the MICA 3D reconstructor — both
    consume the same canonical ArcFace crop, so this must stay one impl."""
    pts = det["pts"]
    src = np.array([[pts[i][0], pts[i][1]] for i in
                    (_FIVE["eye_r"], _FIVE["eye_l"], _FIVE["nose"],
                     _FIVE["mouth_r"], _FIVE["mouth_l"])], dtype=np.float32)
    dst = _ARC_TEMPLATE * (size / 112.0)
    m, _ = cv2.estimateAffinePartial2D(src, dst, method=cv2.LMEDS)
    if m is None:
        return None
    return cv2.warpAffine(rgb, m, (size, size), borderValue=(127, 127, 127))


class IdentityEmbedder:
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

    def embed(self, rgb, det):
        """rgb + MediaPipe detection -> L2-normalized 512-d embedding,
        or None when alignment isn't possible."""
        if not self.available or det is None:
            return None
        face = align_arcface(rgb, det, size=112)
        if face is None:
            return None
        x = (face.astype(np.float32) - 127.5) / 127.5
        x = x.transpose(2, 0, 1)[None]
        emb = self._sess.run(None, {self._input: x})[0][0]
        n = float(np.linalg.norm(emb))
        return emb / n if n > 0 else None

    @staticmethod
    def similarity(a, b):
        """Cosine similarity of two normalized embeddings. Same person is
        typically > 0.35; different people < 0.25 (ArcFace convention)."""
        if a is None or b is None:
            return None
        return float(np.dot(a, b))
