#!/usr/bin/env python3
"""Measure possible picture faults in one film.

Usage: python timecheck.py FILM [--freeze-seconds 1.5] [--features FILE]

JSON goes to stdout. Times are seconds from the input timeline's start. Findings
are measurements for review, not proof of a fault. The scanner reads one reduced
frame at a time and stores only per-frame measurements. FFmpeg/FFprobe must be
on PATH; numpy and OpenCV must be installed. No reference film is needed.

A content deletion or reordering cannot generally be distinguished from an
intentional cut without a reference/expected edit. Ornament and dissolves are
not assessed. Colour/detail comparisons can miss changes on cuts or when the
surrounding content changes, and can report deliberate effects as candidates.

Tested on damage injected into films it hadn't been tuned on: freezes and stutters were found (2 of 2 each, about one
false alarm a minute), softness and colour jumps were not (0 of 2 each). So only the first two are relied on.
"""
import argparse
import json
import math
import re
import subprocess
import sys
import threading
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

cv2.setNumThreads(1)
_SHOW = re.compile(r"showinfo.*?\bn:\s*(\d+)\s+pts:\s*[-\d]+\s+pts_time:\s*([-+\deE.]+)")
_ANGLE = np.arange(180, dtype=np.float32) * (2 * np.pi / 180)
_COS = np.cos(_ANGLE)
_SIN = np.sin(_ANGLE)


def probe(path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import film_diff
    try:  # the one reader that says, in words, when a file isn't there or is a still picture
        film_diff.ffprobe(path)
    except SystemExit as e:
        raise ValueError(str(e)) from None
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height,r_frame_rate,avg_frame_rate,disposition:format=start_time',
                        '-of', 'json', path], capture_output=True, text=True, check=True)
    info = json.loads(p.stdout)
    if not info.get('streams'):
        raise ValueError('no video stream')
    s = info['streams'][0]
    w, h = int(s['width']), int(s['height'])
    if w < 16 or h < 16:
        raise ValueError('picture is too small for these measurements')
    try:
        rate = float(Fraction(s['avg_frame_rate']))
    except (ValueError, ZeroDivisionError, KeyError):
        rate = 0.0
    if not 0 < rate <= 240:
        raise ValueError('no usable average frame rate')
    scale = min(1.0, 640.0 / max(w, h))
    return w, h, max(2, int(round(w * scale / 2)) * 2), max(2, int(round(h * scale / 2)) * 2), rate


def scan(path):
    _, _, w, h, nominal_rate = probe(path)
    cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-v', 'info', '-xerror',
           '-threads', '2', '-noautorotate', '-i', path, '-map', '0:v:0',
           '-an', '-sn', '-dn', '-vf', f'scale={w}:{h}:flags=area,showinfo',
           '-fps_mode', 'passthrough', '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024 * 1024)
    timestamps, diagnostics = [], []
    def read_log():
        for line in iter(proc.stderr.readline, b''):
            text = line.decode('utf-8', errors='replace').strip()
            match = _SHOW.search(text)
            if match:
                timestamps.append((int(match.group(1)), float(match.group(2))))
            elif re.search(r'\b(error|corrupt|invalid|failed|missing picture|concealing)\b', text, re.I):
                diagnostics.append(text[:600])
    log = threading.Thread(target=read_log, daemon=True)
    log.start()
    diff, detail, corr, hue, coherence, saturation, changed = [], [], [], [], [], [], []
    prev_g = prev_hsv = None
    size = w * h * 3
    try:
        while True:
            raw = proc.stdout.read(size)
            if not raw:
                break
            if len(raw) != size:
                raise ValueError('truncated decoded frame')
            image = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
            grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            detail.append(float(cv2.Laplacian(grey, cv2.CV_32F).var()))
            small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
            g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            if prev_g is None:
                diff.append(0.0); corr.append(1.0); hue.append(0.0); coherence.append(0.0); saturation.append(0.0); changed.append(0.0)
            else:
                moved = cv2.absdiff(g, prev_g)
                diff.append(float(moved.mean()))
                changed.append(float((moved > 12).mean()))
                corr.append(float(cv2.matchTemplate(g, prev_g, cv2.TM_CCOEFF_NORMED)[0, 0]))
                dh = ((hsv[:, :, 0].astype(np.int16) - prev_hsv[:, :, 0].astype(np.int16)) % 180).astype(np.uint8)
                weight = np.minimum(hsv[:, :, 1], prev_hsv[:, :, 1]).astype(np.float32)
                weight *= np.minimum(hsv[:, :, 2], prev_hsv[:, :, 2]).astype(np.float32) / 255.0
                den = float(weight.sum())
                saturation.append(den / weight.size)
                if den:
                    x = float((_COS[dh] * weight).sum() / den)
                    y = float((_SIN[dh] * weight).sum() / den)
                    hue.append(math.degrees(math.atan2(y, x)))
                    coherence.append(math.hypot(x, y))
                else:
                    hue.append(0.0); coherence.append(0.0)
            prev_g, prev_hsv = g, hsv
    finally:
        proc.stdout.close()
        rc = proc.wait()
        log.join()
        proc.stderr.close()
    n = len(diff)
    if rc or diagnostics:
        raise ValueError(f'FFmpeg decode failed or reported errors (exit {rc}): ' + '; '.join(diagnostics[:4]))
    if n < 2 or len(timestamps) != n or any(i != x[0] for i, x in enumerate(timestamps)):
        raise ValueError(f'incomplete frame timestamps: decoded {n}, timed {len(timestamps)}')
    ts = np.array([x[1] for x in timestamps], dtype=float)
    if not np.isfinite(ts).all() or np.any(np.diff(ts) <= 0):
        raise ValueError('non-increasing or invalid picture timestamps')
    intervals = np.diff(ts)
    if np.max(intervals) > max(0.5, 4.0 / nominal_rate):
        raise ValueError('large timestamp gaps; cadence analysis is not reliable')
    median_interval = float(np.median(intervals))
    if np.any(np.abs(intervals - median_interval) > max(0.002, 0.1 * median_interval)):
        raise ValueError('variable picture frame intervals; cadence checks are not supported')
    # The last displayed duration is not provided by showinfo; estimate it from
    # the median decoded-frame interval rather than the container/audio length.
    frame_end = float(ts[-1] + np.median(intervals))
    return {'time': ts.tolist(), 'end': frame_end, 'fps': nominal_rate,
            'diff': diff, 'detail': detail, 'corr': corr, 'hue': hue,
            'coherence': coherence, 'saturation': saturation, 'changed': changed}


def groups(mask):
    starts = np.flatnonzero(mask & ~np.r_[False, mask[:-1]])
    ends = np.flatnonzero(mask & ~np.r_[mask[1:], False]) + 1
    return list(zip(starts.tolist(), ends.tolist()))


def _finding(kind, start, end, reason):
    return {'kind': kind, 'start': round(float(start), 3), 'end': round(float(end), 3), 'reason': reason}


def detect(data, freeze_seconds=1.5):
    t = np.array(data['time'], dtype=float)
    d = np.array(data['diff'], dtype=float)
    detail = np.array(data['detail'], dtype=float)
    corr = np.array(data['corr'], dtype=float)
    hue = np.array(data['hue'], dtype=float)
    coherence = np.array(data['coherence'], dtype=float)
    saturation = np.array(data['saturation'], dtype=float)
    n, fps = len(t), data['fps']
    ends = np.r_[t[1:], data['end']]
    findings = []
    # A thin line being drawn barely shifts the average, so a hold also needs no part of the picture to have changed.
    hold = (d <= 0.24) & (np.array(data.get('changed', [0.0] * len(d)), dtype=float) == 0)
    hold[0] = False
    runs = groups(hold)
    for a, b in runs:
        start = t[a - 1]
        end = ends[b - 1]
        if end - start >= freeze_seconds:
            findings.append(_finding('freeze', start, end, f'Picture is nearly identical for {end-start:.2f} s; a deliberate still also measures this way.'))

    # Candidate repeated-frame bursts must depart from the nearby cadence.
    # This compares run lengths, not a global "one frame must change" rule.
    short = [(a, b, b - a) for a, b in runs if 2 <= b-a and ends[b-1] - t[a-1] < freeze_seconds]
    used = set()
    for j, (a, b, length) in enumerate(short):
        if j in used:
            continue
        cluster = [(j, a, b, length)]
        for k in range(j+1, len(short)):
            aa, bb, ll = short[k]
            if t[aa] - t[cluster[-1][2]-1] > 0.45 or t[aa] - t[a] > 2.5:
                break
            cluster.append((k, aa, bb, ll))
        if len(cluster) < 4:
            continue
        start_i, end_i = cluster[0][1]-1, cluster[-1][2]
        left = (t >= t[start_i]-2.0) & (t < t[start_i]-0.15)
        right = (t > ends[end_i-1]+0.15) & (t <= ends[end_i-1]+2.0)
        surrounding = left | right
        if surrounding.sum() < max(6, fps * 0.4):
            continue
        neighbors = [b0-a0 for a0,b0 in runs if surrounding[min(a0,n-1)] and b0-a0 < fps]
        baseline = float(np.percentile(neighbors, 75)) if len(neighbors) >= 3 else 0.0
        typical = float(np.median([x[3] for x in cluster]))
        motion = float(np.percentile(d[surrounding], 70))
        if typical < max(4.0, baseline + 2.0) or motion < 0.45:
            continue
        if np.max(d[start_i+1:end_i]) < 0.7:
            continue
        findings.append(_finding('stutter', t[start_i], ends[end_i-1],
                                  f'Repeated holds of about {typical+1:.0f} frames exceed nearby cadence (75th percentile {baseline+1:.0f} frames).'))
        used.update(x[0] for x in cluster)

    # A sharply reduced, sustained high-frequency measure without a picture
    # cut. The end is where detail returns, a shot transition begins, or the
    # measured film ends; this is an estimate, not a source-aligned boundary.
    window = max(3, round(fps * 0.25))
    last_soft_end = -1
    for i in range(max(2, window), n-window):
        if i < last_soft_end:
            continue
        if d[i] >= 5.0 or corr[i] < 0.97 or detail[i-1] < 40.0:
            continue
        if detail[i] / max(detail[i-1], 1e-9) >= 0.28:
            continue
        before = float(np.median(detail[i-window:i]))
        after = float(np.median(detail[i:i+window]))
        if before < 40.0 or after / before >= 0.40:
            continue
        j = i + window
        while j < n:
            if t[j]-t[i] > 15.0:
                break
            if d[j] >= 8.0 or corr[j] < 0.92:
                break
            if j+window <= n and float(np.median(detail[j:j+window])) >= 0.65*before:
                break
            j += 1
        end = t[j] if j < n else data['end']
        if end-t[i] >= 0.5:
            findings.append(_finding('soft', t[i], end,
                f'Fine-detail measure dropped by {100*(1-after/before):.0f}% and stayed low; endpoint is estimated and focus or content changes can also cause this.'))
            last_soft_end = j

    # A coherent hue rotation on both edges, with the opposite sign on exit.
    color_edges = []
    for i in range(1, n):
        if (abs(hue[i]) >= 30 and coherence[i] >= 0.80 and saturation[i] >= 15
                and corr[i] >= 0.72 and d[i] <= 25):
            color_edges.append(i)
    used = set()
    for a in color_edges:
        if a in used:
            continue
        options = [b for b in color_edges if b not in used and 0.5 <= t[b]-t[a] <= 15
                   and hue[a]*hue[b] < 0 and abs(hue[a]+hue[b]) <= max(14, 0.5*abs(hue[a]))]
        if options:
            b = min(options, key=lambda j: abs(hue[a]+hue[j]))
            findings.append(_finding('colour_jump', t[a], t[b],
                                     f'Colour hue changed abruptly by about {hue[a]:.0f} degrees and reversed at the end.'))
            used.update((a,b))
    findings.sort(key=lambda f: (f['start'], f['kind']))
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('film', help='local film to measure')
    ap.add_argument('--freeze-seconds', type=float, default=1.5, help='minimum still-picture duration, default 1.5 seconds')
    ap.add_argument('--features', help='optional path to save per-frame measurements for reproducible evaluation')
    args = ap.parse_args()
    if not math.isfinite(args.freeze_seconds) or args.freeze_seconds <= 0:
        ap.error('--freeze-seconds must be positive and finite')
    try:
        data = scan(args.film)
        if args.features:
            with open(args.features, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'))
        result = {'film': args.film, 'video_duration_seconds': round(data['end'] - data['time'][0], 3),
                  'frames': len(data['time']), 'findings': detect(data, args.freeze_seconds),
                  'not_assessed': ['missing or reordered content', 'unwanted ornaments', 'unwanted dissolves'],
                  'note': 'Candidates require review; an empty list does not establish an undamaged film.'}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'timecheck: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    import utf8  # noqa: F401
    raise SystemExit(main())
