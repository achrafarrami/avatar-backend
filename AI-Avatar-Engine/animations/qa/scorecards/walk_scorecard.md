# QA Scorecard — walk

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch)
- **Duration/loop:** 1.2s (37f, 36f cycle), loop=true
- **Evidence:** previews/walk/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/walk_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json (action walk, 195 fcurves + followers); bone-track probe (hipZ/footZ/footY over cycle).
- **Automated flags (inspect_clip):** 0 flags (energy mean 0.598 / max 0.852).
- **Curve audit:** findings=0 — bezier limbs, BoneRoot unkeyed (in-place per ruling #1), Hip owns bob, no twist/identity keys, 30fps, naming==id, loop seam value+tangent = 0.00000.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Hip Z bobs 0.91→0.94 (~3cm): down f3-7 (0.91), up f11-16 (0.94), repeat f21-25/f29-34 — matches beat contact/down/passing/up. Weight readable, feet alternate stance. |
| 2 | Timing & spacing | 9 | Two eased bob cycles; foot roll heel→toe (footZ L rises to 0.27 f20, plants 0.05); bezier throughout, no linear ramps. |
| 3 | Naturalness | 9 | L/R not mirror-identical: L foot peak Z 0.27 vs R 0.25; foot phase opposed (L up while R planted). Pelvis counter-rotation keyed. |
| 4 | Facial aliveness | N/A | body clip — runtime facial layer owns face (follower meshes neutral). |
| 5 | Hand & finger life | 9 | Full arm+wrist+finger chains keyed (195 fcurves), arm swing opposes legs; no static >2s. |
| 6 | Eye behavior | N/A | eyes not driven (runtime gaze/blink scheduler composites). |
| 7 | Loop seamlessness | 9 | Curve seam value_diff+tangent_diff = 0.00000 all channels; hip returns to loop-start Z (0.93). |
| 8 | Technical | 9 | In-place authoring correct (ruling #1); stance-foot treadmill slide cancels against optional runtime root curve; bezier/fps/naming clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. In-place cycle (BoneRoot unkeyed, hip zero-net-drift) is correct per lead ruling #1; the stance-foot local slide is the intended treadmill motion the runtime forward-curve cancels, not a skate. Loop seam numerically perfect. N/A dims per anchor convention (runtime facial/gaze layers).
