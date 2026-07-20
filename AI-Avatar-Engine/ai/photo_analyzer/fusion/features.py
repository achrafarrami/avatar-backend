"""Feature table for the fusion layer.

Every geometric signal entering the solver is a FeatureValue:
    value       raw measurement (ratio / degrees)
    confidence  0..1 — how much the solver should trust it
    source      which module produced it ("mediapipe", "face_parsing",
                "profile_left", ...)

Confidence composition order (multiplicative):
    photo quality x head pose        (preprocessing, phase 1)
  x parsing occlusion                (face_parsing, phase 2)
  x semantic beard down-weight       (VLM beard label, phase 2)

The VLM beard channel exists because segmentation models trained on
CelebAMask-HQ label beards inconsistently (verified: our CG test beard
reads as 'skin') — the appearance VLM is the reliable beard detector on
real photos, so EITHER channel may trigger the down-weighting.
"""
from dataclasses import dataclass, field


@dataclass
class FeatureValue:
    value: float
    confidence: float = 1.0
    source: str = "mediapipe"
    factors: dict = field(default_factory=dict)  # name -> multiplier (debug)

    def scale(self, name, mult):
        mult = max(0.0, min(1.0, float(mult)))
        self.factors[name] = round(mult, 3)
        self.confidence = round(self.confidence * mult, 3)

    def as_dict(self):
        return {"value": round(float(self.value), 4),
                "confidence": round(float(self.confidence), 3),
                "source": self.source, "factors": self.factors}


# Measurements a beard corrupts, with down-weight multipliers. The lists
# were derived EMPIRICALLY: pipeline run on the male template wearing the
# beard_short asset (ground truth = all-neutral) showed mouth_width +13%,
# philtrum -24%, jaw widths +6%, nose_width +5%, face_width +3% — facial
# hair distorts the whole lower-face landmark fit, not just the chin.
# These are AGGRESSIVE on the lower-face widths because the MICA 3D stage
# now supplies beard-robust widths (face3d_bizyg/jaw_width) as a backstop —
# so it is safe to nearly discard the beard-corrupted 2D widths rather than
# average them in. Without the 3D stage these would need to be gentler.
_FULL_BEARD = {
    "jaw_width": 0.15, "jaw_mid_width": 0.15, "cheek_mid_width": 0.30,
    "chin_height": 0.30, "lower_face_height": 0.35, "face_height": 0.55,
    "lip_thickness": 0.50, "mouth_width": 0.35, "philtrum_length": 0.40,
    "nose_width": 0.70, "face_width": 0.40,
}
_GOATEE = {
    "jaw_width": 0.35, "jaw_mid_width": 0.35, "cheek_mid_width": 0.50,
    "chin_height": 0.35, "lower_face_height": 0.45, "face_height": 0.65,
    "lip_thickness": 0.50, "mouth_width": 0.40, "philtrum_length": 0.40,
    "nose_width": 0.75, "face_width": 0.55,
}


# baseline trust of each silhouette-derived profile measurement, from the
# left/right repeatability study on the calibration renders (face depth and
# vertical drops are stable; single-notch and slope fits are noisy)
PROFILE_CONFIDENCE = {
    "profile_face_depth": 0.80, "profile_nose_drop": 0.70,
    "profile_nose_proj": 0.45, "profile_chin_forward": 0.40,
    "profile_chin_drop": 0.40, "profile_lip_proj": 0.35,
    "profile_forehead_slope": 0.35, "profile_jaw_slope": 0.35,
}
# a beard hides the chin/jaw silhouette in profile too
_PROFILE_BEARD = {
    "profile_chin_forward": 0.40, "profile_chin_drop": 0.35,
    "profile_jaw_slope": 0.30, "profile_lip_proj": 0.40,
}


# Base trust of each MICA-derived 3D measurement, set from the sweep
# response magnitudes measured in Phase 6c (strong, clean responders get
# high trust; weak responders low). CRUCIALLY these are NOT beard-reduced:
# MICA reconstructs the same skull with or without a beard (verified
# 0.87mm), so the 3D lower-face geometry stays reliable exactly where the
# 2D measurements get down-weighted — this is the point of the 3D stage.
FACE3D_CONFIDENCE = {
    "face3d_jaw_angle": 0.80, "face3d_bizyg_width": 0.90,
    "face3d_jaw_width": 0.90, "face3d_face_depth": 0.80,
    "face3d_chin_proj": 0.75, "face3d_lowerface": 0.75,
    "face3d_nose_bridge": 0.70, "face3d_brow_proj": 0.70,
    "face3d_nose_proj": 0.60, "face3d_cheek_proj": 0.50,
    "face3d_nose_tip": 0.45,
}


def face3d_features(meas3d):
    """MICA 3D anthropometrics -> FeatureValues (source 'face3d'). No beard
    or occlusion penalty by design — the reconstruction is beard-robust."""
    feats = {}
    for k, v in (meas3d or {}).items():
        fv = FeatureValue(value=float(v), confidence=1.0, source="face3d")
        fv.scale("face3d_base", FACE3D_CONFIDENCE.get(k, 0.4))
        feats[k] = fv
    return feats


def profile_features(side_measurements, beard_style=None):
    """Average per-side profile measurement dicts into FeatureValues.
    Averaging left+right cancels the systematic silhouette shift that
    side lighting causes; a single side gets a confidence haircut."""
    if not side_measurements:
        return {}
    keys = sorted(set().union(*(m.keys() for m in side_measurements)))
    feats = {}
    for k in keys:
        vals = [m[k] for m in side_measurements if k in m]
        fv = FeatureValue(value=float(sum(vals) / len(vals)),
                          confidence=1.0, source="profile")
        fv.scale("profile_base", PROFILE_CONFIDENCE.get(k, 0.4))
        if len(vals) < 2:
            fv.scale("single_side", 0.85)
        if beard_style in ("short", "goatee") and k in _PROFILE_BEARD:
            fv.scale("beard", _PROFILE_BEARD[k])
        feats[k] = fv
    return feats


def build_features(measurements, base_confidence, occlusion=None,
                   beard_style=None, beard_coverage=0.0):
    """Compose the front-photo feature table.
    measurements: name -> value (from FaceMeasurer.measure_front)
    base_confidence: name -> 0..1 (pose x quality, phase 1)
    occlusion: name -> 0..1 visible factor (face parsing), optional
    beard_style: VLM label (None/"none"/"short"/"goatee")
    beard_coverage: parser's hair-pixel fraction of the lower face 0..1
    """
    feats = {}
    for name, value in measurements.items():
        if name == "ipd_px":
            continue
        fv = FeatureValue(value=value,
                          confidence=1.0, source="mediapipe")
        fv.scale("photo", base_confidence.get(name, 1.0))
        if occlusion and name in occlusion:
            fv.scale("parsing_occlusion", occlusion[name])
        feats[name] = fv

    # semantic beard down-weight — triggered by the VLM label OR by heavy
    # parser coverage (>15% of the lower face reading as hair)
    table = None
    if beard_style == "short" or beard_coverage > 0.15:
        table = _FULL_BEARD
    elif beard_style == "goatee":
        table = _GOATEE
    if table:
        for name, mult in table.items():
            if name in feats:
                feats[name].scale("beard", mult)
    return feats
