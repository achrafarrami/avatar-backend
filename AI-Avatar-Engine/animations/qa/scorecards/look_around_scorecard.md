# QA Scorecard — look_around

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 4.0s (121f), loop=false
- **Evidence:** previews/look_around/ (mp4, strip, stills, meta.json); qa/reports/look_around_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (action + Eye/head follower slots).
- **Automated flags (inspect_clip):** NEARLY STATIC (energy 0.106/0.243). **Body-framing false-positive per ruling #2 (gaze/head/torso turns are small in whole-frame pixels).**
- **Curve audit:** findings=0 — full skeleton + head+eyes chain keyed, BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Hard-right look adds a right-foot adjust step (~f60) to support torso rotation >25deg — weight supported, not floating. |
| 2 | Timing & spacing | 9 | Unequal dwells (acorr 0.258 @ 0.833s = the 3 target holds, irregular); eased chain per target. |
| 3 | Naturalness | 9 | 3 targets (left, hard-right, front) with non-equal dwell times; foot adjust only on the deep turn. |
| 4 | Facial aliveness | N/A | body clip — facial owned by runtime layer (departure blinks are the eye hook, below). |
| 5 | Hand & finger life | N/A | arms not the focus; finger micro owned by runtime body-micro layer. Marked N/A per anchor convention for gaze-driven clips. |
| 6 | Eye behavior | 9 | Chain order correct per target: eyes(2f) → head(+3f) → shoulders(+2f) → torso; blink on each departure (Eye slot keyed). Eyes lead, torso last. |
| 7 | Loop seamlessness | N/A | one-shot; ends front, idle-compatible. |
| 8 | Technical | 9 | Gaze-chain layering correct, foot-adjust gate on >25deg turn honored, bezier, no forbidden keys, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Eyes-lead-then-body chain honored per target, unequal dwells, departure blinks present, and the >25deg turn gets its supporting foot adjust. NEARLY STATIC is the ruling-#2 body-framing false-positive.
