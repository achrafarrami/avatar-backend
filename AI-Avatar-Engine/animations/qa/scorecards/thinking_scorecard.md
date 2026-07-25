# QA Scorecard — thinking

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 4.0s, loop=true
- **Evidence:** previews/thinking/ (mp4, strip, stills, meta.json), qa/reports/thinking_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action thinking + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial (micro nod is body-hook). |
| 2 | Timing & spacing | 9 | gaze breaks up-left (saccade f0-4), furrow builds over 10f; lip cycles purse/release/press at varied frames; jaw slide held 20f. |
| 3 | Naturalness | 9 | lip cycles non-metronomic (varied spacing); Brow_Drop L/R asym (maxdelta 0.088); gaze micro-shifts twice (bone keys f40,55,75,89). |
| 4 | Facial aliveness | 9 | furrow BREATHES 0.253-0.347 (spec 0.25-0.35); lip activity cycles (pucker 0.2 / press 0.15); jaw sideways 0.15 (chewing the thought). |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | gaze aversion up-LEFT (Look_Up 0.42-0.48 + Look_L 0.27-0.33 — never center-up zombie); micro-shifts within the region (recomputing), not locked. |
| 7 | Loop seamlessness | 9 | seam clean: all channels <=1e-4 value+tangent. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
