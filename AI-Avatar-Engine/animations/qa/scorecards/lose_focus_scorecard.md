# QA Scorecard — lose_focus

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 1.5s, loop=false
- **Evidence:** previews/lose_focus/ (mp4, strip, stills, meta.json), qa/reports/lose_focus_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action lose_focus + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | the ONE legitimate slow eye move: smooth-pursuit drift over 25f+ (bones f1,9,17,27 — NOT saccadic), ends with soft blink f38-39 that doesn't re-alert. |
| 3 | Naturalness | 9 | down-left drift (Look_Down 0.334 + Look_L 0.19); asym L/R (0.334/0.319). |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | Eye_Pupil_Dilate 0->0.25 confirmed; drift is smooth-pursuit speed (not fast saccade); final lid tone stays heavy 0.12 (ends unalert per spec). |
| 7 | Loop seamlessness | N/A | one-shot end-hold. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Pupil dilate on CC_Base_Eye. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
