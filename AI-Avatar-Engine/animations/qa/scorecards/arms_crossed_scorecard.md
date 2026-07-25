# QA Scorecard - arms_crossed

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/arms_crossed/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/arms_crossed_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action arms_crossed + follower slots).
- **Automated flags (inspect_clip):** 2 flags (DEAD ZONE 0.67-2.0s + NEARLY STATIC). The 1.33s still tail is the holdable end pose; runtime crossfades out (transition_model) well before 2s. Under the 2s reject line.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; arms cross the chest with weight settled and stable. |
| 2 | Timing & spacing | 9 | Arm 34 keys bezier; reach across -> settle into cross -> hold. Eased. |
| 3 | Naturalness | 9 | Left-over-right cross (asymmetric by nature); entry arc natural. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 26 finger bones, 77 keys forming the crossed grip during entry. Hold is still (0 finger movers, dead zone 0.67-2.0s = 1.33s) - crossfade-handoff end pose (ruling #2); interpen-clean. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. NOTE: crossed-arms hold is the intended crossfade-handoff pose (ruling #2). Interpenetration clean. Weakest still-hold of the batch but within the <2s bar; consider slight breath drift if held longer at runtime.
