"""MICA 3D face reconstruction (CPU) as a MEASUREMENT instrument.

Turns the front photo into a metric neutral 3D head (FLAME topology, 5023
vertices) via MICA, so the pipeline can read TRUE 3D anthropometrics —
depth, projection, angles — that 2D landmarks and the profile silhouette
can only approximate. Like every other processor, it never emits engine
parameters directly: Phase 6b measures the mesh, the fusion layer feeds
those measurements to the same joint solver.

Model file: models/mica.tar (MICA pretrained weights, MPG research
license). onnx/torch load lazily; degrades gracefully to available=False
if torch or the checkpoint is missing, so the pipeline runs unchanged.

The reconstruction is expression- and pose-neutral (MICA's canonical
identity shape), which is exactly what we want — expression is animation,
handled elsewhere; here we only care about who the person is.
"""
import os

import numpy as np

from .identity_embedding import align_arcface

_MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "mica.tar")


class Face3D:
    def __init__(self, model_path=_MODEL, threads=2):
        self.available = False
        self.why = None
        self.faces = None
        try:
            import torch
        except ImportError:
            self.why = "torch not installed"
            return
        if not os.path.isfile(model_path):
            self.why = f"MICA weights missing: {model_path}"
            return
        try:
            torch.set_num_threads(threads)  # keep the dev box responsive
            from .mica_model import MicaNet
            self._torch = torch
            self._net = MicaNet.from_checkpoint(model_path, device="cpu")
            self.faces = self._net.faces
            self.available = True
        except Exception as e:  # never let a bad load kill the pipeline
            self.why = f"MICA load failed ({type(e).__name__}: {e})"

    def reconstruct(self, rgb, det):
        """rgb (HxWx3 uint8) + MediaPipe detection -> dict with
        `verts` (5023,3) and `lmk68` (68,3) in METERS (FLAME scale), or
        None. The face is aligned with the shared ArcFace 5-point crop —
        identical to the identity embedder's input, which is what MICA was
        trained on."""
        if not self.available or det is None:
            return None
        face = align_arcface(rgb, det, size=112)
        if face is None:
            return None
        # MICA / insightface arcface normalization: RGB, (x-127.5)/127.5
        x = (face.astype(np.float32) - 127.5) / 127.5
        x = self._torch.from_numpy(x.transpose(2, 0, 1)[None])
        verts = self._net(x)
        lmk = self._net.landmarks68(verts)
        return {"verts": verts[0].cpu().numpy(),
                "lmk68": lmk[0].cpu().numpy()}

    def export_obj(self, verts, path):
        """Write the reconstructed mesh for inspection (verts in meters)."""
        with open(path, "w") as f:
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for tri in self.faces:
                f.write(f"f {tri[0] + 1} {tri[1] + 1} {tri[2] + 1}\n")
        return path
