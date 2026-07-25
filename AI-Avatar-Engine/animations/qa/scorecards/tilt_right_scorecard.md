# QA Scorecard — tilt_right

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 1.0s, loop=false
- **Evidence:** previews/tilt_right/ (mp4, strip, stills, meta.json), qa/reports/tilt_right_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** one-shot end-holding tilt (crossfade-out model): inspect end!=start diff and audit head-quat seam diff are the HELD tilt pose, expected — NOT a loop-seam defect.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | head-only clip. |
| 2 | Timing & spacing | 9 | ease-in to held tilt over ~30f (Head+NeckTwist01+NeckTwist02); no snap. |
| 3 | Naturalness | 9 | natural head tilt with neck follow-through; ends holding. |
| 4 | Facial aliveness | N/A | neutral face. |
| 5 | Hand & finger life | N/A | head clip. |
| 6 | Eye behavior | N/A | eyes follower-only (small look offset accompanies the tilt). |
| 7 | Loop seamlessness | N/A | one-shot end-hold — not a loop. |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. Head/NeckTwist01/NeckTwist02. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
