#!/usr/bin/env python3
"""Measure attack timing, tempo, downbeats, loudness rises and drift within a window, ported from legible-film. Into a
film (`vd audio --tempo-map`) it records them as a measure; the film's clock and mix do not change.

  python tempo_map.py music.wav [--bpm 120] [--start 0] [--window 48] [--drop-at-beat 32] [--json grid.json] [--into-film DIR]
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
RATE, HOP, FRAME = 16000, 16, 256


def decode_mono(path, rate=RATE, start=0.0, duration=None, ffmpeg=None):
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("ffmpeg is required on PATH")
    cmd = [ffmpeg, "-v", "error", "-nostdin"]
    if start and start > 0:
        cmd += ["-ss", f"{start:.6f}"]
    if duration is not None and duration > 0:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += ["-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise ValueError("cannot decode audio: " + p.stderr.decode(errors="replace")[-300:])
    x = np.frombuffer(p.stdout, dtype="<f4")
    if not len(x) or not np.isfinite(x).all():
        raise ValueError("decoded audio is empty or non-finite")
    return x.copy()


def rms_db(x):
    if len(x) == 0:
        return -120.0
    r = float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))
    return 20.0 * math.log10(max(r, 1e-12))


def attacks(x):
    """Log spectral flux, chunked STFT; refine isolated peaks to 1 ms waveform attacks."""
    padded = np.pad(x, (FRAME // 2, FRAME // 2))
    n = len(x) // HOP
    if n < 2:
        return np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0)
    full, low = np.zeros(n), np.zeros(n)
    prev = np.zeros(FRAME // 2 + 1)
    window = np.hanning(FRAME)
    freqs = np.fft.rfftfreq(FRAME, 1 / RATE)
    for a in range(0, n, 1024):
        b = min(n, a + 1024)
        starts = np.arange(a, b) * HOP
        frames = padded[starts[:, None] + np.arange(FRAME)] * window
        mag = np.log1p(20 * np.abs(np.fft.rfft(frames, axis=1)))
        delta = np.maximum(mag - np.vstack((prev, mag[:-1])), 0)
        full[a:b] = np.mean(delta, axis=1)
        low[a:b] = np.mean(delta[:, (freqs >= 35) & (freqs <= 250)], axis=1)
        prev = mag[-1]
    full /= max(float(np.percentile(full, 99)), 1e-10)
    low /= max(float(np.percentile(low, 99)), 1e-10)
    env = np.minimum(full, 4) * 0.55 + np.minimum(low, 4) * 0.45
    peaks = np.flatnonzero((env[1:-1] > env[:-2]) & (env[1:-1] >= env[2:]) & (env[1:-1] > max(0.12, float(np.percentile(env, 75)) * 1.4))) + 1
    if n > 1 and env[0] > 0.12 and env[0] >= env[1]:
        peaks = np.r_[0, peaks]
    keep = []
    blocked = np.zeros(n, dtype=bool)
    for k in peaks[np.argsort(env[peaks])[::-1]]:
        if not blocked[k]:
            keep.append(int(k))
            blocked[max(0, k - 45):k + 46] = True
    rms = np.sqrt(np.mean(x[:n * HOP].reshape(n, HOP).astype(np.float64) ** 2, axis=1))
    ts, weights, kicks = [], [], []
    for k in sorted(keep):
        lo, hi = max(0, k - 16), min(n, k + 13)
        seg = rms[lo:hi]
        peak = lo + int(np.argmax(seg))
        floor = float(np.min(seg))
        threshold = floor + 0.10 * (float(rms[peak]) - floor)
        edge = peak
        while edge > lo and rms[edge - 1] > threshold:
            edge -= 1
        isolated = floor < 0.25 * max(float(rms[peak]), 1e-10)
        ts.append(edge / 1000 if isolated else k / 1000)
        weights.append(float(env[k]))
        kicks.append(float(low[k]))
    return np.array(ts), np.array(weights), np.array(kicks), env


def grid_score(times, weights, duration, bpm, width=0.010):
    period = 60.0 / bpm
    bins = max(32, int(round(period * 1000)))
    phases = np.mod(times, period) / period * bins
    hist = np.bincount(np.floor(phases).astype(int) % bins, weights=weights, minlength=bins)
    radius = max(1, int(width * 1000))
    smoothed = sum(np.roll(hist, k) * math.exp(-0.5 * (k / (radius / 2)) ** 2) for k in range(-radius, radius + 1))
    phase = (int(np.argmax(smoothed)) + 0.5) / bins * period
    distance = np.abs((times - phase + period / 2) % period - period / 2)
    near = distance < width * 2
    if not near.any():
        return 0.0, phase
    response = np.exp(-0.5 * (distance / width) ** 2)
    recall = float(np.sum(weights * response) / max(weights.sum(), 1e-10))
    indices = np.round((times[near] - phase) / period).astype(int)
    strongest = {}
    for i, w in zip(indices, weights[near] * response[near]):
        strongest[i] = max(strongest.get(i, 0.0), float(w))
    count = max(1, int(duration / period))
    coverage = min(1.0, len(strongest) / count)
    return math.sqrt(max(0.0, recall * coverage)), phase


LOWEST, HIGHEST = 60.0, 200.0   # the tempos the fit reads, in BPM


def fit(times, weights, duration, prior=None, bounds=None):
    if prior is not None and prior <= 0:
        # read as "no tempo given" (0 is false), so --bpm 0 passed the range check (a review's finding)
        raise ValueError(f"a tempo of {prior:g} BPM is no tempo; give the beat as you hear it, {LOWEST:g} to {HIGHEST:g} BPM")
    if prior is not None and not LOWEST <= prior <= HIGHEST:
        # its search band (the prior +-3%) lay wholly outside the range, so nothing was searched and the fit crashed
        other = prior / 2 if prior > HIGHEST else prior * 2
        hint = (f"; give the same beat counted at {'half' if prior > HIGHEST else 'double'} speed, {other:g} BPM"
                if LOWEST <= other <= HIGHEST else "; give the beat as you count it within that range")   # 20 -> 40 is out too
        raise ValueError(f"a tempo of {prior:g} BPM is outside the {LOWEST:g} to {HIGHEST:g} BPM this reads{hint}")
    if len(times) < 6:
        raise ValueError("fewer than six strong attacks: no measurable beat grid")
    if bounds:
        lo, hi = bounds
    else:
        lo, hi = (max(60.0, prior * 0.97), min(200.0, prior * 1.03)) if prior else (60.0, 200.0)
    length = max(1, int(duration * 200) + 1)
    train = np.zeros(length)
    np.add.at(train, np.minimum((times * 200).astype(int), length - 1), weights)
    size = 1 << (2 * length - 1).bit_length()
    spectrum = np.fft.rfft(train, size)
    ac = np.fft.irfft(spectrum * np.conj(spectrum), size)[:length]
    lags = np.arange(max(1, int(12000 / hi)), min(length - 1, int(12000 / lo)) + 1)
    proposals = [12000.0 / k for k in lags[np.argsort(ac[lags])[-12:]]] if len(lags) else []
    candidates = list(np.arange(lo, hi + 0.001, 0.20)) + [p for p in proposals if lo <= p <= hi]
    if prior and lo <= prior <= hi:
        candidates.append(prior)

    def evaluate(bpm):
        score, phase = grid_score(times, weights, duration, bpm)
        penalty = math.exp(-0.5 * ((bpm / prior - 1) / 0.02) ** 2) if prior else 1.0
        return score * penalty, score, phase, bpm

    winners = sorted((evaluate(p) for p in candidates), reverse=True)[:6]
    fine = []
    for _, _, _, p in winners:
        fine.extend(np.arange(max(lo, p - 0.22), min(hi, p + 0.22) + 0.0001, 0.004))
    _, _score, phase, bpm = max((evaluate(p) for p in fine), default=winners[0])
    period = 60.0 / bpm
    for _ in range(4):
        grid = np.arange(phase, duration, period)
        picks, numbers, strengths = [], [], []
        for i, t in enumerate(grid):
            near = np.flatnonzero(np.abs(times - t) < min(0.045, period / 8))
            if near.size:
                j = near[np.argmax(weights[near] * np.exp(-0.5 * ((times[near] - t) / 0.015) ** 2))]
                picks.append(times[j])
                numbers.append(i)
                strengths.append(weights[j])
        if len(picks) < 4:
            break
        coef = np.polyfit(numbers, picks, 1, w=np.sqrt(strengths))
        residual = np.asarray(picks) - np.polyval(coef, numbers)
        good = np.abs(residual) < max(0.004, float(np.median(np.abs(residual))) * 3)
        if good.sum() >= 4:
            coef = np.polyfit(np.asarray(numbers)[good], np.asarray(picks)[good], 1, w=np.sqrt(np.asarray(strengths)[good]))
        if lo <= 60.0 / coef[0] <= hi:
            period, phase = float(coef[0]), float(coef[1])
        else:
            break
    phase %= period
    if period - phase < 1e-7:
        phase = 0.0
    score, _ = grid_score(times, weights, duration, 60.0 / period)
    return period, phase, score


STRETCH = 16    # beats in a stretch whose offset from the grid and tempo are reported
REACH = 0.2     # of a beat: how far from a grid beat its attack is looked for


def beat_drift(times, weights, offset, period, duration, start=0.0):
    """How far the music's own beats slide from one steady grid (offset, period). For each grid beat, the strongest attack
    within REACH of a beat of it and its signed offset; for each stretch of STRETCH beats (a short last one joins the one
    before), the median of those offsets and the stretch's own tempo, fitted to it alone within 15% of the whole. The
    drift is how far the stretches' median offsets range, in ms. Read on music made to an exact grid (the four worked
    films' tracks) it is 0 to 14 ms; on clicks speeding up from 116 to 120 BPM, 43; from 112 to 124, 61.
    What it cannot do: follow a beat. Attacks further than REACH from the grid are not seen, so for a track that drifts
    further the drift is a floor. A 1906 band record a listener heard speed up 10% reads 34 ms over its first 28 s and
    69 ms over all 118 s; no reading here confirms or rules out that 10%. A stretch's own tempo is a reading, not a
    finding: on music made to an exact 120 BPM one stretch read 126. Returns (stretches, drift_ms), drift_ms None with
    fewer than 8 beats seen."""
    k, r = [], []
    for g in np.arange(offset, duration, period):
        near = np.flatnonzero(np.abs(times - g) <= REACH * period)
        if near.size:
            j = near[np.argmax(weights[near])]
            k.append(g)
            r.append(times[j] - g)
    k, r = np.asarray(k), np.asarray(r)
    if len(k) < 8:
        return [], None
    stretches = []
    edges = list(np.arange(offset, duration, STRETCH * period)) + [duration]
    if len(edges) > 2 and edges[-1] - edges[-2] < 0.75 * STRETCH * period:
        del edges[-2]   # a short last stretch reads a few beats (an ending, a held note) as a slide: it joins the one before
    for a, b in zip(edges[:-1], edges[1:]):
        m = (k >= a) & (k < b)
        if m.sum() >= STRETCH // 2:
            here = (times >= a) & (times < b)
            try:
                own = round(60.0 / fit(times[here] - a, weights[here], b - a, None, (60.0 / period * 0.85, 60.0 / period * 1.15))[0], 2)
            except ValueError:   # too few attacks in it to fit
                own = None
            stretches.append({"from_s": round(start + float(a), 3), "to_s": round(start + float(b), 3), "bpm": own,
                              "off_ms": round(1000 * float(np.median(r[m])), 1)})
    # a smooth trend through every offset was tried and dropped: on Onoma's music its range moved from 10 to 58 ms when
    # the grid's origin moved 10 ms, and once the beat slides past REACH off-beat notes flatten it (8 ms for 112 to 124)
    offs = [x["off_ms"] for x in stretches]
    return stretches, round(max(offs) - min(offs), 1) if len(offs) > 1 else 0.0


def analyse(x, start=0.0, bpm=None, beats_per_bar=4, drop_at_beat=None, tolerance_ms=15.0):
    duration = len(x) / RATE
    times, weights, kicks, _env = attacks(x)
    if len(times) < 6:
        result = {
            "bpm": None, "period_s": None, "offset_s": None, "downbeats": [], "bar_s": None,
            "drops": [], "grid_strength": 0, "residual_ms": {"median": None, "p90": None, "missing_beats": None},
            "drift_ms": None, "stretches": [], "alternatives": [], "duration_s": duration, "start_s": start,
            "film_beats_available": 0, "flags": ["fewer than six strong attacks: no measurable grid"],
            "limit": "Timing only; too little attack evidence to estimate tempo. Unheard.",
        }
        if drop_at_beat is not None:
            result.update(suggested_offset_s=None, suggested_offset_negative=False)
        return result, 1
    period, phase, strength = fit(times, weights, duration, bpm)
    grid = np.arange(phase - period if phase > 0.75 * period else phase, duration, period)
    kick_scores = []
    for slot in range(beats_per_bar):
        vals = []
        for t in grid[slot::beats_per_bar]:
            near = np.abs(times - t) < period / 8
            vals.append(float(np.max(kicks[near])) if near.any() else 0.0)
        kick_scores.append(float(np.mean(vals)) if vals else 0.0)
    slot = int(np.argmax(kick_scores))
    projected_down = grid[slot::beats_per_bar]
    measured_down = []
    for t in projected_down:
        near = np.flatnonzero((np.abs(times - t) < period / 4) & (weights > 0.10))
        if near.size:
            j = near[np.argmax(kicks[near] * np.exp(-0.5 * ((times[near] - t) / 0.035) ** 2))]
            measured_down.append(float(times[j]))
    offset = float(measured_down[0] if measured_down else projected_down[0])
    down = np.array(measured_down)
    grid = np.arange(offset, duration, period)
    residuals, missing = [], 0
    for t in grid:
        distances = np.abs(times - t)
        near = distances[distances <= period / 4]
        if near.size:
            residuals.append(float(near.min()) * 1000.0)
        else:
            missing += 1
    # drift: each half was fitted within 1.5% of the whole, so a band speeding up 10% read as steady; the beats' offsets
    # from one grid, stretch by stretch, show it
    stretches, drift = beat_drift(times, weights, offset, period, duration, start)
    bar = period * beats_per_bar
    drops = []
    for t in down:
        if t < bar or t + bar > duration:
            continue
        before = x[max(0, int((t - bar) * RATE)):int(t * RATE)]
        after = x[int(t * RATE):min(len(x), int((t + 2 * bar) * RATE))]
        rise = rms_db(after) - rms_db(before)
        if rise > 1.0:
            drops.append({"music_s": round(start + float(t), 6), "film_beat": round((t - offset) / period), "rise_db": round(rise, 3)})
    drops.sort(key=lambda d: d["rise_db"], reverse=True)
    alternatives = []
    for name, factor in (("half", 0.5), ("double", 2.0), ("two_thirds", 2.0 / 3.0)):
        score, _ = grid_score(times, weights, duration, 60.0 / period * factor)
        alternatives.append({"tempo": name, "bpm": 60.0 / period * factor, "score": round(score, 4)})
    median = float(np.median(residuals)) if residuals else None
    p90 = float(np.percentile(residuals, 90)) if residuals else None
    reasons = []
    if strength < 0.45 or missing > len(grid) * 0.2:
        reasons.append("weak grid or too many beats without a strong onset")
    if p90 is None or p90 > tolerance_ms:
        reasons.append("onset residual exceeds tolerance")
    if drift is None or abs(drift) > tolerance_ms:
        reasons.append("drift exceeds tolerance or could not be measured")
    if any(v["score"] >= strength * 0.9 for v in alternatives):
        reasons.append("alternative tempo within 10%: ambiguous")
    result = {
        "bpm": 60.0 / period, "period_s": period, "offset_s": start + offset, "fit_phase_s": start + phase,
        "downbeats": [round(start + float(t), 6) for t in down[:16]], "bar_s": bar,
        "drops": drops, "grid_strength": round(strength, 4),
        "residual_ms": {"median": median, "p90": p90, "missing_beats": missing},
        "drift_ms": drift, "stretches": stretches, "alternatives": alternatives,
        "duration_s": duration, "start_s": start,
        "film_beats_available": max(0, int((duration - offset) / period)),
        "kick_slot_scores": kick_scores, "flags": reasons,
        "attacks": [{"t": round(start + float(t), 4), "weight": round(float(w), 3)} for t, w in zip(times[:64], weights[:64])],
        "limit": "Timing only; downbeat and drop are attack/loudness hypotheses. Unheard.",
    }
    if drop_at_beat is not None:
        suggested = None
        if drops and len(down):
            target = drops[0]["music_s"] - drop_at_beat * period
            snap, step, snap_kind = down, bar, "downbeat"
            if drop_at_beat % beats_per_bar:
                measured_beats = []
                for t in grid:
                    near = np.flatnonzero((np.abs(times - t) < period / 4) & (weights > 0.10))
                    if near.size:
                        measured_beats.append(float(times[near[np.argmin(np.abs(times[near] - t))]]))
                if measured_beats:
                    snap, step, snap_kind = np.array(measured_beats), period, "beat"
            extrapolated = target < start + float(snap[0]) or target > start + float(snap[-1])
            if extrapolated:
                index = round((target - (start + offset)) / step)
                suggested = start + offset + index * step
            else:
                suggested = start + float(snap[np.argmin(np.abs(start + snap - target))])
            result["suggested_offset_extrapolated"] = extrapolated
            result["drop_alignment_error_ms"] = (drops[0]["music_s"] - suggested - drop_at_beat * period) * 1000.0
            if abs(result["drop_alignment_error_ms"]) > tolerance_ms:
                reasons.append(f"requested drop beat cannot align after {snap_kind} snapping")
        result["suggested_offset_s"] = suggested
        result["suggested_offset_negative"] = suggested is not None and suggested < 0
        if not drops:
            reasons.append("no measurable drop for requested alignment")
    return result, (1 if reasons else 0)


def analyse_file(music_path, bpm=None, start=0.0, window=None, beats_per_bar=4, drop_at_beat=None, tolerance_ms=15.0, json_out=None):
    x = decode_mono(music_path, rate=RATE, start=start, duration=window)
    result, code = analyse(x, start=start, bpm=bpm, beats_per_bar=beats_per_bar, drop_at_beat=drop_at_beat, tolerance_ms=tolerance_ms)
    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return result, code


MAX_STRETCH = 0.03   # the most a track is sped up or slowed to sit on a whole number of frames a beat (60 fps: 1.8% at worst near 128 BPM)
DRIFT_MAX_MS = 40    # the most a track's beat may slide from one steady grid: past a frame at 25 fps, and near the 45 ms by which
                     # sound ahead of picture starts to be noticed (ITU-R BT.1359). Music made to a grid reads 0 to 14 ms.


def compile_into_film(film_dir: Path, music_path: Path, bpm=None, drop_at_beat=None, replace=False):
    """Make an external music track the film's beat. Records it in score.json's `music` (its tempo, the film's frames a
    beat `fb` nearest to it, the stretch that puts it on that beat, and where it sits) and writes the track so fitted,
    media/NAME-fitted.wav: sped up or slowed by at most MAX_STRETCH, and placed so its first beat, or its loudest drop
    with drop_at_beat, falls on a beat of the film. kit/times.gen.ts is the film's sound.py's: each worked film's
    sound.py takes `fb` from score.json's music, so running it puts every beat, note and picture event on the track's
    tempo; the mix (vd sound, vd export) lays the fitted track under the film's own sound, or in its place with replace.
    Returns (analysis, score.json path). Refuses before writing anything a track with no steady beat or one that would need
    more stretch; how far its beats sit from the grid is recorded (off_grid_ms) and said, to be listened to."""
    import lean
    film_dir = Path(film_dir).resolve()
    music_path = Path(music_path).resolve()
    res, code = analyse_file(music_path, bpm=bpm, drop_at_beat=drop_at_beat)
    flags = res.get("flags") or []
    if res.get("bpm") is None:
        raise ValueError(f"{music_path.name}: no beat grid to map ({'; '.join(flags or ['the fit failed'])}); the film's clock is unchanged")
    if bpm is None and any("weak grid" in f for f in flags):
        # a weak grid is no beat to trust: white noise read as 177.6 BPM and a drone as 198, at a strength (0.30, 0.32) as
        # high as Onoma's own music (0.32). With its tempo given, as heard, the fit is held to it.
        raise ValueError(f"{music_path.name}: its beat is weak ({'; '.join(flags)}), and a weak grid fits noise as well as music. "
                         "If it has a beat, give its tempo as you hear it with --bpm. The film's clock is unchanged")
    s = lean.score_of(film_dir)
    fps = int(s.get("fps") or 60)
    det_bpm = float(res["bpm"])
    octave_note = None
    have_fb = (lean.gen_data(film_dir).get("CLOCK") or {}).get("FB")
    if bpm is None and have_fb and any("ambiguous" in f for f in flags):
        # attacks cannot tell a tempo from its half or double (Linden's 100 BPM read as 200, which halved the film): of the
        # three, the one nearest the film's own beat is taken, and said
        near = min((det_bpm / 2, det_bpm, det_bpm * 2), key=lambda b: abs(60.0 * fps / b - have_fb))
        if near != det_bpm:
            octave_note = f"read as {det_bpm:.2f} BPM, taken as {near:.2f}, the octave nearest the film's own beat ({have_fb} frames); give --bpm to choose"
            det_bpm = near
    fb = int(round(60.0 * fps / det_bpm))
    film_bpm = 60.0 * fps / fb
    stretch = film_bpm / det_bpm          # >1 speeds the track up
    if abs(stretch - 1.0) > MAX_STRETCH:
        raise ValueError(f"{music_path.name}: {det_bpm:.2f} BPM is {abs(stretch - 1) * 100:.1f}% from the nearest beat a {fps} fps film can hold "
                         f"({film_bpm:.2f} BPM at {fb} frames); more than {MAX_STRETCH * 100:g}% would change how it sounds. The film's clock is unchanged")
    # A film's grid is one steady tempo. The old drift measure (each half fitted within 1.5% of the whole) could not tell
    # a drifting track from the accepted films' own music (Onoma's read 120 ms), so nothing was ever refused. beat_drift
    # reads those films' tracks at 0 to 14 ms and clicks speeding up 3% at 43 (its limits are in its own note).
    drift = res.get("drift_ms")
    if drift is not None and drift > DRIFT_MAX_MS:
        where = "; ".join(f"{x['from_s']:g}-{x['to_s']:g} s at {x['bpm']:g} BPM, {x['off_ms']:+g} ms" for x in res.get("stretches") or [])
        raise ValueError(f"{music_path.name}: its beat slides {drift:.0f} ms against one steady {det_bpm:.2f} BPM grid over the track "
                         f"(stretch by stretch, tempo and offset from the grid: {where}). A film's grid holds one steady tempo, and a beat "
                         f"more than {DRIFT_MAX_MS:g} ms off it puts the picture's hits audibly off the music's; this does not follow a "
                         "changing tempo. Use a track made to a steady beat, or cut a stretch whose beat holds and map that. "
                         "The film's clock is unchanged")
    if drop_at_beat is not None and not res.get("drops"):
        raise ValueError(f"{music_path.name}: --drop-at-beat {drop_at_beat} asks for its drop, and no drop was measured in it; "
                         "place it by its first beat (leave --drop-at-beat out). The film's clock is unchanged")
    beat_s = fb / fps
    # where the track sits, in seconds of the fitted track: its first downbeat on beat 0, or its drop on drop_at_beat
    first = float(res.get("offset_s") or 0.0) / stretch
    if drop_at_beat is not None and res.get("drops"):
        anchor, on = float(res["drops"][0]["music_s"]) / stretch, drop_at_beat * beat_s
    else:
        anchor, on = first, 0.0
    shift = on - anchor                   # > 0: the track starts later than the film; < 0: its start is cut
    at, start = (round(shift, 4), 0.0) if shift >= 0 else (0.0, round(-shift, 4))
    (film_dir / "media").mkdir(parents=True, exist_ok=True)
    # a name of its own: never the track, nor a file score.json already uses (a voice called NAME-fitted.wav was written over)
    v = s.get("voice")
    used = {music_path} | {(film_dir / f).resolve() for f in (v.get("file") if isinstance(v, dict) else v, s.get("sound_file"), s.get("tone"),
                                                              (s.get("bed") or {}).get("file"),
                                                              *[e.get("file") for e in s.get("stems", []) + s.get("sounds", [])]) if f}
    old = (s.get("music") or {}).get("file")
    used.discard((film_dir / old).resolve() if old else None)          # the track this one replaces may be written over
    fitted = next(c for c in (film_dir / "media" / f"{music_path.stem}-fitted{'' if n == 1 else f'-{n}'}.wav" for n in range(1, 1000))
                  if c.resolve() not in used)
    ff = shutil.which("ffmpeg") or "ffmpeg"
    p = subprocess.run([ff, "-v", "error", "-y", "-i", str(music_path), "-af", f"atempo={stretch:.6f}", "-ar", "48000", "-ac", "2",
                        "-c:a", "pcm_s16le", str(fitted)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode or not fitted.is_file():
        raise ValueError(f"{music_path.name}: ffmpeg could not fit it: {(p.stderr or '')[-300:]}")
    s.pop("tempo_map", None)
    s["music"] = {"file": fitted.relative_to(film_dir).as_posix(), "source": music_path.name, "bpm": round(det_bpm, 3), "fb": fb,
                  "film_bpm": round(film_bpm, 3), "stretch": round(stretch, 6), "at": at, "from": start,
                  "drop_at_beat": drop_at_beat, "gain": 0.0, "replace": bool(replace), "octave": octave_note,
                  "first_beat_s": round(first + shift, 4)}   # where the track's first beat falls in the film (the file can start before it)
    (film_dir / "score.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
    s["music"]["off_grid_ms"] = {"median": round(float((res.get("residual_ms") or {}).get("median") or 0.0), 1),
                                 "p90": round(float((res.get("residual_ms") or {}).get("p90") or 0.0), 1),
                                 "drift": drift}
    (film_dir / "score.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
    return res, film_dir / "score.json"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("music")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--window", type=float)
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--drop-at-beat", type=int)
    ap.add_argument("--tolerance-ms", type=float, default=15.0)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--into-film", dest="film_dir", help="also compile beat grid into FILM/kit/times.gen.ts and score.json")
    a = ap.parse_args(argv)
    try:
        if a.film_dir:
            res, gen_path = compile_into_film(Path(a.film_dir), Path(a.music), bpm=a.bpm, drop_at_beat=a.drop_at_beat)
            if a.json_out:
                Path(a.json_out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
            print(f"compiled tempo map ({res['bpm']:.2f} BPM, downbeat {res['offset_s']:.3f} s) -> {gen_path}")
            return 0
        res, code = analyse_file(
            a.music, bpm=a.bpm, start=a.start, window=a.window, beats_per_bar=a.beats_per_bar,
            drop_at_beat=a.drop_at_beat, tolerance_ms=a.tolerance_ms, json_out=a.json_out,
        )
    except ValueError as e:
        raise SystemExit(f"tempo_map: {e}")
    tempo = f"{res['bpm']:.3f}" if res["bpm"] is not None else "unknown"
    phase = f"{res['offset_s']:.4f}" if res["offset_s"] is not None else "unknown"
    print(f"{Path(a.music).name}: {tempo} BPM, downbeat {phase} s; strength {res['grid_strength']}; residual {res['residual_ms']}; "
          f"drift {res['drift_ms']} ms against one steady grid (more than {DRIFT_MAX_MS:g} ms and --into-film refuses it)")
    if res.get("stretches"):
        print("  stretch by stretch: " + "; ".join(f"{x['from_s']:g}-{x['to_s']:g} s {x['bpm']:g} BPM, {x['off_ms']:+g} ms" for x in res["stretches"]))
    return code


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
