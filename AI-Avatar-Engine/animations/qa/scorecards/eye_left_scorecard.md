# QA Scorecard — eye_left

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.5s, loop=false
- **Evidence:** previews/eye_left/ (mp4, strip, stills, meta.json), qa/reports/eye_left_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action eye_left + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract; no head keys (correct — head coupling is layered). |
| 2 | Timing & spacing | 9 | saccade ballistic: eye bones reach target in 3f (keys f1->f4), then fixation. No easing over >5f. |
| 3 | Naturalness | 9 | conjugate both eyes, amplitude asymmetric (L_Look_L 0.816 / R 0.791); fixation micro-drift keys f6-16. |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | 0->0.8 in 3f ballistic + ~2% overshoot (0.816), fixation drift present (not frozen), NO head keys per spec, ends holding. |
| 7 | Loop seamlessness | N/A | one-shot end-hold. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Look driven on body+CC_Base_Eye+TearLine+EyeOcclusion. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
