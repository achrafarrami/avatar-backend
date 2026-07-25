# QA Scorecard — idle_looking_around

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (body Tier-1 batch, PERC_LOSSLESS re-render)
- **Duration/loop:** 14s, loop=true
- **Evidence:** previews/idle_looking_around/ (mp4, strip, stills, meta.json), qa/reports/idle_looking_around_inspection.png + _metrics.json (inspect_clip: loop-aware + encoder/I-frame-comb discriminators), qa/reports/curve_audit_body.json (bone + shape-key channels, loop seams, L/R + finger analysis).
- **Note:** inspect NEARLY STATIC flag is EXPECTED per lead ruling (body-framed sub-degree 'sensed not seen' motion; REJECT only if visible as fidgeting). baked_blinks meta + 1-frame wink fix CONFIRMED.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | balanced stance while head scans; hips centered, no lean; Hip/Waist counter present. |
| 2 | Timing & spacing | 9 | head gaze scan: 142 Head keys, max gap 4f (continuously active), non-uniform spacing (2,2,4,4,1,3,4...); eased. |
| 3 | Naturalness | 9 | gaze-shift schedule irregular; animated body sway asymmetric; no byte-mirror. |
| 4 | Facial aliveness | N/A | body clip — face neutral aside from the scheduled blinks. |
| 5 | Hand & finger life | 9 | fingers periodic, no static >2s. |
| 6 | Eye behavior | 9 | 3 baked blinks (f41/f179/f330, ~4.5s rate — natural); WINK FIX holds: L closes f41 peak 1.0, R closes f42 peak 0.98 (1f offset, not identical/simultaneous). |
| 7 | Loop seamlessness | 9 | loop seam clean (<1e-3). |
| 8 | Technical | 9 | Curve audit clean (curve_audit_body.json): findings=0 — no forbidden BoneRoot/twist bones keyed (NeckTwist errata applied), no linear rotation, no range violations, 30fps, cross-mesh followers driven. baked_blinks meta present as expected. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. NEARLY STATIC / 0.50s-metronome inspect flags adjudicated as expected body-framing + encoder-GOP artifacts (see note), not authored defects. N/A dimensions marked per rubric (head-only/body-only/additive-layer clips; one-shot end-hold clips).
