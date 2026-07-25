# QA Scorecard — micro_face_layer

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 12.0s, loop=true
- **Evidence:** previews/micro_face_layer/ (mp4, strip, stills, meta.json), qa/reports/micro_face_layer_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action micro_face_layer + per-mesh follower slots).
- **Note:** ADDITIVE layer — scored against layer contract ('barely perceptible alone' is the spec). inspect METRONOME r=0.74 @0.50s ADJUDICATED as encoder: I-frame grid comb 24/28 (86%) maxima on rigid 15f GOP grid vs near-static background. Strip confirms aperiodic spread micro-events.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | additive facial layer. |
| 2 | Timing & spacing | 9 | eased micro events at varied spacings across 12s. |
| 3 | Naturalness | 9 | no two events same spacing; all L/R asym; aperiodic (autocorr = encoder comb, not authored). |
| 4 | Facial aliveness | 9 | micro-events (cheek/lip-compress/brow/nostril/lid drift) all <=0.06 delta (never fights a base expression); events spread across BOTH halves of the loop (strip verified), not clustered. |
| 5 | Hand & finger life | N/A | facial layer. |
| 6 | Eye behavior | 9 | lid tone drift <=0.04 only (no baked blinks — additive). |
| 7 | Loop seamlessness | 9 | all curves zero at seam (<=1e-4 value+tangent). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. CRITICAL: NO jaw/viseme/V_* keys present (lipsync owns them) — verified; all deltas <=0.06 <0.08. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
