"""Consolidate the 4 per-subset animation masters into one combined master.

The library was parallel-built across four master .blend files, each holding a
disjoint subset of the ~103 clips as NLA tracks (one track per clip id, on the
armature for bone motion and on each mesh's shape-key datablock for face/teeth/
eyes/etc.):

  anim_master_body.blend       37 body/idle/gesture clips  (base — most clips)
  anim_master_facial.blend     33 facial clips
  anim_master_lipsync.blend    15 talking clips
  anim_master_body_loco.blend  18 locomotion clips

All four share the SAME rig (meta_male template: MetaMale_Armature + 7 meshes,
identical bone + shape-key names), so a clip's actions re-target purely BY NAME
across masters. This script opens the base master and, for every OTHER master,
appends exactly that master's per-clip Action datablocks and reconstructs each
clip's NLA tracks on the matching base datablock (armature for bone actions,
the same-named mesh for each shape-key action). Result:

  blender/anim_master_all.blend   ALL ~103 clips as named NLA tracks, no dupes,
                                  identity keys untouched (still at 0).

Idempotent / re-runnable: anim_master_all.blend is regenerated from the 4
sources every run (safe to re-run after loco QA rework).

Usage:
  blender --background --python consolidate_masters.py --
      [--base <body.blend>] [--out <all.blend>]
  # internal (self-spawned) manifest reader:
  blender --background --python consolidate_masters.py -- --dump-manifest <m> <out.json>
"""
import bpy
import json
import os
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework import clips as clips_mod            # noqa: E402
from anim_framework.rig import Rig                       # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BLENDER_DIR = os.path.join(ANIM_ROOT, "blender")
BASE_MASTER = os.path.join(BLENDER_DIR, "anim_master_body.blend")
OTHER_MASTERS = [
    os.path.join(BLENDER_DIR, "anim_master_facial.blend"),
    os.path.join(BLENDER_DIR, "anim_master_lipsync.blend"),
    os.path.join(BLENDER_DIR, "anim_master_body_loco.blend"),
]
OUT_MASTER = os.path.join(BLENDER_DIR, "anim_master_all.blend")


# ---------------------------------------------------------------------------
# Manifest: the exact NLA layout of ONE master, read in an isolated process
# (reading a foreign master's NLA arrangement requires opening it as main; we
# do that in a child Blender, dump JSON, and rebuild in the parent).
# ---------------------------------------------------------------------------
def _db_role(rig, db):
    """Identify a datablock yielded by clips._iter_datablocks."""
    if db is rig.armature:
        return ("armature", rig.armature.name)
    for o in rig.meshes:
        if o.data.shape_keys is db:
            return ("mesh", o.name)
    return ("unknown", getattr(db, "name", ""))


def dump_manifest(master, out_path):
    bpy.ops.wm.open_mainfile(filepath=master)
    rig = Rig()
    entries = []
    for db in clips_mod._iter_datablocks(rig):
        adt = db.animation_data
        if not adt:
            continue
        kind, name = _db_role(rig, db)
        tracks = []
        for t in adt.nla_tracks:
            strips = []
            for s in t.strips:
                if not s.action:
                    continue
                strips.append(dict(
                    action=s.action.name,
                    frame_start=s.frame_start, frame_end=s.frame_end,
                    action_frame_start=s.action_frame_start,
                    action_frame_end=s.action_frame_end,
                    blend_type=s.blend_type, extrapolation=s.extrapolation,
                    scale=s.scale, repeat=s.repeat, mute=s.mute))
            tracks.append(dict(name=t.name, mute=t.mute, strips=strips))
        entries.append(dict(kind=kind, name=name, tracks=tracks))
    manifest = dict(
        master=master, prefix=rig.prefix, entries=entries,
        clips=clips_mod.clips_in_file(rig),
        meta=json.loads(bpy.context.scene.get(clips_mod.SCENE_META_PROP, "{}")))
    with open(out_path, "w") as f:
        json.dump(manifest, f)
    print(f"MANIFEST_WRITTEN {out_path} clips={len(manifest['clips'])} "
          f"entries={len(entries)}")


def _read_manifest(master):
    """Spawn a child Blender to dump `master`'s NLA manifest, then load it."""
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="anim_manifest_")
    os.close(fd)
    cmd = [bpy.app.binary_path, "--background", "--python",
           os.path.abspath(__file__), "--",
           "--dump-manifest", master, tmp]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    with open(tmp) as f:
        manifest = json.load(f)
    os.remove(tmp)
    return manifest


# ---------------------------------------------------------------------------
# Consolidation (runs in the parent process, base master open as main)
# ---------------------------------------------------------------------------
def _target_adt(rig, kind, name):
    if kind == "armature":
        return rig.armature.animation_data_create()
    if kind == "mesh":
        for o in rig.meshes:
            if o.name == name:
                sk = o.data.shape_keys
                return sk.animation_data or sk.animation_data_create()
        raise SystemExit(f"base rig has no mesh named '{name}'")
    raise SystemExit(f"unknown datablock kind '{kind}'")


def _append_actions(master, names):
    """Append exactly `names` from master; return {orig_name: datablock}
    (order-preserving zip survives auto-rename on collision).

    NOTE: libraries.load repopulates the SAME list handed to dt.actions with
    the loaded datablocks on context exit — so we keep the string names in a
    separate list and hand Blender a throwaway copy."""
    orig = list(names)
    with bpy.data.libraries.load(master, link=False) as (df, dt):
        avail = set(df.actions)
        missing = [n for n in orig if n not in avail]
        if missing:
            raise SystemExit(f"{os.path.basename(master)} missing actions: "
                             f"{missing[:8]}{'...' if len(missing) > 8 else ''}")
        dt.actions = list(orig)
    loaded = list(dt.actions)
    if len(loaded) != len(orig):
        raise SystemExit(f"{os.path.basename(master)}: requested {len(orig)} "
                         f"actions, loaded {len(loaded)}")
    return {name: db for name, db in zip(orig, loaded)}


def _rebuild_nla(rig, manifest, name_map):
    for entry in manifest["entries"]:
        adt = _target_adt(rig, entry["kind"], entry["name"])
        for tr in entry["tracks"]:
            nt = adt.nla_tracks.new()
            nt.name = tr["name"]
            for sp in tr["strips"]:
                act = name_map[sp["action"]]
                st = nt.strips.new(sp["action"], int(sp["frame_start"]), act)
                st.action_frame_start = sp["action_frame_start"]
                st.action_frame_end = sp["action_frame_end"]
                st.frame_start = sp["frame_start"]
                st.frame_end = sp["frame_end"]
                st.blend_type = sp["blend_type"]
                st.extrapolation = sp["extrapolation"]
                st.scale = sp["scale"]
                st.repeat = sp["repeat"]
                st.mute = sp["mute"]
            nt.mute = tr["mute"]


def consolidate(base, others, out):
    log = [f"Consolidate -> {os.path.basename(out)}", "=" * 48]

    # ---- read foreign layouts first (isolated child processes) ----------
    manifests = []
    for m in others:
        mf = _read_manifest(m)
        manifests.append(mf)
        log.append(f"read {os.path.basename(m)}: {len(mf['clips'])} clips, "
                   f"{len(mf['entries'])} datablocks")

    # ---- open base master as main --------------------------------------
    bpy.ops.wm.open_mainfile(filepath=base)
    rig = Rig()
    present = list(clips_mod.clips_in_file(rig))
    log.append(f"base {os.path.basename(base)}: {len(present)} clips")

    # ---- collision guard (clip ids must be globally unique) -------------
    collisions = []
    for mf, m in zip(manifests, others):
        for cid in mf["clips"]:
            if cid in present:
                collisions.append((cid, os.path.basename(m)))
            else:
                present.append(cid)
    if collisions:
        for cid, src in collisions:
            log.append(f"  COLLISION: clip '{cid}' from {src} already present")
        _write_log(log)
        raise SystemExit(f"clip-id collisions found: {collisions}")
    log.append("collision check: none (all clip ids unique)")

    # ---- append actions + rebuild NLA for each other master ------------
    scene_meta = json.loads(bpy.context.scene.get(clips_mod.SCENE_META_PROP, "{}"))
    for mf, m in zip(manifests, others):
        names = sorted({sp["action"]
                        for e in mf["entries"] for tr in e["tracks"]
                        for sp in tr["strips"]})
        name_map = _append_actions(mf["master"], names)
        renamed = [f"{o}->{db.name}" for o, db in name_map.items()
                   if db.name != o]
        _rebuild_nla(rig, mf, name_map)
        scene_meta.update(mf["meta"])
        log.append(f"merged {os.path.basename(m)}: +{len(mf['clips'])} clips, "
                   f"{len(names)} actions appended"
                   + (f", {len(renamed)} renamed {renamed[:4]}" if renamed else ""))

    # ---- finalize -------------------------------------------------------
    bpy.context.scene[clips_mod.SCENE_META_PROP] = json.dumps(scene_meta)
    rig.clear_default_animation()   # NLA-only: drop stray active/default actions
    clips_mod.unmute_all(rig)
    final = clips_mod.clips_in_file(rig)
    missing_meta = [c for c in final if c not in scene_meta]
    log.append(f"combined clips in file: {len(final)}")
    log.append(f"combined clip metadata entries: {len(scene_meta)}"
               + (f"  MISSING META: {missing_meta}" if missing_meta else ""))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, copy=True)
    log.append(f"saved: {out} ({os.path.getsize(out) / 1e6:.1f} MB)")
    _write_log(log)
    for line in log:
        print(line)
    print(f"CONSOLIDATE_OK clips={len(final)}")


def _write_log(log):
    exports = os.path.join(ANIM_ROOT, "exports")
    os.makedirs(exports, exist_ok=True)
    with open(os.path.join(exports, "consolidate_log.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    if argv and argv[0] == "--dump-manifest":
        dump_manifest(argv[1], argv[2])
        return
    base, out = BASE_MASTER, OUT_MASTER
    others = list(OTHER_MASTERS)
    i = 0
    while i < len(argv):
        if argv[i] == "--base":
            base = argv[i + 1]; i += 2
        elif argv[i] == "--out":
            out = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"Unknown arg: {argv[i]}")
    consolidate(base, others, out)


if __name__ == "__main__":
    main()
