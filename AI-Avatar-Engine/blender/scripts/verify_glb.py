"""
Verify an exported avatar GLB by re-importing it into a clean scene:
prints meshes, morph target counts, bone count, materials — and renders a
front-view preview.

Usage:
  blender --background --python verify_glb.py -- <avatar.glb> [preview.png]
"""
import bpy
import math
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
glb_path = argv[0]
preview = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

print("\n=== GLB VERIFICATION:", glb_path, "===")
face_z = 1.6
for obj in bpy.context.scene.objects:
    if obj.type == 'ARMATURE':
        print(f"ARMATURE {obj.name}: {len(obj.data.bones)} bones")
        bone = obj.data.bones.get("CC_Base_Head")
        if bone:
            face_z = (obj.matrix_world @ bone.head_local).z + 0.02
    elif obj.type == 'MESH':
        mesh = obj.data
        n_keys = len(mesh.shape_keys.key_blocks) - 1 if mesh.shape_keys else 0
        print(f"MESH {obj.name}: {len(mesh.vertices)} verts, "
              f"{n_keys} morph targets, "
              f"{len(obj.material_slots)} materials")

print(f"Total materials: {len(bpy.data.materials)}")
print(f"Total images: {len(bpy.data.images)}")

if preview:
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 500
    scene.render.resolution_y = 500
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.55, 1)
    scene.world = world
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, -0.55, face_z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    light_data = bpy.data.lights.new("L", type='SUN')
    light_data.energy = 3.0
    light = bpy.data.objects.new("L", light_data)
    scene.collection.objects.link(light)
    light.rotation_euler = (math.radians(60), 0, 0)
    scene.render.filepath = preview
    bpy.ops.render.render(write_still=True)
    print("Preview:", preview)
