# QA Scorecard - clap

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/clap/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/clap_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action clap + follower slots).
- **Automated flags (inspect_clip):** 0 flags (peak energy 1.073).
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine02 19 keys - chest bounces with each clap (energy passes through the trunk); weight stays centered for the bilateral action. |
| 2 | Timing & spacing | 9 | Arm 78 keys bezier; hands meet and part with decaying/varied spacing (not a uniform metronome clap). |
| 3 | Naturalness | 9 | L_Forearm timing offset from R (identical_frames=False); byte-mirror detector clears it. Meets vary - not copy-paste. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | 26 finger bones, 172 keys (most of any clip) - hands shape through each meet/part; very alive. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limbs, BoneRoot unkeyed, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. SPECIAL CALL: rig-limited HIGH meet near the face (chest-height meet impossible per ruling #1). Strip judgment: hands clearly MEET at center then PART WIDE repeatedly (f21-26 together, f31 apart, repeating) - reads as an enthusiastic high clap/applause, NOT a face-cover (a cover would keep hands on the face; these separate wide between meets). SHIP as recognizable weighted clap.
