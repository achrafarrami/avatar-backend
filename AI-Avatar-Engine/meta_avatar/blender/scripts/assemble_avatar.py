"""
Attach selected wardrobe assets onto a template BEFORE identity bake+export.

Thin step in the backend/generate_avatar.py pipeline: opens a template
.blend, imports each asset GLB named in a manifest, positions/binds it using
the SAME two attach conventions as the runtime WardrobeManager
(frontend/threejs-viewer/src/viewer.js attachAsset/attachSkinned) —

  "bone"    rigid: the asset is authored bone-relative (local mesh verts
            already store the offset from the attach bone's HEAD, identity
            object transform — see build_demo_assets.py finalize_rigid() /
            import_hair_pack.py). Reproducing that contract here means:
            place the imported object at this template's own bone-head
            world position, then weight every vertex 1.0 to that bone (a
            single-bone skin, not parent_type='BONE' -- see attach_bone()'s
            docstring for why: bone-parenting does not survive glTF export
            correctly here, verified empirically, while single-bone
            skinning is the same exporter-native path clothing already
            uses and DOES follow the bone at runtime).
  "skinned" the asset carries its OWN copy of the source armature (it was
            exported with export_skins=True). Re-target its Armature
            modifier to THIS template's armature (vertex groups already
            share the CC_Base_* bone names, same skeleton/topology across
            styles per CLAUDE.md) and drop the imported duplicate skeleton
            — mirrors attachSkinned()'s "rebind by bone name, discard the
            asset's own skeleton copy".

Saves the assembled scene as a new .blend; export_avatar_glb.py (unmodified)
does the identity bake + GLB export from there.

Usage:
  blender --background --python assemble_avatar.py -- \
      <template.blend> <manifest.json> <out.blend>

manifest.json: a JSON list of entries -
  {"slot": "hair", "id": "hair_w03", "file": "<abs path to asset .glb>",
   "attach_type": "bone" | "skinned", "attach_to": "<bone name>" (bone only),
   "colorable_materials": ["hair_w03_mat"], "color_hex": "#3b2a1e" | null,
   "offset": [x,y,z] (optional, meta-style fit tweak; three.js/glTF frame,
       straight from the catalog's "styles.meta.offset" -- see
       _meta_offset_to_blender() below, converts to Blender frame before
       use; valid for BOTH bone and skinned items as of the D6 fix),
   "scale": s (optional, meta-style fit tweak; frame-independent; valid for
       BOTH bone and skinned items as of the D6 fix)}

A special manifest entry {"slot": "_template_colors", "skin": "#..",
"brows": "#..", "iris": "#.."} (all optional, measured from the photo by
color_sampler.py) recolors the TEMPLATE's own textures in place before
export: skin/brow diffuse maps get a multiplicative tint, the iris ring
gets a hue/sat replacement (sclera + pupil untouched).

A missing file / import error / attach failure is logged and that ONE item
is skipped — never fatal to the whole assembly.
"""
import bpy
import json
import os
import sys
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, MANIFEST_PATH, OUT_BLEND = argv[0], argv[1], argv[2]

with open(MANIFEST_PATH, encoding="utf-8-sig") as f:
    manifest = json.load(f)

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)

arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
if arm is None:
    sys.exit("[assemble] fatal: no armature found in template")


# ---------------------------------------------------------------- helpers
def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def set_color(obj, colorable_names, hex_color):
    """Recolor materials on `obj` whose name is in colorable_names (same
    hex-> linear conversion as import_hair_pack.py)."""
    if not hex_color or not colorable_names:
        return
    hexs = hex_color.lstrip("#")
    c = tuple(_srgb_to_linear(int(hexs[i:i + 2], 16) / 255)
              for i in (0, 2, 4)) + (1.0,)
    for slot in obj.material_slots:
        mat = slot.material
        # prefix match: meta variant GLBs carry "<name>_meta..." material
        # names while the catalog lists the base name (beard_short_mat vs
        # beard_short_meta_mat) — exact matching silently skipped them
        hit = mat and mat.use_nodes and any(
            mat.name == cn or mat.name.startswith(cn.rsplit("_mat", 1)[0])
            for cn in colorable_names)
        if hit:
            for nd in mat.node_tree.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    # a linked Base Color (vertex-color/texture chain)
                    # silently overrides default_value — unlink first;
                    # "colorable" means flat recolor
                    for lk in list(nd.inputs["Base Color"].links):
                        mat.node_tree.links.remove(lk)
                    nd.inputs["Base Color"].default_value = c
            print(f"[assemble] colored material {mat.name} -> {hex_color}")


def _meta_offset_to_blender(offset):
    """Convert a catalog "styles.meta.offset" value (three.js/glTF frame:
    X same, Y=up, Z=forward -- see compute_fits.py's to_threejs(), x_b, z_b,
    -y_b -> x, y, z) back to Blender frame (Z=up) for use here.

    Root cause of D5/D6/D7 (2026-07-22 QA pass): this conversion was
    MISSING -- assemble_avatar.py was adding the catalog's raw three.js-frame
    vector directly as a Blender translation, e.g. cap's catalog offset
    [0, -0.033461, -0.006164] (three.js) was applied as Blender
    (Y=-0.033461, Z=-0.006164) instead of the correct Blender
    (Y=0.006164, Z=-0.033461). That put ~90% of the intended DOWNWARD (Z)
    correction into the wrong axis (Y, forward/back) and left Z badly
    under-corrected -- confirmed by diffing
    meta_avatar/documentation/wardrobe_fits.json (compute_fits.py's raw
    offset_blender/offset_threejs pairs) against
    meta_avatar/documentation/jobs_male.json / jobs_female.json (which fed
    T3's Blender-native fit_wardrobe_batch.py/fit_beard_meta.py verification
    renders with offset_blender -- the correctly-converted values) against
    assets/shared/catalog.json (which stores offset_threejs, correct for the
    three.js runtime WardrobeManager, wrong for this Blender-side
    consumer). This under-correction is exactly the "floats/rides high"
    symptom QA reported for cap/glasses, worse than T3's own reference
    renders which used the correctly-converted value. Scale needs no
    conversion (uniform/isotropic, frame-independent)."""
    x, y, z = offset
    return (x, -z, y)


def _make_single_bone_skin(obj, bone_name):
    """Weight every vertex 1.0 to `bone_name` + add an Armature modifier
    targeting the template armature -- a single-bone skin, i.e. the same
    skinning path clothing already uses, not object/bone parenting.

    At the export rest pose this is a no-op: the Armature modifier's
    per-vertex transform is (bone.pose_matrix_world @
    bone.bind_matrix_world^-1), which is IDENTITY when pose == bind (no
    posing has happened yet) -- so the mesh stays exactly at the world
    position its own matrix_world already places it at (set by the caller
    BEFORE this runs). The payoff is at runtime: once CC_Base_Head (or
    whichever bone) rotates, the modifier correctly carries the prop along
    rigidly, because bone_name's own vertex-group weight is 1.0 everywhere.
    This survives glTF export reliably (skinning is exporter-native),
    unlike parent_type='BONE'/'OBJECT' hierarchy tricks -- see
    attach_bone()'s docstring for the export-time corruption that
    motivated this switch (D4, 2026-07-22)."""
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm


def attach_bone(obj, bone_name, item_id, offset=None, scale=None):
    """Rigid bone attach: position at the bone's world head, optionally
    nudged by a meta-style {offset, scale} fit tweak, then make it a
    single-bone-skinned attachment (see _make_single_bone_skin) so it
    follows the bone at runtime.

    Earlier version used Blender's parent_type='BONE' +
    parent_set(keep_transform=True) instead. Verified empirically
    (2026-07-22, hair_w03 on the female template) that this does NOT
    correctly round-trip through glTF export -- the bone's own ~100x
    local-space scale (these rigs are authored in raw cm-like units,
    corrected only by the Armature OBJECT's 0.01 world scale) leaked
    through unmodified, landing the exported object nowhere near the bone
    (hair exported at head.z=5.06 instead of the real head.z=1.53,
    scale=100 instead of 1) even though the SAME object verified at the
    exact correct position/scale in the .blend right before export. The
    single-bone-skin technique below replaced it (D4) so animation-follow
    still works without that export corruption."""
    bone = arm.data.bones.get(bone_name) if bone_name else None
    if bone is None:
        print(f"[assemble] {item_id}: bone '{bone_name}' not found on "
              f"{arm.name} -- left at scene origin")
        return
    head_world = arm.matrix_world @ bone.head_local
    s = float(scale) if scale else 1.0
    if s != 1.0:
        for v in obj.data.vertices:
            v.co = v.co * s
    off = Vector(_meta_offset_to_blender(offset)) if offset else Vector((0.0, 0.0, 0.0))
    obj.parent = None
    obj.matrix_world = Matrix.Translation(head_world + off)
    _make_single_bone_skin(obj, bone_name)
    print(f"[assemble] {item_id}: bone-attached (single-bone skin) to "
          f"{bone_name}"
          + (f" (offset {offset}, scale {s})" if offset or s != 1.0 else ""))


def attach_skinned(obj, dup_arm, item_id, offset=None, scale=None):
    """Re-bind a skinned asset to THIS template's armature; drop the
    asset's own imported skeleton copy. Re-parents with
    parent_set(type='OBJECT', keep_transform=True) rather than a bare
    `obj.parent = arm` assignment -- matches the technique T4 (clothing)
    validated in export_dressed_meta.py / test_clothing_fit.py; a naive
    `matrix_parent_inverse = arm.matrix_world.inverted()` was found wrong
    there, and keep_transform lets Blender compute the correct inverse.

    D6 fix (2026-07-22): applies the catalog's meta offset/scale fit to the
    mesh's REST geometry -- vertex data scaled about the mesh's own local
    origin, then translated by the (axis-converted, see
    _meta_offset_to_blender) world-space offset -- BEFORE the retarget/
    reparent below. Previously this function took no offset/scale params at
    all, so beard_short's catalog fit (scale 1.0294, offset [0,-0.135,0.05])
    was silently never read -- the mesh kept whatever position its own
    (realistic-rig-authored) vertex data encoded, which on the Meta armature
    lands at eye/brow height instead of the jaw (F5: bone rest-orientation
    differs between rigs, so a naive bone-name rebind alone isn't enough).

    Doing the scale+translate BEFORE reparenting (rather than after, as T3's
    own fit_beard_meta.py verification script does via matrix_world once
    parented) is mathematically equivalent here: parent_set(keep_transform=
    True) preserves the object's current WORLD transform across the
    reparent, so whether the offset/scale is baked in before or after that
    call, the same final rest-pose world position results. Doing it before
    (while obj still has no parent) sidesteps the meta armature object's own
    0.01 import scale entirely, matching how attach_bone() avoids the same
    distortion (see fit_beard_meta.py's own comment on why a *post*-parent
    matrix_basis edit gets crushed ~100x by that parent scale -- setting
    matrix_world directly, before or after, is what avoids it either way)."""
    s = float(scale) if scale else 1.0
    if s != 1.0:
        for v in obj.data.vertices:
            v.co = v.co * s
    if offset:
        off = Vector(_meta_offset_to_blender(offset))
        obj.matrix_world = Matrix.Translation(off) @ obj.matrix_world
    try:
        retargeted = False
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                mod.object = arm
                retargeted = True
        if not retargeted:
            mod = obj.modifiers.new("Armature", 'ARMATURE')
            mod.object = arm
        with bpy.context.temp_override(active_object=arm,
                                       selected_editable_objects=[obj, arm]):
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        print(f"[assemble] {item_id}: re-bound (skinned) to {arm.name}"
              + (f" (offset {offset}, scale {s})" if offset or s != 1.0 else ""))
    except Exception as e:
        print(f"[assemble] {item_id}: armature retarget failed ({e})")
    if dup_arm is not None:
        try:
            dup_data = dup_arm.data
            bpy.data.objects.remove(dup_arm, do_unlink=True)
            if dup_data.users == 0:
                bpy.data.armatures.remove(dup_data)
        except Exception as e:
            print(f"[assemble] {item_id}: could not drop imported "
                  f"duplicate armature ({e})")


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def _recolor_image(img, fn):
    """Apply fn(N x 3 float array in 0..255 sRGB) -> same, to a packed
    bpy image in place. Alpha untouched."""
    n = img.size[0] * img.size[1]
    px = np.zeros(n * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rgb = fn(px[:, :3].astype(np.float64) * 255.0)
    px[:, :3] = np.clip(rgb / 255.0, 0.0, 1.0).astype(np.float32)
    img.pixels.foreach_set(px.reshape(-1))
    img.update()
    img.pack()


def _diffuse_images(material_names):
    """The diffuse Image datablocks used by the named materials."""
    out = []
    for name in material_names:
        mat = bpy.data.materials.get(name)
        if not mat or not mat.use_nodes:
            continue
        for nd in mat.node_tree.nodes:
            if nd.type == 'TEX_IMAGE' and nd.image and \
                    "diffuse" in nd.image.name.lower():
                out.append(nd.image)
    return out


def recolor_template(colors):
    """Measured photo colors -> template textures, in place.

    skin/brows: multiplicative tint (target / current-texture-mean per
    channel) — keeps the painted shading variation, shifts the overall
    tone; the exact approach three.js uses for material.color on a map.
    iris: hue/sat replaced with the target's on SATURATED pixels only
    (the iris ring), keeping each pixel's value — sclera (white) and
    pupil (black) untouched."""
    def _to_lin(srgb01):
        return np.where(srgb01 <= 0.04045, srgb01 / 12.92,
                        ((srgb01 + 0.055) / 1.055) ** 2.4)

    def _to_srgb(lin):
        return np.where(lin <= 0.0031308, lin * 12.92,
                        1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)

    def _linear_tint(img, target_255, mean_mask=None):
        """Multiply the image toward target in LINEAR space (the space the
        shader actually works in — an sRGB-space multiply under-darkens
        dark targets). mean_mask optionally restricts the mean estimate
        (e.g. brow pixels only)."""
        n = img.size[0] * img.size[1]
        px = np.zeros(n * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        arr = px.reshape(-1, 4)
        sel = arr[mean_mask][:, :3] if mean_mask is not None else arr[:, :3]
        mean_lin = _to_lin(sel.astype(np.float64)).mean(axis=0)
        target_lin = _to_lin(target_255 / 255.0)
        ratio = target_lin / np.maximum(mean_lin, 1e-4)

        def fn(rgb):
            lin = _to_lin(rgb / 255.0) * ratio
            return _to_srgb(lin) * 255.0
        _recolor_image(img, fn)
        return ratio

    skin_hex = colors.get("skin")
    if skin_hex:
        target = _hex_to_rgb(skin_hex)
        for img in _diffuse_images(["Std_Skin_Head", "Std_Skin_Body",
                                    "Std_Skin_Arm", "Std_Skin_Leg"]):
            ratio = _linear_tint(img, target)
            print(f"[assemble] skin tint {skin_hex}: {img.name} "
                  f"(linear ratio {np.round(ratio, 2)})")

    brow_hex = colors.get("brows")
    if brow_hex:
        # flat base color, like hair/beard assets get (meta = flat toon
        # colors). Texture-space recolors kept failing here: the strip's
        # UVs sample background regions of the texture, so per-pixel HSV
        # rewrites tint the wrong pixels.
        hx = brow_hex.lstrip("#")
        c = tuple(_srgb_to_linear(int(hx[i:i + 2], 16) / 255)
                  for i in (0, 2, 4)) + (1.0,)
        mat = bpy.data.materials.get("Toon_Eyebrows_Transparency")
        if mat and mat.use_nodes:
            for nd in mat.node_tree.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    for lk in list(nd.inputs["Base Color"].links):
                        mat.node_tree.links.remove(lk)
                    nd.inputs["Base Color"].default_value = c
            print(f"[assemble] brow flat color {brow_hex}")

    iris_hex = colors.get("iris")
    if iris_hex:
        t = _hex_to_rgb(iris_hex) / 255.0
        t_hsv = cv2_free_rgb_to_hsv(t.reshape(1, 3))[0]

        def make_iris_fn(scale_v):
            def iris_fn(rgb):
                hsv = cv2_free_rgb_to_hsv(rgb / 255.0)
                # ring mask: strongly saturated pixels (the ring core) OR
                # blue-HUED pixels at any mild saturation — the ring's pale
                # scalloped edge sits below the old 0.25 threshold and left
                # a blue outline. Hue-gating keeps warm sclera shading out.
                blue_hue = (hsv[:, 0] > 0.45) & (hsv[:, 0] < 0.80)
                sat = (hsv[:, 1] > 0.25) | (blue_hue & (hsv[:, 1] > 0.06))
                if sat.any():
                    hsv[sat, 0] = t_hsv[0]
                    hsv[sat, 1] = t_hsv[1]
                    if scale_v:
                        # match the ring's median brightness to the target
                        ring_v_med = np.median(hsv[sat, 2])
                        hsv[sat, 2] = np.clip(
                            hsv[sat, 2] * (t_hsv[2] / max(ring_v_med, 1e-4)),
                            0, 1)
                return cv2_free_hsv_to_rgb(hsv) * 255.0
            return iris_fn

        # cornea = a constant-alpha (0.55) layer whose diffuse is an
        # identical copy of the eyeball texture. Give BOTH layers the SAME
        # full recolor: alpha-mixing two identical target colors yields the
        # target; recoloring only one washes it out (verified both ways)
        for img in _diffuse_images(["Std_Cornea_R", "Std_Cornea_L",
                                    "Std_Eye_R", "Std_Eye_L"]):
            _recolor_image(img, make_iris_fn(scale_v=True))
            print(f"[assemble] iris recolor {iris_hex}: {img.name}")


def cv2_free_rgb_to_hsv(rgb):
    """Vectorized RGB(0..1) -> HSV(0..1) without importing cv2 into
    Blender's python."""
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    mx, mn = rgb.max(axis=1), rgb.min(axis=1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-9
    idx = nz & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / d[idx]) % 6
    idx = nz & (mx == g)
    h[idx] = (b[idx] - r[idx]) / d[idx] + 2
    idx = nz & (mx == b)
    h[idx] = (r[idx] - g[idx]) / d[idx] + 4
    h /= 6.0
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    return np.stack([h, s, mx], axis=1)


def cv2_free_hsv_to_rgb(hsv):
    h, s, v = hsv[:, 0] * 6.0, hsv[:, 1], hsv[:, 2]
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=1)


# ------------------------------------------------------------------- main
attached = 0
for entry in manifest:
    if entry.get("slot") == "_template_colors":
        try:
            recolor_template(entry)
        except Exception as e:
            print(f"[assemble] template recolor failed (non-fatal): {e}")
        continue
    item_id = entry.get("id", "?")
    path = entry.get("file")
    if not path or not os.path.isfile(path):
        print(f"[assemble] SKIP {item_id}: file not found ({path})")
        continue

    before = set(bpy.context.scene.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        print(f"[assemble] SKIP {item_id}: import failed ({e})")
        continue
    imported = [o for o in bpy.context.scene.objects if o not in before]
    meshes = [o for o in imported if o.type == 'MESH']
    arms_imported = [o for o in imported if o.type == 'ARMATURE']

    if not meshes:
        print(f"[assemble] SKIP {item_id}: glb contained no mesh")
        for o in imported:
            bpy.data.objects.remove(o, do_unlink=True)
        continue

    # Some shared asset glbs carry a stray leftover object alongside the
    # real mesh (e.g. tshirt.glb also bundles an unrelated 42-vert
    # "Icosphere" -- a pre-existing artifact of how it was exported, not
    # something to silently merge or ship; T4's export_dressed_meta.py hit
    # the exact same thing). Pick the real mesh, drop the rest -- never
    # join blind (a join of unrelated geometry would corrupt the real
    # mesh). Criterion depends on attach type: a skinned shell always has
    # vertex groups (needed to deform at all), junk placeholders never do
    # (T4's signal, cleaner than name-matching here); a rigid bone asset
    # has no vertex groups either way, so fall back to name/largest.
    attach_type = entry.get("attach_type")
    if attach_type == "skinned":
        weighted = [m for m in meshes if m.vertex_groups]
        mesh_obj = weighted[0] if weighted else \
            max(meshes, key=lambda m: len(m.data.vertices))
    else:
        named = [m for m in meshes if m.name.split(".")[0].lower() == item_id.lower()]
        mesh_obj = named[0] if named else max(meshes, key=lambda m: len(m.data.vertices))
    for extra in meshes:
        if extra is mesh_obj:
            continue
        print(f"[assemble] {item_id}: dropping stray extra mesh "
              f"'{extra.name}' ({len(extra.data.vertices)} verts) from the glb")
        bpy.data.objects.remove(extra, do_unlink=True)

    if attach_type == "skinned":
        attach_skinned(mesh_obj, arms_imported[0] if arms_imported else None,
                       item_id, entry.get("offset"), entry.get("scale"))
    elif attach_type == "bone":
        for a in arms_imported:   # bone-rigid assets carry no skeleton
            bpy.data.objects.remove(a, do_unlink=True)
        attach_bone(mesh_obj, entry.get("attach_to"), item_id,
                   entry.get("offset"), entry.get("scale"))
    else:
        print(f"[assemble] SKIP {item_id}: unknown attach_type "
              f"'{attach_type}'")
        bpy.data.objects.remove(mesh_obj, do_unlink=True)
        continue

    set_color(mesh_obj, set(entry.get("colorable_materials") or []),
             entry.get("color_hex"))
    attached += 1

print(f"[assemble] attached {attached}/{len(manifest)} wardrobe item(s)")
os.makedirs(os.path.dirname(os.path.abspath(OUT_BLEND)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"[assemble] saved {OUT_BLEND}")
