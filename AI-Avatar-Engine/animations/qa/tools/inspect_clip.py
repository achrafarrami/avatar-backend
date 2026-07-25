"""QA clip inspector — turns an animation preview folder into a reviewable evidence sheet.

Usage (run with the AI-Avatar-Engine python venv):
    AI-Avatar-Engine\\ai\\.venv\\Scripts\\python AI-Avatar-Engine\\animations\\qa\\tools\\inspect_clip.py \
        <preview_folder> [--frames 12] [--out <reports_dir>] [--dead-sec 0.75]

Given a clip preview folder (AI-Avatar-Engine/animations/previews/<clip_id>/ containing
<clip_id>.mp4 and optionally meta.json), this tool:
  a) extracts N evenly-spaced frames from the MP4, plus a loop-boundary strip
     (last 3 + first 3 frames side by side) for loop-pop detection;
  b) computes a motion-energy series (mean abs consecutive-frame diff), saves it as CSV,
     and flags dead zones (frozen stretches), metronomic repetition (autocorrelation
     peaks), and loop pop (wrap-around diff vs. typical inter-frame motion);
  c) assembles everything into qa/reports/<clip_id>_inspection.png (<=1600px wide),
     and writes qa/reports/<clip_id>_metrics.json with the raw numbers.

Exit code 0 = ran fine (flags are reported, not fatal); nonzero = could not inspect.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PIL import Image, ImageDraw, ImageFont

SHEET_W = 1600
MARGIN = 8
GRID_COLS = 6
BG = (24, 24, 28)
FG = (230, 230, 230)
ACCENT = (255, 120, 90)
OK = (120, 220, 140)


# ----------------------------------------------------------------------------- io

def find_mp4(folder: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            sys.exit(f"ERROR: --mp4 {p} not found")
        return p
    cand = folder / f"{folder.name}.mp4"
    if cand.exists():
        return cand
    mp4s = sorted(folder.glob("*.mp4"))
    if not mp4s:
        sys.exit(f"ERROR: no .mp4 found in {folder}")
    return mp4s[0]


def load_meta(folder: Path) -> dict:
    p = folder / "meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # malformed meta is a finding, not a crash
        return {"_meta_error": f"meta.json unreadable: {e}"}


def read_video(mp4: Path):
    """Return (frames_bgr_small_gray list for energy, keep_frames dict idx->bgr, fps, n, (w,h)).

    We read the stream once. Full-res BGR copies are kept only for the frames we
    will actually show (even samples + first/last 3); everything gets a small
    grayscale copy for the motion-energy series.
    """
    cap = cv2.VideoCapture(str(mp4))
    if not cap.isOpened():
        sys.exit(f"ERROR: cv2 cannot open {mp4}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_report = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    grays, frames = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (160, max(1, int(160 * g.shape[0] / g.shape[1]))))
        grays.append(g.astype(np.float32))
    cap.release()
    if len(frames) < 2:
        sys.exit(f"ERROR: {mp4} has {len(frames)} readable frame(s) — cannot inspect")
    h, w = frames[0].shape[:2]
    if n_report and abs(n_report - len(frames)) > 2:
        print(f"NOTE: container reports {n_report} frames, decoded {len(frames)}")
    return grays, frames, float(fps), len(frames), (w, h)


# ------------------------------------------------------------------- measurements

def motion_energy(grays: list[np.ndarray]) -> np.ndarray:
    return np.array([float(np.mean(np.abs(grays[i + 1] - grays[i])))
                     for i in range(len(grays) - 1)], dtype=np.float64)


def encoder_signature(energy: np.ndarray, fps: float):
    """Detect GOP-quantized previews: mostly exactly-zero diffs refreshed at a
    regular period. Sub-pixel motion below the encoder's quantization emits 0.0
    for every non-keyframe — a fake dead zone + fake metronome at the GOP period."""
    zero_ratio = float(np.mean(energy < 1e-9))
    if zero_ratio < 0.4 or float(energy.max()) <= 0:
        return None
    # significant refresh spikes (codec ringing can smear a refresh over 2-3
    # frames, so cluster adjacent spikes and measure burst-start spacing)
    idx = np.flatnonzero(energy > 0.2 * energy.max())
    if len(idx) < 3:
        return None
    starts = idx[np.concatenate(([True], np.diff(idx) > 2))]
    if len(starts) < 3:
        return None
    gaps = np.diff(starts)
    period = int(np.median(gaps))
    regular = float(np.mean(np.abs(gaps - period) <= 1))
    if period >= 2 and regular > 0.7:
        return {"zero_ratio": round(zero_ratio, 3), "period_frames": period,
                "period_s": round(period / fps, 3), "gap_regularity": round(regular, 3)}
    return None


def grid_comb(energy: np.ndarray, period_f: float):
    """Second encoder discriminator: fraction of significant energy local maxima
    sitting within +-1 frame of a rigid grid of spacing period_f (best phase).
    I-frame refresh pulses comb the trace machine-exactly at the GOP grid on
    near-static clips; authored repeats carry organic timing jitter.
    Period-agnostic: caller passes the detected autocorrelation period.
    Returns (hit_fraction, n_maxima, best_phase) or None."""
    if period_f < 2 or len(energy) < 3 * period_f:
        return None
    # Isolate DOMINANT maxima (I-frame refresh pulses are large outliers ~10x
    # median). A plain > median threshold drowns them in sub-pixel jitter bumps;
    # the comb signal lives in the tall spikes, so gate on prominence.
    med = float(np.median(energy))
    emax = float(energy.max())
    sig = max(3.0 * med, 0.2 * emax)
    maxima = [i for i in range(1, len(energy) - 1)
              if energy[i] >= energy[i - 1] and energy[i] >= energy[i + 1]
              and energy[i] >= sig]
    if len(maxima) < 5:
        return None
    # Spikiness guard: an I-frame comb is sharp pulses against a near-static
    # background (motion sits below encoder quantization BETWEEN refreshes).
    # Authored cyclic motion (a real metronome defect) sustains energy between
    # peaks. Only treat as encoder if the background is a tiny fraction of peaks.
    peak_level = float(np.median([energy[i] for i in maxima]))
    near = np.zeros(len(energy), dtype=bool)
    for m in maxima:
        near[max(0, m - 1):m + 2] = True
    bg = energy[~near]
    background = float(np.median(bg)) if bg.size else 0.0
    if peak_level <= 1e-9 or background >= 0.15 * peak_level:
        return None  # sustained inter-peak motion -> not an encoder comb
    best_hits, best_phase = 0, 0
    for phase_i in range(int(round(period_f))):
        hits = 0
        for m in maxima:
            r = (m - phase_i) % period_f
            if r <= 1.0 or (period_f - r) <= 1.0:
                hits += 1
        if hits > best_hits:
            best_hits, best_phase = hits, phase_i
    return best_hits / len(maxima), len(maxima), best_phase


def find_dead_zones(energy: np.ndarray, fps: float, dead_sec: float):
    """Runs of near-zero motion lasting >= dead_sec. Threshold adapts to the
    clip's own motion scale (framing-aware): head-cam clips get the 0.25 codec
    noise floor; body-framed subtle clips get 5% of their median activity."""
    nz = energy[energy > 1e-9]
    median_active = float(np.median(nz)) if nz.size else 0.0
    thresh = max(0.02, 0.05 * median_active)
    if median_active > 1.0:  # head-cam motion scale: codec noise band applies
        thresh = max(thresh, 0.25)
    min_len = max(2, int(round(dead_sec * fps)))
    zones, start = [], None
    for i, e in enumerate(energy):
        if e < thresh:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_len:
                zones.append((start, i))
            start = None
    if start is not None and len(energy) - start >= min_len:
        zones.append((start, len(energy)))
    return zones, thresh


def autocorr_peak(energy: np.ndarray, fps: float):
    """Strongest autocorrelation peak at lag > 0.25s. Returns (lag_s, r) or None."""
    e = energy - energy.mean()
    denom = float(np.dot(e, e))
    if denom < 1e-9 or len(e) < int(fps):
        return None
    max_lag = len(e) // 2
    min_lag = max(2, int(0.25 * fps))
    if min_lag >= max_lag:
        return None
    r = np.array([float(np.dot(e[:-lag], e[lag:])) / denom
                  for lag in range(min_lag, max_lag)])
    best = None
    for i in range(1, len(r) - 1):  # local maxima only
        if r[i] >= r[i - 1] and r[i] >= r[i + 1]:
            if best is None or r[i] > r[best]:
                best = i
    if best is None:
        return None
    return ((min_lag + best) / fps, float(r[best]))


def loop_pop(grays: list[np.ndarray], energy: np.ndarray):
    wrap = float(np.mean(np.abs(grays[0] - grays[-1])))
    med = float(np.median(energy)) if energy.size else 0.0
    ratio = wrap / med if med > 1e-6 else float("inf") if wrap > 0.5 else 0.0
    return wrap, med, ratio


def build_flags(energy, fps, zones, thresh, ac, wrap, med, ratio, n, meta, enc):
    """Returns (flags, notes). Flags = defects. Notes = informational context
    (one-shot end-hold wrap metrics, encoder-signature downgrades)."""
    flags, notes = [], []
    is_loop = bool(meta.get("loop", True))  # missing meta -> assume loop (strictest)
    dur = n / fps
    if dur < 0.5:
        flags.append(f"SHORT: clip is only {dur:.2f}s")

    if enc:
        notes.append(
            f"ENCODER SIGNATURE: {enc['zero_ratio'] * 100:.0f}% of frame diffs are "
            f"exactly zero, refreshed every ~{enc['period_frames']}f "
            f"({enc['period_s']:.2f}s = GOP) — motion sits below encoder quantization "
            f"at this framing/quality. Dead-zone & metronome checks unreliable; "
            f"verify aliveness from curves/strips, or request a higher-quality render.")
        if zones:
            notes.append(f"dead-zone check suppressed ({len(zones)} zone(s) matched "
                         f"the zero-diff GOP pattern, not authored freezes)")
        zones = []

    for a, b in zones:
        flags.append(f"DEAD ZONE: frozen {a / fps:.2f}s-{b / fps:.2f}s "
                     f"({(b - a) / fps:.2f}s below energy {thresh:.2f})")

    if ac is not None and ac[1] > 0.55:
        period_f = ac[0] * fps
        comb = grid_comb(energy, period_f)
        if enc and abs(period_f - enc["period_frames"]) <= 1.5:
            notes.append(f"autocorrelation peak r={ac[1]:.2f} at {ac[0]:.2f}s matches "
                         f"the encoder GOP period — encoder signature, not motion")
        elif comb is not None and comb[0] >= 0.85:
            # I-frame refresh pulses land machine-exactly on a rigid grid; authored
            # repeats jitter. >=85% of energy maxima on the grid = encoder comb.
            notes.append(f"I-FRAME GRID COMB: {round(comb[0] * comb[1])}/{comb[1]} energy "
                         f"maxima fall within +-1f of a rigid {period_f:.0f}-frame grid "
                         f"(phase {comb[2]}) — encoder I-frame refresh pulses at "
                         f"r={ac[1]:.2f}, not authored cyclic motion. Verify aliveness "
                         f"from strips/curves.")
        else:
            sev = "STRONG" if ac[1] > 0.75 else "moderate"
            grid_txt = (f" (grid-comb {comb[0] * 100:.0f}% of {comb[1]} maxima — "
                        f"below encoder threshold, reads as authored)" if comb else "")
            flags.append(f"METRONOME ({sev}): motion-energy autocorrelation r={ac[1]:.2f} "
                         f"at period {ac[0]:.2f}s — check for mechanical repetition{grid_txt}")

    if enc:  # GOP zeros crush the full-series median; compare against real steps
        nz = energy[energy > 1e-9]
        med = float(np.median(nz)) if nz.size else med
        ratio = wrap / med if med > 1e-6 else (float("inf") if wrap > 0.5 else 0.0)

    if ratio > 3.0 and wrap > 1.0:
        msg = (f"last->first frame diff {wrap:.2f} is {ratio:.1f}x the "
               f"median inter-frame motion ({med:.2f})")
        if is_loop:
            flags.append(f"LOOP POP: {msg} — visible jump at loop point")
        else:
            notes.append(f"one-shot clip (meta loop=false): end pose differs from start "
                         f"({msg}) — expected for end-hold clips, informational only")

    if float(np.max(energy)) < 0.5 and not enc:
        flags.append("NEARLY STATIC: peak motion energy < 0.5 — clip may be frozen throughout")
    if meta.get("_meta_error"):
        flags.append(meta["_meta_error"])
    if not meta:
        flags.append("NO META: meta.json missing from preview folder")
    return flags, notes


# ------------------------------------------------------------------------ drawing

def _font(size):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


def thumb(frame_bgr, width, label):
    h, w = frame_bgr.shape[:2]
    th = int(round(width * h / w))
    img = cv2.resize(frame_bgr, (width, th))
    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)
    f = _font(14)
    d.text((5, 3), label, font=f, fill=(255, 255, 80),
           stroke_width=2, stroke_fill=(0, 0, 0))
    return img


def row_of(images, gap=MARGIN, divider_after=None):
    h = max(im.height for im in images)
    w = sum(im.width for im in images) + gap * (len(images) - 1)
    row = Image.new("RGB", (w, h), BG)
    x = 0
    for i, im in enumerate(images):
        row.paste(im, (x, 0))
        x += im.width + gap
        if divider_after is not None and i == divider_after:
            d = ImageDraw.Draw(row)
            d.rectangle([x - gap + 1, 0, x - 3, h], fill=(220, 60, 60))
    return row


def energy_plot_img(energy, fps, zones, thresh, width):
    t = np.arange(len(energy)) / fps
    fig, ax = plt.subplots(figsize=(width / 100, 3.0), dpi=100)
    fig.patch.set_facecolor("#18181c")
    ax.set_facecolor("#202026")
    ax.plot(t, energy, color="#7ad2ff", lw=1.2)
    ax.axhline(thresh, color="#ff7860", ls="--", lw=0.8, label=f"dead thresh {thresh:.2f}")
    for a, b in zones:
        ax.axvspan(a / fps, b / fps, color="#ff7860", alpha=0.25)
    ax.set_xlabel("time (s)", color="#ddd")
    ax.set_ylabel("motion energy", color="#ddd")
    ax.tick_params(colors="#aaa")
    for s in ax.spines.values():
        s.set_color("#555")
    ax.legend(loc="upper right", fontsize=8, facecolor="#202026",
              labelcolor="#ddd", edgecolor="#555")
    fig.tight_layout()
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    plt.close(fig)
    return Image.fromarray(buf.copy())


def text_block(lines, width, size=15, color=FG, pad=6, line_gap=5):
    f = _font(size)
    h = pad * 2 + len(lines) * (size + line_gap)
    img = Image.new("RGB", (width, h), BG)
    d = ImageDraw.Draw(img)
    y = pad
    for line, c in lines:
        d.text((pad, y), line, font=f, fill=c or color)
        y += size + line_gap
    return img


def meta_summary(meta, mp4, fps, n, size_wh):
    dur = n / fps
    lines = [(f"file: {mp4.name}   {size_wh[0]}x{size_wh[1]}  {fps:.2f} fps  "
              f"{n} frames  {dur:.2f}s", FG)]
    keys = ("duration", "duration_s", "fps", "frame_count", "keyframe_counts",
            "keyframes", "bones_used", "bones", "keys_used", "shape_keys", "clip_id")
    for k in keys:
        if k in meta:
            v = meta[k]
            s = json.dumps(v) if not isinstance(v, str) else v
            if len(s) > 150:
                s = s[:147] + "..."
            lines.append((f"meta.{k}: {s}", (170, 190, 220)))
    return lines


def assemble_sheet(clip_id, header_lines, flag_lines, note_lines, even_rows,
                   loop_row, plot_img, out_png, is_loop=True):
    sections = []
    title = text_block([(f"QA INSPECTION — {clip_id}", (255, 255, 255))], SHEET_W, size=22)
    sections.append(title)
    sections.append(text_block(header_lines, SHEET_W, size=14))
    fl = [("FLAGS:", ACCENT)] + [(f"  ! {f}", ACCENT) for f in flag_lines] \
        if flag_lines else [("FLAGS: none — automated checks clean", OK)]
    sections.append(text_block(fl, SHEET_W, size=15))
    if note_lines:
        sections.append(text_block(
            [("NOTES (informational):", (140, 170, 220))] +
            [(f"  - {t}", (140, 170, 220)) for t in note_lines], SHEET_W, size=14))
    sections.append(text_block([("EVENLY-SPACED FRAMES", (160, 160, 170))], SHEET_W, size=13))
    sections.extend(even_rows)
    loop_label = ("LOOP BOUNDARY — last 3 | first 3 (red bar = loop point)" if is_loop
                  else "END vs START — last 3 | first 3 (one-shot clip: mismatch expected)")
    sections.append(text_block([(loop_label, (160, 160, 170))], SHEET_W, size=13))
    sections.append(loop_row)
    sections.append(text_block([("MOTION ENERGY", (160, 160, 170))], SHEET_W, size=13))
    sections.append(plot_img)
    total_h = sum(s.height for s in sections) + MARGIN * (len(sections) + 1)
    sheet = Image.new("RGB", (SHEET_W, total_h), BG)
    y = MARGIN
    for s in sections:
        sheet.paste(s, (MARGIN if s.width < SHEET_W else 0, y))
        y += s.height + MARGIN
    sheet.save(out_png)


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="clip preview folder (previews/<clip_id>/)")
    ap.add_argument("--frames", type=int, default=12, help="evenly-spaced frames to show")
    ap.add_argument("--out", default=None, help="reports dir (default: qa/reports)")
    ap.add_argument("--mp4", default=None, help="explicit mp4 path override")
    ap.add_argument("--dead-sec", type=float, default=0.75,
                    help="min frozen duration to flag as dead zone")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"ERROR: {folder} is not a directory")
    clip_id = folder.name
    out_dir = Path(args.out) if args.out else Path(__file__).resolve().parents[1] / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    mp4 = find_mp4(folder, args.mp4)
    meta = load_meta(folder)
    grays, frames, fps, n, size_wh = read_video(mp4)

    energy = motion_energy(grays)
    enc = encoder_signature(energy, fps)
    zones, thresh = find_dead_zones(energy, fps, args.dead_sec)
    ac = autocorr_peak(energy, fps)
    wrap, med, ratio = loop_pop(grays, energy)
    flags, notes = build_flags(energy, fps, zones, thresh, ac, wrap, med, ratio,
                               n, meta, enc)
    is_loop = bool(meta.get("loop", True))

    # CSV
    csv_path = out_dir / f"{clip_id}_motion.csv"
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("frame,time_s,energy\n")
        for i, e in enumerate(energy):
            fh.write(f"{i},{i / fps:.4f},{e:.4f}\n")

    # metrics json (for scorecard cross-reference)
    metrics = {
        "clip_id": clip_id, "mp4": str(mp4), "fps": fps, "frames": n,
        "duration_s": round(n / fps, 3), "resolution": list(size_wh),
        "energy": {"mean": round(float(energy.mean()), 3),
                   "median": round(med, 3),
                   "max": round(float(energy.max()), 3),
                   "dead_threshold": round(thresh, 3)},
        "dead_zones_s": [[round(a / fps, 3), round(b / fps, 3)] for a, b in zones],
        "autocorr_peak": {"period_s": round(ac[0], 3), "r": round(ac[1], 3)} if ac else None,
        "loop": {"wrap_diff": round(wrap, 3), "median_diff": round(med, 3),
                 "ratio": round(ratio, 2) if ratio != float("inf") else None},
        "loop_clip": is_loop,
        "encoder_signature": enc,
        "flags": flags,
        "notes": notes,
    }
    metrics_path = out_dir / f"{clip_id}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # visuals
    tw = (SHEET_W - MARGIN * (GRID_COLS + 1)) // GRID_COLS
    idxs = np.linspace(0, n - 1, num=min(args.frames, n), dtype=int)
    thumbs = [thumb(frames[i], tw, f"f{i}  t={i / fps:.2f}s") for i in idxs]
    even_rows = [row_of(thumbs[r:r + GRID_COLS]) for r in range(0, len(thumbs), GRID_COLS)]

    last3 = list(range(max(0, n - 3), n))
    first3 = list(range(0, min(3, n)))
    loop_imgs = [thumb(frames[i], tw, f"f{i} (end)") for i in last3] + \
                [thumb(frames[i], tw, f"f{i} (start)") for i in first3]
    loop_row = row_of(loop_imgs, divider_after=len(last3) - 1)

    plot_img = energy_plot_img(energy, fps, zones, thresh, SHEET_W)
    header = meta_summary(meta, mp4, fps, n, size_wh)

    sheet_path = out_dir / f"{clip_id}_inspection.png"
    assemble_sheet(clip_id, header, flags, notes, even_rows, loop_row, plot_img,
                   sheet_path, is_loop=is_loop)

    print(f"sheet:   {sheet_path}")
    print(f"csv:     {csv_path}")
    print(f"metrics: {metrics_path}")
    print(f"flags:   {len(flags)}")
    for f in flags:
        print(f"  ! {f}")
    for t in notes:
        print(f"  - note: {t}")


if __name__ == "__main__":
    main()
