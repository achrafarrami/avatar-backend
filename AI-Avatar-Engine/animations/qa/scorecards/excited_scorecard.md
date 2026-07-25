# QA Scorecard - excited

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/excited/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/excited_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action excited + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Brows up fast 0.667 f1, Eye_Wide 0.516 f3, two-step smile (Smile_L 15 keys building to 0.9), jaw cracks 0.2 f7. Double head-nod hook (head keyed f7-25). Micro-tremor via Eye_Wide 20 keys. |
| 3 | Naturalness | 9 | L/R asymmetric: Brow_Inner 0.667/0.612, Eye_Wide 0.516/0.45, Smile 0.9/0.83. No mirror. |
| 4 | Facial aliveness | 9 | Over-energized read: tremor 0.03 on brows during hold (multi-key). Jaw component present (open-mouth excitement, not smug). Pairs with breathing_excited (hook noted). |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Eyes wide 0.5; blink f27; brows leap (muscle-speed, not ballistic). |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Double-nod + breathing_excited hooks noted; jaw+cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Two-step smile, jaw crack, and tremor all confirmed.
