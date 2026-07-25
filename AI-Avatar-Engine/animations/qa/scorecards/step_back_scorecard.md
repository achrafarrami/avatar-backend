# QA Scorecard — step_back

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.0s (31f), loop=false
- **Evidence:** previews/step_back/ (mp4, strip, stills, meta.json); qa/reports/step_back_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; gaze-key value probe.
- **Automated flags (inspect_clip):** NEARLY STATIC (energy 0.231/0.461). **Body-framing false-positive per ruling #2 — the step_back retreat is gentle in whole-frame pixels; triaged via curves.**
- **Curve audit:** findings=0 on bone channels. 8 "IDENTICAL L/R CURVES" notices on the Eye follower slots (Eye_L_Look_L==Eye_L_Look_R, Eye_R_Look_L==Eye_R_Look_R) — **adjudicated benign, see call.**

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight rocks back over heels f0-4 (anticipation) BEFORE the foot moves; right foot steps back, left closes; ends balanced. Full skeleton keyed. |
| 2 | Timing & spacing | 9 | Anticipation → step → settle; arms rise slightly outward for balance then settle; eased. |
| 3 | Naturalness | 9 | Asymmetric arm balance; step + close not mechanical. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Arm+finger chains keyed for the balance gesture. |
| 6 | Eye behavior | 9 | Gaze HOLDS on target while the body retreats: horizontal gaze keys flat 0.0 (eyes stay forward), with a subtle authored down-glance that is ASYMMETRIC (Eye_L_Look_Down peaks 0.060 vs Eye_R_Look_Down 0.0577). Correct per beat "head STAYS on target." |
| 7 | Loop seamlessness | N/A | one-shot; idle-compatible hold. |
| 8 | Technical | 9 | Bezier, no forbidden keys, cross-mesh gaze followers driven, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9.

**CALL (identical-curve notices):** NOT the rubric fast-reject (that is identical L/R *eyelid*/Eye_Blink curves). These are horizontal *gaze-direction* keys, and same-eye opposite-direction (Look_L vs Look_R on the same eye) — probed and confirmed **all flat 0.0** (gaze held straight ahead on target, correct for stepping back while keeping eyes on the thing). Actual gaze life is the vertical down-glance, which IS asymmetric. Benign co-keyed followers, same class shipped idles carry. NEARLY STATIC adjudicated as ruling-#2 body-framing false-positive.
