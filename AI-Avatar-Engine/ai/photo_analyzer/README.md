# Photo Analyzer — photos → avatar parameters

Multi-model fusion pipeline: preprocessing → MediaPipe landmarks + BiSeNet
face parsing + profile silhouette analysis + **MICA 3D reconstruction** +
ArcFace identity check + VLM appearance labels → confidence-weighted joint
solve. Architecture:
[docs/ai_photo_pipeline_architecture.md](../../docs/ai_photo_pipeline_architecture.md)

## One-time setup: OpenAI key (for appearance analysis)

```
cd ai\photo_analyzer
copy .env.example .env
notepad .env        <- paste your OPENAI_API_KEY
```

Then (re)start the analyzer server. Appearance analysis (hair style/color,
beard, glasses, skin tone → auto-equipped wardrobe items) uses one small
vision call per avatar (`gpt-4o-mini` by default). **Without a key everything
still works** — you just get geometry only. Check what's active at
<http://127.0.0.1:8100/health>.

## Easiest test: in the Sandbox (recommended)

1. Start the analyzer server (leave it running):

   ```
   ai\.venv\Scripts\python ai\photo_analyzer\server.py
   ```

2. Start the sandbox (`npm run dev` in `frontend/threejs-viewer/`) and open
   the **Photos** tab: drop your front photo (left/right optional), click
   **Generate Avatar**. Identity parameters apply instantly; fine-tune them
   in the Identity tab afterwards.

Photo tips: front = straight at the camera, neutral expression, even light;
profiles = ~60–90° turns (the silhouette analyzer handles true side views;
MediaPipe landmarks are only used up to ~60°).

## CLI alternative

1. Put your 3 photos in `ai/photo_analyzer/input/` (any names).

2. From the `AI-Avatar-Engine/` folder run:

   ```
   ai\.venv\Scripts\python ai\photo_analyzer\pipeline.py ^
       ai\photo_analyzer\input\front.jpg ^
       ai\photo_analyzer\input\left.jpg ^
       ai\photo_analyzer\input\right.jpg
   ```

   (front photo alone also works: profiles are optional in Phase A)

3. Outputs land in `ai/photo_analyzer/output/`:
   - `avatar_parameters.json` — the engine-facing contract (camelCase)
   - `identity_paste.json` — **open the Avatar Sandbox → Identity tab →
     paste this into the JSON box** to see your face parameters applied
   - `raw_analysis.json` — raw measurements + QC (for debugging/calibration)

## If a parameter looks wrong

`calibration/calibration.json` is fully measured, not hand-tuned: per-gender
neutral anchors + a response matrix solved jointly (ridge least squares).
Per-param `clamp` ranges are still hand-editable safety rails, and
`response_matrix.ridge_lambda` trades accuracy (lower) vs stability (higher);
default 0.1.

## Debugging a bad result

Photos tab → tick **Debug** → Generate. The Photo Debug panel shows the
aligned photos, landmark overlay, segmentation (hairline cyan / beard red),
profile silhouette contours, every measurement with its confidence and
down-weighting factors, and each final parameter's confidence + dominant
source. CLI equivalent: `pipeline.py ... --debug` writes the same images to
`output/debug/`.

## Recalibrating (only after morphs/template change)

```
blender --background --python blender/scripts/render_head_views.py -- blender/templates/male_base.blend ai/photo_analyzer/calibration/renders
blender --background --python blender/scripts/render_head_views.py -- blender/templates/female_base.blend ai/photo_analyzer/calibration/renders_female Female
blender --background --python blender/scripts/render_param_sweep.py -- blender/templates/male_base.blend <sweep_dir>
blender --background --python blender/scripts/render_param_sweep.py -- blender/templates/male_base.blend <sweep_left_dir> Male left
blender --background --python blender/scripts/render_hairline_calib.py -- blender/templates/male_base.blend <hair_dir> Male hair_w06 1.09
blender --background --python blender/scripts/render_hairline_calib.py -- blender/templates/female_base.blend <hair_dir_f> Female
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --renders ai/photo_analyzer/calibration/renders --gender male
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --renders ai/photo_analyzer/calibration/renders_female --gender female
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --fit-gains <sweep_dir>
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --fit-profile <sweep_left_dir>
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --fit-3d <sweep_dir>
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --hairline-renders <hair_dir> --gender male
ai\.venv\Scripts\python ai\photo_analyzer\calibrate.py --hairline-renders <hair_dir_f> --gender female
```

(`--renders` also anchors the profile AND MICA 3D measurements from the
neutral renders automatically. `--fit-3d` uses the SAME front sweep dir as
`--fit-gains`.)

## Environment

- venv: `ai/.venv` (Python 3.11; `mediapipe`, `numpy`, `pillow`,
  `opencv-contrib-python`, `onnxruntime`, `torch` CPU)
- models in `models/` (all gitignored; re-download if missing):
  - `face_landmarker.task` — MediaPipe, official release:
    <https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task>
  - `face_parsing_resnet18.onnx` — BiSeNet 19-class face parsing
    (yakhyo/face-parsing, MIT):
    <https://github.com/yakhyo/face-parsing/releases/download/weights/resnet18.onnx>
  - `arcface_w600k_r50.onnx` — ArcFace recognition (insightface buffalo_l,
    immich mirror):
    <https://huggingface.co/immich-app/buffalo_l/resolve/main/recognition/model.onnx>
  - `mica.tar` — MICA 3D face reconstruction weights (Zielon/MICA, MPG
    RESEARCH license; carries the FLAME buffers so no FLAME pkl is needed at
    runtime): Google Drive id `1bYsI_spptzyuFmfLYqYkcJA6GZWZViNt`.
    `data/flame_regions.npz` (committed) holds the region indices it needs.
  Every optional model (parsing / identity / MICA) degrades gracefully when
  missing — a warning, and the rest of the pipeline continues.

## Validating on real photos (validate_real.py)

The closed-loop validation harness: for every photo set it runs the full
pipeline, renders the resulting avatar in Blender
(`blender/scripts/render_avatar_params.py`, same camera as the calibration
renders), and scores photo ↔ avatar with ArcFace identity cosine and MICA
mean-vertex distance (mm), plus a `side_by_side.png` sheet for human review.

```
ai\photo_analyzer\input\<set_name>\front.jpg   <- required
ai\photo_analyzer\input\<set_name>\left.jpg    <- optional (~60-90 deg turn)
ai\photo_analyzer\input\<set_name>\right.jpg   <- optional

ai\.venv\Scripts\python ai\photo_analyzer\validate_real.py [--sets a,b] [--skip-render]
```

Results per set under `output/validation/<set_name>/` (side_by_side.png,
report.md with params + confidence + source, debug images) and a cross-set
`output/validation/summary.md`. Metric guide: identity similarity > 0.5 is a
strong same-person signal on renders; shape3d ~1 mm excellent, > 5 mm poor.

## Validation so far

- Neutral self-test: pipeline on the base avatar's own renders → all 20
  params = 0.50 exactly.
- Morph-response test: injected `nose_width 0.85 / jaw_width 0.25 /
  lip_thickness 0.80` via MorphController, rendered, recovered
  `0.84 / 0.25 / 0.80`. (`mouth_width` recovery is weak — the detector can't
  see our subtle mouth morph; conservative gain, Phase D item.)
- Round-trip via validate_real.py: neutral render → identity 1.0 /
  shape3d 0.0 mm / 20 params at 0.5 exactly; bearded template render →
  identity 0.833 / shape3d 0.71 mm with no beard-inflated cheeks or jaw.
- Real photos: pending — this is the current phase; drop sets into `input/`
  and run the harness.
