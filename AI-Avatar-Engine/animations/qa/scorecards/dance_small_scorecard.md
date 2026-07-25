# QA Scorecard — dance_small

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 2 (targeted re-check of dims 2+3 after rework — SPECIAL JUDGMENT CALL)
- **Duration/loop:** 4.0s (121f, 120bpm, 15f/beat, 8 beats), loop=true
- **Evidence:** previews/dance_small/ (mp4, strip.png read, stills, meta.json); qa/reports/dance_small_inspection.png + _metrics.json (re-run); qa/reports/curve_audit_body_loco.json (re-run); bone-track probe R2 (hip locX + hip yaw extrema/frames/seam).
- **Automated flags (inspect_clip) R2:** METRONOME (moderate) autocorr r=0.596 @ 1.00s — STRONG cleared, below the r<0.7 target. Residual 1.00s/2-beat signal is the preserved plant rhythm, not the defect.
- **Curve audit R2:** findings=0; loop seam hip locX + hip yaw value_diff=0.0 tangent_diff=0.0.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Weight rocks side-to-side on the hips, low-guard arms; balance reads. (Unchanged R1.) |
| 2 | Timing & spacing | **9** | FIXED. Hip-rock + hip-yaw extrema now land at f19/28/50/59/79/87/108 — OFF the 15f grid (grid = 16/31/46/61/76/91/106), ±3-4f jitter. inspect autocorr dropped 0.85@0.5s → 0.596@1.0s (the tell moved to the legit 2-beat plant rhythm). No longer quantized. |
| 3 | Naturalness | **9** | FIXED. Hip lateral rock per-beat amplitude now VARIES: 3.00/2.55/3.30/2.34/3.15/3.60/2.76/2.16 (range 0.72–1.2× nominal); beat 6 = 3.60 = 1.2× emphasis present. Hip yaw re-authored with matching per-beat variation (magnitudes 2.16–3.6°, off-grid extrema). Strip confirms varied lean amplitudes frame-to-frame. Shoulders (beats 3/7) + offset head bob preserved untouched. |
| 4 | Facial aliveness | N/A | body clip — runtime facial owns. |
| 5 | Hand & finger life | 9 | Low-guard arms ride the bounce; finger snaps optional. (Unchanged R1.) |
| 6 | Eye behavior | N/A | runtime gaze/blink owns. |
| 7 | Loop seamlessness | 9 | Curve seam value+tangent = 0.0 (hip locX + yaw); strip f001 pose == f121 pose. Beat 1 preserved. |
| 8 | Technical | 9 | Bezier, no forbidden keys, 30fps, naming clean. (Unchanged R1.) |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9. Round-1 REWORK (dims 2=7, 3=6) resolved.

**RESOLUTION:** Root cause (lead groove curves used constant-amplitude `_beats()` while per-beat variation was wired only to secondary elements) is fixed. Re-check confirms: (1) hip-rock amplitudes now span 0.72–1.2× with the specified beat-6 emphasis; (2) hip-rock + yaw peaks are off the 15f grid (±3-4f jitter); (3) hip yaw carries matching per-beat variation; (4) inspect METRONOME dropped STRONG→moderate, r 0.85→0.596 (< 0.7 target), the residual being the legitimately-preserved plant rhythm; (5) curve audit findings=0 with a numerically perfect seam; (6) the strip reads as a varied human groove (lean amplitude differs frame-to-frame) with f001==f121. Shoulder alternation (beats 3/7) and offset head bob preserved. No residual metronomic tell.
