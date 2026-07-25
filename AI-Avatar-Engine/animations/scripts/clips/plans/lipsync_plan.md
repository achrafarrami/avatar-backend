# Lip Sync / Speech Animation Plan — Procedural Speech Sequencer

Author: lipsync agent. Phase A planning doc. Target: Meta-Avatars-quality
generic ("gibberish") talking — no audio track, procedural rhythm, never a
metronome jaw-flap. 30 fps clips, 10–15 s seamless loops.

Rig: `AI-Avatar-Engine/meta_avatar/blender/base/meta_male.blend`
(verified headlessly 2026-07-23; matches `animations/qa/rig_reference.json`).

---

## 1. Verified rig inventory (exact names)

### 1.1 Visemes on the body (`MetaMale_Body` / data `CC_Base_Body`) — 8

```
V_Open  V_Explosive  V_Dental_Lip  V_Tight_O  V_Tight  V_Wide  V_Affricate  V_Lip_Open
```

There is NO `V_None` on the body (it exists only as a follower on
`Toon_Eyebrows`). "Neutral" = all visemes at 0. No `V_Tongue_*` on the body.

### 1.2 Tongue visemes on `CC_Base_Tongue` — 7

```
V_Tongue_up   (NB: lowercase "up" — exact string)
V_Tongue_Raise  V_Tongue_Out  V_Tongue_Narrow  V_Tongue_Lower
V_Tongue_Curl_U  V_Tongue_Curl_D
```

Plus full `Tongue_*` expression keys (`Tongue_Up`, `Tongue_Tip_Up`,
`Tongue_Out`, `Tongue_Narrow`, …) and `Jaw_*` follower keys.

### 1.3 Mouth-region ARKit-style keys on the body (all 0–1)

- Jaw: `Jaw_Open`, `Jaw_Forward`, `Jaw_Backward`, `Jaw_L`, `Jaw_R`, `Jaw_Up`, `Jaw_Down`
- Lips/mouth: `Mouth_Close`, `Mouth_Smile_L/R`, `Mouth_Smile_Sharp_L/R`,
  `Mouth_Frown_L/R`, `Mouth_Stretch_L/R`, `Mouth_Dimple_L/R`,
  `Mouth_Press_L/R`, `Mouth_Tighten_L/R`, `Mouth_Blow_L/R`,
  `Mouth_Pucker_Up_L/R`, `Mouth_Pucker_Down_L/R`,
  `Mouth_Funnel_Up_L/R`, `Mouth_Funnel_Down_L/R`,
  `Mouth_Roll_In_Upper_L/R`, `Mouth_Roll_In_Lower_L/R`,
  `Mouth_Roll_Out_Upper_L/R`, `Mouth_Roll_Out_Lower_L/R`,
  `Mouth_Push_Upper_L/R`, `Mouth_Push_Lower_L/R`,
  `Mouth_Pull_Upper_L/R`, `Mouth_Pull_Lower_L/R`,
  `Mouth_Up`, `Mouth_Down`, `Mouth_L`, `Mouth_R`,
  `Mouth_Upper_L/R`, `Mouth_Lower_L/R`, `Mouth_Shrug_Upper`,
  `Mouth_Shrug_Lower`, `Mouth_Drop_Upper`, `Mouth_Drop_Lower`,
  `Mouth_Up_Upper_L/R`, `Mouth_Down_Lower_L/R`, `Mouth_Chin_Up`,
  `Mouth_Contract`
- Cheeks: `Cheek_Raise_L/R`, `Cheek_Suck_L/R`, `Cheek_Puff_L/R`
- Support (brow/eye/nose used by emotion layers): `Brow_Raise_Inner_L/R`,
  `Brow_Raise_Outer_L/R`, `Brow_Drop_L/R`, `Brow_Compress_L/R`,
  `Eye_Blink_L/R`, `Eye_Squint_L/R`, `Eye_Wide_L/R`, `Eye_*_Look_*`,
  `Nose_Sneer_L/R`, `Nose_Nostril_Dilate_L/R`

ARKit → CC mapping authority: `ARKIT_TO_CC` in
`AI-Avatar-Engine/blender/scripts/inspect_asset.py` (e.g. mouthFunnel =
4 CC funnel keys, mouthPucker = 4 pucker keys, browInnerUp = both
`Brow_Raise_Inner_*`).

### 1.4 CRITICAL jaw/teeth mechanics (drives the whole design)

`CC_Toon_Teeth_01` (the HUGE toon teeth, 6362 verts) has **no** `Jaw_*` or
`V_*` follower shape keys — only tooth-shape/identity keys. Lower teeth move
**only** via bone `CC_Base_Teeth02`, a child of `CC_Base_JawRoot`. The tongue
root bones (`CC_Base_Tongue01/02/03`) are also JawRoot children.

Consequence: mouth openness MUST be driven primarily by rotating
`CC_Base_JawRoot` (skin is skinned to it; teeth + tongue follow through the
bone hierarchy). The `Jaw_Open` shape key is a skin-only shaper — used at low
weight for lip-skin compression realism, never as the main opener, or the
giant lower teeth stay closed behind an open mouth (or poke through when
mixed wrongly).

Phase B step 0 = a one-off calibration render: JawRoot rotated in small
increments on each local axis (± a few degrees) + `Jaw_Open`-only + mixed, to
lock (a) the correct rotation axis/sign, (b) degrees-per-"open unit"
(expected usable range ≈ 0–12° for speech; cartoon reads best conservative),
(c) the bone:shape-key mix ratio where teeth track lips cleanly. All jaw
values below are in normalized `jaw` units 0–1 mapped through this
calibration.

### 1.5 Frame rate

Deliverables are 30 fps (project convention, `rig_reference.json`).
NOTE: the blend's scene `render.fps` is **60** — the generator must
explicitly set/assume 30 fps and author keyframes in 30 fps frames, not trust
scene fps. Flagged to main.

Cross-mesh fan-out (same-named keys on eyebrows/tearline/occlusion/tongue
meshes) is handled by the framework — the sequencer emits each key name once.

---

## 2. Speech sequencer — architecture

A pure-Python procedural generator (no bpy dependency in the core) that
turns a **style parameter set + seed** into a **keyframe schedule**, which
the clip recipes feed to the animation framework.

```
StyleParams + seed
      │
      ▼
[1] Phrase planner      → list of phrases (start, dur, stress pattern, pause after)
      │
      ▼
[2] Syllable generator  → per phrase: syllable events (t, dur, onset viseme,
      │                    nucleus viseme, coda?, stress, amplitude)
      ▼
[3] Viseme scheduler    → per-viseme keyframe tracks w/ coarticulation overlap
[4] Jaw solver          → low-pass jaw curve from vowel openness (bone + key)
[5] Ornament layers     → breath, blinks, brow/head emphasis, tongue flickers,
      │                    micro asymmetry, amplitude declination
      ▼
Schedule { shape_keys: {name: [(frame, value), …]},
           bones:      {bone_name: channel keyframes} }   → framework
```

Determinism: single seeded RNG (`random.Random(seed)`); every clip is
reproducible. Each named clip uses a fixed seed committed in the recipe.

### 2.1 StyleParams (the preset surface)

| Param | Meaning | Typical range |
|---|---|---|
| `syllable_rate` | mean syllables/s | 2.2–5.5 |
| `rate_jitter` | log-normal sigma on syllable duration | 0.15–0.4 |
| `phrase_len_range` | (min, max) seconds per phrase | (1.5, 4.0) |
| `pause_range` | (min, max) seconds between phrases | (0.3, 1.0) |
| `jaw_amplitude` | peak jaw units on stressed open vowels | 0.15–0.85 |
| `jaw_floor` | fraction of local jaw level kept between syllables | 0.3–0.6 |
| `viseme_energy` | scale on all viseme key weights | 0.4–1.0 |
| `coarticulation_overlap` | viseme cross-fade as fraction of viseme dur | 0.3–0.6 |
| `emphasis_prob` | P(stressed syllable gets brow/head accent) | 0.05–0.5 |
| `breath_depth` | chest-rise + breath visibility 0–1 | 0.2–1.0 |
| `head_motion_scale` | scale on head-nod/emphasis rotations | 0.3–1.5 |
| `articulation` | consonant undershoot (fast speech mumbles) | 0.5–1.0 |
| `asymmetry` | L/R mouth bias (`Mouth_L/R`, per-side smile delta) | 0–0.15 |
| `vowel_bias` | weights over nucleus visemes (style color) | per-style |
| `declination` | amplitude decay across each phrase | 0.1–0.3 |

### 2.2 Phrase planner

- Sample phrase durations uniform in `phrase_len_range`, pauses in
  `pause_range`; fill the clip so the **last phrase ends ≥ 1.0 s before loop
  end** (loop closes inside a pause — §5).
- Anti-repetition: consecutive phrases must differ in syllable count by ≥ 2
  and no two consecutive pauses within 0.1 s of each other; reject-and-resample.
- Stress pattern: mark ~1 syllable per ~0.9 s as stressed (randomized),
  always including the phrase-initial region — natural speech front-loads
  energy; `declination` then decays amplitude toward phrase end.

### 2.3 Syllable generator

Each syllable = optional **onset** (consonant) + **nucleus** (vowel) +
occasional **coda** (consonant, p≈0.25). Durations: nucleus 55–70 % of the
syllable, onset/coda split the rest. Syllable duration = 1/`syllable_rate`
× log-normal jitter (`rate_jitter`) — this jitter is the #1 anti-metronome
device, CV of inter-syllable intervals must exceed 0.25 (QA §6).

Viseme casting (weights are pre-`viseme_energy` peaks):

| Role | Viseme | Peak | Jaw contribution | Notes |
|---|---|---|---|---|
| nucleus AA/AH | `V_Open` | 0.7–1.0 | 1.0 × amp | the big vowel |
| nucleus EE/EH | `V_Wide` | 0.6–0.9 | 0.45 × amp | spread lips |
| nucleus OH/OO | `V_Tight_O` | 0.6–0.9 | 0.55 × amp | rounded |
| nucleus UH (reduced) | `V_Open` 0.35 + `V_Lip_Open` 0.3 | — | 0.35 × amp | schwa, most common |
| onset B/M/P | `V_Explosive` | 0.8–1.0 | forces jaw dip ≤ 0.1 | lips must touch: momentarily suppress smile layer (§4.2) |
| onset F/V | `V_Dental_Lip` | 0.7–0.9 | jaw dip ≤ 0.15 | |
| onset CH/J/SH | `V_Affricate` | 0.6–0.8 | ≤ 0.3 | |
| onset S/T/D/N/L | `V_Tight` 0.4 + tongue flicker | ≤ 0.3 | `V_Tongue_up` or `V_Tongue_Raise` 0.2–0.4, 2-frame attack | alveolar illusion |
| onset K/G/generic | `V_Lip_Open` | 0.4–0.6 | ≤ 0.35 | soft default |
| coda | reuse onset table at 0.6 × peak | | | |

Nucleus sampling uses `vowel_bias` (e.g. happy biases `V_Wide`, serious
biases `V_Open`/`V_Tight_O` low-energy). Consecutive nuclei must not repeat
more than twice (anti-babble-loop). `articulation` < 1 scales consonant peaks
down and shortens them (fast-speech undershoot).

### 2.4 Viseme scheduler — coarticulation

Never snap. Each viseme event becomes keys:
`(t_start − overlap·dur) 0 → (t_peak) peak → (t_end + overlap·dur) 0` with
ease-in/out tangents; adjacent events on the SAME key merge (max), events on
different keys simply overlap → natural cross-fade blending.
`overlap = coarticulation_overlap × event_dur` (clamped 2–6 frames @30fps).

Energy governor: at every frame, if Σ(active viseme weights) > 1.3, scale
that frame's viseme values by 1.3/Σ — prevents mouth blow-out when overlaps
stack (soft-normalized, keeps relative shape).

### 2.5 Jaw solver — the anti-jaw-flap core

The jaw is SLOWER than the lips and does not close between syllables:

1. Build target openness signal: per syllable nucleus, its
   `jaw contribution` (table above) × syllable amplitude × `jaw_amplitude`.
2. Between adjacent syllables inside a phrase, jaw only dips to
   `jaw_floor` × min(neighbor peaks) — never to 0.
3. Consonant closures (`V_Explosive`/`V_Dental_Lip`) insert hard dips
   (≤ 0.1–0.15) — these are the ONLY inter-syllable near-closures.
4. Low-pass the resulting polyline: jaw attack ≈ 80–120 ms, release ≈
   120–180 ms (vs lip keys at 40–70 ms) — keyframes with eased tangents, no
   per-frame bake.
5. Full closure ONLY at phrase ends: ramp to 0 over ~200 ms into the pause,
   ending in a lip press (§2.6).
6. Output split: normalized jaw value → `CC_Base_JawRoot` rotation (primary,
   via §1.4 calibration) + `Jaw_Open` key at `key_ratio` (calibrated,
   expected ≈ 0.2–0.35 of jaw value). Tiny `Jaw_L/R` drift (±0.03, slow
   noise) adds life; `Jaw_Forward` reserved for the angry layer.

Amplitude variation: syllable amplitude = stress (1.0 stressed / 0.55–0.8
unstressed, randomized) × phrase envelope (fast rise over first 2 syllables,
`declination` decay to phrase end) × slow ±10 % wander across the clip.

### 2.6 Breath & pause behavior

At every phrase boundary pause (0.3–1.0 s):
- Jaw eases closed (§2.5.5); `Mouth_Close` NOT used (it fights visemes) —
  closure is jaw + visemes→0.
- Lip press: `Mouth_Press_L/R` rise to 0.12–0.28 (asymmetric ±20 %) for
  200–350 ms — reads as "thinking of the next phrase".
- Breath (visible when pause ≥ 0.45 s): chest rise via `CC_Base_Spine02`
  pitch (−0.8° to −1.6° × `breath_depth`, ~60 % of pause in, 40 % out,
  eased) + optional `Nose_Nostril_Dilate_L/R` 0.1–0.2 flicker on deep
  breaths + shoulder hint via both `CC_Base_*_Clavicle` +0.5° roll. Subtle:
  breath is felt, not performed.
- Occasional (p≈0.2) swallow on long pauses: `Neck_Swallow_Up/Down`
  micro-sequence, 0.15 peak.

### 2.7 Blinks, gaze, brow/head emphasis (speech-coupled ornaments)

- Blinks continue during speech: base gap 2.5–5 s (≈15–20/min), plus a
  boundary-biased blink: p=0.55 of a blink landing within ±200 ms of each
  phrase end. Blink = `Eye_Blink_L/R` 0→1→0 over 7–9 frames (asym 1-frame L/R
  offset). If the idle/base layer already provides blinks, the framework
  layering decides ownership — flagged to main (§7).
- Emphasis on stressed syllables (p = `emphasis_prob`): brow raise
  (`Brow_Raise_Inner_L/R` 0.15–0.35 + `Brow_Raise_Outer_*` at 60 %) rising
  ~2 frames BEFORE the syllable peak (anticipation), decaying over 300–450 ms
  — brows lead the voice. Alternating/random choice of: brow-only, nod-only
  (`CC_Base_Head` pitch 1–2.5° down-up over ~350 ms × `head_motion_scale`),
  or both (p=0.3). Never two consecutive identical emphasis gestures.
- Continuous head life: tiny 3-axis smoothed noise on `CC_Base_Head`
  (±0.6°, period 2–4 s) so the head is never frozen between accents.
  (If the base idle layer already owns head noise, this sub-layer is
  disabled — framework layering question, §7.)
- Micro asymmetry: constant per-clip `Mouth_L` OR `Mouth_R` bias 0.02–0.06
  and one smile corner +15 % over the other (`asymmetry` param) — kills the
  mirror-perfect CG look.

---

## 3. Style presets (the 6 talk_* parameter sets)

All: 30 fps, loop 10–15 s, seeded. Values = the StyleParams of §2.1.

| Preset | rate | phrase_len | pause | jaw_amp | vis_energy | overlap | emph_p | breath | notes |
|---|---|---|---|---|---|---|---|---|---|
| `talk_idle` | 3.2 | (1.5, 3.0) | (0.4, 0.9) | 0.35 | 0.7 | 0.45 | 0.12 | 0.5 | relaxed default; moderate everything |
| `talk_soft` | 2.8 | (1.5, 3.5) | (0.5, 1.0) | 0.22 | 0.55 | 0.55 | 0.08 | 0.6 | gentle, rounded (vowel_bias → `V_Tight_O`), slow jaw release |
| `talk_fast` | 5.0 | (2.5, 4.0) | (0.3, 0.5) | 0.28 | 0.6 | 0.35 | 0.18 | 0.35 | articulation 0.6 (undershoot), quick shallow breaths |
| `talk_excited` | 4.3 | (2.0, 4.0) | (0.3, 0.6) | 0.7 | 0.95 | 0.4 | 0.45 | 0.8 | head_motion 1.4, `Eye_Wide` 0.15 base, big amplitude swings |
| `talk_serious` | 2.9 | (2.5, 4.0) | (0.5, 1.0) | 0.4 | 0.75 | 0.5 | 0.15 | 0.6 | narrow amplitude variance, slight `Brow_Compress` 0.12, head_motion 0.5, slow single nods |
| `talk_whisper` | 3.0 | (1.5, 2.8) | (0.5, 1.0) | 0.12 | 0.8 | 0.5 | 0.06 | 0.9 | whisper = lips articulate MORE, jaw barely moves; lean-in `CC_Base_Head` pitch +1.5° held; audible-breath pauses; `Mouth_Tighten` 0.1 base |

`talk_*` presets are the reusable sequencer configurations; the `talking_*`
emotion clips below are shipped clips = preset + an emotion layer.

---

## 4. Emotion clip recipes (talking_*)

### 4.1 Recipe table

| Clip | Base preset | Emotion layer on top |
|---|---|---|
| `talking_neutral` | `talk_idle` | none — the clean reference clip |
| `talking_happy` | `talk_idle`, rate 3.6, vowel_bias→`V_Wide` | `Mouth_Smile_L/R` base 0.30/0.35 (asym), `Cheek_Raise_L/R` 0.15, brow raises at 1.3×, `Eye_Squint` 0.08 (smiling eyes) |
| `talking_angry` | `talk_serious`, overlap 0.35 (harder attacks), emph_p 0.5 | `Brow_Drop_L/R` 0.45 + `Brow_Compress_L/R` 0.3 held, `Nose_Sneer` flickers 0.15 on stresses, `Jaw_Forward` 0.1, emphasis = head THRUSTS (forward pitch) not nods, `Mouth_Press` 0.2 in pauses, `Eye_Squint` 0.15 |
| `talking_excited` | `talk_excited` | `Eye_Wide_L/R` 0.2, `Brow_Raise_Inner+Outer` frequent, 2 fast double-nods per clip, breath prominent |
| `talking_serious` | `talk_serious` | `Brow_Drop` 0.12 held, one slow deliberate nod on a long phrase, gaze steady (no gaze drift) |
| `talking_fast` | `talk_fast` | none beyond preset (undershoot IS the character) |
| `talking_slow` | rate 2.4, articulation 1.0, pause (0.6, 1.1) | deliberate: longer vowels (nucleus 75 %), emphasis brow raises slow (500 ms decay), thoughtful lip presses |
| `talking_laughing` | `talk_idle`, rate 3.6 | speech interleaved with laugh bursts — §4.3 |
| `talking_thinking` | `talk_soft`, rate 2.7, pause (0.7, 1.2) | gaze-up drifts + hesitations — §4.4 |

### 4.2 Layering rules (conflict policy)

- Emotion base weights on mouth keys (smile/frown) are a CONSTANT layer under
  the viseme layer; during bilabial/labiodental closures
  (`V_Explosive`/`V_Dental_Lip` active > 0.5) the smile layer is scaled to
  40 % for those frames — otherwise lips visibly fail to touch and the plosive
  reads broken.
- `Mouth_Press_*` only in pauses (never concurrent with visemes > 0.1).
- The §2.4 energy governor runs over visemes + emotion mouth keys combined
  (cap 1.4 for the combined set).
- Brow emotion holds (drop/compress) are constant; emphasis raises ADD on
  top and are clamped to 0.8 total.

### 4.3 talking_laughing structure

12–15 s: `phrase → phrase → LAUGH BURST → recovery → phrase → mini-burst →
pause(loop point)`. Laugh burst (1.2–2.0 s):
- Jaw pulses at 4.5–6 Hz: jaw 0.5–0.65 with dips to 0.25 (never closed),
  viseme mix `V_Open` 0.6 + `V_Wide` 0.35 held while pulsing.
- `Mouth_Smile_L/R` ramp to 0.7, `Cheek_Raise` 0.5, `Eye_Squint` 0.45–0.6
  (eyes nearly shut = the laugh sells here, not the jaw).
- Head: tilt back 3–4° pitch up over the burst, small roll wobble; shoulder
  shake = both clavicles ±0.8° at the SAME frequency as jaw pulses (phase
  locked — it is one physical event), spine02 ±0.4°.
- Breath crash at burst end: big inhale (breath_depth 1.0) + smile decays to
  0.35 residue that persists through the following speech (happy contagion),
  decaying fully only by the loop-point pause (loop safety).
- Mini-burst later = 0.6 s, 60 % amplitudes, keeps the loop from feeling
  scripted A-B-A.

### 4.4 talking_thinking structure

- Pauses are the content: p=0.6 of pauses get a gaze-up drift
  (`Eye_L/R_Look_Up` 0.25 + head pitch up 1.5°, ease 400 ms, hold, return),
  alternating with lip-purse holds (`Mouth_Pucker_Up/Down_L/R` 0.12 +
  `Mouth_Press` 0.15).
- Hesitation "um": 1–2 per clip — a single long low-energy `V_Open`
  (0.3, 0.4–0.6 s) with jaw 0.15, brow micro-furrow (`Brow_Compress` 0.15)
  during it.
- One eyebrow-flash "idea" moment (`Brow_Raise_Inner+Outer` 0.4, quick)
  followed by a slightly faster phrase (rate ×1.15) — the thought landing.

---

## 5. Loop strategy (10–15 s, boundary invisible)

1. Loop point lives INSIDE a pause: last phrase ends ≥ 1.0 s before end;
   frame 0 = mid-pause rest pose (jaw 0, visemes 0, breath mid-cycle).
2. First/last frames match in VALUE AND VELOCITY: the final breath curve is
   authored to end exactly at the frame-0 breath phase; head noise uses
   periodic (loopable) noise — sum of 2–3 sines with periods that divide the
   clip length, not raw Perlin.
3. All emotion residues (laugh smile decay, thinking gaze) must be fully
   returned to the layer's base value by loop end.
4. Anti-repetition inside the clip: 3–5 phrases, no two alike in
   syllable-count pattern or emphasis-gesture sequence (§2.2, §2.7); a
   12 s clip at ~3.5 syl/s gives ~35 distinct-jittered syllables — enough
   variety that the loop reads as "still talking" on 3rd+ viewing.
5. Blink schedule wraps: last blink ≥ 1.2 s before end, none at frame 0.

---

## 6. Phase B self-review / QA checklist (per clip)

- [ ] Jaw curve: no zero-crossing between syllables inside a phrase
      (except plosive dips); attack ≥ 80 ms; never a sawtooth.
- [ ] Inter-syllable interval CV ≥ 0.25 (anti-metronome, computed from the
      schedule itself — assert in the generator).
- [ ] Frame-wise Σ visemes ≤ 1.3 (+ emotion mouth ≤ 1.4).
- [ ] Teeth: lower teeth track the jaw (bone-driven), never poke lips at max
      jaw — verify on max-jaw frame render.
- [ ] Loop: frame 0 == frame N pose (assert numerically) + eyeball the
      boundary in the rendered preview played 3×.
- [ ] Blink count in 15–22/min band; ≥ 1 boundary blink.
- [ ] Phrase/pause structure audible in the render ("can I hear the
      sentences?") — subjective pass on turntable + front renders.
- [ ] Style differentiation: talk_soft vs talk_excited must be tellable from
      SILHOUETTE alone (jaw amplitude + head energy).

---

## 7. Uncertainties / questions for main (Phase B blockers)

1. **Framework channel API**: exact schedule format it accepts (shape-key
   fcurves? per-frame bake? bone rotation convention — euler order, local
   axes?). The sequencer core is format-agnostic; the emit step adapts.
2. **Layer ownership**: does a shared idle/base layer already provide blinks
   + head noise + breath, with talk clips expected to layer OVER it? If so I
   disable §2.6/§2.7 ambient parts and keep only speech-coupled events
   (boundary blinks, emphasis nods, pause breaths).
3. **Jaw calibration**: JawRoot axis/sign/range + bone-vs-`Jaw_Open` ratio —
   resolved by Phase B step 0 render calibration (§1.4); flagging in case the
   rig agent already measured this.
4. **FPS**: blend scene fps is 60; plan authored for 30 fps deliverables per
   rig_reference.json — confirm framework renders at 30.
5. `V_None` does not exist on the body — assuming "rest = all visemes 0".
