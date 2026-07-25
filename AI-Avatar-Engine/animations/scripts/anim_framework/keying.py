"""Keyframe authoring API — layered channels flushed to Blender actions.

Generators never write Blender fcurves directly. They add keys to named
LAYERS on a ClipContext; flush() merges layers (values sum per channel),
converts per-bone axis-angle layers to quaternion keys, fans shape keys out
to EVERY mesh that carries the key, enforces loop closure, and pushes one
NLA track per datablock, all named after the clip id (the glTF exporter
merges same-named tracks into one named animation).

Rotation convention (calibrated on the meta rig, see README):
  head/neck/spine family: +x pitch-down, +y yaw-left, +z roll-right-tilt
  JawRoot: +z opens the mouth. Clavicle raise: L +z / R -z.
  Finger curl: +x. Euler order XYZ (small angles, order-insensitive).
"""
import bpy
import math
import random
import zlib
from dataclasses import dataclass, field
from mathutils import Euler, Vector

from . import rig as rig_mod


@dataclass
class Key:
    frame: int
    value: float
    interp: str = 'BEZIER'        # BEZIER | LINEAR | CONSTANT
    handle: str = 'AUTO_CLAMPED'  # AUTO_CLAMPED | AUTO | VECTOR


class Channel:
    """One scalar stream inside one layer."""

    __slots__ = ("keys",)

    def __init__(self):
        self.keys = {}  # frame -> Key (last write wins)

    def add(self, frame, value, interp='BEZIER', handle='AUTO_CLAMPED'):
        frame = int(round(frame))
        self.keys[frame] = Key(frame, float(value), interp, handle)

    def sorted_keys(self):
        return [self.keys[f] for f in sorted(self.keys)]

    def sample(self, frame):
        """Smoothstep interpolation between this layer's keys (used only when
        several layers touch the same channel and must be merged)."""
        if not self.keys:
            return 0.0
        frames = sorted(self.keys)
        if frame <= frames[0]:
            return self.keys[frames[0]].value
        if frame >= frames[-1]:
            return self.keys[frames[-1]].value
        import bisect
        i = bisect.bisect_right(frames, frame)
        f0, f1 = frames[i - 1], frames[i]
        k0, k1 = self.keys[f0], self.keys[f1]
        if k0.interp == 'CONSTANT':
            return k0.value
        t = (frame - f0) / (f1 - f0)
        if k0.interp == 'LINEAR':
            return k0.value + (k1.value - k0.value) * t
        t = t * t * (3.0 - 2.0 * t)  # smoothstep ~ auto-clamped bezier
        return k0.value + (k1.value - k0.value) * t


class ClipContext:
    """Authoring context for one clip. Recipes receive this as `ctx`."""

    def __init__(self, rig, clip_id, seconds, loop=False, fps=30, seed=None):
        self.rig = rig
        self.clip_id = clip_id
        self.loop = bool(loop)
        self.fps = fps
        self.seconds = float(seconds)
        self.frame_start = 1
        self.frame_end = 1 + max(1, int(round(seconds * fps)))
        if seed is None:
            seed = zlib.crc32(clip_id.encode())
        self.rng = random.Random(seed)
        # (kind, target, sub, layer) -> Channel
        #   kind='rot'   target=bone  sub in 'xyz'      value = degrees
        #   kind='loc'   target=bone  sub in 0..2       value = cm (bone-local)
        #   kind='scale' target=bone  sub in 0..2       value = delta from 1.0
        #   kind='shape' target=key   sub=None          value = key value
        self._chan = {}
        self.warnings = []

    # -- helpers --------------------------------------------------------
    def sec(self, seconds):
        """Convert seconds to a frame count."""
        return int(round(seconds * self.fps))

    def at(self, seconds):
        """Absolute frame at `seconds` from clip start."""
        return self.frame_start + self.sec(seconds)

    def _get(self, kind, target, sub, layer):
        return self._chan.setdefault((kind, target, sub, layer), Channel())

    # -- bone rotation --------------------------------------------------
    def key_bone_axis(self, bone, frame, axis, degrees, layer='base',
                      interp='BEZIER', handle='AUTO_CLAMPED'):
        """Key one local-axis rotation (degrees) on `layer`. Layers touching
        the same bone are summed at flush and converted to quaternions."""
        b = self.rig.bone(bone)
        if axis not in 'xyz':
            raise ValueError(f"axis must be x/y/z, got {axis}")
        self._get('rot', b, axis, layer).add(frame, degrees, interp, handle)

    # semantic family (head/neck/spine chain — calibrated signs)
    def pitch(self, bone, frame, deg, layer='base', **kw):
        """+deg = tip forward/down."""
        self.key_bone_axis(bone, frame, 'x', deg, layer, **kw)

    def yaw(self, bone, frame, deg, layer='base', **kw):
        """+deg = turn toward the character's LEFT."""
        self.key_bone_axis(bone, frame, 'y', deg, layer, **kw)

    def roll(self, bone, frame, deg, layer='base', **kw):
        """+deg = tilt toward the character's LEFT shoulder."""
        self.key_bone_axis(bone, frame, 'z', -deg, layer, **kw)

    def jaw_open(self, frame, deg, layer='jaw', **kw):
        """+deg opens the mouth (JawRoot local z; ~1cm chin drop per 10 deg)."""
        self.key_bone_axis("CC_Base_JawRoot", frame, 'z', deg, layer, **kw)

    def clavicle_raise(self, side, frame, deg, layer='base', **kw):
        """+deg lifts the shoulder tip. side 'L' or 'R' (signs mirrored)."""
        sign = 1.0 if side == 'L' else -1.0
        self.key_bone_axis(f"CC_Base_{side}_Clavicle", frame, 'z',
                           sign * deg, layer, **kw)

    def finger_curl(self, side, finger, joint, frame, deg, layer='fingers', **kw):
        """+deg curls toward the palm. finger in Index/Mid/Ring/Pinky/Thumb."""
        self.key_bone_axis(f"CC_Base_{side}_{finger}{joint}", frame, 'x',
                           deg, layer, **kw)

    # -- bone location / scale ------------------------------------------
    def key_bone_loc_world(self, bone, frame, world_cm, layer='base',
                           interp='BEZIER', handle='AUTO_CLAMPED'):
        """Key a bone-location offset given in ARMATURE-space cm
        (x=lateral +left, y=back, z=up). Hip only, per root convention."""
        b = self.rig.assert_loc_allowed(bone)
        local = self.rig.world_to_bone_local(b, Vector(world_cm))
        for i in range(3):
            self._get('loc', b, i, layer).add(frame, local[i], interp, handle)

    def key_bone_scale(self, bone, frame, scale, layer='base',
                       interp='BEZIER', handle='AUTO_CLAMPED'):
        """Key bone scale. `scale` = uniform float or (x, y, z). Stored as
        delta from 1.0 so layers can sum."""
        b = self.rig.bone(bone)
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale)
        for i in range(3):
            self._get('scale', b, i, layer).add(frame, scale[i] - 1.0,
                                                interp, handle)

    # -- shape keys ------------------------------------------------------
    def key_shape(self, key_name, frame, value, layer='base',
                  interp='BEZIER', handle='AUTO_CLAMPED'):
        """Key a shape key. Fan-out to every carrier mesh happens at flush.
        Identity morphs are refused."""
        self.rig.assert_animatable_key(key_name)
        self._get('shape', key_name, None, layer).add(frame, value,
                                                      interp, handle)

    def key_shape_lr(self, pattern, frame, value, layer='base',
                     r_offset=0, r_scale=1.0, **kw):
        """Key an L/R pair with asymmetry. `pattern` contains '{S}', e.g.
        'Eye_Blink_{S}' or 'Eye_{S}_Look_Up'. The right side is keyed
        `r_offset` frames later at `value * r_scale`."""
        self.key_shape(pattern.format(S='L'), frame, value, layer, **kw)
        self.key_shape(pattern.format(S='R'), frame + r_offset,
                       value * r_scale, layer, **kw)

    # -- flush ----------------------------------------------------------
    def _merged_scalar(self, groups):
        """groups: {(target, sub): {layer: Channel}} -> per (target, sub)
        merged key list. Single-layer channels keep their exact keys; multi-
        layer channels are summed over the union of their key frames."""
        merged = {}
        for (target, sub), layers in groups.items():
            chans = list(layers.values())
            if len(chans) == 1:
                merged[(target, sub)] = chans[0].sorted_keys()
                continue
            frames = sorted({f for c in chans for f in c.keys})
            merged[(target, sub)] = [
                Key(f, sum(c.sample(f) for c in chans)) for f in frames]
        return merged

    def _close_loop(self, keys):
        """Force last frame == first frame value (loop contract)."""
        if not keys:
            return keys
        first = keys[0]
        if first.frame > self.frame_start:
            keys.insert(0, Key(self.frame_start, first.value,
                               first.interp, first.handle))
        last = keys[-1]
        if last.frame < self.frame_end:
            keys.append(Key(self.frame_end, keys[0].value,
                            keys[0].interp, keys[0].handle))
        elif abs(last.value - keys[0].value) > 1e-4:
            self.warnings.append(
                f"loop mismatch on a channel ({keys[0].value:.4f} vs "
                f"{last.value:.4f}) — forcing end=start")
            last.value = keys[0].value
        return keys

    def _write_fcurve(self, action, datablock, path, index, keys):
        fc = action.fcurve_ensure_for_datablock(datablock, path, index=index)
        for k in keys:
            fc.keyframe_points.insert(k.frame, k.value, options={'FAST'})
        fc.update()
        for kp, k in zip(fc.keyframe_points, keys):
            kp.interpolation = k.interp
            kp.handle_left_type = k.handle
            kp.handle_right_type = k.handle
        fc.update()
        if self.loop:
            if not any(m.type == 'CYCLES' for m in fc.modifiers):
                fc.modifiers.new('CYCLES')  # cycle-aware auto handles
        return len(keys)

    def _push_nla(self, datablock, action):
        adt = datablock.animation_data or datablock.animation_data_create()
        adt.action = None
        action.use_frame_range = True
        action.frame_start = self.frame_start
        action.frame_end = self.frame_end
        track = adt.nla_tracks.new()
        track.name = self.clip_id
        strip = track.strips.new(self.clip_id, self.frame_start, action)
        if getattr(strip, "action_slot", True) is None and action.slots:
            strip.action_slot = action.slots[0]
        strip.blend_type = 'REPLACE'
        strip.extrapolation = 'HOLD'
        track.mute = True  # master stays quiet; renderer/exporter unmute
        return strip

    def flush(self):
        """Write all buffered layers into Blender actions + NLA tracks.
        Returns a stats dict for meta.json / logging."""
        groups = {'rot': {}, 'loc': {}, 'scale': {}, 'shape': {}}
        for (kind, target, sub, layer), chan in self._chan.items():
            groups[kind].setdefault((target, sub), {})[layer] = chan

        stats = {"bones": set(), "shape_keys": set(),
                 "keyframes_total": 0, "channels": {}}
        arm = self.rig.armature

        # ---- armature action: rotations (euler-deg layers -> quats) ----
        bone_paths = []  # (path, index, keys)
        rot_merged = self._merged_scalar(groups['rot'])
        by_bone = {}
        for (bone, axis), keys in rot_merged.items():
            by_bone.setdefault(bone, {})[axis] = keys
        for bone, axes in by_bone.items():
            frames = sorted({k.frame for ks in axes.values() for k in ks})
            chan_of = {ax: Channel() for ax in axes}
            for ax, ks in axes.items():
                for k in ks:
                    chan_of[ax].keys[k.frame] = k
            quat_keys = [[] for _ in range(4)]
            prev = None
            for f in frames:
                e = [math.radians(chan_of[ax].sample(f)) if ax in chan_of
                     else 0.0 for ax in 'xyz']
                q = Euler(e, 'XYZ').to_quaternion()
                if prev is not None and prev.dot(q) < 0.0:
                    q.negate()
                prev = q
                for i in range(4):
                    quat_keys[i].append(Key(f, q[i]))
            path = f'pose.bones["{bone}"].rotation_quaternion'
            for i in range(4):
                bone_paths.append((path, i, quat_keys[i]))
            stats["bones"].add(bone)

        for kind, prop, base in (('loc', 'location', 0.0),
                                 ('scale', 'scale', 1.0)):
            for (bone, i), keys in self._merged_scalar(groups[kind]).items():
                keys = [Key(k.frame, k.value + base, k.interp, k.handle)
                        for k in keys]
                bone_paths.append(
                    (f'pose.bones["{bone}"].{prop}', i, keys))
                stats["bones"].add(bone)

        if bone_paths:
            act = bpy.data.actions.new(self.clip_id)
            adt = arm.animation_data or arm.animation_data_create()
            adt.action = act
            for path, index, keys in bone_paths:
                keys = self._close_loop(list(keys)) if self.loop else list(keys)
                n = self._write_fcurve(act, arm, path, index, keys)
                stats["keyframes_total"] += n
                stats["channels"][f"{path}[{index}]"] = n
            self._push_nla(arm, act)

        # ---- shape keys: fan out to every carrier mesh -----------------
        shape_merged = self._merged_scalar(groups['shape'])
        per_mesh = {}  # mesh obj -> [(key_name, keys)]
        for (key_name, _), keys in shape_merged.items():
            lo, hi = self.rig.key_range(key_name)
            keys = [Key(k.frame, min(hi, max(lo, k.value)), k.interp, k.handle)
                    for k in keys]
            for obj in self.rig.meshes_with_key(key_name):
                per_mesh.setdefault(obj, []).append((key_name, keys))
            stats["shape_keys"].add(key_name)
        for obj, entries in per_mesh.items():
            sk = obj.data.shape_keys
            act = bpy.data.actions.new(f"{self.clip_id}__{obj.name}")
            adt = sk.animation_data or sk.animation_data_create()
            adt.action = act
            for key_name, keys in entries:
                keys = self._close_loop(list(keys)) if self.loop else list(keys)
                n = self._write_fcurve(
                    act, sk, f'key_blocks["{key_name}"].value', 0, keys)
                stats["keyframes_total"] += n
                stats["channels"][f"{obj.name}.{key_name}"] = n
            self._push_nla(sk, act)

        stats["bones"] = sorted(stats["bones"])
        stats["shape_keys"] = sorted(stats["shape_keys"])
        stats["frame_start"] = self.frame_start
        stats["frame_end"] = self.frame_end
        stats["warnings"] = list(self.warnings)
        return stats
