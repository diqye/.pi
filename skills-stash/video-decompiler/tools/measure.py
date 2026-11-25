#!/usr/bin/env python3
"""Measure a video's feel by code, so a rebuild or a refill can be held to it.

  python measure.py VIDEO --out DIR
  python measure.py compare SOURCE_DIR OTHER_DIR --as rebuild|refill [--out FILE]

The first writes DIR/measure.json and DIR/beats-N.jpg (a still after each event, timestamped) and prints a summary.
Every model gets the same numbers from it, which readings by eye don't give: three models reading the same videos put
the same boundaries within 0.6 s, but one of them ran 1.3 to 3.9 s late wherever it worked by eye.

- Events: hard cuts, and each move that starts after a hold. A reading's timestamps should be these.
- Holds and moves: how long the picture rests and how long it moves.
- Per hold: how much of the frame is drawn (occupancy), how busy it is (detail), its palette, and its ink bands, the
  runs of rows with drawn pixels. The tallest band is the biggest element's height, such as a punch word's.
- Sound: onsets, a tempo if there is one, and which events land on an onset, against what chance gives.
- An encoder's keyframe in a low-bitrate copy shifts the whole picture a little in one frame: such a change (on one of
  the file's keyframes, no more than PULSE, the picture still on both sides) is not counted as a move or an event.

A move's easing is read from how much the picture changes. That stops following speed once a thing moves further in a
frame than its own size (a small cursor or icon, fast), or across fine texture. Such a move is kept with
"ease_reliable": false and its easing, peak and length are not measurements; compare skips it and says so.

With --from/--to, "video" is the file measured, "window" the stretch, "window_seconds" its length (also "duration"),
"film_seconds" the whole file's, and every time is on the whole file's clock ("energy_t0" is where energy starts).

compare --as rebuild: the events must match within 2 frames, one to one, and each hold's look within tolerance.
compare --as refill: content and length differ, so rates and distributions must match instead: events per 10 s, hold
and move lengths, occupancy, detail, the biggest element's height, and sync to sound.
"""
import argparse
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_diff import NO_WINDOW, check_decode, check_window, clock, ffprobe, find_cuts, fps_of, seek_to, stop_decoder  # noqa: E402
import space  # noqa: E402

AW, AH = 320, 180
# mean absolute luma change between frames, at AW x AH, above which the picture is moving. see.py uses the same 0.35
# on frames 480 px wide. Shrinking a picture averages its noise away, so the same film crosses the two at slightly
# different moments; the two tools' rest and motion can disagree by a frame or so near the line.
MOVE = 0.35
MIN_HOLD = 0.1     # seconds: a shorter rest inside a move is part of the move
READ = 0.25        # seconds: a hold at least this long is a rest a viewer reads; shorter ones are typing's gaps
STILL = 0.05       # energy below this is a dead-still picture
MOVE_FIT = 3.0     # seconds: moves up to this long get an easing fit; longer ones are several motions run together
SYNC = 0.05        # seconds: an event this close to an onset lands on it
LINEAR = 0.75      # at a move's fastest frames, change over two frames against the two single-frame changes added up:
                   # 1.0 while change follows speed, 0.5 once a thing moves further in a frame than its size
PULSE = 2.0        # a lone change no bigger than this on one of the file's keyframes, still on both sides, is the encoder's


def probe(path):
    raw = ffprobe(path)
    return {"w": raw["w"], "h": raw["h"], "fps": fps_of(raw), "duration": raw["duration"], "audio": raw["audio"]}


def frames(path, fps, duration=None):
    """Every frame at fps, small. Read to the end, a decode that failed or stopped short of `duration` stops the tool."""
    said = tempfile.TemporaryFile()  # a file, not a pipe: a stream of errors can't fill it and stall ffmpeg
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={fps},scale={AW}:{AH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=said, creationflags=NO_WINDOW)
    size, n, ended = AW * AH * 3, 0, False
    try:
        while True:
            raw = p.stdout.read(size)
            if len(raw) < size:
                ended = True
                break
            n += 1
            yield np.frombuffer(raw, np.uint8).reshape(AH, AW, 3)
    finally:  # a caller may stop early; ffmpeg must not be left writing to a pipe nobody reads
        p.stdout.close()
        if not ended:
            stop_decoder(p)
        p.wait()
        said.seek(0)
        text = said.read()
        said.close()
    check_decode(path, p.returncode, text, n / fps, duration)  # only reached when every frame was read


def analysed_frame(path, fps, k):
    """Analysed frame k decoded again: the rare fallback when a hold's sharp still can't be grabbed. Keeping every
    analysed frame for it held 1.9 GB on a 3 minute film."""
    return next(itertools.islice(frames(path, fps), k, None), None)


LOOK_W, LOOK_H = 960, 540  # holds are looked at this size: at AW x AH a 3 px gap between headline lines vanishes
VERSION = 10              # bump when a measure changes, so compares never mix measurements made two ways (5: the summary
                          # says how the film moves, as a scene or as a sheet being slid, read by space.py. 6: and in how
                          # many of its frames the middle is lit and all four corners are darker. 7: a beat-grid fit; 8: tempo_map's beat-grid fit, which reads Stet as 150, not 75; 9: each hold's ground, its border's commonest colour;
                          # 10: a keyframe's compression pulse over a still picture is no change, quiet_keyframes)
DARKER = 0.9              # a corner is darker than the middle when it gives off less than nine tenths of its light
LIT = 0.02                # and a middle this dark isn't lit at all: a black frame is not a lit middle


def lit_middle(rgb):
    """Is this frame a lit middle with four darker corners? The middle is the centre ninth of the frame and a corner is a
    thirty-sixth, compared in light given off, not in the numbers a file stores. Every film a fresh agent made with this
    skill was that picture in 78% to 95% of its frames: a vignette pasted from an example, a ground that darkens round
    the middle of the frame and a subject always in the centre add up to it. The middle studio film is, in 28%."""
    light = (cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255) ** 2.2
    h, w = light.shape
    middle = float(light[h // 3:2 * h // 3, w // 3:2 * w // 3].mean())
    a, b = h // 6, w // 6
    corners = (light[:a, :b], light[:a, -b:], light[-a:, :b], light[-a:, -b:])
    return middle > LIT and all(float(c.mean()) < DARKER * middle for c in corners)


def grab(path, t, times=None):
    """The frame nearest time t, at LOOK_W x LOOK_H, for a hold's look. Seeking to t printed to 3 decimals returned the
    next frame one time in three; seek_to lands on the frame itself."""
    at = seek_to(clock(path) if times is None else times, t)[0]
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{at:.6f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={LOOK_W}:{LOOK_H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, creationflags=NO_WINDOW)
    if len(p.stdout) < LOOK_W * LOOK_H * 3:
        return None
    return np.frombuffer(p.stdout[:LOOK_W * LOOK_H * 3], np.uint8).reshape(LOOK_H, LOOK_W, 3)


def background(rgb):
    """The frame's ground: the commonest colour along its border."""
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(int)
    keys = (border // 16) @ np.array([256, 16, 1])
    common = np.bincount(keys).argmax()
    return border[keys == common].mean(axis=0)


def look(rgb):
    """Occupancy, detail, ink bands and palette of one still."""
    mask = np.abs(rgb.astype(int) - background(rgb)).max(axis=2) > 40
    rows = mask.mean(axis=1) > 0.004
    bands, start = [], None
    for y, on in enumerate(list(rows) + [False]):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start >= 2:
                bands.append((y - start) / rgb.shape[0])
            start = None
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    small = cv2.resize(rgb, (80, 45), interpolation=cv2.INTER_AREA).reshape(-1, 3).astype(np.float32)
    # k-means draws its starting centres from OpenCV's global random generator, so without a fixed seed the palette
    # depended on how many pictures this process had looked at before
    cv2.setRNGSeed(0)
    _, labels, centres = cv2.kmeans(small, 4, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 2, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(labels.ravel(), minlength=4) / len(labels)
    palette = sorted(((("#%02x%02x%02x" % tuple(int(v) for v in c)), round(float(s), 3)) for c, s in zip(centres, share)), key=lambda x: -x[1])
    ground = "#%02x%02x%02x" % tuple(int(round(v)) for v in background(rgb))
    return {"occupancy": round(float(mask.mean()), 3), "detail": round(float(cv2.Canny(gray, 60, 160).mean() / 255), 4), "ground": ground,
            "bands": [round(b, 3) for b in sorted(bands, reverse=True)[:6]], "largest_band": round(max(bands), 3) if bands else 0.0, "palette": palette}


def keyframe_times(path):
    """The presentation times of the file's keyframes, read from its packets (nothing decoded)."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    out = []
    for line in p.stdout.splitlines():
        t, _, flags = line.partition(",")
        try:
            if "K" in flags:
                out.append(float(t))
        except ValueError:     # a packet with no time
            pass
    return sorted(out)


def quiet_keyframes(energy, keys, first, fps):
    """Take the encoder's pulses out of the change curve: at a keyframe a low-bitrate copy resets its compression and the
    whole picture shifts a little in one frame. il's copy, a keyframe every 3.000 s, changed 0.39 to 0.76 in that frame
    over a still picture (0.0 to 0.32 either side), and each was counted as a move and an event. Such a frame (a
    keyframe, its change no more than PULSE, still on both sides) takes its neighbours' change. A cut is over 12, and a
    real change between keyframes is left as it is. Returns the frames quieted."""
    quieted = []
    for k in keys:
        i = int(round((k - first) * fps))
        if 0 < i < len(energy) - 1 and MOVE < energy[i] <= PULSE and energy[i - 1] <= MOVE and energy[i + 1] <= MOVE:
            energy[i] = max(energy[i - 1], energy[i + 1])
            quieted.append(i)
    return quieted


def segments(energy, fps):
    """Holds and moves as (kind, first frame, end frame), with short rests folded into the moves around them."""
    moving = list(energy > MOVE)
    if len(moving) > 1:
        moving[0] = moving[1]  # the first frame has nothing before it to differ from, so it says nothing about rest
    runs, start = [], 0
    for i in range(1, len(moving) + 1):
        if i == len(moving) or moving[i] != moving[start]:
            runs.append(["move" if moving[start] else "hold", start, i])
            start = i
    shortest = max(1, round(MIN_HOLD * fps))
    for r in runs:
        if r[0] == "hold" and r[2] - r[1] < shortest and r[1] > 0 and r[2] < len(moving):
            r[0] = "move"
    merged = []
    for r in runs:
        if merged and merged[-1][0] == r[0]:
            merged[-1][2] = r[2]
        else:
            merged.append(list(r))
    return merged


def audio(path, duration):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, creationflags=NO_WINDOW)
    check_decode(path, p.returncode, p.stderr, len(p.stdout) / 2 / 16000, duration)  # whole pictures and broken sound: not half a soundtrack read as all
    x = np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768
    hop = 160
    n = len(x) // hop
    if n < 50:
        return None
    rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-10)
    level = 20 * np.log10(rms)
    flux = np.maximum(0, np.diff(level, prepend=level[0]))
    flux = np.convolve(flux, np.ones(3) / 3, mode="same")
    onsets = []
    for i in range(1, n - 1):
        lo, hi = max(0, i - 50), min(n, i + 50)
        local = flux[lo:hi]
        if flux[i] >= flux[i - 1] and flux[i] > flux[i + 1] and flux[i] > local.mean() + 2 * local.std() and level[i] > -50:
            if not onsets or i - onsets[-1] >= 5:
                onsets.append(i)
    # The tempo is tempo_map's beat-grid fit (attacks scored against a grid), not the peak of a level autocorrelation:
    # on the four accepted films that peak read 150, 240, 222 and 67 BPM for 150, 120, 112.5 and 100 (one right, two at
    # no octave of the truth); the grid fit reads 150, 120, 112.5 and 200 (Linden's double: every true beat lies on it).
    # Attacks alone cannot tell a tempo from its half or double, so `octave` names both beside it.
    tempo = None
    try:
        import tempo_map
        times, weights, _, _ = tempo_map.attacks(x)
        period, _, strength = tempo_map.fit(times, weights, len(x) / 16000)
        if strength > 0.2:
            bpm = float(60.0 / period)
            tempo = {"bpm": round(bpm, 1), "strength": round(float(strength), 2), "octave": [round(bpm / 2, 1), round(bpm * 2, 1)]}
    except ValueError:  # fewer than six strong attacks: no pulse to measure
        pass
    loud = level[level > -60]
    return {"onsets": [round(i * hop / 16000, 3) for i in onsets], "tempo": tempo, "mean_db": round(float(loud.mean()), 1) if len(loud) else None}


def sync_rate(events, onsets, duration, tolerance=SYNC, trials=300, seed=0):
    if not events or not onsets:
        return None, None
    o = np.array(onsets)
    near = lambda ts: float(np.mean([np.min(np.abs(o - t)) <= tolerance for t in ts]))
    rng = np.random.default_rng(seed)
    chance = float(np.mean([near((np.array(events) + rng.uniform(0, duration)) % duration) for _ in range(trials)]))
    return round(near(events), 3), round(chance, 3)


def sheet(path, times, out, fps, clock_times=None):
    tiles = []
    clock_times = clock(path) if clock_times is None else clock_times
    for t in times:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{seek_to(clock_times, t)[0]:.6f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=320:180", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, creationflags=NO_WINDOW)
        if len(p.stdout) < 320 * 180 * 3:
            continue
        im = Image.frombytes("RGB", (320, 180), p.stdout[:320 * 180 * 3])
        ImageDraw.Draw(im).rectangle([0, 0, 70, 16], fill=(0, 0, 0))
        ImageDraw.Draw(im).text((4, 2), f"{t + LABEL_OFFSET:6.2f}s", fill=(255, 255, 0))
        tiles.append(im)
    files = []
    for k in range(0, len(tiles), 40):
        chunk = tiles[k:k + 40]
        cols = 5
        board = Image.new("RGB", (320 * cols, 180 * ((len(chunk) + cols - 1) // cols)), (40, 40, 40))
        for i, im in enumerate(chunk):
            board.paste(im, ((i % cols) * 320, (i // cols) * 180))
        name = out / f"beats-{k // 40 + 1}.jpg"
        board.save(name, quality=85)
        files.append(name.name)
    return files


_PROFILES = None
POINTS = 24


def bezier_profiles():
    """The speed profile of every cubic-bezier(x1, y1, x2, y2) easing on a 0.1 grid (y2 up to 1.3, for overshoot):
    progress against time, differenced into POINTS steps and scaled to a peak of 1."""
    global _PROFILES
    if _PROFILES is None:
        g, gy2 = np.round(np.arange(0, 1.01, 0.1), 1), np.round(np.arange(0, 1.31, 0.1), 1)
        params = np.array([(a, b, c, d) for a in g for b in g for c in g for d in gy2])
        s = np.linspace(0, 1, 160)[None, :]
        x1, y1, x2, y2 = (params[:, i:i + 1] for i in range(4))
        bx = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s ** 2 * x2 + s ** 3
        by = 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s ** 2 * y2 + s ** 3
        t = np.linspace(0, 1, POINTS + 1)
        prog = np.array([np.interp(t, bx[k], by[k]) for k in range(len(params))])
        v = np.abs(np.diff(prog, axis=1))
        _PROFILES = (params, v / np.maximum(v.max(axis=1, keepdims=True), 1e-9))
    return _PROFILES


def profile(energy, a, b):
    """A move's speed profile: frame-to-frame change follows how fast things move, resampled to POINTS steps."""
    e = np.asarray(energy[a + 1:b + 1], float)
    if len(e) < 4 or e.max() <= 0:
        return None
    x = np.interp(np.linspace(0, len(e) - 1, POINTS), np.arange(len(e)), e)
    return x / x.max()


def ease_fit(prof):
    params, curves = bezier_profiles()
    k = int(np.argmin(((curves - prof) ** 2).sum(axis=1)))
    return [float(v) for v in params[k]]


def follows_speed(energy, energy2, a, b):
    """Whether picture change still follows speed at this move's fastest frames. While a thing moves less than its own
    size in a frame, the change over two frames is the two single-frame changes added up (ratio 1). Once it moves
    further, old and new places no longer overlap, every frame changes the same pixels' worth, and the ratio falls to
    0.5: the profile flattens and the easing fit comes out nearly linear and short (a 24 px box gave 0.3 s and
    [0.3, 0.4, 0.5, 0.8] for a 0.5 s ease-out that a 200 px box read as [0.3, 0.9, 0.6, 1.0])."""
    steps = range(a + 1, min(b, len(energy) - 1))
    top = max(energy[a + 1:b + 1], default=0.0)
    ratios = [energy2[i + 1] / (energy[i] + energy[i + 1]) for i in steps if energy[i] + energy[i + 1] > 0 and max(energy[i], energy[i + 1]) >= 0.8 * top]
    return not ratios or float(np.median(ratios)) >= LINEAR

FPS_CAP = 60.0
LABEL_OFFSET = 0.0  # a windowed measurement stamps its sheets on the whole video's clock


def shift_times(r, dt):
    """Put a windowed measurement back on the whole video's clock."""
    r["cuts"] = [round(t + dt, 3) for t in r["cuts"]]
    r["events"] = [round(t + dt, 3) for t in r["events"]]
    for group in ("segments", "holds"):
        for x in r[group]:
            x["t0"], x["t1"] = round(x["t0"] + dt, 3), round(x["t1"] + dt, 3)
    for x in r["moves"]:
        x["t0"] = round(x["t0"] + dt, 3)
    if r.get("sound"):
        r["sound"]["onsets"] = [round(t + dt, 3) for t in r["sound"]["onsets"]]


def measure(path, out, keys=None):
    """keys: the keyframe times on this file's clock, when they are not its own (a window cut from a longer file)."""
    info = probe(path)
    fps = min(info["fps"], FPS_CAP)
    times = clock(path)
    energy, energy2, prev, prev2, lit = [], [], None, None, []
    for rgb in frames(path, fps, info["duration"]):
        lit.append(lit_middle(rgb))
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        energy.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        energy2.append(0.0 if prev2 is None else float(np.abs(g - prev2).mean()))  # change over two frames, for follows_speed
        prev2, prev = prev, g
    energy, energy2 = np.array(energy), np.array(energy2)
    quiet_keyframes(energy, keyframe_times(path) if keys is None else keys, float(times[0]) if len(times) else 0.0, fps)
    cut_frames = find_cuts(energy)
    segs = segments(energy, fps)
    events = []
    for e in sorted(set(cut_frames) | {s[1] for k, s in enumerate(segs) if s[0] == "move" and k > 0 and segs[k - 1][0] == "hold"}):
        if events and e - events[-1] <= 2:
            if e in cut_frames:  # a cut is where the eye lands, so it wins over a move that starts a frame before it
                events[-1] = e
            continue
        events.append(e)
    holds = []
    for kind, a, b in segs:
        if kind == "hold":
            mid = (a + b) // 2
            sharp = grab(path, mid / fps, times)
            holds.append({"t0": round(a / fps, 3), "t1": round(b / fps, 3), "drift": round(float(np.median(energy[a:b])), 3), **look(sharp if sharp is not None else analysed_frame(path, fps, mid))})
    sound = audio(path, info["duration"]) if info["audio"] else None
    event_t = [round(e / fps, 3) for e in events]
    rate, chance = sync_rate(event_t, sound["onsets"], info["duration"]) if sound else (None, None)
    hold_len = [h["t1"] - h["t0"] for h in holds]
    reading = [x for x in hold_len if x >= READ]
    move_len = [(b - a) / fps for kind, a, b in segs if kind == "move"]
    moves = []  # each short move's speed profile and the cubic-bezier easing it fits; long ones are several motions
    for kind, a, b in segs:
        if kind == "move" and 0.15 <= (b - a) / fps <= MOVE_FIT:
            prof = profile(energy, a, b)
            if prof is not None:
                moves.append({"t0": round(a / fps, 3), "dur": round((b - a) / fps, 3), "peak": round(int(np.argmax(prof)) / (POINTS - 1), 2),
                              "ease": ease_fit(prof), "profile": [round(float(x), 2) for x in prof], "ease_reliable": follows_speed(energy, energy2, a, b)})
    readable = [m for m in moves if m["ease_reliable"]]
    weights = np.array(hold_len) if holds else None
    wmed = lambda key: round(float(np.median(np.repeat([h[key] for h in holds], np.maximum(1, (weights * 10).astype(int))))), 3) if holds else None
    summary = {
        "events_per_10s": round(10 * len(events) / info["duration"], 2),
        "median_hold_s": round(float(np.median(reading)), 2) if reading else None,
        "median_move_s": round(float(np.median(move_len)), 2) if move_len else None,
        "drift": wmed("drift"),
        "move_share": round(float(np.mean(energy > MOVE)), 2),
        "occupancy": wmed("occupancy"), "detail": wmed("detail"), "largest_band": wmed("largest_band"),
        "sync_rate": rate, "sync_chance": chance,
        "tempo_bpm": sound["tempo"]["bpm"] if sound and sound["tempo"] else None,
        "move_peak": round(float(np.median([m["peak"] for m in readable])), 2) if readable else None,  # only moves whose easing could be read
    }
    how = space.read(path)   # how it moves, as a scene or as a page: a second pass over the film, a few seconds
    summary.update({"scene_move": how["scene_move"], "sheet_move": how["sheet_move"], "dark_corners": round(float(np.mean(lit)), 2) if lit else None})
    out.mkdir(parents=True, exist_ok=True)
    after = []
    for e in events:
        nxt = next((h for h in holds if h["t0"] >= e / fps - 1e-6), None)
        later = next((x for x in events if x > e), None)
        # the still must show what this event brought, so it can't land past the next event
        if nxt and nxt["t0"] - e / fps < 1.0 and (later is None or nxt["t0"] < later / fps):
            after.append(round((nxt["t0"] + nxt["t1"]) / 2, 3))
        elif later is not None:
            after.append(round((e + later) / 2 / fps, 3))
        else:
            after.append(round(min(info["duration"] - 0.05, e / fps + 0.3), 3))
    result = {"version": VERSION, "video": str(path), **info, "analysed_fps": fps, "summary": summary, "cuts": [round(c / fps, 3) for c in cut_frames],
              "events": event_t, "segments": [{"kind": k, "t0": round(a / fps, 3), "t1": round(b / fps, 3)} for k, a, b in segs],
              "holds": holds, "moves": moves, "sound": sound, "energy": [round(float(x), 2) for x in energy], "energy_t0": 0.0}
    result["sheets"] = sheet(path, [0.05] + after if not events or events[0] > 0 else after, out, fps, times)
    (out / "measure.json").write_text(json.dumps(result), encoding="utf-8")
    return result


def show(r):
    s = r["summary"]
    print(f"{Path(r['video']).name}: {r['duration']:.1f} s at {r['fps']:.0f} fps, {len(r['events'])} events ({s['events_per_10s']} per 10 s), "
          f"{len(r['cuts'])} cuts, {len(r['holds'])} holds (median {s['median_hold_s']} s), moves median {s['median_move_s']} s, moving {s['move_share']:.0%} of the time")
    print(f"  look over holds: occupancy {s['occupancy']}, detail {s['detail']}, biggest element {s['largest_band']} of frame height, drift while holding {s['drift']}")
    if s.get("scene_move") is not None:
        print(f"  how it moves: most of the picture moves in more than one way for {s['scene_move']:.0%} of it (a scene), and the whole picture slides or zooms as one flat sheet for {s['sheet_move']:.0%} (a page)")
    if s.get("dark_corners") is not None:
        print(f"  where its light is: the middle is lit and all four corners are darker in {s['dark_corners']:.0%} of its frames")
    if r["moves"]:
        unread = sum(not m.get("ease_reliable", True) for m in r["moves"])
        print(f"  moves: {len(r['moves'])} fitted; speed peaks at {s['move_peak']} of a move (0 start, 1 end); easing of each in measure.json"
              + (f"; {unread} can't be read from picture change (a thing moved further in a frame than its own size, or across fine texture): their easing and length aren't measurements" if unread else ""))
    if r["sound"]:
        t = r["sound"]["tempo"]
        print(f"  sound: {len(r['sound']['onsets'])} onsets, tempo {t['bpm'] if t else 'none'}{' (strength ' + str(t['strength']) + ')' if t else ''}; "
              f"events on an onset {s['sync_rate']} against {s['sync_chance']} by chance")
    else:
        print("  sound: none")
    print("  events (s): " + " ".join(f"{t:.2f}" for t in r["events"]))
    print(f"  sheets: {', '.join(r['sheets'])}")


REBUILD = {"occupancy": 0.05, "largest_band": 0.15, "detail": 1.5}  # per hold: absolute, relative, ratio
EXTRA = 0.15  # a rebuild may add this share of the source's events before it reads as stepping where the source flows
PACE = {"events_per_10s": ("ratio", 1.25), "median_hold_s": ("ratio", 1.33), "median_move_s": ("ratio", 1.5), "move_share": ("abs", 0.10)}
TOLERANCE = {  # refill: (kind, bound); a ratio bound holds either way round, an absolute one is a difference
    "events_per_10s": ("ratio", 1.25), "median_hold_s": ("ratio", 1.33), "move_share": ("abs", 0.10),
    "drift": ("floor", 0.08), "occupancy": ("abs", 0.10), "detail": ("ratio", 1.5), "largest_band": ("ratio", 1.25),
    "move_peak": ("abs", 0.15),
    "scene_move": ("reach", space.SCENE),  # a film whose source moves as a scene has to, at least half as much of the time
}
EASE_OFF = 0.25  # share of matched moves allowed to accelerate differently from the source


def ease_rows(a, b):
    """Each source move against the other's move that overlaps it most: the same speed profile, peak and length. Moves
    pair by overlap, not by start, because a slow-starting ease crosses the motion threshold later than a fast one.
    A pair where either move's easing couldn't be read (ease_reliable false) is left out, and listed second."""
    out, skipped = [], []
    overlap = lambda m, o: max(0.0, min(m["t0"] + m["dur"], o["t0"] + o["dur"]) - max(m["t0"], o["t0"])) / (max(m["t0"] + m["dur"], o["t0"] + o["dur"]) - min(m["t0"], o["t0"]))
    for m in a.get("moves", []):
        o = max(b.get("moves", []), key=lambda x: overlap(m, x), default=None)
        if not o or overlap(m, o) < 0.3:
            continue
        if not m.get("ease_reliable", True) or not o.get("ease_reliable", True):
            skipped.append(m["t0"])
            continue
        corr = float(np.corrcoef(m["profile"], o["profile"])[0, 1]) if np.std(o["profile"]) > 0 and np.std(m["profile"]) > 0 else 0.0
        length = max(m["dur"] / o["dur"], o["dur"] / m["dur"])
        ok = corr >= 0.6 and abs(m["peak"] - o["peak"]) <= 0.25 and length <= 1.5
        out.append({"t": m["t0"], "ok": ok, "corr": round(corr, 2), "source": {"ease": m["ease"], "dur": m["dur"]}, "other": {"ease": o["ease"], "dur": o["dur"]}})
    return out, skipped


def match_events(src, other, tol):
    """Events paired one to one, in as many pairs as can be made. Two earlier rules were wrong. Nearest-within-tolerance
    let one rebuild event stand for two source events a few frames apart (a cut, then a move start), so a merged pair
    passed. Closest-pair-first then took the best single pair and could strand a neighbour: source 1.00 and 1.12 against
    a rebuild at 0.92 and 1.04 pairs both ways within 0.08, and it reported one missing. Both lists run in time, so
    walking them together and pairing the earliest two that fit makes the most pairs there are."""
    a, b = sorted(src), sorted(other)
    i = j = 0
    matched, missing, extra = [], [], []
    while i < len(a) and j < len(b):
        if abs(a[i] - b[j]) <= tol:
            matched.append((a[i], b[j]))
            i, j = i + 1, j + 1
        elif a[i] < b[j]:
            missing.append(a[i])
            i += 1
        else:
            extra.append(b[j])
            j += 1
    return matched, missing + a[i:], extra + b[j:]


BEAT = ("largest_band", "occupancy", "detail", "drift")


def judge(kind, bound, x, y):
    if kind == "abs":
        return abs(x - y) <= bound
    if kind == "floor":  # a still picture where the source drifts (or the reverse) is off; small values both ways are fine
        return (x > bound) == (y > bound) or abs(x - y) <= bound
    if kind == "reach":  # one way only: a film may do more of this than its source, and a source that does none asks for none
        return x <= bound or (y > bound and y >= x / 2)
    return x == y or (min(x, y) > 0 and max(x / y, y / x) <= bound)


def beat_looks(m, beats):
    """Each beat's look from the holds inside it: its biggest element, and occupancy, detail and drift by hold time."""
    out = {}
    for bt in beats:
        hs = [(min(h["t1"], bt["t1"]) - max(h["t0"], bt["t0"]), h) for h in m["holds"] if min(h["t1"], bt["t1"]) > max(h["t0"], bt["t0"])]
        if not hs:
            out[bt["id"]] = None
            continue
        w = sum(x for x, _ in hs)
        out[bt["id"]] = {"largest_band": max(h["largest_band"] for _, h in hs), **{k: sum(x * h[k] for x, h in hs) / w for k in ("occupancy", "detail", "drift")}}
    return out


def still_spots(a, b, fps, least=0.2):
    """Spans where one picture moves and the other is dead still."""
    n = min(len(a), len(b))
    k = max(1, round(0.1 * fps))
    sa = np.convolve(a[:n], np.ones(k) / k, mode="same")
    sb = np.convolve(b[:n], np.ones(k) / k, mode="same")
    bad = (sa > 0.15) & (sb < STILL)
    spans, start = [], None
    for i, x in enumerate(list(bad) + [False]):
        if x and start is None:
            start = i
        elif not x and start is not None:
            if (i - start) / fps >= least:
                spans.append((round(start / fps, 2), round(i / fps, 2)))
            start = None
    return spans


def compare(a_dir, b_dir, mode, beats=None):
    a = json.loads((Path(a_dir) / "measure.json").read_text(encoding="utf-8"))
    b = json.loads((Path(b_dir) / "measure.json").read_text(encoding="utf-8"))
    if a.get("version") != b.get("version") or a.get("version") != VERSION:
        raise SystemExit(f"measured with different versions of measure.py ({a.get('version')} and {b.get('version')}, now {VERSION}): measure both again")
    rest = sum(h["t1"] - h["t0"] for h in a["holds"]) / max(a["duration"], 1e-6)
    if rest < 0.1:
        print(f"note: the source rests only {rest:.0%} of the time, so its look rows come from a frame or two and say little; read the frames instead")
    if abs(a["analysed_fps"] - b["analysed_fps"]) > 0.5:
        print(f"warning: analysed at {a['analysed_fps']:.0f} and {b['analysed_fps']:.0f} fps, which shifts the still and move rows; measure both with --fps {min(a['analysed_fps'], b['analysed_fps']):.0f}")
    rows = []
    if mode == "rebuild":
        frame = 1 / a["analysed_fps"]
        tol = 2 * frame + 1e-6
        matched, missing, extra = match_events(a["events"], b["events"], tol)
        rows.append({"metric": "events within 2 frames", "source": len(a["events"]), "other": len(matched), "ok": not missing, "detail": {"missing": missing}})
        # an extra start or stop is motion that steps where the source flows; every source event can land and the
        # film still read as jerky (one rebuild matched 14 of 14 events with 9.7 events per 10 s against 3.7)
        allowed = max(2, round(EXTRA * len(a["events"])))
        rows.append({"metric": "extra starts and stops", "source": 0, "other": len(extra), "ok": len(extra) <= allowed, "detail": {"extra": extra, "allowed": allowed}})
        # a windowed measurement's energy starts at its window, not at 0: line the two up on the whole clock first
        start = max(a.get("energy_t0", 0.0), b.get("energy_t0", 0.0))
        ea = np.array(a["energy"])[max(0, round((start - a.get("energy_t0", 0.0)) * a["analysed_fps"])):]
        eb = np.array(b["energy"])[max(0, round((start - b.get("energy_t0", 0.0)) * b["analysed_fps"])):]
        dead = [(round(x + start, 2), round(y + start, 2)) for x, y in still_spots(ea, eb, a["analysed_fps"])]
        rows.append({"metric": "still where the source moves", "source": "moving", "other": dead or "none", "ok": not dead})
        shapes, unread = ease_rows(a, b)
        if unread:
            print(f"note: {len(unread)} moves left out of the easing row (at {', '.join(f'{t:.2f}' for t in unread[:8])} s): in one film or the other a thing moved further in a frame than its own size, "
                  "or across fine texture, so picture change stopped following its speed and the easing there isn't a measurement")
        if shapes:
            differ = [x for x in shapes if not x["ok"]]
            rows.append({"metric": "moves that ease like the source", "source": len(shapes), "other": len(shapes) - len(differ),
                         "ok": len(differ) <= EASE_OFF * len(shapes), "detail": {"differ": differ[:8]}})
        for key, (kind, bound) in PACE.items():
            x, y = a["summary"][key], b["summary"][key]
            if x is not None and y is not None:
                rows.append({"metric": key, "source": x, "other": y, "ok": bool(judge(kind, bound, x, y))})
        for h in a["holds"]:
            mid = (h["t0"] + h["t1"]) / 2
            o = next((x for x in b["holds"] if x["t0"] <= mid <= x["t1"]), None)
            if not o:
                rows.append({"metric": f"hold at {mid:.2f}s", "source": "hold", "other": "moving", "ok": False})
                continue
            bad = []
            if abs(o["occupancy"] - h["occupancy"]) > REBUILD["occupancy"]:
                bad.append("occupancy")
            if h["largest_band"] > 0 and abs(o["largest_band"] - h["largest_band"]) > REBUILD["largest_band"] * h["largest_band"]:
                bad.append("largest_band")
            if min(o["detail"], h["detail"]) > 0 and max(o["detail"] / h["detail"], h["detail"] / o["detail"]) > REBUILD["detail"]:
                bad.append("detail")
            if bad:
                rows.append({"metric": f"hold at {mid:.2f}s", "source": {k: h[k] for k in bad}, "other": {k: o[k] for k in bad}, "ok": False})
    else:
        for key, (kind, bound) in TOLERANCE.items():
            x, y = a["summary"].get(key), b["summary"].get(key)
            if key == "scene_move" and (x is None or y is None):  # too few corners to follow in one of them: not read, so no row
                continue
            if x is None or y is None:
                rows.append({"metric": key, "source": x, "other": y, "ok": x is None and y is None})
                continue
            rows.append({"metric": key, "source": x, "other": y, "ok": bool(judge(kind, bound, x, y))})
        if beats:
            la, lb = beat_looks(a, beats[0]), beat_looks(b, beats[1])
            for bid in [bt["id"] for bt in beats[0]]:
                x, y = la.get(bid), lb.get(bid)
                if not any(bt["id"] == bid for bt in beats[1]):
                    rows.append({"metric": f"beat {bid}", "source": "rests" if x else "keeps moving", "other": "has no such beat", "ok": False})
                    continue
                if x is None or y is None:
                    long_enough = all(next((bt["t1"] - bt["t0"] for bt in side if bt["id"] == bid), MIN_HOLD) >= MIN_HOLD for side in beats)  # too short a beat can't rest in either film
                    if (x is None) != (y is None) and long_enough:
                        rows.append({"metric": f"beat {bid}", "source": "rests" if x else "keeps moving", "other": "rests" if y else "keeps moving", "ok": False})
                    continue
                bad = [k for k in BEAT if not judge(*TOLERANCE[k], x[k], y[k])]
                rows.append({"metric": f"beat {bid}", "source": {k: round(x[k], 3) for k in bad} or "ok", "other": {k: round(y[k], 3) for k in bad} or "ok", "ok": not bad})
        sa, sb = a["summary"], b["summary"]
        if sa["sync_rate"] is not None and sa["sync_rate"] > sa["sync_chance"] + 0.1:
            ok = sb["sync_rate"] is not None and sb["sync_rate"] >= sa["sync_rate"] - 0.1
            rows.append({"metric": "events on the beat (source syncs above chance)", "source": sa["sync_rate"], "other": sb["sync_rate"], "ok": bool(ok)})
    return rows


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        ap = argparse.ArgumentParser(prog="measure.py compare")
        ap.add_argument("source")
        ap.add_argument("other")
        ap.add_argument("--as", dest="mode", choices=["rebuild", "refill"], required=True)
        ap.add_argument("--beats", nargs=2, metavar=("SOURCE_BEATS", "OTHER_BEATS"), help="refill: each a JSON list of {id, t0, t1}, so beats compare one to one")
        ap.add_argument("--out")
        args = ap.parse_args(sys.argv[2:])
        beats = [json.loads(Path(f).read_text(encoding="utf-8")) for f in args.beats] if args.beats else None
        if beats:
            src = json.loads((Path(args.source) / "measure.json").read_text(encoding="utf-8"))
            # a windowed source's times run on the whole file's clock, so its beat map may end at the window or the film
            ends = [src["duration"]] + ([src["window"][1], src["film_seconds"]] if src.get("window") else [])
            src_len = src.get("film_seconds", src["duration"])
            if all(abs(beats[0][-1]["t1"] - e) > max(1.0, 0.1 * e) for e in ends):
                raise SystemExit(f"the first --beats file ends at {beats[0][-1]['t1']:.1f} s but the source runs {src_len:.1f} s: it must be the source's own beat map, or the rows mean nothing")
        rows = compare(args.source, args.other, args.mode, beats)
        for r in rows:
            print(f"  {'ok ' if r['ok'] else 'OFF'} {r['metric']}: source {r['source']}, other {r['other']}" + (f"  {r['detail']}" if r.get("detail") and not r["ok"] else ""))
        off = sum(not r["ok"] for r in rows)
        print(f"{off} of {len(rows)} off")
        if args.out:
            Path(args.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
        sys.exit(1 if off else 0)
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="a folder; it will hold measure.json and the beat sheets")
    ap.add_argument("--from", dest="start", type=float, help="measure only this window, in seconds; times in the result stay on the whole video's clock")
    ap.add_argument("--to", dest="end", type=float)
    ap.add_argument("--fps", type=float, help="analyse at no more than this rate; measure a source and its rebuild at the same rate so their rows mean the same")
    args = ap.parse_args()
    global FPS_CAP, LABEL_OFFSET
    if args.fps is not None and args.fps <= 0:
        raise SystemExit(f"--fps {args.fps:g}: the rate to analyse at is a number of frames a second above 0")
    FPS_CAP = args.fps or FPS_CAP
    video = Path(args.video)
    if args.start is None and args.end is None:
        return show(measure(video, Path(args.out)))
    whole = probe(video)
    check_window(args.start, args.end, whole["duration"], video)
    times = clock(video)
    at, first = seek_to(times, args.start or 0.0)
    offset = float(times[first])  # the window starts on a frame, and its times are shifted by that frame's own time
    end = min(args.end if args.end is not None else whole["duration"], whole["duration"])
    asked = end - at  # the window's length, which its pictures have to fill
    stop, last = seek_to(times, end)
    # the window runs up to the frame nearest --to and leaves that frame out, as it always did on a whole-frame time
    until = ["-t", f"{stop - at:.6f}"] if args.end is not None and end <= times[-1] and last > first else []
    end = float(times[last]) if until else whole["duration"]
    LABEL_OFFSET = offset
    # the window is cut to a copy that lives only as long as this run; the old copy stayed in the temp folder for good
    with tempfile.TemporaryDirectory() as tmp:
        # the copy starts at zero and runs for the window's length. With the source's own timestamps kept in it (-copyts),
        # ffmpeg 5.1 reported its length as the time its last frame had in the source, and every rate was wrong
        cut = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.6f}", *until, "-i", str(video), "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-c:a", "aac", str(Path(tmp) / "window.mp4")]
        subprocess.run(cut, check=True, creationflags=NO_WINDOW)
        # the pictures, counted: a cut's own length runs as long as its sound, which can outlast pictures that stopped early
        counted = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(Path(tmp) / "window.mp4")],
                                 capture_output=True, text=True, creationflags=NO_WINDOW).stdout.strip().strip(",")
        got = int(counted) / whole["fps"] if counted.isdigit() else 0.0
        wanted = (stop - at) if until else asked
        if got < wanted - 0.5:  # ffmpeg can end a cut early, exit 0, and leave a short copy: the same half second check_decode allows
            raise SystemExit(f"the window cut from {video} has {got:.2f} s of pictures for the {wanted:.2f} s asked for: the file ends early or is damaged. Nothing was written. "
                             "If the file plays, make a clean copy first: ffmpeg -i IN -c:v libx264 -crf 12 -c:a aac OUT.mp4")
        # the copy has keyframes of its own; the source's pulses are in its pictures, at the source's keyframes
        window_keys = [k - at for k in keyframe_times(video) if at <= k < end] + keyframe_times(Path(tmp) / "window.mp4")
        result = measure(Path(tmp) / "window.mp4", Path(args.out), keys=sorted(window_keys))
    shift_times(result, offset)
    # the record describes the file measured and the stretch of it, not the temporary copy
    result.update({"video": str(video), "window": [round(offset, 3), round(end, 3)], "window_seconds": result["duration"], "film_seconds": whole["duration"], "energy_t0": round(offset, 6)})
    (Path(args.out) / "measure.json").write_text(json.dumps(result), encoding="utf-8")
    show(result)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
