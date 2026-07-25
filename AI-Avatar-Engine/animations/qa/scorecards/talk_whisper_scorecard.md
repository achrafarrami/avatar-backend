# QA Scorecard — talk_whisper

- **Reviewer:** qa
- **Date:** 2026-07-25
- **Review round:** 1 (lip-sync Tier-2 batch, PERC_LOSSLESS+gopsize250)
- **Duration/loop:** 6s
- **Evidence:** previews/talk_whisper/ (mp4, strip, stills, meta.json), qa/reports/talk_whisper_inspection.png + _metrics.json (inspect_clip: 0 flags), qa/reports/curve_audit_lipsync.json (jaw rhythm/overlap, viseme set, blink schedule, seams).
- **Note:** Non-phonemic gibberish speech by design — rhythm/coarticulation/character judged, not lip-reading.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | upper-layer clip; torso stays balanced, speech-coupled Spine/Waist emphasis only (base idle owns stance). |
| 2 | Timing & spacing | 9 | non-metronomic: interval CV=0.82 (incl. pauses), within-phrase syllables varied; pause structure present (long jaw gaps + breath) — NOT a flat flap. |
| 3 | Naturalness | 9 | jaw coarticulation overlap = 17% of peak within-phrase (jaw does NOT fully close between adjacent syllables), closes to ~0 only at phrase boundaries. minimal jaw + Mouth_Pucker lip-shaping + glancing gaze — conspiratorial whisper (strip verified perceptible). |
| 4 | Facial aliveness | 9 | expressive speech: jaw amp 0.040 + visemes + brow/mouth accents; distinct per-clip character. |
| 5 | Hand & finger life | N/A | layer contract — fingers unkeyed, base idle owns them at runtime. |
| 6 | Eye behavior | 9 | phrase-boundary baked blinks landing in jaw pause gaps; 1-frame L/R wink-fix offset holds (L peak 1.0 / R ~0.99). Gaze owned by base idle. |
| 7 | Loop seamlessness | 9 | seam vdiff=0.0000 tdiff=0.0000 (all channels). |
| 8 | Technical | 9 | Curve audit (curve_audit_lipsync.json): no forbidden bones, no linear rotation, no range violations; 30fps. Layer contract HELD: fingers + eye-gaze bones UNKEYED (base idle owns them); Head/Neck/Spine01-02/Clavicle/Waist keyed for speech-coupled head emphasis + breath (owned behavior). minor: Nose_Nostril_Dilate_L==R identical (bilateral flare, sub-perceptual max <=0.11; not the eyelid fast-reject) — polish: add a few % L/R offset for consistency with the clips that vary it. |

**Aggregate:** min applicable score = 9/10

**Polish note (non-blocking):** minor: Nose_Nostril_Dilate_L==R identical (bilateral flare, sub-perceptual max <=0.11; not the eyelid fast-reject) — polish: add a few % L/R offset for consistency with the clips that vary it.

## Verdict

**SHIP** — all applicable dimensions >= 9. N/A dimensions per upper-layer contract (fingers/gaze/stance owned by base idle at runtime).
