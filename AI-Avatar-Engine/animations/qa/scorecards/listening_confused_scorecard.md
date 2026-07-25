# QA Scorecard - listening_confused

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_confused/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_confused_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_confused + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Intermittent asymmetric brow pinch: Brow_Drop_L 0.45 + Brow_Raise_Outer_R 0.38 (opposed) with deeper spike (10 keys). One-sided Eye_Squint_L 0.315. Mouth corner tug (Mouth_L 0.15). Head tilt-drift hook (65 keys). |
| 3 | Naturalness | 9 | Opposed asymmetric brows throughout (never symmetric); one-sided squint; no mirror. |
| 4 | Facial aliveness | 9 | Spike beat present (loop not flat); gaze stays ON speaker (confused-but-listening, not thinking). Aborted near-nod read via head keys. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Gaze on speaker; one-sided squint rides each pinch. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Head tilt-drift hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Asymmetric brows + the deeper spike both present; gaze on speaker.
