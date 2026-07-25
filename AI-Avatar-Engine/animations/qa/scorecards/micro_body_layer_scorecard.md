# QA Scorecard — micro_body_layer

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 12s, loop=true
- **Evidence:** previews/micro_body_layer/ (mp4, strip, stills, meta.json), qa/reports/micro_body_layer_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). ADDITIVE bones-only layer. inspect I-FRAME GRID COMB 23/25 @15f = encoder, adjudicated. Head/Neck EXCLUDED by design (head_micro owns head) — NOT scored as 'frozen face' per lead ruling.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | sub-degree pelvis weight-micro with planted-feet counter: Hip + Spine01/02 + Thigh keys (the measured K_LAT counter). Balanced, no drift (strip). |
| 2 | Timing & spacing | 9 | non-periodic micro-event schedule across 12s; eased. |
| 3 | Naturalness | 9 | aperiodic; animated micro-sway asymmetric L/R; no byte-mirror. |
| 4 | Facial aliveness | N/A | additive body layer — head/neck excluded by design, not a face clip. |
| 5 | Hand & finger life | 9 | finger micro-motion present (all finger bones keyed), no static >2s. |
| 6 | Eye behavior | N/A | no eyes in this layer. |
| 7 | Loop seamlessness | 9 | additive curves zero at seam (<1e-3). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. 37 bones, Head/NeckTwist correctly ABSENT; thigh/spine = planted-feet counter for pelvis weight-micro. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
