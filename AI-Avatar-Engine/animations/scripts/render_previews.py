"""Render QA previews for built clips.

Per clip -> animations/previews/<clip_id>/ :
  front.png side.png persp.png   stills at the clip's action frame
  wireframe.png                  front still with wireframe overlay
  strip.png                      contact sheet, every Nth frame (frame # stamped)
  <clip_id>.mp4                  front view, full duration, EEVEE + FFMPEG H.264
  meta.json                      fps, frame_count, duration_s, keyframe counts,
                                 bones + shape keys used

Usage:
  blender --background --python render_previews.py -- [all | cid [cid ...]]
      [--master <path.blend>] [--no-mp4]
"""
import bpy
import json
import math
import os
import shutil
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from anim_framework import clips as clips_mod            # noqa: E402
from anim_framework.rig import Rig                       # noqa: E402

ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_MASTER = os.path.join(ANIM_ROOT, "blender",
                              "anim_master_meta_male.blend")
PREVIEWS = os.path.join(ANIM_ROOT, "previews")

STILL_RES = 640
TILE_RES = 220
MP4_RES = 512
STRIP_MAX_TILES = 16

FRAMINGS = {  # name -> (z_offset_from_EYES_m, distance_m, lens_mm)
    'face': (-0.07, 0.50, 85),
    'bust': (-0.10, 0.95, 70),
    'body': (-0.70, 2.65, 50),
}


def setup_scene(rig):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 16
    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = \
        (0.52, 0.53, 0.58, 1)
    scene.world = world
    cam_data = bpy.data.cameras.new("PrevCam")
    cam = bpy.data.objects.new("PrevCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    key = bpy.data.lights.new("Key", type='SUN')
    key.energy = 3.2
    ko = bpy.data.objects.new("Key", key)
    scene.collection.objects.link(ko)
    ko.rotation_euler = (math.radians(60), 0, math.radians(-25))
    fill = bpy.data.lights.new("Fill", type='SUN')
    fill.energy = 1.1
    fo = bpy.data.objects.new("Fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(75), 0, math.radians(35))
    # anchor framing on the eyes (robust across head sizes/styles)
    try:
        anchor_z = rig.bone_world_head("CC_Base_L_Eye").z
    except Exception:
        anchor_z = rig.bone_world_head("CC_Base_Head").z + 0.08
    return cam, anchor_z


def place_cam(cam, view, framing, head_z):
    dz, dist, lens = FRAMINGS[framing]
    z = head_z + dz
    cam.data.lens = lens
    if view == 'front':
        cam.location = (0, -dist, z)
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == 'side':
        cam.location = (dist, 0, z)
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    elif view == 'persp':
        a = math.radians(32)
        cam.location = (dist * math.sin(a), -dist * math.cos(a), z + 0.10)
        cam.rotation_euler = (math.radians(83), 0, a)


def render_still(path, res=STILL_RES):
    scene = bpy.context.scene
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.image_settings.media_type = 'IMAGE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_wireframe(rig, path):
    """Front still with black wires overlaid (temp modifiers + material —
    the file is never saved by this script, so nothing leaks)."""
    wire_mat = bpy.data.materials.get("PreviewWireMat")
    if wire_mat is None:
        wire_mat = bpy.data.materials.new("PreviewWireMat")
        wire_mat.use_nodes = True
        bsdf = wire_mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1)
            bsdf.inputs["Roughness"].default_value = 1.0
    mods = []
    for obj in rig.meshes:
        obj.data.materials.append(wire_mat)
        m = obj.modifiers.new("PreviewWire", 'WIREFRAME')
        m.thickness = 0.0035
        m.use_replace = False
        m.material_offset = 100  # clamps to the last slot = wire material
        mods.append((obj, m))
    render_still(path)
    for obj, m in mods:
        obj.modifiers.remove(m)
        obj.data.materials.pop(index=len(obj.data.materials) - 1)


def render_strip(cid, f_start, f_end, out_path, tmp_dir):
    scene = bpy.context.scene
    os.makedirs(tmp_dir, exist_ok=True)
    n_frames = f_end - f_start + 1
    step = max(1, math.ceil(n_frames / STRIP_MAX_TILES))
    frames = list(range(f_start, f_end + 1, step))
    if frames[-1] != f_end:
        frames.append(f_end)
    scene.render.use_stamp = True
    scene.render.use_stamp_frame = True
    scene.render.use_stamp_date = False
    scene.render.use_stamp_time = False
    scene.render.use_stamp_render_time = False
    scene.render.use_stamp_filename = False
    scene.render.use_stamp_camera = False
    scene.render.use_stamp_scene = False
    scene.render.stamp_font_size = 16
    tiles = []
    for f in frames:
        scene.frame_set(f)
        p = os.path.join(tmp_dir, f"t{f:05d}.png")
        render_still(p, res=TILE_RES)
        tiles.append(p)
    scene.render.use_stamp = False

    cols = min(4, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sheet = np.zeros((rows * TILE_RES, cols * TILE_RES, 4), dtype=np.float32)
    for i, p in enumerate(tiles):
        img = bpy.data.images.load(p)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(
            TILE_RES, TILE_RES, 4)
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * TILE_RES  # image origin is bottom-left
        sheet[y0:y0 + TILE_RES, c * TILE_RES:(c + 1) * TILE_RES] = px
        bpy.data.images.remove(img)
    out = bpy.data.images.new("strip", cols * TILE_RES, rows * TILE_RES,
                              alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = out_path
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return len(tiles)


def render_mp4(cid, f_start, f_end, out_dir):
    scene = bpy.context.scene
    scene.frame_start = f_start
    scene.frame_end = f_end
    scene.render.resolution_x = MP4_RES
    scene.render.resolution_y = MP4_RES
    scene.render.image_settings.media_type = 'VIDEO'  # Blender 5.x gate
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'      # .mp4 container
    scene.render.ffmpeg.codec = 'H264'        # plain H.264 (OpenCV-readable)
    # HIGH, not MEDIUM: at MEDIUM the encoder emits skip-blocks for the idles'
    # sub-pixel micro-drift, freezing 14 of every 15 frames (GOP staircase) and
    # false-flagging DEAD ZONE/METRONOME in QA's motion-energy analysis.
    scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
    # Long GOP: at 15, H.264 emits an I-frame refresh pulse every 0.5 s even at
    # near-lossless CRF on near-static content, and QA's autocorrelation pass
    # latches onto that comb as a false 0.50 s "metronome".
    scene.render.ffmpeg.gopsize = 250
    target = os.path.join(out_dir, f"{cid}.mp4")
    scene.render.filepath = target
    bpy.ops.render.render(animation=True)
    if not os.path.isfile(target):  # Blender may append frame ranges
        for f in os.listdir(out_dir):
            if f.startswith(cid) and f.endswith(".mp4"):
                os.replace(os.path.join(out_dir, f), target)
                break
    return target


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    master, no_mp4, ids = DEFAULT_MASTER, False, []
    i = 0
    while i < len(argv):
        if argv[i] == "--master":
            master = argv[i + 1]; i += 2
        elif argv[i] == "--no-mp4":
            no_mp4 = True; i += 1
        else:
            ids.append(argv[i]); i += 1

    bpy.ops.wm.open_mainfile(filepath=master)
    rig = Rig()
    fps = bpy.context.scene.render.fps
    in_file = clips_mod.clips_in_file(rig)
    if not ids or ids == ["all"]:
        ids = in_file
    missing = [c for c in ids if c not in in_file]
    if missing:
        raise SystemExit(f"Clips not in master: {missing} (have {in_file})")

    for cid in ids:
        meta = clips_mod.stored_meta(cid) or {}
        f0 = meta.get("frame_start", 1)
        f1 = meta.get("frame_end", 100)
        framing = meta.get("framing", "bust")
        out_dir = os.path.join(PREVIEWS, cid)
        os.makedirs(out_dir, exist_ok=True)

        clips_mod.set_clip_solo(rig, cid)
        # Clear stale shape-key/pose values left by the previously-soloed clip;
        # muting a track stops it driving but leaves its last value stuck.
        clips_mod.reset_to_rest(rig)
        cam, head_z = setup_scene(rig)
        scene = bpy.context.scene
        scene.frame_start = f0
        scene.frame_end = f1

        still_f = f0 + int(meta.get("still_frame", 0.45) * (f1 - f0))
        scene.frame_set(still_f)
        for view in ('front', 'side', 'persp'):
            place_cam(cam, view, framing, head_z)
            render_still(os.path.join(out_dir, f"{view}.png"))
        place_cam(cam, 'front', framing, head_z)
        render_wireframe(rig, os.path.join(out_dir, "wireframe.png"))
        n_tiles = render_strip(cid, f0, f1, os.path.join(out_dir, "strip.png"),
                               os.path.join(out_dir, "_strip_tmp"))
        place_cam(cam, 'front', framing, head_z)
        mp4 = None
        if not no_mp4:
            mp4 = render_mp4(cid, f0, f1, out_dir)

        frame_count = f1 - f0 + 1
        with open(os.path.join(out_dir, "meta.json"), "w") as fjson:
            json.dump({
                "clip_id": cid,
                "fps": fps,
                "frame_count": frame_count,
                "duration_s": round((f1 - f0) / fps, 4),
                "loop": meta.get("loop", False),
                "category": meta.get("category", ""),
                "description": meta.get("description", ""),
                "still_frame": still_f,
                "strip_tiles": n_tiles,
                "keyframes_total": meta.get("keyframes_total", 0),
                "keyframes_per_channel": meta.get("channels", {}),
                "bones_used": meta.get("bones", []),
                "shape_keys_used": meta.get("shape_keys", []),
            }, fjson, indent=1)
        print(f"PREVIEWED {cid} -> {out_dir}" +
              (f" ({os.path.basename(mp4)})" if mp4 else " (no mp4)"))

        # tear down per-clip scene extras so the next clip starts clean
        for name in ("PrevCam", "Key", "Fill"):
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj)


if __name__ == "__main__":
    main()
