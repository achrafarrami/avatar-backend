# QA Scorecard - proud

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Facial Tier-2 batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/proud/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/proud_inspection.png + _metrics.json (loop-aware inspect_clip); qa/reports/curve_audit_facial_tier2.json (action proud + per-mesh follower slots).
- **Automated flags (inspect_clip):** none (flags: 0). **Curve audit:** findings=0 all slots (no linear rotation, no never_animate/twist/BoneRoot keys, no range violations, cross-mesh followers driven).

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | N/A | facial clip; only light authorized body hooks (head/clavicle/spine) - no weight-bearing action. |
| 2 | Timing & spacing | 9 | Chin-up head hook (19 head keys) + chest lift Spine02/Clavicle f1, slow controlled. Closed-lip smile 0.416 (16 keys) blooms; Jaw_Forward 0.1 set (NO Jaw_Open - no teeth). ONE slow blink beat f31 (close/hold/open). |
| 3 | Naturalness | 9 | Asymmetric smile 0.416/0.34, cheek 0.18/0.158. Corners waver (16 keys). No mirror. |
| 4 | Facial aliveness | 9 | Closed-lip sealed smile verified in front.png (SEAL PASS - no teeth, no open mouth). Slow satisfied blink present. Brows calm/level (+0.05). |
| 5 | Hand & finger life | N/A | facial clip; hands owned by body layer. |
| 6 | Eye behavior | 9 | One slow blink f31 (vmax 0.95, close 6f/hold/open 8f) - the satisfied blink beat present. |
| 7 | Loop seamlessness | N/A | N/A one-shot end-hold (runtime crossfades out) |
| 8 | Technical | 9 | Chin-up + chest hooks authorized; NO teeth (closed-lip); cross-mesh followers driven; naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Closed-lip seal, chest hook, and slow-blink beat all confirmed (smug-cartoon reject avoided).
