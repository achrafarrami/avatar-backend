"""
Garment factory library for the pro Meta-style wardrobe.

Professional-quality procedural tailoring on top of the meta (toon) bases:
  - body-region shells, unsubdivided to game density, relaxed to kill anatomy
  - per-region drape inflation along smoothed normals
  - rolled TRIM geometry swept around every opening (collars/cuffs/hems/brims)
    — thickness is shown where the eye looks for it, interiors stay single
    sided (doubleSided material), exactly like production game clothing
  - ring-lofted skirts with pleats (skirts must not hug legs)
  - constructed details: soles, waistbands, buttons, hood rolls, drawstrings
  - matte fabric PBR + per-vertex baked AO (Cycles -> COLOR_0)
  - inherited skin weights, weight transfer for constructed geometry
  - body-morph follower shape keys sampled from the body (KNN)

Used by build_pro_wardrobe.py — no __main__ here.
"""
import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# ------------------------------------------------------------------ scene
def get_rig(prefix):
    body = bpy.data.objects[f"{prefix}_Body"]
    arm = bpy.data.objects[f"{prefix}_Armature"]
    return body, arm


def body_arrays(body):
    me = body.data
    n = len(me.vertices)
    co = np.zeros(n * 3)
    src = me.shape_keys.key_blocks["Basis"].data if me.shape_keys else me.vertices
    src.foreach_get("co", co)
    return co.reshape(n, 3)


def vg_weights(body, names):
    idx = {g.index for g in body.vertex_groups if g.name in names}
    w = np.zeros(len(body.data.vertices))
    for v in body.data.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w


# ------------------------------------------------------------- mesh utils
def np_verts(obj):
    n = len(obj.data.vertices)
    co = np.zeros(n * 3)
    obj.data.vertices.foreach_get("co", co)
    return co.reshape(n, 3)


def set_verts(obj, V):
    obj.data.vertices.foreach_set("co", V.reshape(-1).astype(np.float32))
    obj.data.update()


def adjacency(obj):
    ne = len(obj.data.edges)
    e = np.zeros(ne * 2, dtype=np.int64)
    obj.data.edges.foreach_get("vertices", e)
    return e.reshape(ne, 2)


def extract_shell(body, mask, name):
    obj = body.copy()
    obj.data = body.data.copy()
    obj.name = obj.data.name = name
    bpy.context.scene.collection.objects.link(obj)
    mw = body.matrix_world.copy()
    obj.parent = None                 # body.copy() keeps the armature parent;
    obj.matrix_world = mw             # unparent but hold the world transform
    obj.shape_key_clear()
    obj.modifiers.clear()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    doomed = [v for v in bm.verts if mask[v.index] < 0.5]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.clear()
    return obj


def unsubdivide(obj, iterations=2):
    mod = obj.modifiers.new("Un", 'DECIMATE')
    mod.decimate_type = 'UNSUBDIV'
    mod.iterations = iterations
    with bpy.context.temp_override(object=obj, active_object=obj,
                                   selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier="Un")


def boundary_loops(obj):
    """Ordered boundary loops as lists of vert indices."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bedges = [e for e in bm.edges if len(e.link_faces) == 1]
    nbr = {}
    for e in bedges:
        a, b = e.verts[0].index, e.verts[1].index
        nbr.setdefault(a, []).append(b)
        nbr.setdefault(b, []).append(a)
    seen, loops = set(), []
    for start in nbr:
        if start in seen or len(nbr[start]) != 2:
            continue
        loop, cur, prev = [start], start, None
        while True:
            seen.add(cur)
            nxt = [x for x in nbr.get(cur, []) if x != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == start:
                break
            if cur in seen:
                break
            loop.append(cur)
        if len(loop) > 4:
            loops.append(loop)
    bm.free()
    return loops


def relax(obj, iters=8, lam=0.5, boundary_iters=4, only=None):
    """Interior Laplacian smoothing; boundary loops smoothed along the loop
    so openings become clean curves instead of jagged mesh cuts.
    only: optional bool mask — verts outside it are pinned."""
    V = np_verts(obj)
    E = adjacency(obj)
    n = len(V)
    bset = set()
    loops = boundary_loops(obj)
    for lp in loops:
        bset.update(lp)
    interior = np.array([i not in bset for i in range(n)])
    if only is not None:
        interior &= np.asarray(only, dtype=bool)
    for _ in range(iters):
        acc = np.zeros_like(V)
        cnt = np.zeros(n)
        for a, b in ((0, 1), (1, 0)):
            np.add.at(acc, E[:, a], V[E[:, b]])
            np.add.at(cnt, E[:, a], 1)
        ok = interior & (cnt > 0)
        V[ok] = V[ok] * (1 - lam) + acc[ok] / cnt[ok, None] * lam
    for _ in range(boundary_iters):
        for lp in loops:
            P = V[lp]
            V[lp] = P * 0.4 + (np.roll(P, 1, 0) + np.roll(P, -1, 0)) * 0.3
    set_verts(obj, V)
    return V


def smoothed_normals(obj, passes=2):
    V = np_verts(obj)
    me = obj.data
    n = len(V)
    N = np.zeros((n, 3))
    for p in me.polygons:
        vs = list(p.vertices)
        nrm = np.array(p.normal)
        for vi in vs:
            N[vi] += nrm
    E = adjacency(obj)
    for _ in range(passes):
        acc = N.copy()
        for a, b in ((0, 1), (1, 0)):
            np.add.at(acc, E[:, a], N[E[:, b]])
        N = acc
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-9)[:, None]
    return N


def inflate(obj, amount):
    """amount: scalar or per-vert array (cm), along smoothed normals."""
    V = np_verts(obj)
    N = smoothed_normals(obj)
    amt = np.asarray(amount).reshape(-1, 1) if np.ndim(amount) else amount
    set_verts(obj, V + N * amt)


def make_bvh(body):
    bco = body_arrays(body)
    return BVHTree.FromPolygons([Vector(v) for v in bco],
                                [tuple(p.vertices) for p in body.data.polygons])


def push_out(obj, bvh, clear=0.45, rounds=2):
    """Push garment verts out of the body, relaxing between rounds so the
    projection doesn't leave spikes (same recipe proven on the realistic
    clothing importer)."""
    V = np_verts(obj)
    E = adjacency(obj)
    n = len(V)

    def one_pass():
        moved = np.zeros(n, dtype=bool)
        for i in range(n):
            loc, nrm, _, dist = bvh.find_nearest(Vector(V[i]))
            if loc is None or dist > 4.0:
                continue
            if (Vector(V[i]) - loc).dot(nrm) < clear:
                V[i] = list(loc + nrm * clear)
                moved[i] = True
        return moved

    moved = one_pass()
    for _ in range(rounds - 1):
        acc = np.zeros_like(V)
        cnt = np.zeros(n)
        for a, b in ((0, 1), (1, 0)):
            np.add.at(acc, E[:, a], V[E[:, b]])
            np.add.at(cnt, E[:, a], 1)
        ok = moved & (cnt > 0)
        V[ok] = V[ok] * 0.5 + acc[ok] / cnt[ok, None] * 0.5
        moved = one_pass()
    # face-center pass: with coarse quads a face's flat span can cross a
    # curved limb even when every vert clears it — test centers and lift the
    # whole face out by the deficit
    polys = [list(p.vertices) for p in obj.data.polygons]
    for _ in range(3):
        fixed = 0
        for pv in polys:
            c = V[pv].mean(0)
            loc, nrm, _, dist = bvh.find_nearest(Vector(c))
            if loc is None or dist > 4.0:
                continue
            d = (Vector(c) - loc).dot(nrm)
            if d < clear * 0.8:
                V[pv] += np.array(nrm) * (clear * 0.8 - d)
                fixed += 1
        if not fixed:
            break
    set_verts(obj, V)


# ------------------------------------------------------------------ trims
def loop_frame(V, loop):
    """Best-fit plane normal (axis) + centroid of a boundary loop."""
    P = V[loop]
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    axis = vt[2]
    return c, axis


def trim_roll(obj, loop, profile, axis_dir=None, scale=None, weight_src=True):
    """Sweep a rolled-trim profile around a boundary loop.

    profile: [(d_out, d_axis), ...] in cm. d_out pushes away from the loop
    centroid (in the loop plane), d_axis moves along the loop axis
    (positive = the side the axis points to). scale: optional per-loop-vert
    array multiplying the profile (e.g. hood roll big at back, 0 at front).
    Copies each base vert's vgroup weights to its swept verts.
    """
    me = obj.data
    V = np_verts(obj)
    c, axis = loop_frame(V, loop)
    if axis_dir is not None:
        if float(np.dot(axis, axis_dir)) < 0:
            axis = -axis
    k = len(loop)
    sc = np.ones(k) if scale is None else np.asarray(scale)
    P = V[loop]
    out = P - c
    out -= np.outer(out @ axis, axis)
    out /= np.maximum(np.linalg.norm(out, axis=1), 1e-9)[:, None]

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    base = [bm.verts[i] for i in loop]
    prev = base
    rings = []
    for d_out, d_ax in profile:
        ring = []
        for j in range(k):
            pos = P[j] + out[j] * d_out * sc[j] + axis * d_ax * sc[j]
            ring.append(bm.verts.new(pos))
        rings.append(ring)
        for j in range(k):
            j2 = (j + 1) % k
            try:
                bm.faces.new((prev[j], prev[j2], ring[j2], ring[j]))
            except ValueError:
                pass
        prev = ring
    bm.verts.index_update()
    new_idx = [[v.index for v in ring] for ring in rings]
    bm.to_mesh(me)
    bm.free()
    if weight_src:
        for ring in new_idx:
            for j, vi in enumerate(ring):
                src = me.vertices[loop[j]]
                for g in src.groups:
                    obj.vertex_groups[g.group].add([vi], g.weight, 'REPLACE')
    me.update()
    return new_idx


def back_scale(V, loop, front=-1.0, power=1.5, floor=0.0):
    """Per-loop-vert factor: 1 at the back (+y), floor at the front."""
    P = V[loop]
    c = P.mean(0)
    d = P - c
    ang = d[:, 1] * (1 if front < 0 else -1)     # +y = back for CC avatars
    f = (ang - ang.min()) / max(ang.max() - ang.min(), 1e-9)
    return floor + (1 - floor) * f ** power


# ------------------------------------------------------------------ lofts
def loft_rings(obj_name, rings, close=False, flip=False, matrix=None):
    """rings: list of (Npts,3) arrays, equal length. Returns new object.
    matrix declares which space the ring coords live in (pass the body's
    matrix_world when building in template-cm space)."""
    me = bpy.data.meshes.new(obj_name)
    obj = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(obj)
    if matrix is not None:
        obj.matrix_world = matrix.copy()
    bm = bmesh.new()
    prev = None
    for ring in rings:
        cur = [bm.verts.new(p) for p in ring]
        if prev:
            k = len(cur)
            for j in range(k):
                j2 = (j + 1) % k
                quad = (prev[j], prev[j2], cur[j2], cur[j])
                bm.faces.new(quad[::-1] if flip else quad)
        prev = cur
    if close and prev:
        bm.faces.new(prev[::-1] if not flip else prev)
    bm.to_mesh(me)
    bm.free()
    return obj


def grid_mesh(obj_name, rows, matrix=None):
    """Open quad grid from a list of equal-length point rows (no wrap)."""
    me = bpy.data.meshes.new(obj_name)
    obj = bpy.data.objects.new(obj_name, me)
    bpy.context.scene.collection.objects.link(obj)
    if matrix is not None:
        obj.matrix_world = matrix.copy()
    bm = bmesh.new()
    grid = [[bm.verts.new(tuple(p)) for p in row] for row in rows]
    for r in range(len(grid) - 1):
        for j in range(len(grid[0]) - 1):
            bm.faces.new((grid[r][j], grid[r][j + 1],
                          grid[r + 1][j + 1], grid[r + 1][j]))
    bm.to_mesh(me)
    bm.free()
    return obj


def circle_ring(center, rx, ry, n=24, pleat_amp=0.0, pleat_n=12, phase=0.0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        r = 1.0 + pleat_amp * (abs(math.sin(pleat_n * t / 2 + phase)) - 0.5)
        pts.append((center[0] + math.cos(t) * rx * r,
                    center[1] + math.sin(t) * ry * r,
                    center[2]))
    return np.array(pts)


def body_radius_at(bco, z, slab=1.5):
    sel = np.abs(bco[:, 2] - z) < slab
    if not sel.any():
        return 10.0, (0.0, 0.0)
    P = bco[sel]
    cx, cy = P[:, 0].mean(), P[:, 1].mean()
    r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
    return float(np.percentile(r, 98)), (float(cx), float(cy))


# ------------------------------------------------------------- hull / sole
def convex_hull_2d(pts):
    pts = sorted(set(map(tuple, np.round(pts, 3))))
    if len(pts) < 3:
        return np.array(pts)
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) > 1 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) > 1 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])


def smooth_outline(pts, iters=2, n_out=28):
    P = pts.copy()
    for _ in range(iters):                       # Chaikin corner cutting
        Q = []
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            Q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        P = np.array(Q)
    # resample to n_out by arc length
    d = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
    t = np.concatenate([[0], np.cumsum(d)])
    tt = np.linspace(0, t[-1], n_out, endpoint=False)
    out = []
    for x in tt:
        i = int(np.searchsorted(t, x).clip(1, len(P))) - 1
        f = (x - t[i]) / max(d[i % len(d)], 1e-9)
        out.append(P[i] * (1 - f) + P[(i + 1) % len(P)] * f)
    return np.array(out)


# -------------------------------------------------------------- materials
PALETTE = {  # research_report.md — Meta reference palette (sRGB hex)
    "rose": "#c98d80", "terracotta": "#b0563b", "plaid_red": "#8f3a34",
    "navy": "#3a4a68", "denim": "#4a5a78", "charcoal": "#2e2f35",
    "cream": "#e5ded2", "slate": "#5c6274", "blush": "#e8b4ac",
    "leather": "#26262a", "forest": "#3f5a43", "mustard": "#c8963e",
    "heather": "#8a8d96", "white": "#e9e9ec", "sand": "#cdb894",
    "brown": "#5a4234", "black": "#232327",
}

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hex_lin(h):
    h = PALETTE.get(h, h)
    return tuple(_lin(int(h[i:i+2], 16) / 255) for i in (1, 3, 5)) + (1.0,)


def fabric_material(name, color, rough=0.85, sheen=0.0, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = hex_lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    # NO sheen: KHR_materials_sheen exports a full-white sheenColorFactor
    # that renders as a milky translucent film on re-import — Meta's look is
    # pure matte anyway
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.0
    # Export contract: Base Color stays a CONSTANT (glTF baseColorFactor);
    # the baked AO lives in the mesh's sole color attribute, which exports
    # as COLOR_0 and multiplies baseColor in every compliant viewer.
    # (A VertexColor->Mix->BaseColor node chain exports as WHITE — verified.)
    mat.use_backface_culling = False
    return mat


def keep_only_ao_attribute(me):
    """Body-derived shells inherit the CC body's color attributes; glTF
    multiplies only COLOR_0, so AO must be the one and only layer."""
    doomed = [ca.name for ca in me.color_attributes if ca.name != "AO"]
    for nm in doomed:
        me.color_attributes.remove(me.color_attributes[nm])
    if "AO" in me.color_attributes:
        me.color_attributes.active_color = me.color_attributes["AO"]


def bake_ao(obj, occluders, strength=0.5, samples=16):
    """Cycles AO -> 'AO' color attribute (exports as COLOR_0 multiplier)."""
    me = obj.data
    if "AO" not in me.color_attributes:
        me.color_attributes.new("AO", 'BYTE_COLOR', 'CORNER')
    me.color_attributes.active_color = me.color_attributes["AO"]
    scene = bpy.context.scene
    prev_engine = scene.render.engine
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.device = 'CPU'
    hidden = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and o is not obj and o not in occluders:
            if not o.hide_render:
                hidden.append(o)
                o.hide_render = True
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        col = me.color_attributes["AO"]
        n = len(col.data)
        buf = np.zeros(n * 4)
        col.data.foreach_get("color", buf)
        buf = buf.reshape(n, 4)
        ao = buf[:, :3].mean(1)
        soft = (1 - strength) + strength * ao     # lift the floor
        buf[:, 0] = buf[:, 1] = buf[:, 2] = soft
        buf[:, 3] = 1.0
        col.data.foreach_set("color", buf.reshape(-1))
    except Exception as e:
        print(f"[ao] bake skipped for {obj.name}: {e}")
    for o in hidden:
        o.hide_render = False
    scene.render.engine = prev_engine
    me.update()


# ------------------------------------------------------ weights & morphs
def transfer_missing_weights(obj, body, bvh):
    """Copy weights from the nearest body vertex to any garment vert that
    has none yet (constructed geometry: soles, lofts, buttons, panels)."""
    need = [v.index for v in obj.data.vertices if not v.groups]
    if not need:
        return
    bco = body_arrays(body)
    name_by_idx = {g.index: g.name for g in body.vertex_groups}
    V = np_verts(obj)
    for vi in need:
        loc, nrm, pidx, dist = bvh.find_nearest(Vector(V[vi]))
        if pidx is None:
            continue
        poly = body.data.polygons[pidx]
        best = min(poly.vertices,
                   key=lambda b: float(np.linalg.norm(bco[b] - V[vi])))
        for g in body.data.vertices[best].groups:
            if g.weight < 1e-4:
                continue
            gname = name_by_idx[g.group]
            vg = obj.vertex_groups.get(gname)
            if vg is None:
                vg = obj.vertex_groups.new(name=gname)
            vg.add([vi], g.weight, 'REPLACE')


def finalize_weights(obj, body, arm, bvh):
    transfer_missing_weights(obj, body, bvh)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.vertex_group_limit_total(limit=4, group_select_mode='ALL')
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',
                                              lock_active=False)
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()


def add_morph_followers(obj, body, key_names, k=4, min_delta=0.05):
    """Sample the body's shape-key deltas at each garment vert (inverse
    distance KNN) so identity/body morphs deform the garment too."""
    if not body.data.shape_keys:
        return []
    bco = body_arrays(body)
    V = np_verts(obj)
    # KNN via chunked brute force (verts are few thousand)
    idx = np.empty((len(V), k), dtype=np.int64)
    wgt = np.empty((len(V), k))
    for i in range(0, len(V), 512):
        d = np.linalg.norm(V[i:i+512, None, :] - bco[None, :, :], axis=2)
        part = np.argpartition(d, k, axis=1)[:, :k]
        dd = np.take_along_axis(d, part, 1)
        idx[i:i+512] = part
        wgt[i:i+512] = 1.0 / np.maximum(dd, 1e-3)
    wgt /= wgt.sum(1)[:, None]
    added = []
    nb = len(bco)
    for kb in body.data.shape_keys.key_blocks:
        if kb.name not in key_names:
            continue
        kco = np.zeros(nb * 3)
        kb.data.foreach_get("co", kco)
        delta = kco.reshape(nb, 3) - bco
        gd = (delta[idx] * wgt[..., None]).sum(1)
        if np.abs(gd).max() < min_delta:
            continue
        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis", from_mix=False)
        sk = obj.shape_key_add(name=kb.name, from_mix=False)
        sk.slider_min, sk.slider_max = kb.slider_min, kb.slider_max
        buf = (V + gd).reshape(-1).astype(np.float32)
        sk.data.foreach_set("co", buf)
        added.append(kb.name)
    return added
