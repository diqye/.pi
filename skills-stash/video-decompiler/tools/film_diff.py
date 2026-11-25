#!/usr/bin/env python3
"""Compare a rebuild with its original frame by frame and say what to fix next. The rebuild starts at its own frame 0.

  python film_diff.py ORIGINAL REBUILD --from 6 --to 12 --out DIR [--spec FILE] [--round N]

Prints the score, the cuts missed and added, what arrives early or late, and the worst moments, each with a sheet of
original, rebuild and difference. Each run appends to DIR/history.jsonl. A rebuild that ends more than one frame before
the target is reported as short, one that runs more than one frame past it as long, and either way the run exits 1.

Other tools import the shared pieces from here: the SSIM, the ffprobe reader and the frame-exact seek.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
W, H = 480, 270
COLS, ROWS = 16, 9
# 1 summed in float32, which lost the small differences variance is made of and read up to 0.04 high (two flat frames
# a level apart scored 1.04). 2 sums in float64. Scores of the two versions can't be compared.
SSIM_VERSION = 2


def rate(text):
    """A frame rate from ffprobe's "num/den". "0/0" means no rate is known: that is 0.0, not a crash."""
    try:
        return float(Fraction(str(text)))
    except (ValueError, ZeroDivisionError):
        return 0.0


def shown_size(stream):
    """A video stream's width and height as it is shown. A phone often stores a portrait clip as a landscape frame with a
    rotation, in the display matrix or in the older rotate tag, and ffmpeg turns it upright as it decodes."""
    turn = next((d["rotation"] for d in stream.get("side_data_list", []) if "rotation" in d), None)
    turn = stream.get("tags", {}).get("rotate", 0) if turn is None else turn
    w, h = int(stream["width"]), int(stream["height"])
    return (h, w) if round(float(turn)) % 180 == 90 else (w, h)


def ffprobe(path):
    """The first video stream's fields as ffprobe gives them, uninterpreted, so each tool keeps choosing its own rate.
    The size is the one shown, after any rotation, which is the size ffmpeg decodes it at. A path that isn't there, and a
    picture with a video's name, are refused in words, not with a KeyError."""
    if not Path(path).exists():
        raise SystemExit(f"no such file: {path}")
    done = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,avg_frame_rate,r_frame_rate:stream_side_data=rotation:stream_tags=rotate",
                           "-show_entries", "format=duration,start_time,format_name", "-of", "json", str(path)], capture_output=True, text=True, creationflags=NO_WINDOW)
    info = json.loads(done.stdout or "{}")
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise SystemExit(f"{path}: no video stream that ffprobe can read")
    fmt = info.get("format", {})
    if re.search(r"_pipe|image2", fmt.get("format_name", "")):  # what the file is (png_pipe, jpeg_pipe, image2), not its name
        raise SystemExit(f"{path} is a still image, not a video")
    start = float(fmt.get("start_time") or 0.0)
    duration = float(fmt["duration"]) if "duration" in fmt else last_packet_end(path, start, rate(video.get("avg_frame_rate", "0/0")) or rate(video.get("r_frame_rate", "0/0")))
    if duration is None:
        raise SystemExit(f"{path}: ffprobe finds neither a length nor a frame rate in it, so it can't be read as a video")
    w, h = shown_size(video)
    return {"w": w, "h": h, "avg_frame_rate": video.get("avg_frame_rate", "0/0"), "r_frame_rate": video.get("r_frame_rate", "0/0"),
            "duration": duration, "start_time": start, "audio": any(s.get("codec_type") == "audio" for s in streams)}


def last_packet_end(path, start=0.0, fps=0.0):
    """A video's length from its packets, for a file written as a stream (a browser's screen recording in webm), whose
    header holds no duration: where its last frame ends, from the file's start. When no frame carries a time (a raw
    stream), the frames counted at the stream's rate; None when there's no rate either. A read of the packets that failed
    or reported an error stops the tool: the frames that survived a cut-off file are not its length."""
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,duration_time", "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True, creationflags=NO_WINDOW)
    said = done.stderr.strip()
    if done.returncode or said:
        raise SystemExit(f"{path} gives no length in its header, and reading its frames for one failed: {said[-300:] or f'exit {done.returncode}'}. "
                         "If the file plays, make a clean copy first: ffmpeg -i IN -c:v libx264 -crf 12 -c:a aac OUT.mp4")
    timed, packets = [], 0
    for line in done.stdout.split():
        packets += 1
        t, _, d = line.strip(",").partition(",")
        try:
            timed.append((float(t), float(d) if d not in ("", "N/A") else None))
        except ValueError:  # a packet with no time
            continue
    if not timed:
        return packets / fps if packets and fps else None
    timed.sort()
    last, lasts = timed[-1]
    if lasts is None:  # the last frame still shows for one frame's interval: from the rate, or from the gap before it
        lasts = 1 / fps if fps else (last - timed[-2][0] if len(timed) > 1 else 0.0)
    return last + lasts - start


def fps_of(raw, field="avg_frame_rate"):
    """The rate a tool asked for, or the other one when ffprobe gives that as 0/0; a file with neither is refused."""
    other = "r_frame_rate" if field == "avg_frame_rate" else "avg_frame_rate"
    fps = rate(raw[field]) or rate(raw[other])
    if not fps:
        raise SystemExit("ffprobe gives this file no frame rate (0/0), so frame numbers can't be turned into times. Make it constant first: ffmpeg -i IN -fps_mode cfr -r 30 OUT.mp4")
    return fps


def check_window(start, end, duration, path):
    """Stop on a --from/--to that isn't a stretch of the file: a window past its end was quietly moved to its end, or
    compared from its start."""
    start = 0.0 if start is None else start
    if not 0 <= start < duration:
        raise SystemExit(f"--from {start:g} is outside {path}, which is {duration:.2f} s long")
    if end is not None and end <= start:
        raise SystemExit(f"--to {end:g} isn't after --from {start:g}")
    if end is not None and end > duration + 0.001:
        raise SystemExit(f"--to {end:g} is past the end of {path}, which is {duration:.2f} s long")


def check_decode(path, code, said, seconds, expected):
    """Stop a tool whose ffmpeg failed, or reported an error and stopped short, so part of a file is never measured as
    all of it. An error with the whole length decoded is let through with a warning, as phone files often carry one."""
    said = (said.decode("utf-8", "replace") if isinstance(said, bytes) else said or "").strip()
    if code:
        raise SystemExit(f"ffmpeg couldn't read {path} (exit {code}): {said[-600:] or 'it said nothing'}. Nothing was written.")
    if said and expected and seconds < expected - 0.5:
        raise SystemExit(f"ffmpeg stopped reading {path} at {seconds:.2f} s of {expected:.2f} s: {said[-600:]}. Nothing was written. "
                         "If the file plays, make a clean copy first: ffmpeg -i IN -c:v libx264 -crf 12 -c:a aac OUT.mp4")
    if said:
        print(f"warning: ffmpeg reported a problem reading {path}, and read all of it: {said.splitlines()[0][:300]}", file=sys.stderr)


def stop_decoder(p, patience=5.0):
    """End an ffmpeg whose pipe the reader has just closed, and come back once it has let go of the film. ffmpeg stops by
    itself on a closed pipe, so it is waited for, and killed only if it doesn't stop. The `ffmpeg` on PATH can be a
    launcher that starts the real one (Chocolatey's and Scoop's are): killing that at once ended the launcher and left
    the real ffmpeg holding the film open, so the next step couldn't delete or replace it."""
    try:
        p.wait(timeout=patience)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()


def frame_times(path):
    """Every frame's time in seconds from the file's start, in display order, read from the packets without decoding.
    Times count from the file's start_time, as ffmpeg's -ss does, so they line up with every seek here."""
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)], capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        pts = sorted(float(x.strip(",")) for x in done.stdout.split() if x.strip(","))
    except ValueError:  # a packet without a time: there is no honest per-frame clock to give
        return None
    if not pts:
        return None
    return np.array(pts) - ffprobe(path)["start_time"]


def variable_rate(times):
    """Whether frames come at uneven intervals, by the rule timecheck.py uses: more than 10% (or 2 ms) off the median."""
    if times is None or len(times) < 3:
        return False
    gaps = np.diff(times)
    middle = float(np.median(gaps))
    return bool(np.any(np.abs(gaps - middle) > max(0.002, 0.1 * middle)))


def refuse_variable(path, times):
    """Tools that turn frame numbers into times need a constant rate: say so, and how to get one."""
    if variable_rate(times):
        gaps = np.diff(times)
        fastest = round(1 / max(float(gaps[gaps > 0].min()), 1e-6))
        raise SystemExit(f"{path} has a variable frame rate (frames {gaps.min() * 1000:.0f} to {gaps.max() * 1000:.0f} ms apart), so its frame numbers don't turn into times. "
                         f"Make it constant first: ffmpeg -i \"{path}\" -fps_mode cfr -r {fastest} constant.mp4")


def seek_to(times, t):
    """The -ss seconds that land on the frame nearest time t, and that frame's number. ffmpeg returns the first frame at
    or after the time given, and a frame's time printed to a few decimals (0.0167 for 1/60 s) can sit just after the
    frame itself, so a plain seek returned the next frame one time in three. Half way back to the frame before can't."""
    k = int(np.clip(np.searchsorted(times, t), 1, len(times) - 1)) if len(times) > 1 else 0
    f = k - 1 if k and abs(times[k - 1] - t) <= abs(times[k] - t) else k
    return (0.0 if f == 0 else float(times[f - 1] + times[f]) / 2), f


def clock(path, fps=None):
    """A file's frame times, or a regular clock at its rate when the packets carry no times."""
    times = frame_times(path)
    if times is None:
        raw = ffprobe(path)
        fps = fps or fps_of(raw)
        times = np.arange(int(raw["duration"] * fps) + 2) / fps
    return times


def probe(path):
    raw = ffprobe(path)
    return {"w": raw["w"], "h": raw["h"], "fps": fps_of(raw), "duration": raw["duration"]}


def stream(path, start, seconds, fps, times=None):
    """Frames from the frame nearest `start`, at `fps`, as float64 Y planes."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start:
        command += ["-ss", f"{seek_to(clock(path, fps) if times is None else times, start)[0]:.6f}"]
    command += ["-i", str(path)]
    if seconds:
        command += ["-t", f"{seconds:.4f}"]
    command += ["-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"]
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    size = W * H * 3 // 2
    try:
        while True:
            raw = p.stdout.read(size)
            if len(raw) < size:
                break
            yield np.frombuffer(raw[:W * H], dtype=np.uint8).reshape(H, W).astype(np.float64)
    finally:  # a caller that stops early (next(), break) closes the generator: end ffmpeg, or it keeps the file open.
        # The pipe is closed first and ffmpeg waited for: killed at once, a launcher (Chocolatey's ffmpeg on the hosted
        # Windows runners) died and left the real ffmpeg holding the film (a council's finding)
        p.stdout.close()
        stop_decoder(p)


def blur8(x):
    pad = np.pad(x, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    return (pad[8:, 8:] - pad[:-8, 8:] - pad[8:, :-8] + pad[:-8, :-8]) / 64.0


def ssim_map(a, b):
    """SSIM at every place, from 8x8 box means. Always in float64: the box sums run over the whole frame, and in float32
    they lose the small differences that variance and covariance are made of."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = blur8(a), blur8(b)
    va, vb = blur8(a * a) - ma * ma, blur8(b * b) - mb * mb
    cov = blur8(a * b) - ma * mb
    return ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))


def ssim(a, b):
    return float(ssim_map(a, b).mean())


def cells(x):
    h, w = H // ROWS, W // COLS
    return x[:h * ROWS, :w * COLS].reshape(ROWS, h, COLS, w).mean(axis=(1, 3))


def read_pair(original, rebuild, start, seconds, fps, times=None):
    scores, maes, la, lb, ea, eb, errors = [], [], [], [], [], [], []
    prev_a = prev_b = None
    missing = 0
    b_iter = stream(rebuild, 0, None, fps)  # all of it, so frames past the target's end are counted, not cut off
    a_iter = stream(original, start, seconds, fps, times)
    for a in a_iter:
        b = next(b_iter, None)
        if b is None:
            # the target's frames the rebuild never reached: counted, so a render that died early can't read as perfect
            missing = 1 + sum(1 for _ in a_iter)
            break
        scores.append(ssim(a, b))
        maes.append(float(np.abs(a - b).mean()))
        la.append(cells(a))
        lb.append(cells(b))
        errors.append(cells(np.abs(a - b)))
        ea.append(0.0 if prev_a is None else float(np.abs(a - prev_a).mean()))
        eb.append(0.0 if prev_b is None else float(np.abs(b - prev_b).mean()))
        prev_a, prev_b = a, b
    extra = sum(1 for _ in b_iter)
    return {"ssim": np.array(scores), "mae": np.array(maes), "la": np.array(la), "lb": np.array(lb), "ea": np.array(ea), "eb": np.array(eb), "errors": np.array(errors), "frames_past_end": extra, "frames_missing": missing}


def find_cuts(e):
    out = []
    for t in range(1, len(e)):
        around = np.concatenate([e[max(t - 15, 0):t], e[t + 1:t + 16]])
        if e[t] > max(12.0, 5 * float(np.median(around)) if len(around) else 12.0) and e[t] >= e[max(t - 1, 0)]:
            if out and t - out[-1] <= 3:
                if e[t] > e[out[-1]]:  # a fast move can cross the line a frame or two before the cut it runs into
                    out[-1] = t
            else:
                out.append(t)
    return out


def match_cuts(a, b, tolerance=1):
    missing = [x for x in a if not any(abs(x - y) <= tolerance for y in b)]
    extra = [y for y in b if not any(abs(x - y) <= tolerance for x in a)]
    late = [(x, min(b, key=lambda y: abs(x - y)) - x) for x in missing if b and abs(min(b, key=lambda y: abs(x - y)) - x) <= 60]
    return missing, extra, late


def events(series, threshold=4.0):
    d = np.zeros(len(series))
    d[1:-1] = np.abs(series[2:] - series[:-2]) / 2
    marks = [t for t in range(1, len(d) - 1) if d[t] > threshold and d[t] >= d[t - 1] and d[t] > d[t + 1]]
    merged = []
    for t in marks:
        if not merged or t - merged[-1] > 3:
            merged.append(t)
    return merged


def timing(la, lb, fps, window=30):
    """Matches each place's changes in the original with the rebuild's nearest change there, and groups the lags by half second."""
    rows = []
    for r in range(ROWS):
        for c in range(COLS):
            ours = events(lb[:, r, c])
            for t in events(la[:, r, c]):
                near = [o for o in ours if abs(o - t) <= window]
                rows.append((t, None if not near else min(near, key=lambda o: abs(o - t)) - t))
    buckets = {}
    size = int(fps / 2)
    for t, lag in rows:
        buckets.setdefault(t // size, []).append(lag)
    out = []
    for k in sorted(buckets):
        lags = buckets[k]
        found = [x for x in lags if x is not None]
        out.append({"t": round(k * size / fps, 2), "changes": len(lags), "no_match": len(lags) - len(found), "median_lag_frames": int(np.median(found)) if found else None})
    all_found = [abs(lag) for _, lag in rows if lag is not None]
    return out, {"changes": len(rows), "unmatched": sum(lag is None for _, lag in rows), "median_abs_lag": float(np.median(all_found)) if all_found else None}


def worst_frames(scores, k=4, spacing=20):
    order = np.argsort(scores)
    picks = []
    for t in order:
        if scores[t] < 0.999 and all(abs(int(t) - p) >= spacing for p in picks):
            picks.append(int(t))
        if len(picks) == k:
            break
    return picks


def colour_matrix(path):
    """raea's MP4s carry no colour tags though their data is BT.709, and ffmpeg reads an untagged file as BT.601."""
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_space", "-of", "csv=p=0", str(path)], capture_output=True, text=True, creationflags=NO_WINDOW)
    return "bt601" if done.stdout.strip() in ("smpte170m", "bt470bg") else "bt709"


def full_frame(path, seconds, w=960, h=540, times=None):
    at = seek_to(clock(path) if times is None else times, seconds)[0]
    done = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{at:.6f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:{h}:in_color_matrix={colour_matrix(path)}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, creationflags=NO_WINDOW)
    return Image.fromarray(np.frombuffer(done.stdout, dtype=np.uint8).reshape(h, w, 3))


def error_box(cell_errors):
    top = cell_errors.max()
    ys, xs = np.nonzero(cell_errors >= max(top * 0.5, 2.0))
    if not len(xs):
        return None
    return xs.min() / COLS, ys.min() / ROWS, (xs.max() + 1) / COLS, (ys.max() + 1) / ROWS


def sheet(original, rebuild, box):
    difference = ImageChops.difference(original, rebuild).convert("L").point(lambda v: min(255, v * 4)).convert("RGB")
    w, h = original.size
    out = Image.new("RGB", (w * 3 + 20, h + 26), (24, 24, 30))
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate((("original", original), ("rebuild", rebuild), ("difference x4", difference))):
        out.paste(im, (i * (w + 10), 26))
        d.text((i * (w + 10) + 6, 6), name, fill=(235, 235, 240))
        if box:
            d.rectangle((i * (w + 10) + box[0] * w, 26 + box[1] * h, i * (w + 10) + box[2] * w, 26 + box[3] * h), outline=(255, 70, 70))
    return out, difference


def ink(image, box, margin=0.03):
    """The drawn thing inside a box: its bounds in fractions of the frame, and its colour against the ground around it."""
    w, h = image.size
    x0, y0, x1, y1 = max(box[0] - margin, 0) * w, max(box[1] - margin, 0) * h, min(box[2] + margin, 1) * w, min(box[3] + margin, 1) * h
    crop = np.asarray(image.crop((int(x0), int(y0), int(x1), int(y1))), dtype=np.int16)
    edge = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    ground = np.median(edge, axis=0)
    mask = np.abs(crop - ground).max(axis=2) > 24
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    colour = np.median(crop[mask], axis=0).astype(int)
    return {"box": [(x0 + xs.min()) / w, (y0 + ys.min()) / h, (x0 + xs.max() + 1) / w, (y0 + ys.max() + 1) / h], "colour": "#%02x%02x%02x" % tuple(colour), "ground": "#%02x%02x%02x" % tuple(ground.astype(int))}


def compare_ink(original, rebuild, box, source_width, source_height):
    """Exact numbers for what geometry and colour to change, from the same region in both pictures."""
    a, b = ink(original, box), ink(rebuild, box)
    if a is None or b is None:
        return {"original_ink": a is not None, "rebuild_ink": b is not None}
    return {"move_rebuild_x": round((a["box"][0] - b["box"][0]) * source_width), "move_rebuild_y": round((a["box"][1] - b["box"][1]) * source_height),
            "scale_rebuild_w": round(float((a["box"][2] - a["box"][0]) / max(b["box"][2] - b["box"][0], 1e-6)), 3), "scale_rebuild_h": round(float((a["box"][3] - a["box"][1]) / max(b["box"][3] - b["box"][1], 1e-6)), 3),
            "colour": [a["colour"], b["colour"]], "ground": [a["ground"], b["ground"]]}


def run(original, rebuild, start, end, out, spec=None, round_no=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    info = probe(original)
    check_window(start, end, info["duration"], original)  # the window is the original's; the rebuild's length is checked against it below
    fps = info["fps"]
    seconds = (end - start) if end else info["duration"] - start
    reb = probe(rebuild)
    times_a, times_b = clock(original, fps), clock(rebuild, reb["fps"])
    data = read_pair(original, rebuild, start, seconds, fps, times_a)
    n = len(data["ssim"])
    cuts_a, cuts_b = find_cuts(data["ea"]), find_cuts(data["eb"])
    missing, added, near = match_cuts(cuts_a, cuts_b)
    lags, lag_summary = timing(data["la"], data["lb"], fps)
    picks = worst_frames(data["ssim"])
    moments = []
    first = seek_to(times_a, start)[1] if start else 0  # the frame the comparison started on, so each still is the frame scored
    for t in picks:
        seconds_in = t / fps
        a = full_frame(original, float(times_a[min(first + t, len(times_a) - 1)]), times=times_a)
        b = full_frame(rebuild, seconds_in, times=times_b)
        box = error_box(data["errors"][t])
        image, difference = sheet(a, b, box)
        name = f"worst-{t:05d}.jpg"
        image.save(out / name, quality=90)
        row = {"frame": t, "t_in_clip": round(seconds_in, 3), "ssim": round(float(data["ssim"][t]), 3), "box": None if box is None else [round(float(v), 3) for v in box], "sheet": str(out / name)}
        if box is not None:
            row["ink"] = compare_ink(a, b, box, info["w"], info["h"])
        moments.append(row)
    result = {"round": round_no, "frames": n, "fps": fps, "size_match": (info["w"], info["h"]) == (reb["w"], reb["h"]), "rebuild_seconds": round(reb["duration"], 3), "target_seconds": round(seconds, 3), "frames_past_end": data["frames_past_end"],
              "frames_missing": data["frames_missing"], "ssim_version": SSIM_VERSION,
              "ssim_mean": round(float(data["ssim"].mean()), 4), "ssim_p10": round(float(np.percentile(data["ssim"], 10)), 4), "mae_mean": round(float(data["mae"].mean()), 3),
              "cuts_original": cuts_a, "cuts_rebuild": cuts_b, "cuts_missing": missing, "cuts_added": added, "cuts_nearly": near, "timing": lag_summary, "timing_by_half_second": lags, "worst": moments, "spec_bytes": Path(spec).stat().st_size if spec else None}
    history = out / "history.jsonl"
    # rows scored by the float32 SSIM read higher than this one would on the same frames, so say when they are there
    older = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines() if line.strip()] if history.exists() else []
    result["history_older_rows"] = sum(1 for row in older if row.get("ssim_version") != SSIM_VERSION)
    (out / "diff.json").write_text(json.dumps(result, indent=0), encoding="utf-8")
    with open(history, "a", encoding="utf-8") as f:
        f.write(json.dumps({k: result[k] for k in ("round", "ssim_mean", "ssim_p10", "mae_mean", "spec_bytes", "ssim_version", "frames", "frames_missing", "rebuild_seconds", "target_seconds")}
                           | {"cuts_missing": len(missing), "cuts_added": len(added), "median_abs_lag": lag_summary["median_abs_lag"], "unmatched": lag_summary["unmatched"]}) + "\n")
    return result


def show(r):
    print(f"score: mean SSIM {r['ssim_mean']:.4f}, worst tenth {r['ssim_p10']:.4f}, mean error {r['mae_mean']:.2f}/255 over {r['frames']} frames" + (f", spec {r['spec_bytes']} bytes" if r["spec_bytes"] else ""))
    if not r["size_match"] or abs(r["rebuild_seconds"] - r["target_seconds"]) > 0.05:
        print(f"shape: size match {r['size_match']}; rebuild {r['rebuild_seconds']} s against target {r['target_seconds']} s")
    if r["frames_missing"] > 1:
        print(f"short: the rebuild ends {r['frames_missing']} frames ({r['frames_missing'] / r['fps']:.2f} s) before the target does, so the score covers only the {r['frames']} frames it has")
    if r["frames_past_end"] > 1:
        print(f"long: the rebuild runs {r['frames_past_end']} frames ({r['frames_past_end'] / r['fps']:.2f} s) past the target's end, so the score covers only the first {r['frames']} frames. Is the original the right file, and the window (--from, --to) the right one?")
    if r.get("history_older_rows"):
        print(f"note: history.jsonl holds {r['history_older_rows']} rows scored by an older SSIM (float32), which read up to 0.04 higher; compare scores only between rows with ssim_version {SSIM_VERSION}")
    print(f"cuts: original {r['cuts_original']}; missing {r['cuts_missing']}; added {r['cuts_added']}; nearest offsets {r['cuts_nearly']}")
    t = r["timing"]
    print(f"timing: {t['changes']} changes in the original, {t['unmatched']} with no match, median |lag| {t['median_abs_lag']} frames")
    for row in r["timing_by_half_second"]:
        if row["no_match"] or (row["median_lag_frames"] not in (None, 0)):
            print(f"  at {row['t']:>6.2f} s: {row['changes']} changes, {row['no_match']} unmatched, rebuild lag {row['median_lag_frames']} frames")
    for m in r["worst"]:
        print(f"worst: frame {m['frame']} ({m['t_in_clip']} s) SSIM {m['ssim']} box {m['box']} sheet {m['sheet']}" + (f"\n  ink: {m['ink']}" if m.get("ink") else ""))


if __name__ == "__main__":
    import utf8  # noqa: F401
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("rebuild")
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--to", dest="end", type=float, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec")
    ap.add_argument("--round", type=int)
    args = ap.parse_args()
    result = run(args.original, args.rebuild, args.start, args.end, args.out, args.spec, args.round)
    show(result)
    if result["frames_missing"] > 1 or result["frames_past_end"] > 1:
        sys.exit(1)
