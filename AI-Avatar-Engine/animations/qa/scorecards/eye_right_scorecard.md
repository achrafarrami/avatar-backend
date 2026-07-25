# QA Scorecard — eye_right

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.5s, loop=false
- **Evidence:** previews/eye_right/ (mp4, strip, stills, meta.json), qa/reports/eye_right_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action eye_right + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract, no head keys. |
| 2 | Timing & spacing | 9 | ballistic 3f saccade (bones f1->f4) to 0.814, fixation after. |
| 3 | Naturalness | 9 | NOT a byte-mirror of eye_left: drift key frames differ ([1,4,7,11,13,16] vs eye_left's [1,4,6,9,12,14,16]); amplitude asym (0.814/0.773). |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | ballistic, overshoot, distinct fixation-drift pattern from eye_left (spec anti-flip gate met). |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
