"""
Soften the brow-ridge / upper-eyelid crease on a meta template so the area
above the eye is smooth and rounded (Meta-avatar "fun" look, no anatomical
socket shading).

Masked Laplacian smoothing of the body basis in the band between the upper
eyelid and the eyebrow line. Delta-preserving like stylize_meta_base.py's
neutral bake: the same displacement field D is applied to the basis AND every
shape key, so all 169 identity/animation deltas stay correct. Toon_Eyebrows
(floating brow mesh) follows via KNN-sampled D so the brows stay glued to the
skin. TearLine/EyeOcclusion/Eye are untouched — the mask fades to zero at the
eye opening.

Region is measured, never hardcoded: per-eye centers from CC_Base_Eye verts,
band top from the Toon_Eyebrows strip — works on both genders.

Usage:
  blender --background --python smooth_eye_socket.py -- \
      <in.blend> <out.blend> <Prefix> [strength 0..1, default 0.6]
"""
import bpy
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
blend_in, blend_out, prefix = argv[0], argv[1], argv[2]
strength = float(argv[3]) if len(argv) > 3 else 0.6
ITERS = max(1, int(round(20 * strength)))
LAM = 0.5

bpy.ops.wm.open_mainfile(filepath=blend_in)


def world_verts(obj):
    n = len(obj.data.vertices)
    co = np.zeros(n * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world)
    return co @ mw[:3, :3].T + mw[:3, 3]


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


body = bpy.data.objects[f"{prefix}_Body"]
eye = bpy.data.objects["CC_Base_Eye"]
brows = bpy.data.objects["Toon_Eyebrows"]

eye_w = world_verts(eye)
eye_centers = [eye_w[eye_w[:, 0] < 0].mean(axis=0),
               eye_w[eye_w[:, 0] >= 0].mean(axis=0)]
brow_w = world_verts(brows)
brow_top_z = brow_w[:, 2].max()
eye_z = float(np.mean([c[2] for c in eye_centers]))

bw = world_verts(body)
n = len(body.data.vertices)

# ---- mask: band between upper lid and brow top, per-eye lateral falloff
mask = np.zeros(n)
z_lo, z_hi = eye_z + 0.006, brow_top_z + 0.005
zm = smoothstep(z_lo, z_lo + 0.008, bw[:, 2]) * \
     (1.0 - smoothstep(z_hi - 0.006, z_hi, bw[:, 2]))
for c in eye_centers:
    lat = 1.0 - smoothstep(0.028, 0.045, np.abs(bw[:, 0] - c[0]))
    front = 1.0 - smoothstep(c[1] + 0.035, c[1] + 0.055, bw[:, 1])
    mask = np.maximum(mask, zm * lat * front)
active = mask > 1e-4
print(f"[socket] mask: {active.sum()} verts, band z [{z_lo:.3f},{z_hi:.3f}]")

# ---- adjacency from edges (local-space smoothing; mask is world-derived)
me = body.data
co0 = np.zeros(n * 3)
me.vertices.foreach_get("co", co0)
co0 = co0.reshape(-1, 3)
nbr = [[] for _ in range(n)]
for e in me.edges:
    a, b = e.vertices
    nbr[a].append(b)
    nbr[b].append(a)
idx = np.where(active)[0]
neighbors = [np.array(nbr[i]) for i in idx]

co = co0.copy()
for _ in range(ITERS):
    means = np.array([co[nb].mean(axis=0) for nb in neighbors])
    co[idx] += (LAM * mask[idx])[:, None] * (means - co[idx])

D = (co - co0).reshape(-1)
max_d = np.abs(co - co0).max()
print(f"[socket] {ITERS} iters, max displacement {max_d*10:.2f} mm (local cm units)")

# ---- apply D to basis + every shape key (delta-preserving)
kbs = me.shape_keys.key_blocks
for kb in kbs:
    buf = np.zeros(n * 3)
    kb.data.foreach_get("co", buf)
    kb.data.foreach_set("co", (buf + D).astype(np.float32))
buf = np.zeros(n * 3)
me.vertices.foreach_get("co", buf)
me.vertices.foreach_set("co", (buf + D).astype(np.float32))
me.update()
print(f"[socket] baked into {body.name} ({len(kbs)} keys shifted)")

# ---- eyebrows follow: KNN(4) inverse-distance sample of D from body verts
Dv = D.reshape(-1, 3)
moved = np.where(np.abs(Dv).sum(axis=1) > 1e-9)[0]
if len(moved):
    bn = len(brows.data.vertices)
    bco = np.zeros(bn * 3)
    brows.data.vertices.foreach_get("co", bco)
    bco = bco.reshape(-1, 3)
    # both meshes share armature space; compare in body local via world
    mw_body = np.array(body.matrix_world)
    mw_brow = np.array(brows.matrix_world)
    bco_w = bco @ mw_brow[:3, :3].T + mw_brow[:3, 3]
    body_w = co0 @ mw_body[:3, :3].T + mw_body[:3, 3]
    src = body_w[moved]
    # displacement in world space: world_D = body_rot @ D_local
    Dw = Dv @ mw_body[:3, :3].T
    Dbw = np.zeros_like(bco)
    for i, p in enumerate(bco_w):
        d2 = ((src - p) ** 2).sum(axis=1)
        k = np.argsort(d2)[:4]
        if d2[k[0]] > 0.02 ** 2:      # >2cm from any moved skin: ignore
            continue
        w = 1.0 / (np.sqrt(d2[k]) + 1e-6)
        Dbw[i] = (Dw[moved][k] * (w / w.sum())[:, None]).sum(axis=0)
    # world delta -> brow local
    inv = np.linalg.inv(mw_brow[:3, :3])
    Db_final = (Dbw @ inv.T).reshape(-1)
    bkbs = brows.data.shape_keys.key_blocks if brows.data.shape_keys else []
    for kb in bkbs:
        buf = np.zeros(bn * 3)
        kb.data.foreach_get("co", buf)
        kb.data.foreach_set("co", (buf + Db_final).astype(np.float32))
    buf = np.zeros(bn * 3)
    brows.data.vertices.foreach_get("co", buf)
    brows.data.vertices.foreach_set("co", (buf + Db_final).astype(np.float32))
    brows.data.update()
    print(f"[socket] eyebrows followed ({int((np.abs(Dbw).sum(axis=1) > 1e-9).sum())} verts)")

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("Saved:", blend_out)
