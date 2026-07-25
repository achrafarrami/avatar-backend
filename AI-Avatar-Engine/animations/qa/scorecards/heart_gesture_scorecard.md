# QA Scorecard - heart_gesture

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/heart_gesture/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/heart_gesture_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action heart_gesture + follower slots).
- **Automated flags (inspect_clip):** 0 flags (peak energy sufficient).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; both hands form a heart at the chest, weight centered and stable. |
| 2 | Timing & spacing | 9 | Arm 46 keys bezier; both hands reach -> form heart -> hold -> release. Eased. |
| 3 | Naturalness | 9 | L/R arm keys OFFSET (identical_frames=False) - hands arrive with slight stagger, no byte-mirror. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | STRONGEST hand life: 28 finger bones, 102 keys; 22 finger movers in the hold - the heart shape lives, fingers not frozen. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Heart formed cleanly at chest; contact/interpenetration CLEAN in strip (fingers meet to form the outline, no torso penetration). Very alive hold. L/R offset present.
