# QA Scorecard - thumbs_down

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.8s, loop=false
- **Evidence:** previews/thumbs_down/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/thumbs_down_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action thumbs_down + follower slots).
- **Automated flags (inspect_clip):** NEARLY-STATIC = framing false-positive.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; stable torso. |
| 2 | Timing & spacing | 9 | Arm 42 keys bezier; raise -> thumb-down form -> hold -> settle. |
| 3 | Naturalness | 9 | Eased, deliberate; distinct from thumbs_up (inverted, not a byte flip). |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 28 finger bones, 97 keys; thumb-down cascades during reach; 13 hold-movers. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Rich finger life; flag is framing.
