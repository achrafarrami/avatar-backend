# QA Scorecard — head_micro

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 8s, loop=true
- **Evidence:** previews/head_micro/ (mp4, strip, stills, meta.json), qa/reports/head_micro_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | head-only micro layer. |
| 2 | Timing & spacing | 9 | continuous micro head drift/settle over 240f (Head+NeckTwist01), non-uniform; eased. |
| 3 | Naturalness | 9 | aperiodic micro-motion, no mechanical cycle. |
| 4 | Facial aliveness | N/A | neutral face. |
| 5 | Hand & finger life | N/A | head clip. |
| 6 | Eye behavior | N/A | eyes follower-only. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. Head+NeckTwist01 only. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
