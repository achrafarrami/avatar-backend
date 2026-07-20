# AI Photo Pipeline — Architecture

**Status: approved 2026-07-16; upgraded to the multi-model fusion
architecture (v2, below) on 2026-07-20. Phases A (geometry), B (appearance
via OpenAI vision, key in `ai/photo_analyzer/.env`), C (sandbox "Generate
From Photos": `server.py` on port 8100 + Photos tab) and the v2 fusion
pipeline implemented — see `ai/photo_analyzer/README.md`.**

---

## v2: Multi-model feature fusion (implemented 2026-07-20)

Accuracy problems v1 shipped with — beards inflating jaw/cheek widths,
foreheads not tracking photos (MediaPipe's mesh-top point is not the
hairline), everything regularized toward neutral, profiles unused — are
addressed by specialized models fused through one confidence-weighted
solve:

```
3 photos (front + left + right profile)
        ↓
preprocessing/               quality score (blur/exposure/face size),
                             roll alignment, crop, resize; gray-world WB +
                             CLAHE copies for the color-sensitive models
        ↓
processors/  (each does ONLY what it's best at)
  face_landmarks.py          MediaPipe: frontal proportions + per-
                             measurement confidence + landmark overlay
  face_parsing.py            BiSeNet 19-class segmentation (onnxruntime):
                             occlusion factors, beard coverage, hairline
  profile_analyzer.py        profile silhouette contour (ear-anchored):
                             nose/chin projection, face depth, jaw slope —
                             works at 90° where MediaPipe fails
  identity_embedding.py      ArcFace ONNX: same-person check across the 3
                             photos + stored embedding (offline eval);
                             NEVER converted to morphs
  appearance_analyzer.py     VLM labels only (hair/beard/glasses/skin)
        ↓
fusion/                      every signal = {value, confidence, source};
                             confidences compose multiplicatively:
                             photo quality x pose x parsing occlusion x
                             semantic beard down-weight
        ↓
fusion/solver.py             confidence-weighted joint ridge solve against
                             the calibrated response matrix; missing
                             measurements drop out; low-trust evidence
                             moves sliders less; per-param confidence +
                             dominant source reported in `faceMeta`
        ↓
avatar_parameters.json       `face` map unchanged (engine contract);
                             `faceMeta` adds {value, confidence, source}
```

Key design decisions:

- **Two-channel beard defense.** Segmentation labels beards inconsistently
  (CelebAMask-HQ heritage — our CG test beard reads as skin), so the
  lower-face down-weighting triggers from EITHER parser beard coverage OR
  the VLM's beard label. The down-weight tables in `fusion/features.py`
  were measured empirically: a beard corrupts mouth_width (+13%!),
  philtrum, jaw widths, nose_width — not just the chin.
- **Hairline forehead.** `forehead_hairline` = (hairline→brow)/(brow→chin)
  from the parser's hair boundary. Its anchor CANNOT come from the
  standard neutral renders (templates are bald): `render_hairline_calib.py`
  renders the template WEARING a wardrobe hair asset and
  `calibrate.py --hairline-renders` measures it through the same code path
  as photos. Male renders use the female hair scaled 1.09x (head-width
  probe) until male hair assets exist.
- **Profiles via silhouette, ear-anchored.** MediaPipe sees nothing past
  ~60° yaw. The profile analyzer uses the segmentation silhouette's
  contour-curve extrema, framed and normalized by the EAR (top ~ brow,
  bottom ~ nose base, height = scale unit) — the one region BiSeNet nails
  at 90°. Left+right measurements are averaged (side lighting shifts the
  silhouette; averaging cancels it). Response slopes come from a left-view
  sweep (`render_param_sweep.py <template> <dir> Male left` +
  `calibrate.py --fit-profile`), filtered by a physical-plausibility
  whitelist. ear_size is genuinely observable through the ear-normalized
  scale. Honest per-measurement noise floors live in `fusion/solver.py`
  (NOISE_FLOOR_OVERRIDES — measured from left/right spread).
- **Regularization is tunable, confidence-aware.** ridge_lambda stays the
  global knob; per-param `prior_strength` in calibration.json scales each
  parameter's pull toward neutral; and because lambda is computed from
  noise-floor weights only, dropping confidences (beard/blur/occlusion)
  automatically pulls only the affected params toward neutral.
- **Debug everywhere.** `pipeline.py --debug` writes aligned/landmark/
  segmentation/profile-contour images; `/analyze?debug=true` returns them
  base64 to the sandbox's Photo Debug panel (Photos tab → Debug checkbox):
  stage images, measurement table with confidences and down-weight
  factors, final parameters with provenance.

Verified end-to-end on synthetic ground truth (template renders where the
true answer is known): neutral → all 20 params 0.500 exactly; bearded
neutral (template wearing beard_short) → cheeks/jaw back to ≈0.51-0.53
(was the core complaint); haired neutral → forehead 0.49; param sweeps
recover face_width 0.28/0.72 for truth 0.20/0.80, chin_size 0.35/0.62.
Known limits: jaw_angle's visible response is below measurement noise from
every angle (stays near neutral, low confidence reported); single-notch
profile measurements (lip/chin projection) are noisy and carry 0.35-0.40
confidence by design.

The bridge between user photos and the existing Avatar Engine:

```
3 photos (front, left, right)
        ↓
AI Face Analysis            (new: ai/photo_analyzer/)
        ↓
avatar_parameters.json      (the ONLY thing the AI layer produces)
        ↓
Existing Avatar Engine      (untouched: morph layer, templates, wardrobe)
        ↓
Customized avatar in the Sandbox / exported GLB
```

Hard rules honored throughout: the AI layer **never generates meshes**, never
touches the Reallusion avatar, never calls external avatar generators. It
emits parameters; the engine we already built does 100% of the 3D work.

---

## 1. Module layout

```
AI-Avatar-Engine/
  ai/
    photo_analyzer/
      input/                     # user photos dropped here (or via API)
        front.jpg  left.jpg  right.jpg
      processors/
        face_landmarks.py        # MediaPipe → measurements (geometry)
        face_identity.py         # InsightFace → embedding (identity QC)
        appearance_analyzer.py   # VLM → hair/beard/glasses/skin labels
      calibration/
        calibration.json         # measurement → engine-param mappings (EDITABLE)
        appearance_map.json      # semantic labels → wardrobe catalog ids (EDITABLE)
      schema/
        avatar_parameters.schema.json
      pipeline.py                # CLI orchestrator: photos in → JSON out
      server.py                  # (Phase C) FastAPI for the Sandbox button
      output/
        raw_analysis.json        # intermediate: measurements + confidences
        avatar_parameters.json   # final deliverable
```

Design principle: **processors measure, calibration maps, the engine renders.**
No processor ever writes an engine parameter directly — everything passes
through the calibration layer, because raw AI values will not match Blender
morph values (this is where `noseWidth 0.8 → morph 0.55` gets fixed, in data,
not code).

---

## 2. The two parameter spaces (and why we need both)

| Space | Who owns it | Names | Example |
|---|---|---|---|
| **AI output space** | `avatar_parameters.json` (spec'd format) | camelCase | `faceWidth: 0.55` |
| **Engine morph space** | `blender/scripts/morph_definitions.json` | snake_case | `face_width: 0.55` |

The output JSON follows the agreed format exactly (camelCase, semantic
appearance labels). A fixed 1:1 name map (part of the calibration layer)
converts it into the engine's 20 params:

`faceWidth→face_width, faceLength→jaw_height, jawWidth→jaw_width,
chinSize→chin_size, noseWidth→nose_width, noseLength→nose_length,
eyeSize→eye_size, eyeDistance→eye_distance, lipThickness→lip_thickness, …`

plus the engine params the example format doesn't list yet but our engine
supports and MediaPipe can measure — these will be added to the `face` block:
`foreheadHeight, cheekboneHeight, cheekSize, jawAngle, noseBridgeHeight,
noseTipSize, eyeTilt, eyebrowHeight, mouthWidth, philtrumLength, earSize`.
(20 total, matching the engine's identity morphs 1:1.)

Appearance labels map to **wardrobe catalog ids** via `appearance_map.json`:

```
hair.style  "short_curly" → equip("hair", "hair_curly")
hair.color  "black"       → palette hex "#111114"
beard.style "short"       → equip("beard", "beard_short")
glasses     "round"       → equip("glasses", "glasses_round")
```

The VLM is *prompted with the catalog vocabulary* so it can only answer in
labels we can actually equip — no free-text drift.

---

## 3. Processors

### 3.1 face_landmarks.py — MediaPipe Face Landmarker (geometry driver)

- 478 3D landmarks + head-pose transform per photo.
- **Front photo is the primary driver.** All distances are normalized by
  inter-pupillary distance (IPD) to be scale/zoom invariant, e.g.:
  - `face_width` ← bizygomatic width / IPD
  - `eye_distance` ← inner-canthal distance / IPD
  - `mouth_width` ← lip-corner distance / IPD
  - `jaw_width` ← gonion-to-gonion / IPD … (full table lives in calibration.json)
- **Profile photos** are used for (a) quality control — reject if head yaw is
  not ≈ ±90°/0°, (b) depth measures the front view can't see well:
  nose bridge projection, nose length, chin projection, jaw angle.
- Head-pose QC gate: if the "front" photo has |yaw| > 15° we warn — bad input
  is the #1 cause of garbage parameters.

### 3.2 face_identity.py — InsightFace (identity QC, not a driver)

- 512-d face embedding (buffalo_l, ONNX — no PyTorch needed).
- Prototype uses it for two checks, not for setting parameters:
  1. **Same-person check**: all 3 photos must match each other (cos > 0.4).
  2. **Identity score** (the long-game feature): render the generated avatar,
     embed the render, report cosine similarity photo↔avatar. This gives us
     an *objective number* to tune calibration against, instead of eyeballing.

### 3.3 appearance_analyzer.py — Vision Language Model (semantic labels)

- Input: front photo (+ profiles for hair-back/length). Output: strict JSON
  with enums limited to our catalog vocabulary + palette names.
- Detects: hair style/color, beard style/color, glasses shape, skin tone,
  visible clothing type, approximate body build.
- Engine choice: **Claude API vision** as the prototype default (best
  accuracy, ~1 call/avatar, structured output), with the module written
  against a thin interface so a local VLM (LLaVA via Ollama) can be swapped
  in later. If no API key is configured, the pipeline still runs — appearance
  block is emitted as `null`s and only geometry params are produced.

### 3.4 DECA / EMOCA — evaluated, deferred

Recommendation: **do not include in the prototype.**
- Their output is FLAME model coefficients (100 shape dims of a *different*
  head basis). Converting FLAME→our 20 CC morphs is a research project by
  itself, with no guarantee it beats simple calibrated landmark ratios.
- Heavy PyTorch/pytorch3d stack, painful on Windows, GPL-ish license
  concerns on some checkpoints (commercial platform!).
- The landmark path already covers every one of our 20 params.

Revisit only if Phase D's identity score shows the ratio approach plateauing.

---

## 4. Calibration system (the core deliverable)

`calibration/calibration.json` — one entry per engine parameter:

```json
"nose_width": {
  "measurement": "nose_alar_width_over_ipd",
  "neutral": 0.578,          // measurement value that must map to param 0.5
  "gain": 2.4,               // param units per measurement unit
  "clamp": [0.15, 0.85],     // never push a morph to its extremes from AI
  "invert": false,
  "note": "alar width / IPD; neutral measured on the base avatar render"
}
```

Formula: `param = clamp(0.5 + (measurement − neutral) × gain × (invert ? −1 : 1))`

Two properties make this commercial-grade rather than guesswork:

1. **Neutral anchored to OUR avatar, not to population averages.** We render
   the base template head (params all 0.5), run MediaPipe *on that render*,
   and record its measurements as the `neutral` values. Then "user's nose is
   wider than the avatar's" directly means `nose_width > 0.5`. Systematic
   MediaPipe biases cancel out because both sides of the comparison go
   through the same detector.

2. **Auto-calibration harness (Phase D).** For each param: render the head at
   0.1 / 0.5 / 0.9, re-measure the renders, fit `gain` from the measured
   deltas. Calibration becomes a build artifact (`calibrate.py` regenerates
   the JSON), and it automatically stays correct if morphs are re-sculpted or
   a new style (female base, future cartoon style) is added.

Until Phase D, `calibration.json` ships with hand-tuned gains — and because
it's data, anyone can adjust a mapping without touching code.

---

## 5. Output contract

`avatar_parameters.json` — exactly the agreed format (abridged):

```json
{
  "version": 1,
  "gender": "male",
  "face":       { "faceWidth": 0.55, "...": "all 20 params, 0..1, 0.5 neutral" },
  "appearance": {
    "skinTone": "medium",
    "hair":    { "style": "short_curly", "color": "black" },
    "beard":   { "style": "short", "color": "black" },
    "glasses": "round"
  },
  "body": { "bodyType": "average" },
  "meta": {
    "confidence": { "geometry": 0.86, "appearance": 0.9 },
    "identity_check": "passed",
    "source_photos": ["front.jpg", "left.jpg", "right.jpg"]
  }
}
```

- Validated against `schema/avatar_parameters.schema.json` (JSON Schema).
- `raw_analysis.json` is also written (all raw measurements, per-photo pose,
  embedding similarities) — this is the debugging/calibration artifact.
- Honest scoping notes: `gender` selects the male/female template (both
  exist; wardrobe items are male-fitted today). `bodyType` is emitted for
  forward-compatibility — the engine has **no body morphs yet**, so it is
  recorded but not applied.

---

## 6. Sandbox integration — "Generate From Photos"

The sandbox is a static Vite app, so photo processing needs a tiny local
backend (Python owns the AI deps):

```
Sandbox (new "Photos" panel)                server.py (FastAPI, localhost:8100)
  3 file inputs + [Generate] ──POST /analyze (multipart)──▶ pipeline.run()
  ◀───────────── avatar_parameters.json ────────────────────┘
  then, all EXISTING code paths:
    face params  → same path as the Identity sliders (main.js computeKeyValues)
    hair/beard/glasses → WardrobeManager.equip(slot, id) + palette color
    sliders + wardrobe UI update to show what was chosen (fully editable after)
```

- One new sandbox file/panel; zero changes to viewer.js morph logic — the AI
  result is literally "someone moved the sliders and picked wardrobe items".
- Server offline → panel shows "start the analyzer: `python ai/photo_analyzer/server.py`".
- Privacy: everything runs locally; photos never leave the machine except the
  single VLM call (Claude API) — and that call is skippable.

---

## 7. Build phases (each one stops for approval)

| Phase | Scope | Proof it works |
|---|---|---|
| **A — Geometry prototype** | env setup; `face_landmarks.py`; `calibration.json` (hand-tuned, neutral anchored to base-avatar render); `pipeline.py` CLI; schema + output JSONs | Run on test photos → JSON; apply params in sandbox manually; side-by-side screenshot |
| **B — Appearance** | `appearance_analyzer.py` (VLM) + `appearance_map.json`; wire into pipeline | Photos of people with distinct hair/beard/glasses → correct catalog picks |
| **C — Sandbox button** | `server.py` + "Photos" panel in the sandbox | Upload 3 photos in the browser → avatar appears |
| **D — Feedback loop** | `face_identity.py` scoring render↔photo; `calibrate.py` auto-calibration harness | Identity score reported per generation; calibration regenerated from renders |

Python env: separate venv under `ai/` (`mediapipe`, `insightface`,
`onnxruntime`, `numpy`, `pillow`, `fastapi`, `uvicorn`, `anthropic`). Python
3.11 recommended (best MediaPipe wheel support on Windows).

---

## 8. Risks / open questions

- **MediaPipe measures 2D-projected geometry** — ratios are pose-sensitive;
  we mitigate with the pose QC gate and IPD normalization, but expect Phase A
  output to need calibration iteration. That's what the identity score in
  Phase D is for.
- **VLM cost/latency**: one image call per avatar (~seconds). Acceptable for
  a dev tool; a local VLM swap keeps the door open for production.
- **Only 5 hair styles / 2 beards / 2 glasses exist** in the catalog — the
  VLM will pick the *closest*, so mapping quality grows as the hairstyle
  library grows (the `build_hair_style.py` track feeds directly into this).
- **Ethics/consent**: pipeline processes faces of the person who uploaded
  them; no face database is built (embeddings live only in `raw_analysis.json`).
