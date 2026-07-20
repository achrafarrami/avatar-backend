"""Feature fusion layer: combines MediaPipe measurements, face-parsing
signals, VLM appearance labels (and, in later phases, profile analysis +
identity embeddings) into one confidence-weighted feature table, then
solves it into engine parameters.

Single entry point: `fuse()`. Every parameter that leaves this layer
carries {value, confidence, source} — pipeline.py exposes those in
`faceMeta` next to the flat engine-facing `face` map (the engine contract
itself is unchanged).
"""
from .features import (build_features, profile_features, face3d_features,
                       FeatureValue)
from .solver import solve

__all__ = ["build_features", "profile_features", "face3d_features",
           "FeatureValue", "solve", "fuse"]


def fuse(measurements, base_confidence, calib, gender="male",
         occlusion=None, beard_style=None, beard_coverage=0.0,
         extra_features=None):
    """Build the feature table and solve it.
    `extra_features`: dict name -> FeatureValue for signals measured by
    other modules (forehead_hairline from face parsing, profile depth
    measurements in Phase 3...). Returns (params, meta, features, notes)."""
    feats = build_features(measurements, base_confidence,
                           occlusion=occlusion, beard_style=beard_style,
                           beard_coverage=beard_coverage)
    if extra_features:
        feats.update(extra_features)
    params, meta, notes = solve(feats, calib, gender=gender)
    return params, meta, feats, notes
