"""Listening set — 6 Tier-2 loop clips (owner: facial). 8.0s / 240f each.

listening_relaxed     neutral-alive + soft acknowledgment nods
listening_interested  engaged baseline (brows/lids up), lean-in, brow flash
listening_confused    intermittent asymmetric brow pinch, tilt drift, aborted nod
listening_thinking    gaze breaks up-left + re-engagement, furrow on the away-dwell
listening_happy       soft-smile baseline, faster warm nod cadence, bloom beat
listening_serious     damped stillness (60% micro), 0.2 furrow, two slow nods

Spec: animations/library_spec.json. Per the Tier-2 brief these clips OWN
their small head motion (<=2.5deg nods/tilts, keyed on CC_Base_Head directly
— no marker handoff). Every clip is a seam-clean loop: constant baselines
are held at frame_start AND frame_end; all transient events return to the
baseline with >=15f margin from both boundaries; the ambient gaze drift, lid
tone and head sway are integer-cycle loop_noise (periodic by construction).
Designed to run WITH the additive micro layer (face_micro_engaged etc.).

BLINK_META (baked-blink frames + runtime notes) is stamped into meta.json by
patch_facial_tier2_meta.py — the runtime blink scheduler must suppress
procedural blinks over these baked ones.
"""
from anim_framework.clips import clip
from anim_framework import motion

EYE_L, EYE_R = "CC_Base_L_Eye", "CC_Base_R_Eye"

BLINK_META = {
    "listening_relaxed": {"blinks": [56, 151, 206],
        "note": "3 baked blinks, non-metronomic gaps (3.2s/1.8s)."},
    "listening_interested": {"blinks": [76, 196],
        "note": "2 baked blinks; brighter engaged lids."},
    "listening_confused": {"blinks": [61, 146, 201],
        "note": "3 baked blinks around the pinch beats."},
    "listening_thinking": {"blinks": [31, 123, 206],
        "note": "Blinks are SLOW (thinking); f123 masks the gaze return."},
    "listening_happy": {"blinks": [71, 176],
        "note": "2 baked blinks under the warm smile."},
    "listening_serious": {"blinks": [71, 216],
        "note": "Blink interval STRETCHED to ~5s (serious). Runtime blink "
                "scheduler MUST use the 5-6s cadence, not the default rate."},
}


def _aim(ctx, frame, dx, dy, r_scale=1.0, layer='eye_bones'):
    z = dx * 16.0
    x = -dy * (12.0 if dy >= 0 else 13.0)
    for bone, s in ((EYE_L, 1.0), (EYE_R, r_scale)):
        ctx.key_bone_axis(bone, frame, 'z', z * s, layer=layer)
        ctx.key_bone_axis(bone, frame, 'x', x * s, layer=layer)


def _drift(ctx, mag=0.6):
    """Ambient iris fixation drift on the eye bones (loop-safe, on speaker)."""
    for bone, sc in ((EYE_L, 1.0), (EYE_R, 0.9)):
        motion.loop_noise(ctx, lambda f, v, b=bone: ctx.key_bone_axis(
            b, f, 'z', v, layer='drift'), amp=mag * sc, cycles=(2, 3), step=8)
        motion.loop_noise(ctx, lambda f, v, b=bone: ctx.key_bone_axis(
            b, f, 'x', v, layer='drift'), amp=mag * 0.6 * sc,
            cycles=(3, 4), step=8)


def _lid_tone(ctx, base_l=0.03, base_r=0.028, scale=1.0):
    """Breathing lid tone so the lids are never frozen (loop-safe)."""
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Eye_Blink_L", f, base_l + v, 'lid_tone'),
        amp=0.012 * scale, cycles=(2, 3), step=6)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Eye_Blink_R", f, base_r + v, 'lid_tone'),
        amp=0.010 * scale, cycles=(3, 4), step=6)


def _nod(ctx, cf, deg, dur=14, wob=0.35):
    """Acknowledgment nod (<=2.5deg), returns to 0 with an off-axis yaw wobble
    so it's never a pure-pitch metronome. Side of the wobble alternates."""
    ctx.pitch("CC_Base_Head", cf - 4, 0.0, layer='nod')
    ctx.pitch("CC_Base_Head", cf, deg, layer='nod')
    ctx.pitch("CC_Base_Head", cf + int(dur * 0.55), -0.12 * deg, layer='nod')
    ctx.pitch("CC_Base_Head", cf + dur, 0.0, layer='nod')
    side = 1.0 if (cf // 9) % 2 else -1.0
    ctx.yaw("CC_Base_Head", cf - 2, 0.0, layer='nod')
    ctx.yaw("CC_Base_Head", cf + int(dur * 0.4), wob * side, layer='nod')
    ctx.yaw("CC_Base_Head", cf + dur + 2, 0.0, layer='nod')


def _tilt(ctx, cf, deg, up=18, hold=24):
    """Head roll drift out to `deg` and back to level (confused/curious)."""
    ctx.roll("CC_Base_Head", cf, 0.0, layer='tilt')
    ctx.roll("CC_Base_Head", cf + up, deg, layer='tilt')
    ctx.roll("CC_Base_Head", cf + up + hold, deg * 0.7, layer='tilt')
    ctx.roll("CC_Base_Head", cf + up + hold + up, 0.0, layer='tilt')


# ---------------------------------------------------------------------------
@clip("listening_relaxed", "listening", 8.0, loop=True, framing='face',
      still_frame=0.4,
      description="neutral-alive palette + gaze held on speaker with fixation "
      "drift. Soft acknowledgment nods 0.6-1deg at f70/f160/f210 (irregular "
      "cadence, not a timer). Lips relaxed, tiny part 0.05 with a lip-press "
      "beat f120. Soft lid tone. Seam-clean loop")
def listening_relaxed(ctx):
    f0, fe = ctx.frame_start, ctx.frame_end
    _drift(ctx, mag=0.7)
    _lid_tone(ctx)
    motion.head_micro_sway(ctx, amp_deg=0.4)
    # relaxed tiny lip part held, with a waver so the mouth is never dead
    ctx.key_shape("Mouth_Drop_Lower", f0, 0.05, 'mouth')
    ctx.key_shape("Mouth_Drop_Lower", fe, 0.05, 'mouth')
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Drop_Lower", f, v, 'lipwaver'), amp=0.02, cycles=(2, 3), step=6)
    # single 'taking it in' lip-press beat
    for f, v in [(112, 0.0), (120, 0.06), (134, 0.0)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'beat')
        ctx.key_shape("Mouth_Press_R", f0 + f + 2, v * 0.7, 'beat')
    # irregular acknowledgment nods (varied amplitude + duration)
    _nod(ctx, f0 + 70, 0.9, dur=15)
    _nod(ctx, f0 + 160, 0.6, dur=12)
    _nod(ctx, f0 + 210, 1.0, dur=16)
    motion.add_blink(ctx, f0 + 55, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 150, amp=0.85, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 205, amp=0.9, close=3, hold=1, open_=6,
                     r_offset=1)


# ---------------------------------------------------------------------------
@clip("listening_interested", "listening", 8.0, loop=True, framing='face',
      still_frame=0.45,
      description="Engaged baseline: brows +0.15, lids +0.10 (Eye_Wide), "
      "slight lean-in ~1deg (1cm body hook). Bigger nods 2-3deg f70/f150 "
      "(double at f150 = agreement spike)/f205, brow flash +0.30 f100 "
      "(something landed), one saccade (+3deg) f130 back f150. Gaze locked "
      "with focus-grade stillness. Seam-clean loop")
def listening_interested(ctx):
    f0, fe = ctx.frame_start, ctx.frame_end
    _drift(ctx, mag=0.4)                       # tighter, focus-grade
    _lid_tone(ctx, base_l=0.02, base_r=0.018)
    motion.head_micro_sway(ctx, amp_deg=0.35)
    # engaged baseline held across the loop
    for pat, v, off, sc in (("Brow_Raise_Inner_{S}", 0.15, 0, 0.85),
                            ("Brow_Raise_Outer_{S}", 0.08, 0, 0.85),
                            ("Eye_Wide_{S}", 0.10, 1, 0.8)):
        ctx.key_shape_lr(pat, f0, v, 'base', r_offset=off, r_scale=sc)
        ctx.key_shape_lr(pat, fe, v, 'base', r_offset=off, r_scale=sc)
    # lean-in (spine hook, subtle constant lean)
    ctx.pitch("CC_Base_Spine02", f0, 1.0, 'lean')
    ctx.pitch("CC_Base_Spine02", fe, 1.0, 'lean')
    # brow flash 'that landed' (additive delta) f100
    for f, v in [(94, 0.0), (100, 0.30), (114, 0.0)]:
        ctx.key_shape_lr("Brow_Raise_Inner_{S}", f0 + f, v, 'flash',
                         r_offset=1, r_scale=0.88)
        ctx.key_shape_lr("Brow_Raise_Outer_{S}", f0 + f, v * 0.8, 'flash',
                         r_offset=1, r_scale=0.88)
    # nods: single, DOUBLE (agreement spike), single — unequal sizes
    _nod(ctx, f0 + 70, 2.2, dur=16)
    _nod(ctx, f0 + 150, 2.6, dur=14)
    _nod(ctx, f0 + 168, 1.8, dur=12)           # the second half of the double
    _nod(ctx, f0 + 205, 2.4, dur=15)
    # one small interest saccade toward the speaker's gesture and back
    _aim(ctx, f0 + 126, 0.0, 0.0)
    motion.gaze_to(ctx, f0 + 130, 0.18, 0.02, layer='gaze')
    _aim(ctx, f0 + 132, 0.18, 0.02)
    motion.gaze_to(ctx, f0 + 150, 0.0, 0.0, from_dx=0.18, from_dy=0.02,
                   layer='gaze')
    _aim(ctx, f0 + 152, 0.0, 0.0)
    motion.add_blink(ctx, f0 + 75, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 195, amp=0.85, close=3, hold=1, open_=6,
                     r_offset=1)


# ---------------------------------------------------------------------------
@clip("listening_confused", "listening", 8.0, loop=True, framing='face',
      still_frame=0.5,
      description="Intermittent asymmetric brow pinch (L drop 0.3 f40, deeper "
      "0.45 f120 = the 'wait, what?' beat) with R outer-raise counter and "
      "one-sided L squint riding each. Head tilt drifts 0-2.5deg (5deg body "
      "hook) and re-levels. Mouth corner tug 0.15 f125. Gaze STAYS on speaker "
      "(drift only). A near-nod ABORTS halfway at f180. Seam-clean loop")
def listening_confused(ctx):
    f0 = ctx.frame_start
    _drift(ctx, mag=0.6)
    _lid_tone(ctx)
    motion.head_micro_sway(ctx, amp_deg=0.35)

    def _pinch(cf, dropL, up, dur):
        for df, s in ((0, 0.0), (int(dur * 0.35), 1.0),
                      (int(dur * 0.7), 0.9), (dur, 0.0)):
            ctx.key_shape("Brow_Drop_L", cf + df, dropL * s, 'pinchL')
            ctx.key_shape("Brow_Compress_L", cf + df, dropL * 0.6 * s, 'pinchL')
            ctx.key_shape("Eye_Squint_L", cf + df, dropL * 0.7 * s, 'pinchL')
            ctx.key_shape("Brow_Raise_Outer_R", cf + df + 1, up * s, 'pinchR')
            ctx.key_shape("Brow_Raise_Inner_R", cf + df + 1, up * 0.7 * s,
                          'pinchR')
    _pinch(f0 + 34, 0.30, 0.26, 30)            # first mild pinch
    _pinch(f0 + 114, 0.45, 0.38, 34)           # the deeper 'wait, what?' beat
    # tilt drifts out and re-levels around each pinch (5deg body hook)
    _tilt(ctx, f0 + 40, 2.3, up=16, hold=22)
    _tilt(ctx, f0 + 120, -2.5, up=16, hold=24)
    # mouth corner tug f125
    for f, v in [(118, 0.0), (125, 0.15), (140, 0.0)]:
        ctx.key_shape("Mouth_L", f0 + f, v, 'mouth')
        ctx.key_shape("Mouth_Press_L", f0 + f, v * 0.7, 'mouth')
    # near-nod that aborts halfway (started to agree, didn't) @f180
    ctx.pitch("CC_Base_Head", f0 + 176, 0.0, 'abort')
    ctx.pitch("CC_Base_Head", f0 + 181, 1.4, 'abort')
    ctx.pitch("CC_Base_Head", f0 + 185, 0.5, 'abort')      # stalls, no follow-through
    ctx.pitch("CC_Base_Head", f0 + 192, 0.0, 'abort')
    motion.add_blink(ctx, f0 + 60, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 145, amp=0.85, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 200, amp=0.9, close=3, hold=1, open_=6,
                     r_offset=1)


# ---------------------------------------------------------------------------
@clip("listening_thinking", "listening", 8.0, loop=True, framing='face',
      still_frame=0.4,
      description="Gaze on speaker f0-55, breaks up-left f60 (saccade + 1.5s "
      "dwell = processing), RE-ENGAGES f105 (the return is the acting). Brow "
      "settles 0.2 furrow during the away-dwell, releases fully on return. "
      "Lip press cycle f70-95. Slow deliberate 'I see' nod 2deg f200. Second "
      "shorter gaze-break f180 (0.8s). Slow blinks. Seam-clean loop")
def listening_thinking(ctx):
    f0 = ctx.frame_start
    _drift(ctx, mag=0.5)
    _lid_tone(ctx)
    motion.head_micro_sway(ctx, amp_deg=0.35)

    def _break(cf, back, dx, dy, furrow):
        # saccade away, dwell with micro-drift, return; furrow rises then
        # releases FULLY by the return (must not persist)
        _aim(ctx, cf - 2, 0.0, 0.0)
        motion.gaze_to(ctx, cf + 2, dx, dy, layer='gaze')
        _aim(ctx, cf + 4, dx, dy)
        _aim(ctx, cf + int((back - cf) * 0.5), dx + 0.03, dy - 0.02)  # drift
        motion.gaze_to(ctx, back - 3, 0.0, 0.0, from_dx=dx, from_dy=dy,
                       layer='gaze')
        _aim(ctx, back, 0.0, 0.0)
        for df, s in ((-2, 0.0), (10, 1.0), (back - cf - 6, 0.9),
                      (back - cf + 2, 0.0)):
            ctx.key_shape("Brow_Drop_L", cf + df, furrow * s, 'furrow')
            ctx.key_shape("Brow_Drop_R", cf + df + 1, furrow * 0.88 * s,
                          'furrow')
    _break(f0 + 60, f0 + 105, 0.28, 0.24, 0.20)        # 1.5s recall break
    _break(f0 + 180, f0 + 204, 0.20, 0.18, 0.14)       # 0.8s shorter break
    # lip press cycle f70-95 (chewing on the thought)
    for f, v in [(68, 0.0), (76, 0.18), (88, 0.15), (95, 0.0)]:
        ctx.key_shape("Mouth_Press_L", f0 + f, v, 'lips')
        ctx.key_shape("Mouth_Press_R", f0 + f + 1, v * 0.85, 'lips')
    ctx.key_shape("Mouth_Pucker_Up_L", f0 + 76, 0.10, 'lips')
    ctx.key_shape("Mouth_Pucker_Up_L", f0 + 68, 0.0, 'lips')
    ctx.key_shape("Mouth_Pucker_Up_L", f0 + 95, 0.0, 'lips')
    # slow deliberate 'I see' nod
    _nod(ctx, f0 + 200, 2.0, dur=20, wob=0.25)
    motion.add_blink(ctx, f0 + 30, amp=1.0, close=6, hold=2, open_=9,
                     r_offset=1, eye_down=0.06)                 # slow
    motion.add_blink(ctx, f0 + 122, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1)                                # masks return
    motion.add_blink(ctx, f0 + 205, amp=0.9, close=6, hold=2, open_=9,
                     r_offset=1, eye_down=0.06)                 # slow


# ---------------------------------------------------------------------------
@clip("listening_happy", "listening", 8.0, loop=True, framing='face',
      still_frame=0.45,
      description="soft-smile baseline 0.25 (asymmetric) held alive with "
      "+-0.05 waver, cheeks 0.2, lower-lid warmth 0.1. Warm nod cadence "
      "f50/f110/f165/f218 (faster than relaxed). Smile blooms to 0.4 at f110 "
      "(agreeing WITH pleasure) then relaxes. Brows soft. Seam-clean loop")
def listening_happy(ctx):
    f0, fe = ctx.frame_start, ctx.frame_end
    _drift(ctx, mag=0.6)
    _lid_tone(ctx, base_l=0.02, base_r=0.018)
    motion.head_micro_sway(ctx, amp_deg=0.4)
    # soft-smile baseline (asymmetric), held across the loop
    ctx.key_shape("Mouth_Smile_L", f0, 0.25, 'base')
    ctx.key_shape("Mouth_Smile_L", fe, 0.25, 'base')
    ctx.key_shape("Mouth_Smile_R", f0, 0.21, 'base')
    ctx.key_shape("Mouth_Smile_R", fe, 0.21, 'base')
    ctx.key_shape_lr("Cheek_Raise_{S}", f0, 0.20, 'base', r_offset=0,
                     r_scale=0.85)
    ctx.key_shape_lr("Cheek_Raise_{S}", fe, 0.20, 'base', r_offset=0,
                     r_scale=0.85)
    ctx.key_shape_lr("Eye_Squint_{S}", f0, 0.10, 'base', r_offset=0,
                     r_scale=0.85)
    ctx.key_shape_lr("Eye_Squint_{S}", fe, 0.10, 'base', r_offset=0,
                     r_scale=0.85)
    # smile bloom to 0.4 @f110 then relax (additive delta over the baseline)
    for f, v in [(96, 0.0), (110, 0.15), (128, 0.0)]:
        ctx.key_shape("Mouth_Smile_L", f0 + f, v, 'bloom')
        ctx.key_shape("Mouth_Smile_R", f0 + f + 1, v * 0.85, 'bloom')
        ctx.key_shape("Cheek_Raise_L", f0 + f, v * 0.6, 'bloom')
        ctx.key_shape("Cheek_Raise_R", f0 + f + 1, v * 0.5, 'bloom')
    # corner waver keeps the baseline smile alive (delta)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_L", f, v, 'waver'), amp=0.05, cycles=(2, 3), step=5)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Mouth_Smile_R", f, v, 'waver'), amp=0.04, cycles=(3, 4), step=5)
    # warm faster nod cadence, unequal
    _nod(ctx, f0 + 50, 1.8, dur=13)
    _nod(ctx, f0 + 110, 2.2, dur=15)
    _nod(ctx, f0 + 165, 1.5, dur=12)
    _nod(ctx, f0 + 218, 2.0, dur=14)
    motion.add_blink(ctx, f0 + 70, amp=1.0, close=3, hold=1, open_=6,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 175, amp=0.85, close=3, hold=1, open_=6,
                     r_offset=1)


# ---------------------------------------------------------------------------
@clip("listening_serious", "listening", 8.0, loop=True, framing='face',
      still_frame=0.4,
      description="Stillness IS the register: micro amplitude ~60% of "
      "neutral. Brows 0.2 down baseline, lips lightly pressed 0.1, NO smile. "
      "Two slow deliberate nods only (f90/f210, 2deg over 18f). Unbroken "
      "gaze; blink interval stretched to ~5s (runtime hint in meta). Jaw "
      "set, one micro clench f150. Seam-clean loop")
def listening_serious(ctx):
    f0, fe = ctx.frame_start, ctx.frame_end
    _drift(ctx, mag=0.35)                      # damped
    _lid_tone(ctx, base_l=0.03, base_r=0.028, scale=0.6)
    motion.head_micro_sway(ctx, amp_deg=0.24)  # 60% of neutral
    # furrow + light press baseline held; no smile
    ctx.key_shape("Brow_Drop_L", f0, 0.20, 'base')
    ctx.key_shape("Brow_Drop_L", fe, 0.20, 'base')
    ctx.key_shape("Brow_Drop_R", f0, 0.18, 'base')
    ctx.key_shape("Brow_Drop_R", fe, 0.18, 'base')
    ctx.key_shape("Mouth_Press_L", f0, 0.10, 'base')
    ctx.key_shape("Mouth_Press_L", fe, 0.10, 'base')
    ctx.key_shape("Mouth_Press_R", f0, 0.085, 'base')
    ctx.key_shape("Mouth_Press_R", fe, 0.085, 'base')
    # subtle furrow breathe so the brow is never a frozen pose (delta)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_L", f, v, 'furrbreathe'), amp=0.025, cycles=(2, 3), step=6)
    motion.loop_noise(ctx, lambda f, v: ctx.key_shape(
        "Brow_Drop_R", f, v, 'furrbreathe'), amp=0.02, cycles=(3, 4), step=6)
    # one micro jaw clench f150 (Mouth_Tighten pulse)
    for f, v in [(142, 0.0), (150, 0.12), (162, 0.0)]:
        ctx.key_shape("Mouth_Tighten_L", f0 + f, v, 'clench')
        ctx.key_shape("Mouth_Tighten_R", f0 + f + 1, v * 0.85, 'clench')
    # two slow deliberate nods only
    _nod(ctx, f0 + 90, 2.0, dur=18, wob=0.2)
    _nod(ctx, f0 + 210, 1.8, dur=18, wob=0.2)
    # stretched blink cadence (~5s apart)
    motion.add_blink(ctx, f0 + 70, amp=1.0, close=4, hold=1, open_=7,
                     r_offset=1)
    motion.add_blink(ctx, f0 + 215, amp=0.9, close=4, hold=1, open_=7,
                     r_offset=1)
