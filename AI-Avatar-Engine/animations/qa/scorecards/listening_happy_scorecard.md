# QA Scorecard - listening_happy

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_happy/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_happy_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_happy + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | soft_smile baseline 0.383 (51 keys) held alive with waver; blooms briefly then relaxes. Cheeks 0.29 (not mouth-only). Faster nod cadence (head 84 keys). Lower-lid warmth. |
| 3 | Naturalness | 9 | Asymmetric smile 0.383/0.31, cheek 0.29/0.245; bloom event present; nods varied; no mirror. |
| 4 | Facial aliveness | 9 | Smile NOT static (51/52 keys waver + bloom); cheeks engaged (Duchenne warmth). Alive. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Soft lids; cheek-raise warmth; gaze on speaker. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Nod-cadence hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Bloom event + cheek engagement confirmed (mouth-only-smile reject avoided).
