# QA Scorecard — talking_happy

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1
- **Evidence reviewed:** `previews/talking_happy/` (mp4, strip, stills, meta.json),
  `qa/reports/talking_happy_inspection.png`, `talking_happy_metrics.json`,
  `qa/reports/curve_audit_lipsync.json` (actions `talking_happy` + per-mesh slots)
- **Automated flags** (inspect_clip): none. Curve audit: no linear rotation, no
  never_animate hits, all loop seams 0.0/0.0. NeckTwist01 keyed (dim 8 ruling).

## Scores

| # | Dimension | Score | Evidence / justification |
|---|-----------|-------|--------------------------|
| 1 | Weight & balance | 9 | Upper-layer clip, rest-posed body per contract. Slightly richer spine involvement (Spine02 33 keys) supporting the lighter/more-frequent nods — plausible, seam-clean. |
| 2 | Timing & spacing | 9 | Viseme chain inherits talking_neutral ruleset; laugh-adjacent exhale lands as specced: single jaw pulse f159 (0.253 — clip max) decaying by f166, with Eye_Squint 0.32/0.29 — strip f161 shows the open-mouth laugh moment reading naturally. Head accents more frequent, smaller. |
| 3 | Naturalness | 9 | Smile L/R never identical (max delta 0.05); cheeks asymmetric 0.26 / 0.23; brow deltas 0.043; blink gaps non-uniform (f63/f147/f215); nod sizes vary. Autocorr r=0.20. Nostril L/R identical accepted (physiology). |
| 4 | Facial aliveness | 10 | The headline requirement — smile that BREATHES with speech — is verified in curves AND pixels: Mouth_Smile 40 keys oscillating 0.48 max -> 0.10 during rounded visemes with rebound (spec: reduce to 0.1, rebound), visible in sheet f109 (dipped) vs f130/f196 (full); cheeks constant per spec (2 keys, stable — not per-viseme); brows bright with 0.1 floor that never zeroes; squint fires only on the exhale beat. No rubber face, no flickering mood. This is the spec executed exactly. |
| 5 | Hand & finger life | N/A | Deliberately unkeyed — base idle layer owns fingers (lead ruling). No violation. |
| 6 | Eye behavior | 7 | Blink cadence and profile fine (phrase-aligned, close 3f/open 6-7f, blink-coupled eye-down). BUT TWO of three blinks carry the 2-frame inter-eye offset and both produce visible wink frames on the oversized toon eyes: blink 1 (L f63->66, R f65->68) — sheet f65 shows one eye fully open, other fully closed; blink 3 (L f215->218, R f217->220) — sheet/strip f218/f225 same artifact + lid-fold chunk on the trailing eye. Worst of the batch (2 of 3 blinks affected). |
| 7 | Loop seamlessness | 10 | All channels 0.0 value / 0.0 tangent seam diff; smile at consistent 0.1 dip value at both ends; tiles f238-240 vs f0-2 identical. Wrap ratio 1.09x median = noise. |
| 8 | Technical | 8 | Bezier, ranges legal (V_Explosive 0.88 punchy but <1.0; Mouth_Close 1.0 on bilabials is correct full closure), action name == clip id, 30fps, cross-mesh contract COMPLETE incl. Smile/Cheek/Squint driven on TearLine+EyeOcclusion+Toon_Eyebrows, tongue keys on Tongue mesh. Same three gaps: (a) Eyelash_* not mirrored (tier-1 retarget risk); (b) baked blink schedule missing from meta.json; (c) NeckTwist01 keyed — lead ruling. GLB re-import pending (not penalized). |

**Aggregate:** min score = 7 / 10

## Verdict

**REWORK** (dims 6, 8) — facial performance is the best of the batch (dim 4 = 10); the blink offset defect is concentrated here.

## Rework requests

| # | Dimension | Frame/time ref | Finding | Required fix |
|---|-----------|----------------|---------|--------------|
| 1 | 6 eye | f63-75 (blink 1), f215-228 (blink 3) | 2f inter-eye offsets -> wink frames (sheet f65, f218; strip f225) | Cap inter-eye blink offset at 1 frame on BOTH blinks (blink 2 f147/f148 is the correct model); keep peak-value asymmetry 0.97-0.99 |
| 2 | 8 technical | all blinks | Eyelash_* channels unkeyed while Eye_Blink baked | Mirror Eye_Blink_L/R onto Eyelash_* channels for retarget safety, or lead waiver for meta-only scope |
| 3 | 8 technical | meta.json | Baked blink frames not exported | Add `"baked_blinks": [63, 147, 215]` + runtime-scheduler suppression note to meta.json |
| 4 | 8 technical | armature action | NeckTwist01 keyed vs twist_helpers classification | LEAD RULING: reclassify NeckTwist01/02 as neck in rig_reference (recommended) |

## Notes for next round

- Re-render: targeted — both fixed blink regions + rerun inspect_clip. Full set not needed if only blink/meta change.
- Conditionally accepted: nostril symmetry; lid-fold chunk (pre-ruled template cosmetic — but note it is most visible on THIS clip's trailing-eye wink frames; fixing the offset also hides the chunk at speed).

---

# Round 2 — targeted re-check (dims 6 + 8 only), 2026-07-24

- **Evidence:** re-rendered previews (mp4/strips 17:03-17:08), rerun inspect_clip reports
  (21:52, zero flags), rerun curve audit (`curve_audit_lipsync.json`), consecutive-frame
  blink rows `qa/reports/batch1_recheck_blink_rows.png`, patched meta.json (21:52).

Blinks 1+3 (f63/f64, f215/f216) verified fixed; lead adjudication applied: single asymmetric mid-close frame (f65) accepted, wink read eliminated.

| # | Dimension | Round 1 | Round 2 | Evidence |
|---|-----------|---------|---------|----------|
| 6 | Eye behavior | 7 | 9 | Curve audit: all blinks now exactly 1-frame inter-eye lag, peak asymmetry kept (0.97-0.996). Frame rows: no monocular open-vs-shut frame remains; divergence limited to one partial-vs-partial mid-close/mid-reopen frame; 3-4 frames of shared full closure per blink. At-speed read = blink, not wink. Fallback not needed. |
| 8 | Technical | 8 | 9 | meta.json now carries baked_blinks [63, 147, 215] (matches curve onsets exactly) + explicit runtime blink-scheduler suppression note. Eyelash_* mirroring: LEAD WAIVER recorded (meta-only scope) - re-open if tier-1 retarget to realistic base is scheduled. NeckTwist01/02: accepted by lead ruling scope; recommend recording the rig_reference errata (reclassify as neck) so future pre-passes stop flagging it. Loop seams still 0.0/0.0. |

**Aggregate:** min score = 9 / 10 -> **VERDICT: SHIP**
