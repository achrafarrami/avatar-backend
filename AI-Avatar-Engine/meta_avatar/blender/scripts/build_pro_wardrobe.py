"""
Build the professional Meta-style wardrobe on the meta (toon) bases.

Every garment is tailored by garment_factory.py (relaxed shells, drape
inflation, rolled trims at all openings, lofted pleated skirts, constructed
soles/collars/details, matte fabric PBR + baked vertex AO, inherited
weights, body-morph follower keys) and exported GLB (+ .blend/.fbx/QA
renders under output/wardrobe_pro/<id>/).

Usage:
  blender --background --python build_pro_wardrobe.py -- <repo_root> all
  blender --background --python build_pro_wardrobe.py -- <repo_root> tshirt hoodie
"""
import bpy
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import garment_factory as gf

argv = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.abspath(argv[0])
WANTED = argv[1:]
ENG = os.path.join(ROOT, "AI-Avatar-Engine")
SHARED = os.path.join(ENG, "assets", "shared")
SANDBOX = os.path.join(ENG, "frontend", "threejs-viewer", "public", "wardrobe")
OUT = os.path.join(ENG, "output", "wardrobe_pro")
TPL = {"male": os.path.join(ENG, "meta_avatar", "blender", "base", "meta_male.blend"),
       "female": os.path.join(ENG, "meta_avatar", "blender", "base", "meta_female.blend")}
PREFIX = {"male": "MetaMale", "female": "MetaFemale"}

# ------------------------------------------------------------------ recipes
# kind: top | pants | shoe | dress | hijab | scarf | cap | beanie | glasses
G = {
    "tshirt":        dict(kind="top", label="T-Shirt", color="cream", sleeves=0.45,
                          inflate=1.1, collar=0.5, exist=True),
    "shirt_short":   dict(kind="top", label="Short Sleeve Shirt", color="forest",
                          sleeves=0.5, inflate=0.9, collar=1.0, buttons=5, exist=False),
    "shirt_long":    dict(kind="top", label="Long Sleeve Shirt", color="plaid_red",
                          sleeves=1.0, inflate=0.9, collar=1.0, buttons=5, exist=False),
    "hoodie":        dict(kind="top", label="Hoodie", color="rose", sleeves=1.0,
                          inflate=2.0, hood=True, pocket=True, strings=True,
                          hip=0.55, hem=1.5, exist=True),
    "sweater":       dict(kind="top", label="Sweater", color="mustard", sleeves=1.0,
                          inflate=1.7, collar=0.9, sheen=0.45, hip=0.4,
                          hem=1.5, exist=False),
    "suit_jacket":   dict(kind="top", label="Suit Jacket", color="#2e3a54",
                          sleeves=1.0, inflate=1.3, lapel=True, buttons=2,
                          shirt_v=True, hip=0.65, hem=0.5, rough=0.7, exist=False),
    "jeans":         dict(kind="pants", label="Jeans", color="denim", length=1.0,
                          inflate=1.0, cuff=True, exist=True),
    "pants_casual":  dict(kind="pants", label="Casual Pants", color="sand",
                          length=1.0, inflate=1.15, exist=False),
    "suit_pants":    dict(kind="pants", label="Suit Pants", color="navy",
                          length=1.0, inflate=1.05, rough=0.7, exist=False),
    "shorts":        dict(kind="pants", label="Shorts", color="slate", length=0.42,
                          inflate=1.1, cuff=True, exist=True),
    "sneakers":      dict(kind="shoe", label="Sneakers", color="white",
                          sole_h=1.7, sole_color="cream", exist=True),
    "boots":         dict(kind="shoe", label="Boots", color="brown", sole_h=2.1,
                          shaft=0.55, sole_color="black", rough=0.55,
                          hole_lo=0.62, exist=False),
    "dress_shoes":   dict(kind="shoe", label="Dress Shoes", color="black",
                          sole_h=1.0, rough=0.4, sole_color="charcoal",
                          toe_ext=1.8, instep_pad=-0.5, hole_lo=0.28,
                          hole_span=0.5, exist=False),
    "dress":         dict(kind="dress", label="Dress", color="rose",
                          gender="female", exist=False),
    "hijab":         dict(kind="hijab", label="Hijab", color="#8f4a44",
                          gender="female", exist=False),
    "scarf":         dict(kind="scarf", label="Scarf", color="terracotta", exist=False),
    "cap":           dict(kind="cap", label="Cap", color="terracotta", exist=True),
    "beanie":        dict(kind="beanie", label="Beanie", color="heather", exist=True),
    "glasses_round": dict(kind="glasses", label="Round Glasses", color="black",
                          shape=2.0, exist=True),
    "glasses_square": dict(kind="glasses", label="Square Glasses", color="brown",
                          shape=4.0, exist=True),
}
SLOT = {"top": ("top", "clothes"), "pants": ("pants", "clothes"),
        "shoe": ("shoes", "shoes"), "dress": ("top", "clothes"),
        "hijab": ("hat", "hats"), "scarf": ("neck", "accessories"),
        "cap": ("hat", "hats"), "beanie": ("hat", "hats"),
        "glasses": ("glasses", "glasses")}

ids = list(G) if WANTED == ["all"] else WANTED

# ---------------------------------------------------------------- template
class Rig:
    def __init__(self, gender):
        bpy.ops.wm.open_mainfile(filepath=TPL[gender])
        self.body, self.arm = gf.get_rig(PREFIX[gender])
        self.bco = gf.body_arrays(self.body)
        b = self.arm.data.bones
        def bz(n): return b[n].head_local.z
        self.neck_z = bz("CC_Base_NeckTwist01")
        self.waist_z = bz("CC_Base_Waist")
        self.hip_z = bz("CC_Base_Hip")
        self.knee_z = bz("CC_Base_L_KneeShareBone")
        self.ankle_z = bz("CC_Base_L_Foot")
        self.sh = np.array(b["CC_Base_L_Upperarm"].head_local)
        self.el = np.array(b["CC_Base_L_Forearm"].head_local)
        self.wr = np.array(b["CC_Base_L_Hand"].head_local)
        self.head_z = bz("CC_Base_Head")
        w = lambda names: gf.vg_weights(self.body, names)
        L, R = "CC_Base_L_", "CC_Base_R_"
        self.torso = w(["CC_Base_Spine01", "CC_Base_Spine02", "CC_Base_Waist",
                        L+"Clavicle", R+"Clavicle", L+"RibsTwist", R+"RibsTwist",
                        L+"Breast", R+"Breast"])
        self.hipw = w(["CC_Base_Hip", "CC_Base_Pelvis"])
        self.uarm = w([L+"Upperarm", R+"Upperarm", L+"UpperarmTwist01",
                       R+"UpperarmTwist01", L+"UpperarmTwist02", R+"UpperarmTwist02"])
        self.farm = w([L+"Forearm", R+"Forearm", L+"ForearmTwist01", R+"ForearmTwist01",
                       L+"ForearmTwist02", R+"ForearmTwist02",
                       L+"ElbowShareBone", R+"ElbowShareBone"])
        self.hand = w([g.name for g in self.body.vertex_groups
                       if "_Hand" in g.name or "Finger" in g.name or "Thumb" in g.name
                       or "Index" in g.name or "Mid" in g.name and "Toe" not in g.name
                       or "Ring" in g.name or "Pinky" in g.name and "Toe" not in g.name])
        self.neckw = w(["CC_Base_NeckTwist01", "CC_Base_NeckTwist02", "CC_Base_Head"])
        self.leg = w([L+"Thigh", R+"Thigh", L+"ThighTwist01", R+"ThighTwist01",
                      L+"ThighTwist02", R+"ThighTwist02", L+"Calf", R+"Calf",
                      L+"CalfTwist01", R+"CalfTwist01", L+"CalfTwist02", R+"CalfTwist02",
                      L+"KneeShareBone", R+"KneeShareBone"])
        self.foot = w([L+"Foot", R+"Foot", L+"ToeBase", R+"ToeBase",
                       L+"ToeBaseShareBone", R+"ToeBaseShareBone"] +
                      [g.name for g in self.body.vertex_groups if "Toe1" in g.name])
        # mirror-safe arm parameter: 0 at shoulder, 1 at elbow, ~2 at wrist,
        # measured on |x| so it works for BOTH arms (bone-projection on the
        # left arm alone gave every right-arm vert a negative t)
        sx, ex = abs(self.sh[0]), abs(self.el[0])
        self.arm_t = np.clip((np.abs(self.bco[:, 0]) - sx) / max(ex - sx, 1e-3),
                             -2, 3)
        self.bvh = gf.make_bvh(self.body)
        ne = len(self.body.data.edges)
        e = np.zeros(ne * 2, dtype=np.int64)
        self.body.data.edges.foreach_get("vertices", e)
        self.body_edges = e.reshape(ne, 2)

    def close_mask(self, mask, iters=2):
        """Fill pinholes: a vert joins the mask if >=4 neighbors are in."""
        m = mask.copy()
        for _ in range(iters):
            cnt = np.zeros(len(m))
            for a, b in ((0, 1), (1, 0)):
                np.add.at(cnt, self.body_edges[:, a],
                          m[self.body_edges[:, b]].astype(float))
            m = m | (cnt >= 4)
        return m

    def arm_mask(self, frac):
        full = (self.uarm > 0.3) | (self.farm > 0.3)
        lim = self.arm_t < (frac * 2.0 if frac >= 1.0 else frac)
        return full & lim & (self.hand < 0.3)


def classify_loops(obj):
    """-> dict: neck / hem / cuffs(list) / others by centroid geometry."""
    V = gf.np_verts(obj)
    loops = gf.boundary_loops(obj)
    info = []
    for lp in loops:
        c = V[lp].mean(0)
        info.append((lp, c))
    out = {"cuffs": [], "others": []}
    if not info:
        return out
    info.sort(key=lambda t: -t[1][2])
    for lp, c in info:
        if abs(c[0]) > 8:
            out["cuffs"].append(lp)
        elif "neck" not in out and c[2] > (info[0][1][2] - 6):
            out["neck"] = lp
        elif "hem" not in out or c[2] < V[out["hem"]].mean(0)[2]:
            out.setdefault("hem", lp)
        else:
            out["others"].append(lp)
    return out


# ------------------------------------------------------------------ builds
def build_top(rig, gid, cfg):
    hipf = cfg.get("hip", 0.45)
    hem_z = rig.hip_z + cfg.get("hem", 2.0)
    mask = ((rig.torso + rig.hipw * hipf > 0.3) | rig.arm_mask(cfg["sleeves"])) \
        & (rig.neckw < 0.4)
    mask = rig.close_mask(mask) & (rig.bco[:, 2] > hem_z)
    obj = gf.extract_shell(rig.body, mask, gid)
    gf.unsubdivide(obj, 2)
    gf.relax(obj, iters=7, lam=0.5)
    V = gf.np_verts(obj)
    amt = np.full(len(V), cfg["inflate"])
    lo, hi = V[:, 2].min(), V[:, 2].max()
    t = np.clip((V[:, 2] - lo) / max(hi - lo, 1), 0, 1)
    amt *= 0.85 + 0.45 * np.sin(np.pi * np.clip(t * 1.15, 0, 1))
    gf.inflate(obj, amt)
    gf.push_out(obj, rig.bvh, clear=0.5)
    lps = classify_loops(obj)
    if "neck" in lps:
        V = gf.np_verts(obj)
        if cfg.get("hood"):
            sc = gf.back_scale(V, lps["neck"], power=1.6, floor=0.12)
            gf.trim_roll(obj, lps["neck"],
                         [(1.6, 0.9), (2.6, -0.4), (1.4, -2.2), (0.2, -3.0)],
                         axis_dir=(0, 0, 1), scale=sc * 1.6)
        elif cfg.get("lapel"):
            back = gf.back_scale(V, lps["neck"], power=1.3, floor=0.0)
            sc = 0.35 + 1.35 * (1.0 - back)    # thin at the nape, deep at front
            gf.trim_roll(obj, lps["neck"],
                         [(1.2, 0.5), (2.0, -1.2), (1.2, -3.4), (0.2, -4.6)],
                         axis_dir=(0, 0, 1), scale=sc)
        else:
            c = cfg.get("collar", 0.6)
            prof = [(0.4 * c, 0.5 * c), (0.65 * c, -0.1 * c), (0.35 * c, -0.9 * c)] \
                if c <= 0.6 else \
                [(0.4, 0.9), (0.9, 0.3), (1.1, -1.0), (0.5, -1.9)]
            gf.trim_roll(obj, lps["neck"], prof, axis_dir=(0, 0, 1))
    for lp in lps["cuffs"]:
        V = gf.np_verts(obj)
        cx = V[lp].mean(0)
        ax = np.array([np.sign(cx[0]), 0.15, -0.6])
        gf.trim_roll(obj, lp, [(0.45, 0.15), (0.6, -0.55), (0.25, -1.15)],
                     axis_dir=ax / np.linalg.norm(ax))
    if "hem" in lps:
        gf.trim_roll(obj, lps["hem"], [(0.4, -0.15), (0.5, -0.8), (0.2, -1.35)],
                     axis_dir=(0, 0, -1))
    gf.push_out(obj, rig.bvh, clear=0.3, rounds=1)   # trim rolls off the skin
    apply_host_mat(obj, gid, cfg)
    if cfg.get("shirt_v"):
        # white dress-shirt triangle between the lapels: wide at the neck,
        # tapering to the sternum — a material island, no extra geometry
        shirt = gf.fabric_material(f"{gid}_shirt_mat", "white",
                                   rough=0.55, sheen=0.1)
        obj.data.materials.append(shirt)
        V2 = gf.np_verts(obj)
        for p in obj.data.polygons:
            c = V2[[v for v in p.vertices]].mean(0)
            w = 5.5 * np.clip((c[2] - (rig.neck_z - 13)) / 11.0, 0.0, 1.0) ** 0.8
            if c[1] < 0 and abs(c[0]) < w and c[2] > rig.neck_z - 13:
                p.material_index = 1
    parts = []
    if cfg.get("pocket"):
        parts.append(front_panel(rig, obj, gid + "_pocket",
                                 z0=rig.waist_z - 4, z1=rig.waist_z + 8,
                                 half_w=9, out=0.9))
    if cfg.get("strings"):
        parts += drawstrings(rig, obj, gid)
    if cfg.get("buttons") or cfg.get("shirt_v"):
        parts += buttons_and_panels(rig, obj, gid, cfg)
    return join_parts(obj, parts)


def front_panel(rig, host, name, z0, z1, half_w, out):
    """Kangaroo-pocket style rounded panel floating on the host front."""
    V = gf.np_verts(host)
    rows, cols = 5, 9
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    import bmesh as bmesh_mod
    bm = bmesh_mod.new()
    grid = []
    for r in range(rows):
        zr = z0 + (z1 - z0) * r / (rows - 1)
        row = []
        for cidx in range(cols):
            x = -half_w + 2 * half_w * cidx / (cols - 1)
            x *= 1.0 - 0.25 * (1 - r / (rows - 1))          # taper bottom
            sel = (np.abs(V[:, 0] - x) < 3) & (np.abs(V[:, 2] - zr) < 3) & (V[:, 1] < 0)
            y = V[sel, 1].min() - out if sel.any() else -10
            row.append(bm.verts.new((x, y, zr)))
        grid.append(row)
    for r in range(rows - 1):
        for cidx in range(cols - 1):
            bm.faces.new((grid[r][cidx], grid[r][cidx+1],
                          grid[r+1][cidx+1], grid[r+1][cidx]))
    bm.to_mesh(me)
    bm.free()
    ob.matrix_world = host.matrix_world.copy()    # data lives in template cm
    return ob


def drawstrings(rig, host, gid):
    out = []
    V = gf.np_verts(host)
    for sx in (-1, 1):
        top = np.array([sx * 3.2, 0, rig.neck_z - 2.0])
        sel = (np.abs(V[:, 0] - top[0]) < 2.5) & (np.abs(V[:, 2] - top[2]) < 2.5) & (V[:, 1] < 0)
        y = V[sel, 1].min() if sel.any() else -12
        rings = []
        for i in range(5):
            t = i / 4
            rings.append(gf.circle_ring((top[0], y - 0.5 - 0.3 * math.sin(t * 3),
                                         top[2] - 7.5 * t), 0.22, 0.22, n=6))
        ob = gf.loft_rings(f"{gid}_str{sx}", rings, close=True,
                           matrix=host.matrix_world)
        out.append(ob)
    return out


def buttons_and_panels(rig, host, gid, cfg):
    parts = []
    V = gf.np_verts(host)
    nb = cfg.get("buttons", 0)
    if cfg.get("lapel"):                   # suit: buttons sit below the V
        z_top, z_bot = rig.waist_z + 6, rig.waist_z + 2
    else:
        z_top, z_bot = rig.neck_z - 4.5, rig.waist_z + 2
    for i in range(nb):
        z = z_top + (z_bot - z_top) * i / max(nb - 1, 1)
        sel = (np.abs(V[:, 0]) < 2.0) & (np.abs(V[:, 2] - z) < 2.0) & (V[:, 1] < 0)
        if not sel.any():
            continue
        y = V[sel, 1].min()
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, segments=10, ring_count=6,
                                             location=(0, (y - 0.25) * 0.01, z * 0.01))
        b = bpy.context.object
        b.scale = (0.01, 0.004, 0.01)
        with bpy.context.temp_override(active_object=b, selected_editable_objects=[b]):
            bpy.ops.object.transform_apply(scale=True)
        b.scale = (1, 1, 1)
        b.name = f"{gid}_btn{i}"
        parts.append(b)
    return parts


def join_parts(host, parts):
    """Join parts into host, re-expressing each part's data in host local
    space (handles cm-space lofts and meter-space primitives alike)."""
    if parts:
        inv = host.matrix_world.inverted()
        for p in parts:
            p.data.transform(inv @ p.matrix_world)
            p.matrix_world = host.matrix_world.copy()
            if not p.data.materials and host.data.materials:
                p.data.materials.append(host.data.materials[0])   # else the
                # part lands in an empty slot and renders default white
        with bpy.context.temp_override(active_object=host,
                selected_editable_objects=[host] + parts,
                selected_objects=[host] + parts):
            bpy.ops.object.join()
    return host


def apply_host_mat(obj, gid, cfg):
    mat = gf.fabric_material(f"{gid}_mat", cfg["color"],
                             rough=cfg.get("rough", 0.85),
                             sheen=cfg.get("sheen", 0.25))
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.material_index = 0
    return mat


def build_pants(rig, gid, cfg):
    length = cfg["length"]
    z_cut = rig.hip_z - (rig.hip_z - rig.ankle_z - 1.5) * length
    mask = ((rig.hipw > 0.3) | (rig.leg > 0.3)) & (rig.foot < 0.4) \
        & (rig.torso < 0.45)
    mask = rig.close_mask(mask) & (rig.bco[:, 2] > z_cut)
    obj = gf.extract_shell(rig.body, mask, gid)
    gf.unsubdivide(obj, 2)
    gf.relax(obj, iters=4, lam=0.45)      # gentle: legs shrink fast under
    gf.inflate(obj, cfg["inflate"])       # Laplacian and mottle into the skin
    gf.push_out(obj, rig.bvh, clear=0.55)
    lps = classify_loops(obj)
    V = gf.np_verts(obj)
    legs = [lp for lp in ([lps.get("neck")] if lps.get("neck") else [])
            + ([lps.get("hem")] if lps.get("hem") else []) + lps["cuffs"]
            + lps["others"] if lp]
    legs.sort(key=lambda lp: V[lp].mean(0)[2])
    waist = legs[-1]
    hems = [lp for lp in legs[:-1] if len(lp) > 6][:2]
    gf.trim_roll(obj, waist, [(0.5, 0.6), (0.75, 1.4), (0.35, 2.1), (-0.15, 2.15)],
                 axis_dir=(0, 0, 1))
    for lp in hems:
        prof = [(0.5, -0.2), (0.65, -1.0), (0.3, -1.6)] if cfg.get("cuff") \
            else [(0.35, -0.3), (0.35, -1.0)]
        gf.trim_roll(obj, lp, prof, axis_dir=(0, 0, -1))
    gf.push_out(obj, rig.bvh, clear=0.4, rounds=1)
    apply_host_mat(obj, gid, cfg)
    return obj


def build_shoe(rig, gid, cfg):
    """Parametric shoe-last loft — the body's toes are tubes and no amount
    of smoothing turns them into a toe box (verified the ugly way)."""
    import bmesh as bmod
    parts = []
    host = None
    m = 16
    nr = 11
    for side in (-1, 1):
        side_sel = (rig.bco[:, 0] * side) > 0
        pts = rig.bco[(rig.foot > 0.25) & side_sel]
        toe_y, heel_y = pts[:, 1].min(), pts[:, 1].max()
        ground = pts[:, 2].min()
        hole_y = heel_y - (heel_y - toe_y) * cfg.get("hole_span", 0.42)
        hole_sin = cfg.get("hole_lo", 0.45)
        toe_ext = cfg.get("toe_ext", 1.5)
        bm = bmod.new()
        grid, flags = [], []
        for i in range(nr):
            t = i / (nr - 1)
            y = heel_y + 0.6 - (heel_y - toe_y + 0.6 + toe_ext) * t
            slab = pts[np.abs(pts[:, 1] - y) < 1.6]
            if len(slab) < 4:
                slab = pts[np.abs(pts[:, 1] - np.clip(y, toe_y, heel_y)) < 3.0]
            cx = slab[:, 0].mean()
            hw = (slab[:, 0].max() - slab[:, 0].min()) / 2 + 1.05
            top = np.percentile(slab[:, 2], 97) + 1.0 + cfg.get("instep_pad", 0.0)
            tip = np.clip((t - 0.86) / 0.14, 0, 1)
            heelt = np.clip((0.07 - t) / 0.07, 0, 1)
            hw *= max(1 - 0.6 * tip ** 1.6 - 0.5 * heelt, 0.2)
            top = ground + (top - ground) * max(1 - 0.45 * tip ** 1.4, 0.35)
            bot = ground + cfg["sole_h"] * 0.3
            zc, hh = (top + bot) / 2, max((top - bot) / 2, 0.4)
            row, frow = [], []
            for j in range(m):
                a = 2 * math.pi * j / m
                ce, se = math.cos(a), math.sin(a)
                x = cx + hw * math.copysign(abs(ce) ** 0.8, ce)
                z = zc + hh * math.copysign(abs(se) ** 0.85, se)
                row.append(bm.verts.new((x, y, z)))
                frow.append(se > hole_sin and y > hole_y)
            grid.append(row)
            flags.append(frow)
        for i in range(nr - 1):
            for j in range(m):
                j2 = (j + 1) % m
                if flags[i][j] or flags[i][j2] or flags[i+1][j] or flags[i+1][j2]:
                    continue
                bm.faces.new((grid[i][j], grid[i][j2],
                              grid[i+1][j2], grid[i+1][j]))
        for ring, at_toe in ((grid[-1], True), (grid[0], False)):
            c = bm.verts.new(np.mean([v.co for v in ring], axis=0))
            for j in range(m):
                j2 = (j + 1) % m
                tri = (ring[j], ring[j2], c) if at_toe else (ring[j2], ring[j], c)
                try:
                    bm.faces.new(tri)
                except ValueError:
                    pass
        me = bpy.data.meshes.new(f"{gid}_{side}")
        up = bpy.data.objects.new(f"{gid}_{side}", me)
        bpy.context.scene.collection.objects.link(up)
        bm.to_mesh(me)
        bm.free()
        up.matrix_world = rig.body.matrix_world.copy()
        apply_host_mat(up, gid, cfg)
        lps = gf.boundary_loops(up)
        if lps:
            Vv = gf.np_verts(up)
            ankle = max(lps, key=lambda lp: Vv[lp].mean(0)[2])
            gf.trim_roll(up, ankle, [(0.4, 0.35), (0.5, -0.25), (0.2, -0.8)],
                         axis_dir=(0, 0, 1), weight_src=False)
        gf.push_out(up, rig.bvh, clear=0.35, rounds=1)   # feet yaw outward a
        # touch — the axis-aligned last can clip a side wall without this
        if cfg.get("shaft"):
            z0 = rig.ankle_z + 0.5
            z1 = rig.knee_z - (rig.knee_z - rig.ankle_z) * (1 - cfg["shaft"])
            calf_pts = rig.bco[side_sel & (rig.foot < 0.3)]
            rings = []
            for i in range(5):
                z = z0 + (z1 - z0) * i / 4
                r, cc = gf.body_radius_at(calf_pts, z, 2.0)
                r = min(r, 5.4 if i < 2 else 7.0)   # no bell over the shoe
                rings.append(gf.circle_ring((cc[0], cc[1], z), r + 1.4, r + 1.4,
                                            n=m))
            sh = gf.loft_rings(f"{gid}_shaft{side}", rings,
                               matrix=rig.body.matrix_world)
            lp_sh = gf.boundary_loops(sh)
            Vs = gf.np_verts(sh)
            top_sh = max(lp_sh, key=lambda lp: Vs[lp].mean(0)[2])
            gf.trim_roll(sh, top_sh, [(0.45, 0.4), (0.55, -0.4), (0.2, -1.0)],
                         axis_dir=(0, 0, 1), weight_src=False)
            parts.append(sh)
        foot_pts = rig.bco[(rig.foot > 0.3) & side_sel]
        hull = gf.convex_hull_2d(foot_pts[:, :2])
        outline = gf.smooth_outline(hull, n_out=26)
        ctr = outline.mean(0)
        outline += (outline - ctr) * 0.10
        h = cfg["sole_h"]
        rings = []
        for zz, bulge in ((0.05, 0.99), (h * 0.45, 1.08), (h, 1.0)):
            ring = np.column_stack([ctr[0] + (outline[:, 0] - ctr[0]) * bulge,
                                    ctr[1] + (outline[:, 1] - ctr[1]) * bulge,
                                    np.full(len(outline), zz)])
            rings.append(ring)
        sole = gf.loft_rings(f"{gid}_sole{side}", rings[::-1], close=True,
                             matrix=rig.body.matrix_world)
        sole.data.materials.append(gf.fabric_material(
            f"{gid}_sole_mat", cfg.get("sole_color", "white"), rough=0.6, sheen=0.0))
        parts.append(sole)
        host = up if host is None else join_parts(host, [up])
    obj = join_parts(host, parts)
    obj.name = obj.data.name = gid
    return obj


def build_dress(rig, gid, cfg):
    mask = ((rig.torso + rig.hipw * 0.2 > 0.36) | rig.arm_mask(0.35)) & (rig.neckw < 0.4)
    obj = gf.extract_shell(rig.body, mask, gid)
    gf.unsubdivide(obj, 2)
    gf.relax(obj, iters=7)
    gf.inflate(obj, 1.2)
    gf.push_out(obj, rig.bvh, clear=0.5)
    lps = classify_loops(obj)
    if "neck" in lps:
        gf.trim_roll(obj, lps["neck"], [(0.35, 0.4), (0.55, -0.1), (0.3, -0.8)],
                     axis_dir=(0, 0, 1))
    for lp in lps["cuffs"]:
        V = gf.np_verts(obj)
        cx = V[lp].mean(0)
        ax = np.array([np.sign(cx[0]), 0.15, -0.6])
        gf.trim_roll(obj, lp, [(0.5, 0.1), (0.6, -0.6), (0.25, -1.1)],
                     axis_dir=ax / np.linalg.norm(ax))
    z0 = rig.waist_z + 1
    z1 = rig.knee_z + 6
    r0, c0 = gf.body_radius_at(rig.bco, rig.hip_z, 2.5)
    rings = []
    nseg = 28
    for i in range(9):
        t = i / 8
        z = z0 + (z1 - z0) * t
        r = r0 + 1.6 + 7.5 * t ** 1.25
        rings.append(gf.circle_ring((0, c0[1], z), r, r * 0.86, n=nseg,
                                    pleat_amp=0.16 * t, pleat_n=14))
    skirt = gf.loft_rings(gid + "_skirt", rings, matrix=rig.body.matrix_world)
    lpsk = gf.boundary_loops(skirt)
    lpsk.sort(key=lambda lp: gf.np_verts(skirt)[lp].mean(0)[2])
    gf.trim_roll(skirt, lpsk[0], [(0.35, -0.3), (0.45, -0.9), (0.2, -1.4)],
                 axis_dir=(0, 0, -1), weight_src=False)
    band_r = r0 + 1.7
    band = gf.loft_rings(gid + "_band",
                         [gf.circle_ring((0, c0[1], z0 + 2.6), band_r, band_r * 0.86, n=nseg),
                          gf.circle_ring((0, c0[1], z0 - 1.2), band_r * 1.01, band_r * 0.87, n=nseg)],
                         matrix=rig.body.matrix_world)
    apply_host_mat(obj, gid, cfg)
    return join_parts(obj, [skirt, band])


def build_hijab(rig, gid, cfg):
    headw = gf.vg_weights(rig.body, ["CC_Base_Head"])
    clav = gf.vg_weights(rig.body, ["CC_Base_L_Clavicle", "CC_Base_R_Clavicle",
                                    "CC_Base_NeckTwist01", "CC_Base_NeckTwist02"])
    eye_obj = next((o for o in bpy.data.objects
                    if o.type == 'MESH' and "CC_Base_Eye" in o.name
                    and "Occlusion" not in o.name), None)
    ez = float(gf.np_verts(eye_obj)[:, 2].mean()) if eye_obj else rig.head_z + 8
    # face window measured off the face's own landmarks: eyebrow mesh top to
    # teeth mesh bottom, elliptical width falloff — cloth wraps the temples
    # and under the chin, face features stay fully visible.
    nrm = np.zeros(len(rig.bco) * 3)
    rig.body.data.vertices.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    eb = next((o for o in bpy.data.objects
               if o.type == 'MESH' and "Eyebrow" in o.name), None)
    th = next((o for o in bpy.data.objects
               if o.type == 'MESH' and "Teeth" in o.name), None)
    z_top = (float(gf.np_verts(eb)[:, 2].max()) + 1.0) if eb else ez + 5.5
    chin_lo = (float(gf.np_verts(th)[:, 2].min()) - 0.5) if th else ez - 7.5
    zc, za = (z_top + chin_lo) / 2, (z_top - chin_lo) / 2
    rel = np.clip((rig.bco[:, 2] - zc) / max(za, 1e-3), -1, 1)
    xlim = 5.4 * np.sqrt(np.maximum(0.12, 1 - rel ** 2))
    face_window = (nrm[:, 1] < -0.2) & (rig.bco[:, 2] > chin_lo) \
        & (rig.bco[:, 2] < z_top) & (np.abs(rig.bco[:, 0]) < xlim)
    mask = ((headw > 0.15) | (clav > 0.25)
            | ((rig.torso > 0.35) & (rig.bco[:, 2] > rig.neck_z - 17))) \
        & ~face_window & (rig.bco[:, 2] > rig.neck_z - 17) & (rig.hand < 0.2) \
        & (rig.uarm < 0.4)
    mask = rig.close_mask(mask)  & ~face_window
    obj = gf.extract_shell(rig.body, mask, gid)
    gf.unsubdivide(obj, 1)
    gf.relax(obj, iters=6, lam=0.5)
    V = gf.np_verts(obj)
    amt = np.full(len(V), 1.2)
    amt[V[:, 2] > ez + 1] = 3.2                   # hair volume under the wrap
    amt[V[:, 2] < rig.neck_z + 2] = 2.0           # fuller drape at shoulders
    gf.inflate(obj, amt)
    gf.push_out(obj, rig.bvh, clear=0.55)
    lps = gf.boundary_loops(obj)
    V = gf.np_verts(obj)
    if lps:
        face_lp = min(lps, key=lambda lp: V[lp][:, 1].mean())
        gf.trim_roll(obj, face_lp, [(0.55, 0.3), (0.75, -0.35), (0.4, -1.0)],
                     axis_dir=(0, -1, 0))
        low = [lp for lp in lps if lp is not face_lp]
        if low:
            hem_lp = min(low, key=lambda lp: V[lp].mean(0)[2])
            gf.trim_roll(obj, hem_lp, [(0.4, -0.3), (0.5, -1.0), (0.2, -1.5)],
                         axis_dir=(0, 0, -1))
    gf.push_out(obj, rig.bvh, clear=0.35, rounds=1)
    apply_host_mat(obj, gid, cfg)
    return obj


def build_scarf(rig, gid, cfg):
    r, c = gf.body_radius_at(rig.bco, rig.neck_z + 2, 2.0)
    path_r = r + 1.6
    n = 22
    rings = []
    for i in range(n):
        t = 2 * math.pi * i / n
        px, py = math.cos(t) * path_r * 1.05, math.sin(t) * path_r * 0.95 + c[1]
        rings.append((px, py))
    prof = [(2.0, 0), (1.4, 1.5), (-1.4, 1.5), (-2.0, 0), (-1.4, -1.5), (1.4, -1.5)]
    ring_pts = []
    for px, py in rings:
        ang = math.atan2(py - c[1], px)
        pts = []
        for du, dv in prof:
            rr = path_r + du
            pts.append((math.cos(ang) * rr, math.sin(ang) * rr * 0.95 + c[1] * 0,
                        rig.neck_z + 1.5 + dv))
        ring_pts.append(np.array([(p[0], p[1] + c[1], p[2]) for p in pts]))
    loop = gf.loft_rings(gid, ring_pts + [ring_pts[0]],
                         matrix=rig.body.matrix_world)
    # tails drape ON the chest: sample the body surface with the BVH and
    # float the strip a scarf-thickness above it
    from mathutils import Vector as _V
    tails = []
    for sx, dz in ((-1, 0), (1, -4.5)):
        rows = []
        for i in range(7):
            t = i / 6
            w = 3.6 * (1 - 0.18 * t)
            z = rig.neck_z - 1.5 - 15.5 * t + dz
            row = []
            for j in range(4):
                x = sx * 3.0 + (j / 3 - 0.5) * w
                hit = rig.bvh.find_nearest(_V((x, -25.0, z)))
                ysurf = hit[0].y if hit[0] is not None else -9.0
                bulge = 0.45 * math.sin(math.pi * j / 3)
                row.append((x, ysurf - (1.7 - 0.5 * t) - bulge, z))
            rows.append(np.array(row))
        tails.append(gf.grid_mesh(f"{gid}_tail{sx}", rows,
                                  matrix=rig.body.matrix_world))
    apply_host_mat(loop, gid, cfg)
    return join_parts(loop, tails)


def build_cap(rig, gid, cfg):
    scalp = rig.bco[(gf.vg_weights(rig.body, ["CC_Base_Head"]) > 0.4)
                    & (rig.bco[:, 2] > rig.head_z + 9)]
    cz = scalp[:, 2].max()
    cx, cy = 0.0, scalp[:, 1].mean()
    rr = (scalp[:, 0].max() - scalp[:, 0].min()) / 2 + 1.6
    depth = 9.2
    rings = []
    n = 22
    for i in range(8):
        t = i / 7
        z = cz + 1.8 - (1.8 + depth) * t
        rad = rr * math.sqrt(max(0.04, 1 - (1 - t) ** 2 * 0.97))
        rings.append(gf.circle_ring((cx, cy, z), rad, rad * 1.06, n=n))
    dome = gf.loft_rings(gid, rings[::-1], close=False,
                         matrix=rig.body.matrix_world)
    # brim: front half-annulus fan, drooping toward its outer edge
    brim_z = cz - depth + 1.4
    rows = []
    for k in range(4):
        t = k / 3
        rad = rr * 1.02 + 6.6 * t
        row = []
        for j in range(13):
            a = math.radians(-52 + 104 * j / 12)
            row.append((cx + math.sin(a) * rad,
                        cy - math.cos(a) * rad * 1.02,
                        brim_z + 0.5 - 1.1 * t - 3.0 * t * t))
        rows.append(np.array(row))
    brim = gf.grid_mesh(gid + "_brim", rows, matrix=rig.body.matrix_world)
    sol = brim.modifiers.new("S", 'SOLIDIFY')
    sol.thickness = 0.55
    sol.offset = 0.0
    with bpy.context.temp_override(object=brim, active_object=brim,
                                   selected_objects=[brim]):
        bpy.ops.object.modifier_apply(modifier="S")
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.95, segments=10, ring_count=6,
                                         location=(0, cy * 0.01, (cz + 2.0) * 0.01))
    btn = bpy.context.object
    btn.scale = (0.01, 0.01, 0.006)
    with bpy.context.temp_override(active_object=btn, selected_editable_objects=[btn]):
        bpy.ops.object.transform_apply(scale=True)
    btn.name = gid + "_btn"
    apply_host_mat(dome, gid, cfg)
    return join_parts(dome, [brim, btn])


def build_beanie(rig, gid, cfg):
    scalp = rig.bco[(gf.vg_weights(rig.body, ["CC_Base_Head"]) > 0.4)
                    & (rig.bco[:, 2] > rig.head_z + 9)]
    cz = scalp[:, 2].max()
    cy = scalp[:, 1].mean()
    rr = (scalp[:, 0].max() - scalp[:, 0].min()) / 2 + 1.1
    rings = []
    n = 22
    for i in range(8):
        t = i / 7
        z = cz + 3.0 - (3.0 + 11.5) * t
        rad = rr * math.sqrt(max(0.03, 1 - (1 - t) ** 1.8 * 0.99)) * (1 - 0.06 * (1 - t))
        rings.append(gf.circle_ring((0, cy, z), rad, rad * 1.04, n=n))
    dome = gf.loft_rings(gid, rings[::-1], matrix=rig.body.matrix_world)
    lps = gf.boundary_loops(dome)
    V = gf.np_verts(dome)
    rim = min(lps, key=lambda lp: V[lp].mean(0)[2])
    gf.trim_roll(dome, rim, [(0.7, 0.9), (0.9, -0.4), (0.5, -2.0), (0.0, -2.6)],
                 axis_dir=(0, 0, -1), weight_src=False)
    apply_host_mat(dome, gid, cfg)
    return dome


def build_glasses(rig, gid, cfg):
    # anchor on the actual eyeball mesh clusters — bones proved unreliable
    eye_obj = next((o for o in bpy.data.objects
                    if o.type == 'MESH' and "CC_Base_Eye" in o.name
                    and "Occlusion" not in o.name), None)
    if eye_obj is not None:
        E = gf.np_verts(eye_obj)
        ex = float(np.abs(E[:, 0]).mean())
        ez = float(E[:, 2].mean())
    else:
        ex, ez = 3.2, rig.head_z + 8
    face = rig.bco[np.abs(rig.bco[:, 2] - ez) < 3]
    y_front = face[:, 1].min() - 1.0
    exp = cfg.get("shape", 2.0)
    lens_r = 2.55
    parts = []
    objs = []
    for sx in (-1, 1):
        path = []
        n = 22
        for i in range(n):
            t = 2 * math.pi * i / n
            ct, st = math.cos(t), math.sin(t)
            f = (abs(ct) ** exp + abs(st) ** exp) ** (-1.0 / exp)
            path.append((sx * ex + ct * f * lens_r, y_front, ez + st * f * lens_r * 0.92))
        rings = []
        for du, dv in ((0.45, 0), (0, 0.45), (-0.45, 0), (0, -0.45)):
            ring = []
            for px, py, pz in path:
                dx, dz = px - sx * ex, pz - ez
                dl = math.hypot(dx, dz)
                ring.append((px + dx / dl * du, py + dv, pz + dz / dl * du))
            rings.append(np.array(ring))
        lens = gf.loft_rings(f"{gid}_l{sx}", [rings[i % 4] for i in range(5)],
                             matrix=rig.body.matrix_world)
        objs.append(lens)
        arm_rings = []
        for i in range(8):
            t = i / 7
            y = y_front + (abs(y_front) - 0.0) * 0 + t * 11.5
            x = sx * (ex + lens_r + 0.15 + 0.5 * t)
            z = ez + 0.4 - max(0, t - 0.82) * 14
            arm_rings.append(gf.circle_ring((x, y, z), 0.32, 0.32, n=6))
        objs.append(gf.loft_rings(f"{gid}_t{sx}", arm_rings,
                                  matrix=rig.body.matrix_world))
    bridge = gf.loft_rings(gid + "_bridge",
                           [gf.circle_ring((x, y_front, ez + 0.5), 0.3, 0.3, n=6)
                            for x in np.linspace(-(ex - lens_r), ex - lens_r, 4)],
                           matrix=rig.body.matrix_world)
    host = objs[0]
    apply_host_mat(host, gid, cfg)
    obj = join_parts(host, objs[1:] + [bridge])
    obj.name = obj.data.name = gid
    return obj


BUILDERS = {"top": build_top, "pants": build_pants, "shoe": build_shoe,
            "dress": build_dress, "hijab": build_hijab, "scarf": build_scarf,
            "cap": build_cap, "beanie": build_beanie, "glasses": build_glasses}
RIGID = {"cap", "beanie", "glasses"}
MORPH_KEYS = {"top": ["body_weight"], "pants": ["body_weight"], "shoe": [],
              "dress": ["body_weight"], "scarf": ["body_weight"],
              "hijab": ["body_weight", "head_size", "face_width", "jaw_width",
                        "cheek_size", "head_width"]}

# ------------------------------------------------------------ render & QA
def studio(scene):
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.72, 0.72, 0.75, 1)
    scene.world = world
    for name, loc, rot, e, size in (
            ("Key", (2.2, -2.6, 3.2), (0.9, 0, 0.65), 420, 3.0),
            ("Fill", (-2.8, -1.8, 2.0), (1.1, 0, -0.9), 160, 3.0),
            ("Rim", (0.4, 3.0, 2.6), (-1.0, 0, 0.1), 240, 2.0)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = e
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = rot


def render_views(obj, rig, out_dir, gid):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.film_transparent = False
    if not any(o.name == "Key" for o in bpy.data.objects):
        studio(scene)
    cam_data = bpy.data.cameras.new("QACam")
    cam_data.lens = 65
    cam = bpy.data.objects.new("QACam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    M = np.array(obj.matrix_world)
    V = gf.np_verts(obj)
    W = V @ M[:3, :3].T + M[:3, 3]
    c = (W.min(0) + W.max(0)) / 2
    size = float(np.linalg.norm(W.max(0) - W.min(0)))
    target = Vector(c)
    dist = max(size * 1.7, 0.45)
    views = {"front": (0, -1, 0.1), "back": (0, 1, 0.1), "left": (-1, 0, 0.1),
             "right": (1, 0, 0.1), "persp": (0.75, -0.75, 0.35)}
    os.makedirs(out_dir, exist_ok=True)
    outs = {}
    for tag, d in views.items():
        dv = Vector(d).normalized()
        cam.location = target + dv * dist
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(out_dir, f"{gid}_{tag}.png")
        bpy.ops.render.render(write_still=True)
        outs[tag] = scene.render.filepath
    # wireframe pass: clay dup + wire dup
    mats = [ms.material for ms in obj.material_slots]
    clay = bpy.data.materials.new("QA_clay")
    clay.use_nodes = True
    clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.75, 0.78, 1)
    for ms in obj.material_slots:
        ms.material = clay
    wire = obj.copy()
    wire.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(wire)
    wm = wire.modifiers.new("W", 'WIREFRAME')
    wm.thickness = 0.0035 / max(obj.matrix_world.to_scale()[0], 1e-4)
    wmat = bpy.data.materials.new("QA_wire")
    wmat.use_nodes = True
    wnode = wmat.node_tree.nodes["Principled BSDF"]
    wnode.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1)
    wire.data.materials.clear()
    wire.data.materials.append(wmat)
    dv = Vector(views["persp"]).normalized()
    cam.location = target + dv * dist
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(out_dir, f"{gid}_wire.png")
    bpy.ops.render.render(write_still=True)
    outs["wire"] = scene.render.filepath
    bpy.data.objects.remove(wire, do_unlink=True)
    for ms, m in zip(obj.material_slots, mats):
        ms.material = m
    bpy.data.objects.remove(cam, do_unlink=True)
    return outs


# ------------------------------------------------------------------- main
report = {}
by_gender = {}
for gid in ids:
    cfg = G[gid]
    by_gender.setdefault(cfg.get("gender", "male"), []).append(gid)

for gender, glist in by_gender.items():
    rig = Rig(gender)
    for gid in glist:
        cfg = G[gid]
        print(f"\n=== BUILD {gid} ({gender}) ===")
        obj = BUILDERS[cfg["kind"]](rig, gid, cfg)
        obj.name = obj.data.name = gid
        import bmesh as _bmesh
        bm = _bmesh.new()
        bm.from_mesh(obj.data)
        _bmesh.ops.recalc_face_normals(bm, faces=bm.faces)   # constructed
        bm.to_mesh(obj.data)                                 # panels/lofts can
        bm.free()                                            # face inward
        with bpy.context.temp_override(active_object=obj, selected_objects=[obj],
                                       selected_editable_objects=[obj]):
            bpy.ops.object.shade_smooth()
        obj.data.validate(verbose=False)
        gf.bake_ao(obj, [rig.body], strength=0.45)
        gf.keep_only_ao_attribute(obj.data)
        src_dir = os.path.join(OUT, gid)
        outs = render_views(obj, rig, src_dir, gid)   # on-body, pre-recenter
        rigid = cfg["kind"] in RIGID
        if not rigid:
            gf.finalize_weights(obj, rig.body, rig.arm, rig.bvh)
            keys = MORPH_KEYS.get(cfg["kind"], [])
            added = gf.add_morph_followers(obj, rig.body, keys) if keys else []
        else:
            # rigid convention: data in METERS, bone-relative, identity matrix
            head = np.array(rig.arm.data.bones["CC_Base_Head"].head_local)
            V = gf.np_verts(obj)
            gf.set_verts(obj, (V - head) * 0.01)
            obj.matrix_world.identity()
            added = []
        # exports
        slot, cat = SLOT[cfg["kind"]]
        item_dir = os.path.join(SHARED, cat, gid)
        os.makedirs(item_dir, exist_ok=True)
        suffix = "_meta" if cfg["exist"] else ""
        glb = os.path.join(item_dir, f"{gid}{suffix}.glb")
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        if not rigid:
            rig.arm.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB',
            use_selection=True, export_skins=not rigid,
            export_morph=bool(added), export_animations=False, export_yup=True)
        os.makedirs(src_dir, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(src_dir, f"{gid}.fbx"),
                                 use_selection=True, add_leaf_bones=False)
        bpy.data.libraries.write(os.path.join(src_dir, f"{gid}.blend"),
                                 {obj}, path_remap='ABSOLUTE')
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        report[gid] = {
            "gender": gender, "tris": tris, "verts": len(obj.data.vertices),
            "materials": [m.name for m in obj.data.materials if m],
            "morph_followers": added, "glb": os.path.relpath(glb, SHARED),
            "size_kb": round(os.path.getsize(glb) / 1024, 1),
            "renders": {k: os.path.relpath(v, OUT) for k, v in outs.items()},
        }
        print(f"[done] {gid}: {tris} tris, {report[gid]['size_kb']} KB, "
              f"morphs={added}")
        obj.hide_render = True

rep_path = os.path.join(OUT, "build_report.json")
merged = {}
if os.path.isfile(rep_path):                 # per-item runs must not clobber
    with open(rep_path) as f:                # the rest of the library
        merged = json.load(f)
merged.update(report)
with open(rep_path, "w") as f:
    json.dump(merged, f, indent=1)
print("\nBUILD REPORT ->", rep_path)
