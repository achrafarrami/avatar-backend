# QA Scorecard - confused

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/confused/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/confused_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action confused + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Asymmetry-led: Brow_Drop_L 0.517 + Brow_Raise_Outer_R 0.46 (opposed brows) onset f1; head tilt follows at f7 (face leads). Second recompute beat: Brow_Drop_L 18 keys, head re-keys f46/f53. Mouth sideways pull 0.2. |
| 3 | Naturalness | 9 | Opposed asymmetric brows (not symmetric = would be anger/surprise). One-sided squint 0.3. Eye darts within region (Look_L/R delta 0.2). No byte-mirror. |
| 4 | Facial aliveness | 9 | Ends unresolved; f45 recompute beat present (single-beat would read as glitch - avoided). Head-follows-face ordering correct. |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | Eye dart micro-shifts (6-9 keys/dir) within aversion region; blink f45. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Head tilt hook authorized; cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Face-leads-head and the f45 second beat both confirmed.
