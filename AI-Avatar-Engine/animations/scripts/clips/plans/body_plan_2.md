# Body Animation Plan — Part 2 of 2 (gestures, full-body/locomotion)

Conventions, rig facts, bone-name shorthand: see `body_plan.md` §1–2.
All frames at 30 fps. Arms start from the A-pose (~30° below horizontal).

## 6. GESTURES — 18 one-shots, return-to-neutral tails for crossfade-out

Shared gesture rules: 3–8 f anticipation opposite the action; arcs not
straight lines (hands travel through slight curves); finger cascade 1 f per
finger when opening/closing; every hold has ≤0.5° micro-drift (alive, not
frozen); tail = 8–12 f ease into exact neutral. R-handed by default.

### gesture_wave_small — 2.5 s / 75 f
- f0–f5 antic: R clavicle dips 1°. f5–f18 raise: clavicle +5°, upperarm
  abduct+flex to hand-at-shoulder-height, elbow flexes to 70°, fingers open
  cascade. f18–f48: 3 waves — wrist ±20° w/ forearm ±8°, decaying 20/18/14°,
  finger drag 2 f behind wrist. f48–f66 lower along an arc (elbow leads
  down, hand lags 3 f), f66–f75 tail. Head tilt 2° + Spine 1° lean R
  during waves. breath_weight 1.0.

### gesture_wave_big — 3.2 s / 96 f
- f0–f6 antic dip. f6–f22 raise overhead: clavicle +8°, upperarm to 120°
  flex, elbow 40°, torso counter-leans 3° L, hip shifts 1.5 cm L (balance).
- f22–f70: 4 whole-forearm waves ±25° (elbow pivots, wrist +10° drag,
  fingers spread), amplitude decays 25/24/20/15°, period uneven 11/12/11/13 f.
- f70–f96 arc down w/ shoulder-elbow-wrist-finger lag chain (2 f each), tail.

### gesture_point_forward — 2.2 s / 66 f
- f0–f6 antic: hand pulls back 4 cm toward hip, elbow bends.
- f6–f16 extend: arm to horizontal forward (-Y), index straight, others
  curl 70° (cascade), thumb rests on mid. Spine02 recruits 2° forward, head
  aligns to point line (yaw toward target 3°).
- f16–f40 hold w/ 0.3° tremor + 1 cm slow push further (emphasis).
- f40–f58 retract w/ elbow leading, f58–f66 tail.

### gesture_thumbs_up — 2.0 s / 60 f
- f0–f5 antic. f5–f15 raise: elbow-led, forearm to 45° up, hand at chest
  height, fist forms (cascade 4 f) w/ thumb extending LAST (readability).
- f15–f20 emphasis bounce: hand +4° pitch pop w/ 1° overshoot.
- f20–f38 hold, micro-drift. f38–f52 drop w/ fingers relaxing mid-fall,
  f52–f60 tail. Head nods 3° once at the pop (sympathetic).

### gesture_shrug — 2.4 s / 72 f
- f0–f6 antic: clavicles dip -1.5°.
- f6–f16 up: both clavicles +9° (L leads 1 f, +10%), upperarms rotate out,
  elbows flex 60°, forearms supinate (palms up), fingers spread half, head
  tilts 4° R, pitch +2°; Spine02 +1.5° (shoulders swallow the neck).
- f16–f40 hold w/ palms micro-rotate (searching), head micro-shake 1°.
- f40–f54 drop: clavicles fall w/ -1.5° overshoot below rest, arms swing
  down w/ 2 f lag, palms pronate back. f54–f72 tail. Brows = face agent.

### gesture_clap — 3.0 s / 90 f
- f0–f8 raise both hands to sternum height, 30 cm apart, elbows 55°.
- f8–f56: 5 claps, intervals accelerate then relax (12/10/9/10/12 f).
  Per clap: hands arc together, 1 f contact hold (impact), 2° torso bounce
  pitch + clavicle jolt 1°, fingers of striking (R) hand splay 3° on impact.
  L hand is the anvil (moves 40%), R the hammer (60%) — asymmetry.
- f56–f78 hands separate, drop w/ lag chain. f78–f90 tail. breath 0.5.

### gesture_beckon — 2.2 s / 66 f
- f0–f14 raise R arm half-out (upperarm 45°, elbow 80°), palm up, head
  tilts 3° invite, weight shifts 1 cm back (drawing-in energy).
- f14–f44: 3 finger-curl waves — all four fingers curl 60°→10° in a 3 f
  cascade (index first), wrist adds ±8°, period 10/10/12 f.
- f44–f58 arm lowers, f58–f66 tail.

### gesture_stop_palm — 1.8 s / 54 f
- f0–f4 antic: hand pulls back 3 cm, shoulder loads.
- f4–f10 strike out: arm extends forward, wrist extends 30° (palm faces
  target), fingers spread full cascade, clavicle +2°; Spine02 braces -1°
  (lean back 1°, authority). 1° overshoot on wrist.
- f10–f34 hold RIGID except 0.2° tremor (tension, not noise).
- f34–f48 relax retract (wrist softens first, then elbow), f48–f54 tail.

### gesture_facepalm — 3.0 s / 90 f
- f0–f8 antic: head starts pitching down 4° (despair leads).
- f8–f22 R hand rises to forehead (elbow 110°, palm cups brow, fingers
  slightly spread; stop 2 cm proud of the head mesh — no interpenetration),
  head MEETS it: pitch +10°, shoulders slump 3°, Spine01 +2°.
- f22–f60 hold: 2 slow micro head-shakes (yaw ±1.5°) inside the hand.
- f60–f78 hand slides down-off (wrist flexes, head stays down till f70,
  then lifts w/ 1° overshoot), f78–f90 tail. breath duck 0.3.

### gesture_thinking_chin — 3.5 s / 105 f
- f0–f20 R hand to chin: elbow 120°, thumb under chin, index curled along
  jaw (stop 1.5 cm proud of mesh), L arm crosses to support R elbow
  (forearm horizontal — classic pose), head tilts 5° w/ yaw 3° L, eyes up
  (face dep), weight back 1 cm.
- f20–f85 hold: micro nod ×2 (f45, f70 — 2° each, "hm"), index taps jaw
  once f60 (finger curl 8°).
- f85–f105 both arms unwind (L first), head levels, tail. breath 1.0.

### gesture_arms_crossed — 4.0 s / 120 f
- f0–f28 enter: R arm crosses first (hand tucks to L ribs), L follows over
  it (hand grips R bicep area, stop 2 cm proud), clavicles forward 2°,
  Spine02 +1° — closed silhouette. Staggered, not simultaneous.
- f28–f95 hold: L index taps bicep ×2 (f55, f76), one weight shift 1.5 cm
  (f65, full counter chain from plan §2).
- RISK note: breathing layer chest expansion can cause forearm/chest
  interpenetration — recommend breath_weight 0.4 during hold, and I'll
  verify clearance against renders in Phase B.
- f95–f120 unwind (L releases first, mirrored lag), tail.

### gesture_hands_on_hips — 3.5 s / 105 f
- f0–f22 both hands to iliac crests (thumbs back, fingers forward, elbows
  flare 40° out; L lands 2 f after R), chest opens: Spine02 -2°, clavicles
  back 2°, chin +2°.
- f22–f85 hold: one weight shift (f50), head scan 8° (f65–80).
- f85–f105 release (hands slide off, arms fall w/ lag chain), tail.

### gesture_open_palms_explain — 2.6 s / 78 f
- f0–f6 antic: hands draw in 3 cm. f6–f20 out: both forearms extend
  forward-out 35°, supinate to palms-up 80°, hands end 40 cm apart, fingers
  open cascade, elbows stay soft 40°; Spine02 +1° toward listener.
- f20–f44: double emphasis beat — hands dip 4 cm and rise ×2 (offer, offer),
  L hand 90% amplitude of R, 1 f late.
- f44–f66 retract w/ pronation mid-path, f66–f78 tail. breath 1.0.

### gesture_count_123 — 3.6 s / 108 f
- f0–f16 raise R hand beside shoulder, palm out, all fingers curled.
- f16–f24 "one": index extends w/ wrist flick 5° + hand push 2 cm.
- f46–f54 "two": middle joins (same flick, slightly bigger — building).
- f76–f84 "three": ring joins, plus 2° head nod (emphasis compounds).
- Gaps hold w/ micro-drift; spacing 22 f (not exactly even: 22/23/22).
- f84–f96 hold all three, f96–f108 drop + tail.

### gesture_fist_pump — 2.0 s / 60 f
- f0–f10 antic: R arm rises up-forward 50°, hand open, chest -2° extension.
- f10–f16 PULL: elbow yanks down-back (upperarm to -20°, elbow flexes 90°),
  fist snaps closed (1 f per finger), torso crunches +5°, head dips +3°,
  hip drops 1 cm — whole body hits the accent. 3° overshoot everything.
- f16–f24 hold the clench (0.4° tremor — effort).
- f24–f46 release: everything unwinds w/ 2 f lag chain, fingers relax last.
- f46–f60 tail. breath duck 0.2 during pull, restore over 15 f.

### gesture_head_scratch — 3.2 s / 96 f
- f0–f18 R hand rises behind ear (upperarm 85° abduct, elbow 130°, stop
  2 cm proud of head), head tilts forward +5° w/ yaw 3° L (away from hand),
  sheepish energy: L shoulder drops 1°.
- f18–f56: 3 scratch strokes — fingers curl/uncurl 15° w/ wrist ±8°,
  head bobs 1° per stroke, uneven periods 12/11/14 f.
- f56–f80 arm drops along arc w/ lag chain, head levels w/ small shake.
- f80–f96 tail. breath 1.0.

### gesture_look_watch — 2.8 s / 84 f
- f0–f16 L forearm raises across body (elbow 90°, forearm pronates 60° to
  face wrist up), R hand stays down; head pitches +12° w/ yaw -8° (down-left
  to the wrist), Spine02 +2°.
- f16–f52 read hold: micro head scan ±1° (reading), L wrist adjusts 4°
  once (f34 — catching light).
- f52–f72 release: arm drops, head returns w/ 1.5° overshoot, f72–f84 tail.

### gesture_salute — 2.2 s / 66 f
- f0–f4 antic: posture snaps first — Spine02 -2°, chin level, heels
  imply-together (feet adduct 2°).
- f4–f12 rise: R hand snaps to brow (fingers flat/together, palm down 15°),
  crisp ease-out, 2° overshoot at contact point (2 cm proud of brow).
- f12–f44 hold rigid (0.2° tremor only), chest stays lifted.
- f44–f52 crisp drop (faster than rise — military), 3 f settle bounce at
  the bottom, f52–f66 tail relaxing posture back to neutral.

## 7. FULL-BODY / LOCOMOTION — 18 clips

Locomotion = in-place loops: ZERO translation on CC_Base_BoneRoot; the legs
"treadmill" under a stationary hip (hip keeps its bob/sway but no world
advance). Foot phases per cycle: contact (heel strike, toe up 12–18°) →
down (weight accept, hip lowest) → passing (hip highest, free foot clears) →
up (heel off, toe-off push, ToeBase bends 20–25°) → contact opposite.
breath_weight: walk 0.3, run/jog/jump 0.0, crouch/sit idles 1.0.

### walk_fwd_loop — 32 f cycle (1.07 s)
- Beats (L side; R = +16 f): f0 L heel contact (toe up 15°) / f4 down
  (hip lowest, -2.2 cm) / f8 passing (hip +2.2 cm, R foot clears w/ knee
  40°) / f12 up (L heel off) / f16 R contact. Two hip bobs per cycle.
- Pelvis: yaw ±4° (leads w/ swing leg), roll ±3° (drops on swing side),
  lateral sway ±1.8 cm over stance foot.
- Spine01+02 counter-yaw ±4° (2 f behind pelvis), clavicles counter 1.5°.
- Arms: shoulder swing ±28° opposite legs, elbow 15°±10° (bends on
  back-swing), wrist drag 2 f, fingers relax baseline. L/R swing differs 8%.
- Head: stable, counter-bob keeps eyeline (net ±0.5°), 1° sway absorb.

### walk_back_loop — 36 f cycle (1.2 s)
- Toe-first contacts (toe strikes, then heel lowers), stride 75% of fwd,
  hip bob ±1.5 cm, torso 2° forward lean (caution), arm swing 60%,
  pelvis yaw ±2.5°. Head does one small over-shoulder check baked OUT —
  keep loop clean; checks live in head_glance clips layered by runtime.

### jog_fwd_loop — 24 f cycle (0.8 s)
- Flight 2 f after each toe-off. Hip bob ±3.5 cm, lean 5°, arm swing ±35°
  w/ elbows 75°, pelvis yaw ±5°, heel-to-mid contacts.

### run_fwd_loop — 20 f cycle (0.67 s)
- Beats: f0 L contact (mid-foot) / f3 down (-5 cm hip... hip lowest) / f7
  toe-off → flight f8–f10 / f10 R contact / f17–f20 flight. Hip bob ±5 cm.
- Torso lean 8°, pelvis yaw ±6°, roll ±4°, spine counter w/ 1 f lag.
- Arms: shoulder ±45°, elbows locked ~90°, hands loose-fist, clavicles ±3°.
- Head: 1.5° bob absorb, gaze locked forward. ToeBase push-off 25°.

### strafe_left_loop — 28 f cycle
- Shuffle gait (no crossover): L foot reaches 25 cm L, R pushes-drags to
  meet, torso faces forward (-Y) throughout, pelvis roll ±4° into travel,
  hip sway leads 2 cm L of center, arms subtle counter-sway ±10°,
  head level, 2° lean into direction.

### strafe_right_loop — 28 f cycle
- Mirror of strafe_left ×0.95 amplitude, push phase 1 f longer (asymmetry
  so paired strafes don't read as clones).

### turn_left_90 — one-shot 20 f + 8 f settle
- f0–f4 head leads: yaw +30° (eyes first — face dep), shoulders +10°.
- f4–f14 body follows: weight to L foot, R foot steps-pivots, hips rotate
  +90° yaw (carried on CC_Base_Hip per current assumption — root-yaw
  question flagged to main), spine unwinds top-down.
- f14–f20 R foot plants, weight recenters; f20–f28 settle w/ 2° overshoot.

### turn_right_90 — one-shot 20 f + 8 f settle — mirror ×0.95, step 1 f later.

### crouch_idle_loop — 8.0 s / 240 f
- Pose: hip -35 cm, thighs ~100° flex, calves ~115°, torso 15° forward,
  arms hang forward of knees (upperarm +20°), head up -10° (looking ahead),
  heels down, weight on mid-foot.
- Balance wobble: ±1.5 cm hip drift (bigger than standing — harder pose).
- Micro-events: f90 R heel lifts/re-plants (balance catch, 8 f); f170 head
  scan L 15° (20 f); f215 finger re-grip curl. breath 1.0 (reads in
  shoulders).

### crouch_walk_loop — 36 f cycle
- Stays low (hip -30 cm ±1.5 cm bob only — no popping up), short 40 cm
  strides, high care: swing foot lifts 8 cm clear, toe-first contacts,
  torso 18° fwd, arms out 10° for balance w/ ±15° counter-swing,
  pelvis roll ±5° (deep weight transfer each step).

### jump_in_place — one-shot 45 f
- f0–f10 antic crouch: hip -15 cm, torso +15°, arms sweep back 30°, heels
  stay down till f8.
- f10–f14 launch: full leg extension, hip rises +40 cm above rest (vertical
  translation on CC_Base_Hip — flagged), arms throw up-forward to 100°,
  toes last contact (ToeBase 25° push).
- f14–f26 air: legs tuck slightly (knees 20°), arms float at 70°, torso
  vertical, hip apex f20.
- f26–f32 land: absorb — hip -12 cm below rest, knees 50°, torso +12°,
  arms swing forward 15° (catch), 1 f impact hold.
- f32–f45 settle: rise to neutral w/ 2° overshoot chain (hips→spine→head
  1 f lags), arms fall w/ drag. breath 0.0, restore after.

### sit_down — one-shot 50 f (chair seat assumed at 45 cm, behind character)
- f0–f8 check: head turns -35° over R shoulder (glance at seat), R hand
  reaches back-down 20°.
- f8–f36 descent: hips travel back+down (arc, not elevator: -Y 25 cm,
  -47 cm... down to 45 cm seat height), torso counter-leans forward 20°
  (nose over toes — balance), knees flex to 90°, arms: hands brace toward
  thighs, landing softened 4 f (contact f32, weight fully settles f36).
- f36–f50 settle into sit_idle pose: torso stacks upright, hands to thighs,
  1° overshoot. Tail matches sit_idle_loop f0 exactly (chaining contract).

### sit_idle_loop — 10.0 s / 300 f (chains from sit_down)
- Pose: thighs 90°, calves down 90°... shins vertical, feet flat, torso
  upright w/ 3° relaxed slump, hands resting on thighs, elbows soft.
- Micro-events: f80 weight shift L 2 cm (seated version — pelvis roll 2°,
  shoulder counter); f180 hand adjust — R hand lifts 3 cm, re-lands on
  thigh 12 f; f240 head drift yaw +8° and back (30 f).
- Breathing reads clearly in shoulders+chest: breath 1.0. Sway minimal
  (±0.4 cm) — chair carries the weight.

### stand_up — one-shot 40 f (chains from sit_idle)
- f0–f8 load: torso pitches forward 25° (nose over toes), feet pull back
  5 cm... shins angle back, hands press thighs (elbows extend, shoulders
  +10° load).
- f8–f24 rise: hips up+forward arc to standing, legs extend (knee 90°→0°),
  torso un-pitches with 2 f lag behind hips, hands leave thighs at f18,
  arms swing to neutral w/ drag.
- f24–f32 overshoot: torso -2° past vertical (momentum), hip +0.8 cm high.
- f32–f40 settle to exact standing neutral (tail). breath duck 0.3.

### dance_groove_loop — 128 f (4.27 s, 8 beats @ ~112 bpm, 16 f/beat)
- Foundation: hip bounce on every beat (-2.5 cm dip on the beat, rebound
  off-beat — bounce is IN the knees: 8° flex pulse), weight trades L/R
  every 2 beats (hip sway ±3 cm).
- Shoulders: alternating pop 4° (R on beats 1,3,5,7; L on 2,4,6,8 w/ 10%
  more — asymmetry), clavicle +2° w/ each pop.
- Head: nod 8° on beats 2 and 4 (backbeat, not downbeat — groove), loose
  1.5° roll drift throughout.
- Arms: loose 20° swing at sides, elbows pump 10° with shoulder pops,
  hands relaxed-open, 2 f drag everywhere. Pelvis yaw ±3° syncopated
  (hits the "&" after beats 4 and 8 — keeps the loop from metronoming).

### celebrate_victory — one-shot 60 f
- f0–f8 antic crouch: hip -12 cm, arms load back 25°, torso +10°.
- f8–f14 explode: small hop (hip +20 cm), both arms throw overhead into a
  V (upperarm 130° flex, 30° abduct, L 1 f late), fists closed, chest -8°
  extension, head -10° (looking up), 4° overshoot on everything.
- f14–f34: 2 fist shakes at apex (elbow 15° pump, 9/11 f periods), torso
  micro-bounce w/ each.
- f34–f42 land+release: drop to rest heights, arms descend w/ lag chain.
- f42–f60: pride exit — hands land on hips (hands_on_hips pose ×0.7),
  chest stays +1°... lifted, hold 10 f, then tail to neutral. breath 0.0
  until f42, then restore.

### stretch_full — one-shot 90 f (3.0 s)
- f0–f20 rise: both arms sweep forward-up to 150° overhead, fingers
  interlace-imply (palms up), spine extends -6°, head follows arms -8°,
  heels rise 2 cm at f18 (toes take weight).
- f20–f34 lean L 8° (Spine01+02 lateral), hip counters 2 cm R; f34–f48
  lean R 8° ×0.9 (asymmetry), hip counters L.
- f48–f60 apex hold w/ 0.5° tremble (effort), heels still up.
- f60–f78 release: heels drop f62, everything collapses 60% in 6 f (big
  exhale — breath_sigh sync slot), arms swing down loose.
- f78–f90: 2 loose arm shake-out swings (±8°, pendulum decay), tail.
  breath duck 0.2 f0–f60, sigh at release.

### bow_greeting — one-shot 55 f
- f0–f6 antic: chest lifts -2°, R arm begins sweep across waist (formal),
  L arm stays at side (asymmetric bow — more character than symmetric).
- f6–f22 bow: Spine01 +15°, Spine02 +18°, head +10° (total ~43° fold),
  hips counter -8 cm... translate back 8 cm (balance), R forearm crosses
  waist, L arm hangs plumb (gravity — it stays vertical as torso pitches).
- f22–f37 hold at depth, stillness (respect) except 0.3° drift.
- f37–f51 rise SLOWER than descent (14 f vs 16... rise takes the full 14 f
  w/ dignity, head unstacks LAST — spine leads, head lags 3 f).
- f51–f55 settle w/ 1° overshoot; tail to neutral. breath duck 0.2,
  restore on rise.

## 8. Phase B self-review checklist (what I'll verify on renders)

- Silhouette reads at 100% and 25% playback speed; no pose-to-pose popping.
- Loop seams invisible (scrub f_end-5..f_start+5 across the wrap).
- No interpenetration: hands vs head/torso on contact gestures (2 cm
  clearance rule), forearms vs chest in arms_crossed WITH breathing at 1.0.
- Feet: no skating in idles (contact feet stay planted through weight
  shifts); locomotion contact phases have zero vertical foot jitter.
- Asymmetry present in every bilateral clip (diff L vs R curves).
- Head eyeline stability in idles/walk (net world-space bob within ±1°).
- Every one-shot's last frame == shared neutral within 0.1° / 0.05 cm.
