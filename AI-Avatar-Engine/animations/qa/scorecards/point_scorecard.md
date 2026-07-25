# QA Scorecard - point

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.8s, loop=false
- **Evidence:** previews/point/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/point_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action point + follower slots).
- **Automated flags (inspect_clip):** NEARLY-STATIC = framing false-positive.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; torso orients toward the pointed target. |
| 2 | Timing & spacing | 9 | Arm 44 keys bezier; raise antic -> extend point -> hold on target -> settle. |
| 3 | Naturalness | 9 | Index isolates while other fingers curl (cascade), natural pointing arc. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 26 finger bones, 92 keys; index extends while curl fingers hold soft (13 hold-movers). No board hand. |
| 6 | Eye behavior | 9 | Gaze target carried: Eye_L/R_Look_* keyed - eyes go to the pointed thing (correct for a directing gesture). |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, gaze keys legit (not never_animate), naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Eyes-lead-to-target gaze present; flag is framing.
