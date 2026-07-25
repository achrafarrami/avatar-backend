# QA Scorecard - thinking_pose

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.2s, loop=false
- **Evidence:** previews/thinking_pose/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/thinking_pose_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action thinking_pose + follower slots).
- **Automated flags (inspect_clip):** 1 flag (DEAD ZONE 0.73-2.2s hold). The hand-at-chin hold is the pose; contact verified clean; <2s-per-mesh spirit honored (crossfade-handoff).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; hand-to-chin with the supporting forearm across the torso, weight settled and stable. |
| 2 | Timing & spacing | 9 | Arm 34 keys bezier; raise -> hand to chin -> hold. Eased contact. |
| 3 | Naturalness | 9 | Asymmetric (one hand at chin, other supports elbow); natural settle into contact. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 27 finger bones, 79 keys; fingers curl at the chin during the reach; one finger (R_Index2) micro-lives in the hold. |
| 6 | Eye behavior | 9 | Gaze target carried (Eye_Look_* keyed) - eyes drift in thought (correct). |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, gaze keys legit, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Hand reaches the LOWER face/chin (not forehead) per rig limit (ruling #1). Contact interpenetration CLEAN in strip. Reads clearly as a thinking pose. Still hold is the intended handoff.
