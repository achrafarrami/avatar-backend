"""Confidence-weighted joint ridge solve: feature table -> engine params.

Same mathematical core as calibration v2 (response matrix A = d meas /
d param, ridge least squares), upgraded for fusion:

- MISSING measurements are simply dropped from the system (a photo without
  a detectable hairline just has no forehead_hairline row).
- Each measurement row is weighted by its CONFIDENCE on top of the noise
  floor. Crucially, the ridge lambda is computed from the noise-floor
  weights ONLY: when confidences drop (beard, blur, occlusion), the data
  term shrinks against a fixed prior and the affected params are pulled
  toward neutral 0.5 — low-trust evidence moves sliders less. That is the
  intended behavior, not an accident; don't "fix" lambda to track the
  confidence-weighted matrix.
- Regularization is adjustable: response_matrix.ridge_lambda is the global
  knob; params.<name>.prior_strength (default 1.0) scales the pull toward
  neutral per parameter (lower = the param follows evidence more eagerly,
  higher = it stays conservative).
- Output includes per-parameter confidence + dominant source, computed
  from each parameter's observability: how much confident measurement
  signal exists along its response column.
"""
import numpy as np

# Absolute noise floors for measurements whose real-world repeatability is
# far worse than the default 2%-of-neutral model. Values come from the
# left-vs-right spread observed on the calibration renders (side lighting
# shifts the segmentation silhouette). Without these, the slope/notch
# measurements get weighted ~30x too high, inflating the ridge term and
# shrinking every OTHER measurement's influence with it.
NOISE_FLOOR_OVERRIDES = {
    "profile_jaw_slope": 0.15, "profile_forehead_slope": 0.15,
    "profile_chin_forward": 0.05, "profile_chin_drop": 0.08,
    "profile_lip_proj": 0.04, "profile_nose_proj": 0.06,
    "profile_nose_drop": 0.05, "profile_face_depth": 0.08,
    "forehead_hairline": 0.04,
}


def solve(feats, calib, gender="male"):
    """feats: name -> FeatureValue. Returns (params, meta, notes).
    params: name -> 0..1 engine value.
    meta:   name -> {value, confidence, source} for the engine contract."""
    neutral = calib.get("neutral_measurements") or {}
    if gender == "female" and calib.get("neutral_measurements_female"):
        neutral = calib["neutral_measurements_female"]
    if not neutral:
        raise RuntimeError(
            "calibration.json has no neutral anchors — run calibrate.py")

    rm = calib.get("response_matrix")
    notes = []
    if not (rm and rm.get("slopes")):
        raise RuntimeError("calibration.json has no response_matrix — "
                           "run calibrate.py --fit-gains")

    pnames = list(rm["slopes"].keys())
    all_m = sorted({m for row in rm["slopes"].values() for m in row})
    mnames = [m for m in all_m if m in feats and m in neutral]
    dropped = [m for m in all_m if m not in mnames]
    if dropped:
        notes.append("measurements absent this run: " + ", ".join(dropped))

    # noise-floor weights (comparability across ratio/degree units) and
    # confidence weights (trust) — see module docstring for why lambda
    # uses only the former
    w_floor = np.array([1.0 / max(0.006, 0.02 * abs(neutral[m]),
                                  NOISE_FLOOR_OVERRIDES.get(m, 0.0))
                        for m in mnames])
    w_conf = np.array([max(0.02, feats[m].confidence) for m in mnames])

    A0 = np.array([[rm["slopes"][p].get(m, 0.0) for p in pnames]
                   for m in mnames]) * w_floor[:, None]
    A = A0 * w_conf[:, None]
    dm = np.array([feats[m].value - neutral[m]
                   for m in mnames]) * w_floor * w_conf

    lam_base = rm.get("ridge_lambda", 0.3) * \
        float(np.trace(A0.T @ A0)) / len(pnames)
    prior = np.array([
        float(calib["params"].get(p, {}).get("prior_strength", 1.0))
        for p in pnames])
    lam_diag = lam_base * prior
    dp = np.linalg.solve(A.T @ A + np.diag(lam_diag), A.T @ dm)

    params, meta = {}, {}
    # per-param observability: confidence-weighted share of its response
    # column that survives — this is what "how sure are we about cheekSize"
    # honestly means in a joint solve
    col_abs = np.abs(A0)  # (m, p)
    for i, name in enumerate(pnames):
        lo, hi = calib["params"][name]["clamp"]
        val = round(float(min(hi, max(lo, 0.5 + dp[i]))), 4)
        params[name] = val
        weights = col_abs[:, i]
        total = float(weights.sum())
        if total < 1e-9:
            conf, source = 0.0, "none"
        else:
            conf = float((weights * w_conf).sum() / total)
            j = int(np.argmax(weights * w_conf))
            source = feats[mnames[j]].source
        meta[name] = {"value": val, "confidence": round(conf, 3),
                      "source": source}
    for name in calib["params"]:
        if name not in params:
            params[name] = 0.5
            meta[name] = {"value": 0.5, "confidence": 0.0, "source": "none"}

    notes.append(f"confidence-weighted ridge: {len(pnames)} params x "
                 f"{len(mnames)} measurements, lambda={lam_base:.4f}, "
                 f"mean confidence={float(w_conf.mean()):.2f}")
    return params, meta, notes
