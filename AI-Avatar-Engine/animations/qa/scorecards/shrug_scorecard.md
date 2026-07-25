# QA Scorecard - shrug

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 1.8s, loop=false
- **Evidence:** previews/shrug/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/shrug_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action shrug + follower slots).
- **Automated flags (inspect_clip):** 0 flags.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine chain keyed; shoulders rise via clavicles with stable trunk - classic 'I don't know' weight-neutral shrug. |
| 2 | Timing & spacing | 9 | Arm 48 keys bezier; shoulders rise antic -> hold -> release. Eased. |
| 3 | Naturalness | 9 | L/R amplitudes DIFFER (Upperarm qy L0.098/R0.107, Clavicle L0.083/R0.078, ~2-9%) - asymmetric amplitude satisfies the naturalness bar; byte-mirror detector clears it (0 findings). |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 26 finger bones, 92 keys; hands turn palms-up with finger life (8 hold-movers). |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. NOTE: shrug L/R timing is synchronized (natural for a bilateral shrug) but amplitudes are asymmetric 2-9% - clears the no-byte-mirror bar. If a future pass wants more life, add a 1-2f R-shoulder phase lag.
