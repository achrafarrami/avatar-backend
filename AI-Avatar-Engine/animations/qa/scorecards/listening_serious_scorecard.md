# QA Scorecard - listening_serious

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_serious/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_serious_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_serious + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Damped register: Brow_Drop 0.225 baseline (41 keys), lips lightly pressed/tightened 0.1-0.12, NO smile. Two slow deliberate nods only (head 71 keys). One micro jaw clench. Blink cadence 5-6s (runtime hint in meta). |
| 3 | Naturalness | 9 | Asymmetric brows 0.225/0.199, tighten 0.12/0.102; only two nods; no mirror. |
| 4 | Facial aliveness | 9 | Micro amplitude damped vs neutral_alive (seriousness=stillness); no smile leak; sealed lips. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Unbroken gaze; stretched blink cadence hint present for runtime scheduler. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Two nods max; no smile keys; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Damping, no-smile, and 2-nod-max all confirmed; blink-cadence runtime hint noted.
