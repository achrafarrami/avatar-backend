# QA Scorecard — turn_right

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.0s (31f), loop=false
- **Evidence:** previews/turn_right/ (mp4, strip, stills, meta.json); qa/reports/turn_right_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; bone-track probe (foot XY vs turn_left for byte-mirror check).
- **Automated flags (inspect_clip):** 0 flags; informational one-shot note (wrap 2.14, expected).
- **Curve audit:** findings=0 — no byte-mirror detected; bezier, Eye+head slots keyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight passes R→L→balanced; right foot steps out (footX -0.08→-0.12, Y dip -0.07) and pivots through; idle-compatible end. |
| 2 | Timing & spacing | 9 | Step-driven eased; foot plants+pivots. |
| 3 | Naturalness | 9 | **NOT a byte-mirror of turn_left:** foot step lands ~1f later and the unloaded-foot Y-dip holds a frame longer (turnR footY -0.07 spans f6-7 vs turnL's f6), and mean energy differs (0.573 vs turn_left 0.600). Fresh timing per spec. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Arm+finger counter-swing keyed. |
| 6 | Eye behavior | 9 | Gaze leads (Eye slot keyed), head follows before body completes. |
| 7 | Loop seamlessness | N/A | one-shot; idle-compatible hold. |
| 8 | Technical | 9 | Bezier, no forbidden/mirror keys, 30fps, naming clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Byte-mirror ruled out by both the curve auditor and the foot-path probe (~1f step offset, different weight rhythm and energy). Gaze-lead + idle-compatible exit hold.
