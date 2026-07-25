# QA Scorecard — happy

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/happy/ (mp4, strip, stills, meta.json), qa/reports/happy_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action happy + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial, body unkeyed (head hook is body-layer's). |
| 2 | Timing & spacing | 9 | Duchenne timing: Cheek onset f1, Smile f3 (2f behind), Squint f5 — correct muscle order; eased. |
| 3 | Naturalness | 9 | asymmetric throughout: Cheek L0.51/R0.40, Smile L0.65/R0.56, Squint L0.30/R0.27; hold wavers. |
| 4 | Facial aliveness | 9 | cheeks-FIRST Duchenne order (strip confirms), eye squint 0.3 engaged (no dead-eye), hold ALIVE: smile wavers 0.57-0.65 (+-0.05), cheek re-raise at f35 (0.43->0.51). |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | eye squint completes the smile (lids lower), not frozen. |
| 7 | Loop seamlessness | N/A | one-shot end-hold (runtime crossfades). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
