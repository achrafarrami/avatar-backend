# QA Scorecard — stretch

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 3.5s (106f), loop=false
- **Evidence:** previews/stretch/ (mp4, strip, stills, meta.json); qa/reports/stretch_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json.
- **Automated flags (inspect_clip):** 0 flags (energy 0.235 mean / 1.048 max — a strong rise-to-peak-then-release profile).
- **Curve audit:** findings=0 — full skeleton + breathing_deep hook + Eye_Blink squeeze hook keyed; BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine extends into a back arch, heels may rise, weight carries up through the reach then settles below neutral on release. |
| 2 | Timing & spacing | 9 | Rise f0-20 → PEAK HOLD f20-50 (with isometric tremble keyed, 1-2f oscillation) → RELEASE f50-75 that collapses (drag+bounce), asymmetric with the rise. Energy peak 1.048 mid-clip confirms real extension, not a static hold. |
| 3 | Naturalness | 9 | Release is a collapse, not a reversed rise; shoulders overshoot BELOW neutral then settle; end more relaxed than start. acorr 0.334 @ 1.567s = the slow arch/hold, not repetition. |
| 4 | Facial aliveness | 9 | Eye squeeze hook keyed at peak (eyes screw shut at the stretch limit) — face participates. |
| 5 | Hand & finger life | 9 | Arms rise (interlaced-finger variant optional) then fall with drag/bounce; fingers keyed. |
| 6 | Eye behavior | 9 | Eye squeeze at peak + release; lids driven by the hook. |
| 7 | Loop seamlessness | N/A | one-shot; ends on a relaxed hold. |
| 8 | Technical | 9 | Breathing_deep exhale coupling on release, bezier, no forbidden keys, cross-mesh followers driven, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Real spine extension + isometric tremble at peak + exhale-coupled collapse with shoulders overshooting below neutral. Rise and release are asymmetric (collapse, not reverse). Energy profile (peak 1.048 then settle) confirms genuine effort.
