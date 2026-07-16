"""
Generate the 20 user-customization shape keys on a CC3+ avatar template.

Region masks are derived from the vertex regions Reallusion already sculpted
for the ARKit expression shape keys (Nose_*, Cheek_*, Mouth_*, Jaw_*, Brow_*,
Eye_*), so morphs inherit clean, production-quality falloffs. Regions with no
expression analog (ears, forehead, philtrum) use geometric masks whose
landmarks are computed dynamically from the armature bones and mask
centroids — the same script therefore works on the male, female, and toon
bases without retuning.

Usage:
  blender --background --python generate_customization_morphs.py -- \
      <in.blend> <out.blend> <body_object> <armature_object> <eye_object>

Example:
  ... -- male_base.blend male_base.blend Male_Body Male_Armature CC_Base_Eye
"""
import bpy
import numpy as np
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
blend_in, blend_out = argv[0], argv[1]
BODY_NAME = argv[2] if len(argv) > 2 else "Male_Body"
ARMATURE_NAME = argv[3] if len(argv) > 3 else "Male_Armature"
EYE_NAME = argv[4] if len(argv) > 4 else "CC_Base_Eye"

bpy.ops.wm.open_mainfile(filepath=blend_in)

body = bpy.data.objects[BODY_NAME]
arm = bpy.data.objects[ARMATURE_NAME]
mesh = body.data
n = len(mesh.vertices)
key_blocks = mesh.shape_keys.key_blocks
basis = key_blocks["Basis"]

basis_co = np.zeros(n * 3, dtype=np.float64)
basis.data.foreach_get("co", basis_co)
basis_co = basis_co.reshape(n, 3)

normals = np.zeros(n * 3, dtype=np.float64)
mesh.vertices.foreach_get("normal", normals)
normals = normals.reshape(n, 3)

X, Y, Z = basis_co[:, 0], basis_co[:, 1], basis_co[:, 2]

# --- dynamic skeletal landmarks (armature local == body local for CC rigs) ---
HEAD_Z = arm.data.bones["CC_Base_Head"].head_local.z
NECK_Z = arm.data.bones["CC_Base_NeckTwist02"].head_local.z
JAW_Z = arm.data.bones["CC_Base_JawRoot"].head_local.z

# eyeball centers, in body-local space (eye & body share the same transform)
eye_obj = bpy.data.objects[EYE_NAME]
en = len(eye_obj.data.vertices)
eye_co = np.zeros(en * 3, dtype=np.float64)
eye_obj.data.vertices.foreach_get("co", eye_co)
eye_co = eye_co.reshape(en, 3)
eye_pos_center = eye_co[eye_co[:, 0] > 0].mean(axis=0)   # +X side eye
eye_neg_center = eye_co[eye_co[:, 0] < 0].mean(axis=0)   # -X side eye


def smoothstep(v, edge0, edge1):
    t = np.clip((v - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def falling(v, high, low):
    """1 for v<=low, 0 for v>=high, smooth between."""
    return smoothstep(-v, -high, -low)


def band(v, rise_lo, rise_hi, fall_lo, fall_hi):
    return smoothstep(v, rise_lo, rise_hi) * falling(v, fall_hi, fall_lo)


def midline(x_abs, inner, outer):
    """1 at x_abs<=inner, 0 at x_abs>=outer."""
    return falling(x_abs, outer, inner)


# Our own generated keys must never contaminate the expression-derived masks
CUSTOMIZATION_NAMES = {
    "face_width", "jaw_width", "jaw_height", "chin_size", "nose_width",
    "nose_length", "eye_size", "eye_distance", "lip_thickness", "mouth_width",
    "cheek_size", "forehead_height", "eyebrow_height", "eye_tilt",
    "nose_bridge_height", "nose_tip_size", "ear_size", "jaw_angle",
    "cheekbone_height", "philtrum_length",
}


def mask_from_prefixes(prefixes, exclude=()):
    mag = np.zeros(n, dtype=np.float64)
    for kb in key_blocks:
        name = kb.name
        if name == "Basis" or name in CUSTOMIZATION_NAMES:
            continue
        if any(ex in name for ex in exclude):
            continue
        if any(name.startswith(p) for p in prefixes):
            co = np.zeros(n * 3, dtype=np.float64)
            kb.data.foreach_get("co", co)
            co = co.reshape(n, 3)
            d = np.linalg.norm(co - basis_co, axis=1)
            mag = np.maximum(mag, d)
    return mag


def normalize_mask(mag, pct=99.0):
    nz = mag[mag > 1e-6]
    if len(nz) == 0:
        return mag
    hi = np.percentile(nz, pct)
    return np.clip(mag / hi, 0.0, 1.0) if hi > 0 else mag


nose_mask = normalize_mask(mask_from_prefixes(["Nose_"]))
cheek_mask = normalize_mask(mask_from_prefixes(["Cheek_"]))
mouth_mask = normalize_mask(mask_from_prefixes(["Mouth_"]))
jaw_mask = normalize_mask(mask_from_prefixes(["Jaw_"]))
brow_mask = normalize_mask(mask_from_prefixes(["Brow_"]))
eye_mask = normalize_mask(mask_from_prefixes(["Eye_"], exclude=["Eyelash"]))

head_mask = smoothstep(Z, NECK_Z, HEAD_Z)  # 0 at neck -> 1 across head


def weighted_centroid(mask):
    w = mask
    if w.sum() == 0:
        return np.zeros(3)
    return (basis_co * w[:, None]).sum(axis=0) / w.sum()


nose_c = weighted_centroid(nose_mask)
cheek_c = weighted_centroid(cheek_mask)
mouth_c = weighted_centroid(mouth_mask)
jaw_c = weighted_centroid(jaw_mask)
brow_c = weighted_centroid(brow_mask)

morphs = []  # (name, weight_array, direction(n,3), magnitude in local cm)


def add_morph(name, weight, direction, magnitude):
    peak = weight.max()
    if peak > 1e-6:
        weight = weight / peak  # slider=1 reaches full intended magnitude
    morphs.append((name, weight, direction, magnitude))


# Lateral (sign(X)) morphs need a midline ramp: without it, the narrowing
# direction (slider < 0) pushes near-center vertices PAST the midline and the
# face pinches inside-out. The ramp scales displacement to zero at X=0 so
# vertices can never cross sides. Ramp width chosen so displacement < |X|
# everywhere at full slider.
def lateral_dir(ramp_width):
    ramp = smoothstep(np.abs(X), 0.0, ramp_width)
    return np.stack([np.sign(X) * ramp, np.zeros(n), np.zeros(n)], axis=1)


# 1. face_width - whole head scales sideways, smooth taper into neck.
# Hard-dampened in a radius around each eyeball: the eyeball meshes are
# separate objects, so shifting the socket without them creates a cross-eyed
# misalignment. A geometric radius guarantees zero shift at the eye opening.
eye_center_per_vert = np.where((X > 0)[:, None], eye_pos_center, eye_neg_center)
dist_to_eye_xz = np.linalg.norm(basis_co[:, [0, 2]] - eye_center_per_vert[:, [0, 2]], axis=1)
eye_dampen = smoothstep(dist_to_eye_xz, 1.0, 6.0)
add_morph("face_width", head_mask * eye_dampen, lateral_dir(3.0), 1.2)

# 2. jaw_width
add_morph("jaw_width", jaw_mask, lateral_dir(3.0), 0.9)

# 3. jaw_height - jaw drops (mask weakest at hinge, strongest at chin)
add_morph("jaw_height", jaw_mask, np.tile([0, 0, -1.0], (n, 1)), 1.0)

# 4. chin_size - lower-front quadrant of jaw mask, inflate + forward push
chin_sub = jaw_mask * smoothstep(Z, jaw_c[2], jaw_c[2] - 8) * \
    smoothstep(-Y, -jaw_c[1], -jaw_c[1] + 6)
chin_dir = normals * 0.7 + np.tile([0, -0.3, 0], (n, 1))
add_morph("chin_size", chin_sub, chin_dir, 2.2)

# 5. nose_width
add_morph("nose_width", nose_mask, lateral_dir(1.5), 0.5)

# 6. nose_length - tip stretches forward+down, bridge anchored
nose_tip_sub = nose_mask * smoothstep(nose_c[2] - Z, 0, 10)
add_morph("nose_length", nose_tip_sub, np.tile([0, -0.6, -0.8], (n, 1)), 1.4)

# 7. eye_size - radial scale from each eye's own center, X/Z plane only
radial = basis_co - eye_center_per_vert
radial[:, 1] = 0
add_morph("eye_size", eye_mask, radial, 0.35)

# 8. eye_distance - eyes move apart along X
add_morph("eye_distance", eye_mask, lateral_dir(1.0), 0.6)

# 9. lip_thickness - inflate mouth region along normal
add_morph("lip_thickness", mouth_mask, normals, 0.5)

# 10. mouth_width - corners move outward (mask already excludes the midline)
mouth_corner_sub = mouth_mask * smoothstep(np.abs(X), 2, 9)
add_morph("mouth_width", mouth_corner_sub, lateral_dir(2.5), 1.6)

# 11. cheek_size - inflate along normal
add_morph("cheek_size", cheek_mask, normals, 0.7)

# 12. forehead_height - cap above the brows, front-facing only, pushed up
front_facing = smoothstep(-normals[:, 1], 0.15, 0.5)
forehead_mask = smoothstep(Z, brow_c[2] - 4.6, brow_c[2] + 8.4) * front_facing
add_morph("forehead_height", forehead_mask, np.tile([0, 0, 1.0], (n, 1)), 1.8)

# 13. eyebrow_height
add_morph("eyebrow_height", brow_mask, np.tile([0, 0, 1.0], (n, 1)), 0.5)

# 14. eye_tilt - outer corner up, inner corner down (canthal tilt)
outer_sign = np.sign(np.abs(X) - np.abs(eye_center_per_vert[:, 0]))
add_morph("eye_tilt", eye_mask,
          np.stack([np.zeros(n), np.zeros(n), outer_sign], axis=1), 0.28)

# 15. nose_bridge_height - upper nose pushed forward
bridge_sub = nose_mask * smoothstep(Z - nose_c[2], 0, 10)
add_morph("nose_bridge_height", bridge_sub, np.tile([0, -1.0, 0], (n, 1)), 1.0)

# 16. nose_tip_size - tip cluster, inflate along normal
tip_sub = nose_mask * smoothstep(nose_c[2] - Z, 3, 12)
add_morph("nose_tip_size", tip_sub, normals, 1.1)

# 17. ear_size - lateral band at ear height. Lateral thresholds derived from
# the widest geometry (the ears) in the band around head-bone height.
ear_zone = (Z > HEAD_Z + 2) & (Z < HEAD_Z + 7)
W = np.abs(X[ear_zone]).max() if ear_zone.any() else 9.0
lateral = smoothstep(np.abs(X), 0.65 * W, 0.93 * W)
ear_height = band(Z, HEAD_Z - 5, HEAD_Z - 2, HEAD_Z + 3, HEAD_Z + 6)
add_morph("ear_size", lateral * ear_height * head_mask, normals, 1.3)

# 18. jaw_angle - gonion corners: high |X| within jaw mask, mid-height
gonion_sub = jaw_mask * smoothstep(np.abs(X), 7, 10.5) * \
    smoothstep(Z, jaw_c[2] - 6, jaw_c[2] + 4)
add_morph("jaw_angle", gonion_sub,
          np.stack([np.sign(X) * 0.8, np.zeros(n), np.full(n, -0.4)], axis=1), 1.8)

# 19. cheekbone_height - upper cheek up + slightly out
cheekbone_sub = cheek_mask * smoothstep(Z - cheek_c[2], 0, 8)
add_morph("cheekbone_height", cheekbone_sub,
          np.stack([np.sign(X) * 0.3, np.zeros(n), np.full(n, 1.0)], axis=1), 1.1)

# 20. philtrum_length - midline band between upper lip and nose base,
# front-facing skin only. Offsets relative to mouth/nose mask centroids.
# (1 - nose_mask) keeps the columella / nose base anchored — without it the
# nose bottom droops with the philtrum (visible on the female base).
philtrum_mask = band(Z, mouth_c[2] - 2.5, mouth_c[2] - 1.0,
                     mouth_c[2] + 0.5, mouth_c[2] + 2.0) * \
    midline(np.abs(X), 1.0, 3.0) * \
    falling(Y, nose_c[1] + 4.3, nose_c[1] + 1.3) * \
    np.clip(1.0 - nose_mask, 0.0, 1.0)
add_morph("philtrum_length", philtrum_mask, np.tile([0, 0, -1.0], (n, 1)), 0.6)

# ---------------------------------------------------------------------------
print(f"\nLandmarks: HEAD_Z={HEAD_Z:.2f} NECK_Z={NECK_Z:.2f} JAW_Z={JAW_Z:.2f} "
      f"ear_W={W:.2f}")
print(f"Centroids: nose={nose_c.round(2)} mouth={mouth_c.round(2)} "
      f"jaw={jaw_c.round(2)} brow={brow_c.round(2)}")
print(f"\nCreating {len(morphs)} customization shape keys on {BODY_NAME}...\n")

failures = []
for name, weight, direction, magnitude in morphs:
    kb = mesh.shape_keys.key_blocks.get(name)
    if kb is None:
        kb = body.shape_key_add(name=name, from_mix=False)
    kb.slider_min = -1.0
    kb.slider_max = 1.0
    kb.value = 0.0
    new_co = basis_co + direction * (weight * magnitude)[:, None]
    kb.data.foreach_set("co", new_co.reshape(-1).astype(np.float32))
    nz = int((weight > 0.05).sum())
    status = "" if nz > 20 else "  <-- SUSPICIOUS (too few verts)"
    if nz <= 20:
        failures.append(name)
    print(f"  {name:20s} affected_verts={nz:5d}{status}")

mesh.update()
if failures:
    raise SystemExit(f"ABORT, degenerate masks: {failures}")

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("\nSaved:", blend_out)
