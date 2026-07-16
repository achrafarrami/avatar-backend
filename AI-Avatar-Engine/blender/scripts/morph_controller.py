"""
Morph abstraction layer for the AI-Avatar-Engine.

Users (and later, the AI) never touch the 169 raw shape keys. They provide
semantic parameters in 0..1 space (0.5 = neutral), e.g.:

    {"face_width": 0.55, "nose_width": 0.3, "jaw_angle": 0.8}

This controller translates each parameter into one or more underlying shape
key values via `morph_definitions.json`:

    key_value = (param - 0.5) * 2 * target_weight        # -> -1..1

When two params drive the same shape key, contributions are summed and
clamped to the key's slider range. Keys are applied to every mesh in the
scene that has a key of that name (body + tearline/occlusion followers).

Usage (headless):
  blender --background template.blend --python morph_controller.py -- \
      --params '{"face_width": 0.8, "chin_size": 0.7}' \
      [--render out.png] [--save-as out.blend]

Usage (as a module inside Blender):
  from morph_controller import MorphController
  mc = MorphController()
  mc.apply({"face_width": 0.8})
  mc.reset()
"""
import bpy
import json
import math
import os
import sys

DEFAULT_DEFINITIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "morph_definitions.json")


class MorphController:
    def __init__(self, definitions_path=None):
        path = definitions_path or DEFAULT_DEFINITIONS
        with open(path) as f:
            self.defs = json.load(f)
        self.params_spec = self.defs["params"]
        neutral = self.defs["param_space"]["neutral"]
        self.neutral = neutral

    # ------------------------------------------------------------------
    def _meshes_with_key(self, key_name):
        for obj in bpy.context.scene.objects:
            if obj.type != 'MESH' or not obj.data.shape_keys:
                continue
            kb = obj.data.shape_keys.key_blocks.get(key_name)
            if kb is not None:
                yield kb

    # ------------------------------------------------------------------
    def compute_key_values(self, params):
        """Translate user params -> {shape_key_name: value}. Pure function,
        no Blender access — reusable logic for backend/runtime ports."""
        unknown = [p for p in params if p not in self.params_spec]
        if unknown:
            raise KeyError(f"Unknown morph parameters: {unknown}")

        key_values = {}
        for name, value in params.items():
            value = max(0.0, min(1.0, float(value)))
            centered = (value - self.neutral) * 2.0  # -> -1..1
            for target in self.params_spec[name]["targets"]:
                k = target["shape_key"]
                key_values[k] = key_values.get(k, 0.0) + centered * target["weight"]
        return key_values

    # ------------------------------------------------------------------
    def apply(self, params, reset_first=True):
        """Apply user params to the open scene. Returns the applied
        {shape_key: value} map (post-clamping)."""
        if reset_first:
            self.reset()
        applied = {}
        for key_name, value in self.compute_key_values(params).items():
            found = False
            for kb in self._meshes_with_key(key_name):
                v = max(kb.slider_min, min(kb.slider_max, value))
                kb.value = v
                applied[key_name] = v
                found = True
            if not found:
                print(f"WARNING: shape key '{key_name}' not found on any mesh")
        return applied

    # ------------------------------------------------------------------
    def reset(self):
        """Zero every customization shape key on every mesh."""
        all_keys = set()
        for spec in self.params_spec.values():
            for t in spec["targets"]:
                all_keys.add(t["shape_key"])
        for key_name in all_keys:
            for kb in self._meshes_with_key(key_name):
                kb.value = 0.0

    # ------------------------------------------------------------------
    def list_params(self):
        return {
            name: {"label": s["label"], "category": s["category"],
                   "description": s["description"]}
            for name, s in self.params_spec.items()
        }


# ---------------------------------------------------------------------------
def _render_preview(filepath):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 500
    scene.render.resolution_y = 500

    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.55, 1)
    scene.world = world

    # auto-frame on the head bone so the same code works for every template
    face_z = 1.65
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            bone = obj.data.bones.get("CC_Base_Head")
            if bone:
                head_world = obj.matrix_world @ bone.head_local
                face_z = head_world.z + 0.02
            break

    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, -0.55, face_z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam

    light_data = bpy.data.lights.new("PreviewSun", type='SUN')
    light_data.energy = 3.0
    light = bpy.data.objects.new("PreviewSun", light_data)
    scene.collection.objects.link(light)
    light.rotation_euler = (math.radians(60), 0, 0)

    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    params_json, render_path, save_path = None, None, None
    i = 0
    while i < len(argv):
        if argv[i] == "--params":
            params_json = argv[i + 1]; i += 2
        elif argv[i] == "--render":
            render_path = argv[i + 1]; i += 2
        elif argv[i] == "--save-as":
            save_path = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"Unknown argument: {argv[i]}")

    mc = MorphController()
    if params_json:
        if os.path.isfile(params_json):
            with open(params_json) as f:
                params = json.load(f)
        else:
            params = json.loads(params_json)
        applied = mc.apply(params)
        print("Applied user params:", json.dumps(params, indent=2))
        print("Resulting shape key values:", json.dumps(applied, indent=2))
    if render_path:
        _render_preview(render_path)
        print("Preview rendered:", render_path)
    if save_path:
        bpy.ops.wm.save_as_mainfile(filepath=save_path)
        print("Saved:", save_path)


if __name__ == "__main__":
    main()
