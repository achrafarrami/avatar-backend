"""micro_face_layer — Tier-1 additive micro-expression loop (owner: facial).

ADDITIVE over ANY base clip including talking. Contract (library_spec):
- 12 s loop, 8 micro events, no two inter-event gaps equal
- every delta <= 0.06 (never fights a base expression)
- NO jaw / viseme / V_* keys (lipsync owns them), no gaze, no bones
- all curves zero at the loop seam; events keep >= 15f seam margin
- runtime randomizes the start offset per session
"""
from anim_framework.clips import clip


def _pulse(ctx, key, f_start, rise, fall, amp, layer='micro'):
    ctx.key_shape(key, f_start, 0.0, layer)
    ctx.key_shape(key, f_start + rise, amp, layer)
    ctx.key_shape(key, f_start + rise + fall, 0.0, layer)


@clip("micro_face_layer", "micro_layer", 12.0, loop=True, framing='face',
      still_frame=0.21,
      description="Additive face life: 8 unevenly spaced micro events "
                  "(cheek/brow/lip/nostril/lid tone), all <=0.06, zero-delta "
                  "seam; jaw+visemes untouched (lipsync layer owns them)")
def micro_face_layer(ctx):
    f0 = ctx.frame_start
    # event starts: 30,72,121,160,206,253,291,334
    # gaps: 42,49,39,46,47,38,43 — all distinct (anti-metronome contract)

    # 1) f30  cheek flicker, left only
    _pulse(ctx, "Cheek_Raise_L", f0 + 30, 4, 6, 0.040)
    # 2) f72  brow micro-raise (bilateral, R weaker + 2f late)
    _pulse(ctx, "Brow_Raise_Inner_L", f0 + 72, 5, 9, 0.050)
    _pulse(ctx, "Brow_Raise_Inner_R", f0 + 74, 5, 9, 0.040)
    # 3) f121 unilateral lip compression
    _pulse(ctx, "Mouth_Press_L", f0 + 121, 5, 8, 0.060)
    # 4) f160 nostril flicker
    _pulse(ctx, "Nose_Sneer_L", f0 + 160, 3, 5, 0.020)
    _pulse(ctx, "Nose_Sneer_R", f0 + 161, 3, 5, 0.015)
    # 5) f206 lid-tone swell (slow, both lids, decorrelated)
    _pulse(ctx, "Eye_Blink_L", f0 + 206, 14, 16, 0.040)
    _pulse(ctx, "Eye_Blink_R", f0 + 208, 14, 16, 0.034)
    # 6) f253 brow knit micro
    _pulse(ctx, "Brow_Compress_L", f0 + 253, 5, 7, 0.040)
    _pulse(ctx, "Brow_Compress_R", f0 + 255, 5, 7, 0.032)
    # 7) f291 cheek flicker, right (answers event 1, different side/size)
    _pulse(ctx, "Cheek_Raise_R", f0 + 291, 4, 7, 0.035)
    # 8) f334 lip compression, right (ends f346 — 15f before the seam)
    _pulse(ctx, "Mouth_Press_R", f0 + 334, 4, 8, 0.045)
