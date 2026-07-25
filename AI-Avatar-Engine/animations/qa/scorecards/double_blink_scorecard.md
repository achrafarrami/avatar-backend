# QA Scorecard — double_blink

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.6s, loop=false
- **Evidence:** previews/double_blink/ (mp4, strip, stills, meta.json), qa/reports/double_blink_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action double_blink + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | blink#1 full f1-9, gap with lids held ~0.12 (not full open), blink#2 80% amp (0.8) f12-18, faster open — reflexive doublet read. |
| 3 | Naturalness | 9 | two blinks differ (amp 1.0 vs 0.8, timing), L/R offset 1f asymmetric; brow residue 0.05 at f17. |
| 4 | Facial aliveness | N/A | blink clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | doublet lids never return fully open between (0.12 floor) — sells the reflex; brow surprise-residue present. |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
