# QA Scorecard — slow_blink

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.8s, loop=false
- **Evidence:** previews/slow_blink/ (mp4, strip, stills, meta.json), qa/reports/slow_blink_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action slow_blink + per-mesh follower slots).
- **Note:** wink-class fixed (1f cap) confirmed: L close f9 / R close f10.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | close 8f (f1-9, heavy), hold 3f (f9-12), open 12f (f12-23, soft ease) — distinct from blink, has the hold phase per spec. |
| 3 | Naturalness | 9 | L/R offset 1f (peak 1.0 vs 0.97); brows drop 0.1 asymmetric (L 0.10/R 0.09). |
| 4 | Facial aliveness | N/A | blink clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | true slow blink (not stretched blink): hold present, eased open, brows 0.1 drop+recover 4f after lids. |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
