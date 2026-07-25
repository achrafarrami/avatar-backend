# QA Scorecard — run

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 0.8s (25f, 24f cycle), loop=true
- **Evidence:** previews/run/ (mp4, strip, stills, meta.json); qa/reports/run_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; bone-track probe (hipZ/footZ over cycle).
- **Automated flags (inspect_clip):** 0 flags (energy mean 1.018 / max 1.363 — highest of batch, vigorous).
- **Curve audit:** findings=0 — bezier limbs, BoneRoot unkeyed, no forbidden keys, 30fps, loop seam value+tangent = 0.00000.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Hip Z range 0.89→0.96 (~7cm, matches spec): sharp contact dips f3 (0.89) & f15 (0.89) = knee-absorb impact, apex f7/f18 (0.96). Impact absorbed over 2f, not stopped dead. |
| 2 | Timing & spacing | 9 | Eased dip-and-drive per stride; high knee lift (footZ to 0.69) with foot articulation; bezier. |
| 3 | Naturalness | 9 | Strides not byte-identical (foot Z peaks L 0.69 vs R 0.65); arm pump keyed opposed to legs. |
| 4 | Facial aliveness | N/A | body clip — runtime facial layer owns face. |
| 5 | Hand & finger life | 9 | Arms pump at elbow with soft-closed fists keyed; no static >2s. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns (residual 1cm head bounce keyed for stabilization). |
| 7 | Loop seamlessness | 9 | Curve seam value+tangent = 0.00000; hip returns to loop-start. |
| 8 | Technical | 9 | Airborne phase present (both feet elevated at push-off transitions; hip apex 0.96 = flight); in-place authoring correct; bezier/fps/naming clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Genuine run (7cm hip range with 2f contact knee-absorb + flight apex, high knee lift), not a fast walk. In-place per ruling #1, loop seam numerically perfect.
