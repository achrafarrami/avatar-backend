"""
Compute candidate Meta wardrobe-fit scale/offset values from
meta_avatar/documentation/head_measurements.json (produced by
measure_heads.py). Crown/region-anchored math (same idea as
blender/scripts/import_hair_pack.py's autofit):

  scale = meta_region_width / realistic_region_width
  offset = anchor_meta - scale * anchor_realistic

where anchor = (0, region.top_y_rel, region.top_z_rel) in the region the
item is authored against. This re-anchors the item's own "top" landmark
(crown for hair/hats, cheek/jaw top for beard, hand-top for wrist items)
from the realistic template's landmark onto the Meta template's, while
scaling by the region's own width ratio (NOT a single global head ratio --
JawRoot barely grows on Meta while the cranium grows a lot, verified).

Items with no per-gender split (glasses/hat/watch: same catalog entry worn
by either Meta avatar) get a compromise = arithmetic mean of the male and
female fits, since the "styles.meta" schema has one override per item, no
gender axis.

Both Blender-frame (Z-up, for the verification renders) and three.js/glTF-
frame (Y-up, X same / Y=Blender Z / Z=-Blender Y -- verified empirically
against the live sandbox) values are written, since the render script and
the item.json runtime schema use different axis conventions.

Usage: python compute_fits.py <head_measurements.json> <out_json>
"""
import json
import sys

MEAS, OUT = sys.argv[1], sys.argv[2]
m = json.load(open(MEAS))


def anchor(region):
    return (0.0, region["top_y_rel"], region["top_z_rel"])


def fit(realistic_region, meta_region):
    scale = meta_region["width"] / realistic_region["width"]
    ar = anchor(realistic_region)
    am = anchor(meta_region)
    offset = (
        am[0] - scale * ar[0],
        am[1] - scale * ar[1],
        am[2] - scale * ar[2],
    )
    return scale, offset


def to_threejs(offset_blender):
    x, y, z = offset_blender
    return [x, z, -y]


def mean(*vals):
    return sum(vals) / len(vals)


out = {}

# --- hair: female-only, CC_Base_Head ---
s_f, o_f = fit(m["realistic_female"]["CC_Base_Head"], m["meta_female"]["CC_Base_Head"])
out["hair_female"] = {"scale": s_f, "offset_blender": o_f, "offset_threejs": to_threejs(o_f)}

# --- glasses/hat: worn by either gender, CC_Base_Head -> compromise ---
s_hm, o_hm = fit(m["realistic_male"]["CC_Base_Head"], m["meta_male"]["CC_Base_Head"])
s_hf, o_hf = s_f, o_f
s_head_c = mean(s_hm, s_hf)
o_head_c = tuple(mean(a, b) for a, b in zip(o_hm, o_hf))
out["head_compromise"] = {
    "scale": s_head_c, "offset_blender": o_head_c, "offset_threejs": to_threejs(o_head_c),
    "male": {"scale": s_hm, "offset_blender": o_hm, "offset_threejs": to_threejs(o_hm)},
    "female": {"scale": s_hf, "offset_blender": o_hf, "offset_threejs": to_threejs(o_hf)},
}

# --- glasses: same head anchor but eye-line sits well below the crown, so
# only apply a fraction of the vertical correction (crown correction is
# calibrated for a landmark at the very top of the head; glasses sit near
# the bone origin, not the crown) ---
GLASSES_Z_FRACTION = 0.35
o_glasses = (o_head_c[0], o_head_c[1] * GLASSES_Z_FRACTION, o_head_c[2] * GLASSES_Z_FRACTION)
out["glasses_compromise"] = {
    "scale": s_head_c, "offset_blender": o_glasses, "offset_threejs": to_threejs(o_glasses),
}

# --- watch: worn by either gender, CC_Base_L_Hand -> compromise ---
s_wm, o_wm = fit(m["realistic_male"]["CC_Base_L_Hand"], m["meta_male"]["CC_Base_L_Hand"])
s_wf, o_wf = fit(m["realistic_female"]["CC_Base_L_Hand"], m["meta_female"]["CC_Base_L_Hand"])
s_w_c = mean(s_wm, s_wf)
o_w_c = tuple(mean(a, b) for a, b in zip(o_wm, o_wf))
out["watch_compromise"] = {
    "scale": s_w_c, "offset_blender": o_w_c, "offset_threejs": to_threejs(o_w_c),
    "male": {"scale": s_wm, "offset_blender": o_wm}, "female": {"scale": s_wf, "offset_blender": o_wf},
}

# --- beard: male-only, proxy region CC_Base_JawRoot ---
s_b, o_b = fit(m["realistic_male"]["CC_Base_JawRoot"], m["meta_male"]["CC_Base_JawRoot"])
out["beard_male"] = {"scale": s_b, "offset_blender": o_b, "offset_threejs": to_threejs(o_b)}

json.dump(out, open(OUT, "w"), indent=2)
for k, v in out.items():
    print(f"[fits] {k}: scale={v['scale']:.4f} offset_blender={[round(x,5) for x in v['offset_blender']]} "
          f"offset_threejs={[round(x,5) for x in v['offset_threejs']]}")
