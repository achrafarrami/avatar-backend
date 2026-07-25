# QA Scorecard — check_watch

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 2.2s (67f), loop=false
- **Evidence:** previews/check_watch/ (mp4, strip, stills, meta.json); qa/reports/check_watch_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (148 fcurves + head/eye/brow followers).
- **Automated flags (inspect_clip):** 0 flags (energy 0.603 / max 2.613).
- **Curve audit:** findings=0 — bezier, arms + head + Eye (gaze drop) + brow micro slots keyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Upright; head pitches down 8deg to read; forearm rotates up-and-in toward the ribs — natural reading posture. |
| 2 | Timing & spacing | 9 | Forearm supinates up f0-10, gaze drops f4 (4f AFTER the arm starts — you look once it's moving), reading beat f14-40, then arm+gaze return TOGETHER f40-58, micro nod at end. Eased. |
| 3 | Naturalness | 9 | Reading fixation shifts (2 tiny eye moves on the dial) — not a glance-at-nothing; optional sleeve-tap flagged. |
| 4 | Facial aliveness | 9 | Brow micro-knit 0.15 during reading (concentration) — face participates. |
| 5 | Hand & finger life | 9 | Wrist supination to present the watch face; fingers keyed; optional right-hand sleeve tap. |
| 6 | Eye behavior | 9 | Gaze drops to the wrist AFTER the arm moves (correct order), 2 fixation shifts while reading, gaze returns with the arm. Eyes lead within the return. |
| 7 | Loop seamlessness | N/A | one-shot; returns to front with a micro nod. |
| 8 | Technical | 9 | Bezier, no forbidden keys, cross-mesh gaze/brow followers driven, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Gaze drops after the arm begins (not before), genuine reading fixation shifts + brow micro-knit, head pitched while reading, arm and gaze return together. No glance-at-nothing.
