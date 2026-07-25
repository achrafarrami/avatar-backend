# QA Scorecard - disappointed

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/disappointed/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/disappointed_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action disappointed + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | EXHALE-LED order is the read: Spine02+Clavicle sigh f1 -> nostril f3 -> inner brows f9 -> mouth press/frown f15 -> head micro-shake f13-31 -> gaze breaks down-away f19. Breath-before-face confirmed. |
| 3 | Naturalness | 9 | Asymmetric frown 0.42/0.35, press 0.26/0.22. Single head shake only (3deg, not 'no'). Nostril delta 0.03 secondary. No mirror. |
| 4 | Facial aliveness | 9 | Sealed mouth verified in front.png (frown+press, NO Jaw_Open key - SEAL PASS, no stale-open-mouth). Ends looking away, lids 0.2. One slow blink (vmax 1.0). |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Gaze aversion down-and-left (Look_Down 0.27 + Look_L 0.16); disappointment averts, does not hold target. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | breathing_tired exhale hook + spine/clavicle authorized; single shake; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Breath->face->head->gaze sequence and mouth-seal both confirmed.
