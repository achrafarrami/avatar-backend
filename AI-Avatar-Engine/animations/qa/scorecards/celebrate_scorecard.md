# QA Scorecard - celebrate

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/celebrate/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/celebrate_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action celebrate + follower slots).
- **Automated flags (inspect_clip):** 0 flags (peak energy 1.625 - big two-arm motion).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | BEST weight evidence: Hip (6k) + L_Foot/R_Foot (4k each) + Spine02 (14k) - both-arms-up celebration commits weight through hips and feet with torso counter-extension. Not a floating upper body. |
| 2 | Timing & spacing | 9 | Arm 60 keys bezier; anticipation dip -> arms rocket up -> overshoot -> settle -> lower to neutral. Full antic/overshoot/settle chain. |
| 3 | Naturalness | 9 | L/R arm keys OFFSET (identical_frames=False; R leads) - no byte-mirror. Strip shows asymmetric arm heights and counter-motion. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 30 finger bones, 109 keys; hands open/celebrate with finger spread. Fingers settle at peak (0 late movers acceptable - arms already lowering by hold). |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, Hip owns weight (ruling #4), naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Textbook weight commitment (hip+feet) and L/R offset; no byte-mirror.
