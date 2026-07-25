# QA Scorecard - listening_interested

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_interested/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_interested_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_interested + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Engaged baseline brows +0.45/+0.392, lids +0.1 wide, lean-in Spine02 hook. Bigger nods (head 78 keys) incl double-nod; brow-flash event present (Brow 5 keys stepping). |
| 3 | Naturalness | 9 | Asymmetric brows 0.45/0.392, 0.32/0.279; nods varied size; no mirror. |
| 4 | Facial aliveness | 9 | Brow-flash 'something landed' beat present; baseline lift <0.25 (not perpetual surprise). Alive. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Gaze locked focus-grade; Eye_Wide 0.1 brightness; lids track. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Spine lean-in hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Lean-in hook, brow-flash, varied nods all present.
