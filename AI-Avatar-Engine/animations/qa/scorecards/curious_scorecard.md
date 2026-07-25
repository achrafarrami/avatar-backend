# QA Scorecard - curious

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/curious/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/curious_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action curious + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Head tilt WITH brows raising f1 (spec: simultaneous for curious), lids widen 0.2 f5, lips part 0.1 f7. Spine02 lean hook f1. Micro head re-aim f34-41. |
| 3 | Naturalness | 9 | One brow higher: Inner_L 0.451 vs R 0.36, Outer_L 0.396/R 0.324. Eye_Wide 0.2/0.176. All asymmetric, no mirror. |
| 4 | Facial aliveness | 9 | Gaze locks with focus-like stillness; brows raise (15 keys L) alive. Curiosity read via tilt+lean present. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Eyes hold target; blink f29; lids widen 0.2 (curious brightness). |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Head-tilt + spine lean hooks authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Head-tilt and forward-lean hooks both present (curiosity-without-tilt reject avoided).
