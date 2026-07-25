# QA Scorecard - embarrassed

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/embarrassed/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/embarrassed_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action embarrassed + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Aversion-FIRST: Eye_Look_Down f3 + Look_R f5 BEFORE the smile (Mouth_Smile f7) - order carries meaning. Suppressed smile: Smile 0.433 + Mouth_Press 0.3 (16 keys). Head turns away f9-23. Quick blink f22. |
| 3 | Naturalness | 9 | Asymmetric smile 0.433/0.34, cheek 0.4/0.34. Gaze aversion delta 0.22. No mirror. |
| 4 | Facial aliveness | 9 | Suppressed sealed smile verified in front.png (SEAL PASS - lips pressed, no open mouth). Cheeks 0.4 engage. Gaze-away precedes smile (proud-vs-embarrassed distinction correct). |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Gaze breaks down-right first (aversion); head turns away not toward camera; blink f22. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Head turn-away hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Aversion-before-smile ordering and seal both confirmed.
