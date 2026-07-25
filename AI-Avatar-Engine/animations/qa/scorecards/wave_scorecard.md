# QA Scorecard - wave

- **Reviewer:** qa-2
- **Date:** 2026-07-25
- **Review round:** 1 (Body Gesture batch)
- **Duration/loop:** 2.5s, loop=false
- **Evidence:** previews/wave/ (mp4, strip, front/side/persp/wireframe, meta.json); qa/reports/wave_inspection.png + _metrics.json; qa/reports/curve_audit_body_gestures.json (action wave + follower slots).
- **Automated flags (inspect_clip):** NEARLY-STATIC flag confirmed a framing false-positive (peak 0.246 vs 0.02 dead thr; richly keyed). Shoulder-height wave is the rig-legal idiom per ruling #1.
- **Curve audit:** findings=0 all slots - no linear rotation on limbs (all bezier), no never_animate/twist/BoneRoot keys (BoneRoot unkeyed, Hip owns weight, NeckTwist=neck errata), no byte-mirror, no range violations, naming==clip id, 30fps.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Spine02 (11k)+Spine01+Waist keyed - torso counterbalances the raised arm; no rigid trunk under a moving limb. Shoulder-height extended-out wave (rig-adapted per ruling #1). |
| 2 | Timing & spacing | 9 | Arm 57 keys, all bezier; raise anticipation -> oscillating wave -> settle to neutral tail. Multi-key arcs, no linear ramps. |
| 3 | Naturalness | 9 | Wave oscillation amplitudes vary (not a uniform metronome); right-arm gesture with natural drag. Strip confirms clear side-to-side hand motion. |
| 4 | Facial aliveness | N/A | body clip; shape_keys empty (except gaze targets where noted); facial owned by runtime facial layer. |
| 5 | Hand & finger life | 9 | Full right-hand finger rig keyed (26 finger bones, 64 keys); finger movers active into the wave hold (R_Index/Mid/Ring/Pinky). No paddle hand. |
| 6 | Eye behavior | N/A | no eye keys baked; runtime blink scheduler + gaze layer composite over this body clip (ruling #3). Not a defect. |
| 7 | Loop seamlessness | N/A | one-shot with return-to-neutral tail / holdable end pose (runtime crossfades out). |
| 8 | Technical | 9 | Bezier limb rotation, BoneRoot unkeyed, no twist keys, naming/fps clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** - all applicable dimensions >= 9. Rig-adapted extended-out wave; motion verified in strip. The lone inspect flag is a full-body-framing artifact.
