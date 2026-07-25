"""Facial expressions — 10 Tier-2 clips (owner: facial).

big_smile 2.0s   two-step bloom, jaw teeth-reveal, alive hold
laugh     3.0s   decaying jaw-pulse train + body bounce, ends on soft smile
giggle    1.8s   suppressed laugh (smile fights lip-press), tiny pulses
confused  2.5s   asymmetric brow knot + head tilt follows, second recompute beat
curious   2.0s   head tilt WITH brows, forward lean, focus-grade gaze stillness
excited   2.0s   two-step smile + jaw crack, double nod, sparkle tremor
angry     2.0s   5f slam, glare, tension-in-stillness, suppressed blink
disappointed 2.5s exhale-led: breath -> face -> head-shake -> gaze aversion
embarrassed 2.5s  gaze aversion FIRST, suppressed smile, head turns away
proud     2.5s   chin/chest lift, closed-lip smile, one slow satisfied blink

Spec: animations/library_spec.json (beats + quality gates). Style reference:
clips/expressions.py (tier-1). All one-shots end HOLDING their apex for
runtime crossfade-out (never snapped to neutral). Head motion keyed within
the <=~2.5-3 deg facial allowance; full body hooks (laugh 6deg, confused/
curious tilt, proud chin, disappointed/embarrassed turn, breathing hooks)
stay noted in the descriptions for the body/breathing layer. Mouth opening
always drives the JawRoot BONE (ctx.jaw_open) + Jaw_Open key at angle/15 —
the key alone leaves the toon lips closed (README jaw standard).

BLINK_META: baked-blink frames + runtime notes, stamped into meta.json by
patch_facial_tier2_meta.py (QA dim8 — runtime blink scheduler must suppress
procedural blinks over these).
"""
from anim_framework.clips import clip
from anim_framework import motion

EYE_L, EYE_R = "CC_Base_L_Eye", "CC_Base_R_Eye"

# absolute baked-blink start frames (frame_start == 1). angry bakes none.
BLINK_META = {
    "big_smile":    {"blinks": [31], "note": "One blink mid-hold (f31)."},
    "laugh":        {"blinks": [71], "note": "Partial lid-squeezes ride the "
                     "jaw pulses (f11-46); one full reset blink on recovery "
                     "(f71). Runtime scheduler MUST suppress procedural blinks."},
    "giggle":       {"blinks": [39], "note": "One blink (f39) under the "
                     "suppressed-laugh crinkle."},
    "confused":     {"blinks": [45], "note": "One blink (f45) between the two "
                     "recompute beats."},
    "curious":      {"blinks": [29], "note": "One blink (f29); gaze holds "
                     "focus-grade still otherwise."},
    "excited":      {"blinks": [27], "note": "One fast blink (f27) inside the "
                     "sparkle hold."},
    "angry":        {"blinks": [], "note": "NO blink — suppressed blink is the "
                     "menace. Runtime scheduler MUST NOT fire a blink during "
                     "the glare hold."},
    "disappointed": {"blinks": [41], "note": "One heavy down-cast blink (f41) "
                     "after the gaze averts."},
    "embarrassed":  {"blinks": [23], "note": "One quick blink (f23) as the "
                     "head turns away."},
    "proud":        {"blinks": [31], "note": "One SLOW satisfied blink "
                     "(f31, close6/hold2/open8). Cadence hint: relaxed."},
}


def _aim(ctx, frame, dx, dy, r_scale=1.0, layer='eye_bones'):
    """Aim both irises via the eye bones (Look keys move lids only). dx + =
    character's left, dy + = up; 16 deg/unit yaw, 12 up / 13 down."""
    z = dx * 16.0
    x = -dy * (12.0 if dy >= 0 else 13.0)
    for bone, s in ((EYE_L, 1.0), (EYE_R, r_scale)):
        ctx.key_bone_axis(bone, frame, 'z', z * s, layer=layer)
        ctx.key_bone_axis(bone, frame, 'x', x * s, layer=layer)


# ---------------------------------------------------------------------------
@clip("big_smile", "facial", 2.0, loop=False, framing='face', still_frame=0.55,
      description="Two-step bloom: soft smile by f8 then full at f14-20 with "
      "jaw teeth-reveal (bone 4deg + Jaw_Open 0.15) and cheeks 0.7 squinting "
      "lids 0.45; 5% corner overshoot f18; head tips back ~2deg (body hook). "
      "Alive hold: corner waver + cheek re-raise; blink f31; ends holding")
def big_smile(ctx):
    f0 = ctx.frame_start
    # cheeks lead (Duchenne), two-step; R lags 1f, ~8% weaker
    for f, v in [(0, 0.0), (8, 0.34), (14, 0.72), (18, 0.66), (34, 0.71),
                 (59, 0.68)]:
        ctx.key_shape("Cheek_Raise_L", f0 + f, v, 'cheeks')
    for f, v in [(1, 0.0), (9, 0.30), (15, 0.66), (19, 0.61), (35, 0.65),
                 (59, 0.62)]:
        ctx.key_shape("Cheek_Raise_R", f0 + f, v, 'cheeks')
    # corners: soft step then full with 5% overshoot; L leads
    for f, v in [(2, 0.0), (8, 0.44), (16, 1.0), (18, 1.03), (21, 0.98),
                 (59, 0.97)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(3, 0.0), (9, 0.39), (17, 0.92), (19, 0.95), (22, 0.90),
                 (59, 0.90)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    # upper-teeth reveal
    for f, v in [(8, 0.0), (16, 0.16), (20, 0.14), (59, 0.14)]:
        ctx.key_shape("Mouth_Up_Upper_L", f0 + f, v, 'smile')
        ctx.key_shape("Mouth_Up_Upper_R", f0 + f + 1, v * 0.88, 'smile')
    # jaw reveal: BONE opens the bite + key shapes the lip part
    for f, d in [(10, 0.0), (16, 4.2), (20, 3.7), (59, 3.7)]:
        ctx.jaw_open(f0 + f, d)
    for f, v in [(10, 0.0), (16, 0.16), (20, 0.15), (59, 0.15)]:
        ctx.key_shape("Jaw_Open", f0 + f, v, 'jaw')
    # lids compress with the cheeks (the real-smile tell)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 6, 0.0, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 18, 0.45, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 59, 0.43, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 8, 0.0, 'brow', r_offset=2,
                     r_scale=0.85)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 18, 0.15, 'brow', r_offset=2,
                     r_scale=0.85)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 59, 0.12, 'brow', r_offset=2,
                     r_scale=0.85)
    # head tips back (facial <=2.5; body hook completes); off-axis roll
    for f, d in [(0, 0.0), (14, -2.0), (20, -1.8), (59, -1.6)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(2, 0.0), (16, 0.5), (59, 0.4)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    motion.add_blink(ctx, f0 + 30, amp=0.9, close=3, hold=1, open_=6,
                     r_offset=1)
    # keep the apex alive: cheek pulse delta + corner waver
    for f, v in [(30, 0.0), (34, 0.05), (41, 0.0)]:
        ctx.key_shape("Cheek_Raise_L", f0 + f, v, 'cheekpulse')
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_L", f, v, 'waver'),
        start=f0 + 22, end=f0 + 59, amp=0.03, cycles=(2, 3), step=4, fade=0.2)


# ---------------------------------------------------------------------------
def _laugh_pulses(ctx, f0, amps, layer='laugh'):
    """Decaying jaw-pulse train with jittered spacing; each pulse phase-locks
    a clavicle+chest bounce and a tiny head bob (one physical event)."""
    ctx.jaw_open(f0 - 2, 0.0, layer=layer)
    ctx.key_shape("Jaw_Open", f0 - 2, 0.0, layer)
    fp, peaks = f0 + 3, []
    for a in amps:
        deg = min(11.0, a * 15.0)
        ctx.jaw_open(fp, deg, layer=layer)
        ctx.key_shape("Jaw_Open", fp, a, layer)
        ctx.jaw_open(fp + 4, deg * 0.32, layer=layer)
        ctx.key_shape("Jaw_Open", fp + 4, a * 0.32, layer)
        peaks.append(fp)
        fp += 7 + ctx.rng.randint(-1, 1)
    end = fp + 2
    ctx.jaw_open(end, 0.0, layer=layer)
    ctx.key_shape("Jaw_Open", end, 0.0, layer)
    for p in peaks:
        for side, s in (('L', 1.0), ('R', 0.85)):
            ctx.clavicle_raise(side, p - 3, 0.0, layer=layer)
            ctx.clavicle_raise(side, p, 0.8 * s, layer=layer)
            ctx.clavicle_raise(side, p + 4, 0.0, layer=layer)
        ctx.key_bone_axis("CC_Base_Spine02", p, 'x', 0.5, layer=layer)
        ctx.key_bone_axis("CC_Base_Spine02", p + 4, 'x', 0.0, layer=layer)
        ctx.pitch("CC_Base_Head", p, 0.6, layer='toss')
        ctx.pitch("CC_Base_Head", p + 4, 0.0, layer='toss')
    return end, peaks


@clip("laugh", "facial", 3.0, loop=False, framing='face', still_frame=0.3,
      description="Onset f0-8 smile bloom + head back ~3deg (6deg body hook). "
      "Pulse train f11-46: Jaw_Open 0.40/0.35/0.28/0.22/0.16 decaying, ~7f "
      "jittered spacing, each synced to a clavicle+chest bounce (body hook) "
      "and head bob; eyes squeeze 0.7, partial blinks ride peaks. Wind-down "
      "f46-70, aftershock chuckle f66, recovery breath (chest hook) f74-89. "
      "Ends on a warm soft smile 0.4, NOT neutral. Reset blink f71")
def laugh(ctx):
    f0 = ctx.frame_start
    # smile bloom -> pulses -> residual soft smile (never zero)
    for f, v in [(0, 0.0), (8, 0.88), (50, 0.86), (72, 0.42), (89, 0.40)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(1, 0.0), (9, 0.80), (50, 0.78), (73, 0.37), (89, 0.36)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    for f, v in [(2, 0.0), (8, 0.80), (50, 0.78), (72, 0.30), (89, 0.28)]:
        ctx.key_shape("Cheek_Raise_L", f0 + f, v, 'cheeks')
    for f, v in [(3, 0.0), (9, 0.73), (50, 0.71), (73, 0.26), (89, 0.25)]:
        ctx.key_shape("Cheek_Raise_R", f0 + f, v, 'cheeks')
    # eyes squeeze nearly shut by pulse 2, re-open on recovery
    for f, v in [(4, 0.15), (18, 0.70), (50, 0.66), (72, 0.20), (89, 0.16)]:
        ctx.key_shape("Eye_Squint_L", f0 + f, v, 'squint')
        ctx.key_shape("Eye_Squint_R", f0 + f + 1, v * 0.86, 'squint')
    # laugh brows lift + nose crease
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 6, 0.0, 'brow', r_offset=2,
                     r_scale=0.87)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 16, 0.15, 'brow', r_offset=2,
                     r_scale=0.87)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 55, 0.10, 'brow', r_offset=2,
                     r_scale=0.87)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 89, 0.05, 'brow', r_offset=2,
                     r_scale=0.87)
    for f, v in [(8, 0.0), (18, 0.20), (55, 0.10), (89, 0.0)]:
        ctx.key_shape("Nose_Crease_L", f0 + f, v, 'nose')
        ctx.key_shape("Nose_Crease_R", f0 + f + 1, v * 0.85, 'nose')
    # head back ~3deg (body hook 6deg), returns f50-70; off-axis roll
    for f, d in [(0, 0.0), (8, -3.0), (50, -2.6), (70, -0.6), (89, -0.4)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(4, 0.0), (20, 0.8), (60, 0.3), (89, 0.2)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    # the pulse train
    _end, peaks = _laugh_pulses(ctx, f0 + 8, (0.40, 0.35, 0.28, 0.22, 0.16))
    # partial blink riding alternate pulse peaks (eyes nearly shut on peaks)
    for p in peaks[1::2]:
        ctx.key_shape_lr("Eye_Blink_{S}", p - 2, 0.0, 'squeeze', r_offset=1,
                         r_scale=0.9)
        ctx.key_shape_lr("Eye_Blink_{S}", p, 0.22, 'squeeze', r_offset=1,
                         r_scale=0.9)
        ctx.key_shape_lr("Eye_Blink_{S}", p + 4, 0.0, 'squeeze', r_offset=1,
                         r_scale=0.9)
    # aftershock chuckle (single small jaw bob)
    for f, d, v in [(64, 0.0, 0.0), (66, 3.0, 0.2), (71, 0.0, 0.0)]:
        ctx.jaw_open(f0 + f, d, layer='after')
        ctx.key_shape("Jaw_Open", f0 + f, v, 'after')
    # recovery breath: chest sink + nostril
    for f, v in [(74, 0.0), (80, -0.9), (89, -0.3)]:
        ctx.key_bone_axis("CC_Base_Spine02", f0 + f, 'x', v, layer='breath')
    for s, a in (('L', 0.14), ('R', 0.12)):
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 74, 0.0, 'breath')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 79, a, 'breath')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 88, 0.0, 'breath')
    motion.add_blink(ctx, f0 + 70, amp=0.9, close=3, hold=1, open_=6,
                     r_offset=1)


# ---------------------------------------------------------------------------
@clip("giggle", "facial", 1.8, loop=False, framing='face', still_frame=0.45,
      description="Suppressed laugh: smile 0.7 with lips FIGHTING closed "
      "(Mouth_Press 0.3 riding over), jaw pulses tiny 0.12/0.10/0.07 at 5f "
      "spacing, shoulders micro-bounce (body hook), L eye crinkles harder "
      "than R, nose-flare exhale f30. Recovers to a soft smile; blink f39")
def giggle(ctx):
    f0 = ctx.frame_start
    for f, v in [(0, 0.0), (7, 0.70), (40, 0.66), (53, 0.30)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(1, 0.0), (8, 0.62), (40, 0.59), (53, 0.26)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    # suppression press riding over (the fight IS the giggle)
    for f, v in [(2, 0.0), (8, 0.30), (30, 0.24), (44, 0.28), (53, 0.10)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'press')
    for f, v in [(3, 0.0), (9, 0.26), (30, 0.20), (44, 0.24), (53, 0.08)]:
        ctx.key_shape("Mouth_Press_R", f0 + f, v, 'press')
    # asymmetric crinkle: L eye much harder than R
    for f, v in [(4, 0.0), (12, 0.50), (53, 0.34)]:
        ctx.key_shape("Eye_Squint_L", f0 + f, v, 'squint')
    for f, v in [(6, 0.0), (14, 0.30), (53, 0.22)]:
        ctx.key_shape("Eye_Squint_R", f0 + f, v, 'squint')
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 4, 0.0, 'cheeks', r_offset=1,
                     r_scale=0.8)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 12, 0.40, 'cheeks', r_offset=1,
                     r_scale=0.8)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 53, 0.24, 'cheeks', r_offset=1,
                     r_scale=0.8)
    # tiny jaw pulses (bone stays small; lips barely part) + shoulder bounce
    L, fp, peaks = 'gig', f0 + 10, []
    for a in (0.12, 0.10, 0.07):
        ctx.jaw_open(fp - 2, 0.0, layer=L)
        ctx.jaw_open(fp, a * 15.0, layer=L)
        ctx.jaw_open(fp + 3, a * 15.0 * 0.3, layer=L)
        ctx.key_shape("Jaw_Open", fp - 2, 0.0, L)
        ctx.key_shape("Jaw_Open", fp, a, L)
        ctx.key_shape("Jaw_Open", fp + 3, a * 0.3, L)
        peaks.append(fp)
        fp += 5
    ctx.jaw_open(fp, 0.0, layer=L)
    ctx.key_shape("Jaw_Open", fp, 0.0, L)
    for p in peaks:
        for side, s in (('L', 1.0), ('R', 0.8)):
            ctx.clavicle_raise(side, p - 2, 0.0, layer=L)
            ctx.clavicle_raise(side, p, 0.4 * s, layer=L)
            ctx.clavicle_raise(side, p + 3, 0.0, layer=L)
    # nose-flare exhale @f30
    for s, a in (('L', 0.20), ('R', 0.17)):
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 26, 0.0, 'flare')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 30, a, 'flare')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 36, 0.0, 'flare')
    motion.add_blink(ctx, f0 + 38, amp=0.85, close=3, hold=1, open_=5,
                     r_offset=1)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Press_L", f, v, 'jitter'),
        start=f0 + 10, end=f0 + 44, amp=0.03, cycles=(3, 5), step=3, fade=0.2)


# ---------------------------------------------------------------------------
@clip("confused", "facial", 2.5, loop=False, framing='face', still_frame=0.6,
      description="Asymmetry IS the read: L brow knits down 0.5 while R "
      "raises 0.4 (f0-10, R leader), L eye squints 0.3, mouth corner pulls "
      "LEFT 0.2 (dropped-brow side). Head tilts ~2.5deg (6deg body hook) "
      "arriving 6f AFTER the brows. Searching gaze; f45 recompute beat "
      "(brows re-pinch, dominance shifts); blink f45. Ends unresolved")
def confused(ctx):
    f0 = ctx.frame_start
    # LEFT knits down (with the f45 recompute re-deepen)
    for f, v in [(0, 0.0), (8, 0.50), (45, 0.42), (50, 0.50), (74, 0.46)]:
        ctx.key_shape("Brow_Drop_L", f0 + f, v, 'browL')
    for f, v in [(3, 0.0), (9, 0.30), (74, 0.26)]:
        ctx.key_shape("Brow_Compress_L", f0 + f, v, 'browL')
    for f, v in [(4, 0.0), (10, 0.30), (74, 0.26)]:
        ctx.key_shape("Eye_Squint_L", f0 + f, v, 'lids')
    # RIGHT raises (leader), re-arches on the recompute
    for f, v in [(0, 0.0), (7, 0.40), (45, 0.34), (50, 0.46), (74, 0.42)]:
        ctx.key_shape("Brow_Raise_Outer_R", f0 + f, v, 'browR')
    for f, v in [(0, 0.0), (7, 0.35), (45, 0.30), (50, 0.40), (74, 0.36)]:
        ctx.key_shape("Brow_Raise_Inner_R", f0 + f, v, 'browR')
    # mouth pulls left + purses that corner
    for f, v in [(4, 0.0), (12, 0.20), (74, 0.17)]:
        ctx.key_shape("Mouth_L", f0 + f, v, 'mouth')
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 6, 0.0, 'mouth', r_offset=1,
                     r_scale=0.8)
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 14, 0.20, 'mouth', r_offset=1,
                     r_scale=0.8)
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 74, 0.16, 'mouth', r_offset=1,
                     r_scale=0.8)
    for f, v in [(6, 0.0), (14, 0.10), (74, 0.09)]:
        ctx.key_shape("Mouth_Pucker_Up_L", f0 + f, v, 'mouth')
    # head tilt follows the brows by 6f (~2.5deg facial; 6deg body hook)
    for f, d in [(6, 0.0), (12, 2.3), (45, 2.0), (52, 2.6), (74, 2.4)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(8, 0.0), (14, -0.8), (74, -0.6)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='head')
    # searching gaze: iris via bones, lid follow via gaze_to look keys
    _aim(ctx, f0 + 0, 0.0, 0.0)
    motion.gaze_to(ctx, f0 + 10, 0.20, 0.10, layer='gaze')
    _aim(ctx, f0 + 12, 0.20, 0.10)
    motion.gaze_to(ctx, f0 + 34, -0.14, 0.14, from_dx=0.20, from_dy=0.10,
                   layer='gaze')
    _aim(ctx, f0 + 36, -0.14, 0.14)
    motion.gaze_to(ctx, f0 + 58, 0.0, 0.0, from_dx=-0.14, from_dy=0.14,
                   layer='gaze')
    _aim(ctx, f0 + 60, 0.0, 0.0)
    # 'wait... what?' brow pulse (additive delta) f22
    for f, v in [(18, 0.0), (22, 0.06), (28, 0.0)]:
        ctx.key_shape("Brow_Raise_Outer_R", f0 + f, v, 'pulse')
    motion.add_blink(ctx, f0 + 44, amp=0.9, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_L", f, v, 'waver'),
        start=f0 + 12, end=f0 + 74, amp=0.02, cycles=(2, 3), step=5, fade=0.15)


# ---------------------------------------------------------------------------
@clip("curious", "facial", 2.0, loop=False, framing='face', still_frame=0.55,
      description="Head tilts ~2.5deg WITH brows raising 0.4 (7deg body "
      "hook), lids widen 0.2, lips part 0.1 (key-only, teeth shut). Forward "
      "lean ~1.2deg (1cm body hook) toward the interesting thing. Gaze locks "
      "target with focus-grade stillness; one brow higher; micro re-aim f38")
def curious(ctx):
    f0 = ctx.frame_start
    # brows raise WITH the tilt; L higher than R (asym height)
    for f, v in [(0, 0.0), (8, 0.42), (35, 0.38), (40, 0.44), (59, 0.40)]:
        ctx.key_shape("Brow_Raise_Inner_L", f0 + f, v, 'brow')
        ctx.key_shape("Brow_Raise_Outer_L", f0 + f, v * 0.9, 'brow')
    for f, v in [(1, 0.0), (9, 0.34), (35, 0.30), (40, 0.36), (59, 0.33)]:
        ctx.key_shape("Brow_Raise_Inner_R", f0 + f, v, 'brow')
        ctx.key_shape("Brow_Raise_Outer_R", f0 + f, v * 0.9, 'brow')
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 4, 0.0, 'lids', r_offset=1,
                     r_scale=0.88)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 12, 0.20, 'lids', r_offset=1,
                     r_scale=0.88)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 59, 0.18, 'lids', r_offset=1,
                     r_scale=0.88)
    for f, v in [(6, 0.0), (12, 0.10), (59, 0.09)]:
        ctx.key_shape("Mouth_Drop_Lower", f0 + f, v, 'mouth')
    # head tilt (roll) + slight turn toward target; micro re-aim @f38
    for f, d in [(0, 0.0), (8, 2.5), (33, 2.3), (38, 2.6), (59, 2.4)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(2, 0.0), (8, -1.2), (35, -1.0), (40, -1.4), (59, -1.2)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='head')
    # forward lean ~1cm (spine hook, keyed subtly)
    ctx.pitch("CC_Base_Spine02", f0 + 0, 0.0, layer='lean')
    ctx.pitch("CC_Base_Spine02", f0 + 10, 1.2, layer='lean')
    ctx.pitch("CC_Base_Spine02", f0 + 59, 1.1, layer='lean')
    # focus-grade gaze stillness: locked, faint drift only
    _aim(ctx, f0 + 0, 0.0, 0.02)
    _aim(ctx, f0 + 30, 0.03, 0.0)
    _aim(ctx, f0 + 59, 0.0, 0.01)
    motion.add_blink(ctx, f0 + 28, amp=0.85, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Raise_Inner_L", f, v, 'waver'),
        start=f0 + 12, end=f0 + 59, amp=0.02, cycles=(2, 3), step=5, fade=0.2)


# ---------------------------------------------------------------------------
@clip("excited", "facial", 2.0, loop=False, framing='face', still_frame=0.5,
      description="Brows up 0.6 fast (4f), eyes wide 0.5 + dilate, smile "
      "builds in TWO steps (0.5 f6, 0.9 f14) with jaw cracking 0.2 (bone 5deg "
      "+ key), double eyebrow flash f18/f32, quick double head-nod f10/f18 "
      "(body hook). Micro tremor 0.03 on brows/eyes in hold. Pairs with "
      "breathing_excited layer. Asymmetric smile; blink f27; ends holding")
def excited(ctx):
    f0 = ctx.frame_start
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 0, 0.0, 'brow', r_offset=1,
                     r_scale=0.92)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 4, 0.60, 'brow', r_offset=1,
                     r_scale=0.92)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 59, 0.52, 'brow', r_offset=1,
                     r_scale=0.92)
    ctx.key_shape_lr("Brow_Raise_Outer_{S}", f0 + 0, 0.0, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Outer_{S}", f0 + 4, 0.50, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Outer_{S}", f0 + 59, 0.44, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 2, 0.0, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 6, 0.50, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 59, 0.44, 'lids', r_offset=1,
                     r_scale=0.9)
    for f, v in [(2, 0.0), (8, 0.25), (59, 0.22)]:
        ctx.key_shape("Eye_Pupil_Dilate", f0 + f, v, 'pupil')
    # smile two-step + jaw crack
    for f, v in [(2, 0.0), (6, 0.50), (14, 0.90), (18, 0.86), (59, 0.84)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(3, 0.0), (7, 0.45), (15, 0.83), (19, 0.80), (59, 0.78)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    for f, v in [(6, 0.0), (16, 0.20), (59, 0.18)]:
        ctx.key_shape("Mouth_Smile_Sharp_L", f0 + f, v, 'smile')
    for f, d in [(6, 0.0), (14, 5.0), (18, 4.4), (59, 4.4)]:
        ctx.jaw_open(f0 + f, d)
    for f, v in [(6, 0.0), (14, 0.20), (18, 0.18), (59, 0.18)]:
        ctx.key_shape("Jaw_Open", f0 + f, v, 'jaw')
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 6, 0.0, 'cheeks', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 16, 0.40, 'cheeks', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 59, 0.36, 'cheeks', r_offset=1,
                     r_scale=0.9)
    # double head nod (<=2.5) + off-axis roll
    for cf, d in [(10, 1.8), (18, 2.2)]:
        ctx.pitch("CC_Base_Head", f0 + cf - 4, 0.0, layer='nod')
        ctx.pitch("CC_Base_Head", f0 + cf, d, layer='nod')
        ctx.pitch("CC_Base_Head", f0 + cf + 6, 0.0, layer='nod')
    ctx.roll("CC_Base_Head", f0 + 12, 0.0, layer='nod')
    ctx.roll("CC_Base_Head", f0 + 16, 0.5, layer='nod')
    ctx.roll("CC_Base_Head", f0 + 24, 0.0, layer='nod')
    # double eyebrow flash (additive delta) f18, f32
    for cf in (18, 32):
        ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + cf - 4, 0.0, 'flash',
                         r_offset=1, r_scale=0.9)
        ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + cf, 0.08, 'flash',
                         r_offset=1, r_scale=0.9)
        ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + cf + 6, 0.0, 'flash',
                         r_offset=1, r_scale=0.9)
    motion.add_blink(ctx, f0 + 26, amp=0.8, close=2, hold=1, open_=5,
                     r_offset=1)
    # sparkle: eye-wide tremor + smile breathe
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Eye_Wide_L", f, v, 'tremor'),
        start=f0 + 8, end=f0 + 59, amp=0.03, cycles=(3, 5), step=3, fade=0.2)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_L", f, v, 'waver'),
        start=f0 + 18, end=f0 + 59, amp=0.03, cycles=(2, 3), step=4, fade=0.2)


# ---------------------------------------------------------------------------
@clip("angry", "facial", 2.0, loop=False, framing='face', still_frame=0.55,
      description="FAST 5f slam: brows down 0.8 (L 0.80 / R 0.72 asym) + "
      "pinch, nostrils flare 0.3, lips tighten/press 0.5, jaw sets "
      "(Jaw_Forward 0.15 f8). Chin drops ~2.5deg — bull stare under the brow "
      "(3deg body hook). TENSION IN STILLNESS: hold nearly frozen with 0.02 "
      "brow/jaw tremor. Glare = Eye_Squint 0.3 over Eye_Wide 0.12. NO blink "
      "(suppressed = menace). Mouth stays closed. Ends holding the glare")
def angry(ctx):
    f0 = ctx.frame_start
    # brows slam (asymmetric depth), 5f
    for f, v in [(0, 0.0), (5, 0.80), (59, 0.74)]:
        ctx.key_shape("Brow_Drop_L", f0 + f, v, 'brow')
    for f, v in [(1, 0.0), (6, 0.72), (59, 0.67)]:
        ctx.key_shape("Brow_Drop_R", f0 + f, v, 'brow')
    ctx.key_shape_lr("Brow_Compress_{S}", f0 + 1, 0.0, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Compress_{S}", f0 + 6, 0.50, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Compress_{S}", f0 + 59, 0.46, 'brow', r_offset=1,
                     r_scale=0.9)
    # glare: squint NARROWS the eyes (dominant), a hint of wide underneath
    # for lower-lid tension (too much Eye_Wide reads bug-eyed/manic)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 2, 0.0, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 7, 0.42, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 59, 0.40, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 2, 0.0, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 7, 0.08, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Wide_{S}", f0 + 59, 0.07, 'lids', r_offset=1,
                     r_scale=0.9)
    # nose sneer + crease
    ctx.key_shape_lr("Nose_Sneer_{S}", f0 + 2, 0.0, 'nose', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Nose_Sneer_{S}", f0 + 6, 0.28, 'nose', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Nose_Sneer_{S}", f0 + 59, 0.26, 'nose', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Nose_Crease_{S}", f0 + 2, 0.0, 'nose', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Nose_Crease_{S}", f0 + 6, 0.30, 'nose', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Nose_Crease_{S}", f0 + 59, 0.28, 'nose', r_offset=1,
                     r_scale=0.85)
    # nostril breathing pulse 0.30->0.22->0.30 across the hold
    ctx.key_shape("Nose_Nostril_Dilate_L", f0 + 2, 0.0, 'breath')
    ctx.key_shape("Nose_Nostril_Dilate_R", f0 + 2, 0.0, 'breath')
    for f, v in [(6, 0.30), (20, 0.22), (34, 0.30), (48, 0.24), (59, 0.28)]:
        ctx.key_shape("Nose_Nostril_Dilate_L", f0 + f, v, 'breath')
        ctx.key_shape("Nose_Nostril_Dilate_R", f0 + f + 1, v * 0.9, 'breath')
    # mouth: SEALED lips, corners pulled DOWN (closed — no teeth, no grin;
    # Mouth_Tighten stays low or it splays the corners into a grimace-smile,
    # and Mouth_Down_Lower is omitted entirely — it parted the lips)
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 2, 0.0, 'mouth', r_offset=1,
                     r_scale=0.86)
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 7, 0.45, 'mouth', r_offset=1,
                     r_scale=0.86)
    ctx.key_shape_lr("Mouth_Press_{S}", f0 + 59, 0.42, 'mouth', r_offset=1,
                     r_scale=0.86)
    for f, v in [(4, 0.0), (10, 0.36), (59, 0.32)]:
        ctx.key_shape("Mouth_Frown_L", f0 + f, v, 'mouth')
        ctx.key_shape("Mouth_Frown_R", f0 + f + 1, v * 0.85, 'mouth')
    for f, v in [(4, 0.0), (10, 0.14), (59, 0.12)]:
        ctx.key_shape("Mouth_Down", f0 + f, v, 'mouth')       # whole mouth down
    ctx.key_shape_lr("Mouth_Tighten_{S}", f0 + 2, 0.0, 'mouth', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Mouth_Tighten_{S}", f0 + 8, 0.12, 'mouth', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Mouth_Tighten_{S}", f0 + 59, 0.11, 'mouth', r_offset=1,
                     r_scale=0.85)
    for f, v in [(4, 0.0), (8, 0.15), (59, 0.15)]:
        ctx.key_shape("Jaw_Forward", f0 + f, v, 'jaw')
    # chin drops (bull stare), off-axis roll
    for f, d in [(0, 0.0), (6, 2.5), (28, 2.3), (59, 2.4)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(2, 0.0), (8, -0.4), (59, -0.4)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='head')
    # tension in stillness: 0.02 tremor on brow + jaw clench (NO blink)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_L", f, v, 'tremor'),
        start=f0 + 8, end=f0 + 59, amp=0.02, cycles=(3, 5), step=3, fade=0.15)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Tighten_L", f, v, 'tremor'),
        start=f0 + 10, end=f0 + 59, amp=0.02, cycles=(2, 5), step=3, fade=0.15)


# ---------------------------------------------------------------------------
@clip("disappointed", "facial", 2.5, loop=False, framing='face',
      still_frame=0.7,
      description="EXHALE-LED (the order is the read): sigh chest-drop first "
      "(f0-12, breathing_tired body hook), face follows (inner brows 0.3, "
      "press-then-frown asymmetric f8-24), single small head shake ~2.5deg "
      "f14-22 (body hook), gaze breaks down-and-away f18. Ends looking away, "
      "lids 0.2; heavy down-cast blink f41")
def disappointed(ctx):
    f0 = ctx.frame_start
    # 1) EXHALE first: chest/shoulders drop
    ctx.pitch("CC_Base_Spine02", f0 + 0, 0.0, layer='sigh')
    ctx.pitch("CC_Base_Spine02", f0 + 12, 1.4, layer='sigh')
    ctx.pitch("CC_Base_Spine02", f0 + 40, 1.1, layer='sigh')
    ctx.pitch("CC_Base_Spine02", f0 + 74, 1.2, layer='sigh')
    for side, d in (('L', -0.9), ('R', -0.8)):
        ctx.clavicle_raise(side, f0 + 0, 0.0, layer='sigh')
        ctx.clavicle_raise(side, f0 + 14, d, layer='sigh')
        ctx.clavicle_raise(side, f0 + 74, d * 0.85, layer='sigh')
    for s, a in (('L', 0.22), ('R', 0.19)):
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 2, 0.0, 'sigh')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 8, a, 'sigh')
        ctx.key_shape(f"Nose_Nostril_Dilate_{s}", f0 + 22, 0.0, 'sigh')
    # 2) face follows f8-24
    for f, v in [(8, 0.0), (20, 0.30), (74, 0.26)]:
        ctx.key_shape("Brow_Raise_Inner_L", f0 + f, v, 'brow')
    for f, v in [(10, 0.0), (22, 0.26), (74, 0.22)]:
        ctx.key_shape("Brow_Raise_Inner_R", f0 + f, v, 'brow')
    # press briefly, then a CLEAR frown (0.42 — a weak frown reads neutral on
    # this toon; diag confirmed Mouth_Frown 0.40 is a clean closed downturn)
    for f, v in [(8, 0.0), (14, 0.26), (22, 0.06), (74, 0.05)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'mouth')
    for f, v in [(9, 0.0), (15, 0.22), (23, 0.05), (74, 0.04)]:
        ctx.key_shape("Mouth_Press_R", f0 + f, v, 'mouth')
    for f, v in [(14, 0.0), (24, 0.42), (74, 0.38)]:
        ctx.key_shape("Mouth_Frown_L", f0 + f, v, 'mouth')
    for f, v in [(16, 0.0), (26, 0.35), (74, 0.31)]:
        ctx.key_shape("Mouth_Frown_R", f0 + f, v, 'mouth')
    for f, v in [(14, 0.0), (24, 0.14), (74, 0.12)]:
        ctx.key_shape("Mouth_Down", f0 + f, v, 'mouth')      # whole-mouth droop
    # 3) single head shake (one only -> not 'no') + a sink
    for f, d in [(14, 0.0), (18, 2.6), (22, -0.6), (30, 0.0)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='shake')
    for f, d in [(12, 0.0), (30, 1.8), (74, 1.9)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    # 4) gaze breaks down-and-away, heavy lids
    _aim(ctx, f0 + 16, 0.0, 0.0)
    motion.gaze_to(ctx, f0 + 22, 0.16, -0.22, from_dx=0.0, from_dy=0.0,
                   layer='gaze')
    _aim(ctx, f0 + 24, 0.16, -0.22)
    _aim(ctx, f0 + 50, 0.14, -0.24)
    _aim(ctx, f0 + 74, 0.15, -0.23)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 16, 0.0, 'lids', r_offset=1,
                     r_scale=0.93)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 30, 0.20, 'lids', r_offset=1,
                     r_scale=0.93)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 74, 0.20, 'lids', r_offset=1,
                     r_scale=0.93)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 18, 0.0, 'gaze', r_scale=0.95)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 26, 0.22, 'gaze', r_scale=0.95)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 74, 0.22, 'gaze', r_scale=0.95)
    motion.add_blink(ctx, f0 + 40, amp=0.85, close=4, hold=1, open_=6,
                     r_offset=1, eye_down=0.05)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Frown_L", f, v, 'waver'),
        start=f0 + 26, end=f0 + 74, amp=0.02, cycles=(2, 3), step=5, fade=0.15)


# ---------------------------------------------------------------------------
@clip("embarrassed", "facial", 2.5, loop=False, framing='face',
      still_frame=0.6,
      description="Gaze breaks down-RIGHT FIRST (f0-4, aversion precedes the "
      "smile — order carries the meaning). Suppressed smile: corners 0.4 "
      "while lips press 0.3 against it (f6-16), cheeks 0.4, apologetic inner "
      "brows. Head turns ~2.5deg away + 2.2deg down (8/4deg body hook, "
      "f8-20). Quick blink f23. Body hook: hand-to-neck (scratch_head). "
      "Ends holding averted")
def embarrassed(ctx):
    f0 = ctx.frame_start
    # 1) gaze aversion FIRST (down-right)
    _aim(ctx, f0 + 0, 0.0, 0.0)
    motion.gaze_to(ctx, f0 + 4, -0.22, -0.20, layer='gaze')
    _aim(ctx, f0 + 6, -0.22, -0.20)
    _aim(ctx, f0 + 40, -0.20, -0.22)
    _aim(ctx, f0 + 74, -0.21, -0.21)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 2, 0.0, 'gaze', r_scale=0.95)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 8, 0.20, 'gaze', r_scale=0.95)
    ctx.key_shape_lr("Eye_{S}_Look_Down", f0 + 74, 0.20, 'gaze', r_scale=0.95)
    # 2) suppressed smile (corners pull while lips press against it)
    for f, v in [(6, 0.0), (16, 0.40), (74, 0.36)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(7, 0.0), (17, 0.34), (74, 0.30)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    for f, v in [(6, 0.0), (14, 0.30), (30, 0.22), (74, 0.20)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'press')
    for f, v in [(7, 0.0), (15, 0.26), (30, 0.18), (74, 0.16)]:
        ctx.key_shape("Mouth_Press_R", f0 + f, v, 'press')
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 6, 0.0, 'cheeks', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 16, 0.40, 'cheeks', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 74, 0.36, 'cheeks', r_offset=1,
                     r_scale=0.85)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 6, 0.0, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 16, 0.18, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 74, 0.15, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 6, 0.0, 'lids', r_offset=1,
                     r_scale=0.93)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 18, 0.14, 'lids', r_offset=1,
                     r_scale=0.93)
    ctx.key_shape_lr("Eye_Blink_{S}", f0 + 74, 0.13, 'lids', r_offset=1,
                     r_scale=0.93)
    # 3) head turns away (yaw) + down (pitch), ~2.5 facial; off-axis roll
    for f, d in [(8, 0.0), (20, -2.5), (74, -2.4)]:
        ctx.yaw("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(8, 0.0), (20, 2.2), (74, 2.1)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(10, 0.0), (22, 0.6), (74, 0.5)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    # 4) one quick blink @f22
    motion.add_blink(ctx, f0 + 22, amp=1.0, close=3, hold=1, open_=5,
                     r_offset=1)
    # peek smile pulse + waver
    for f, v in [(48, 0.0), (52, 0.06), (60, 0.0)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'peek')
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Press_L", f, v, 'waver'),
        start=f0 + 18, end=f0 + 74, amp=0.02, cycles=(2, 3), step=5, fade=0.15)


# ---------------------------------------------------------------------------
@clip("proud", "facial", 2.5, loop=False, framing='face', still_frame=0.55,
      description="Chin rises ~2.5deg + chest lifts (5/2deg body hooks, "
      "f0-14, slow controlled). Closed-lip smile 0.4 blooms over 12f (NO "
      "Jaw_Open — teeth hidden), slight Jaw_Forward set, lower-lid warmth "
      "0.1, brows level +0.05. ONE slow satisfied blink f31 (close6/hold2/"
      "open8). Tall hold, reduced sway, corners waver +-0.03; ends holding")
def proud(ctx):
    f0 = ctx.frame_start
    # chin up (facial ~2.5, hook 5) + off-axis roll
    for f, d in [(0, 0.0), (14, -2.5), (40, -2.4), (74, -2.4)]:
        ctx.pitch("CC_Base_Head", f0 + f, d, layer='head')
    for f, d in [(2, 0.0), (16, 0.5), (74, 0.4)]:
        ctx.roll("CC_Base_Head", f0 + f, d, layer='head')
    # chest lift (spine extension) + clavicle (body hook)
    ctx.pitch("CC_Base_Spine02", f0 + 0, 0.0, layer='chest')
    ctx.pitch("CC_Base_Spine02", f0 + 14, -1.4, layer='chest')
    ctx.pitch("CC_Base_Spine02", f0 + 74, -1.3, layer='chest')
    for side, d in (('L', 0.7), ('R', 0.6)):
        ctx.clavicle_raise(side, f0 + 0, 0.0, layer='chest')
        ctx.clavicle_raise(side, f0 + 16, d, layer='chest')
        ctx.clavicle_raise(side, f0 + 74, d * 0.9, layer='chest')
    # closed-lip smile (no jaw)
    for f, v in [(0, 0.0), (12, 0.40), (40, 0.38), (74, 0.39)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'smile')
    for f, v in [(1, 0.0), (13, 0.34), (40, 0.33), (74, 0.34)]:
        ctx.key_shape("Mouth_Smile_R", f0 + f, v, 'smile')
    for f, v in [(4, 0.0), (16, 0.10), (74, 0.10)]:
        ctx.key_shape("Jaw_Forward", f0 + f, v, 'jaw')
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 2, 0.0, 'cheeks', r_offset=1,
                     r_scale=0.88)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 14, 0.18, 'cheeks', r_offset=1,
                     r_scale=0.88)
    ctx.key_shape_lr("Cheek_Raise_{S}", f0 + 74, 0.16, 'cheeks', r_offset=1,
                     r_scale=0.88)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 2, 0.0, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 16, 0.05, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + 74, 0.05, 'brow', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 4, 0.0, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 16, 0.10, 'lids', r_offset=1,
                     r_scale=0.9)
    ctx.key_shape_lr("Eye_Squint_{S}", f0 + 74, 0.10, 'lids', r_offset=1,
                     r_scale=0.9)
    # one slow satisfied blink
    motion.add_blink(ctx, f0 + 30, amp=0.95, close=6, hold=2, open_=8,
                     r_offset=1, eye_down=0.06)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_L", f, v, 'waver'),
        start=f0 + 16, end=f0 + 74, amp=0.03, cycles=(2, 3), step=5, fade=0.2)
    motion.head_micro_sway(ctx, start=f0 + 16, end=f0 + 74, amp_deg=0.3)
