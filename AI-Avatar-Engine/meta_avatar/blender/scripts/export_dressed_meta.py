"""
Export ONE dressed meta avatar GLB for the T4 verification step (Phase 3).

Opens a meta template, equips it with a set of wardrobe GLBs (skinned shells
re-bound to the meta armature by bone name -- same technique as
test_clothing_fit.py / SandboxViewer.attachSkinned), keeps the 20 identity
keys live (dev-build convention, same as export_avatar_glb.py --keep-identity)
and exports a single combined GLB so blender/scripts/verify_glb.py can prove
the export pipeline still produces a valid rig + skin + materials once
clothing meshes are riding on the same armature as the body.

This does not touch export_avatar_glb.py or any realistic-pipeline file --
it is a standalone script for the meta clothing QA pass.

Usage:
  blender --background --python export_dressed_meta.py -- \
      <meta_template.blend> <Prefix> <out.glb> <item_glb> [<item_glb> ...]
"""
import bpy
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, PREFIX, OUT_GLB = argv[0], argv[1], argv[2]
ITEM_GLBS = argv[3:]

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(TEMPLATE))
arm = bpy.data.objects[f"{PREFIX}_Armature"]

for glb in ITEM_GLBS:
    before = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(glb))
    imported = [o for o in bpy.data.objects if o.name not in before]
    imported_arm = next((o for o in imported if o.type == 'ARMATURE'), None)
    # Blender's gltf importer sometimes adds small placeholder mesh objects
    # (e.g. "Icosphere", no vertex groups) alongside the real skinned shell --
    # drop anything that isn't actually bound to the skeleton. Build both
    # lists before deleting so we never iterate over a freed object.
    junk = [o for o in imported if o.type == 'MESH' and not o.vertex_groups]
    real_meshes = [o for o in imported if o.type == 'MESH' and o.vertex_groups]
    for o in junk:
        bpy.data.objects.remove(o, do_unlink=True)
    for mesh in real_meshes:
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE':
                mod.object = arm
        # keep_transform reparent -- see test_clothing_fit.py for why naive
        # matrix_parent_inverse = arm.matrix_world.inverted() is wrong here.
        with bpy.context.temp_override(active_object=arm,
                                        selected_editable_objects=[mesh, arm]):
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    if imported_arm is not None:
        bpy.data.objects.remove(imported_arm, do_unlink=True)
    print(f"[export-dressed-meta] equipped {os.path.basename(glb)}")

os.makedirs(os.path.dirname(os.path.abspath(OUT_GLB)) or ".", exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=os.path.abspath(OUT_GLB),
    export_format='GLB',
    export_morph=True,
    export_morph_normal=True,
    export_skins=True,
    export_animations=False,
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_yup=True,
)
size_mb = os.path.getsize(OUT_GLB) / 1e6
print(f"[export-dressed-meta] Exported: {OUT_GLB} ({size_mb:.1f} MB)")
