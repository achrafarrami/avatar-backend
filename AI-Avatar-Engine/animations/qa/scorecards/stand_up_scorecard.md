# QA Scorecard — stand_up

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.5s (46f), loop=false
- **Evidence:** previews/stand_up/ (mp4, strip, stills, meta.json); qa/reports/stand_up_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; bone-track probe (hipZ rise + foot Z/Y planted-check — verifies the fixed 45cm double-count bug).
- **Automated flags (inspect_clip):** 0 flags; informational one-shot note (wrap 2.32 = seated→standing, expected).
- **Curve audit:** findings=0 — bezier, BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Hip Z rises ONCE 0.48→0.93 (seated→standing, ~45cm) — no double-count jump. Feet stay planted: LfootZ 0.06→0.12 max (small weight-shift lift) →0.05, LfootY drifts only as weight comes over the feet then settles. Nose-over-toes weight-forward phase f0-8 (hip holds 0.48 while spine flexes). |
| 2 | Timing & spacing | 9 | Eased rise f9-24; 5% overshoot past vertical (hipZ 0.94 at f29-30) then settle to 0.93 f31+. Antic→drive→overshoot→settle present. |
| 3 | Naturalness | 9 | Spine unrolls bottom-up (pelvis→lumbar→chest→head keyed in that order); arms swing back-to-front for momentum. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Arm swing + optional thigh-press hint keyed; fingers alive. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | N/A | one-shot; idle-compatible end hold. |
| 8 | Technical | 9 | Single clean hip rise (the 45cm double-counted-hip bug is NOT present — probe confirms one monotonic 0.48→0.93 rise, feet near floor throughout); bezier/fps/naming clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Weight-forward commit + bottom-up spine unroll + overshoot-settle all present; feet planted through the rise; the author's fixed double-count-hip bug is verified absent (single 45cm rise, no skate).
