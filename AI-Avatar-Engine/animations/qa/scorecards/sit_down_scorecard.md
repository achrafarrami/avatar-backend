# QA Scorecard — sit_down

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.5s (46f), loop=false
- **Evidence:** previews/sit_down/ (mp4, strip, stills, meta.json); qa/reports/sit_down_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; bone-track probe (hipZ descent profile + end-pose match to sit_idle).
- **Automated flags (inspect_clip):** 0 flags; informational one-shot note (wrap 2.31, expected).
- **Curve audit:** findings=0 — bezier, BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Hips reach back+down; descent controlled onto sit bones; feet planted (LfootY settles to -0.21 and holds). Not a plop. |
| 2 | Timing & spacing | 9 | Descent is ECCENTRIC — decelerates into contact: hipZ deltas taper (~-0.03/f early f6-14 → ~-0.01/f near contact f19-22), then a small settle rise 0.46→0.48 (weight settling onto seat). Not constant-speed (no elderly-collapse). |
| 3 | Naturalness | 9 | Reverse-but-not-mirrored of stand_up (different descent profile); optional hand-reach-back hint keyed. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Arm/finger chains keyed for the settle. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | N/A | one-shot; **end pose matches sit_idle f0** (hipZ 0.48) — pose-contract to the seated hold verified. |
| 8 | Technical | 9 | Bezier, no forbidden keys, end-pose contract to sit_idle numerically met (0.48), 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Eccentric decelerating descent (not a controlled fall), soft contact compression, weight settles onto sit bones, and the end pose lands exactly on sit_idle's seated hold (0.48) — the sit_down→sit_idle seam is clean.
