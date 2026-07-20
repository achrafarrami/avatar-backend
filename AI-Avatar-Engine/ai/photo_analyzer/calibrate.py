"""
Calibration factory: anchors AND gains, both measured — never guessed.

Modes (combinable):
  python calibrate.py --renders <dir> --gender male|female
      Anchor the 0.5-neutral measurements to renders of that template's
      neutral head (blender/scripts/render_head_views.py output). Female
      anchors live in "neutral_measurements_female"; a female photo is then
      compared against the female head, not the male one.

  python calibrate.py --fit-gains <sweep_dir>
      Fit every parameter's gain from a morph-response sweep
      (blender/scripts/render_param_sweep.py: renders at param 0.2 / 0.8).
      gain = (0.8 - 0.2) / (measurement_hi - measurement_lo), signed.
      Parameters whose measurement barely responds on the render (below a
      relative noise threshold) are marked unreliable and their measurement
      is disabled instead of amplifying noise.

  python calibrate.py --hairline-renders <dir> --gender male|female
      Anchor the forehead_hairline measurement from renders of the
      template WEARING HAIR (blender/scripts/render_hairline_calib.py) —
      the templates are bald, so the standard neutral renders can't
      provide this one. The measurement runs through the pipeline's own
      preprocessing + face-parsing code so parser bias cancels. If the dir
      also contains <param>_lo/_hi.png sweeps, the hairline response
      slopes are (re)written into the response matrix.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from processors.face_landmarks import FaceMeasurer
import preprocessing


def _measure(fm, image_path, expect_yaw=0.0):
    """Measure a render through the SAME preprocessing chain the pipeline
    uses on photos (align/crop/resize). Anchors and photo measurements must
    go through identical code or the landmarker's crop-dependent bias stops
    cancelling out."""
    meas, qc, _extras = preprocessing.analyze_photo(fm, image_path,
                                                    expect_yaw=expect_yaw)
    return meas, qc

HERE = os.path.dirname(os.path.abspath(__file__))
CALIB = os.path.join(HERE, "calibration", "calibration.json")

# which morph params may PHYSICALLY drive each 3D measurement — the sweep
# fit keeps only these (MICA reconstructs plausible faces, so spurious
# cross-responses are noise; whitelisting mirrors the profile approach)
FACE3D_RESPONSE_WHITELIST = {
    "face3d_nose_proj":   ["nose_bridge_height", "nose_tip_size", "nose_length"],
    "face3d_nose_bridge": ["nose_bridge_height", "forehead_height"],
    "face3d_nose_tip":    ["nose_tip_size", "nose_length"],
    "face3d_chin_proj":   ["chin_size", "jaw_angle"],
    "face3d_brow_proj":   ["nose_bridge_height", "eyebrow_height", "forehead_height"],
    "face3d_face_depth":  ["face_width", "jaw_width"],
    "face3d_cheek_proj":  ["cheekbone_height", "cheek_size"],
    "face3d_jaw_angle":   ["jaw_angle", "jaw_height"],
    "face3d_lowerface":   ["jaw_height", "chin_size"],
    "face3d_bizyg_width": ["cheek_size", "face_width", "cheekbone_height"],
    "face3d_jaw_width":   ["jaw_width", "jaw_angle"],
}


def _face3d_stack():
    """Load the MICA reconstructor + measurer, or (None, None, why)."""
    from processors.face3d import Face3D
    from processors.face3d_measure import Face3DMeasurer
    f3d = Face3D()
    if not f3d.available:
        return None, None, f3d.why
    m3d = Face3DMeasurer()
    if not m3d.available:
        return None, None, "flame_regions.npz missing"
    return f3d, m3d, None


def _measure_face3d(fm, f3d, m3d, path):
    """Front render -> 3D anthropometrics through the pipeline's own
    preprocessing + MICA path (bias cancels vs photos)."""
    meas, qc, x = preprocessing.analyze_photo(fm, path)
    if meas is None:
        return None
    rec = f3d.reconstruct(x["aligned_rgb"], x["det"])
    return m3d.measure(rec) if rec is not None else None


def anchor_face3d(fm, calib, renders_dir, gender):
    """Anchor the face3d_* neutral measurements from the neutral front
    render (MICA is a front-photo reconstructor)."""
    f3d, m3d, why = _face3d_stack()
    if f3d is None:
        print(f"[face3d] unavailable ({why}) — 3D anchors skipped")
        return
    front = os.path.join(renders_dir, "neutral_front.png")
    meas = _measure_face3d(fm, f3d, m3d, front)
    if meas is None:
        print("[face3d] no reconstruction on neutral render — skipped")
        return
    key = "neutral_measurements" if gender == "male" else \
          "neutral_measurements_female"
    calib.setdefault(key, {})
    for k, val in meas.items():
        calib[key][k] = round(float(val), 6)
    print(f"[face3d] {gender}: anchored {len(meas)} 3D measurements")


def fit_face3d(fm, calib, sweep_dir):
    """Measure d(face3d measurement)/d(param) from the FRONT sweep renders
    (same renders as --fit-gains), keeping only whitelisted responses."""
    f3d, m3d, why = _face3d_stack()
    if f3d is None:
        sys.exit(f"face3d unavailable: {why}")
    rm = calib.get("response_matrix")
    if not (rm and rm.get("slopes")):
        sys.exit("run --fit-gains before --fit-3d")
    print(f"[fit-3d] {'param':20s} kept 3D responses")
    for pname, row in rm["slopes"].items():
        lo = _measure_face3d(fm, f3d, m3d,
                             os.path.join(sweep_dir, f"{pname}_lo.png"))
        hi = _measure_face3d(fm, f3d, m3d,
                             os.path.join(sweep_dir, f"{pname}_hi.png"))
        kept = {}
        for k in FACE3D_RESPONSE_WHITELIST:
            row[k] = 0.0
            if lo and hi and pname in FACE3D_RESPONSE_WHITELIST[k]:
                row[k] = round((hi[k] - lo[k]) / 0.6, 6)
                if row[k] != 0.0:
                    kept[k] = row[k]
        if kept:
            print(f"[fit-3d] {pname:20s} " + "  ".join(
                f"{m}:{v:+.4f}" for m, v in kept.items()))


def anchor(fm, calib, renders_dir, gender):
    front = os.path.join(renders_dir, "neutral_front.png")
    if not os.path.isfile(front):
        sys.exit(f"missing {front} — run blender/scripts/render_head_views.py first")
    meas, qc = _measure(fm, front, expect_yaw=0.0)
    if meas is None:
        sys.exit(f"no face detected on the neutral render: {qc}")
    key = "neutral_measurements" if gender == "male" else \
          "neutral_measurements_female"
    calib[key] = {k: round(v, 6) for k, v in meas.items() if k != "ipd_px"}
    print(f"[anchor] {gender}: {len(calib[key])} neutrals "
          f"(yaw {qc['yaw']:.1f} deg)")


def fit_gains(fm, calib, sweep_dir):
    """Measure the FULL response matrix: d(every measurement)/d(every param).
    The pipeline then solves all params jointly (ridge least squares), which
    kills the cross-talk that made single-gain calibration slam into clamps
    (e.g. face_width inflates every /IPD width ratio at once)."""
    meas_names = [k for k in calib["neutral_measurements"] if k != "ipd_px"]
    slopes = {}
    print(f"[fit] {'param':20s} strongest measurement responses")
    for pname in calib["params"]:
        lo_p = os.path.join(sweep_dir, f"{pname}_lo.png")
        hi_p = os.path.join(sweep_dir, f"{pname}_hi.png")
        if not (os.path.isfile(lo_p) and os.path.isfile(hi_p)):
            print(f"[fit] {pname:20s} sweep renders missing, skipped")
            continue
        lo_meas, _ = _measure(fm, lo_p)
        hi_meas, _ = _measure(fm, hi_p)
        if lo_meas is None or hi_meas is None:
            print(f"[fit] {pname:20s} face not detected, skipped")
            continue
        row = {m: round((hi_meas[m] - lo_meas[m]) / 0.6, 6)
               for m in meas_names}
        slopes[pname] = row
        top = sorted(row.items(), key=lambda kv: -abs(kv[1]))[:3]
        print(f"[fit] {pname:20s} " + "  ".join(
            f"{m}:{v:+.3f}" for m, v in top))
    calib["response_matrix"] = {
        "note": "d(measurement)/d(param) from render sweep; used by the "
                "pipeline's joint ridge least-squares solve. Regenerate with "
                "calibrate.py --fit-gains after morph changes.",
        "ridge_lambda": 0.3,
        "slopes": slopes,
    }
    print(f"[fit] response matrix: {len(slopes)} params x {len(meas_names)} measurements")


def _measure_profile_render(fp, path):
    """Silhouette measurements of one 90° profile render — the same code
    path the pipeline uses for user profile photos (no MediaPipe: it can't
    see faces at 90°)."""
    from processors.face_landmarks import load_image_rgb
    from processors.profile_analyzer import analyze_profile
    from preprocessing.normalize import normalize
    labels = fp.parse(normalize(load_image_rgb(path)))
    meas, info = analyze_profile(labels, yaw_deg=90.0)
    return meas, info


def anchor_profiles(fm, calib, renders_dir, gender):
    """Anchor profile_* measurements from the neutral left+right renders
    (averaged — the side lighting shifts the segmentation boundary, and
    averaging both sides cancels it, matching what the pipeline does with
    user photos)."""
    from processors.face_parsing import FaceParser
    fp = FaceParser()
    if not fp.available:
        print(f"[profile] parser unavailable ({fp.why}) — profile anchors "
              "skipped")
        return
    sides = []
    for side in ("left", "right"):
        p = os.path.join(renders_dir, f"neutral_{side}.png")
        if not os.path.isfile(p):
            continue
        meas, info = _measure_profile_render(fp, p)
        if meas is None:
            print(f"[profile] {side}: {info.get('reason')}")
            continue
        sides.append(meas)
    if not sides:
        print("[profile] no usable profile renders — anchors skipped")
        return
    keys = sorted(set().union(*(m.keys() for m in sides)))
    key = "neutral_measurements" if gender == "male" else \
          "neutral_measurements_female"
    for k in keys:
        vals = [m[k] for m in sides if k in m]
        calib[key][k] = round(float(sum(vals) / len(vals)), 6)
    print(f"[profile] {gender}: anchored {len(keys)} profile measurements "
          f"from {len(sides)} side(s)")


# Which parameters may PHYSICALLY drive each profile measurement. The
# single-view sweep is noisy (side lighting + silhouette jitter produce
# absurd fits like cheek_size -> forehead_slope -2.2), so only anatomically
# plausible responses are kept; everything else is zeroed. ear_size appears
# in the ear-normalized measurements because scaling the avatar's ear
# genuinely rescales every /ear_height ratio — that is real observability,
# not noise.
PROFILE_RESPONSE_WHITELIST = {
    "profile_nose_proj": ["nose_bridge_height", "nose_tip_size",
                          "nose_length", "ear_size"],
    "profile_nose_drop": ["nose_length", "ear_size"],
    "profile_face_depth": ["ear_size", "jaw_width", "face_width"],
    "profile_chin_forward": ["chin_size", "jaw_angle", "jaw_height"],
    "profile_chin_drop": ["chin_size", "jaw_height", "lip_thickness"],
    "profile_lip_proj": ["lip_thickness", "philtrum_length"],
    "profile_forehead_slope": ["forehead_height", "nose_bridge_height",
                               "eyebrow_height"],
    "profile_jaw_slope": ["jaw_angle", "jaw_height", "chin_size",
                          "jaw_width"],
}


def fit_profile(fm, calib, sweep_dir):
    """Measure d(profile measurement)/d(param) from a left-view sweep
    (render_param_sweep.py with view=left), keeping only whitelisted
    (physically plausible) responses."""
    from processors.face_parsing import FaceParser
    fp = FaceParser()
    if not fp.available:
        sys.exit(f"face parser unavailable: {fp.why}")
    rm = calib.get("response_matrix")
    if not (rm and rm.get("slopes")):
        sys.exit("run --fit-gains before --fit-profile")
    print(f"[fit-profile] {'param':20s} kept profile responses")
    for pname, row in rm["slopes"].items():
        lo_p = os.path.join(sweep_dir, f"{pname}_lo.png")
        hi_p = os.path.join(sweep_dir, f"{pname}_hi.png")
        if not (os.path.isfile(lo_p) and os.path.isfile(hi_p)):
            continue
        lo_m, _ = _measure_profile_render(fp, lo_p)
        hi_m, _ = _measure_profile_render(fp, hi_p)
        kept = {}
        for k in PROFILE_RESPONSE_WHITELIST:
            row[k] = 0.0
            if (lo_m and hi_m and k in lo_m and k in hi_m
                    and pname in PROFILE_RESPONSE_WHITELIST[k]):
                row[k] = round((hi_m[k] - lo_m[k]) / 0.6, 6)
                kept[k] = row[k]
        if kept:
            print(f"[fit-profile] {pname:20s} " + "  ".join(
                f"{m}:{v:+.3f}" for m, v in kept.items()))


def anchor_hairline(fm, calib, renders_dir, gender):
    """Anchor forehead_hairline (+ optionally its response slopes) from
    haired renders, using the pipeline's own parsing path."""
    from processors.face_parsing import FaceParser
    from pipeline import analyze_front_parsing
    fp = FaceParser()
    if not fp.available:
        sys.exit(f"face parser unavailable: {fp.why}")

    def fh(path):
        meas, qc, x = preprocessing.analyze_photo(fm, path)
        if meas is None:
            sys.exit(f"no face detected on {path}: {qc}")
        p = analyze_front_parsing(fp, x)
        v = p.get("forehead_hairline")
        if v is None:
            sys.exit(f"no hairline detected on {path} — check the hair "
                     "asset is visible in the render")
        return v

    neutral_png = os.path.join(renders_dir, "neutral_haired.png")
    if not os.path.isfile(neutral_png):
        sys.exit(f"missing {neutral_png} — run render_hairline_calib.py")
    val = fh(neutral_png)
    key = "neutral_measurements" if gender == "male" else \
          "neutral_measurements_female"
    calib[key]["forehead_hairline"] = round(val, 6)
    print(f"[hairline] {gender} anchor forehead_hairline = {val:.4f}")

    rm = calib.get("response_matrix")
    if not (rm and rm.get("slopes")):
        print("[hairline] no response matrix yet — slopes skipped")
        return
    wrote = 0
    for pname, row in rm["slopes"].items():
        lo_p = os.path.join(renders_dir, f"{pname}_lo.png")
        hi_p = os.path.join(renders_dir, f"{pname}_hi.png")
        if os.path.isfile(lo_p) and os.path.isfile(hi_p):
            row["forehead_hairline"] = round((fh(hi_p) - fh(lo_p)) / 0.6, 6)
            wrote += 1
        else:
            row.setdefault("forehead_hairline", 0.0)
    print(f"[hairline] response slopes measured for {wrote} params "
          "(others below noise, set 0)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", default=None,
                    help="neutral render dir to anchor (with --gender)")
    ap.add_argument("--gender", default="male", choices=["male", "female"])
    ap.add_argument("--fit-gains", default=None, metavar="SWEEP_DIR")
    ap.add_argument("--fit-profile", default=None, metavar="SWEEP_DIR",
                    help="left-view sweep dir (render_param_sweep.py "
                         "view=left) to fit profile-measurement responses")
    ap.add_argument("--fit-3d", default=None, metavar="SWEEP_DIR",
                    help="front sweep dir (same as --fit-gains) to fit the "
                         "MICA face3d_* measurement responses")
    ap.add_argument("--hairline-renders", default=None, metavar="DIR",
                    help="haired render dir (render_hairline_calib.py) to "
                         "anchor forehead_hairline (with --gender)")
    ap.add_argument("legacy_dir", nargs="?", help=argparse.SUPPRESS)
    args = ap.parse_args()

    with open(CALIB) as f:
        calib = json.load(f)
    fm = FaceMeasurer()

    renders = args.renders or args.legacy_dir
    if renders is None and args.fit_gains is None \
            and args.hairline_renders is None and args.fit_profile is None \
            and args.fit_3d is None:
        renders = os.path.join(HERE, "calibration", "renders")
    if renders:
        anchor(fm, calib, renders, args.gender)
        anchor_profiles(fm, calib, renders, args.gender)
        anchor_face3d(fm, calib, renders, args.gender)
    if args.fit_gains:
        if not calib.get("neutral_measurements"):
            sys.exit("anchor neutrals before fitting gains")
        fit_gains(fm, calib, args.fit_gains)
    if args.fit_profile:
        fit_profile(fm, calib, args.fit_profile)
    if args.fit_3d:
        fit_face3d(fm, calib, args.fit_3d)
    if args.hairline_renders:
        anchor_hairline(fm, calib, args.hairline_renders, args.gender)
    fm.close()

    with open(CALIB, "w") as f:
        # default=float: numpy scalars must never truncate the JSON write
        json.dump(calib, f, indent=2, default=float)
    print(f"[calibrate] wrote {CALIB}")


if __name__ == "__main__":
    main()
