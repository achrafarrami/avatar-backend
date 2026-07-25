# QA Scorecard — idle_01

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 10s, loop=true
- **Evidence:** previews/idle_01/ (mp4, strip, stills, meta.json), qa/reports/idle_01_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). I-frame comb absent here; motion carried by Head (100 keys) + Spine02 (83 keys).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | balanced upright stance throughout (strip); hips centered over feet, no uncompensated lean; Hip shifts irregular (gaps 60,50,6,12,12,12,8,70,40,30). |
| 2 | Timing & spacing | 9 | Waist sway ~19f, Head micro 2-4f, Spine02 ~5f — layered multi-rate, eased. |
| 3 | Naturalness | 9 | no byte-mirror: neutral arm pose is bilaterally symmetric (correct) but animated sway asymmetric (Upperarm[1] L 0.016-0.020 vs R 0.018-0.022, different centers). L/R clavicle share frame schedule (natural bilateral breathing). |
| 4 | Facial aliveness | N/A | body clip — face neutral (follower meshes only). |
| 5 | Hand & finger life | 9 | fingers micro-curl; worst static gap 50f (1.7s) L_Index1 — within 2s bar. |
| 6 | Eye behavior | N/A | eyes not driven (idle) — follower meshes only. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3 value+tangent, all channels). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

**Polish notes (non-blocking, optional future pass):**
- clav L/R identical frame schedule — see note

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
