# QA Scorecard — adjust_glasses

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 2.0s (61f), loop=false
- **Evidence:** previews/adjust_glasses/ (mp4, strip, stills, meta.json); qa/reports/adjust_glasses_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (156 fcurves + Eye/head/brow followers).
- **Automated flags (inspect_clip):** 0 flags (energy 0.856 / max 3.825 — brisk arm raise).
- **Curve audit:** findings=0 — bezier, precision finger + head + Eye (blink hook) slots keyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Upright; head tips DOWN 2deg into the push then re-levels (glasses-wearer counter to the nod) — weight/head coupling correct. |
| 2 | Timing & spacing | 9 | Elbow leads the rise f0-10; micro push 1cm up-and-in over 3f; return f20-35 via a LOWER path than the approach (no retrace). Antic→contact→push→settle. |
| 3 | Naturalness | 9 | Approach and return paths differ; other (left) arm stays alive at side. |
| 4 | Facial aliveness | 9 | Brow/blink participate — eyes blink once at the push (Eye hook keyed). |
| 5 | Hand & finger life | 9 | Index+thumb form a precision pinch DURING the rise (not pre-formed at rest, not after arrival); fingers keyed. |
| 6 | Eye behavior | 9 | Blink at the push (hook); gaze stable otherwise. |
| 7 | Loop seamlessness | N/A | one-shot; returns to neutral. |
| 8 | Technical | 9 | Bezier, no forbidden keys, cross-mesh followers driven, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. **Ruling #3 applied:** the pinch lands on the TEMPLE (rig arm sweeps hand center-front; cannot reach the center bridge) — this is the verified rig limit targeting the nose-bridge point, clip-free, NOT a defect. Pinch forms during the rise, head counter-tips into the push, return path lowers (no retrace), blink hooked.
