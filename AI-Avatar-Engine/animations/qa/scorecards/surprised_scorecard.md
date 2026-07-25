# QA Scorecard — surprised

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 1.2s, loop=false
- **Evidence:** previews/surprised/ (mp4, strip, stills, meta.json), qa/reports/surprised_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action surprised + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial (head jerk is body-hook). |
| 2 | Timing & spacing | 9 | SPEED read: micro forward anticipation (head bone f1-3), brows rocket 0->0.927 in 3f (f3-6), jaw drops with 1f LAG (starts f4, peaks f9 — heavier), onset ~6f total. |
| 3 | Naturalness | 9 | brow/lid stagger 1f (brow f3, wide f4 — NOT identical frames), 3% overshoot then settle; all L/R asym (brow 0.927/0.890, wide 0.82/0.78). |
| 4 | Facial aliveness | 9 | brows+lids+jaw with correct stagger; hold micro-tremor 0.02 on brows (f13-31 wavers 0.887-0.917); anticipation dip present. |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | Eye_Wide 0.8 lids peak 1f after brow, tracks the surprise. |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Toon_Eyebrows driven (critical for this clip). |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
