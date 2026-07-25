# QA Scorecard - come_here

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/come_here/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/come_here_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action come_here + follower slots).
- **Automated flags (inspect_clip):** NEARLY-STATIC = framing false-positive (peak energy diluted by full-body frame; 160 finger keys prove rich motion).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine02+Hip (4k) keyed - weight shifts under the extended beckoning arm. |
| 2 | Timing & spacing | 9 | Arm 49 keys bezier; extend -> beckon curls -> settle. Eased. |
| 3 | Naturalness | 9 | Beckoning finger curls repeat with varied timing (not a uniform loop). |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 160 finger keys (2nd-most) - repeated beckon curls cascade; extremely alive fingers. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, Hip weight (ruling #4), naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Rich beckon finger life + hip weight shift. Flag is framing.
