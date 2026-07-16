"""
Import a CC3+ FBX into a fresh scene and save it as an engine template.

Renames the armature and body mesh to <Prefix>_Armature / <Prefix>_Body;
secondary meshes keep their CC names (shared across all CC characters).

Usage:
  blender --background --python import_template.py -- \
      <source.fbx> <out.blend> <Prefix>
"""
import bpy
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
fbx_path, blend_out, prefix = argv[0], argv[1], argv[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

for obj in bpy.context.scene.objects:
    if obj.type == 'ARMATURE':
        obj.name = f"{prefix}_Armature"
    elif obj.type == 'MESH' and obj.data.name.startswith('CC_Base_Body'):
        obj.name = f"{prefix}_Body"

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print(f"Saved: {blend_out}")
print(f"Objects: {[o.name for o in bpy.context.scene.objects]}")
