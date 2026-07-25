# QA Scorecard — breathing_excited

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 2.6s, loop=true
- **Evidence:** previews/breathing_excited/ (mp4, strip, stills, meta.json), qa/reports/breathing_excited_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). inspect I-FRAME GRID COMB 5/5 @15f = encoder, adjudicated.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | chest/clavicle rise is the breath; torso stays balanced, no drift. |
| 2 | Timing & spacing | 9 | fast shallow breaths: Spine02 phases ~12-19f (quick onset f5), Head+clavicles engaged; L/R clavicle offset (L f6 vs R f8); eased, over-energized rhythm fits 'excited'. |
| 3 | Naturalness | 9 | breath rhythm organic (irregular gaps, not a pure sine); real breath period ~0.6s (Spine02 phases ~17f) — fast shallow, distinct. |
| 4 | Facial aliveness | N/A | body clip — face neutral. |
| 5 | Hand & finger life | N/A | fingers not in this clip's bone set. |
| 6 | Eye behavior | N/A | eyes not driven. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
