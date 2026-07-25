# QA Scorecard — sit_idle

- **Reviewer:** qa-3
- **Date:** 2026-07-25
- **Review round:** 1 (Locomotion/full-body batch — SPECIAL JUDGMENT CALL)
- **Duration/loop:** 10.0s (301f), loop=true
- **Evidence:** previews/sit_idle/ (mp4, strip, stills, meta.json); qa/reports/sit_idle_inspection.png + _metrics.json; qa/reports/curve_audit_body_loco.json; bone-track probe (per-frame motion + absolute Spine02 pitch over the flagged window).
- **Automated flags (inspect_clip):** 4× DEAD ZONE (f1-65, f67-98, f120-151, f278-300) + NEARLY STATIC. **Adjudicated — see special call below.**
- **Curve audit:** findings=0 — seated-chain keyed, BoneRoot unkeyed, no forbidden keys, loop seam value+tangent = 0.00000.

## Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Weight & balance | 9 | Seated weight on sit bones; lateral weight shift at f150 confirmed (window f120-151 max per-frame motion 7.1, mean 0.43 — the biggest event, the 1cm sit-bone shift). Soft C-curve spine, not military. |
| 2 | Timing & spacing | 9 | Multi-rate: slow breathing arc + foot taps (~f100) + finger drift (~f200) + posture re-stack (~f250); eased. |
| 3 | Naturalness | 9 | Events irregular; foot taps non-metronomic; re-stack present. No periodic tell in the back half (many <0.2s micro-spans interleaved with motion). |
| 4 | Facial aliveness | N/A | body clip (seated) — runtime facial layer owns face. |
| 5 | Hand & finger life | 9 | Fingers drift on thighs (Index bones keyed); hands not welded. |
| 6 | Eye behavior | N/A | runtime gaze/blink scheduler owns. |
| 7 | Loop seamlessness | 9 | Curve seam value+tangent = 0.00000; breathing/sway zero-delta at wrap. |
| 8 | Technical | 9 | No true frozen span (see call); seated chain keyed, cross-mesh followers driven, 30fps, naming clean. |

**Aggregate:** min applicable score = 9/10

## Verdict

**SHIP** — all applicable dimensions >= 9.

**SPECIAL CALL (DEAD ZONE flags):** The inspector's whole-frame pixel motion reads the seated breathing as frozen — the same body-framing false-positive the shipped `idle_hands_together` carries (identical energy mean 0.023, same NEARLY STATIC + I-frame flags, shipped). Bone probe disproves a freeze: absolute Spine02 pitch across the largest flagged window (f1-65) is a **smooth continuous breathing arc 1.529°→0.766° (min f37)→1.174°** — range 0.76°, moving every frame. My per-frame delta metric only dipped below threshold at the breath turnaround (f37, a natural inhale/exhale pause), producing an apparent 1.53s low-motion span — under the 2s reject bar and NOT a true hold. Spec beats (weight shift f150, foot taps ~f100, finger drift ~f200, re-stack ~f250) all present. Author's tight seated pose-contract (chosen over hip-drift that would pad energy but break the sit_down→sit_idle→stand_up seam) holds aliveness. Ships.
