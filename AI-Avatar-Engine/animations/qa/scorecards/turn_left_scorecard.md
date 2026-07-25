# QA Scorecard — turn_left

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.0s (31f), loop=false
- **Evidence:** previews/turn_left/ (mp4, strip, stills, meta.json); qa/reports/turn_left_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (action + Eye/head follower slots); bone-track probe (foot XY step path).
- **Automated flags (inspect_clip):** 0 flags; informational one-shot note (wrap 2.23 = end-hold, expected).
- **Curve audit:** findings=0 — bezier, BoneRoot unkeyed, Eye + head slots keyed (gaze lead), no byte-mirror, 30fps, naming clean.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight passes L→R→balanced; left foot steps out (footX 0.08→0.12 f5-7, Y dips -0.07 = step-out) then body pivots through; ends balanced idle-compatible. |
| 2 | Timing & spacing | 9 | Step-driven, eased; foot plants then pivots (not ice-skate); settle f22-30. |
| 3 | Naturalness | 9 | Not a rigid unit-rotation — foot articulates the step+pivot; arms counter-swing keyed. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Arm+finger chains keyed, counter-swing alive. |
| 6 | Eye behavior | 9 | Gaze LEADS: Eye slot keyed, eyes saccade f0, head follows f2-8 arriving before the body completes (f22) — chain order correct. |
| 7 | Loop seamlessness | N/A | one-shot; ends on idle_01-compatible hold (runtime crossfades). |
| 8 | Technical | 9 | Bezier, no forbidden keys, gaze-lead layering correct, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Gaze-leads-body confirmed, step+pivot articulated (not on-ice), idle-compatible exit.
