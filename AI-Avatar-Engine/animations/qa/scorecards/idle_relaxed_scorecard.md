# QA Scorecard — idle_relaxed

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 12s, loop=true
- **Evidence:** previews/idle_relaxed/ (mp4, strip, stills, meta.json), qa/reports/idle_relaxed_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). inspect METRONOME r=0.61 @0.50s ADJUDICATED encoder: 0.50s=15f=GOP period (grid-comb 77%); the authored composite is non-metronomic — Head gaps 2-4f irregular, Hip gaps 175/17/16/82/40/30, Waist ~22f. No real motion cycle at 0.50s.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | relaxed weight-shifted stance, balanced; Hip weight-shifts irregular; no uncompensated lean. |
| 2 | Timing & spacing | 9 | Waist sway ~22f, Head irregular micro 2-4f, Hip irregular — layered; eased. Composite non-metronomic despite the 0.50s autocorr (encoder). |
| 3 | Naturalness | 9 | no harmful byte-mirror (symmetric rest pose; animated Upperarm/Forearm sway asymmetric L vs R). Clavicle shares L/R schedule = bilateral breathing. |
| 4 | Facial aliveness | N/A | body clip — face neutral (follower meshes only). |
| 5 | Hand & finger life | 9 | fingers micro-curl; worst gap 60f (2.0s) L_Index1 — at the threshold, not over. |
| 6 | Eye behavior | N/A | eyes not driven (idle) — follower meshes only. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3 value+tangent, all channels). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

**Polish notes (non-blocking, optional future pass):**
- waist ~22f sway is near-uniform (polish: jitter +-2-3f)
- L_Index1 static gap = exactly 60f (2.0s), right at the >2s bar (polish: add one micro-key)
- L/R clavicle identical frame schedule (polish: offset R a few frames)

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
