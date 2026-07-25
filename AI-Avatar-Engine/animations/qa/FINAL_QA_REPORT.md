# FINAL QA REPORT — AI-Avatar-Engine Animation Library

- **Reviewer / QA authority:** qa-3 (consolidating qa, qa-2, qa-3 review rounds)
- **Date:** 2026-07-25
- **Scope:** all 103 shipped clips (the full library)
- **Gate:** every applicable rubric dimension >= 9/10 (`qa/rubric.md`). **All 103 clips PASS.**
- **Verdict:** **103/103 SHIP** — library is at the 9/10 gate on all 8 dimensions.
- **Numbers below are generated programmatically** from each `previews/<id>/meta.json` (duration/frames/keyframes/loop/category) and each `qa/scorecards/<id>_scorecard.md` (8-dimension scores → overall = min applicable). Not hand-transcribed.

## Summary

- **Total shipped clips:** 103  (of a 107-clip director spec — 4 transition helpers unbuilt, see Notes c)
- **Total animation runtime:** 441.6 s  (~7.36 min)
- **Total keyframes:** 112,426
- **Loop vs one-shot:** 42 loop / 61 one-shot

**Count per category:**

| Category | Clips |
|----------|-------|
| Idle | 8 |
| Breathing | 4 |
| Eyes | 10 |
| Head | 6 |
| Facial-expression | 16 |
| Listening | 6 |
| Talking | 15 |
| Gesture | 18 |
| Locomotion | 18 |
| Micro-layer | 2 |
| **Total** | **103** |

**Count per owner (animation domain):**

| Owner | Clips |
|-------|-------|
| body | 55 |
| facial | 33 |
| lipsync | 15 |
| **Total** | **103** |

**Per-dimension average score across the library** (averaged over clips where the dimension applies; N/A excluded):

| # | Dimension | Clips scored | Avg |
|---|-----------|--------------|-----|
| 1 | Weight/balance | 52 | 9.00 |
| 2 | Timing | 103 | 9.00 |
| 3 | Naturalness | 103 | 9.00 |
| 4 | Facial | 43 | 9.02 |
| 5 | Hand life | 44 | 9.00 |
| 6 | Eye behavior | 60 | 9.00 |
| 7 | Loop seam | 42 | 9.07 |
| 8 | Technical | 103 | 9.00 |

- **Library-wide mean of all applicable dimension scores:** 9.007 (min observed across every applicable dimension of every clip: 9).

## Per-clip verdicts (grouped by category)

Columns: id | category | duration_s | frames | keyframes | loop | owner | verdict | overall (min applicable dimension).

### Idle (8 clips — 94.0s, 26,018 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| idle_01 | idle | 10.0 | 301 | 3,397 | Y | body | SHIP | 9/10 |
| idle_02 | idle | 12.0 | 361 | 3,262 | Y | body | SHIP | 9/10 |
| idle_confident | idle | 10.0 | 301 | 3,126 | Y | body | SHIP | 9/10 |
| idle_hands_behind_back | idle | 12.0 | 361 | 2,640 | Y | body | SHIP | 9/10 |
| idle_hands_together | idle | 12.0 | 361 | 2,473 | Y | body | SHIP | 9/10 |
| idle_looking_around | idle | 14.0 | 421 | 4,550 | Y | body | SHIP | 9/10 |
| idle_phone | idle | 12.0 | 361 | 3,753 | Y | body | SHIP | 9/10 |
| idle_relaxed | idle | 12.0 | 361 | 2,817 | Y | body | SHIP | 9/10 |

### Breathing (4 clips — 20.1s, 592 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| breathing_deep | breathing | 6.0 | 181 | 176 | Y | body | SHIP | 9/10 |
| breathing_excited | breathing | 2.6 | 79 | 100 | Y | body | SHIP | 9/10 |
| breathing_normal | breathing | 4.5 | 136 | 76 | Y | body | SHIP | 9/10 |
| breathing_tired | breathing | 7.0 | 211 | 240 | Y | body | SHIP | 9/10 |

### Eyes (10 clips — 7.5s, 1,616 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| blink | eyes | 0.4 | 12 | 86 | N | facial | SHIP | 9/10 |
| double_blink | eyes | 0.6 | 19 | 130 | N | facial | SHIP | 9/10 |
| eye_dart | eyes | 1.2 | 37 | 416 | N | facial | SHIP | 9/10 |
| eye_down | eyes | 0.5 | 16 | 140 | N | facial | SHIP | 9/10 |
| eye_left | eyes | 0.5 | 16 | 112 | N | facial | SHIP | 9/10 |
| eye_right | eyes | 0.5 | 16 | 96 | N | facial | SHIP | 9/10 |
| eye_up | eyes | 0.5 | 16 | 160 | N | facial | SHIP | 9/10 |
| focus | eyes | 1.0 | 31 | 164 | N | facial | SHIP | 9/10 |
| lose_focus | eyes | 1.5 | 46 | 218 | N | facial | SHIP | 9/10 |
| slow_blink | eyes | 0.8 | 25 | 94 | N | facial | SHIP | 9/10 |

### Head (6 clips — 13.3s, 1,430 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| head_micro | head | 8.0 | 241 | 548 | Y | body | SHIP | 9/10 |
| nod_big | head | 1.3 | 40 | 302 | N | body | SHIP | 9/10 |
| nod_small | head | 0.8 | 25 | 176 | N | body | SHIP | 9/10 |
| shake_no | head | 1.2 | 37 | 180 | N | body | SHIP | 9/10 |
| tilt_left | head | 1.0 | 31 | 116 | N | body | SHIP | 9/10 |
| tilt_right | head | 1.0 | 31 | 108 | N | body | SHIP | 9/10 |

### Facial-expression (16 clips — 45.5s, 6,799 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| angry | facial | 2.0 | 61 | 451 | N | facial | SHIP | 9/10 |
| big_smile | facial | 2.0 | 61 | 346 | N | facial | SHIP | 9/10 |
| confused | facial | 2.5 | 76 | 525 | N | facial | SHIP | 9/10 |
| curious | facial | 2.0 | 61 | 286 | N | facial | SHIP | 9/10 |
| disappointed | facial | 2.5 | 76 | 436 | N | facial | SHIP | 9/10 |
| embarrassed | facial | 2.5 | 76 | 400 | N | facial | SHIP | 9/10 |
| excited | facial | 2.0 | 61 | 442 | N | facial | SHIP | 9/10 |
| giggle | facial | 1.8 | 55 | 382 | N | facial | SHIP | 9/10 |
| happy | facial | 2.0 | 61 | 196 | N | facial | SHIP | 9/10 |
| laugh | facial | 3.0 | 91 | 681 | N | facial | SHIP | 9/10 |
| neutral_alive | facial | 10.0 | 301 | 1,133 | Y | facial | SHIP | 9/10 |
| proud | facial | 2.5 | 76 | 341 | N | facial | SHIP | 9/10 |
| sad | facial | 3.0 | 91 | 286 | N | facial | SHIP | 9/10 |
| soft_smile | facial | 2.5 | 76 | 92 | N | facial | SHIP | 9/10 |
| surprised | facial | 1.2 | 37 | 236 | N | facial | SHIP | 9/10 |
| thinking | facial | 4.0 | 121 | 566 | Y | facial | SHIP | 9/10 |

### Listening (6 clips — 48.0s, 8,267 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| listening_confused | listening | 8.0 | 241 | 1,263 | Y | facial | SHIP | 9/10 |
| listening_happy | listening | 8.0 | 241 | 1,516 | Y | facial | SHIP | 9/10 |
| listening_interested | listening | 8.0 | 241 | 1,332 | Y | facial | SHIP | 9/10 |
| listening_relaxed | listening | 8.0 | 241 | 1,258 | Y | facial | SHIP | 9/10 |
| listening_serious | listening | 8.0 | 241 | 1,380 | Y | facial | SHIP | 9/10 |
| listening_thinking | listening | 8.0 | 241 | 1,518 | Y | facial | SHIP | 9/10 |

### Talking (15 clips — 108.0s, 29,955 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| talk_excited | talking | 6.0 | 181 | 1,987 | Y | lipsync | SHIP | 9/10 |
| talk_fast | talking | 6.0 | 181 | 1,786 | Y | lipsync | SHIP | 9/10 |
| talk_idle | talking | 6.0 | 181 | 1,610 | Y | lipsync | SHIP | 9/10 |
| talk_serious | talking | 6.0 | 181 | 1,351 | Y | lipsync | SHIP | 9/10 |
| talk_soft | talking | 6.0 | 181 | 1,219 | Y | lipsync | SHIP | 9/10 |
| talk_whisper | talking | 6.0 | 181 | 1,677 | Y | lipsync | SHIP | 9/10 |
| talking_angry | talking | 8.0 | 241 | 1,977 | Y | lipsync | SHIP | 9/10 |
| talking_excited | talking | 8.0 | 241 | 2,928 | Y | lipsync | SHIP | 9/10 |
| talking_fast | talking | 8.0 | 241 | 2,674 | Y | lipsync | SHIP | 9/10 |
| talking_happy | talking | 8.0 | 241 | 2,736 | Y | lipsync | SHIP | 9/10 |
| talking_laughing | talking | 8.0 | 241 | 2,551 | Y | lipsync | SHIP | 9/10 |
| talking_neutral | talking | 8.0 | 241 | 2,124 | Y | lipsync | SHIP | 9/10 |
| talking_serious | talking | 8.0 | 241 | 1,583 | Y | lipsync | SHIP | 9/10 |
| talking_slow | talking | 8.0 | 241 | 1,687 | Y | lipsync | SHIP | 9/10 |
| talking_thinking | talking | 8.0 | 241 | 2,065 | Y | lipsync | SHIP | 9/10 |

### Gesture (18 clips — 37.6s, 14,375 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| arms_crossed | gesture | 2.0 | 61 | 637 | N | body | SHIP | 9/10 |
| celebrate | gesture | 2.5 | 76 | 942 | N | body | SHIP | 9/10 |
| clap | gesture | 2.5 | 76 | 1,248 | N | body | SHIP | 9/10 |
| come_here | gesture | 2.0 | 61 | 1,044 | N | body | SHIP | 9/10 |
| face_palm | gesture | 2.2 | 67 | 792 | N | body | SHIP | 9/10 |
| goodbye | gesture | 2.5 | 76 | 652 | N | body | SHIP | 9/10 |
| hands_together | gesture | 1.5 | 46 | 804 | N | body | SHIP | 9/10 |
| heart_gesture | gesture | 2.5 | 76 | 780 | N | body | SHIP | 9/10 |
| hello | gesture | 2.0 | 61 | 628 | N | body | SHIP | 9/10 |
| point | gesture | 1.8 | 55 | 884 | N | body | SHIP | 9/10 |
| presentation_gesture | gesture | 2.5 | 76 | 860 | N | body | SHIP | 9/10 |
| question_gesture | gesture | 2.0 | 61 | 736 | N | body | SHIP | 9/10 |
| shrug | gesture | 1.8 | 55 | 752 | N | body | SHIP | 9/10 |
| stop_gesture | gesture | 1.5 | 46 | 692 | N | body | SHIP | 9/10 |
| thinking_pose | gesture | 2.2 | 67 | 712 | N | body | SHIP | 9/10 |
| thumbs_down | gesture | 1.8 | 55 | 748 | N | body | SHIP | 9/10 |
| thumbs_up | gesture | 1.8 | 55 | 780 | N | body | SHIP | 9/10 |
| wave | gesture | 2.5 | 76 | 684 | N | body | SHIP | 9/10 |

### Locomotion (18 clips — 43.6s, 20,788 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| adjust_glasses | locomotion | 2.0 | 61 | 846 | N | body | SHIP | 9/10 |
| celebrate_big | locomotion | 3.0 | 91 | 1,223 | N | body | SHIP | 9/10 |
| check_watch | locomotion | 2.2 | 67 | 912 | N | body | SHIP | 9/10 |
| dance_small | locomotion | 4.0 | 121 | 1,594 | Y | body | SHIP | 9/10 |
| hands_in_pockets | locomotion | 2.0 | 61 | 797 | N | body | SHIP | 9/10 |
| lean_left | locomotion | 1.2 | 37 | 1,215 | N | body | SHIP | 9/10 |
| lean_right | locomotion | 1.2 | 37 | 1,212 | N | body | SHIP | 9/10 |
| look_around | locomotion | 4.0 | 121 | 1,818 | N | body | SHIP | 9/10 |
| run | locomotion | 0.8 | 25 | 835 | Y | body | SHIP | 9/10 |
| scratch_head | locomotion | 2.5 | 76 | 1,152 | N | body | SHIP | 9/10 |
| sit_down | locomotion | 1.5 | 46 | 801 | N | body | SHIP | 9/10 |
| sit_idle | locomotion | 10.0 | 301 | 2,686 | Y | body | SHIP | 9/10 |
| stand_up | locomotion | 1.5 | 46 | 759 | N | body | SHIP | 9/10 |
| step_back | locomotion | 1.0 | 31 | 815 | N | body | SHIP | 9/10 |
| stretch | locomotion | 3.5 | 106 | 986 | N | body | SHIP | 9/10 |
| turn_left | locomotion | 1.0 | 31 | 811 | N | body | SHIP | 9/10 |
| turn_right | locomotion | 1.0 | 31 | 811 | N | body | SHIP | 9/10 |
| walk | locomotion | 1.2 | 37 | 1,515 | Y | body | SHIP | 9/10 |

### Micro-layer (2 clips — 24.0s, 2,586 keyframes)

| id | category | dur (s) | frames | keyframes | loop | owner | verdict | overall |
|----|----------|--------:|-------:|----------:|:----:|-------|:------:|:-------:|
| micro_body_layer | micro_layer | 12.0 | 361 | 2,346 | Y | body | SHIP | 9/10 |
| micro_face_layer | micro_layer | 12.0 | 361 | 240 | Y | facial | SHIP | 9/10 |

## Notes

### (a) Accepted cosmetic items (adjudicated, non-defect)

- **Toon mid-blink lid-fold:** on the stylized toon mesh the upper lid folds slightly at mid-blink amplitudes. Intrinsic to the toon eyelid geometry, not the animation; accepted across all blink/lid-bearing clips.
- **NEARLY-STATIC / DEAD-ZONE metric caveat:** `inspect_clip.py` measures whole-frame PIXEL motion, so body-framed sub-degree clips (idles, leans, step_back, look_around, seated sit_idle) legitimately read NEARLY STATIC or DEAD ZONE. These were triaged against curves/strips/bone probes (motion present, 'sensed not seen'), NOT auto-rejected. sit_idle's flagged windows were bone-probe-verified as a continuous 0.76-deg breathing arc, not a freeze.

### (b) Optional non-blocking polish notes (OPTIONAL / non-gating — all these clips already SHIP at 9/10)

- **Bilateral nostril L/R symmetry** on 8 talking clips — the Nose_Sneer/nostril micro is L/R symmetric where a trace of asymmetry would read marginally livelier. OPTIONAL.
- **idle_phone / idle_relaxed cadence off-grid** — micro-event scheduling sits fractionally off an ideal cadence grid. OPTIONAL, imperceptible at conversation distance.
- **idle_relaxed L_Index1 micro-key** — one finger's micro-drift key could be smoothed. OPTIONAL.
- **shrug R-phase lag** — the right shoulder trails the left by a hair more than ideal on the shrug release. OPTIONAL.

_None of the above gate shipping; they are captured for a future optional polish pass only._

### (c) Documented gap vs the 107-clip director spec — 4 UNBUILT transition-helper clips

The director spec enumerates 107 clips; 103 are built and shipped. The following 4 **transition-helper** clips (category `transition`, owner `body`) were spec'd but NOT authored, and are a documented gap:

| id | category | owner | status |
|----|----------|-------|--------|
| arms_crossed_exit | transition | body | UNBUILT (spec'd, not authored) |
| hands_pockets_exit | transition | body | UNBUILT (spec'd, not authored) |
| phone_raise | transition | body | UNBUILT (spec'd, not authored) |
| phone_lower | transition | body | UNBUILT (spec'd, not authored) |

These are runtime exit/entry blends (their partner poses — arms_crossed, hands_in_pockets, idle_phone — all shipped). Runtime can crossfade in their absence; building them is future work, not a regression against the shipped set.

### (d) Rig facts established during QA (carry forward)

- **Jaw is JawRoot-bone-driven** (`CC_Base_JawRoot`), not a shape-key-only jaw — facial/lipsync clips animate the jaw via the bone; teeth/tongue follow the JawRoot chain.
- **Toon arm cannot abduct out-to-side-and-up** — the arm sweeps the hand center-front on a raise; reaches are rig-limited (adjust_glasses lands at the TEMPLE not the center bridge; scratch_head reaches the back-CROWN not the forehead). Verified clip-free — a rig limit, not a defect.
- **NeckTwist01/02 = the neck chain** (legit to key); `BoneRoot` and `*Twist`/share/identity bones are forbidden (framework-refused). This 'NeckTwist errata' was applied throughout — no clip keys BoneRoot, twist helpers, or identity/customization morphs.

### Methodology

Every clip passed: automated pre-pass (`inspect_clip.py` energy/loop/metronome/dead-zone + encoder-GOP & I-frame-comb discriminators), headless curve audit (`audit_curves.py` — linear-rotation, forbidden-bone, byte-mirror, range/seam, timing, cross-mesh follower coverage), scorecard scoring against `library_spec.json` per-clip beats, and — for the judgment-call clips — direct Blender bone-track probes (per-frame position/rotation) and strip reads. Loop clips' seams verified numerically (value_diff + tangent_diff = 0).
