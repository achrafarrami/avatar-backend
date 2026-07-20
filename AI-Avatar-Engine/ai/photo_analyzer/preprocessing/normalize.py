"""Color/lighting normalization for ANALYSIS COPIES only.

The normalized image is fed to segmentation / appearance models, which are
sensitive to color casts and flat lighting. It is NEVER used for geometry
measurement (landmarks run on the un-retouched aligned image) and it is not
a beauty filter: only global white balance and mild adaptive contrast —
no smoothing, no local edits, no feature modification.
"""
import cv2
import numpy as np


def normalize(rgb):
    """Gray-world white balance + CLAHE on the L channel. Returns uint8 RGB."""
    img = rgb.astype(np.float32)

    # gray-world: scale channels so their means match the overall mean
    means = img.reshape(-1, 3).mean(axis=0)
    gray = float(means.mean())
    scale = gray / np.maximum(means, 1e-3)
    scale = np.clip(scale, 0.6, 1.6)  # bound the correction — strong casts
    img = np.clip(img * scale, 0, 255).astype(np.uint8)

    # mild CLAHE on lightness only (keeps chroma intact)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
