# Body Animation Plan — Part 1 of 2 (conventions, idle, breathing, head)

Author: body (senior body animator). Phase A planning doc — no Blender execution yet.
Part 2 (`body_plan_2.md`): gestures (18) + full-body/locomotion (18).
Clip IDs are proposals; reconcile against `animations/library_spec.json` when the
director lands it.

## 1. Rig facts (measured from meta_male.blend, read-only dump)

- `MetaMale_Armature`, 101 bones, ALL deform, no control rig — we key FK on
  deform bones directly. Raw dump: scratchpad `rig_dump.json`.
- Units cm, Z-up, character faces **-Y** in armature space. Hip z≈92.5,
  head z≈155. Rest pose is an **A-pose**: full arm slopes ~30° below
  horizontal (shoulder (16.2, 5.6, 140.1) → hand (60.3, 9.3, 114.1)).
- **Scene fps in the .blend is 60**, spec says author at 30 — flagged to main.
  All frame numbers below assume 30 fps.
- Spine chain (pelvis→head): `CC_Base_Hip` → `CC_Base_Pelvis` /
  `CC_Base_Waist` → `CC_Base_Spine01` → `CC_Base_Spine02` →
  `CC_Base_NeckTwist01` → `CC_Base_NeckTwist02` → `CC_Base_Head`.
  There is NO plain `CC_Base_Neck`; the two NeckTwist bones ARE the neck.
  Legs hang off `CC_Base_Pelvis`; clavicles + RibsTwist hang off `CC_Base_Spine02`.
- Arms: `CC_Base_{L,R}_Clavicle` → `_Upperarm` → `_Forearm` → `_Hand` →
  finger chains `_Thumb1..3`, `_Index1..3`, `_Mid1..3`, `_Ring1..3`, `_Pinky1..3`.
- Legs: `_Thigh` → `_Calf` → `_Foot` → `_ToeBase` → 5 single toe bones
  (`_BigToe1`, `_IndexToe1`, `_MidToe1`, `_RingToe1`, `_PinkyToe1`).
- Helper bones — **NEVER keyed** by clips: all `*Twist01/02` (thigh, calf,
  upperarm, forearm, neck twists are keyed as NECK, see below), all
  `*ShareBone` (elbow/knee/toe correctives), `CC_Base_{L,R}_RibsTwist` +
  `_Breast` (breathing generator territory only), facial bones
  (`FacialBone`, `JawRoot`, `Teeth*`, `Tongue*`, `_Eye`) = face agent.
  Exception: NeckTwist01/02 are structural neck bones and are keyed.
- `CC_Base_BoneRoot` = root. In-place locomotion: zero translation on it.

## 2. Shared conventions (apply to every clip in both parts)

- **Angles are semantic**: pitch+ = flex forward/down; yaw+ = turn to
  character's LEFT; roll+ = right ear toward right shoulder (head) /
  right-side-down (pelvis). Mapping semantic→bone-local Euler axes is
  resolved once in Phase B against the framework pose API, then constant.
- **Head-turn distribution** (any head yaw/pitch/roll): NeckTwist01 20%,
  NeckTwist02 30%, Head 50%. Neck leads, Head lags 1–2 f (drag).
- **Weight shift logic**: hips translate laterally over the supporting foot
  (2–4 cm on `CC_Base_Hip`), pelvis lists (roll) 2–4° with free-side hip
  dropping, Spine01+02 counter-lean 60% of pelvis list, head counters again
  so the eyeline stays level (net head roll ≤1.5°). Free knee unlocks
  (thigh/calf +4–8° flex). Transfer takes 20–30 f, never linear — ease with
  a small dip (hip drops 0.5 cm mid-transfer).
- **Asymmetry by default**: bilateral actions offset L/R by 1–2 f and
  8–15% amplitude; micro-event timings placed at irrational fractions of the
  loop (≈0.382 / 0.618 / 0.786 of duration), never at halves/quarters.
- **Finger baseline**: framework finger-relaxation generator supplies a
  relaxed curl (≈12°/8°/5° per phalanx, pinky most, index least) — clips key
  fingers only when a beat needs them, always returning to the relax pose.
- **One-shot tails**: every one-shot ends with 8–12 f easing back into the
  exact shared neutral pose so runtime can crossfade out at any point after
  the hold. Loops get framework loop-closure enforcement (pos+velocity).
- **Breathing coexistence**: breathing is a separate always-on layer owning
  Spine02 pitch ±≈1°, clavicle lift ≈1–2°, RibsTwist (see §4). Body clips
  therefore (a) keep Spine02 keys low-frequency so the layer reads on top,
  (b) declare a `breath_weight` recommendation in each beat sheet
  (1.0 idle / 0.3 walk / 0.0 run+jump), and (c) clips that slam the chest
  (bow, stretch, fist_pump) note "duck breathing to 0.2 during action,
  restore over 15 f".

## 3. IDLE — 8 loops, 8–15 s, each with 2–3 embedded micro-events

### idle_neutral_stand — 12.0 s / 360 f, loop
Baseline standing idle; everything else layers on this energy level.
- Continuous: hip sway drift ±0.8 cm lateral, ±0.5 cm fore-aft from two
  overlapping slow sines (~0.07 Hz and 0.11 Hz, phase-offset) — never still,
  never metronomic. Spine01 counter 40%. Head micro-drift ±0.8° yaw.
- Micro-events: f95 small weight shift L (hip +1.8 cm, 25 f, settle back by
  f150); f210 head drift-scan R then back (yaw -6°, 40 f arc); f300 R-hand
  finger micro-curl ripple (pinky→index cascade, 12 f, +6° curl then relax).
- Arms: ride the sway passively — upperarm ±0.6°, 2 f behind hips (drag).
- breath_weight 1.0 (breath_calm).

### idle_weight_shift — 14.0 s / 420 f, loop
Two full weight transfers, asymmetric hold lengths.
- f0–f60: neutral (both feet). f60–f95: transfer to L (hip 3.5 cm L, pelvis
  roll 3° R-side-down, spine counter 2°, head counter 1.2°, R knee unlocks
  6°). f95–f250: hold L stance w/ slow 0.5 cm drift; f160 micro: R toe
  taps once (ToeBase 12°, 8 f). f250–f290: transfer to R stance (same
  numbers mirrored ×0.88 amplitude, 2 f slower — asymmetry). f290–f400 hold
  R; f350 micro: head tilt 2.5° L. f400–f420: ease toward neutral = loop.
- Arm drag 2–3 f behind each transfer; hands swing 1–1.5 cm.
- breath_weight 1.0.

### idle_bored — 15.0 s / 450 f, loop
Slouched, heavy, time-killing.
- Baseline: Spine01 pitch +3°, Spine02 +4°, head pitch +6° with 3° tilt,
  clavicles forward 2°, hip sway slower (0.05 Hz, ±1 cm).
- f150–f190: toe-tap ×3 on R foot (ToeBase 15°, foot heel-pivot 3°,
  intervals 11/13 f — uneven), hip bounces 0.3 cm per tap.
- f280–f330: big sigh — sync slot for `breath_sigh` (chest up 2°, hold,
  collapse w/ shoulders dropping 3°, head drops extra 2° on exhale).
- f380–f420: slow head roll L→R (roll -4°→+4°→0, lazy arc, eyes lead —
  face agent note).
- breath_weight 1.0 (breath_calm between events).

### idle_confident — 10.0 s / 300 f, loop
Open chest, still, minimal apology in the silhouette.
- Baseline: Spine02 pitch -2° (extension), clavicles back 3°, chin up
  (head pitch -3°), stance sway amplitude 60% of neutral, slower (0.05 Hz).
- f80–f140: deliberate slow scan L→R (head yaw +12°→-12°, 60 f, ease both
  ends, torso recruits 20% of the yaw).
- f200–f230: single clean weight shift R (hip 2.5 cm, full counter chain).
- f260–f275: R hand micro-flex (fingers extend 5° then re-relax — energy).
- breath_weight 1.0 (breath_calm, slightly deeper via director param if avail).

### idle_tired — 13.0 s / 390 f, loop
Weight sags, everything droops, recoveries are slow.
- Baseline: shoulders (clavicles) forward+down 4°, Spine01 +2.5°, head +4°,
  hip parked 1.5 cm L (uneven stance), arms hang 1° more adducted.
- f100–f160: head droop-recover — pitch +6° over 30 f (fighting sleep),
  sharp 8 f recover to baseline w/ 1.5° overshoot, small spine ripple.
- f230–f270: weight sag further R→L, sloppy: hip overshoots 0.8 cm, corrects.
- f330–f360: aborted arm lift — R upperarm raises 8°, elbow 10°, then gives
  up and drops back w/ 2 f settle bounce.
- breath_weight 1.0 but paired with `breath_deep` (slower cycle sells fatigue).

### idle_alert — 9.0 s / 270 f, loop
Coiled, listening, ready to move. Fortnite-lobby energy floor.
- Baseline: sway amplitude 40% of neutral, faster micro-noise (0.15 Hz
  component), weight 1.5 cm toward balls of feet (hip -Y 1.5 cm), fingers 5%
  tenser than relax baseline, head level.
- f60–f90: sharp glance L — head yaw +25° in 5 f (neck leads, head 1 f lag),
  hold 18 f with 1° drift, return 7 f with 2° overshoot.
- f150–f185: glance R, -20°, hold 22 f (different length — asymmetry).
- f220–f240: weight micro-drop — both knees flex 3°, hip -1.2 cm, recover.
- breath_weight 0.8 (breath_calm at slightly faster rate if param exists).

### idle_lean_casual — 12.0 s / 360 f, loop
All weight on the left leg the entire loop; right leg is decoration.
- Baseline: hip 3 cm L and parked, pelvis roll 4° (R hip dropped), R knee
  lax 8°, R foot rolled to outer edge (foot roll 4°), spine counter 2.5°,
  head counter to level, R shoulder 1° lower than L (asymmetry).
- f120–f140: free-foot fidget — R heel lifts 2 cm (foot pitch 12°), drops.
- f210–f235: hip re-settle bounce — sink 0.8 cm and back w/ soft ease.
- f290–f320: head tilt 3° w/ 4° yaw L (something caught the eye), return.
- breath_weight 1.0.

### idle_fidget — 11.0 s / 330 f, loop
Restless: hands and feet can't stay still, torso mostly quiet.
- Baseline: neutral_stand sway ×1.1, slightly faster.
- f40–f90: thumb-rub — R Thumb2/3 rub across Index2 (thumb ±10° opposition
  cycle ×3, index yields 4°), wrist rotates 3° with it.
- f140–f200: heel-toe rock — weight rocks heel (foot pitch -4°, hip +1.2 cm
  -Y... aft) then toe (foot +6°, hip fwd), ×2 uneven intervals, arms drag.
- f240–f300: cuff-glance — L forearm lifts 15°, pronates 20°, head pitches
  +8° w/ -6° yaw to look at wrist, 12 f hold, drop everything w/ 2 f lag chain.
- breath_weight 1.0.

## 4. BREATHING — 4 layer clips (additive over everything)

Bones owned by this layer: Spine02 (pitch), L/R Clavicle (lift/rot),
L/R RibsTwist (chest expansion — pending scale-channel answer from tech),
Head (tiny counter so gaze doesn't bob). Nothing else.
L clavicle leads R by 1 f, +10% amplitude (asymmetry rule).

### breath_calm — 4.0 s / 120 f, loop (~15 bpm)
- Inhale 54 f (45%), exhale 66 f (55%) — exhale always longer.
- Peak: Spine02 pitch -0.7° (extension), clavicles +1.2° lift, RibsTwist
  scale +1.5% (or +0.4 cm translate fallback), head counter +0.4° pitch.
- Curve: ease-in-out both directions, exhale tail flattens (plateau ~8 f).

### breath_deep — 6.0 s / 180 f, loop (~10 bpm)
- Inhale 80 f, hold 8 f at top, exhale 92 f.
- Peak: Spine02 -1.5°, Spine01 -0.5°, clavicles +2.5°, ribs +2.5%,
  head counter +0.8°. Slight shoulder-blade squeeze feel: clavicles also
  rotate back 1°.

### breath_winded — 2.0 s / 60 f, loop (~30 bpm)
- Baseline INSIDE the clip: Spine01+02 slump +6° forward, clavicles forward
  3° (so runtime can blend the whole exhausted posture in/out as one).
- Cycle: Spine02 -2.5° from slumped base, clavicle heave 4°, hip bob 0.8 cm
  vertical, head pitch swings 1.5°. Sharp inhale (25 f), collapsing exhale
  (35 f). Mouth/nostril work = face agent dependency, noted.

### breath_sigh — one-shot, 3.5 s / 105 f
- f0–f25 quick inhale: chest up 2° (Spine02), clavicles +2°, head lifts 1°.
- f25–f40 hold (suspension — no movement except 0.2° drift).
- f40–f70 collapse: everything drops w/ overshoot 1° PAST neutral, clavicles
  -1.5° below rest, head drops +2°.
- f70–f105 recover to exact neutral (tail for crossfade). Slots into
  idle_bored f280 or plays standalone.

## 5. HEAD — 6 clips (one-shots with return tails)

All use the 20/30/50 neck distribution and neck-leads-head-lags (1–2 f) rule.
Eye darts that should precede these turns are face-agent territory — noted
as a layering dependency, my clips assume eyes lead by 2–4 f.

### head_nod_yes — 1.6 s / 48 f, one-shot
- f0–f6 anticipation: pitch -3° (up), Spine02 recruits 0.5°.
- f6–f14 nod down: +14° total, ease-out sharp (accent).
- f14–f20 rebound to -2° (overshoot past neutral).
- f20–f32 second nod: +8° (decayed repeat — nods come in pairs).
- f32–f48 settle to neutral w/ 1° overshoot. Spine02 sympathetic +1° total.

### head_shake_no — 1.8 s / 54 f, one-shot
- f0–f5 micro-anticipation: yaw -2° (opposite).
- f5–f14 yaw +16° L; f14–f26 yaw -14° R; f26–f36 +7° L; f36–f44 -3° R
  (decaying oscillation, period stretches 10→12 f as it dies).
- Neck leads, head lags 2 f (drag whip). Chin drops 1° during shakes.
- f44–f54 settle to neutral.

### head_tilt_curious — 2.5 s / 75 f, one-shot
- f0–f18 tilt: roll 12° R w/ 1.5° yaw R and 1° pitch down (ear leads toward
  shoulder, arc not straight), R clavicle rises 1° sympathetically.
- f18–f55 hold w/ micro drift (roll ±0.5°); f38 tiny extra 1.5° settle-in.
- f55–f75 return w/ 2° roll overshoot L, then neutral.

### head_glance_left — 2.0 s / 60 f, one-shot
- f0–f5 fast out: yaw +35° (eyes led 3 f earlier — face dep), ease-out hard.
- f5–f40 hold w/ 1° slow drift further L (interest), 0.5° pitch scan.
- f40–f52 return, 3° overshoot R, f52–f60 settle. Spine02 recruits 2° yaw.

### head_glance_right — 2.0 s / 60 f, one-shot
- Mirror of glance_left ×0.9 amplitude (-32°), hold 5 f SHORTER, return 1 f
  faster — deliberately not a mirror clone (asymmetry rule).

### head_double_take — 2.8 s / 84 f, one-shot
- f0–f12 casual glance L: yaw +20°, relaxed ease.
- f12–f24 dismiss: return toward neutral, reaches +5°...
- f24–f28 SNAP back: yaw +40° in 4 f, 4° overshoot, Spine02 recruits 3° yaw
  + 1° pitch (whole upper body startles), clavicles jump 1°.
- f28–f56 hold locked (0.3° tremor first 6 f), lean-in 1 cm (hip -Y).
- f56–f84 slow disengage return, neutral tail.
