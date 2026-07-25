# QA Scorecard — soft_smile

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/soft_smile/ (mp4, strip, stills, meta.json), qa/reports/soft_smile_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action soft_smile + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial. |
| 2 | Timing & spacing | 9 | slow 12f onset to corners 0.35 (>=8f, no snap); micro fade-return at ~f45 (breathes). |
| 3 | Naturalness | 9 | one corner 20% stronger (L0.35/R0.28) WITH cheek raise (not a smirk); cheek/squint asym. |
| 4 | Facial aliveness | 9 | warmth in the lower lid (Eye_Squint 0.15) not just mouth; cheek 0.2; closed-lip pleasant read; breathing hold. |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | lower-lid raise 0.15 engaged (spec's warmth channel). |
| 7 | Loop seamlessness | N/A | one-shot end-hold. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
