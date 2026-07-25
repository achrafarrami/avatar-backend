# QA Scorecard — scratch_head

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 2.5s (76f), loop=false
- **Evidence:** previews/scratch_head/ (mp4, strip, stills, meta.json); qa/reports/scratch_head_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (152 fcurves + head/eye/brow followers).
- **Automated flags (inspect_clip):** 0 flags (energy 0.476 / max 2.413; acorr 0.264 @ 1.0s = the scratch bursts, irregular).
- **Curve audit:** findings=0 — bezier, finger + head + Eye + Toon_Eyebrows (facial hook) slots keyed, no forbidden keys, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Left shoulder rises 1deg as counterbalance to the raised right arm; upright weight holds. |
| 2 | Timing & spacing | 9 | Arm wraps up f0-14 (elbow high); THREE scratch oscillations f14-32 with IRREGULAR spacing (6,5,7f), then relaxed-drag drop, head re-levels last. Not even spacing. |
| 3 | Naturalness | 9 | Scratches vary in spacing; head yields 1deg per stroke (not static); counterbalancing shoulder. |
| 4 | Facial aliveness | 9 | Sheepish half-smile + gaze-aside facial hook keyed (Toon_Eyebrows/Eye slots) — face participates. |
| 5 | Hand & finger life | 9 | FINGER-led scratch (fingers flex/extend ~60% of the motion, wrist 30%, arm 10%) — not a shoulder-saw with rigid fingers. |
| 6 | Eye behavior | 9 | Gaze aside (sheepish) keyed via the facial hook. |
| 7 | Loop seamlessness | N/A | one-shot; returns to neutral. |
| 8 | Technical | 9 | Bezier, no forbidden keys, cross-mesh followers driven, 30fps. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. **Ruling #3 applied:** the hand reaches the back-CROWN (rig cannot abduct out-to-side-and-up to the forehead) — verified rig limit, clip-free, not a defect. Finger-led scratch with irregular 6/5/7f spacing, head yields per stroke, embarrassed-lite facial hook present.
