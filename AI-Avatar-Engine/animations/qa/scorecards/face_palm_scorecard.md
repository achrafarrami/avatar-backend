# QA Scorecard - face_palm

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.2s, loop=false
- **Evidence:** previews/face_palm/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/face_palm_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action face_palm + follower slots).
- **Automated flags (inspect_clip):** 1 flag (DEAD ZONE 0.53-1.33s = 0.8s settle). Brief; the hand keeps finger life through it (12 hold-movers).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; hand rises to the face with stable trunk. |
| 2 | Timing & spacing | 9 | Arm 52 keys bezier; raise antic -> hand to face -> react -> lower. Eased. |
| 3 | Naturalness | 9 | Single-arm exasperation arc; natural, non-mechanical. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | STRONG hand life: 26 finger bones, 88 keys; 12 finger movers DURING the hold - the hand is alive at the face, not frozen. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Hand reaches the LOWER face (not forehead) per rig limit (ruling #1). Contact CLEAN in strip. Strong hand life in the hold - one of the most alive contact clips.
