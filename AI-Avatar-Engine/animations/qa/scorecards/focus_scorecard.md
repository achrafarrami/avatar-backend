# QA Scorecard — focus

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1 (facial Tier-1 batch)
- **Duration/loop:** 1.0s, loop=false
- **Evidence:** previews/focus/ (mp4, strip, stills, meta.json), qa/reports/focus_inspection.png + _metrics.json (updated inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_facial.json (action focus + per-mesh follower slots).


## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | layer contract. |
| 2 | Timing & spacing | 9 | convergence over ~4f (bones f1->f5), pupil contracts over 8f (not instant), lids narrow over ~10f; one micro re-fixation ~f22. |
| 3 | Naturalness | 9 | convergence 0.158/0.148 (asym, <0.2 not cross-eyed); squint 0.12/0.11, brow drop 0.10/0.09. |
| 4 | Facial aliveness | N/A | eye clip. |
| 5 | Hand & finger life | N/A | layer contract. |
| 6 | Eye behavior | 9 | Eye_Pupil_Contract 0->0.3 confirmed on CC_Base_Eye; convergence nasal 0.15 (not cross-eyed); fixation measurably stiller than gaze clips (reduced drift), micro re-fixation present. |
| 7 | Loop seamlessness | N/A | one-shot end-hold. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_facial.json): no linear rotation, no never_animate/twist keys (NeckTwist errata applied), no range violations, action name==clip id, 30fps, cross-mesh followers driven. Pupil key on CC_Base_Eye. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9; N/A dimensions marked explicitly per rubric (layer contract: fingers/gaze/body owned by other runtime layers; one-shot clips end-hold by design).
