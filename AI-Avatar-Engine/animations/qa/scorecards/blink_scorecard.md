# QA Scorecard — blink

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.37s, loop=false
- **Evidence:** previews/blink/ (mp4, strip, stills, meta.json), qa/reports/blink_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action blink + per-mesh follower slots).
- **Note:** inspect SHORT flag = expected (spec 0.37s), not a defect.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip, body unkeyed (layer contract). |
| 2 | Timing & spacing | 9 | close 0->1 in 3f (f1-4), 1f hold, open over 6f (f5-11, ease-out) — open slower than close per spec. |
| 3 | Naturalness | 9 | L/R not identical: L peak 1.0 / R 0.998, R lags 1f (f4 vs f5). Asymmetry present, wink-class avoided. |
| 4 | Facial aliveness | N/A | blink clip — no facial expression dimension. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | 3f ballistic close, 6f eased open, micro Eye_Squint 0.05 rides the close; lid-fold chunk at mid-blink = standing-ruling cosmetic, not scored. |
| 7 | Loop seamlessness | N/A | one-shot (loop=false). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Eyelash/TearLine/EyeOcclusion/Toon_Eyebrows all driven (lash stays attached). Duration 0.40s < 0.45s cap. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
