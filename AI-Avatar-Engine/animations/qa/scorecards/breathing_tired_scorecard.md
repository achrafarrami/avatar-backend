# QA Scorecard — breathing_tired

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 7.0s, loop=true
- **Evidence:** previews/breathing_tired/ (mp4, strip, stills, meta.json), qa/reports/breathing_tired_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). inspect METRONOME r=0.71 @0.50s ADJUDICATED encoder: 0.50s=15f=GOP, NOT the breath — Spine02 shows slow irregular cycles (gaps 20,8,18,8,34,34,30,15,21,14,8) with sigh-hitches, no 0.50s motion cycle.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | chest/clavicle rise is the breath; torso stays balanced, no drift. |
| 2 | Timing & spacing | 9 | heavy tired breathing: slow cycles with catch-breath hitches (8f gaps = the sigh), Spine01/02+Head+Neck; L/R clavicle offset; eased. |
| 3 | Naturalness | 9 | breath rhythm organic (irregular gaps, not a pure sine); real breath slow+irregular (Spine02 long cycles ~34f with catch-breaths/hitches at 8f gaps) — distinct heavy-tired rhythm. |
| 4 | Facial aliveness | N/A | body clip — face neutral. |
| 5 | Hand & finger life | N/A | fingers not in this clip's bone set. |
| 6 | Eye behavior | N/A | eyes not driven. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
