# QA Scorecard — eye_dart

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 1.2s, loop=false
- **Evidence:** previews/eye_dart/ (mp4, strip, stills, meta.json), qa/reports/eye_dart_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action eye_dart + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | three 2f-ballistic saccades (bones f3,5 / 16,18 / 27,29), fixation gaps UNEQUAL (~11/9/6f). |
| 3 | Naturalness | 9 | amplitudes vary (Look_R 0.5, Look_Up 0.44, Look_Down 0.21); not a symmetric pattern; all L/R asym. |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | ballistic 2f saccades, unequal intervals + unequal amplitudes (anti-metronome gates met), lids micro-react on vertical components only (Eye_Wide 0.08 / partial-blink 0.07). |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
