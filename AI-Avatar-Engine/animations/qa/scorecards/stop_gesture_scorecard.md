# QA Scorecard - stop_gesture

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.5s, loop=false
- **Evidence:** previews/stop_gesture/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/stop_gesture_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action stop_gesture + follower slots).
- **Automated flags (inspect_clip):** 0 flags.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine02+Hip (4k) keyed - weight settles as the palm pushes out (stop = braced). |
| 2 | Timing & spacing | 9 | Arm 46 keys bezier; raise antic -> palm-out push -> hold. Eased with a firm stop. |
| 3 | Naturalness | 9 | Single-arm palm-out; natural push arc. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 26 finger bones, 76 keys; fingers splay to the flat stop palm (4 hold-movers keep it from freezing). |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, Hip weight, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Palm-out stop with hip-braced weight; hand alive in hold.
