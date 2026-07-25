# QA Scorecard — talk_idle

- **Reviewer:** qa
- **Date:** 2026-07-24
- **Review round:** 1
- **Evidence reviewed:** `previews/talk_idle/` (mp4, strip, stills, meta.json),
  `qa/reports/talk_idle_inspection.png`, `talk_idle_metrics.json`,
  `qa/reports/curve_audit_lipsync.json` (curve-level audit of `anim_master_lipsync.blend`,
  action `talk_idle` + per-mesh slot actions)
- **Automated flags** (inspect_clip): none. Curve audit: no linear rotation keys, no
  never_animate hits, all loop seams 0.0 value AND 0.0 tangent diff.
  NeckTwist01 keyed (see dim 8 — ruling needed).

## Scores

| # | Dimension | Score | Evidence / justification |
|---|-----------|-------|--------------------------|
| 1 | Weight & balance | 9 | Upper-layer clip: body rest-posed per layer contract (expected). Subtle Spine01/02/Waist/Clavicle support motion for nods+breath is seam-clean and plausible. Ownership question flagged to lead (below), not a defect. |
| 2 | Timing & spacing | 9 | All bezier; jaw attacks/releases varied (peaks f11/f27/f71/f86/f164, amplitudes 0.02-0.17); phrase taper into seam f164->f178 present; blink close 4f / open 7f natural profile. |
| 3 | Naturalness | 9 | Phrase lengths unequal (~49f/43f/35f speak, 7-13f pauses); jaw NOT a uniform sine (irregular peaks/valleys per curve data); brow L/R amplitude deltas 0.015; blink gaps 76f/31f non-uniform. Energy autocorr r=0.36 — no metronome. Nostril L/R identical accepted (bilateral breath physiology). |
| 4 | Facial aliveness | 9 | V_Wide/V_Tight_O flickers ~0.1 present (spec); 4 brow accents 0.1; nostril breath events; pauses close FULLY (jaw=0 at f54-64, f130-136 — sheet f65/f81 read shut, no hanging mouth). Note: Mouth_Close listed in spec layers but unkeyed — jaw=0 achieves closure visually; flag to director as layer-list deviation only. |
| 5 | Hand & finger life | N/A | Fingers deliberately unkeyed — owned by base idle layer (lead ruling). No violation: zero finger channels in action. |
| 6 | Eye behavior | 8 | Blinks phrase-aligned (f51/f127/f158 at pause boundaries), eye-down 0.1 coupled to blinks (natural, stays within blink ownership). BUT blink 2 has a 2-frame inter-eye offset (L f127->131, R f129->133): inspection sheet f130 shows one eye fully shut, other ~25% — reads as wink/flutter, amplified by toon-scale eyes. Blinks 1/3 (1f offset) read fine (proof the 1f version works). |
| 7 | Loop seamlessness | 10 | Curve-perfect: every channel first/last key value diff 0.0 AND tangent diff 0.0. Boundary tiles f178-180 vs f0-2 indistinguishable; pixel wrap diff 1.65x median = codec noise. Seam lands mid-pause per spec. |
| 8 | Technical | 8 | Bezier everywhere, values in range, action name == clip id, 30fps, cross-mesh coverage COMPLETE per key_inventory (Jaw_Open on all 5 sharing meshes incl. Tongue; teeth follow JawRoot bone — CC_Toon_Teeth_01 has no Jaw_Open key). Gaps: (a) Eyelash_* channels not mirrored from Eye_Blink — invisible on toon (lash line follows lid in renders) but breaks tier-1 retarget to realistic templates (rubric cross-mesh line + protocol 5); (b) baked blink frames absent from meta.json — spec's "(runtime note)" for the runtime blink scheduler unfulfilled, double-blink collision risk; (c) CC_Base_NeckTwist01 keyed = rig_reference twist_helpers hit — BUT NeckTwist01/02 are the ONLY neck chain (Spine02->NT01->NT02->Head); keying them is anatomically correct. Lead ruling needed: reclassify as neck in rig_reference, or head-only nods (worse). GLB re-import/sandbox playback still pending at this stage (not penalized). |

**Aggregate:** min score = 8 / 10

## Verdict

**REWORK** (dims 6, 8) — all fixes small and surgical; everything else at or above bar.

## Rework requests

| # | Dimension | Frame/time ref | Finding | Required fix |
|---|-----------|----------------|---------|--------------|
| 1 | 6 eye | f127-133 (blink 2) | 2f inter-eye offset -> visible wink frame (sheet f130) | Cap inter-eye blink offset at 1 frame everywhere (L leads); KEEP the peak-value asymmetry (R 0.97-0.99) — blinks 1/3 are the model |
| 2 | 8 technical | all blinks | Eyelash_* channels unkeyed while Eye_Blink baked | Mirror Eye_Blink_L/R curves onto corresponding Eyelash_* channels (template convention) so tier-1 clip survives retarget to realistic base; or obtain lead waiver for meta-only scope |
| 3 | 8 technical | meta.json | Baked blink schedule not exported ("runtime note" in spec beats) | Add `"baked_blinks": [51, 127, 158]` (+ note that runtime blink scheduler must suppress during this clip) to meta.json |
| 4 | 8 technical | armature action | NeckTwist01 keyed; rig_reference classifies it twist_helper | LEAD RULING: amend rig_reference to classify NeckTwist01/02 as neck (recommended — they are the deform neck chain), else clips must drop neck keys |

## Notes for next round

- Re-render: targeted only — new inspection run + mid-blink frames of the fixed blink (f127-135). Full preview set not required if only blink/meta change.
- Conditionally accepted: nostril L/R symmetry (physiological); Mouth_Close omission (jaw=0 closure verified in renders — director to bless or author to add); mid-blink lid-fold chunk (lead pre-ruled template cosmetic, out of clip scope).

---

# Round 2 — targeted re-check (dims 6 + 8 only), 2026-07-24

- **Evidence:** re-rendered previews (mp4/strips 17:03-17:08), rerun inspect_clip reports
  (21:52, zero flags), rerun curve audit (`curve_audit_lipsync.json`), consecutive-frame
  blink rows `qa/reports/batch1_recheck_blink_rows.png`, patched meta.json (21:52).

Blink 2 (f127/f128) verified fixed: f130 now shows matched lid phases.

| # | Dimension | Round 1 | Round 2 | Evidence |
|---|-----------|---------|---------|----------|
| 6 | Eye behavior | 8 | 9 | Curve audit: all blinks now exactly 1-frame inter-eye lag, peak asymmetry kept (0.97-0.996). Frame rows: no monocular open-vs-shut frame remains; divergence limited to one partial-vs-partial mid-close/mid-reopen frame; 3-4 frames of shared full closure per blink. At-speed read = blink, not wink. Fallback not needed. |
| 8 | Technical | 8 | 9 | meta.json now carries baked_blinks [51, 127, 158] (matches curve onsets exactly) + explicit runtime blink-scheduler suppression note. Eyelash_* mirroring: LEAD WAIVER recorded (meta-only scope) - re-open if tier-1 retarget to realistic base is scheduled. NeckTwist01/02: accepted by lead ruling scope; recommend recording the rig_reference errata (reclassify as neck) so future pre-passes stop flagging it. Loop seams still 0.0/0.0. |

**Aggregate:** min score = 9 / 10 -> **VERDICT: SHIP**
