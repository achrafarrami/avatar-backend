# QA Scorecard — lean_right

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.2s (37f), loop=false
- **Evidence:** previews/lean_right/ (mp4, strip, stills, meta.json); qa/reports/lean_right_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json.
- **Automated flags (inspect_clip):** NEARLY STATIC (energy 0.102/0.250). **Body-framing false-positive per ruling #2.**
- **Curve audit:** findings=0 — no byte-mirror; root/pelvis/spine/legs/neck+head keyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight pours onto right leg, right hip juts, left foot lightens; counter-balanced holdable pose. |
| 2 | Timing & spacing | 9 | Eased pour + overshoot settle; distinct rhythm from lean_left (acorr -0.167 vs none). |
| 3 | Naturalness | 9 | **NOT a byte-mirror of lean_left:** 10% less hip jut per spec, confirmed by lower energy (mean 0.102 vs lean_left 0.132) and fresh timing; curve auditor clears byte-mirror. Shoulder/head counter-tilt keyed. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Left arm swing-space bend; fingers keyed. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | N/A | one-shot; holdable end pose. |
| 8 | Technical | 9 | Hip owns jut, counter-tilt keyed, bezier, no forbidden/mirror keys, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Weighted lean with counter-tilt; byte-mirror ruled out (10% less jut = measurably lower energy, distinct timing, auditor clears). NEARLY STATIC is the ruling-#2 held-pose false-positive.
