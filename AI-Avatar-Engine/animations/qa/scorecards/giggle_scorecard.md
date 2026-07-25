# QA Scorecard - giggle

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 1.8s, loop=false
- **Evidence:** previews/giggle/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/giggle_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action giggle + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Suppressed: smile 0.7 with Mouth_Press 0.303 (17 keys) fighting closed; tiny jaw pulses 0.12 (8 keys f9-26). Onset smile f1 -> press f3 -> squint/cheek f5 -> jaw f9. Nose-flare f27. Recovery to soft smile. |
| 3 | Naturalness | 9 | L/R asymmetric: Smile 0.7/0.62, Squint 0.5/0.3 (one eye crinkles harder), Cheek 0.4/0.32. Nostril delta 0.03 (secondary, not identical). |
| 4 | Facial aliveness | 9 | Lip-suppression component present (the fight IS the giggle). Mouth stays small - not a wide laugh. Clavicle micro-bounce hook keyed. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Asymmetric squint between eyes (0.5 vs 0.3); blink f39. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Jaw small, cross-mesh followers driven; clavicle hook authorized; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Suppression + asymmetric crinkle both confirmed.
