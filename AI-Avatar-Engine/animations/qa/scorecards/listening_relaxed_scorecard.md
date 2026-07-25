# QA Scorecard - listening_relaxed

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 8.0s, loop=true
- **Evidence:** previews/listening_relaxed/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/listening_relaxed_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action listening_relaxed + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Irregular acknowledgment nods (head 73 keys) follow imagined speech beats, not a timer. Lips relaxed tiny part (Mouth_Drop_Lower 0.069, 41 keys). Fixation drift (eyes keyed every 8f). |
| 3 | Naturalness | 9 | Nod cadence irregular; blink L/R non-identical (52/49 keys); no metronome. |
| 4 | Facial aliveness | 9 | neutral_alive palette alive - mouth life present (41-key micro), lid tone breathes. Never static. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Gaze held on speaker with fixation micro-drift; baked blinks non-identical L/R. |
| 7 | Loop seamlessness | 9 | Loop seam CLEAN: worst value_diff=0.0000 AND tangent_diff=0.0000 across ALL slots (frame001==frame241). Event schedule non-clustered at seam. |
| 8 | Technical | 9 | Cross-mesh followers driven; head-nod hook authorized (<=3deg); naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Gaze stays on speaker; mouth life across full 8s.
