# QA Scorecard — celebrate_big

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 3.0s (91f), loop=false
- **Evidence:** previews/celebrate_big/ (mp4, strip, stills, meta.json); qa/reports/celebrate_big_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (199 fcurves + big_smile/breathing_excited hooks); bone-track probe (hipZ/footZ jump + L/R hand pump asymmetry).
- **Automated flags (inspect_clip):** 0 flags (energy 0.467 / max 2.412).
- **Curve audit:** findings=0 — full skeleton + big_smile + breathing_excited hooks keyed; BoneRoot unkeyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Real crouch compression f1-7 (hipZ 0.925→0.805, -12cm) BEFORE launch; genuine airborne jump (hipZ apex 1.125 = +32cm, LfootZ 0.25 = feet 25cm off floor); 2-STAGE landing absorb (f16 0.883 → f17 0.805 impact compression → rebound f18+). Not floaty, not bone-jarring. |
| 2 | Timing & spacing | 9 | crouch→launch→flight→land→pump→settle, each eased with antic/overshoot; recovery breath f60-90 (hands slowly lower to rest 0.894) sells the wind-down. |
| 3 | Naturalness | 9 | Two fist pumps DECAYING and OFF-mirror: L peak 1.678 vs R 1.701 at apex, L 1.638 vs R 1.669 on the second pump — not mirror-identical; pumps decay in amplitude. |
| 4 | Facial aliveness | 9 | big_smile hook keyed through the celebration — face participates. |
| 5 | Hand & finger life | 9 | Arms punch overhead (full extension at apex), fists cocked in the crouch; finger chains keyed. |
| 6 | Eye behavior | N/A | runtime gaze/blink owns (head-back at launch keyed). |
| 7 | Loop seamlessness | N/A | one-shot; settles to idle-compatible standing hold (hipZ 0.925). |
| 8 | Technical | 9 | Real jump verified (feet leave floor, single clean flight arc), 2-stage absorb, bezier, no forbidden keys, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Hero clip: genuine crouch (-12cm) → airborne jump (+32cm, feet 25cm off ground) → 2-stage knee-absorb landing → decaying off-mirror fist pumps → visible recovery breath. big_smile + breathing_excited hooks present.
