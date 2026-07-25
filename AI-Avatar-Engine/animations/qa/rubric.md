# Animation QA Rubric

Quality bar: Meta Avatars / Apple Memoji / Ready Player Me. The avatar must feel
ALIVE — never frozen, never robotic. Every clip is scored 1–10 on each dimension
below. **Gate: every applicable dimension must score >= 9 to ship.** One 8 = the
clip goes back with notes. Dimensions that don't apply to a clip (e.g.
hand/finger life on a blink) are marked N/A, not skipped silently — the reviewer
writes N/A explicitly.

Reference data: `rig_reference.json` (same folder) — bone list, shape-key
classification, cross-mesh key map, and `never_animate_keys` (identity morphs +
TL/EO utility keys). The clip contract lives in `../library_spec.json` (beats,
layers, hooks, transition/pose contracts).

## Scoring dimensions

### 1. Weight & balance
Does the body obey gravity? Weight visibly commits to a support leg; actions
that move mass show anticipation (unload before a step, crouch before a jump,
nose-over-toes before standing); impacts are absorbed through knees/spine, not
stopped dead.

- 9–10: weight readable in silhouette at every frame; counter-balance present
  (hip jut with shoulder counter-tilt, arm balance on step_back).
- REJECT examples: foot leaves the ground with no prior weight transfer; hips
  perfectly level during a lean; stand_up with a vertical spine (physically
  impossible); landing absorbed in 0–1 frames.

### 2. Timing & spacing
Ease-in/ease-out everywhere; anticipation before main actions; overshoot and
settle after them; follow-through on chains (wrist trails forearm, fingers trail
wrist).

- 9–10: every major action has antic → action → overshoot → settle; drag chains
  ordered correctly; fast things are fast (saccades 2–3f, surprise onset <=6f)
  and slow things slow (sad onset >=15f).
- REJECT examples: **linear interpolation on limb rotation = automatic
  reject**; nod with no upward anticipation; gesture that stops at its end pose
  with non-zero velocity (no settle); all joints of an arm arriving on the same
  frame; a "slow" clip made by time-stretching a normal clip's curves.

### 3. Naturalness (asymmetry, no mechanical repetition)
Humans are asymmetric and aperiodic. Left/right differ in amplitude or phase;
repeated events differ in spacing and size; mirrored clips are re-authored, not
byte-mirrored.

- 9–10: no two repeats identical (claps at 8,7,9,8f; decaying wave amplitudes);
  shoulders never perfectly level; L/R walk strides differ ~2%.
- REJECT examples: evenly spaced repeats of anything (nods, taps, jaw pulses,
  scroll flicks); an oscillation at constant amplitude (shake_no must decay
  12→7→3 deg); tilt_right that is a byte-mirror of tilt_left; both fists
  perfectly mirrored in celebrate.

### 4. Facial aliveness
The face is never a held pose. Onsets ordered correctly (Duchenne: cheeks before
corners; surprise: brows before jaw; sad: face before head). Holds carry micro
variation. Expressions are asymmetric.

- 9–10: hold phases waver (+-0.03–0.05); emotion arrives in the documented
  order; co-articulation on smiles during speech (corners reduce through rounded
  visemes and rebound).
- REJECT examples: any facial hold frozen at constant values for >2 s; smile
  with zero eye/cheek engagement (dead-eye smile); perfectly symmetric
  expression at full amplitude; expression pops on in <4f when the spec says
  slow; visemes at 1.0 (over-articulated puppet); no pauses/breath in a talking
  clip.

### 5. Hand & finger life
Hands are half the aliveness budget. Fingers hold soft natural curls, cascade
rather than snap, and never freeze.

- 9–10: finger motion phase-offset per finger; grips form during the reach, not
  before; contact poses (clasp, pocket, face) land without interpenetration and
  with a settle.
- REJECT examples: **fingers static for >2 s in any body clip = reject**;
  board-flat palm with locked fingers; fist forming in a single frame; finger
  interpenetration at ANY frame of a clasp/heart/crossed-arms pose; both hands'
  wrist noise mirrored in the micro layer.

### 6. Eye behavior
Eyes lead, head follows, torso last. Saccades ballistic (2–3f) with 1–2%
overshoot and fixation micro-drift; lids follow vertical gaze; blinks mask gaze
shifts; eyes counter-rotate against head motion to hold targets
(vestibulo-ocular reflex).

- 9–10: gaze chain order correct everywhere; fixation drift present but subtle;
  pupil response used where specified (focus/lose_focus); blink cadence hints in
  metadata for states that alter it (serious: 5–6 s, angry hold: suppressed).
- REJECT examples: **both eyelids keyed with identical frames and identical
  values = reject**; eyes glued to head rotation during nods/shakes; slow eased
  eye travel on a saccade (dead eyes); no lid lift on up-gaze; gaze frozen with
  zero drift for >1.5 s; head moving before the eyes on any look-at.

### 7. Loop seamlessness
Loop clips must be undetectable at the seam over 3+ consecutive plays.

- 9–10: first/last keys match in value AND tangent; event schedule doesn't
  cluster near the seam; additive layers are zero-delta at both ends; dance
  seam preserves the beat grid.
- REJECT examples: **loop pops at boundary = reject** (position OR velocity
  discontinuity); a micro-event visibly "resetting" at the seam; additive
  breathing layer with non-zero boundary deltas (breaks stacking); visible
  repeat period inside a "non-periodic" micro layer.

### 8. Technical (keyframe hygiene, GLB compatibility)
- Action name == clip id (snake_case) == glTF animation name; 30 fps.
- No keys on `never_animate_keys` (identity morphs, TL/EO utility keys), on
  twist/share helper bones, or on identity sliders — check against
  `rig_reference.json`.
- Cross-mesh contract: every keyed shape key driven on EVERY mesh sharing that
  key name (192 shared keys — body, Toon_Eyebrows, TearLine, EyeOcclusion,
  Tongue, Teeth, Eye). Eyelash_* keys mirror Eye_Blink curves.
- Bone rotations quaternion, bezier interpolation; no redundant keys; no
  subframe keys; values within slider min/max; clip passes `verify_glb.py`
  re-import and plays in the sandbox viewer.
- Pose contracts: entry clips end exactly on their hold-loop's first frame;
  exits start exactly on the hold's pose (transition_model in the spec).
- REJECT examples: a single key on `face_width` or any identity morph anywhere
  in the action; blink clip that leaves TearLine/EyeOcclusion/Eyelash keys
  undriven (lash/tearline detaches from the lid); euler keys on limbs;
  animation named "Action.003"; keyed twist bones; a viseme value of 1.2.

## Review protocol

1. Automated pre-pass (QA scripts): action naming, fps, forbidden keys
   (never_animate + twist bones), interpolation mode scan, loop boundary
   value/tangent diff, cross-mesh key coverage, slider range check. Any hit =
   instant reject, no human review spent.
2. Playblast review at 1x and 0.25x speed, front + three-quarter (same camera
   convention as `render_meta_look.py`). Loops watched 3x consecutive.
3. Score the 8 dimensions; any applicable dimension < 9 → reject with
   frame-specific notes referencing the beat-sheet in `library_spec.json`.
4. Stack test for layered clips: additive layers verified OVER idle_01 and over
   talking_neutral (not in isolation). Blink scheduler collision check for any
   clip that bakes lid motion.
5. Retarget spot-check: tier-1 clips verified on at least one other template
   (meta_female or realistic male) — shared bone/key names must carry the clip
   without re-authoring.

## Fast-reject checklist (any one = stop scoring, send back)

- [ ] Linear interpolation on any limb rotation channel
- [ ] Loop pop (value or tangent) at seam
- [ ] Identical L/R eyelid curves
- [ ] Fingers static > 2 s in a body clip
- [ ] Face static > 2 s in any non-N/A facial clip
- [ ] Any identity/customization or TL/EO key animated
- [ ] Cross-mesh follower keys missing (lash/tearline/teeth/tongue desync)
- [ ] Evenly-spaced repeated events (metronome anything)
- [ ] Head moves before eyes on a gaze change
- [ ] Interpenetration in any contact pose (clasp, crossed arms, face touch)
- [ ] Entry/exit pose contract broken (doesn't match its hold clip's frame)
- [ ] Byte-mirrored L/R variant of another clip
