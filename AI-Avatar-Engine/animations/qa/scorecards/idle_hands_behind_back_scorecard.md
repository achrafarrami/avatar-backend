# QA Scorecard — idle_hands_behind_back

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 12s, loop=true
- **Evidence:** previews/idle_hands_behind_back/ (mp4, strip, stills, meta.json), qa/reports/idle_hands_behind_back_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | planted balanced stance with FEET + ToeBase keyed (48 bones) — weight-shift counter at the base; chest open (hands-behind-back read), balanced (strip). |
| 2 | Timing & spacing | 9 | layered sway + subtle foot weight-shift counter; eased. |
| 3 | Naturalness | 9 | asymmetric animated sway; feet provide independent counter-motion; no byte-mirror. |
| 4 | Facial aliveness | N/A | body clip — face neutral (follower meshes only). |
| 5 | Hand & finger life | 9 | fingers keyed (hands clasped behind); no static >2s. |
| 6 | Eye behavior | N/A | eyes not driven (idle) — follower meshes only. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3 value+tangent, all channels). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
