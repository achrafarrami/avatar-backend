# QA Scorecard - thumbs_up

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.8s, loop=false
- **Evidence:** previews/thumbs_up/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/thumbs_up_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action thumbs_up + follower slots).
- **Automated flags (inspect_clip):** NEARLY-STATIC = framing false-positive (peak 0.25, richly keyed 104 finger keys).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; torso stable under the presented hand. |
| 2 | Timing & spacing | 9 | Arm 42 keys bezier; raise antic -> thumb form -> present hold -> settle. |
| 3 | Naturalness | 9 | Deliberate presentation with eased arc; not mechanical. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | STRONG hand life: 28 finger bones, 104 keys; thumb+fingers cascade to form the thumbs-up during the reach (not pre-formed); 13 finger movers in the hold keep it alive. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Grip forms during the reach; hold stays alive. Flag is framing.
