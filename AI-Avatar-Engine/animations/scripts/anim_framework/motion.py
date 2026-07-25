"""Naturalness toolkit — procedural generators layered onto a ClipContext.

Every generator produces asymmetric L/R output by default (1–3 frame
offsets, 5–15 % amplitude variation) and is deterministic per clip
(ctx.rng is seeded from the clip id). Loop-safe: periodic generators use
integer cycle counts over the clip length; transient generators keep a
rest margin at the loop boundaries.
"""
import math

TWO_PI = math.tau


# ---------------------------------------------------------------------------
# ease profiles
# ---------------------------------------------------------------------------
def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def ease_in(t, power=2.0):
    return min(1.0, max(0.0, t)) ** power


def ease_out(t, power=2.0):
    return 1.0 - (1.0 - min(1.0, max(0.0, t))) ** power


def ease_out_back(t, k=1.7):
    """Overshooting ease-out (settles from beyond the target)."""
    t = min(1.0, max(0.0, t)) - 1.0
    return 1.0 + t * t * ((k + 1.0) * t + k)


def breath_wave(p, inhale_frac=0.42):
    """Asymmetric breath cycle, 0 at p=0/1, 1 at end of inhale.
    Inhale is faster than exhale; flat spots at the turnarounds."""
    p %= 1.0
    if p < inhale_frac:
        return smoothstep(p / inhale_frac)
    return 1.0 - smoothstep((p - inhale_frac) / (1.0 - inhale_frac))


# ---------------------------------------------------------------------------
# anticipation / overshoot / settle
# ---------------------------------------------------------------------------
def aos_keys(f0, f1, v1, v0=0.0, anticipation=0.15, overshoot=0.12,
             settle=0.3):
    """[(frame, value)] moving v0 -> v1 with counter-motion before, an
    overshoot past the target and a settle back. Fractions are of |v1-v0|."""
    d = v1 - v0
    T = f1 - f0
    keys = [(f0, v0)]
    if anticipation > 1e-4 and T >= 8:
        keys.append((f0 + max(2, round(0.20 * T)), v0 - anticipation * d))
    keys.append((f0 + round(0.62 * T), v1 + overshoot * d))
    if settle > 1e-4 and T >= 6:
        keys.append((f0 + round(0.84 * T), v1 - settle * overshoot * d))
    keys.append((f1, v1))
    out, seen = [], set()
    for f, v in keys:
        f = int(round(f))
        if f not in seen:
            seen.add(f)
            out.append((f, v))
    return out


def swing_aos(ctx, bone, axis, f0, f1, deg, deg0=0.0, layer='gesture', **kw):
    """Key an axis rotation with anticipation/overshoot/settle."""
    for f, v in aos_keys(f0, f1, deg, deg0, **kw):
        ctx.key_bone_axis(bone, f, axis, v, layer=layer)


# ---------------------------------------------------------------------------
# layered breathing
# ---------------------------------------------------------------------------
def breathing(ctx, start=None, end=None, period=4.0, amp=1.0, phase=0.0,
              chest=1.0, shoulders=1.0, head=1.0, layer='breath',
              keys_per_cycle=8):
    """Chest/spine/clavicle/head breathing cycle. Loop-safe: an integer
    number of cycles is fitted into [start, end]. `phase` (0..1) offsets
    the whole cycle so different clips don't breathe in unison.
    Signs: inhale = spine extension (-x) + clavicle raise; the head
    counter-pitches so the face stays level."""
    start = ctx.frame_start if start is None else start
    end = ctx.frame_end if end is None else end
    dur_s = (end - start) / ctx.fps
    n_cycles = max(1, round(dur_s / period))
    period_f = (end - start) / n_cycles

    # per-cycle peak variation (periodic across the loop => seamless)
    cycle_gain = [1.0 + ctx.rng.uniform(-0.07, 0.07) for _ in range(n_cycles)]

    # (bone, axis, peak_deg, extra_phase)
    channels = [
        ("CC_Base_Spine02",     'x', -0.85 * chest, 0.00),
        ("CC_Base_Spine01",     'x', -0.42 * chest, 0.03),
        ("CC_Base_Waist",       'x', -0.18 * chest, 0.05),
        ("CC_Base_NeckTwist01", 'x', +0.22 * head,  0.06),
        ("CC_Base_Head",        'x', +0.30 * head,  0.08),
    ]
    # asymmetric shoulders: R lags ~2 frames and is slightly weaker
    lag_r = 2.0 / period_f
    channels += [
        ("CC_Base_L_Clavicle", 'z', +1.05 * shoulders, -0.02),
        ("CC_Base_R_Clavicle", 'z', -0.95 * shoulders, -0.02 + lag_r),
    ]

    n_keys = n_cycles * keys_per_cycle
    for bone, axis, peak, extra in channels:
        for i in range(n_keys + 1):
            f = start + (end - start) * i / n_keys
            p = (i / keys_per_cycle + phase + extra) % n_cycles
            gain = cycle_gain[int(p) % n_cycles]
            v = amp * peak * gain * breath_wave(p % 1.0)
            ctx.key_bone_axis(bone, f, axis, v, layer=layer)


# ---------------------------------------------------------------------------
# blinks
# ---------------------------------------------------------------------------
def add_blink(ctx, frame, amp=1.0, close=None, hold=1, open_=None,
              eye_down=0.10, double=False, r_offset=None, layer='blink'):
    """One natural blink starting at `frame`. Close 3–4 f, open 5–7 f,
    slight conjugate eye-down at the closed peak, right eye lags 1–2 f.
    The Eye_Blink_* keys carry the lashes on this rig (calibrated) —
    no Eyelash_* keys are added. Returns the frame the blink ends."""
    close = close if close is not None else ctx.rng.randint(3, 4)
    open_ = open_ if open_ is not None else ctx.rng.randint(5, 7)
    # 1 frame max: a 2-frame inter-eye lag freeze-frames as a WINK (QA batch-1
    # reject class). Asymmetry comes from the amplitude scale below instead.
    r_offset = r_offset if r_offset is not None else 1

    def lid(side, off, scale):
        k = f"Eye_Blink_{side}"
        f0 = frame + off
        ctx.key_shape(k, f0, 0.0, layer)
        ctx.key_shape(k, f0 + close, amp * scale, layer, handle='VECTOR')
        if double:
            ctx.key_shape(k, f0 + close + hold + 3, 0.35 * amp * scale, layer)
            ctx.key_shape(k, f0 + close + hold + 6, 0.9 * amp * scale, layer)
            ctx.key_shape(k, f0 + close + hold + 6 + open_, 0.0, layer)
        else:
            ctx.key_shape(k, f0 + close + hold, amp * scale, layer)
            ctx.key_shape(k, f0 + close + hold + open_, 0.0, layer)

    lid('L', 0, 1.0)
    lid('R', r_offset, ctx.rng.uniform(0.97, 1.0))

    if eye_down > 1e-4:  # eyes dip slightly while the lids are closed
        for s in 'LR':
            k = f"Eye_{s}_Look_Down"
            ctx.key_shape(k, frame, 0.0, layer)
            ctx.key_shape(k, frame + close + hold, eye_down, layer)
            ctx.key_shape(k, frame + close + hold + open_ + 1, 0.0, layer)
    end = frame + r_offset + close + hold + open_
    return end + (9 if double else 0)


def blink_schedule(ctx, start=None, end=None, gap=(2.0, 6.0),
                   double_prob=0.12, margin=18, layer='blink', **blink_kw):
    """Randomized blink schedule over [start, end]. Keeps `margin` frames
    of rest at both ends so looping clips stay seamless."""
    start = ctx.frame_start if start is None else start
    end = ctx.frame_end if end is None else end
    f = start + margin + ctx.sec(ctx.rng.uniform(0.2, 1.2))
    blinks = []
    while f < end - margin - 20:
        dbl = ctx.rng.random() < double_prob
        add_blink(ctx, f, double=dbl, layer=layer, **blink_kw)
        blinks.append(f)
        f += ctx.sec(ctx.rng.uniform(*gap))
    return blinks


# ---------------------------------------------------------------------------
# gaze: saccades + fixation drift, eyes lead the head
# ---------------------------------------------------------------------------
def _set_gaze(ctx, frame, dx, dy, layer, r_scale=1.0):
    """Conjugate gaze via the Look shape keys. dx + = character's left,
    dy + = up. Values 0..1 per direction key."""
    for side, scale in (('L', 1.0), ('R', r_scale)):
        ctx.key_shape(f"Eye_{side}_Look_L", frame, max(0.0, dx) * scale, layer)
        ctx.key_shape(f"Eye_{side}_Look_R", frame, max(0.0, -dx) * scale, layer)
        ctx.key_shape(f"Eye_{side}_Look_Up", frame, max(0.0, dy) * scale, layer)
        ctx.key_shape(f"Eye_{side}_Look_Down", frame, max(0.0, -dy) * scale, layer)


def gaze_to(ctx, frame, dx, dy, from_dx=0.0, from_dy=0.0, dart=None,
            layer='gaze'):
    """One saccade: eyes dart to (dx, dy) in 1–4 frames (bigger = slower).
    Returns the arrival frame."""
    dist = math.hypot(dx - from_dx, dy - from_dy)
    if dart is None:
        dart = max(1, min(4, round(1 + dist * 5)))
    _set_gaze(ctx, frame, from_dx, from_dy, layer)
    r_scale = ctx.rng.uniform(0.93, 1.0)
    _set_gaze(ctx, frame + dart, dx, dy, layer, r_scale=r_scale)
    return frame + dart


def gaze_wander(ctx, start=None, end=None, magnitude=0.22,
                fix_time=(0.8, 2.4), drift=0.03, head_follow=0.0,
                margin=15, layer='gaze'):
    """Idle gaze: random fixations with micro-drift, saccade transitions.
    With head_follow > 0 the head trails the eyes by 2–5 frames at that
    fraction of the gaze deflection. Starts and ends at center (loop-safe)."""
    start = ctx.frame_start if start is None else start
    end = ctx.frame_end if end is None else end
    f = start + margin
    cur = (0.0, 0.0)
    _set_gaze(ctx, start, 0.0, 0.0, layer)
    while f < end - margin - ctx.sec(fix_time[0]):
        remaining = (end - margin) - f - ctx.sec(fix_time[0])
        if remaining < ctx.sec(1.0):
            tgt = (0.0, 0.0)  # return to center for the loop
        else:
            tgt = (ctx.rng.uniform(-magnitude, magnitude),
                   ctx.rng.uniform(-magnitude * 0.6, magnitude * 0.5))
        arrive = gaze_to(ctx, f, tgt[0], tgt[1], cur[0], cur[1], layer=layer)
        if head_follow > 1e-4:
            lag = ctx.rng.randint(2, 5)
            ease = ctx.rng.randint(10, 16)
            ctx.yaw("CC_Base_Head", f + lag, cur[0] * 12.0 * head_follow,
                    layer=layer + "_head")
            ctx.yaw("CC_Base_Head", arrive + lag + ease,
                    tgt[0] * 12.0 * head_follow, layer=layer + "_head")
            ctx.pitch("CC_Base_Head", f + lag, -cur[1] * 8.0 * head_follow,
                      layer=layer + "_head")
            ctx.pitch("CC_Base_Head", arrive + lag + ease,
                      -tgt[1] * 8.0 * head_follow, layer=layer + "_head")
        # fixation with micro-drift
        fix = ctx.sec(ctx.rng.uniform(*fix_time))
        n_drift = max(1, fix // ctx.sec(0.5))
        dxy = tgt
        for i in range(int(n_drift)):
            fd = arrive + int((i + 1) * fix / n_drift)
            if fd >= end - margin:
                break
            dxy = (tgt[0] + ctx.rng.uniform(-drift, drift),
                   tgt[1] + ctx.rng.uniform(-drift, drift))
            _set_gaze(ctx, fd, dxy[0], dxy[1], layer)
        cur = dxy
        f = arrive + fix
    # settle to center at the end
    gaze_to(ctx, min(f, end - margin), 0.0, 0.0, cur[0], cur[1], layer=layer)
    if head_follow > 1e-4:
        ctx.yaw("CC_Base_Head", end - margin + 5, 0.0, layer=layer + "_head")
        ctx.pitch("CC_Base_Head", end - margin + 5, 0.0, layer=layer + "_head")


# ---------------------------------------------------------------------------
# weight shift
# ---------------------------------------------------------------------------
def weight_shift(ctx, f0, f1, side='L', lateral_cm=1.5, layer='weight',
                 anticipation=0.06, overshoot=0.10):
    """Shift the hips over the supporting foot with a spine counter-lean so
    the head stays over the support polygon. side 'L' = hips move to the
    character's left. Key f0 -> f1 transition; call again to shift back."""
    s = 1.0 if side == 'L' else -1.0
    for f, v in aos_keys(f0, f1, s * lateral_cm,
                         anticipation=anticipation, overshoot=overshoot):
        ctx.key_bone_loc_world("CC_Base_Hip", f, (v, 0.0, -abs(v) * 0.12),
                               layer=layer)
    # counter-lean: tilt spine back toward center, head re-levels
    for bone, deg in (("CC_Base_Spine01", -2.0), ("CC_Base_Spine02", -1.1),
                      ("CC_Base_NeckTwist01", +0.6), ("CC_Base_Head", +1.2)):
        for f, v in aos_keys(f0 + 2, f1 + 2, s * deg,
                             anticipation=0.0, overshoot=overshoot * 0.7):
            ctx.roll(bone, f, v, layer=layer)
    # trailing shoulder drops a touch
    drop_side = 'R' if side == 'L' else 'L'
    for f, v in aos_keys(f0 + 3, f1 + 3, -0.8, anticipation=0.0,
                         overshoot=0.0):
        ctx.clavicle_raise(drop_side, f, v, layer=layer)


# ---------------------------------------------------------------------------
# finger micro-relaxation
# ---------------------------------------------------------------------------
FINGER_AMP = {"Index": 0.6, "Mid": 0.8, "Ring": 1.0, "Pinky": 1.15}


def finger_relax(ctx, start=None, end=None, amp_deg=1.8, period=8.0,
                 layer='fingers', keys_per_cycle=6):
    """Slow curl/relax ripple across the fingers of both hands. Always a
    positive extra curl (fingers never hyper-extend past rest). Loop-safe."""
    start = ctx.frame_start if start is None else start
    end = ctx.frame_end if end is None else end
    dur_s = (end - start) / ctx.fps
    n_cycles = max(1, round(dur_s / period))
    n_keys = int(n_cycles * keys_per_cycle)
    hand_phase = {'L': ctx.rng.random(), 'R': ctx.rng.random()}
    for side in 'LR':
        for fi, (finger, f_amp) in enumerate(FINGER_AMP.items()):
            ph = hand_phase[side] + fi * 0.12
            amp = amp_deg * f_amp * ctx.rng.uniform(0.85, 1.15)
            for joint, j_amp in ((1, 1.0), (2, 0.8), (3, 0.6)):
                bone = f"CC_Base_{side}_{finger}{joint}"
                for i in range(n_keys + 1):
                    f = start + (end - start) * i / n_keys
                    p = (i / keys_per_cycle + ph) % 1.0
                    v = amp * j_amp * (0.5 - 0.5 * math.cos(TWO_PI * p))
                    ctx.key_bone_axis(bone, f, 'x', v, layer=layer)
        # thumb: half amplitude, joints 2-3 only
        ph = hand_phase[side] + 0.3
        for joint in (2, 3):
            bone = f"CC_Base_{side}_Thumb{joint}"
            for i in range(n_keys + 1):
                f = start + (end - start) * i / n_keys
                p = (i / keys_per_cycle + ph) % 1.0
                v = amp_deg * 0.4 * (0.5 - 0.5 * math.cos(TWO_PI * p))
                ctx.key_bone_axis(bone, f, 'x', v, layer=layer)


# ---------------------------------------------------------------------------
# seamless-loop noise
# ---------------------------------------------------------------------------
def loop_noise(ctx, apply, start=None, end=None, amp=1.0, cycles=(2, 3, 5),
               step=3, fade=None):
    """Bake band-limited noise into keyframes via `apply(frame, value)`.
    Uses integer cycle counts over [start, end] with random phases, so the
    signal is EXACTLY periodic (loop closure by construction). For
    one-shots pass fade=0.12 to blend to zero at both boundaries."""
    start = ctx.frame_start if start is None else start
    end = ctx.frame_end if end is None else end
    span = end - start
    comps = [(c, ctx.rng.uniform(0.0, 1.0), 1.0 / (i + 1))
             for i, c in enumerate(cycles)]
    wsum = sum(w for _, _, w in comps)
    f = start
    while f <= end:
        u = (f - start) / span
        v = sum(w * math.sin(TWO_PI * (c * u + ph))
                for c, ph, w in comps) / wsum
        if fade:
            edge = min(u, 1.0 - u)
            v *= smoothstep(edge / fade)
        apply(f, amp * v)
        f += step
    if (f - step) < end:
        apply(end, apply_end_value(comps, wsum, amp, fade))


def apply_end_value(comps, wsum, amp, fade):
    v = sum(w * math.sin(TWO_PI * ph) for _, ph, w in comps) / wsum
    return 0.0 if fade else amp * v


def head_micro_sway(ctx, start=None, end=None, amp_deg=0.7, layer='sway',
                    step=4):
    """Tiny never-still head motion (yaw/pitch/roll noise, decorrelated)."""
    for axis, scale in (('y', 1.0), ('x', 0.6), ('z', 0.45)):
        loop_noise(
            ctx,
            lambda f, v, a=axis: ctx.key_bone_axis(
                "CC_Base_Head", f, a, v, layer=layer),
            start, end, amp=amp_deg * scale,
            cycles=(2, 3, 5) if axis == 'y' else (3, 4, 7),
            step=step, fade=None if ctx.loop else 0.12)
