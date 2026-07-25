# QA Scorecard — eye_down

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.5s, loop=false
- **Evidence:** previews/eye_down/ (mp4, strip, stills, meta.json), qa/reports/eye_down_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action eye_down + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | saccade 3f (bones f1->f4) to 0.71; partial lid follows with 1f lag. |
| 3 | Naturalness | 9 | conjugate asym (0.71/0.68); partial-blink L 0.22/R 0.209. |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | lid-follow-down met: Eye_Blink partial 0.20 (~20%), settles (not full Blink bounce) — downcast read, not startled. |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
