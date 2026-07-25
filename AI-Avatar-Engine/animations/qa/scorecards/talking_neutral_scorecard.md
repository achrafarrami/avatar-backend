# QA Scorecard — talking_neutral

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1
- **Evidence reviewed:** `previews/talking_neutral/` (mp4, strip, stills, meta.json),
  `qa/reports/talking_neutral_inspection.png`, `talking_neutral_metrics.json`,
  `qa/reports/curve_audit_lipsync.json` (actions `talking_neutral` + per-mesh slots)
- **Automated flags** (inspect_clip): none. Curve audit: no linear rotation, no
  never_animate hits, all loop seams 0.0/0.0. NeckTwist01 keyed (dim 8 ruling).

## Scores

| # | Dimension | Score | Evidence / justification |
|---|-----------|-------|--------------------------|
| 1 | Weight & balance | 9 | Upper-layer clip, rest-posed body per contract. Chest (Spine02, 24 keys) breath motion sanctioned by spec's "nostril + chest hook". Seam-clean. |
| 2 | Timing & spacing | 9 | Viseme attacks 3-5f per key spacing; releases overlap next attack (no zero-crossing gaps between adjacent viseme curves); bilabial V_Explosive events carry Mouth_Close to 1.0 with 1-2f holds (10 keys); jaw layered under at ~28-35% of viseme openness, spec band 30-50% (borderline low edge, reads correctly). |
| 3 | Naturalness | 9 | Phrases 55f/70f/75f unequal per spec; blink gaps 85f/73f non-uniform; brow L/R amplitude deltas up to 0.043; head emphasis events vary in size (82 head keys, non-repeating). Energy autocorr r=0.21 — no metronome. Nostril L/R identical accepted (bilateral physiology). |
| 4 | Facial aliveness | 9 | THE reference viseme clip: articulate open shapes at peaks (strip f97 — teeth visible, convincing), co-articulated softness elsewhere; tongue fires on dentals/affricates (V_Tongue_Raise 18 keys, V_Tongue_up 6, driven on Tongue mesh); breath at pause starts (nostril 0.13 + chest). WATCH ITEM for director: 6 of 8 viseme peaks sit below the documented 0.6-0.8 band (V_Open 0.59, V_Wide 0.57, V_Tight_O 0.51, V_Tight 0.45, V_Affricate 0.54, V_Lip_Open 0.36; only V_Explosive 0.75 / V_Dental_Lip 0.61 in band). Renders read well — either bless the softer band in the spec or bump stressed-syllable peaks +0.05-0.1. Not gated here because reject line is over-articulation and pixels read correctly. |
| 5 | Hand & finger life | N/A | Deliberately unkeyed — base idle layer owns fingers (lead ruling). No violation. |
| 6 | Eye behavior | 8 | Blinks near each phrase END per spec (f60/f145/f218); close-fast/open-slow profile; blink-coupled eye-down 0.1. Blinks 1-2 (1f offset) read symmetric at speed (sheet f65: both lids down together — correct look). BUT blink 3 (L f218->221, R f220->223, 2f offset): strip f225 shows one eye open / one closed — wink artifact on the reference clip. |
| 7 | Loop seamlessness | 10 | All channels 0.0 value / 0.0 tangent seam diff. Tiles f238-240 vs f0-2 identical. Wrap pixel ratio 1.21x median = noise. |
| 8 | Technical | 8 | Bezier, ranges legal (viseme max 0.75 — no 1.0 puppet), action name == clip id, 30fps, cross-mesh contract COMPLETE (all keyed keys driven on every sharing mesh per key_inventory; V_Tongue_* on Tongue+Toon_Eyebrows = full set; teeth ride JawRoot bone). Same three gaps as talk_idle: (a) Eyelash_* not mirrored from Eye_Blink (tier-1 retarget risk); (b) baked blink schedule missing from meta.json (spec "(runtime note)"); (c) NeckTwist01 keyed — lead ruling on rig_reference classification. GLB re-import pending at this stage (not penalized). |

**Aggregate:** min score = 8 / 10

## Verdict

**REWORK** (dims 6, 8) — the viseme sequencing core is ship-grade; fixes are peripheral.

## Rework requests

| # | Dimension | Frame/time ref | Finding | Required fix |
|---|-----------|----------------|---------|--------------|
| 1 | 6 eye | f218-229 (blink 3) | 2f inter-eye offset -> wink frame (strip f225) | Cap inter-eye blink offset at 1 frame (match blinks 1-2, which are correct); keep peak-value asymmetry |
| 2 | 8 technical | all blinks | Eyelash_* channels unkeyed while Eye_Blink baked | Mirror Eye_Blink_L/R onto Eyelash_* channels for retarget safety, or lead waiver for meta-only scope |
| 3 | 8 technical | meta.json | Baked blink frames not exported | Add `"baked_blinks": [60, 145, 218]` + runtime-scheduler suppression note to meta.json |
| 4 | 8 technical | armature action | NeckTwist01 keyed vs twist_helpers classification | LEAD RULING: reclassify NeckTwist01/02 as neck in rig_reference (recommended) |

## Notes for next round

- Re-render: targeted — fixed blink region (f215-230) + rerun inspect_clip. Full set not needed if only blink/meta change.
- Director decision requested: viseme peak band (see dim 4 watch item) — spec text vs authored 0.45-0.6 for non-bilabials.
- Conditionally accepted: nostril symmetry; lid-fold chunk (pre-ruled template cosmetic).

---

# Round 2 — targeted re-check (dims 6 + 8 only), 2026-07-24

- **Evidence:** re-rendered previews (mp4/strips 17:03-17:08), rerun inspect_clip reports
  (21:52, zero flags), rerun curve audit (`curve_audit_lipsync.json`), consecutive-frame
  blink rows `qa/reports/batch1_recheck_blink_rows.png`, patched meta.json (21:52).

Blink 3 (f218/f219) verified fixed: f225 now both-lids-as-slits, old wink frame gone.

| # | Dimension | Round 1 | Round 2 | Evidence |
|---|-----------|---------|---------|----------|
| 6 | Eye behavior | 8 | 9 | Curve audit: all blinks now exactly 1-frame inter-eye lag, peak asymmetry kept (0.97-0.996). Frame rows: no monocular open-vs-shut frame remains; divergence limited to one partial-vs-partial mid-close/mid-reopen frame; 3-4 frames of shared full closure per blink. At-speed read = blink, not wink. Fallback not needed. |
| 8 | Technical | 8 | 9 | meta.json now carries baked_blinks [60, 145, 218] (matches curve onsets exactly) + explicit runtime blink-scheduler suppression note. Eyelash_* mirroring: LEAD WAIVER recorded (meta-only scope) - re-open if tier-1 retarget to realistic base is scheduled. NeckTwist01/02: accepted by lead ruling scope; recommend recording the rig_reference errata (reclassify as neck) so future pre-passes stop flagging it. Loop seams still 0.0/0.0. |

**Aggregate:** min score = 9 / 10 -> **VERDICT: SHIP**
