# Architecture v2 — Multi-Style Avatar Platform (PROPOSAL)

**Status: awaiting approval — nothing has been moved or modified yet.**

Goal: one universal parameter system, N avatar styles. The AI never sees a
mesh; styles never see a photo. The contract between them is a JSON document.

---

## 1. Folder structure

```
AI-Avatar-Engine/
│
├── schema/                          ★ NEW — the platform contract layer
│   ├── avatar_params.schema.json    # universal parameter schema (versioned)
│   ├── catalogs/
│   │   ├── hairstyles.json          # global catalog ids: "short_fade", "bob", ...
│   │   ├── beards.json              # "none", "stubble", "short", "full", ...
│   │   ├── glasses.json
│   │   ├── skin_tones.json          # "light" ... "deep" (id + reference values)
│   │   └── hair_colors.json
│   └── mappers/
│       ├── realistic.map.json       # universal params → realistic morphs/assets
│       └── meta.map.json            # universal params → meta morphs/assets (future)
│
├── assets/
│   ├── styles/
│   │   ├── realistic/
│   │   │   ├── style.json           # style manifest: variants, capabilities, mapper ref
│   │   │   ├── male/                # source FBX, textures (current reallusion_base/M)
│   │   │   └── female/
│   │   └── meta/                    # future — same layout, empty until then
│   │       ├── style.json
│   │       ├── male/
│   │       └── female/
│   └── shared/                      # style-agnostic wardrobe & motion
│       ├── hairstyles/<item_id>/    #   item.json + default.glb [+ per-style overrides]
│       ├── beards/<item_id>/
│       ├── clothes/<item_id>/
│       ├── glasses/<item_id>/
│       ├── accessories/<item_id>/
│       └── animations/              # ARKit/viseme test clips, idle/gesture clips
│
├── blender/
│   ├── scripts/                     # style-agnostic tooling (already mostly is)
│   ├── templates/
│   │   ├── realistic_male.blend     # renamed from male_base.blend
│   │   ├── realistic_female.blend
│   │   └── meta_male.blend ...      # future
│   └── exports/
│
├── ai/            # untouched (future: photos → universal params)
├── backend/       # untouched (future: generation service API)
├── frontend/threejs-viewer/         # sandbox (§5)
└── docs/
```

**Asset resolution rule** for wardrobe: each item folder has `item.json`:

```json
{
  "id": "short_fade",
  "category": "hairstyles",
  "attach_to": "CC_Base_Head",
  "variants": {
    "default": "default.glb",
    "meta": "meta.glb"          // optional stylized override
  }
}
```

Style asks for `short_fade` → use its own variant if present, else `default`.
This lets one catalog id serve every style, and lets styles override only
what looks wrong. A style manifest may also declare unsupported ids
(fallback id per category).

**Migration of current files** (after approval):

| Today | Becomes |
|---|---|
| `assets/reallusion_base/CC Character Base/.../03_Neutral_M` | `assets/styles/realistic/male/source/` |
| `assets/reallusion_base/.../02_Neutral_F` | `assets/styles/realistic/female/source/` |
| `blender/templates/male_base.blend` | `blender/templates/realistic_male.blend` |
| `blender/scripts/morph_definitions.json` | **split** → `schema/avatar_params.schema.json` + `schema/mappers/realistic.map.json` |
| `assets/hairstyles,beards,clothes,glasses,animations/` (empty) | `assets/shared/...` |
| sandbox `public/morph_definitions.json` | serves `schema/` files instead |

---

## 2. Avatar Parameter Schema

### 2.1 The three parameter classes

**A. Universal continuous (AI-predicted, 0–1, 0.5 = neutral)** — geometry
identity. Style-independent by definition: "wide jaw" is a property of the
*person*, not of the rendering style.

`face_width, jaw_width, jaw_height, jaw_angle, chin_size, nose_width,
nose_length, nose_bridge_height, nose_tip_size, eye_size, eye_distance,
eye_tilt, eyebrow_height, mouth_width, lip_thickness, philtrum_length,
cheek_size, cheekbone_height, forehead_height, ear_size` (the 20 we built)
+ roadmap: `body_weight, body_muscle, height` (need body morphs first).

**B. Universal categorical (AI-predicted, enum ids from `schema/catalogs/`)** —
`gender` (template selector), `age` (integer, morph-composite later),
`skin_tone`, `hair_style`, `hair_color`, `eye_color`, `beard`, `glasses`,
`body_type`.

**C. Style-space (NOT in the AI output)** — `style` (chosen by the user),
plus anything only meaningful inside one style (toon outline width, meta
head-to-body ratio, anime eye highlight shape). These live in the style
manifest / mapper as configuration, never in the avatar params JSON.
**Rule: if a parameter would mean nothing in at least one style, it does not
belong in the universal schema.**

### 2.2 Canonical example (`schema_version` mandatory)

```json
{
  "schema_version": "2.0",
  "gender": "male",
  "age": 30,
  "identity": {
    "face_width": 0.55, "jaw_width": 0.42, "nose_width": 0.60,
    "nose_length": 0.45, "eye_size": 0.55, "eye_distance": 0.48,
    "lip_thickness": 0.40, "...": "all 20, default 0.5"
  },
  "appearance": {
    "skin_tone": "medium", "hair_style": "short_fade", "hair_color": "black",
    "eye_color": "brown", "beard": "short", "glasses": "round",
    "body_type": "average"
  }
}
```

Naming decision: **snake_case is canonical** (matches the entire existing
Python/Blender/JSON pipeline). The AI/back-end boundary can trivially accept
camelCase and normalize; changing the whole pipeline to camelCase buys
nothing.

### 2.3 How a style maps parameters — the mapper file

Each style ships one `*.map.json`. It is **pure data** (no code) so Python
(Blender) and JS (sandbox/runtime) read the identical file — this is the same
single-source-of-truth pattern that already works for `morph_definitions.json`.

```json
{
  "style": "realistic",
  "schema_version": "2.0",
  "identity_mapping": {
    "face_width": {
      "targets": [
        { "shape_key": "face_width", "weight": 1.0 },
        { "shape_key": "jaw_width",  "weight": 0.25 }
      ]
    },
    "nose_width": { "targets": [ { "shape_key": "nose_width", "weight": 1.0 } ] }
  },
  "exaggeration": 1.0,
  "appearance_mapping": {
    "skin_tone": { "medium": { "texture_set": "skin_medium", "tint": [0.87, 0.72, 0.6] } },
    "hair_color": { "black": { "color": [0.05, 0.04, 0.04] } }
  }
}
```

The meta mapper uses the **same left-hand keys** with different right-hand
sides — e.g. `"exaggeration": 1.6` (cartoons amplify identity), targets that
point at the meta template's own morph names, and `skin_tone` resolving to a
flat albedo color instead of a texture set. A style with no morph for some
param maps it to an empty target list (param silently ignored — degradation,
not failure).

Engine math (unchanged from today): `value = (param − 0.5) × 2 × weight ×
exaggeration`, summed per target, clamped to the key's range.

---

## 3. Avatar Engine workflow

```
photos (3)
   ↓
AI Analysis                        [future — ai/]
   ↓
avatar_params.json                 ← universal, style-free, validated
   ↓                                 against avatar_params.schema.json
user picks style + gender
   ↓
STYLE MAPPER          (pure function, no I/O)
   params × <style>.map.json × catalogs
   ↓
avatar_recipe.json    ★ resolved intermediate:
   {                    - template: realistic_male.blend
     morphs: {face_width: 0.10, jaw_width: 0.025, ...},
     assets: [{id, file, attach_to}, ...],
     materials: {skin: {...}, hair: {...}}
   }
   ↓
AVATAR GENERATOR      (Blender headless, backend job)
   load template → apply recipe.morphs → bake identity
   → attach recipe.assets → apply recipe.materials → export
   ↓
avatar.glb            (skeleton + 148 animation morphs + wardrobe)
   ↓
runtime (Three.js)    — animation, rendering, no identity logic
```

**Why the explicit recipe stage matters:** it is cacheable (same recipe ⇒
same GLB), diffable in QA, testable without any AI, and it is the *only*
thing the generator ever reads — the generator does not know what a
"nose_width" is. Mapper bugs and generator bugs become separable.

---

## 4. Blender's role

| Phase | Frequency | Blender? | What happens |
|---|---|---|---|
| **Authoring** (offline) | rare | ✅ interactive + scripts | Build style templates: import base, generate morph keys, eye-follow, validate. Our existing scripts, run once per new style/variant |
| **Generation** (per avatar) | every avatar | ✅ headless service | `export_avatar_glb.py`-style job: recipe in → GLB out. Seconds per avatar, horizontally scalable workers |
| **Runtime** (per frame) | always | ❌ never | Three.js drives animation morphs/bones on the shipped GLB |

**Blender does:** mesh/morph authoring, identity baking, wardrobe fitting &
attachment at build time, material assembly, GLB export, QA renders.

**Blender does NOT:** talk to the AI, decide parameter semantics (it executes
recipes), serve real-time previews, run in the user's browser, or store any
state (workers are stateless: template + recipe in, GLB out).

**When runtime code is used instead:** everything after the GLB exists —
loading, ARKit/viseme morph driving, bone animation/retargeting, lipsync,
emotion playback, and *preview-quality* identity morphing in the sandbox
(dev GLBs keep identity morphs live precisely for this; production GLBs
stay baked).

---

## 5. Avatar Sandbox v2

The sandbox becomes the platform's reference client — it exercises the same
schema, catalogs, and mappers the production pipeline uses.

```
┌────────────────────────────────────────┬───────────────────────┐
│                                        │  Style: [Realistic ▾] │
│                                        │  Gender: [Male ▾]     │
│              3D viewport               │───────────────────────│
│                                        │  Tabs:                │
│   (loads assets/styles/<style>/        │   Identity   (schema- │
│    dev GLB for chosen gender)          │     driven sliders +  │
│                                        │     live JSON editor) │
│                                        │   Appearance (skin/   │
│                                        │     hair/wardrobe     │
│                                        │     from catalogs)    │
│                                        │   Blendshapes (raw)   │
│                                        │   Animation  ★NEW     │
│                                        │   Inspector / Display │
│                                        │   Export              │
└────────────────────────────────────────┴───────────────────────┘
```

Changes vs. today's sandbox:

1. **Style selector** (top bar, next to existing gender select). Loading a
   style = fetch its `style.json` → dev GLB per gender + its mapper file.
   The Identity tab is built from the *universal schema*, so it never changes
   between styles; only the mapper behind it changes.
2. **Appearance tab** — categorical params from `schema/catalogs/`
   (skin tone swatches, hair style/color pickers, beard/glasses). Uses the
   asset-resolution rule from §1 (style variant → default fallback).
   Replaces/absorbs today's Assets tab.
3. **Animation tab (new)** — plays clips from `assets/shared/animations/`
   (blink cycles, viseme sentences, ARKit emotion sequences) against the live
   avatar, validating that identity + style + animation compose correctly.
4. **Recipe debug view** — shows the resolved `avatar_recipe.json` for the
   current params (the exact payload the Blender generator would receive).
   Today's "resolved blendshape values" box, upgraded.
5. **Export** — GLB (current state) and `avatar_params.json` (v2 schema).
6. Kept as-is: raw Blendshapes tab, Inspector, Display toggles,
   `window.sandbox` console access.

Mapper/schema/catalog files are served directly from `schema/` (symlink or
copy step) so sandbox and pipeline can never drift.

---

## 6. Sequencing after approval (no work started)

1. Restructure folders + migrate files (table in §1), fix script paths.
2. Split `morph_definitions.json` → schema + realistic mapper; port
   `morph_controller.py` and sandbox to read them.
3. Sandbox v2 (style selector, appearance tab, animation tab, recipe view).
4. Wardrobe + material (skin tone) support in mapper → generator → sandbox.
5. Meta style: acquire/author cartoon bases, run the existing template
   authoring scripts on them, write `meta.map.json` — **zero engine changes
   if the architecture holds.** That is the test of this design.
```
