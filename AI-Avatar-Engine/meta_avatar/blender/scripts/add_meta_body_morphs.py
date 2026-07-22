"""
Add Meta-specific stylization morphs that the 20 shared identity morphs don't
cover: head-to-body ratio and body build. These are the cartoon "big head /
stocky vs slim" controls. Kept OUT of the shared morph_definitions.json on
purpose — that file is the AI pipeline's contract (20x20 calibration); these
are meta-only. They live as real shape keys on the meta templates and are
declared in meta_avatar/renderer/meta.map.json.

Morphs (0..1 slider -1..1, 0 = neutral), gender-agnostic (all landmarks are
computed from the armature bones + mesh bounds, nothing hardcoded per base):

  head_size   whole head scales about the head centroid, tapering to 0 across
              the neck. Cross-mesh: the same key is added to EVERY head sub-mesh
              (eyes, teeth, tongue, tearline, occlusion, eyebrows) scaled about
              the same centre, so the face rides with the skull (the cross-mesh
              contract, same as eye_size followers). Eyeball stays spherical
              (uniform scale).
  body_weight torso + limbs inflate outward horizontally (girth), zero on the
              head and fading across the neck. Body mesh only.

Usage:
  blender --background --python add_meta_body_morphs.py -- \
      <in.blend> <out.blend> <body_object> <armature_object>
"""
import bpy
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_in, blend_out = argv[0], argv[1]
BODY_NAME = argv[2]
ARM_NAME = argv[3]

HEAD_SIZE_SCALE = 0.18   # +-18% head scale at slider +-1
BODY_WEIGHT_CM = 0.9     # outward girth (cm) at slider 1

bpy.ops.wm.open_mainfile(filepath=blend_in)
body = bpy.data.objects[BODY_NAME]
arm = bpy.data.objects[ARM_NAME]
mesh = body.data
n = len(mesh.vertices)


def smoothstep(v, e0, e1):
    t = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def obj_basis(obj):
    m = obj.data
    if m.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    co = np.zeros(len(m.vertices) * 3)
    m.shape_keys.key_blocks[0].data.foreach_get("co", co)
    return co.reshape(-1, 3)


def set_key(obj, name, new_co):
    kb = obj.data.shape_keys.key_blocks.get(name) or \
         obj.shape_key_add(name=name, from_mix=False)
    kb.slider_min, kb.slider_max, kb.value = -1.0, 1.0, 0.0
    kb.data.foreach_set("co", new_co.reshape(-1).astype(np.float32))
    obj.data.update()


basis = obj_basis(body)
X, Y, Z = basis[:, 0], basis[:, 1], basis[:, 2]
normals = np.zeros(n * 3)
mesh.vertices.foreach_get("normal", normals)
normals = normals.reshape(n, 3)

HEAD_Z = arm.data.bones["CC_Base_Head"].head_local.z
NECK_Z = arm.data.bones["CC_Base_NeckTwist02"].head_local.z

# head centroid: the skull verts well above the neck (a stable pivot)
skull = basis[Z > HEAD_Z + 3.0]
head_c = skull.mean(axis=0) if len(skull) else np.array(
    [0.0, arm.data.bones["CC_Base_Head"].head_local.y, HEAD_Z + 6.0])
print(f"[meta-body] HEAD_Z={HEAD_Z:.2f} NECK_Z={NECK_Z:.2f} head_c={head_c.round(2)}")

# --- head_size on the body: scale about head_c, tapering to 0 across the neck.
# The ramp must reach 1.0 across the WHOLE face (chin/mouth included) and blend
# only inside the neck band — otherwise the lower-face skin scales less than the
# uniformly-scaled teeth/tongue followers and the mouth pops open. The neck bone
# sits at the head/neck junction, so a band centred there isolates the blend.
head_mask = smoothstep(Z, NECK_Z - 2.0, NECK_Z + 2.0)   # 0 below neck -> 1 face
body_head = basis + (basis - head_c) * (head_mask[:, None] * HEAD_SIZE_SCALE)
set_key(body, "head_size", body_head)

# --- head_size followers: every head sub-mesh scales uniformly about head_c
followers = 0
for obj in bpy.data.objects:
    if obj.type != 'MESH' or obj.name == BODY_NAME:
        continue
    b = obj_basis(obj)
    set_key(obj, "head_size", b + (b - head_c) * HEAD_SIZE_SCALE)
    followers += 1
print(f"[meta-body] head_size + {followers} follower meshes")

# --- body_weight on the body: outward horizontal girth below the neck
body_mask = 1.0 - smoothstep(Z, NECK_Z - 2.0, NECK_Z + 2.0)   # 1 body -> 0 face
horiz = normals.copy()
horiz[:, 2] = 0.0                                        # girth, not height
ln = np.linalg.norm(horiz, axis=1, keepdims=True)
horiz = np.divide(horiz, ln, out=np.zeros_like(horiz), where=ln > 1e-6)
body_weight = basis + horiz * (body_mask[:, None] * BODY_WEIGHT_CM)
set_key(body, "body_weight", body_weight)
print(f"[meta-body] body_weight (body verts affected "
      f"{int((body_mask > 0.05).sum())})")

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
