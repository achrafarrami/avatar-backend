@echo off
rem Regenerates the *.mobile.glb builds the mobile app loads (10x smaller):
rem   textures resized to 1024 (64 for the animation GLB - its meshes are
rem   discarded after clip extraction) + WebP, then meshopt compression
rem   (EXT_meshopt_compression + KHR_mesh_quantization; decoded by three.js
rem   with MeshoptDecoder, already wired in avatar-mobile).
rem Run after re-exporting sandbox_meta_*.glb or avatar_animated_meta_male.glb.
rem Order matters: meshopt must be LAST (every gltf-transform pass decodes it).
setlocal
cd /d "%~dp0.."

set CLI=npx --yes @gltf-transform/cli

for %%G in (sandbox_meta_male sandbox_meta_female) do (
  echo === %%G ===
  %CLI% resize "meta_avatar\blender\exports\%%G.glb" "%TEMP%\_opt1.glb" --width 1024 --height 1024
  %CLI% webp "%TEMP%\_opt1.glb" "%TEMP%\_opt2.glb"
  %CLI% meshopt "%TEMP%\_opt2.glb" "meta_avatar\blender\exports\%%G.mobile.glb" --level medium
)

echo === avatar_animated_meta_male ===
%CLI% resample "animations\exports\avatar_animated_meta_male.glb" "%TEMP%\_opt1.glb"
%CLI% resize "%TEMP%\_opt1.glb" "%TEMP%\_opt2.glb" --width 64 --height 64
%CLI% webp "%TEMP%\_opt2.glb" "%TEMP%\_opt3.glb"
%CLI% meshopt "%TEMP%\_opt3.glb" "animations\exports\avatar_animated_meta_male.mobile.glb" --level medium

del "%TEMP%\_opt1.glb" "%TEMP%\_opt2.glb" "%TEMP%\_opt3.glb" 2>nul
echo Done.
