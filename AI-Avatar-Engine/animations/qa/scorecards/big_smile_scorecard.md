# QA Scorecard - big_smile

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/big_smile/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/big_smile_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action big_smile + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Two-step bloom staggered; jaw teeth-reveal opens f11 (JawRoot bone + Jaw_Open 0.16). Onset staggered cheeks f1 -> smile f3 -> squint f7 -> jaw f11 (not simultaneous). Mouth_Smile_L peaks 1.0 over 16 keys. |
| 3 | Naturalness | 9 | L/R asymmetric everywhere: Cheek 0.76/0.66, Smile 1.0/0.95, Squint 0.45/0.405; all lr_pairs identical=false. No byte-mirror. |
| 4 | Facial aliveness | 9 | Duchenne order cheeks-first; teeth part verified in front.png/strip (jaw opens, teeth visible - teeth-part gate PASS). Alive hold via 16-key smile waver; baked blink f31. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Baked blink f31: Eye_Blink_L f31-41 / R f32-42 = 1f offset (spec-legal, NOT a wink). Freeze-frame lid-fold at f34 = accepted toon cosmetic. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | action==clip id, 30fps, bones CC_Base_Head+JawRoot only (authorized), cross-mesh followers (Toon_Eyebrows/TearLine/EyeOcclusion/Tongue/Eye) driven. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Teeth-reveal jaw component present and rendered. Two-step bloom confirmed.
