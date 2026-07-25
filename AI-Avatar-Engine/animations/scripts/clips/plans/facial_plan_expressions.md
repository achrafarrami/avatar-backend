# Facial Animation Plan — Part 2: Expressions (16) + Listening Set (6)

Owner: facial agent. Conventions, macros (STD_BLINK / GAZE / JAW), asymmetry,
decay and hold-life laws: see `facial_plan.md` Part 1. 30 fps. Every
expression is a key COMBINATION — no single-key poses anywhere below.
"Leader" = the side that moves first/strongest (asymmetry law).

Files: expressions → `scripts/clips/expressions.py`,
listening → `scripts/clips/listening.py`.

---

## 1. EXPRESSIONS — 16 one-shot clips (neutral in → neutral out unless noted)

### 1.1 expr_smile_soft — 75 f (2.5 s). Leader: L
Duchenne-lite. Onset f0–f6 fast:
- Mouth_Smile_L 0.45 @f6 / R 0.42 @f7; Mouth_Dimple 0.12/0.10;
  Mouth_Up 0.05.
- Cheeks LAG corners 2 f: Cheek_Raise_L 0.25 @f8 / R 0.22 @f9.
- Eye_Squint 0.14/0.12 @f9 (lower-lid raise = the "real smile" tell);
  Brow_Drop 0.04/0.03 (brows settle, never rise in a soft smile).
Apex f9–f48: amplitude breathes ±0.03 (period ~40 f); one corner
reinforcement +0.05 L-only @f30; STD_BLINK(f24, 1.0).
Decay f48–f75: R corner first (f48), L @f51; cheeks linger 6 f after
corners; squint releases last. Zero by f75.

### 1.2 expr_smile_big — 84 f (2.8 s). Leader: R
Onset f0–f7:
- Mouth_Smile 0.75/0.70 + Mouth_Smile_Sharp 0.15/0.12; Mouth_Dimple 0.20;
  Mouth_Up_Upper 0.15/0.13 (upper-teeth reveal); Mouth_Stretch 0.08.
- JAW 6° / Jaw_Open 0.18 (parted lips, teeth showing — bone MOVES the teeth).
- Cheek_Raise 0.50/0.46 (lag 2 f); Eye_Squint 0.35/0.32; Nose_Crease 0.12;
  Brow_Drop 0.06.
Apex f8–f54: squint flicker ±0.03; cheek pulse +0.04 @f34;
STD_BLINK(f30, 0.9). Decay f54–f84: jaw closes first (f54–f60), corners
f58, cheeks/squint trail to f78.

### 1.3 expr_laugh — 105 f (3.5 s). Leader: L
Build f0–f8 = smile_big onset compressed. Laugh pulses f10–f42:
- JAW oscillates 8°→3°→8°, period 7–8 f, x4 pulses; Jaw_Open key base 0.25
  + 0.12 riding in sync (each pulse peak 1 f after the bone — skin lags bone).
- Mouth_Smile 0.80/0.75; Mouth_Stretch 0.15 pulses in antiphase with jaw;
  Cheek_Raise 0.55/0.50; Eye_Squint 0.45→0.60 at pulse peaks (eyes nearly
  shut); Eye_Blink 0.25 partial riding pulse peaks; Nose_Crease 0.20;
  Brow_Raise_Inner 0.15/0.13 (laugh brows lift); Nose_Nostril_Dilate 0.15.
Wind-down f42–f75: pulses shrink 60% then die; residual smile 0.35;
one aftershock chuckle pulse (JAW 3°) @f66; STD_BLINK(f70, 0.9).
Settle f75–f105: warm soft-smile 0.12 plateau f88, then fade to 0 @f105.
QA note: toon teeth are HUGE — verify no teeth-through-lip at pulse peaks.

### 1.4 expr_surprise — 54 f (1.8 s). Leader: L
FASTEST onset f0–f3/f4:
- Brow_Raise_Inner 0.70/0.66 + Brow_Raise_Outer 0.60/0.55.
- Eye_Wide 0.65/0.60; Eyelash_Upper_Up 0.50; Eye_Pupil_Dilate 0.30.
- JAW 5° / Jaw_Open 0.15 + Mouth_Drop_Lower 0.25 + Mouth_Drop_Upper 0.10.
Hold f5–f28: NO blink (startle suppresses blinking); brow tremor ±0.02;
gaze locked dead ahead, zero drift (frozen attention — deliberate exception
to drift rule, the stillness IS the expression; lids/brows still carry the
tremor so the face isn't dead).
Decay f28–f54: jaw first, brows two-stage; STD_BLINK(f34, 1.0) as the brows
fall = the classic "reset" blink.

### 1.5 expr_confused — 78 f (2.6 s). Leader: R (the raised brow)
Asymmetric brow knot, onset f0–f7 (slow-ish — confusion dawns):
- LEFT down: Brow_Drop_L 0.45 + Brow_Compress_L 0.30 + Eye_Squint_L 0.28.
- RIGHT up: Brow_Raise_Inner_R 0.35 + Brow_Raise_Outer_R 0.40.
- Mouth: Mouth_Press 0.22/0.18; Mouth_L 0.10 (mouth pulls left);
  Mouth_Pucker_Up_L + Mouth_Pucker_Down_L 0.10 (lips purse leftward);
  Nose_Crease_L 0.08.
Searching gaze: GAZE(+7°, +3°) @f10; GAZE(−5°, +5°) @f34; back to center f58.
Hold micro: raised R brow pulses +0.05 @f22 and @f46 ("wait... what?");
STD_BLINK(f44, 0.9). Decay f56–f78; the raised brow releases LAST.

### 1.6 expr_thinking — 96 f (3.2 s). Leader: L
- Gaze up-right (recall): GAZE(+12°, +14°) f0–f4; look-keys ≈ Eye_L/R_Look_Up
  0.23 + Eye_L/R_Look_R 0.20; Eye_Wide 0.08 (lid follow per macro).
- Brows: Brow_Compress 0.26/0.23 + Brow_Drop 0.12 + Brow_Raise_Inner 0.10
  (concentration mix — compress dominates).
- Mouth: Mouth_Press 0.30/0.26; Mouth_Pucker_Up 0.12; Mouth_L 0.12 (twist);
  Cheek_Suck_L 0.10.
- Gaze micro-shifts: (+9°, +10°) @f52; (+13°, +12°) @f70 (scanning memory).
- STD_BLINK(f38, 1.0, slow=True) — thinking blinks are slow.
- JAW micro 1.5° @f60 (jaw shifts in thought, 8 f), teeth stay near-closed.
Decay f78–f96: gaze returns center @f80 with STD_BLINK(f80, 0.9);
mouth releases before brows (thought lingers on the forehead).

### 1.7 expr_frown_sad — 90 f (3.0 s). Leader: R
SLOW onset f0–f14 (sadness creeps, never snaps):
- Brow_Raise_Inner 0.50/0.46 (oblique "grief" brows) + Brow_Compress 0.15.
- Mouth_Frown 0.40/0.36; Mouth_Shrug_Lower 0.28 (chin pout);
  Mouth_Chin_Up 0.15 (chin crumple); Mouth_Down 0.10.
- Heavy lids: Eye_Blink 0.18 partial + Eyelash_Upper_Down 0.18.
- Gaze drops: GAZE(0°, −12°) @f10 + Look_Down keys 0.20.
Hold f14–f60: lip tremble Mouth_Frown ±0.04 (period 5 f, x3 starting f30);
STD_BLINK(f48, 1.0, slow=True) heavy blink.
Decay f60–f90 VERY slow; mouth releases first, oblique brows last
(the brow is the final trace of sadness). Optional Neck_Swallow beat @f40
SKIPPED — corrective-class key, not mine to fire (flagged to main).

### 1.8 expr_angry — 72 f (2.4 s). Leader: L
Onset f0–f5 hard:
- Brow_Drop 0.70/0.65 + Brow_Compress 0.50/0.46.
- Glare combo: Eye_Squint 0.30/0.27 + Eye_Wide 0.12 UNDER it (upper lid up,
  lower lid tense = predator stare; squint alone reads sleepy).
- Nose_Sneer 0.28; Nose_Crease 0.30; Nose_Nostril_Dilate 0.30.
- Mouth_Tighten 0.35/0.30 + Mouth_Press 0.30 + Mouth_Frown 0.20 +
  Mouth_Down_Lower 0.12 (lower-teeth hint); Jaw_Forward key 0.15 (jut).
Hold f6–f50: nostril breathing pulse 0.30→0.22→0.30 (30 f); brow deepens
+0.05 @f28 (second wave); NO blink until f44 (stare suppression), then a
SNAP blink: close 2 f, open 4 f, amp 1.0.
Decay f52–f72: mouth first; Brow_Drop keeps 0.10 residual until f70.

### 1.9 expr_disgust — 66 f (2.2 s). Leader: L (sneer side)
Onset f0–f5:
- Nose_Sneer 0.60/0.54 + Nose_Crease 0.50/0.44 + Nose_Nostril_Raise 0.30.
- Mouth_Up_Upper 0.35/0.30 (asymmetric lip curl); Mouth_Frown 0.22.
- Brow_Drop 0.35/0.31; Eye_Squint 0.42/0.38 (nose pushes lids shut);
  Cheek_Raise 0.25 (recruited by the sneer, NOT a smile cheek).
Hold f6–f38: sneer pulse +0.06 @f22 (the "ugh" second hit);
STD_BLINK(f36, 0.85). Head recoil belongs to the body agent (marker @f4).
Decay f38–f66: lip curl first, nose crease last; L releases after R.

### 1.10 expr_worried — 84 f (2.8 s). Leader: R
Onset f0–f8:
- Worry knit: Brow_Raise_Inner 0.55/0.50 + Brow_Compress 0.30/0.26 +
  Brow_Raise_Outer 0.15 (inner-up + squeeze ≠ sad's clean oblique).
- Eye_Wide 0.30/0.27 (vigilance); Mouth_Stretch 0.25/0.20;
  Mouth_Frown 0.18; Mouth_Press 0.15; Mouth_Roll_In_Lower 0.15 (lip bite).
Scanning gaze: GAZE(−6°, 0°) @f30; GAZE(+6°, 0°) @f52; center @f70.
Double blink @f40: STD_BLINK(f40, 1.0) + STD_BLINK(f52→ actually f52 is a
gaze beat — second blink f54, 0.8) (worried blink rate is HIGH).
Hold micro: knit tightens +0.04 @f46. Decay f64–f84; Eye_Wide drops first,
the inner-brow knit fades last.

### 1.11 expr_wink — 39 f (1.3 s). Leader: L (the winking eye)
- f0–f3: Eye_Blink_L 0→1.0 (Eyelash_Upper_Down_L 1.0); Cheek_Raise_L 0.35
  (winks recruit the cheek or they look like a twitch); Brow_Drop_L 0.12.
- Grin: Mouth_Smile_L 0.42 / R 0.15 (strongly asymmetric) @f4.
- Open eye stays alive: Eye_Squint_R 0.06 sympathetic; NO R blink.
- HOLD closed f3–f18 (a wink is held, a blink is not).
- f18–f24 open (5 f); smile decays f24–f39 through 0.08 residual → 0.
- Optional Eye_Pupil_Dilate 0.15 on the open eye @f4 (charm detail).

### 1.12 expr_skeptical — 72 f (2.4 s). Leader: R (arched brow)
Onset f0–f6:
- R brow arch: Brow_Raise_Outer_R 0.55 + Brow_Raise_Inner_R 0.28 +
  Eye_Wide_R 0.10 (eye opens under the arch).
- L side presses down: Brow_Drop_L 0.35 + Brow_Compress_L 0.20 +
  Eye_Squint_L 0.32.
- Mouth: Mouth_Press 0.28/0.22; Mouth_Smile_Sharp_L 0.14 (dry half-smirk);
  Mouth_L 0.08.
Side-eye: GAZE(−8°, 0°) @f12 hold, return @f50 (looking at them sideways
while the face says "really?").
Hold micro: arch pulses +0.06 @f28; STD_BLINK(f36, 0.9, slow=True).
Decay f54–f72: mouth first, the R arch releases LAST (skepticism lingers).

### 1.13 expr_excited — 66 f (2.2 s). Leader: L
Onset f0–f4 explosive:
- Brow_Raise_Inner 0.50/0.46 + Outer 0.45/0.41; Eye_Wide 0.45/0.40;
  Eye_Pupil_Dilate 0.25; Eyelash_Upper_Up 0.35.
- Mouth_Smile 0.70/0.65 + Smile_Sharp 0.20 + Mouth_Stretch 0.10;
  Cheek_Raise 0.40/0.36; JAW 5° / Jaw_Open 0.15 (grin gape, teeth visible).
Double eyebrow flash: brows re-pulse +0.08 @f18 and @f32 (4 f up, 6 f down).
Hold sparkle: Eye_Wide tremor ±0.03; smile breathes ±0.03.
STD_BLINK(f26, 0.8) fast. Decay f46–f66 through warm 0.10 smile → 0;
brows land before the smile (afterglow on the mouth).

### 1.14 expr_smirk — 60 f (2.0 s). Leader: L (contempt is unilateral)
Onset f0–f6 SLOW spread (smirks creep):
- Mouth_Smile_Sharp_L 0.45 + Mouth_Smile_L 0.15 + Mouth_Dimple_L 0.30.
- R side pinned: Mouth_Press_R 0.12 (the asymmetry IS the emotion).
- Eye_Squint_L 0.18; Brow_Raise_Outer_L 0.22 (knowing brow).
Side gaze: GAZE(−6°, 0°) f8–f40 (toward the smirk side), lazy return.
Hold: corner pulse +0.05 @f30; STD_BLINK(f34, 0.9).
Decay f44–f60: brow first, the corner releases last, 2-stage.

### 1.15 expr_sheepish — 78 f (2.6 s). Leader: R
The suppressed-smile fight, onset f0–f8:
- Smile TRYING: Mouth_Smile 0.35/0.30 + Cheek_Raise 0.22/0.19.
- Suppression FIGHTING it: Mouth_Press 0.30/0.26 + Mouth_Roll_In_Lower 0.18
  (bitten smile — both teams keyed simultaneously, the tension reads).
- Apologetic brows: Brow_Raise_Inner 0.35/0.32.
- Lids soft: Eye_Blink 0.12 partial.
Avert: GAZE(−10°, −12°) @f8 (down-left escape). Peek back: GAZE(0°, 0°)
@f44 with smile pulse +0.08 (caught, smiles wider).
Double blink @f46: STD_BLINK(f46, 1.0) + STD_BLINK(f58, 0.75).
Decay f60–f78; press releases before smile (the smile wins at the end:
0.10 residual @f70 → 0 @f78).

### 1.16 expr_sigh_bored — 102 f (3.4 s). Leader: L
Inhale f0–f20 (slow): Brow_Raise_Inner 0.22/0.19; Nose_Nostril_Dilate 0.25;
lids drift heavy Eye_Blink 0.20 partial; gaze neutral.
Exhale f20–f40: JAW 3° / Jaw_Open 0.08 + Mouth_Drop_Lower 0.15 +
Mouth_Blow 0.12/0.10 (lips loose); brows collapse to Brow_Drop 0.10;
lid droop deepens 0.30; GAZE(−8°, −10°) drift @f36 (down-right, checked out).
Bored hold f40–f84: STD_BLINK(f52, 1.0, slow=True) (close 5, open 10);
Mouth_Press 0.10 @f66; Jaw_L key 0.06 @f66 (idle jaw shift, 10 f);
fixation drift ±1° (eyes wander more when bored).
Recover f84–f102: gaze center @f88, lids stay 0.08 heavy until f96, then
neutral. Chest/shoulder sigh belongs to body agent (marker @f20).

---

## 2. LISTENING SET — 6 loop clips (`scripts/clips/listening.py`)

All loops; interlocutor assumed at gaze (0°, 0°). Frame-0 pose == frame-N
pose exactly (loop-safe). Designed to run WITH face_micro_engaged (part 1
§5.2) — intrinsic micro-events here are the ones that carry MEANING (beats,
reactions); texture comes from the additive layer.
HEAD MOTION: nods/tilts need CC_Base_Head — owned by the body agent. My
clips ship "nod"/"tilt" marker events (frame + type metadata) instead of
keying the bone. If main rules that facial owns micro-nods, Phase B adds
them via head bone at ≤ 2.5°, never via Head_* corrective keys standalone.

### 2.1 listen_neutral — 240 f (8.0 s). Leader: L
Baseline: everything 0 (rest face is fine here — life comes from eyes+micro).
- Gaze on speaker; drift ±0.7° (steps f30, f110, f200); micro-saccades
  (+2.5°, −1°) @f70 and (−2°, +1°) @f150, 2 f each, return within 20 f.
- Blinks: STD_BLINK(f60, 1.0); STD_BLINK(f168, 0.9) — gaps 2.0 s / 3.6 s.
- Brow_Raise_Inner 0.06/0.05 slow swell f90–f140 (a breath of interest).
- Mouth_Press_L 0.05 @f120 (8 f) — single "taking it in" beat.

### 2.2 listen_engaged — 225 f (7.5 s). Leader: R
Attentive baseline (held through loop, ramps in/out over first/last 10 f
from/to the loop pose):
- Brow_Raise_Inner 0.12/0.10 + Outer 0.08/0.07; Eye_Wide 0.10/0.08;
  Mouth_Smile 0.10/0.08 (pleasant, not grinning).
Events:
- Brow flash +0.15 over baseline @f45 (6 f up, 10 f down) = "uh-huh" beat;
  smaller +0.10 @f160. Nod markers @f45, @f160 (body agent).
- Smile swell +0.08 f100–f130; Cheek_Raise 0.08 rides it.
- Blinks: STD_BLINK(f75, 1.0); STD_BLINK(f195, 0.85).
- One saccade (+3°, 0°) @f130, back @f150.

### 2.3 listen_agree — 180 f (6.0 s). Leader: L
listen_engaged baseline PLUS two agreement beats (nod windows f40–f60 and
f120–f140; nod markers for body agent at f42, f122):
- At each nod onset: STD_BLINK(nod_f, 0.9) — people blink when they nod.
- Smile swells to 0.22/0.19 inside each window; Cheek_Raise 0.12.
- Brow flash +0.12 leading each nod by 3 f.
- Closed-mouth "mm-hm" at f48 and f128: Mouth_Press 0.15 + Mouth_Pucker_Up
  0.05 pulse, 8 f (NOT a viseme — lips stay sealed, speech layer untouched).
- Between beats: relax to engaged baseline (never to zero — still agreeing).

### 2.4 listen_thoughtful — 270 f (9.0 s). Leader: L
Baseline: Brow_Compress 0.18/0.15 + Brow_Drop 0.08; Mouth_Press 0.18/0.15.
- Recall break: GAZE(−10°, +12°) f60–f120 (up-left = retrieving), return
  saccade @f120 with STD_BLINK(f122, 1.0) on refixation.
- Evaluate break: GAZE(−6°, −8°) f200–f225 (down = weighing it), return f225.
- Slow blinks: STD_BLINK(f30, 1.0, slow=True); STD_BLINK(f180, 0.9,
  slow=True).
- Mouth purse pulse: Mouth_Pucker_Up_L/R + Mouth_Pucker_Down_L 0.10 @f90
  (12 f); Cheek_Suck_L 0.08 @f210 (10 f).
- Brow_Compress deepens +0.05 during each gaze break (thinking harder).

### 2.5 listen_surprised_react — 195 f (6.5 s). Leader: L
Neutral-listen f0–f70 (drift; STD_BLINK(f40, 1.0)).
REACTION @f70, onset 3 f (this is expr_surprise at listening scale):
- Brow_Raise_Inner 0.45/0.41 + Outer 0.35/0.31; Eye_Wide 0.40/0.36;
  Eye_Pupil_Dilate 0.20; lips part: Mouth_Drop_Lower 0.12 + Jaw_Open 0.06
  key-only (NO bone — mouth barely opens, teeth stay shut).
Hold f74–f110: no blink (startle suppression); brow tremor ±0.02.
Recover f110–f140: STD_BLINK(f114, 1.0) reset blink; brows fall two-stage.
Settle f140–f195: mild residual interest (Brow_Raise_Inner 0.08) easing to
the f0 neutral pose by f195 (loop-safe); STD_BLINK(f172, 0.85).

### 2.6 listen_empathetic — 255 f (8.5 s). Leader: R
Concern baseline: Brow_Raise_Inner 0.30/0.27 + Brow_Compress 0.12;
Mouth_Frown 0.10/0.08 + Mouth_Press 0.10; Eye_Squint 0.08 (soft eyes).
- Gaze dwells on speaker, drift widened to ±1.0° (soft focus).
- Warm slow blinks: STD_BLINK(f66, 1.0, slow=True); STD_BLINK(f180, 0.9,
  slow=True).
- Sorrow swell f100–f150: Brow_Raise_Inner +0.10, Mouth_Frown +0.06,
  head-TILT marker @f90 (body agent).
- Sympathy pout: Mouth_Shrug_Lower 0.08 @f130 (12 f).
- Reassurance turn f210–f250: Mouth_Smile eases in to 0.06/0.05 while the
  frown fades (the "it'll be okay" beat), returning to baseline @f255.

---

## 3. Cross-clip consistency rules

- Blink amplitudes never repeat exactly back-to-back anywhere in the library
  (1.0 → 0.9 → 1.0 ok; 0.9 → 0.9 not).
- Leader side across the 16 expressions: 8 L / 8 R as assigned above — the
  character has no fixed dominant side over a session.
- Any expression followed by another in a runtime queue passes through ≤ 8 f
  of neutral; decays already end at true zero (except noted residuals which
  also reach zero by the final frame).
- Every clip that opens the bite uses the JAW macro (bone + key). Clips
  that only PART LIPS (listen_surprised_react) use keys only — grep test in
  Phase B self-review: no Jaw_Open key > 0.10 without a JawRoot bone key.
- Marker events (nod/tilt/recoil/sigh) ship in clip metadata for the body
  agent; facial never keys CC_Base_Head or Head_*/Neck_* correctives.
