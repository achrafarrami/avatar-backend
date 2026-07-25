# QA Scorecard - laugh

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 3.0s, loop=false
- **Evidence:** previews/laugh/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/laugh_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action laugh + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Jaw pulse train decaying 0.4 -> 0.15 at ~7f spacing with jitter (15 Jaw_Open keys f7-72); onset smile f1 -> cheek f3 -> squint f5 -> jaw f7. Head back+return keyed (18 head keys). Ends on residual soft smile, not neutral. |
| 3 | Naturalness | 9 | L/R asymmetric: Smile 0.88/0.8, Cheek 0.8/0.73, Squint 0.7/0.602. Nose_Nostril near-sym (delta 0.02, identical=false - acceptable secondary). Clavicle body-hook keyed (authorized laugh-shake). |
| 4 | Facial aliveness | 9 | Strip confirms eyes progressively squeeze through pulses (f37-49 clearly narrowed) - NOT psycho-laugh. Teeth reveal on each jaw open. Recovery breath f70-90, ends soft smile. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Eye_Squint reaches 0.7 by pulse 2; blink pulses (10 keys) within laugh. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Clavicle/head/jaw hooks authorized for facial; cross-mesh Tongue+Teeth follow jaw driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Body-layer hooks present in metadata. Ends on soft smile ~0.4 per spec.
