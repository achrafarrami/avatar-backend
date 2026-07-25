# QA Scorecard — hands_in_pockets

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 2.0s (61f), loop=false
- **Evidence:** previews/hands_in_pockets/ (mp4, strip, stills, meta.json); qa/reports/hands_in_pockets_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (183 fcurves — both arms/hands/fingers/spine/legs).
- **Automated flags (inspect_clip):** 0 flags; informational one-shot note (wrap 1.04 = holdable end pose, expected).
- **Curve audit:** findings=0 — bezier, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight rocks back, shoulders drop 2deg, spine eases 1deg — the relaxed hands-in-pockets stance reads. |
| 2 | Timing & spacing | 9 | Staggered entry (RIGHT hand f0-12, LEFT f8-20 — not simultaneous), eased, elbows settle back; holdable end. |
| 3 | Naturalness | 9 | Asymmetric staggered timing; relaxed shoulder drop. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Full finger chains keyed; thumbs stay OUT hooked on the pocket edge (the readable silhouette detail), fingers form during the slide-in. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | N/A | one-shot; holdable end pose (pairs with hands_pockets_exit). |
| 8 | Technical | 9 | Bezier, no forbidden keys, 30fps. Wardrobe-dependency (pants geometry) flagged in metadata per beat. No hand-hip interpenetration in stills. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Staggered R-then-L entry, hooked thumbs preserved for silhouette, relaxed weight-back stance, holdable end pose. Wardrobe-dependency correctly flagged.
