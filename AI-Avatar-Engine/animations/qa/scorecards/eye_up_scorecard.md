# QA Scorecard — eye_up

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 0.5s, loop=false
- **Evidence:** previews/eye_up/ (mp4, strip, stills, meta.json), qa/reports/eye_up_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action eye_up + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | saccade 3f (bones f1->f4) to 0.714; brows drift up 0.1 over ~6f (slower than eyes — muscle vs ballistic). |
| 3 | Naturalness | 9 | conjugate asym (0.714/0.685); Eye_Wide L 0.15/R 0.135, brows L 0.10/R 0.09. |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | CRITICAL lid-follow met: Eye_Wide lifts f2->f5 (0.15), 1f behind saccade — upper lids track upward gaze (no iris-slice-behind-static-lid); brows non-ballistic. |
| 7 | Loop seamlessness | N/A | one-shot. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
