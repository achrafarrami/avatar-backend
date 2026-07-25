"""Bone world-position probe — tune hand-contact gestures (facepalm etc.).

Prints world-space (meters) head positions of the requested bones at a
given frame of a clip, evaluated with only that clip's NLA tracks active.

Usage:
  blender --background --python probe_pose.py -- <clip_id> <frame>
      <bone> [<bone> ...] [--master <path.blend>] [--json <out.json>]

Bone names may be short ('Head', 'L_Hand') or full CC_Base_* names.
"""
import bpy
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework import clips as clips_mod            # noqa: E402
from anim_framework.rig import Rig                       # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_MASTER = os.path.join(ANIM_ROOT, "blender",
                              "anim_master_meta_male.blend")


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    master, out_json = DEFAULT_MASTER, None
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] == "--master":
            master = argv[i + 1]; i += 2
        elif argv[i] == "--json":
            out_json = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    if len(pos) < 3:
        raise SystemExit(__doc__)
    cid, frame, bones = pos[0], int(pos[1]), pos[2:]

    bpy.ops.wm.open_mainfile(filepath=master)
    rig = Rig()
    if not clips_mod.set_clip_solo(rig, cid):
        raise SystemExit(f"Clip '{cid}' not found "
                         f"(have {clips_mod.clips_in_file(rig)})")
    bpy.context.scene.frame_set(frame)

    result = {}
    print(f"\n=== POSE PROBE {cid} @ frame {frame} (world meters) ===")
    for b in bones:
        p = rig.bone_world_head(b, evaluated=True)
        result[rig.bone(b)] = [round(v, 5) for v in p]
        print(f"  {rig.bone(b)}: ({p.x:.4f}, {p.y:.4f}, {p.z:.4f})")
    if out_json:
        with open(out_json, "w") as f:
            json.dump({"clip": cid, "frame": frame, "bones": result}, f,
                      indent=1)
        print("written:", out_json)


if __name__ == "__main__":
    main()
