# QA Scorecard - angry

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.0s, loop=false
- **Evidence:** previews/angry/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/angry_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action angry + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | FAST onset f1-6: Brow_Drop_L 0.802 slams f1, R f2; Mouth_Press 0.45 then Jaw_Forward 0.15 (jaw set) f5; chin-down head hook f1-9. Tension-in-stillness hold with micro-tremor (Brow_Drop_L 20 keys, Mouth_Tighten_L 20 keys). |
| 3 | Naturalness | 9 | Asymmetric brow depth 0.802/0.72, Compress 0.5/0.45, Sneer 0.28/0.238. No mirror. |
| 4 | Facial aliveness | 9 | Sealed pressed-lip glare verified in front.png (mouth SEALED, no open-mouth). NO blink in hold - by-design hard glare (baked_blinks=[], authorized; not flagged). Tremor present (not a mannequin). |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Lids narrow to glare (Eye_Squint 0.42/0.378); suppressed blink = menace (authorized per lead ruling #2). |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | No Eye_Blink keys (intentional); chin-down head hook authorized; no jaw-open (rage-shout out of scope); naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Mouth-seal spot-check PASS. Blink-suppression is intended per lead ruling #2.
