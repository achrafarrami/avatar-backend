# QA Scorecard — neutral_alive

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 10.0s, loop=true
- **Evidence:** previews/neutral_alive/ (mp4, strip, stills, meta.json), qa/reports/neutral_alive_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action neutral_alive + per-mesh follower slots).
- **Note:** inspect METRONOME r=0.83 @0.50s ADJUDICATED as encoder: I-frame grid comb 19/19 energy maxima on a rigid 15f (GOP) grid, spikes against near-static background — not authored motion. gopsize now 250 for future renders. Strip confirms genuine aperiodic micro-variation.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial default face, body unkeyed. |
| 2 | Timing & spacing | 9 | irregular event schedule (brow raise, lip compression 8f-in/14f-out, cheek, nostril flickers, swallow) at unequal spacings; eased in/out. |
| 3 | Naturalness | 9 | no two events share spacing; all L/R asym (Brow 0.065/0.035, Cheek 0.05/0.03, etc.); aperiodic (autocorr peak is encoder, not motion). |
| 4 | Facial aliveness | 9 | never a readable expression at thumbnail (strip verified — all deltas <=0.08: max Mouth_Press 0.08); lid tone breathes 0.02-0.05 (partial, NOT baked full blinks — spec collision gate met); no static >2s (54 brow + 61 lid keys across 300f). |
| 5 | Hand & finger life | N/A | facial. |
| 6 | Eye behavior | 9 | lid tone slow cycles 0.02-0.05 (partial), L/R offset asym; blinks correctly NOT baked (runtime scheduler owns them). |
| 7 | Loop seamlessness | 9 | zero-delta seam: all channels <=1e-4 value AND tangent diff; f001~=f301 in strip. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Every delta <=0.08 per spec; no baked full blinks. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
