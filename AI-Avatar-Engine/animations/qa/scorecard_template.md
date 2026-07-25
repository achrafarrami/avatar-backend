# QA Scorecard — <clip_id>

- **Reviewer:** qa
- **Date:** YYYY-MM-DD
- **Review round:** 1
- **Evidence reviewed:** `previews/<clip_id>/` stills (front/side/persp/wireframe), `strip.png`,
  `qa/reports/<clip_id>_inspection.png`, `qa/reports/<clip_id>_metrics.json`, `meta.json`
- **Automated flags** (from `inspect_clip.py`): none | list verbatim

> Scoring: 1-10 per dimension. Ship bar is **>= 9 on every dimension** — a single 8 is REWORK.
> Every score below 9 MUST have at least one concrete fix in the rework table.
> NOTE: reconcile dimensions/weights with `qa/rubric.md` when the director lands it;
> until then these are the eight agreed dimensions.

## Scores

| # | Dimension | Score | Evidence / justification (frame refs) |
|---|-----------|-------|---------------------------------------|
| 1 | Weight & balance — center of gravity plausible, feet planted (no floating/sliding), mass carries through poses | /10 | |
| 2 | Timing & spacing — ease-in/out present, no linear robot ramps, accents where the motion needs them, holds breathe | /10 | |
| 3 | Naturalness — asymmetry, overlap/follow-through, no pose-to-pose popping, secondary motion on spine/head | /10 | |
| 4 | Facial aliveness — brows/lids/mouth participate; face never a frozen mask while the body moves | /10 | |
| 5 | Hand life — fingers posed and moving (no rigid paddles), wrist rotation accompanies arm motion | /10 | |
| 6 | Eye behavior — blinks at plausible intervals, saccades/gaze shifts, lids track eye direction | /10 | |
| 7 | Loop seamlessness — no position/velocity pop at wrap (check loop-boundary strip + LOOP POP flag), energy continuous across the seam | /10 | |
| 8 | Technical — no interpenetration (hands/body/clothes), no broken bones or counter-animated twists, correct fps/duration vs meta, no dead zones, keys only on intended bones/shape keys | /10 | |

**Aggregate:** min score = __ / 10

## Verdict

**SHIP** (all dimensions >= 9) / **REWORK** (any dimension < 9)

## Rework requests (REWORK only — each item concrete, actionable, tagged)

| # | Dimension | Frame/time ref | Finding | Required fix |
|---|-----------|----------------|---------|--------------|
| 1 | e.g. 7 loop | f164 vs f0, t=5.47s | right arm 12deg forward of start pose at wrap | match end keys to frame 0 pose, or blend last 6 frames into start |
| 2 | | | | |

## Notes for next round

- What must be re-rendered as evidence (full preview set vs. targeted frames only):
- Anything conditionally accepted (and why):
