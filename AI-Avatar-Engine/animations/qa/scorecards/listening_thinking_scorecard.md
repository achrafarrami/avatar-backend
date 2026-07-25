# QA Scorecard - listening_thinking

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_thinking/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_thinking_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_thinking + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Gaze on speaker then breaks up-left (Look_L 0.28 + Look_Up 0.24, 10 keys) - processing dwell - and RETURNS (re-engage is the acting). Brow furrow 0.2 during away-dwell, releases on return. Lip press/purse cycles. Slow nod hook (head 64 keys). |
| 3 | Naturalness | 9 | Asymmetric brows 0.2/0.176; two gaze-breaks of differing length; no mirror. |
| 4 | Facial aliveness | 9 | Gaze-away is up-LEFT (not center-up zombie); furrow does not persist after return. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Saccadic gaze break up-left with dwell then return; deliberate re-fixation. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Slow-nod hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. The gaze-break-and-RETURN (the acting beat) is present; up-left aversion correct.
