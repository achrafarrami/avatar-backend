# QA Scorecard - hands_together

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.5s, loop=false
- **Evidence:** previews/hands_together/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/hands_together_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action hands_together + follower slots).
- **Automated flags (inspect_clip):** 2 flags (DEAD ZONE 0.53-1.5s end-hold + NEARLY STATIC). Both explained by the intended holdable end pose; 0.97s < 2s rubric reject.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; hands clasp at front with stable centered weight. |
| 2 | Timing & spacing | 9 | Arm 30 keys bezier; reach -> clasp -> hold. Eased into the contact. |
| 3 | Naturalness | 9 | Interleaved clasp; not a rigid single block on entry (fingers interleave during reach). |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 126 finger keys during the reach forming the clasp. Hold is still (0 finger movers, dead zone 0.53-1.5s = 0.97s < 2s reject line) - this is the crossfade-handoff end pose (ruling #2), interpen-clean. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. NOTE: clasp hold is still (crossfade-handoff pose per ruling #2, under the 2s reject line). Interpenetration clean. If runtime ever sustains it >2s, add finger micro-drift.
