"""Clip registry + declarative build API.

A clip = one recipe (id, category, duration, loop, build fn). Building a
clip creates one Action per animated datablock (armature + each mesh's
shape keys), all pushed onto NLA tracks NAMED THE CLIP ID — the glTF
exporter merges same-named tracks into a single named glTF animation.

Recipe modules live in animations/scripts/clips/*.py and either call
`register(ClipRecipe(...))` at import time or use the @clip decorator.
"""
import bpy
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field

from .keying import ClipContext

SCENE_META_PROP = "anim_clips"  # scene custom prop: clip id -> metadata


@dataclass
class ClipRecipe:
    cid: str
    category: str          # idle | gesture | emotion | locomotion | test ...
    seconds: float
    build: callable
    loop: bool = False
    framing: str = 'bust'  # face | bust | body  (preview camera)
    still_frame: float = 0.45  # fraction through the clip for still renders
    description: str = ''
    seed: int = None


REGISTRY = {}


def register(recipe):
    if recipe.cid in REGISTRY:
        print(f"WARNING: clip '{recipe.cid}' re-registered (overriding)")
    REGISTRY[recipe.cid] = recipe
    return recipe


def clip(cid, category, seconds, **kw):
    """Decorator: @clip("blink", "idle", 1.0, loop=False, framing='face')"""
    def deco(fn):
        register(ClipRecipe(cid=cid, category=category, seconds=seconds,
                            build=fn, **kw))
        return fn
    return deco


def load_recipe_modules(clips_dir):
    """Import every .py in clips_dir so recipes self-register."""
    loaded = []
    for fname in sorted(os.listdir(clips_dir)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        mod_name = f"anim_clips_{fname[:-3]}"
        path = os.path.join(clips_dir, fname)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        for r in getattr(mod, "CLIPS", []):
            register(r)
        loaded.append(fname)
    return loaded


# ---------------------------------------------------------------------------
def _iter_datablocks(rig):
    """The armature object + every mesh's shape-key datablock."""
    yield rig.armature
    for obj in rig.meshes:
        yield obj.data.shape_keys


def remove_clip(rig, cid):
    """Delete the clip's NLA tracks + actions everywhere (idempotent)."""
    removed = 0
    for db in _iter_datablocks(rig):
        adt = db.animation_data
        if not adt:
            continue
        for track in [t for t in adt.nla_tracks if t.name == cid]:
            for strip in list(track.strips):
                act = strip.action
                track.strips.remove(strip)
                if act and act.users == 0:
                    bpy.data.actions.remove(act)
            adt.nla_tracks.remove(track)
            removed += 1
    # stale actions from interrupted builds
    for act in [a for a in bpy.data.actions
                if (a.name == cid or a.name.startswith(cid + "__"))
                and a.users == 0]:
        bpy.data.actions.remove(act)
    return removed


def build_clip(rig, recipe):
    """Build (or rebuild) one clip. Returns the flush stats."""
    remove_clip(rig, recipe.cid)
    ctx = ClipContext(rig, recipe.cid, recipe.seconds, loop=recipe.loop,
                      seed=recipe.seed)
    recipe.build(ctx)
    stats = ctx.flush()
    meta = {
        "category": recipe.category,
        "loop": recipe.loop,
        "framing": recipe.framing,
        "still_frame": recipe.still_frame,
        "description": recipe.description,
        "frame_start": stats["frame_start"],
        "frame_end": stats["frame_end"],
        "seconds": recipe.seconds,
        "bones": stats["bones"],
        "shape_keys": stats["shape_keys"],
        "keyframes_total": stats["keyframes_total"],
        "channels": stats["channels"],
    }
    _store_meta(recipe.cid, meta)
    for w in stats["warnings"]:
        print(f"  WARN [{recipe.cid}] {w}")
    return stats


def _store_meta(cid, meta):
    scene = bpy.context.scene
    all_meta = json.loads(scene.get(SCENE_META_PROP, "{}"))
    all_meta[cid] = meta
    scene[SCENE_META_PROP] = json.dumps(all_meta)


def stored_meta(cid=None):
    all_meta = json.loads(bpy.context.scene.get(SCENE_META_PROP, "{}"))
    return all_meta if cid is None else all_meta.get(cid)


def clips_in_file(rig):
    """Clip ids present as NLA tracks in the open file."""
    ids = []
    for db in _iter_datablocks(rig):
        adt = db.animation_data
        if adt:
            for t in adt.nla_tracks:
                if t.name not in ids:
                    ids.append(t.name)
    return ids


def set_clip_solo(rig, cid):
    """Mute every track except `cid`'s (preview isolation)."""
    found = False
    for db in _iter_datablocks(rig):
        adt = db.animation_data
        if not adt:
            continue
        for t in adt.nla_tracks:
            t.mute = (t.name != cid)
            if t.name == cid:
                found = True
        if adt.action:
            adt.action = None
    return found


def reset_to_rest(rig):
    """Zero every shape-key value and clear every pose-bone transform to rest.

    Muting an NLA track (set_clip_solo) stops it DRIVING a channel but leaves
    the channel's last-evaluated value stuck. Without this reset, a clip that
    ends holding a nonzero jaw/pose contaminates the next clip's render for any
    channel that clip doesn't itself animate. Call after set_clip_solo, before
    frame_set — the soloed strip re-drives its own channels on evaluation; the
    rest are left at rest instead of inheriting stale values.
    """
    for obj in rig.meshes:
        sk = obj.data.shape_keys
        if not sk:
            continue
        for kb in sk.key_blocks[1:]:
            kb.value = 0.0
    for pb in rig.armature.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)


def unmute_all(rig):
    for db in _iter_datablocks(rig):
        adt = db.animation_data
        if adt:
            for t in adt.nla_tracks:
                t.mute = False


def keep_only_clips(rig, cids):
    """Delete every clip track not in `cids` (per-category export path)."""
    for existing in clips_in_file(rig):
        if existing not in cids:
            remove_clip(rig, existing)
