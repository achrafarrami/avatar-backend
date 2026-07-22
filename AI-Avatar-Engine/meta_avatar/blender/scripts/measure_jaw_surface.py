"""One-off: find the frontmost (min Y) point of the meta_male head mesh in a
Z-band around the jaw/chin, to get a precise placement target for the beard
fit (the JawRoot-vertex-group-based anchor undershoots since the CC_Base_Head
group also covers cheek/jaw skin, not just a pure "chin surface" point)."""
import bpy, sys
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEMPLATE, PREFIX = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath=TEMPLATE)
body = bpy.data.objects[f"{PREFIX}_Body"]
arm = bpy.data.objects[f"{PREFIX}_Armature"]
mesh = body.data
n = len(mesh.vertices)
co = np.zeros(n*3)
mesh.shape_keys.key_blocks["Basis"].data.foreach_get("co", co)
co = co.reshape(n,3)
mw = np.array(body.matrix_world)
world = co @ mw[:3,:3].T + mw[:3,3]
head_origin = arm.matrix_world @ arm.data.bones["CC_Base_Head"].head_local
jaw_origin = arm.matrix_world @ arm.data.bones["CC_Base_JawRoot"].head_local
print(f"[jaw] head_origin={list(head_origin)} jaw_origin={list(jaw_origin)}")
# chin/jaw band: within +/- 3cm of jaw origin Z, near midline (|x|<3cm)
z0 = float(jaw_origin.z)
band = (np.abs(world[:,2]-z0) < 0.03) & (np.abs(world[:,0]) < 0.03)
pts = world[band]
print(f"[jaw] {len(pts)} verts in chin band")
if len(pts):
    frontmost = pts[pts[:,1].argmin()]
    print(f"[jaw] frontmost (min Y) point in chin band: {list(frontmost)}")
    print(f"[jaw] relative to head_origin: {list(frontmost - np.array([head_origin.x, head_origin.y, head_origin.z]))}")
