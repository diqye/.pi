#!/usr/bin/env python3
"""Measure sound, earshot 7-launch-film spectral/stereo profile, onset transcript, circular-shift sync coincidence,
and 5-lane visual sound sheet, ported from legible-film.

  python listen.py measure AUDIO_OR_VIDEO [--json report.json]
  python listen.py transcript AUDIO_OR_VIDEO [--json transcript.json]
  python listen.py sheet AUDIO_OR_VIDEO --out sheet.png [--cues cues.json]
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
RATE = 48000

# 10th to 90th percentiles from earshot's launch profile (Leon Lin, MIT)
PROFILE = {
    "integrated_lufs": [-19.32, -9.16],
    "true_peak_dbtp": [-0.26, 1.52],
    "lra_lu": [2.66, 9.08],
    "side_to_mid_db": [-11.8, -5.78],
    "correlation": [0.58, 0.864],
    "sub": [-12.36, -4.58],
    "low": [-5.92, -2.34],
    "lowmid": [-16.38, -3.2],
    "mid": [-15.92, -10.68],
    "presence": [-30.24, -13.52],
    "air": [-31.86, -14.74],
}
BANDS = {
    "sub": (20, 60),
    "low": (60, 250),
    "lowmid": (250, 1000),
    "mid": (1000, 4000),
    "presence": (4000, 8000),
    "air": (8000, 16000),
    "top": (16000, 24000),
}


def decode_audio(path, rate=RATE, channels=2, ffmpeg=None):
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("ffmpeg is required on PATH")
    cmd = [ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ar", str(rate), "-ac", str(channels), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise ValueError("cannot decode audio: " + r.stderr.decode(errors="replace").strip()[-300:])
    values = np.frombuffer(r.stdout, dtype="<f4")
    if not len(values) or len(values) % channels or not np.isfinite(values).all():
        raise ValueError("audio is empty or invalid")
    return values.reshape(-1, channels)


def loudness(path, ffmpeg=None):
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("ffmpeg is required on PATH")
    cmd = [
        ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", str(path), "-map", "0:a:0",
        "-af", "loudnorm=I=-16:LRA=11:TP=-1:print_format=json", "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    matches = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.DOTALL)
    if not matches:
        return {"integrated_lufs": None, "true_peak_dbtp": None, "lra_lu": None}
    data = json.loads(matches[-1])

    def val(k):
        try:
            v = float(data[k])
            return v if math.isfinite(v) else None
        except (KeyError, TypeError, ValueError):
            return None

    return {"integrated_lufs": val("input_i"), "true_peak_dbtp": val("input_tp"), "lra_lu": val("input_lra")}


def spectrum(samples):
    samples = np.asarray(samples, dtype=np.float64)
    count = min(len(samples), 8192)
    if count < 128:
        return {}
    step = max(1, count // 2)
    starts = range(0, len(samples) - count + 1, step)
    power = np.zeros(count // 2 + 1, dtype=np.float64)
    for start in starts:
        segment = samples[start:start + count] * np.hanning(count)[:, None]
        power += np.sum(np.abs(np.fft.rfft(segment, axis=0)) ** 2, axis=1)
    freqs = np.fft.rfftfreq(count, 1.0 / RATE)
    total = float(power.sum())
    if total <= 1e-20:
        return {}
    return {
        key: round(10.0 * math.log10(max(float(power[(freqs >= lo) & (freqs < hi)].sum()) / total, 1e-12)), 2)
        for key, (lo, hi) in BANDS.items()
    }


def measure(path, samples=None, ffmpeg=None):
    samples = decode_audio(path, ffmpeg=ffmpeg) if samples is None else samples
    meters = loudness(path, ffmpeg=ffmpeg)
    mid = (samples[:, 0].astype(np.float64) + samples[:, 1]) / 2.0
    side = (samples[:, 0].astype(np.float64) - samples[:, 1]) / 2.0
    mid_rms = float(np.sqrt(np.mean(mid ** 2)))
    side_rms = float(np.sqrt(np.mean(side ** 2)))
    width = 20.0 * math.log10(side_rms / mid_rms) if mid_rms > 1e-10 and side_rms > 1e-10 else None
    corr = float(np.corrcoef(samples[:, 0], samples[:, 1])[0, 1]) if all(np.std(samples[:, idx]) > 1e-10 for idx in (0, 1)) else None
    bands = spectrum(samples)
    duration = len(samples) / RATE
    if duration < 6.0 or meters["integrated_lufs"] is None:
        meters["lra_lu"] = None
    return {
        "file": str(path),
        "duration_s": round(duration, 3),
        "measurements": dict(
            meters,
            side_to_mid_db=round(width, 2) if width is not None else None,
            correlation=round(corr, 3) if corr is not None else None,
            spectrum_db=bands,
            sub_20_60_hz_percent=round(100.0 * 10.0 ** (bands["sub"] / 10.0), 3) if "sub" in bands else None,
        ),
        "reference": {"label": "seven launch films (n = 7)", "range": "10th to 90th percentile", "values": PROFILE},
        "limit": "Ranges describe seven launch films and are not a score. A person must listen.",
    }


def section_changes(samples):
    """Report sustained level changes of at least 8 dB (400 ms mean log RMS before and after)."""
    channels = np.asarray(samples, dtype=np.float32)
    hop, size = 240, 480
    if len(channels) < RATE:
        return []
    padded = np.pad(channels, ((size // 2, size // 2), (0, 0)), mode="reflect")
    count = (len(padded) - size) // hop + 1
    rms = np.empty(count, dtype=np.float64)
    for start in range(0, count, 1024):
        stop = min(count, start + 1024)
        indices = np.arange(start, stop)[:, None] * hop + np.arange(size)
        rms[start:stop] = np.sqrt(np.mean(padded[indices] ** 2, axis=(1, 2)))
    db = 20.0 * np.log10(np.maximum(rms, 1e-5))
    width = 80
    prefix = np.r_[0.0, np.cumsum(np.pad(db, (width, width), mode="edge"))]
    before = (prefix[width + np.arange(count) + 1] - prefix[np.arange(count)]) / (width + 1)
    after = (prefix[2 * width + np.arange(count) + 1] - prefix[width + np.arange(count)]) / (width + 1)
    jump = after - before
    result, index = [], max(width, 100)
    while index < count - width:
        if abs(jump[index]) >= 8.0:
            chosen = index + int(np.argmax(np.abs(jump[index:index + width])))
            result.append({
                "t": round(chosen * hop / RATE, 3),
                "change_db": round(float(jump[chosen]), 2),
                "method": "400 ms mean log RMS before and after",
            })
            index = chosen + width
        else:
            index += 1
    return result


def transcript(path, detail="normal"):
    import tempo_map
    samples = decode_audio(path)
    channels = decode_audio(path, rate=tempo_map.RATE, channels=2)
    detected = []
    for ch in range(channels.shape[1]):
        times, weights, _, _ = tempo_map.attacks(channels[:, ch])
        detected.extend((float(t), float(w)) for t, w in zip(times, weights))
    kept = []
    for t, w in sorted(detected, key=lambda pair: pair[1], reverse=True):
        if all(abs(t - other[0]) > 0.045 for other in kept):
            kept.append((t, w))
    mono = np.mean(channels, axis=1)
    channel_power = np.mean(channels.astype(np.float64) ** 2, axis=0)
    mono_power = float(np.mean(mono.astype(np.float64) ** 2))
    if mono_power < 0.25 * float(np.mean(channel_power)):
        choice = int(np.argmax(channel_power))
        mono = channels[:, choice]
        beat_signal = ("left" if choice == 0 else "right") + " channel; mono mix cancels"
    else:
        beat_signal = "mono mix"
    grid, grid_code = tempo_map.analyse(mono)
    return {
        "file": str(path),
        "duration_s": round(len(samples) / RATE, 3),
        "detail": detail,
        "events": [{"t": round(t, 3), "strength": round(w, 3), "kind": "onset"} for t, w in sorted(kept)],
        "sections": section_changes(samples),
        "beat_grid": grid,
        "beat_grid_status": "measured" if grid_code == 0 else "inconclusive",
        "beat_grid_signal": beat_signal,
        "limit": "Events are measured onsets, not identified sounds. A person must listen.",
    }


def coincidence(first, second, tolerance, duration, seed=0, iterations=200):
    """Compare event coincidence with circularly shifted event times."""
    first, second = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    result = {"n": len(first), "seed": seed, "iterations": iterations, "tolerance_s": tolerance}
    if len(first) == 0 or len(second) == 0 or duration <= 2.0:
        return dict(result, state="inconclusive", reason="too few events or duration for a shift null")

    def fraction(a, b):
        b = np.sort(b)
        pos = np.searchsorted(b, a)
        left = b[np.clip(pos - 1, 0, len(b) - 1)]
        right = b[np.clip(pos, 0, len(b) - 1)]
        return float(np.mean(np.minimum(np.abs(a - left), np.abs(a - right)) <= tolerance))

    observed = fraction(first, second)
    rng = np.random.default_rng(seed)
    null = [fraction(first, (second + shift) % duration) for shift in rng.uniform(1.0, duration - 1.0, iterations)]
    p95 = float(np.percentile(null, 95))
    return dict(
        result,
        state="above shifted chance" if observed > p95 else "not distinguishable",
        observed=round(observed, 4),
        chance_mean=round(float(np.mean(null)), 4),
        chance_p95=round(p95, 4),
        spread=[round(float(min(null)), 4), round(float(max(null)), 4)],
    )


def sheet(path, out_png, cues_list=None):
    """Draw a 5-lane time-aligned PNG of the sound: onsets, spectrogram, waveform, 8 dB sections, and beats/cues."""
    from PIL import Image, ImageDraw, ImageFont
    destination = Path(out_png)
    destination.parent.mkdir(parents=True, exist_ok=True)
    samples = decode_audio(path)
    tl = transcript(path)
    duration = len(samples) / RATE
    width, height, left, right = 1600, 760, 110, 1550
    panel = Image.new("RGB", (width, height), "#f8f8f5")
    draw = ImageDraw.Draw(panel)
    font = title = ImageFont.load_default()

    def x_of(t):
        return int(left + (right - left) * min(1.0, max(0.0, t / max(duration, 1e-9))))

    draw.text((left, 18), "Sound sheet: " + Path(path).name, fill="#18232b", font=title)
    draw.text((left, 42), f"{duration:.2f} s  |  {len(tl['events'])} onsets  |  Measurements only. A person must listen.", fill="#42545d", font=font)
    lanes = [("events", 100, 150), ("spectrum", 175, 420), ("waveform", 445, 555), ("sections", 580, 630), ("beats / cues", 655, 705)]
    for label, top, bottom in lanes:
        draw.text((8, top + 8), label, fill="#34444b", font=font)
        draw.rectangle((left, top, right, bottom), outline="#aebac0", width=1)
    for ev in tl["events"]:
        xx = x_of(ev["t"])
        draw.line((xx, 112, xx, 145), fill="#df6d35", width=2)

    columns, fft_size = right - left, 2048
    centers = np.linspace(0, max(0, len(samples) - 1), columns, dtype=int)
    padded = np.pad(samples, ((fft_size // 2, fft_size // 2), (0, 0)))
    window = np.hanning(fft_size).astype(np.float32)
    frequencies = np.fft.rfftfreq(fft_size, 1.0 / RATE)
    bins = np.clip(np.searchsorted(frequencies, np.geomspace(30, 16000, 245)), 0, len(frequencies) - 1)
    levels = np.empty((len(bins), columns), dtype=np.float32)
    for start in range(0, columns, 64):
        points = centers[start:start + 64, None] + np.arange(fft_size)[None, :]
        powers = np.sum(np.abs(np.fft.rfft(padded[points] * window[None, :, None], axis=1)) ** 2, axis=2)
        levels[:, start:start + len(points)] = (10.0 * np.log10(np.maximum(powers[:, bins], 1e-12))).T
    maximum = max(float(np.max(levels)), -40.0)
    intensity = np.clip((levels - maximum + 75.0) / 75.0, 0.0, 1.0)
    image = np.zeros((*intensity.shape, 3), dtype=np.uint8)
    image[:, :, 0] = (255 * np.clip(intensity * 1.7, 0.0, 1.0)).astype(np.uint8)
    image[:, :, 1] = (220 * np.clip((intensity - 0.3) * 1.7, 0.0, 1.0)).astype(np.uint8)
    image[:, :, 2] = (130 * np.clip((intensity - 0.65) * 2.8, 0.0, 1.0)).astype(np.uint8)
    panel.paste(Image.fromarray(np.flipud(image), "RGB"), (left, 175))
    draw = ImageDraw.Draw(panel)
    power = np.max(np.abs(samples), axis=1)
    indices = np.linspace(0, len(power), columns + 1).astype(int)
    for col in range(columns):
        lo, hi = indices[col], max(indices[col] + 1, indices[col + 1])
        peak = min(1.0, float(np.max(power[lo:hi]))) if lo < len(power) else 0.0
        half = int(48 * peak)
        draw.line((left + col, 500 - half, left + col, 500 + half), fill="#345c80")
    for sec in tl["sections"]:
        xx = x_of(sec["t"])
        draw.line((xx, 590, xx, 625), fill="#ad4840", width=2)
    grid = tl.get("beat_grid") or {}
    for beat in grid.get("downbeats") or []:
        if isinstance(beat, (int, float)) and 0.0 <= beat <= duration:
            xx = x_of(beat)
            draw.line((xx, 660, xx, 677), fill="#34444b", width=2)
    for cue in cues_list or []:
        t = cue.get("t") if isinstance(cue, dict) else (cue[1] if isinstance(cue, (list, tuple)) and len(cue) >= 2 else None)
        if isinstance(t, (int, float)) and 0.0 <= t <= duration:
            xx = x_of(float(t))
            draw.polygon(((xx - 5, 685), (xx + 5, 685), (xx, 697)), fill="#316a62")
    panel.save(destination, format="PNG")
    return {"png": str(destination.resolve()), "duration_s": round(duration, 3), "events": len(tl["events"])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("path")
    m.add_argument("--json", dest="json_out")
    t = sub.add_parser("transcript")
    t.add_argument("path")
    t.add_argument("--json", dest="json_out")
    sh = sub.add_parser("sheet")
    sh.add_argument("path")
    sh.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        res = measure(a.path)
        if a.json_out:
            Path(a.json_out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(res["measurements"]))
    elif a.cmd == "transcript":
        res = transcript(a.path)
        if a.json_out:
            Path(a.json_out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print(f"{Path(a.path).name}: {len(res['events'])} onsets, {len(res['sections'])} section jumps, beat_grid={res['beat_grid_status']}")
    elif a.cmd == "sheet":
        res = sheet(a.path, a.out)
        print(res["png"])
    return 0


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
