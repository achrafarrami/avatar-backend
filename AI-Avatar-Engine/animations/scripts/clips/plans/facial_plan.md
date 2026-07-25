# Facial Animation Plan — Part 1: Conventions, Key Inventory, Eyes, Micro Layer

> **Phase B reconciliation (2026-07-24):** `animations/library_spec.json` is
> AUTHORITATIVE for clip ids/durations/beats — the clip lists below were the
> Phase A draft and differ in ids and counts. Implemented Tier 1 (17
> facial-owned clips) lives in `scripts/clips/{eyes,expressions,micro}.py`.
> **Measured gaze calibration** (supersedes the GAZE macro's assumption):
> the `Eye_*_Look_*` SHAPE keys move lid/socket skin only — the iris does
> not move (CC_Base_Eye has no horizontal/up look keys). Iris aim =
> CC_Base_L/R_Eye BONES: local **+z = character's LEFT** (16 deg per 1.0
> gaze unit), **+x = DOWN** (12 deg/unit up, 13 down) — pixel-verified on
> renders. Look keys remain keyed as the lid-follow layer, exactly as the
> macro intended. Blinks: always `motion.add_blink` (Eye_Blink_* carries
> the lashes on this rig — never key `Eyelash_*` manually).

Owner: facial agent. Target rig: `meta_avatar/blender/base/meta_male.blend`
(MetaMale_Body + 5 follower meshes + MetaMale_Armature, 101 bones). 30 fps.
Part 2 (16 expressions + 6 listening clips): `facial_plan_expressions.md`.

Quality bar: Apple Memoji / Meta Avatars. A frozen face at any frame of any
clip is a reject. Every hold has micro-motion; nothing is ever keyed L/R
symmetric; onsets are fast (3–7 f), decays slow and asymmetric (2–3x onset).

---

## 1. Verified key inventory (dumped from meta_male.blend, read-only)

Body mesh `MetaMale_Body`: 171 keys. Expression keys by region
(all fan out by same name to follower meshes — see section 2):

| Region | Keys |
|---|---|
| Brows (8) | Brow_Raise_Inner_L/R, Brow_Raise_Outer_L/R, Brow_Drop_L/R, Brow_Compress_L/R |
| Lids (6) | Eye_Blink_L/R, Eye_Squint_L/R, Eye_Wide_L/R |
| Eyes-look (8) | Eye_L_Look_L/R/Up/Down, Eye_R_Look_L/R/Up/Down (suffix = CHARACTER-space direction; ARKit eyeLookIn/Out maps crosswise, see ARKIT_TO_CC) |
| Eyelashes (8) | Eyelash_Upper_Up/Down_L/R, Eyelash_Lower_Up/Down_L/R (secondary — co-key with lids) |
| Ears (6) | Ear_Up/Down/Out_L/R (unused by this plan) |
| Nose (16) | Nose_Sneer_L/R, Nose_Nostril_Raise/Dilate/Down/In_L/R, Nose_Crease_L/R, Nose_Tip_L/R/Up/Down |
| Cheeks (6) | Cheek_Raise_L/R, Cheek_Suck_L/R, Cheek_Puff_L/R |
| Mouth (~60) | Smile, Smile_Sharp, Frown, Stretch, Dimple, Press, Tighten, Blow, Pucker_Up/Down, Funnel_Up/Down, Roll_In/Out_Upper/Lower, Push/Pull_Upper/Lower, Up/Down/L/R, Upper/Lower_L/R, Shrug_Upper/Lower, Drop_Upper/Lower, Up_Upper_L/R, Down_Lower_L/R, Chin_Up, Close, Contract (all _L/_R paired where applicable) |
| Jaw keys (7) | Jaw_Open/Forward/Backward/L/R/Up/Down (see JAW macro — bone is source of truth) |
| Tongue (body) | Tongue_Bulge_L/R only; full Tongue_* set lives on CC_Base_Tongue |
| Pupil (2) | Eye_Pupil_Dilate/Contract — NOT on body; on CC_Base_Eye, TearLine, EyeOcclusion, Toon_Eyebrows only |

NEVER keyed by facial clips: identity morphs (face_width ... philtrum_length,
head_size, body_weight), `TL *`/`EO *` utility keys, `Head_*`/`Neck_*`
correctives (fire with head-bone rotation, owned by body/tech layer),
visemes `V_*` (speech layer). Matches `animations/qa/rig_reference.json`
`never_animate_keys`.

Bones used by facial clips (from rig_reference.json, all children of
CC_Base_FacialBone unless noted):
- `CC_Base_JawRoot` — gross jaw open/side/jut. CONFIRMED by lead (lipsync
  recon): teeth mesh `CC_Toon_Teeth_01` has ZERO jaw/viseme follower keys —
  lower teeth move ONLY via the `CC_Base_Teeth02` bone under JawRoot. Any
  visible mouth-open MUST rotate JawRoot (see JAW macro); Jaw_Open/mouth keys
  shape the skin but never move teeth. Exact jaw axis/sign convention will be
  in the tech agent's framework README — recipes quote degrees, not radians
  on a guessed axis.
- `CC_Base_L_Eye` / `CC_Base_R_Eye` — eyeball aim (gross gaze). Heads at
  (±4.252, −5.58, 163.16); toon eyes are large, keep rotations modest.
- NOT touched by facial: CC_Base_Head (body agent), CC_Base_Teeth01/02,
  UpperJaw (static), Tongue01–03 (speech layer).

## 2. Cross-mesh fan-out contract (for the framework)

Same-named keys exist on up to 5 meshes and MUST be keyed together
(framework fans out automatically per rig_reference.json `cross_mesh_keys`).
Groups my clips rely on:
- Brow_* → Body + Toon_Eyebrows + TearLine + EyeOcclusion. Toon_Eyebrows is
  the VISIBLE floating brow mesh — brow motion that skips it is invisible.
- Eye_Blink/Squint/Wide/Look_* → Body + Toon_Eyebrows + TearLine +
  EyeOcclusion (+ CC_Base_Eye for the two Look_Down deform keys).
- Eye_Pupil_Dilate/Contract → CC_Base_Eye + TearLine + EyeOcclusion +
  Toon_Eyebrows. ABSENT from body: the framework's canonical key list must be
  the UNION across meshes, not the body's list, or pupil keys silently no-op.
- Mouth_*/Jaw_*/Cheek_*/Nose_* → Body (+ zero-delta copies on follower
  meshes; keying them by name is harmless and expected).
- Eyelash_* → keyed explicitly by my recipes (they do NOT auto-follow lids).

## 3. Shared macros (referenced by every recipe; implement once in Phase B)

**STD_BLINK(f0, amp=1.0, slow=False)** — the only legal blink.
- L lid: f0→f0+3 Eye_Blink_L 0→1.00*amp (easeInQuad), 1 f hold,
  f0+4→f0+10 back to 0 (easeOutCubic; passes 0.05 at f0+9).
- R lid: starts f0+1 (1 f LAG), peak 0.96*amp at f0+4, opens f0+5→f0+12.
- slow=True (heavy/thinking blink): close 5 f, open 9–10 f, lag 2 f.
- Co-keys: Eyelash_Upper_Down_L/R at 1.0x the matching lid weight;
  Eye_L/R_Look_Down 0.10 peak during closure (eyes drop physiologically);
  Brow_Drop_L/R +0.02 pulse on close.
- Never two blinks < 45 f apart except deliberate double-blinks.
- Loop rule: every loop ≥ 4 s contains ≥ 1 blink; gaps 2–6 s, never metronomic
  (successive gaps must differ ≥ 20%).

**GAZE(yaw°, pitch°, dur_f)** — saccade + lid follow. Convention:
+yaw = character's right, +pitch = up. Both eye bones get the same rotation
(distance gaze; convergence noted per-clip where used).
- Bone: rotate CC_Base_L/R_Eye over dur_f (saccades 2–3 f) with 10%
  overshoot for 1 f, settle 2 f. Leading eye starts 1 f early (side stated
  per clip). Max excursion ±25° yaw, +20/−22° pitch.
- Look-key lid/socket follow at weight = |deg| / 30 * 0.5 on the matching
  direction keys (e.g. yaw −20° left → Eye_L_Look_L 0.33, Eye_R_Look_L 0.33;
  per-eye ±5% asym). CALIBRATE ratio in Phase B renders.
- Vertical lid follow: pitch > +6° → Eye_Wide 0.10–0.20 + Eyelash_Upper_Up;
  pitch < −6° → Eye_Blink 0.15–0.30 partial + Eyelash_Upper_Down (upper lid
  tracks the iris — skipping this reads dead).
- Fixation drift: any gaze hold ≥ 25 f gets ±0.5–0.8° micro-drift (2–3 steps)
  and optionally one 1° micro-saccade (1–2 f).

**JAW(open_deg)** — gross open = CC_Base_JawRoot rotation (lower teeth
follow via child bone CC_Base_Teeth02; axis/sign per framework README).
Companion skin key Jaw_Open at open_deg/15 (so 15° ≈ key 1.0) UNLESS
Phase B render shows double-displacement of the chin skin — then bone-only +
Mouth_Drop_Lower for lip part. Recipes quote both (e.g. "JAW 6° / Jaw_Open
0.18" = already de-rated pending calibration). Lips-part-WITHOUT-bite-open
uses Mouth_Drop_Lower/Drop_Upper keys ONLY (no bone, teeth stay closed).
All timings in this plan are 30 fps terms (template ships 60 fps; framework
sets the scene to 30 — do not rescale my frame numbers).

**Asymmetry law**: no L/R pair identical. Follower side = 0.88–0.97x leader
with 1–2 f lag. Leader side stated per clip (alternates across the library
so the character has no fixed "good side").

**Decay law**: decay ≥ 2x onset, two-stage (fast 60% drop, slow tail); one
side releases 2–4 f before the other; cheek/brow components linger 4–8 f
after mouth components (or vice versa, stated per clip).

**Hold-life law**: any hold ≥ 20 f contains ≥ 2 micro-events chosen from:
brow flicker ±0.02–0.05, Mouth_Press 0.03–0.05, Cheek_Raise 0.02–0.04,
Nose_Nostril_Dilate 0.02–0.04, gaze drift ≤ 1.5°, apex amplitude "breathing"
±0.03 (period 30–50 f). Peak-weight tremor never exceeds ±10% of the peak.

---

## 4. EYES — 10 clips (`scripts/clips/eyes.py`)

### 4.1 eye_blink_single — 15 f (0.50 s), one-shot
STD_BLINK(f0, amp=1.0). Nothing else. Exported standalone so the runtime can
fire blinks over any base clip that lacks its own.
Regions: lids + eyelashes + look-down co-key. Leader: L.

### 4.2 eye_blink_double — 27 f (0.90 s), one-shot
STD_BLINK(f0, 1.0); STD_BLINK(f12, 0.85) with open shortened to 5 f.
Second blink is smaller and snappier (attention reset). Leader: L both;
R lag grows to 2 f on the second (fatigue asymmetry).

### 4.3 eye_look_left — 54 f (1.8 s), one-shot
- f0–f3 GAZE(−20°, 0°) saccade, overshoot −22° at f3, settle f5. Leader: L.
- Keys at settle: Eye_L_Look_L 0.35, Eye_R_Look_L 0.33.
- f5–f38 hold: fixation drift ±0.8° (steps at ~f14, f26); Brow_Raise_Outer_L
  0.06 swell f10–f24 (attention cue on gaze side).
- STD_BLINK(f28, 0.8) mid-hold.
- f38–f41 return saccade with +2° overshoot, settle f44; residual drift to f54.

### 4.4 eye_look_right — 54 f, one-shot
Exact mirror of 4.3 (yaw +20°, Eye_*_Look_R keys, Leader: R,
Brow_Raise_Outer_R swell). Blink at f30 (schedule differs from 4.3 so the
pair doesn't read mechanical when sequenced).

### 4.5 eye_look_up — 48 f (1.6 s), one-shot
- f0–f3 GAZE(0°, +15°). Leader: L. Keys: Eye_L_Look_Up 0.30 / R 0.28.
- Lid follow: Eye_Wide_L 0.15 / R 0.13, Eyelash_Upper_Up 0.15.
- Brows follow upward gaze: Brow_Raise_Inner 0.10/0.09 + Outer 0.08/0.07
  (f4–f7, decay with the return).
- f5–f34 hold with drift; NO blink while looking up (unnatural);
- f34–f37 return; STD_BLINK(f38, 1.0) on return (blink-on-refixation).

### 4.6 eye_look_down — 48 f, one-shot
- f0–f4 GAZE(0°, −18°) (down-saccades slightly slower). Leader: R.
- Keys: Eye_L_Look_Down 0.35 / R 0.33 (also hits CC_Base_Eye deform keys).
- Lid follow: Eye_Blink 0.22/0.20 partial, Eyelash_Upper_Down 0.22; brows
  neutral (a brow drop here would read as anger).
- f6–f34 hold, drift ±0.6°; f34–f38 return; STD_BLINK(f38, 0.9).

### 4.7 eye_saccade_idle — 240 f (8.0 s), LOOP (ambient gaze life)
Fixation plan (bone yaw,pitch; saccades 2–3 f; look-keys per GAZE macro):
- f0–f55 center, drift ±0.5° (steps f18, f40).
- f55 saccade to (+8°, −3°); hold to f120 w/ drift; micro-saccade +1° f88.
- f120 saccade to (−6°, +2°) — 2 f; correction micro-saccade f130 (−1°).
- f195 saccade back to (0°, 0°); drift to f240 = f0 state (loop-safe).
- Blinks: STD_BLINK(f78, 1.0); STD_BLINK(f186, 0.9) timed to COINCIDE with
  the f195 return-saccade prep (natural blink–saccade coupling; gaps 2.6 s /
  3.6 s — non-metronomic).
- Intrinsic micro kept minimal (designed to stack with micro layer):
  Brow_Raise_Inner 0.03 swell f100–f140 only.
Leader: alternates per saccade (L, R, L).

### 4.8 eye_roll — 48 f (1.6 s), one-shot (exasperation)
- Gaze arc: (0,0) → f4 (−10°, +2°) → f8 (−6°, +18°) → f12 (0°, +20°) →
  f16 (+6°, +16°) → f20–f28 drift down to (+4°, +4°) → f30 center.
- Lids: Eye_Wide 0.15 f8–f14, then Eye_Blink 0.35 partial f16–f24 (lids
  half-close over the top of the roll), Eyelash follows.
- Brows: Brow_Raise_Inner 0.30/0.27 + Outer 0.25/0.22 peak f12, decay f18–f34.
- Mouth (unimpressed): Mouth_Press 0.15/0.12 + Mouth_L 0.06 + Mouth_Frown_L
  0.10, f10–f34.
- STD_BLINK(f30, 1.0) closes the gesture; settle to neutral by f45. Leader: L.

### 4.9 eye_wide_surprise — 39 f (1.3 s), one-shot
- f0–f3 (FAST onset): Eye_Wide_L 0.70 @f3 / R 0.65 @f4; Eyelash_Upper_Up 0.5.
- Brow_Raise_Inner 0.45/0.42 + Outer 0.40/0.36 @f4–f5.
- Eye_Pupil_Dilate 0.30 (fan-out meshes only — see section 2).
- f5–f22 hold: NO blink (startle suppresses blinking); Eye_Wide tremor ±0.02;
  two 0.6° gaze micro-saccades (f10, f16).
- f22–f39 decay two-stage; R brow releases first (f22), L f25;
  STD_BLINK(f26, 0.8) = the "reset" blink as brows fall. Leader: L.

### 4.10 eye_squint_focus — 60 f (2.0 s), one-shot
- f0–f6 onset: Eye_Squint_L 0.45 @f6 / R 0.42 @f7; Brow_Drop 0.28/0.25;
  Brow_Compress 0.30/0.28; Eyelash_Lower_Up 0.15; Nose_Crease 0.08/0.06.
- Optional convergence: each eye +1.5° toward nose (near-focus read) —
  Phase B toggle, verify no cross-eyed artifact on the big toon eyes.
- f8–f45 hold: squint tremor ±0.03 (period ~6 f, L/R out of phase);
  single brow micro-lift +0.04 f28 (re-evaluation beat); NO blink (stare).
- f45–f60 decay; brows release before lids; 0 by f60. Leader: L.

---

## 5. MICRO-EXPRESSION ADDITIVE LAYER — 4 loops (`scripts/clips/micro.py`)

Purpose: continuous sub-perceptual life over ANY base clip. Runtime sums
weights (additive). Design rules that make them collision-free:
- All weights ≤ 0.06; all curves start AND end at 0 (loop-safe, pop-free).
- NEVER touch: Eye_Blink_*, Eye_*_Look_*, any Jaw_*, any V_*, Mouth_Funnel/
  Pucker cores above 0.03, bones. (Blinks/gaze/jaw belong to base clips.)
- Loop lengths co-prime with common base loop lengths (240/225/180 f) so
  repetition never phase-locks: 219 f, 177 f, 291 f, 141 f.
- L/R always phase-offset 2–4 f and amp-offset ~10%.
- If the base clip drives a channel > 0.30, the runtime SHOULD attenuate the
  additive contribution on that channel by 50% (framework request; clips
  still safe without it thanks to the 0.06 cap).

### 5.1 face_micro_calm — 219 f (7.3 s)
Default under idle/neutral bases.
- Breath: Nose_Nostril_Dilate_L/R sine, peak 0.025, period 110 f (~16 bpm),
  R phase-lags 3 f.
- Brow_Raise_Inner_L/R slow drift 0→0.03→0 across full loop (R 0.025).
- Mouth_Press_L 0.03 single event f140 (6 f in, 10 f out).
- Eye_Squint_L 0.02 swell f60–f120 (R 0.015, lags 4 f).

### 5.2 face_micro_engaged — 177 f (5.9 s)
Under listening/conversation bases.
- Brow micro-flash: Raise_Inner+Outer 0.05/0.04 @f30 (5 f up, 9 f down);
  second smaller flash 0.035 @f120.
- Cheek_Raise_L/R 0.04/0.03 flicker @f70 (8 f).
- Mouth_Smile_L/R 0.03/0.025 swell f90–f140; Mouth_Dimple_L 0.03 @f75.
- Nose_Nostril_Dilate 0.03 sine period 90 f.

### 5.3 face_micro_thoughtful — 291 f (9.7 s)
Under thinking/explaining bases.
- Brow_Compress_L/R pulses 0.04/0.035 @f50, 0.03 @f190 (12 f each).
- Mouth_Press_L/R 0.05/0.04 @f80 (14 f) + Mouth_Pucker_Up_L/R 0.03 rider.
- Mouth_Tighten_L 0.03 @f210; Eye_Squint 0.03/0.025 swell f120–f180.
- Nose_Nostril_Dilate 0.02 sine period 130 f (slow deliberate breath).

### 5.4 face_micro_energetic — 141 f (4.7 s)
Under excited/energetic bases.
- Brow flashes 0.06/0.05 @f20, 0.05/0.04 @f85 (4 f up, 7 f down).
- Eye_Wide 0.03 pulse rides the f20 brow flash (2 f lag).
- Cheek_Raise 0.05/0.04 @f50, 0.04 @f110; Mouth_Smile 0.03 + Mouth_Stretch
  0.02 pulses @f55.
- Nose_Nostril_Dilate 0.04 sine period 70 f (quicker breath).

Pairing guidance (metadata to ship with clips): calm→idle/neutral bases;
engaged→listening/smile bases; thoughtful→thinking/confused/skeptical;
energetic→excited/laugh/surprise. Any pairing is SAFE (caps guarantee it),
pairing only tunes flavor.

---

## 6. Phase B self-review checklist (renders)

1. Scrub every clip at 2x zoom on eyes and mouth: no frame where the whole
   face is static (hold-life law), no symmetric L/R frame.
2. Blink integrity: lids never interpenetrate lashes/brows; Eyelash keys
   track lids; blink over any gaze direction stays clean.
3. Jaw: teeth follow every mouth-open (JawRoot keyed); no teeth-through-lip
   at Jaw_Open + smile combos (toon teeth are HUGE — check expr_laugh apex).
4. Look keys vs eye bones: iris never clips the lids; lid-follow ratio reads
   natural at ±20° yaw on the toon's oversized eyes.
5. Micro loops rendered ALONE on neutral must be barely perceptible
   (if obvious, weights are too hot); rendered OVER expr_smile_soft apex and
   listen_engaged must show zero fighting.
6. Loop clips: frame 0 == frame N pose exactly; play 3x looped, no pop.
