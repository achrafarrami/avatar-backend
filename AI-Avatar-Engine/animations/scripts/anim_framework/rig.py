"""Rig discovery + safety layer for the animation framework.

Prefix-agnostic: works on any of the 4 templates (MetaMale/MetaFemale/
Male/Female) because it discovers the armature and every shape-keyed mesh
at runtime instead of hardcoding object names.

Hard rule enforced here: IDENTITY shape keys are NEVER animated. The 20
customization morphs + the meta-only head_size/body_weight (and anything
declared in morph_definitions.json, read when available) are refused by
the keying API via `assert_animatable_key`.
"""
import bpy
import json
import os

# The 20 canonical customization morphs (mirrors CUSTOMIZATION_MORPHS in
# blender/scripts/inspect_asset.py) + meta-only identity morphs. Baseline
# guard even when morph_definitions.json is not found on disk.
IDENTITY_KEYS_BASE = frozenset({
    "face_width", "jaw_width", "jaw_height", "chin_size", "nose_width",
    "nose_length", "eye_size", "eye_distance", "lip_thickness", "mouth_width",
    "cheek_size", "forehead_height", "eyebrow_height", "eye_tilt",
    "nose_bridge_height", "nose_tip_size", "ear_size", "jaw_angle",
    "cheekbone_height", "philtrum_length",
    # meta-only stylization morphs (meta.map.json -> meta_morphs)
    "head_size", "body_weight",
})

# Utility depth-tuning keys (tearline/eye-occlusion fitting) — not identity,
# but not animation either. Keying them raises too.
UTILITY_PREFIXES = ("TL ", "EO ")

# Location keyframes are restricted to the hip; CC_Base_BoneRoot is never
# keyed at all (root convention: loops are in-place, the hip carries turn
# yaw / vertical / lateral motion).
LOC_ALLOWED_BONES = frozenset({"CC_Base_Hip"})
FORBIDDEN_BONES = frozenset({"CC_Base_BoneRoot"})

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# animations/scripts/anim_framework -> repo AI-Avatar-Engine root
_ENGINE_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))


def _identity_keys_from_defs():
    """Union in every target shape key from morph_definitions.json, if found."""
    path = os.path.join(_ENGINE_ROOT, "blender", "scripts", "morph_definitions.json")
    keys = set()
    try:
        with open(path) as f:
            defs = json.load(f)
        for spec in defs.get("params", {}).values():
            for t in spec.get("targets", []):
                keys.add(t["shape_key"])
    except (OSError, ValueError, KeyError):
        pass
    return keys


IDENTITY_KEYS = frozenset(IDENTITY_KEYS_BASE | _identity_keys_from_defs())


class RigError(RuntimeError):
    pass


class Rig:
    """Discovered armature + all shape-keyed meshes of the open scene."""

    def __init__(self, scene=None):
        scene = scene or bpy.context.scene
        self.scene = scene
        armatures = [o for o in scene.objects if o.type == 'ARMATURE']
        if len(armatures) != 1:
            raise RigError(f"Expected exactly 1 armature, found {len(armatures)}")
        self.armature = armatures[0]
        # "MetaMale_Armature" -> "MetaMale"
        self.prefix = self.armature.name.rsplit("_Armature", 1)[0]
        self.meshes = [o for o in scene.objects
                       if o.type == 'MESH' and o.data.shape_keys]
        if not self.meshes:
            raise RigError("No shape-keyed meshes found")
        self.bone_names = {b.name for b in self.armature.data.bones}
        # key name -> [mesh objects that have it]   (UNION across all meshes —
        # e.g. Eye_Pupil_Dilate lives ONLY on CC_Base_Eye, never on the body)
        self.key_meshes = {}
        for obj in self.meshes:
            for kb in obj.data.shape_keys.key_blocks[1:]:
                self.key_meshes.setdefault(kb.name, []).append(obj)

    # -- bones ----------------------------------------------------------
    def bone(self, name):
        """Resolve a bone name; accepts short form ('Head' -> 'CC_Base_Head')."""
        if name in self.bone_names:
            resolved = name
        elif f"CC_Base_{name}" in self.bone_names:
            resolved = f"CC_Base_{name}"
        else:
            raise RigError(f"Unknown bone: {name}")
        if resolved in FORBIDDEN_BONES:
            raise RigError(f"{resolved} is never keyed (root convention: "
                           "the hip carries yaw/vertical/lateral motion)")
        return resolved

    def pose_bone(self, name):
        return self.armature.pose.bones[self.bone(name)]

    def assert_loc_allowed(self, name):
        resolved = self.bone(name)
        if resolved not in LOC_ALLOWED_BONES:
            raise RigError(f"Location keys are restricted to "
                           f"{sorted(LOC_ALLOWED_BONES)}; got {resolved}")
        return resolved

    def world_to_bone_local(self, name, vec):
        """Express an armature-space (cm) direction in the bone's rest frame
        (for pose_bone.location, which lives in bone-local space)."""
        b = self.armature.data.bones[self.bone(name)]
        return b.matrix_local.to_3x3().inverted() @ vec

    def bone_world_head(self, name, evaluated=False):
        """World-space (meters) head position of a bone. With evaluated=True
        the current pose/animation is applied."""
        if evaluated:
            deps = bpy.context.evaluated_depsgraph_get()
            arm = self.armature.evaluated_get(deps)
            return arm.matrix_world @ arm.pose.bones[self.bone(name)].head
        b = self.armature.data.bones[self.bone(name)]
        return self.armature.matrix_world @ b.head_local

    # -- shape keys -----------------------------------------------------
    def has_key(self, key_name):
        return key_name in self.key_meshes

    def meshes_with_key(self, key_name):
        """Every mesh object carrying this shape key (cross-mesh contract:
        callers key ALL of them). Case-sensitive by design (V_Tongue_up)."""
        return self.key_meshes.get(key_name, [])

    def key_range(self, key_name):
        """(slider_min, slider_max) of the key on its first carrier mesh."""
        obj = self.key_meshes[key_name][0]
        kb = obj.data.shape_keys.key_blocks[key_name]
        return kb.slider_min, kb.slider_max

    def assert_animatable_key(self, key_name):
        if key_name in IDENTITY_KEYS:
            raise RigError(f"'{key_name}' is an IDENTITY morph — identity is "
                           "never keyframed (it is baked per-avatar at export)")
        if key_name.startswith(UTILITY_PREFIXES):
            raise RigError(f"'{key_name}' is a tearline/occlusion fitting "
                           "shape, not an animation target")
        if key_name not in self.key_meshes:
            raise RigError(f"Shape key '{key_name}' not found on any mesh")

    # -- reporting ------------------------------------------------------
    def clear_default_animation(self):
        """Drop the template's shipped rest action (it stomps poses) and any
        stale active actions on shape keys."""
        removed = []
        adt = self.armature.animation_data
        if adt and adt.action:
            removed.append(adt.action.name)
            act = adt.action
            adt.action = None
            if act.users == 0:
                bpy.data.actions.remove(act)
        for obj in self.meshes:
            sadt = obj.data.shape_keys.animation_data
            if sadt and sadt.action:
                sadt.action = None
        return removed

    def dump_key_inventory(self, out_path):
        """Write the per-mesh shape key availability map (authors check this
        to know where a key lives — see README)."""
        inv = {"armature": self.armature.name,
               "meshes": {o.name: [kb.name for kb in
                                   o.data.shape_keys.key_blocks[1:]]
                          for o in self.meshes},
               "key_to_meshes": {k: [o.name for o in v]
                                 for k, v in sorted(self.key_meshes.items())},
               "identity_keys_guarded": sorted(
                   k for k in IDENTITY_KEYS if k in self.key_meshes)}
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(inv, f, indent=1)
        return out_path
