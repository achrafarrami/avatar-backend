"""Build animation clips into the anim master .blend.

Opens the anim master if it exists (else creates it from the template:
save-as, 30 fps, default rest action removed — templates are NEVER touched),
imports every recipe module from scripts/clips/, then (re)builds the
requested clips. Idempotent: only the requested clip ids are rebuilt,
existing clips are preserved.

Usage:
  blender --background --python build_animations.py -- [all | cid [cid ...]]
      [--template <path.blend>] [--master <path.blend>]
"""
import bpy
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework import clips as clips_mod            # noqa: E402
from anim_framework.rig import Rig                       # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ENGINE_ROOT = os.path.abspath(os.path.join(ANIM_ROOT, ".."))
DEFAULT_TEMPLATE = os.path.join(ENGINE_ROOT, "meta_avatar", "blender",
                                "base", "meta_male.blend")
DEFAULT_MASTER = os.path.join(ANIM_ROOT, "blender",
                              "anim_master_meta_male.blend")
CLIPS_DIR = os.path.join(SCRIPT_DIR, "clips")
FPS = 30


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    template, master = DEFAULT_TEMPLATE, DEFAULT_MASTER
    ids = []
    i = 0
    while i < len(argv):
        if argv[i] == "--template":
            template = argv[i + 1]; i += 2
        elif argv[i] == "--master":
            master = argv[i + 1]; i += 2
        else:
            ids.append(argv[i]); i += 1
    return template, master, ids or ["all"]


def open_master(template, master):
    if os.path.isfile(master):
        bpy.ops.wm.open_mainfile(filepath=master)
        print(f"Opened existing master: {master}")
        return Rig()
    bpy.ops.wm.open_mainfile(filepath=template)
    rig = Rig()
    removed = rig.clear_default_animation()
    if removed:
        print(f"Removed template default action(s): {removed}")
    # drop any pre-existing NLA junk from the template
    for db in clips_mod._iter_datablocks(rig):
        adt = db.animation_data
        if adt:
            for t in list(adt.nla_tracks):
                adt.nla_tracks.remove(t)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    os.makedirs(os.path.dirname(master), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=master)
    print(f"Created master from template ({FPS} fps): {master}")
    return rig


def main():
    template, master, ids = parse_args()
    rig = open_master(template, master)
    bpy.context.scene.render.fps = FPS  # enforce even on old masters
    bpy.context.scene.render.fps_base = 1.0

    loaded = clips_mod.load_recipe_modules(CLIPS_DIR)
    print(f"Recipe modules: {loaded} -> {len(clips_mod.REGISTRY)} clips")

    if ids == ["all"]:
        ids = list(clips_mod.REGISTRY)
    unknown = [c for c in ids if c not in clips_mod.REGISTRY]
    if unknown:
        raise SystemExit(f"Unknown clip ids: {unknown} "
                         f"(registered: {sorted(clips_mod.REGISTRY)})")

    for cid in ids:
        recipe = clips_mod.REGISTRY[cid]
        stats = clips_mod.build_clip(rig, recipe)
        print(f"BUILT {cid}: frames {stats['frame_start']}-"
              f"{stats['frame_end']}, {stats['keyframes_total']} keys, "
              f"{len(stats['bones'])} bones, "
              f"{len(stats['shape_keys'])} shape keys")

    # key inventory for authors (per-mesh availability map)
    inv = rig.dump_key_inventory(
        os.path.join(ANIM_ROOT, "blender", "key_inventory.json"))
    print(f"Key inventory: {inv}")

    bpy.ops.wm.save_as_mainfile(filepath=master)
    print(f"Saved master: {master}")
    print(f"Clips in file: {clips_mod.clips_in_file(rig)}")


if __name__ == "__main__":
    main()
