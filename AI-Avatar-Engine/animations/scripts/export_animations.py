"""Export the animation library.

Produces in animations/exports/:
  avatar_animated_meta_male.glb            all clips as named glTF animations
  avatar_animated_meta_male_<category>.glb one GLB per clip category
  avatar_animated_meta_male.fbx            best-effort FBX (baked, see log)
  export_log.txt                           what was exported + FBX limitations

Identity morphs never ship: the same delta-preserving bake as
blender/scripts/export_avatar_glb.py is applied (the meta template already
carries its stylized neutral in the mesh basis, and the anim master keys
identity at 0, so the bake reduces to deleting the identity keys — the
general displacement-field path still runs for safety).

Usage:
  blender --background --python export_animations.py --
      [--master <path.blend>] [--skip-fbx] [--only-full]
"""
import bpy
import json
import os
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework import clips as clips_mod            # noqa: E402
from anim_framework.rig import Rig, IDENTITY_KEYS        # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_MASTER = os.path.join(ANIM_ROOT, "blender",
                              "anim_master_meta_male.blend")
EXPORTS = os.path.join(ANIM_ROOT, "exports")
BASE_NAME = "avatar_animated_meta_male"


def bake_out_identity(rig, log):
    """Delta-preserving removal of identity keys (port of export_avatar_glb).
    Current identity values (normally all 0) are folded into the basis and
    every surviving key; the identity key blocks are then deleted."""
    for obj in rig.meshes:
        mesh = obj.data
        kbs = mesh.shape_keys.key_blocks
        present = [kb for kb in kbs if kb.name in IDENTITY_KEYS]
        if not present:
            continue
        n = len(mesh.vertices)
        basis_co = np.zeros(n * 3, dtype=np.float64)
        kbs[0].data.foreach_get("co", basis_co)
        D = np.zeros(n * 3, dtype=np.float64)
        nonzero = False
        for kb in present:
            v = max(kb.slider_min, min(kb.slider_max, kb.value))
            if abs(v) < 1e-6:
                continue
            nonzero = True
            co = np.zeros(n * 3, dtype=np.float64)
            kb.data.foreach_get("co", co)
            D += v * (co - basis_co)
        if nonzero:
            names = {kb.name for kb in present}
            for kb in kbs:
                if kb.name in names:
                    continue
                co = np.zeros(n * 3, dtype=np.float64)
                kb.data.foreach_get("co", co)
                kb.data.foreach_set("co", (co + D).astype(np.float32))
            verts = np.zeros(n * 3, dtype=np.float64)
            mesh.vertices.foreach_get("co", verts)
            mesh.vertices.foreach_set("co", (verts + D).astype(np.float32))
        for kb in present:
            obj.shape_key_remove(kb)
        mesh.update()
        log.append(f"  {obj.name}: removed {len(present)} identity keys"
                   f"{' (baked non-zero values)' if nonzero else ''}, "
                   f"{len(mesh.shape_keys.key_blocks) - 1} animation keys kept")


def export_glb(out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        export_morph=True,
        export_morph_normal=True,
        export_skins=True,
        export_animations=True,
        export_animation_mode='NLA_TRACKS',
        export_anim_slide_to_zero=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_yup=True,
    )
    return os.path.getsize(out_path) / 1e6


def prepare(master):
    bpy.ops.wm.open_mainfile(filepath=master)
    rig = Rig()
    clips_mod.unmute_all(rig)
    return rig


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    master, skip_fbx, only_full = DEFAULT_MASTER, False, False
    i = 0
    while i < len(argv):
        if argv[i] == "--master":
            master = argv[i + 1]; i += 2
        elif argv[i] == "--skip-fbx":
            skip_fbx = True; i += 1
        elif argv[i] == "--only-full":
            only_full = True; i += 1
        else:
            raise SystemExit(f"Unknown arg: {argv[i]}")

    log = [f"Export log — {BASE_NAME}", "=" * 40]

    # ---- full GLB ------------------------------------------------------
    rig = prepare(master)
    all_meta = clips_mod.stored_meta() or {}
    in_file = clips_mod.clips_in_file(rig)
    log.append(f"Clips in master: {in_file}")
    log.append("Identity bake:")
    bake_out_identity(rig, log)
    full = os.path.join(EXPORTS, f"{BASE_NAME}.glb")
    size = export_glb(full)
    log.append(f"FULL: {full} ({size:.1f} MB, {len(in_file)} animations)")
    print(log[-1])

    # ---- per-category GLBs --------------------------------------------
    if not only_full:
        categories = {}
        for cid in in_file:
            cat = (all_meta.get(cid) or {}).get("category", "uncategorized")
            categories.setdefault(cat, []).append(cid)
        for cat, cids in sorted(categories.items()):
            rig = prepare(master)  # fresh open per category
            clips_mod.keep_only_clips(rig, cids)
            bake_out_identity(rig, [])
            out = os.path.join(EXPORTS, f"{BASE_NAME}_{cat.lstrip('_')}.glb")
            size = export_glb(out)
            log.append(f"CATEGORY {cat}: {out} ({size:.1f} MB) clips={cids}")
            print(log[-1])

    # ---- FBX best-effort ----------------------------------------------
    if not skip_fbx:
        rig = prepare(master)
        bake_out_identity(rig, [])
        fbx = os.path.join(EXPORTS, f"{BASE_NAME}.fbx")
        try:
            bpy.ops.export_scene.fbx(
                filepath=fbx,
                use_selection=False,
                add_leaf_bones=False,
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,   # one take per NLA strip
                bake_anim_use_all_actions=False,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=0.0,   # no lossy simplification
                mesh_smooth_type='OFF',
                path_mode='COPY',
                embed_textures=True,
            )
            log.append(f"FBX: {fbx} ({os.path.getsize(fbx) / 1e6:.1f} MB)")
            log.append("FBX limitations: animation is BAKED per frame from "
                       "NLA strips (one take per clip); bezier easing is "
                       "sampled, not preserved. Shape-key (blendshape) "
                       "curves are exported per take where supported by the "
                       "FBX baker; verify in the target DCC. Bone scale "
                       "bakes numerically. glTF remains the reference "
                       "format for runtimes.")
        except Exception as e:  # noqa: BLE001 — best-effort by contract
            log.append(f"FBX FAILED: {e}")
        print(log[-1])

    log.append("Master .blend deliverable: " + master)
    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, "export_log.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    print(f"Log: {os.path.join(EXPORTS, 'export_log.txt')}")


if __name__ == "__main__":
    main()
