# QA Scorecard — lean_left

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.2s (37f), loop=false
- **Evidence:** previews/lean_left/ (mp4, strip, stills, meta.json); qa/reports/lean_left_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json.
- **Automated flags (inspect_clip):** NEARLY STATIC (energy 0.132/0.366). **Body-framing false-positive per ruling #2 (a lean holds its pose — low whole-frame motion by design).**
- **Curve audit:** findings=0 — root/pelvis/spine/legs/neck+head keyed, BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight pours onto LEFT leg f0-14, left hip juts out (root_pelvis keyed — the jut IS the pose), right foot goes light. Counter-balanced, holdable end. |
| 2 | Timing & spacing | 9 | Eased pour with 1 overshoot settle bounce; holdable end pose. |
| 3 | Naturalness | 9 | Shoulder line counter-tilts (head counters ~70% of the lean, keyed on neck+head) — not a level-hip spine-only lean. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Right arm gains soft swing-space bend; fingers keyed. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | N/A | one-shot; holdable end pose. |
| 8 | Technical | 9 | Hip owns the jut (correct), counter-tilt on neck/head, bezier, no forbidden keys, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. The hip jut + shoulder/head counter-tilt is the correct weighted lean (not spine-only with level hips). NEARLY STATIC adjudicated as ruling-#2 body-framing false-positive (a held lean is legitimately low-motion).
