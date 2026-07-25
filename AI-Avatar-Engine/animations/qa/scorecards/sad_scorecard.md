# QA Scorecard — sad

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 3.0s, loop=false
- **Evidence:** previews/sad/ (mp4, strip, stills, meta.json), qa/reports/sad_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action sad + per-mesh follower slots).
- **Note:** wink-class fixed: slow blink at f65-67 shows matched lid phases (strip f67 both lids closed together).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial (head sink is body-hook). |
| 2 | Timing & spacing | 9 | SLOW onset 21f (Brow_Raise_Inner f1->f22, sadness arrives not snaps); frown 4f lag; head sinks arriving LAST (f20 vs brow f1). |
| 3 | Naturalness | 9 | asymmetric frown (Inner_Brow L 16 keys/R 3 keys, Frown L0.45/R0.34); lip tremble non-metronomic (f75/80/86 uneven). |
| 4 | Facial aliveness | 9 | inner-brow pinch 0.6 present (the oblique brow — not grumpy-frown); heavy lids 0.3; gaze drop 0.3; lip tremble 0.05 x3; slow blink f65. |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | heavy lids 0.3 + gaze drop; slow blink f65 with matched L/R phases (wink fix holds); lid-fold chunk = standing cosmetic. |
| 7 | Loop seamlessness | N/A | one-shot end-hold. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Toon_Eyebrows driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
