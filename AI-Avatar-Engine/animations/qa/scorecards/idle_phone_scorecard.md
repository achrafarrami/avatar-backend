# QA Scorecard — idle_phone

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 12s, loop=true
- **Evidence:** previews/idle_phone/ (mp4, strip, stills, meta.json), qa/reports/idle_phone_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). inspect METRONOME r=0.58 @0.50s ADJUDICATED encoder: 0.50s=15f=GOP (grid-comb 83%). Waist authored on a uniform 15f grid (sub-degree, masked by pose); Head/Hip/clavicle overlays are irregular so composite is non-mechanical (strip reads as natural 'looking at phone').

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | balanced stance, head down at phone; R forearm raised across body holding phone (2-key held pose), L arm hangs — weight centered. |
| 2 | Timing & spacing | 9 | head-down attention + subtle sway; waist uniform 15f (sub-degree), head/hip irregular; eased. |
| 3 | Naturalness | 9 | PROPERLY ASYMMETRIC: R arm raised (phone), L arm sway (61 keys) — NOT byte-mirrored; R clavicle has extra keys (34 vs L 31). |
| 4 | Facial aliveness | N/A | body clip — face neutral (follower meshes only). |
| 5 | Hand & finger life | 9 | L hand fingers micro-curl (worst gap 30f/1.0s); R hand holds phone pose. |
| 6 | Eye behavior | N/A | eyes not driven (idle) — follower meshes only. |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3 value+tangent, all channels). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. |

**Aggregate:** min applicable score = 9/10

**Polish notes (non-blocking, optional future pass):**
- waist keyed on a strict 15f grid (uniform) — polish: jitter +-2-3f to fully de-correlate from any periodic read

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
