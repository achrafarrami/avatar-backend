# AI-Avatar-Engine

A from-scratch avatar generation pipeline (Meta Avatars / Ready Player Me
style), built in-house:

```
photos  →  AI analysis  →  avatar_parameters.json  →  rigged, animatable avatar
```

Everything is data-driven and measured — no hand-tuned magic numbers: the
AI layer only ever produces **parameters**, the Blender "Avatar Factory"
turns parameters into meshes, and a browser sandbox validates both.

> **This is the backend repo** (the "brain"). The web client lives in its own
> repo, `../avatar-frontend`, and talks to this backend over HTTP — see
> [Two-repo layout](#two-repo-layout) below.

## Quick start (dev machine)

Start the backend (AI analyzer + shared-data/asset API on :8100):

```
AI-Avatar-Engine\run.cmd
```

Then start the web client in the sibling repo (`cd ../avatar-frontend &&
npm run dev` → :5173), open the **Photos** tab, drop a front photo (left/right
profiles optional), and click **Generate Avatar**. Tick **Debug** to see every
intermediate stage (landmarks, segmentation, 3D reconstruction, and each
parameter's confidence + source).

## How it works

### 1. AI photo analyzer (`AI-Avatar-Engine/ai/photo_analyzer/`)

A multi-model fusion pipeline — each model does only what it is best at,
and every signal carries `{value, confidence, source}`:

| Stage | Model | Job |
|---|---|---|
| Preprocessing | OpenCV | quality score, roll alignment, consistent crop, color normalization |
| Frontal proportions | MediaPipe Face Landmarker (478 pts) | scale-invariant face ratios + per-measurement confidence |
| Face parsing | BiSeNet (19-class, ONNX) | beard coverage, real hairline, per-landmark occlusion |
| Profile depth | Silhouette contour analysis | nose/chin projection, face depth from true side views |
| 3D reconstruction | **MICA** (CPU torch, FLAME topology) | metric neutral 3D head → depth, jaw angle, beard-robust widths |
| Identity | ArcFace (ONNX) | same-person check across photos (never converted to morphs) |
| Appearance | Vision LLM (optional) | hair/beard/glasses/skin-tone labels → wardrobe auto-equip |
| Fusion | Confidence-weighted joint ridge solver | all measurements → 20 identity parameters |

Key design rules:

- **Calibration is measured, never guessed** — neutral anchors and the
  response matrix come from running the *same measurement code* on renders
  of the neutral templates, so systematic model bias cancels out.
- **Beards can't inflate the face** — beard-covered 2D measurements are
  down-weighted (parser coverage OR VLM label), while MICA's 3D widths are
  beard-invariant (verified: same skull to 0.87 mm with/without a beard)
  and carry the width instead.
- **Measure, don't map** — MICA's FLAME mesh is a measurement instrument;
  its coefficients/topology never become engine morphs.
- **Graceful degradation** — any missing optional model (parsing, identity,
  MICA, VLM key) produces a warning, not a failure.

Full design: [docs/ai_photo_pipeline_architecture.md](AI-Avatar-Engine/docs/ai_photo_pipeline_architecture.md)
· usage: [ai/photo_analyzer/README.md](AI-Avatar-Engine/ai/photo_analyzer/README.md)

### 2. Avatar Factory (`AI-Avatar-Engine/blender/`)

Blender 5.2 headless scripts that author the avatar templates (Reallusion
CC3+ base): generate the 20 semantic identity morphs from data (expression-
key-derived vertex masks — nothing hand-sculpted), keep cross-mesh shape
keys in sync (eyes/teeth follow the face), repair lip-seal artifacts, bake
identity into production GLB exports, and build the entire demo wardrobe
library. The semantic parameter layer (`morph_definitions.json`, 0–1 scale,
0.5 = neutral) is the single contract shared by Blender, the AI, and the
web viewer.

### 3. Meta avatar style (`AI-Avatar-Engine/meta_avatar/`)

A second, **Meta-Avatars-inspired stylized renderer** off the *same*
universal parameters — the AI layer is style-agnostic (photos never see a
style, styles never see a photo). Built on the Reallusion CC3+ **Toon** base
(identical topology/skeleton/morph names to realistic, so every authoring
script is reused). A moderate-cartoon neutral is baked in (bigger eyes,
softer nose, rounder cheeks), identity is amplified via a mapper
`exaggeration` (1.3), and Meta-only `head_size` / `body_weight` morphs are
added — see `meta_avatar/documentation/` (phase reports + `qa_report.md`).

The **generation backend** (`backend/generate_avatar.py`) is the one-command
chain: photos → params → per-style mapping → morph bake → wardrobe assembly
→ dressed, rigged `avatar.glb`. It reuses the AI pipeline, exporter, and
verifier unmodified.

### 4. Avatar Sandbox (web client — separate repo `../avatar-frontend`)

Vanilla Three.js + Vite dev tool: template inspector, blendshape and
identity sliders, catalog-driven wardrobe (bone-attached + skinned assets,
per-style fit overrides), a **Realistic / Meta** style switch, the Photos
tab (full AI pipeline with debug panel + photo-vs-avatar compare strip), and
GLB export. It keeps **no local asset copies** — morph definitions, style
maps, the wardrobe catalog + GLBs, and the avatar bases are all fetched from
this backend's API (`VITE_API_BASE`, default `:8100`). The future mobile app
is a second client on the same endpoints.

### 5. Validation loop

`validate_real.py` closes the loop: photo set → pipeline → Blender render
of the predicted avatar → **ArcFace identity similarity + MICA 3D shape
distance (mm)** + a side-by-side sheet per person. Ground-truth round-trips:
neutral render → identity 1.0 / 0.0 mm / all params exactly neutral;
bearded render → identity 0.833 / 0.71 mm, no beard-inflated jaw.

## Two-repo layout

The project is two independent git repos living side by side inside a plain
`avatar_blender/` container folder (neither is nested in the other, so each
moves/deploys on its own):

```
avatar_blender/            (plain container — no git of its own)
├── avatar-backend/        (THIS repo — BACKEND / "brain")
└── avatar-frontend/       (sibling repo — web client, hits this backend's API)
```

The frontend (and the future mobile app) keep **no local asset copies**; the
backend is the single source of truth, served over HTTP:

| Endpoint | Serves |
|---|---|
| `GET /data/{morph_definitions,meta.map,style}.json` | morph defs + style maps |
| `GET /wardrobe/catalog.json`, `/wardrobe/<cat>/<id>/<file>` | wardrobe catalog + item GLBs/thumbnails (from `assets/shared/`) |
| `GET /avatars/sandbox_*.glb` | avatar base dev builds |
| `POST /analyze`, `/appearance` | the AI photo pipeline |

### Backend repo (`AI-Avatar-Engine/`)

```
AI-Avatar-Engine/
├── run.cmd / run.ps1          # start the backend API (:8100)
├── ai/photo_analyzer/         # photos → avatar_parameters.json (see its README)
│   ├── preprocessing/  processors/  fusion/  calibration/
│   ├── server.py              # FastAPI: AI pipeline + shared data/asset routes (:8100)
│   ├── pipeline.py            # CLI: pipeline.py front.jpg [left right] [--debug]
│   └── validate_real.py       # real-photo validation loop
├── blender/
│   ├── templates/             # male_base.blend / female_base.blend (CC3+, textures packed)
│   ├── exports/               # sandbox_{male,female}.glb — realistic bases served by the API
│   └── scripts/               # morph generation, followers, export, calibration renders
├── meta_avatar/               # Meta (cartoon) style: toon bases, mapper, meta scripts, docs
│   ├── blender/base/          # meta_male.blend / meta_female.blend
│   ├── blender/exports/       # sandbox_meta_{male,female}.glb — meta bases served by the API
│   ├── renderer/              # meta.map.json (params → meta morphs) + style.json (served)
│   └── documentation/         # phase1–3 reports, qa_report.md, phase3_status.md
├── backend/                   # generate_avatar.py — photos → assembled avatar.glb
├── assets/shared/             # canonical wardrobe library (catalog.json + items) — served at /wardrobe
└── docs/                      # architecture docs (pipeline, asset system, factory)
```

## Setup on a fresh machine

1. **Blender 5.2** (scripts assume `BLENDER_EEVEE` engine enum).
2. **Node** ≥ 18 for the web client — in the sibling repo:
   `cd ../avatar-frontend && npm install` (not part of this backend repo).
3. **Python 3.11** venv at `AI-Avatar-Engine/ai/.venv`
   (mediapipe requires ≤ 3.12):
   ```
   py -3.11 -m venv AI-Avatar-Engine/ai/.venv
   AI-Avatar-Engine/ai/.venv/Scripts/pip install mediapipe opencv-contrib-python \
       onnxruntime pillow pillow-heif fastapi uvicorn python-multipart \
       python-dotenv openai
   AI-Avatar-Engine/ai/.venv/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```
4. **Model files** into `ai/photo_analyzer/models/` — download URLs and
   license notes in [ai/photo_analyzer/README.md](AI-Avatar-Engine/ai/photo_analyzer/README.md#environment).
5. Optional: `OPENAI_API_KEY` (env var or `ai/photo_analyzer/.env`) for
   appearance labels — everything else runs fully local.

## Licensing notes (important)

- **Reallusion CC3+ base characters** are licensed content — do not
  redistribute the templates/GLBs outside the terms of your Reallusion
  license.
- **MICA weights + FLAME 2020** are under the MPG **research license**:
  fine for this prototype, NOT for commercial shipping. The commercial path
  is FLAME 2023 Open (CC-BY-4.0) + adapting MICA to it.
- BiSeNet face parsing weights: MIT (yakhyo/face-parsing). ArcFace weights:
  insightface buffalo_l. MediaPipe: Apache-2.0.
- Large source assets and all model weights are gitignored; only code,
  configs, and the calibration renders are committed.

## Status

- ✅ Avatar Factory: templates, 20 data-driven identity morphs, cross-mesh
  followers, lip-seal repair, identity-baking GLB export, wardrobe library
- ✅ AI pipeline v3: multi-model fusion + MICA 3D stage, verified on
  synthetic ground truth (neutral = 0.500 exact, sweeps recover)
- ✅ Closed-loop validation harness
- ✅ **Meta (cartoon) style** — Phase 1 bases, Phase 2 stylized morph library
  (baked neutral + exaggeration + head/body morphs), Phase 3 end-to-end
  generation, wardrobe fitted to the toon heads
- ✅ **One-step generation backend** (`backend/generate_avatar.py`): photos →
  dressed, rigged `avatar.glb` (realistic or meta) — 4 QA cases pass
- 🔄 **Current: validation on real photos** — drop sets into
  `ai/photo_analyzer/input/<name>/front.jpg`, then `validate_real.py`
  (realistic) or `backend/generate_avatar.py` (meta). This also first
  exercises the appearance-driven wardrobe auto-detect path.
- ⬜ Multi-style schema split
  ([docs/architecture_v2_proposal.md](AI-Avatar-Engine/docs/architecture_v2_proposal.md));
  male-native hair fits; commercial-license model swap before production ship
