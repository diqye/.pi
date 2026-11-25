#!/usr/bin/env python3
"""Write out how a film moves, as text a reader can reason from.

  python see.py FILM --out DIR

DIR/motion.json is the structured model. DIR/SEE.md is the transcript: shots and how each one joins the next, what the
camera does, which distinct things move, how big they are, where they go, how they accelerate and settle, what starts
before something else has finished, how long anything is truly still, and where colour or sharpness change suddenly.

A film is read one reduced frame at a time, so memory stays small whatever its length: dense optical flow at 480 px, a
sharpness reading at up to 1280 px, and small grey thumbnails kept in a temporary file for the dissolve test.

The model describes only what can be measured. It doesn't name objects. Things with little texture on a plain ground
are tracked by their moving edges, so a size is the box those edges enclose. Motion faster than optical flow can follow,
rotating or morphing shapes and two things crossing are all weak spots, and the transcript says "about" where its own
two estimates of a distance disagree.
"""
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
import threading
from collections import namedtuple
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_diff import NO_WINDOW, check_decode, stop_decoder  # noqa: E402
from measure import background, ease_fit, POINTS, probe  # noqa: E402
import timecheck  # noqa: E402

cv2.setNumThreads(2)
VERSION = 2

FLOW_EDGE, DETAIL_EDGE, THUMB_EDGE = 480, 1280, 96  # long edge, in pixels, of the three readings of each frame
FPS_CAP = 60
_PTS = re.compile(r"showinfo.*?\bn:\s*(\d+)\s+pts:\s*[-\d]+\s+pts_time:\s*([-+\deE.]+)")

REPEAT = 0.08       # mean grey change below this is the same picture again, whatever the encoder left behind
QUIET = 0.45        # below this with no region moving, the picture is at rest and only noise is changing
STILL_MIN = 0.25    # seconds: a shorter rest is part of the motion around it
STEP_MIN = 0.12     # px per frame at flow size: slower than this is noise for a tracked thing
TRAVEL_MIN = 1.5    # px at flow size: a thing that goes less far than this hasn't moved
MAX_GAP = 0.2       # seconds a track may go unseen and still be the same track
FAST = 30           # px per frame at flow size: beyond this, optical flow is guessing
NEAR_REPEAT = 0.25  # mean grey change below this, with almost no pixel changing visibly, is a held picture for cadence purposes
MAX_HOLD = 0.4      # seconds: a held picture longer than this is a rest, not a step in a cadence


_HUE_COS, _HUE_SIN = np.cos(np.arange(180, dtype=np.float32) * np.pi / 90), np.sin(np.arange(180, dtype=np.float32) * np.pi / 90)
Reg = namedtuple("Reg", "x0 y0 x1 y1 area vx vy coh b g r fill kind change ink0 ink1")


def fit_size(w, h, edge):
    s = min(1.0, edge / max(w, h))
    return max(2, int(round(w * s / 2)) * 2), max(2, int(round(h * s / 2)) * 2)


class Decoder:
    """Yields frames one at a time as BGR; times come from the stream itself, so a variable frame rate reads true."""

    def __init__(self, path, w, h, step, duration=None):
        select = f"select='not(mod(n\\,{step}))'," if step > 1 else ""
        # level+info marks each line with its level, so an error can be told from showinfo's lines
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "level+info", "-i", str(path), "-map", "0:v:0", "-an", "-sn", "-dn",
               "-vf", f"{select}scale={w}:{h}:flags=area,showinfo", "-fps_mode", "passthrough", "-pix_fmt", "bgr24", "-f", "rawvideo", "pipe:1"]
        self.path, self.duration, self.errors = path, duration, []
        self.size, self.shape, self.times = w * h * 3, (h, w, 3), []
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1 << 20, creationflags=NO_WINDOW)
        self.log = threading.Thread(target=self._read_log, daemon=True)
        self.log.start()

    def _read_log(self):
        for line in iter(self.proc.stderr.readline, b""):
            text = line.decode("utf-8", "replace")
            m = _PTS.search(text)
            if m:
                self.times.append(float(m.group(2)))
            elif re.search(r"\[(error|fatal|panic)\] ", text):
                self.errors.append(text.strip())

    def __iter__(self):
        ended = False
        try:
            while True:
                raw = self.proc.stdout.read(self.size)
                if len(raw) < self.size:
                    ended = True
                    break
                yield np.frombuffer(raw, np.uint8).reshape(self.shape)
        finally:
            self.proc.stdout.close()
            if not ended:
                stop_decoder(self.proc)
            self.proc.wait()
            self.log.join()
            self.proc.stderr.close()
        # only reached when every frame was read
        check_decode(self.path, self.proc.returncode, "\n".join(self.errors), self.times[-1] if self.times else 0.0, self.duration)


def _box(x, k):
    """Moving average of length k, same length as x; a window longer than the signal leaves it unsmoothed."""
    return np.convolve(x, np.ones(k) / k, mode="same") if 1 < k <= len(x) else np.array(x, float)


def similarity(p, q):
    """Least-squares x' = ax - by + c, y' = bx + ay + d, as a 2x3 matrix."""
    n = len(p)
    A = np.zeros((2 * n, 4), np.float64)
    A[0::2, 0], A[0::2, 1], A[0::2, 2] = p[:, 0], -p[:, 1], 1
    A[1::2, 0], A[1::2, 1], A[1::2, 3] = p[:, 1], p[:, 0], 1
    a, b, c, d = np.linalg.lstsq(A, q.reshape(-1), rcond=None)[0]
    return np.array([[a, -b, c], [b, a, d]], np.float64)


def fit_camera(prev, flow, w, h):
    """The frame-wide motion between two frames, from textured points: (status, matrix or None, points that agree, points).

    The model that the frame's edges agree with wins: a big moving thing can hold more points than the background does,
    so a locked camera shows up as edges that fit "no motion" better than they fit the largest consensus."""
    pts = cv2.goodFeaturesToTrack(prev, 900, 0.003, 6, blockSize=5)
    if pts is None or len(pts) < 12:
        return "no_texture", None, 0.0, 0 if pts is None else len(pts)
    p = pts.reshape(-1, 2)
    d = flow[p[:, 1].astype(int), p[:, 0].astype(int)].astype(np.float64)
    target = p + d
    M, inliers = cv2.estimateAffinePartial2D(p, target.astype(np.float32), method=cv2.RANSAC, ransacReprojThreshold=0.6, maxIters=400, confidence=0.99, refineIters=8)
    if M is None or inliers is None or inliers.sum() < 8:
        return "unsure", None, 0.0, len(p)
    keep = inliers.ravel() > 0
    M = similarity(p[keep], target[keep])
    moved = (M[:, :2] @ p.T + M[:, 2:]).T
    misfit = np.hypot(*(moved - target).T)
    fits, still = misfit < 0.6, np.hypot(d[:, 0], d[:, 1]) < 0.35
    bx, by = 0.18 * w, 0.18 * h
    edge = (p[:, 0] < bx) | (p[:, 0] > w - bx) | (p[:, 1] < by) | (p[:, 1] > h - by)
    fit_share, still_share = (fits[edge].mean(), still[edge].mean()) if edge.sum() >= 8 else (fits.mean(), still.mean())
    if still_share > fit_share + 0.12 and still.sum() >= 6:   # the frame's edges say the camera isn't moving
        return "locked", similarity(p[still], target[still]), float(still.mean()), len(p)
    span_x, span_y = np.ptp(p[keep, 0]), np.ptp(p[keep, 1])
    if keep.mean() < 0.3 or span_x < 0.45 * w or span_y < 0.35 * h:   # consensus confined to one patch of the frame is an object, not the camera
        return "unsure", None, float(keep.mean()), len(p)
    corners = np.array([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]], float)
    travel = float(np.max(np.hypot(*((M[:, :2] @ corners.T + M[:, 2:]) - corners.T))))
    return ("moving" if travel >= 0.15 else "locked"), M, float(keep.mean()), len(p)


def join_primitives(prims, w, h):
    """Moving edges of one thing arrive as separate strips: join pieces that move alike and sit along the motion."""
    n = len(prims)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def gap(a, b):
        return max(0, max(a[0], b[0]) - min(a[2], b[2])), max(0, max(a[1], b[1]) - min(a[3], b[3]))

    for i in range(n):
        a = prims[i]
        for j in range(i + 1, n):
            b = prims[j]
            sa, sb = math.hypot(a[5], a[6]), math.hypot(b[5], b[6])
            s = max(sa, sb)
            if math.hypot(a[5] - b[5], a[6] - b[6]) > max(0.7, 0.5 * s):
                continue
            gx, gy = gap(a, b)
            if max(gx, gy) <= 14:
                parent[find(i)] = find(j)
                continue
            if s < 0.15 or max(gx, gy) > 0.8 * max(w, h):
                continue
            mean_x, mean_y = (a[5] + b[5]) / 2, (a[6] + b[6]) / 2
            mean_len = math.hypot(mean_x, mean_y) + 1e-9
            ux, uy = mean_x / mean_len, mean_y / mean_len
            perp = lambda box: sorted(abs(-uy * x + ux * y) for x in (box[0], box[2]) for y in (box[1], box[3]))
            pa, pb = perp(a), perp(b)
            lap = min(pa[-1], pb[-1]) - max(pa[0], pb[0])
            short = min(pa[-1] - pa[0], pb[-1] - pb[0])
            ca, cb = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            dist = math.hypot(ca[0] - cb[0], ca[1] - cb[1])
            if short > 0 and lap >= 0.6 * short and dist > 0 and abs((ca[0] - cb[0]) * ux + (ca[1] - cb[1]) * uy) / dist > 0.7:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(prims[i])
    joined = [_union(g) for g in groups.values()]
    return _join_radial(joined, w, h)


def _union(g):
    area = sum(p[4] for p in g)
    x0, y0, x1, y1 = min(p[0] for p in g), min(p[1] for p in g), max(p[2] for p in g), max(p[3] for p in g)
    vx, vy, coh = (sum(p[k] * p[4] for p in g) / area for k in (5, 6, 7))
    return [x0, y0, x1, y1, area, vx, vy, coh]


def _join_radial(groups, w, h):
    """Thin strips moving apart or together along the line between them are the edges of one thing changing size."""
    n = len(groups)
    if n < 2:
        return groups
    thin = [max(g[2] - g[0], g[3] - g[1]) > 2.5 * max(1, min(g[2] - g[0], g[3] - g[1])) and math.hypot(g[5], g[6]) > 0.4 for g in groups]
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if not (thin[i] and thin[j]):
                continue
            a, b = groups[i], groups[j]
            dv = np.array([a[5] - b[5], a[6] - b[6]])
            dp = np.array([(a[0] + a[2] - b[0] - b[2]) / 2, (a[1] + a[3] - b[1] - b[3]) / 2])
            nv, np_ = np.hypot(*dv), np.hypot(*dp)
            if nv < 0.6 or np_ < 6:
                continue
            if abs(dv[0] * dp[1] - dv[1] * dp[0]) <= 0.4 * nv * np_ and 0.002 < abs(float(dv @ dp)) / (np_ * np_) < 0.5:
                parent[find(i)] = find(j)
    merged = {}
    for i in range(n):
        merged.setdefault(find(i), []).append(groups[i])
    out = []
    for g in merged.values():
        if len(g) == 1:
            out.append(g[0])
        else:   # a size change has no net travel of its own
            u = _union(g)
            u[5], u[6] = 0.0, 0.0
            out.append(u)
    return out


def regions_in(prev, cur, cur_bgr, flow, M, X, Y, ground, hot):
    """The moving and changing regions between two frames, with the camera's motion taken out."""
    h, w = cur.shape
    warped = cv2.warpAffine(prev, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) if M is not None else prev
    if M is not None:
        gx = M[0, 0] * X + M[0, 1] * Y + M[0, 2] - X
        gy = M[1, 0] * X + M[1, 1] * Y + M[1, 2] - Y
        ru, rv = flow[..., 0] - gx.astype(np.float32), flow[..., 1] - gy.astype(np.float32)
    else:
        ru, rv = flow[..., 0], flow[..., 1]
    signed = cur.astype(np.int16) - warped.astype(np.int16)
    d = np.abs(signed).astype(np.float32)
    tau = max(6.0, 4.0 * (float(np.median(d)) * 1.5 + 0.5))
    mag = cv2.magnitude(ru, rv)
    changed = d > tau
    scattered = scatter_stats(changed, d, tau, ru, rv, w, h)
    moving = changed & (mag > 0.25)
    if hot is not None and hot.any():
        moving |= hot & (d > 0.6 * tau) & (mag > 0.06)   # where something was just moving, follow it down to a crawl
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    prims = []
    closed = cv2.morphologyEx(moving.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    order = np.argsort(-stats[1:, cv2.CC_STAT_AREA])[:40] + 1 if count > 1 else []
    for k in order:
        x, y, bw, bh, area = stats[k]
        if area < 10:
            break
        core = (labels[y:y + bh, x:x + bw] == k) & moving[y:y + bh, x:x + bw]
        if core.sum() < 6:
            continue
        u, v = ru[y:y + bh, x:x + bw][core], rv[y:y + bh, x:x + bw][core]
        vx, vy = float(np.median(u)), float(np.median(v))
        coh = float(np.mean(np.hypot(u - vx, v - vy) <= max(0.7, 0.4 * math.hypot(vx, vy))))
        prims.append([int(x), int(y), int(x + bw), int(y + bh), int(core.sum()), vx, vy, coh])
    out = []
    for g in (join_primitives(prims, w, h) if prims else []):
        crop = cur_bgr[g[1]:g[3], g[0]:g[2]].astype(np.int16)
        ink = np.abs(crop - ground).max(axis=2) > 30
        colour = np.median(crop[ink], axis=0) if ink.sum() >= 4 else np.median(crop.reshape(-1, 3), axis=0)
        out.append(Reg(*g[:8], int(colour[0]), int(colour[1]), int(colour[2]), float(ink.mean()), 0, 0.0, 0.0, 0.0))
    # what changed without moving: something fading, popping on or off, or flickering in place
    still_change = (changed & ~(mag > 0.25)).astype(np.uint8)
    if still_change.mean() < 0.6:
        closed = cv2.morphologyEx(still_change, cv2.MORPH_CLOSE, kernel)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
        order = np.argsort(-stats[1:, cv2.CC_STAT_AREA])[:8] + 1 if count > 1 else []
        for k in order:
            x, y, bw, bh, area = stats[k]
            if area < 40:
                break
            part = labels[y:y + bh, x:x + bw] == k
            mean_change = float(signed[y:y + bh, x:x + bw][part].mean())
            before = np.abs(prev[y:y + bh, x:x + bw].astype(np.int16) - _grey(ground))[part] > 30
            after = np.abs(cur[y:y + bh, x:x + bw].astype(np.int16) - _grey(ground))[part] > 30
            out.append(Reg(int(x), int(y), int(x + bw), int(y + bh), int(area), 0.0, 0.0, 1.0, 0, 0, 0, 0.0, 1, mean_change, float(before.mean()), float(after.mean())))
    return out, scattered


NO_SCATTER = (0, 0.0, 0, 0.0, 0.0, 0.0, 0)


def scatter_stats(changed, d, tau, ru, rv, w, h):
    """Small separate patches of change: how many, how big, how widely spread, and whether they go their own ways.

    Returns (count, typical width in px at flow size, grid cells of 24 touched, share of changed pixels they hold, how much
    their directions agree, share of them actually travelling, and the smaller of how many rows and columns they reach). Only
    patches that change strongly count, so film grain and shimmer along edges don't."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(changed.astype(np.uint8), connectivity=8)
    if count <= 1:
        return NO_SCATTER
    areas = stats[1:, cv2.CC_STAT_AREA]
    strength = np.bincount(labels.ravel(), d.ravel(), count)[1:] / np.maximum(areas, 1)
    u = np.bincount(labels.ravel(), ru.ravel(), count)[1:] / np.maximum(areas, 1)
    v = np.bincount(labels.ravel(), rv.ravel(), count)[1:] / np.maximum(areas, 1)
    # something faint counts if it is really travelling; something staying put has to change strongly to tell it from shimmer
    small = (areas >= 3) & (areas <= max(30, 0.0015 * w * h)) & ((strength >= 2.5 * tau) | ((strength >= 1.5 * tau) & (np.hypot(u, v) > 0.25)))
    n = int(small.sum())
    if n == 0:
        return NO_SCATTER
    if n > 400:      # a field of specks is noise or a texture changing, not separate things
        return (n, 0.0, 24, 0.0, 0.0, 0.0, 0)
    xs = stats[1:, cv2.CC_STAT_LEFT][small] + stats[1:, cv2.CC_STAT_WIDTH][small] / 2
    ys = stats[1:, cv2.CC_STAT_TOP][small] + stats[1:, cv2.CC_STAT_HEIGHT][small] / 2
    grid = {(int(x * 6 // w), int(y * 4 // h)) for x, y in zip(xs, ys)}
    cells = len(grid)
    reach = min(len({c for c, _ in grid}), len({r for _, r in grid}))
    u, v = u[small], v[small]
    speed = np.hypot(u, v)
    going = speed > 0.25
    agree = float(np.hypot((u[going] / speed[going]).mean(), (v[going] / speed[going]).mean())) if going.sum() >= 4 else 0.0
    return (n, float(np.median(np.sqrt(areas[small]))), cells, float(areas[small].sum() / max(areas.sum(), 1)), agree, float(going.mean()), reach)


def scattered_in_shot(scanned, first, last):
    """Many small things scattered across the frame, each on its own, reported as a count and a rough size."""
    rows = scanned["scatter"][first + 1:last]
    if len(rows) < 3:
        return None
    t = scanned["t"][first + 1:last]
    dt = float(np.median(np.diff(scanned["t"][first:last])))
    n, size, cells, held, agree, going, reach = rows.T
    active = (n >= 4) & (n <= 400) & (cells >= 6) & (reach >= 3) & (held >= 0.4) & (agree < 0.8)
    if active.sum() * dt < 0.4 or active.mean() < 0.3:
        return None
    return {"t0": float(t[active][0]), "t1": float(t[active][-1]), "count": int(round(float(np.median(n[active])))), "count_low": int(np.percentile(n[active], 10)), "count_high": int(np.percentile(n[active], 90)),
            "size_px": float(np.median(size[active])) * scanned["scale"], "cells": int(round(float(np.median(cells[active])))), "travelling": float(np.median(going[active]))}


def _grey(bgr):
    return int(round(0.114 * bgr[0] + 0.587 * bgr[1] + 0.299 * bgr[2]))


def scan(path, info, tmp):
    """Everything that needs pixels, in one pass; only per-frame numbers and thumbnails outlast each frame."""
    step = max(1, int(round(info["fps"] / FPS_CAP))) if info["fps"] > FPS_CAP * 1.1 else 1
    dw, dh = fit_size(info["w"], info["h"], DETAIL_EDGE)
    aw, ah = fit_size(info["w"], info["h"], FLOW_EDGE)
    tw, th = fit_size(info["w"], info["h"], THUMB_EDGE)
    dec = Decoder(path, dw, dh, step, info["duration"])
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    X, Y = np.meshgrid(np.arange(aw, dtype=np.float32), np.arange(ah, dtype=np.float32))
    prev = prev_lab = hot = None
    rows = {k: [] for k in ("e", "repeat", "near", "detail", "luma", "L", "a", "b", "dL", "da", "db", "spread", "hue", "hue_coh", "sat")}
    prev_hsv = None
    cams, regs, scatter = [], [], []
    thumb_path, colour_path = Path(tmp) / "thumbs.bin", Path(tmp) / "colour.bin"
    n = 0
    with open(thumb_path, "wb") as thumbs, open(colour_path, "wb") as colours:
        for big in dec:
            detail_grey = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
            rows["detail"].append(float(cv2.Laplacian(detail_grey, cv2.CV_32F, ksize=3).var()))
            small = cv2.resize(big, (aw, ah), interpolation=cv2.INTER_AREA)
            grey = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            thumbs.write(cv2.resize(grey, (tw, th), interpolation=cv2.INTER_AREA).tobytes())
            blocks = cv2.cvtColor(cv2.resize(small, (32, 18), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2LAB)
            colours.write(cv2.resize(blocks, (16, 9), interpolation=cv2.INTER_AREA).tobytes())
            lab = blocks.astype(np.float32).reshape(-1, 3)
            lab[:, 0] /= 2.55     # OpenCV stores L as 0-255
            rows["luma"].append(float(grey.mean()))
            mean_lab = lab.mean(axis=0)
            rows["L"].append(float(mean_lab[0])); rows["a"].append(float(mean_lab[1])); rows["b"].append(float(mean_lab[2]))
            hsv = cv2.cvtColor(cv2.resize(small, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV)
            if prev_hsv is None:
                rows["hue"].append(0.0); rows["hue_coh"].append(0.0); rows["sat"].append(0.0)
            else:
                shift = ((hsv[:, :, 0].astype(np.int16) - prev_hsv[:, :, 0].astype(np.int16)) % 180).astype(np.uint8)
                weight = np.minimum(hsv[:, :, 1], prev_hsv[:, :, 1]).astype(np.float32) * np.minimum(hsv[:, :, 2], prev_hsv[:, :, 2]).astype(np.float32) / 255.0
                total = float(weight.sum())
                rows["sat"].append(total / weight.size)
                if total > 0:
                    x, y = float((_HUE_COS[shift] * weight).sum() / total), float((_HUE_SIN[shift] * weight).sum() / total)
                    rows["hue"].append(math.degrees(math.atan2(y, x))); rows["hue_coh"].append(math.hypot(x, y))
                else:
                    rows["hue"].append(0.0); rows["hue_coh"].append(0.0)
            prev_hsv = hsv
            if prev is None:
                rows["e"].append(0.0); rows["repeat"].append(0.0); rows["near"].append(0.0); rows["dL"].append(0.0); rows["da"].append(0.0); rows["db"].append(0.0); rows["spread"].append(0.0)
                cams.append(("first", None, 0.0, 0)); regs.append([]); scatter.append(NO_SCATTER)
            else:
                absd = cv2.absdiff(grey, prev)
                e = float(absd.mean())
                repeat = e < REPEAT and int((absd > 8).sum()) < 12
                rows["e"].append(e)
                rows["repeat"].append(float(repeat))
                rows["near"].append(float(e < NEAR_REPEAT and int((absd > 10).sum()) < 0.0005 * absd.size))
                delta = lab - prev_lab
                med = np.median(delta, axis=0)
                rows["dL"].append(float(med[0])); rows["da"].append(float(med[1])); rows["db"].append(float(med[2]))
                rows["spread"].append(float(np.median(np.abs(delta - med).sum(axis=1))))
                if repeat:
                    cams.append(("repeat", None, 1.0, 0)); regs.append([]); scatter.append(NO_SCATTER)
                else:
                    flow = dis.calc(prev, grey, None)
                    status, M, share, npts = fit_camera(prev, flow, aw, ah)
                    cams.append((status, M.tolist() if M is not None else None, share, npts))
                    ground = background(small).astype(int)
                    found, scattered = regions_in(prev, grey, small, flow, M, X, Y, ground, hot)
                    regs.append(found)
                    scatter.append(scattered)
                    hot = None
                    for r in found:
                        if r.kind == 0:
                            if hot is None:
                                hot = np.zeros((ah, aw), bool)
                            hot[max(0, r.y0 - 8):min(ah, r.y1 + 8), max(0, r.x0 - 8):min(aw, r.x1 + 8)] = True
            prev, prev_lab = grey, lab
            n += 1
    if n < 2:
        raise SystemExit("too few frames to read")
    t = np.array(dec.times[:n], float)
    if len(t) < n:   # showinfo lost lines: a regular clock is the honest fallback
        t = np.arange(n) / (info["fps"] / step)
    return {"t": t, "n": n, "aw": aw, "ah": ah, "tw": tw, "th": th, "scale": info["w"] / aw, "cams": cams, "regs": regs, "scatter": np.array(scatter, float),
            "thumbs": thumb_path, "colour_blocks": colour_path, "step": step, **{k: np.array(v, float) for k, v in rows.items()}}


def _ncc(a, b):
    a, b = a - a.mean(), b - b.mean()
    den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum()) / den if den > 1e-6 else 1.0


def _edges(a):
    return cv2.magnitude(cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3))


def load_thumbs(scanned):
    return np.memmap(scanned["thumbs"], dtype=np.uint8, mode="r", shape=(scanned["n"], scanned["th"], scanned["tw"]))


def cut_signals(thumbs):
    """Frame-to-frame change, and whether the old picture's edges survive and the new picture's edges were already there."""
    n = len(thumbs)
    e, changed, struct = np.zeros(n), np.zeros(n), np.ones(n)
    keep_old, keep_new, blank = np.ones(n), np.ones(n), np.zeros(n, bool)
    a = thumbs[0].astype(np.float32)
    ea = _edges(a)
    ma = ea > 24
    grow = np.ones((3, 3), np.uint8)
    limit = 0.002 * a.size
    for i in range(1, n):
        b = thumbs[i].astype(np.float32)
        eb = _edges(b)
        mb = eb > 24
        delta = b - a
        e[i] = float(np.abs(delta).mean())
        changed[i] = float((np.abs(delta - np.median(delta)) > 14).mean())
        struct[i] = _ncc(ea, eb)
        count_a, count_b = int(ma.sum()), int(mb.sum())
        blank[i] = count_a < limit or count_b < limit
        if count_a:
            keep_old[i] = float((ma & (cv2.dilate(mb.astype(np.uint8), grow) > 0)).sum() / count_a)
        if count_b:
            keep_new[i] = float((mb & (cv2.dilate(ma.astype(np.uint8), grow) > 0)).sum() / count_b)
        a, ea, ma = b, eb, mb
    return {"e": e, "changed": changed, "struct": struct, "keep_old": keep_old, "keep_new": keep_new, "blank": blank}


def find_cuts(sig, stepped=None):
    """Hard cuts and jumps. A cut replaces what was on screen: the old picture's edges are gone and the new one's weren't there.

    That holds however little of the frame the pictures cover, so one graphic swapped for another on a plain ground is a
    cut, and an element added to a picture that stays is not. Frames that are steps of a held cadence are never cuts."""
    e, changed, struct, keep_old, keep_new, blank = (sig[k] for k in ("e", "changed", "struct", "keep_old", "keep_new", "blank"))
    out = []
    for i in np.flatnonzero(e > 2.0):
        if i < 1 or (stepped is not None and stepped[i]):
            continue
        around = np.r_[e[max(1, i - 12):i - 1], e[i + 2:i + 13]]
        local = float(np.median(around)) if len(around) else 0.0
        if e[i] < max(3.0, 3.5 * local + 1.0) and not (struct[i] < 0.4 and e[i] > 2 * local + 1):
            continue
        if i + 1 < len(e) and e[i + 1] > e[i] * 1.5:
            continue
        replaced = (keep_old[i] < 0.5 and keep_new[i] < 0.5) or (struct[i] < 0.25 and keep_old[i] < 0.65 and keep_new[i] < 0.65)
        if blank[i]:
            if e[i] >= 20:
                out.append((int(i), "cut"))
        elif replaced and changed[i] >= 0.03:
            out.append((int(i), "cut"))
        elif changed[i] >= 0.2 and struct[i] < 0.72:
            out.append((int(i), "cut"))
        elif struct[i] < 0.93 and changed[i] >= 0.35:
            out.append((int(i), "jump"))
    return out


def blend_test(thumbs, s, e):
    """Are frames s to e a blend of the frame before them and the frame after? Returns alpha per frame, or None."""
    a, b = max(0, s - 2), min(len(thumbs) - 1, e + 2)
    if b - a < 4:
        return None
    A, B = thumbs[a].astype(np.float32), thumbs[b].astype(np.float32)
    D = B - A
    if float((np.abs(D) > 10).mean()) < 0.3:
        return None
    den = float((D * D).sum())
    if den < 1:
        return None
    blank_end = float(A.std()) < 8 or float(B.std()) < 8
    if not blank_end and _ncc(_edges(A), _edges(B)) >= 0.9:
        return None
    alphas, residuals = [], []
    for i in range(a, b + 1):
        x = thumbs[i].astype(np.float32) - A
        al = float((x * D).sum()) / den
        alphas.append(al)
        residuals.append(math.sqrt(float(((x - al * D) ** 2).sum()) / den))
    alphas, residuals = np.array(alphas), np.array(residuals)
    inner = residuals[1:-1] if len(residuals) > 4 else residuals
    if float(np.median(inner)) > 0.4 or np.corrcoef(np.arange(len(alphas)), alphas)[0, 1] < 0.93:
        return None
    return a, b, alphas


def camera_explains(scanned, s, e):
    """True when one camera move accounts for this stretch: a push is not a dissolve even though its frames blend alike."""
    shares = [c[2] for c in scanned["cams"][s:e + 1] if c[0] == "moving"]
    return len(shares) >= 0.6 * (e - s + 1) and float(np.median(shares)) >= 0.7


def _dip_to_blank(thumbs, s, e, t):
    """Picture out to black (or any blank) and the next picture in, reported as one join."""
    n = len(thumbs)
    lo, hi = max(0, s - 2), min(n - 1, e + 2)
    dev = [float(thumbs[i].std()) for i in range(lo, hi + 1)]
    k = int(np.argmin(dev))
    if dev[k] >= 8 or k < 1 or k >= len(dev) - 1 or dev[0] < 15 or dev[-1] < 15:
        return None
    dark = lo + k
    out_fit, in_fit = blend_test(thumbs, s, dark), blend_test(thumbs, dark, e)
    if out_fit is None or in_fit is None:
        return None
    luma = [float(thumbs[i].mean()) for i in range(lo, hi + 1)]
    first = lo + next((j for j in range(0, k + 1) if luma[j] < 0.97 * luma[0]), 0)
    last = lo + next((j for j in range(k, len(luma)) if luma[j] >= 0.97 * luma[-1]), len(luma) - 1)
    return {"kind": "fade_through", "first": int(first), "last": int(last), "t0": float(t[first]), "t1": float(t[last])}


def same_scene(a, b):
    """Is frame b frame a displaced? Correlation after the best shift, away from the frame's edges."""
    a, b = a.astype(np.float32), b.astype(np.float32)
    h, w = a.shape
    (dx, dy), _ = cv2.phaseCorrelate(a, b, cv2.createHanningWindow((w, h), cv2.CV_32F))
    if abs(dx) > 0.45 * w or abs(dy) > 0.45 * h:
        return False
    moved = cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (w, h), borderMode=cv2.BORDER_REPLICATE)
    my, mx = int(0.2 * h), int(0.2 * w)
    return _ncc(moved[my:h - my, mx:w - mx], b[my:h - my, mx:w - mx]) >= 0.5


def stepped_stretches(scanned, thumbs, sig):
    """Runs of pictures held for near-equal counts of frames, where each new picture is the same scene moved on.

    Returns the runs and a frame mask of their steps. Those steps can be big enough to look like cuts; they are not."""
    n, t = scanned["n"], scanned["t"]
    e = scanned["e"]
    near = scanned["near"] > 0
    # an encoder leaves a held frame slightly different; next to a real step it is still a tiny change
    around = np.maximum(np.r_[e[1:], 0.0], np.r_[0.0, e[:-1]])
    near = near | ((e < 1.5) & (e < 0.2 * around))
    dt = float(np.median(np.diff(t)))
    starts = [0] + [i for i in range(1, n) if not near[i]]
    mask = np.zeros(n, bool)
    if len(starts) < 5:
        return [], mask
    holds = np.diff(starts + [n])
    longest = int(round(MAX_HOLD / dt))
    fits = (holds >= 2) & (holds <= longest)
    runs, k, m = [], 0, len(holds)
    while k < m:
        if not fits[k]:
            k += 1
            continue
        j = k
        while j + 1 < m and fits[j + 1]:
            typical = float(np.median(holds[k:j + 2]))
            if abs(holds[j + 1] - typical) > max(1.0, 0.25 * typical):
                break
            j += 1
        if j - k + 1 >= 3:
            steps = [starts[x] for x in range(k + 1, min(j + 2, len(starts)))]
            frames_held = [x for a0 in range(k, j + 1) for x in range(starts[a0] + 1, starts[a0 + 1] if a0 + 1 < len(starts) else n)]
            quiet_level = float(np.mean(e[frames_held])) if frames_held else 0.0
            real = [x for x in steps if e[x] >= max(0.5, 5 * quiet_level)]
            alike = [x for x in real if same_scene(thumbs[x - 1], thumbs[x])]
            if len(real) >= 0.6 * len(steps) and len(alike) >= 0.6 * len(real) and len(alike) >= 2:
                mask[alike] = True
                runs.append({"first": int(starts[k]), "last": int(steps[-1]), "t0": float(t[starts[k]]), "t1": float(t[steps[-1]]), "hold_frames": int(round(float(np.median(holds[k:j + 1])))),
                             "hold_s": float(np.median(holds[k:j + 1])) * dt, "steps": len(steps)})
        k = j + 1
    return runs, mask


def find_dissolves(thumbs, cuts, t, scanned):
    """Stretches where the change from frame to frame is the same image difference every time: a blend, not movement."""
    n = len(thumbs)
    cand = np.zeros(n, bool)
    for k in (1, 2, 3):
        prev = None
        for i in range(0, n - k):
            d = thumbs[i + k].astype(np.float32) - thumbs[i].astype(np.float32)
            if prev is not None and float((np.abs(d) > 2.5).mean()) >= 0.3 and _ncc(d, prev) > 0.75:
                cand[max(0, i - k):min(n, i + k + 1)] = True
            prev = d if i % k == 0 else prev
    hard = {c[0] for c in cuts}
    runs, i, out = [], 0, []
    while i < n:
        if cand[i]:
            j = i
            while j + 1 < n and (cand[j + 1] or (j + 2 < n and cand[j + 2])):
                j += 1
            if j - i >= 3:
                runs.append((i, j))
            i = j + 1
        else:
            i += 1
    for s, e in runs:
        if any(s <= c <= e + 1 for c in hard) or camera_explains(scanned, s, e):
            continue
        dip = _dip_to_blank(thumbs, s, e, t)
        if dip is not None:
            out.append(dip)
            continue
        fit = blend_test(thumbs, s, e)
        if fit is None:
            continue
        a, b, alpha = fit
        first = a + int(np.argmax(alpha > 0.04))
        last = a + len(alpha) - 1 - int(np.argmax(alpha[::-1] < 0.96))
        if last <= first:
            continue
        A, B = thumbs[a], thumbs[b]
        kind = "fade_in" if float(A.std()) < 8 else "fade_out" if float(B.std()) < 8 else "dissolve"
        out.append({"kind": kind, "first": int(first), "last": int(last), "t0": float(t[first]), "t1": float(t[last])})
    return out


def build_shots(n, t, cuts, dissolves, thumbs):
    """Shots as frame ranges with the join that opens each. A one-frame shot between same pictures is a flash, not a shot."""
    edges = [{"at": c, "kind": k, "first": c, "last": c} for c, k in cuts]
    edges += [{"at": d["first"], "kind": d["kind"], "first": d["first"], "last": d["last"]} for d in dissolves]
    edges.sort(key=lambda x: x["at"])
    grouped, i = [], 0
    while i < len(edges):
        x = edges[i]
        j = i
        while x["kind"] in ("cut", "jump") and j + 1 < len(edges) and edges[j + 1]["kind"] in ("cut", "jump") and edges[j + 1]["at"] - edges[j]["at"] <= 2:
            j += 1
        if j - i >= 2:
            grouped.append({"at": x["at"], "kind": "flurry", "first": x["at"], "last": edges[j]["at"], "count": j - i + 1})
            i = j + 1
        else:
            grouped.append(x)
            i += 1
    edges = grouped
    flashes, kept, i = [], [], 0
    while i < len(edges):
        x = edges[i]
        if i + 1 < len(edges) and edges[i + 1]["at"] - x["at"] <= 2 and x["kind"] in ("cut", "jump") and edges[i + 1]["kind"] in ("cut", "jump"):
            a, b = thumbs[max(0, x["at"] - 1)].astype(np.float32), thumbs[min(n - 1, edges[i + 1]["at"])].astype(np.float32)
            if float(np.abs(a - b).mean()) < 6:
                flashes.append({"t": float(t[x["at"]]), "frames": edges[i + 1]["at"] - x["at"]})
            else:
                kept.append({"at": x["at"], "kind": "flurry", "first": x["at"], "last": edges[i + 1]["at"], "count": 2})
            i += 2
            continue
        kept.append(x)
        i += 1
    shots, start = [], 0
    previous = {"kind": "start", "first": 0, "last": 0, "at": 0}
    for edge in kept:
        last = edge["first"]
        if last - start >= 1:
            shots.append({"first": start, "last": last, "in": previous})
        previous, start = edge, edge["last"]
    if n - start >= 1:
        shots.append({"first": start, "last": n, "in": previous})
    return shots, flashes


def crossing(series, level, times):
    """First time a rising series reaches level, by interpolation."""
    for k in range(1, len(series)):
        if series[k] >= level > series[k - 1]:
            f = (level - series[k - 1]) / max(series[k] - series[k - 1], 1e-9)
            return float(times[k - 1] + f * (times[k] - times[k - 1]))
    return float(times[0] if series[0] >= level else times[-1])


def describe_move(v, t, a, b, tol):
    """One move: steps a to b-1 of per-step displacement v, with frame times t (t[k] before step k, t[k+1] after)."""
    disp = np.vstack([[0.0, 0.0], np.cumsum(v[a:b], axis=0)])
    net = disp[-1]
    path = float(np.hypot(v[a:b, 0], v[a:b, 1]).sum())
    if path <= 0:
        return None
    if math.hypot(*net) > 0.25 * path:
        axis = net / math.hypot(*net)
    else:
        axis = np.linalg.svd(v[a:b] - v[a:b].mean(axis=0), full_matrices=False)[2][0]
    along = disp @ axis
    last = float(np.median(along[-3:])) if len(along) >= 4 else float(along[-1])
    if last < 0:
        along, axis, last = -along, -axis, -last
    distance = float(along[-1])
    times = t[a:b + 1]
    dt = np.diff(times)
    if distance <= 0:
        return None
    start = crossing(along, 0.02 * distance, times)
    arrive = crossing(along, 0.98 * distance, times)
    half = crossing(along, 0.5 * distance, times)
    dur = max(arrive - start, 1e-3)
    speed = np.diff(along) / np.maximum(dt, 1e-6)
    i0 = max(0, int(np.searchsorted(times, start) - 1))
    i1 = max(i0 + 2, int(np.searchsorted(times, arrive)))
    window = speed[i0:i1]
    peak_k = i0 + int(np.argmax(window)) if len(window) else 0
    peak = float(speed[peak_k]) if len(speed) else 0.0
    ramp = min(2, len(window))
    start_speed = float(window[:ramp].mean()) if ramp else 0.0
    end_speed = float(window[-ramp:].mean()) if ramp else 0.0
    if len(window) >= 3 and window.max() > 0:
        prof = np.interp(np.linspace(0, len(window) - 1, POINTS), np.arange(len(window)), np.maximum(window, 0))
        prof = prof / prof.max()
        bezier = ease_fit(prof)
    else:
        prof, bezier = None, None
    t50 = (half - start) / dur
    tail_from = i1 + 1
    over = float(along[tail_from:].max() - distance) if tail_from < len(along) else 0.0
    max_at = float(along.max() - distance)
    overshoot = max(over, max_at) if along.max() > distance else 0.0
    over_t = float(times[int(np.argmax(along))])
    settled = None
    if overshoot > tol:
        away = np.abs(along - distance) > tol
        settled = float(times[min(len(times) - 1, len(times) - int(np.argmax(away[::-1])))]) if away.any() else float(times[-1])
    middle = speed[i0 + int(0.15 * len(window)):i0 + max(1, int(0.85 * len(window)))] if len(window) >= 5 else window
    cv_mid = float(np.std(middle) / max(np.mean(middle), 1e-6)) if len(middle) else 0.0
    edge_n = max(1, int(round(0.12 * len(window)))) if len(window) else 1
    abrupt_start = bool(len(window) and window[:edge_n].mean() >= 0.6 * max(window.max(), 1e-6))
    abrupt_end = bool(len(window) and window[-edge_n:].mean() >= 0.6 * max(window.max(), 1e-6))
    if len(window) < 3:
        shape = "too short to shape"
    elif abrupt_start and abrupt_end and cv_mid < 0.25:
        shape = "constant speed"
    elif t50 < 0.42:
        shape = "decelerates"
    elif t50 > 0.58:
        shape = "accelerates"
    else:
        shape = "eased both ends"
    second = np.diff(np.diff(along))
    rough = float(np.median(np.abs(second)) / max(np.median(np.abs(np.diff(along))), 1e-6)) if len(along) > 5 else 0.0
    return {"t0": start, "t1": arrive, "t_half": half, "settled": settled, "dur": dur, "t50": float(t50), "peak_speed": peak, "start_speed": start_speed, "end_speed": end_speed,
            "peak_at": float((times[peak_k] + times[peak_k + 1]) / 2) if len(speed) else start, "peak_frac": float((peak_k - i0 + 0.5) / max(len(window), 1)),
            "dx": float(net[0]), "dy": float(net[1]), "distance": distance, "path": path, "straight": float(math.hypot(*net) / path),
            "shape": shape, "abrupt_start": abrupt_start, "abrupt_end": abrupt_end, "overshoot": overshoot if overshoot > tol else 0.0, "overshoot_at": over_t if overshoot > tol else None,
            "bezier": bezier, "rough": rough, "profile": [round(float(x), 2) for x in prof] if prof is not None else None}


def split_runs(on, gap):
    runs, i, n = [], 0, len(on)
    while i < n:
        if on[i]:
            j = i
            while j + 1 < n and (on[j + 1] or (j + 1 + gap < n and on[j + 1:j + 2 + gap].any())):
                j += 1
            runs.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    return runs


def reversal_points(v, a, b, tol):
    """Indices inside steps a..b at which a real change of direction happens: a return of at least 30% of the way out."""
    seg = v[a:b]
    if len(seg) < 4:
        return []
    axis = np.linalg.svd(seg - seg.mean(axis=0), full_matrices=False)[2][0]
    along = np.cumsum(seg @ axis)
    points, last = [], 0
    sign = 0
    for k in range(1, len(along)):
        d = seg[k] @ axis
        if abs(d) < 1e-3:
            continue
        s = 1 if d > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            out = abs(along[k - 1] - (along[last - 1] if last else 0.0))
            rest = along[k:]
            back = float(np.max(np.abs(rest - along[k - 1]))) if len(rest) else 0.0
            if back >= 0.3 * out and back > 3 * tol and out > 3 * tol:
                points.append(a + k)
                last = k
                sign = s
    return points


def moves_from(v, t, vmin, travel, tol, bridge=None):
    """Moves within per-step displacements v, splitting at rests and at true reversals."""
    if len(v) == 0:
        return []
    dt = float(np.median(np.diff(t)))
    speed = np.hypot(v[:, 0], v[:, 1])
    smooth = _box(speed, 3)
    on = smooth > vmin
    if bridge is not None:
        on = on | bridge
    windows = []
    for a, b in split_runs(on, max(2, int(round(0.1 / dt)))):
        windows += _pairs(a, b, reversal_points(v, a, b, tol))
    merged = []
    for w in windows:
        if merged:
            pa, pb = merged[-1]
            net_prev, net_now = v[pa:pb].sum(axis=0), v[w[0]:w[1]].sum(axis=0)
            gap_time = float(t[w[0]] - t[pb])
            len_prev, len_now = float(np.hypot(*net_prev)), float(np.hypot(*net_now))
            if gap_time <= 0.45 and float(net_prev @ net_now) < 0 and len_now <= 0.35 * len_prev:
                merged[-1] = (pa, w[1])    # a small return right after a move is that move settling back
                continue
        merged.append(w)
    out = []
    for x, y in merged:
        m = describe_move(v, t, x, y, tol)
        if m and m["path"] >= travel:
            out.append(m)
    return out


def _pairs(a, b, points):
    edges = [a] + list(points) + [b]
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def link_tracks(regs, t, first, last, kind=0):
    """Join each pair's regions into tracks of one thing: predict from velocity, accept the nearest of a similar size."""
    max_idle = max(2, int(round(MAX_GAP / max(float(np.median(np.diff(t))), 1e-6))))
    live, done = [], []
    for i in range(first + 1, last):
        items = [r for r in regs[i] if r.kind == kind]
        scored = []
        for ti, tr in enumerate(live):
            r0 = tr["regs"][-1]
            gap = i - tr["idx"][-1]
            cx, cy = (r0.x0 + r0.x1) / 2 + r0.vx * gap, (r0.y0 + r0.y1) / 2 + r0.vy * gap
            size = max(8.0, (r0.x1 - r0.x0 + r0.y1 - r0.y0) / 2)
            for gi, r in enumerate(items):
                x, y = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                dist = math.hypot(x - cx, y - cy) / size
                ix = max(0, min(r0.x1 + r0.vx, r.x1) - max(r0.x0 + r0.vx, r.x0))
                iy = max(0, min(r0.y1 + r0.vy, r.y1) - max(r0.y0 + r0.vy, r.y0))
                union = (r0.x1 - r0.x0) * (r0.y1 - r0.y0) + (r.x1 - r.x0) * (r.y1 - r.y0) - ix * iy
                iou = ix * iy / max(union, 1)
                dv = math.hypot(r.vx - r0.vx, r.vy - r0.vy)
                size_change = abs(math.log(max(r.area, 1) / max(r0.area, 1)))
                if dist < 1.2 or iou > 0.15:
                    if kind == 1 or dv <= max(3.0, 0.8 * math.hypot(r0.vx, r0.vy) + 1):
                        scored.append((dist - iou + 0.3 * dv / max(1.0, math.hypot(r0.vx, r0.vy)) + 0.25 * size_change, ti, gi))
                elif kind == 0 and gap == 1 and dist < 6 and size_change < 0.4 and abs(r.b - r0.b) + abs(r.g - r0.g) + abs(r.r - r0.r) < 60:
                    scored.append((3.0 + dist * 0.1 + 0.25 * size_change, ti, gi))     # too fast for flow to agree: same size and colour, one frame on
        used_t, used_g = set(), set()
        for _, ti, gi in sorted(scored):
            if ti in used_t or gi in used_g:
                continue
            used_t.add(ti); used_g.add(gi)
            live[ti]["idx"].append(i); live[ti]["regs"].append(items[gi])
        for gi, r in enumerate(items):
            if gi not in used_g:
                live.append({"idx": [i], "regs": [r]})
        still = []
        for tr in live:
            (done if i - tr["idx"][-1] > max_idle else still).append(tr)
        live = still
    done.extend(live)
    return done


def merge_parts(tracks, near=8):
    """Pieces of one thing: a shorter track whose boxes sit inside a longer track's box, at the same time or just beside it.

    At a crawl the two edges of a plain shape come apart and each gets its own short track."""
    tracks = sorted(tracks, key=lambda tr: -len(tr["idx"]))
    out = []
    for tr in tracks:
        home = None
        for big in out:
            hits, tries = 0, 0
            for i, r in zip(tr["idx"], tr["regs"]):
                nearby = [x for k, x in zip(big["idx"], big["regs"]) if abs(k - i) <= near]
                if not nearby:
                    continue
                tries += 1
                bx0, by0, bx1, by1 = min(x.x0 for x in nearby), min(x.y0 for x in nearby), max(x.x1 for x in nearby), max(x.y1 for x in nearby)
                if r.x0 >= bx0 - 12 and r.y0 >= by0 - 12 and r.x1 <= bx1 + 12 and r.y1 <= by1 + 12:
                    hits += 1
            if tries >= 2 and hits >= 0.7 * tries:
                home = big
                break
        if home is None:
            out.append({"idx": list(tr["idx"]), "regs": list(tr["regs"])})
        else:
            taken = set(home["idx"])
            for i, r in zip(tr["idx"], tr["regs"]):
                if i not in taken:
                    home["idx"].append(i)
                    home["regs"].append(r)
            order = np.argsort(home["idx"])
            home["idx"] = [home["idx"][k] for k in order]
            home["regs"] = [home["regs"][k] for k in order]
    return out


def merge_rests(tracks, scale_w):
    """A thing that stops and starts again is one thing: rejoin tracks that end where another begins."""
    tracks = sorted(tracks, key=lambda x: x["idx"][0])
    merged = []
    for tr in tracks:
        r = tr["regs"][0]
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        size = max(10.0, (r.x1 - r.x0 + r.y1 - r.y0) / 2)
        best, best_d = None, 1e9
        for m in merged:
            if m["idx"][-1] >= tr["idx"][0]:
                continue
            e = m["regs"][-1]
            ex, ey = (e.x0 + e.x1) / 2, (e.y0 + e.y1) / 2
            sz = max(10.0, (e.x1 - e.x0 + e.y1 - e.y0) / 2)
            if not 0.5 < size / sz < 2.0:
                continue
            d = math.hypot(cx - ex, cy - ey) / max(size, sz)
            if d < 0.7 and d < best_d:
                best, best_d = m, d
        if best is not None:
            best["idx"] += tr["idx"]
            best["regs"] += tr["regs"]
        else:
            merged.append({"idx": list(tr["idx"]), "regs": list(tr["regs"])})
    return merged


def _net(tr):
    return sum(r.vx for r in tr["regs"]), sum(r.vy for r in tr["regs"])


def place_word(x, y, w, h):
    col = "left" if x < w / 3 else "right" if x > 2 * w / 3 else "centre"
    row = "top" if y < h / 3 else "bottom" if y > 2 * h / 3 else "middle"
    if row == "middle" and col == "centre":
        return "centre"
    return f"{row}-{col}".replace("middle-", "centre-").replace("-centre", " centre") if row != "middle" else f"centre-{col}"


def size_word(area_share):
    if area_share >= 0.25:
        return "very large"
    if area_share >= 0.08:
        return "large"
    if area_share >= 0.015:
        return "medium"
    if area_share >= 0.0025:
        return "small"
    return "tiny"


def colour_word(b, g, r, fill):
    bgr = np.array([[[b, g, r]]], np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
    v, s, h = int(hsv[2]), int(hsv[1]), int(hsv[0]) * 2
    tone = "bright" if v > 170 else "dark" if v < 70 else "mid-toned"
    if s < 60:
        return tone
    for name, top in (("red", 15), ("orange", 45), ("yellow", 70), ("green", 165), ("cyan", 200), ("blue", 255), ("purple", 290), ("magenta", 335), ("red", 361)):
        if h <= top:
            return f"{tone} {name}"
    return tone


def direction_word(dx, dy):
    a = math.degrees(math.atan2(-dy, dx)) % 360
    names = ["right", "up-right", "up", "up-left", "left", "down-left", "down", "down-right"]
    return names[int(round(a / 45)) % 8]


def verb_for(dx, dy):
    word = direction_word(dx, dy)
    return {"up": "rises", "down": "falls"}.get(word, f"moves {word}")


def _bridge(scanned, a, b):
    """Steps that fall inside a held cadence: the motion hasn't stopped there, the picture just hasn't updated."""
    held = np.zeros(b - a, bool)
    mask = scanned["stepped_mask"]
    idx = np.flatnonzero(mask)
    if len(idx) >= 2:
        lo, hi = int(idx[0]), int(idx[-1])
        gap_ok = int(round(MAX_HOLD / max(float(np.median(np.diff(scanned["t"]))), 1e-6))) + 1
        last = None
        for i in idx.tolist():
            if last is not None and i - last <= gap_ok:
                x0, x1 = max(a, last), min(b, i + 1)
                if x1 > x0:
                    held[x0 - a:x1 - a] = True
            last = i
    return held


def track_model(tr, scanned, label):
    t, aw, ah, scale = scanned["t"], scanned["aw"], scanned["ah"], scanned["scale"]
    ia, ib = tr["idx"][0], tr["idx"][-1] + 1
    span = np.zeros((ib - ia, 2))
    coh = np.zeros(ib - ia)
    for i, r in zip(tr["idx"], tr["regs"]):
        span[i - ia] = (r.vx, r.vy)
        coh[i - ia] = r.coh
    times = t[ia - 1:ib]
    by_step = dict(zip(tr["idx"], tr["regs"]))
    for i in tr["idx"][1:]:    # where flow gives up on a fast thing, a box that keeps its size has really moved
        if i - 1 not in by_step:
            continue
        a, b = by_step[i - 1], by_step[i]
        wa, ha, wb, hb = a.x1 - a.x0, a.y1 - a.y0, b.x1 - b.x0, b.y1 - b.y0
        if max(wa, wb) == 0 or max(ha, hb) == 0 or abs(wa - wb) > 0.2 * max(wa, wb) or abs(ha - hb) > 0.2 * max(ha, hb):
            continue
        bx, by = (b.x0 + b.x1 - a.x0 - a.x1) / 2, (b.y0 + b.y1 - a.y0 - a.y1) / 2
        fx, fy = span[i - ia]
        if math.hypot(bx, by) > 10 and math.hypot(fx, fy) < 0.55 * math.hypot(bx, by):
            span[i - ia] = (bx, by)
    moves = moves_from(span, times, STEP_MIN, TRAVEL_MIN, 0.45, _bridge(scanned, ia, ib))
    boxes = np.array([(r.x0, r.y0, r.x1, r.y1) for r in tr["regs"]], float)
    w, h = np.median(boxes[:, 2] - boxes[:, 0]), np.median(boxes[:, 3] - boxes[:, 1])
    cx, cy = np.median((boxes[:, 0] + boxes[:, 2]) / 2), np.median((boxes[:, 1] + boxes[:, 3]) / 2)
    fills = [r.fill for r in tr["regs"]]
    colours = np.array([(r.b, r.g, r.r) for r in tr["regs"]], float)
    colour = np.median(colours, axis=0)
    out_moves = []
    centres = (boxes[:, :2] + boxes[:, 2:]) / 2
    for m in moves:
        k0 = int(np.searchsorted(tr["idx"], np.searchsorted(t, m["t0"]) - 1))
        k1 = min(len(boxes) - 1, int(np.searchsorted(tr["idx"], np.searchsorted(t, m["t1"]))))
        box_net = float(np.hypot(*(centres[k1] - centres[k0]))) if k1 > k0 else 0.0
        flow_net = float(math.hypot(m["dx"], m["dy"]))
        trust = "good"
        too_fast = m["peak_speed"] * float(np.median(np.diff(times))) > FAST
        if too_fast:
            trust = "too fast to follow"
        elif flow_net > 2 and box_net > 2 and not 0.7 < box_net / flow_net < 1.4:
            trust = "two estimates disagree"
        elif float(np.mean(coh[max(0, k0):max(k0 + 1, k1 + 1)])) < 0.45:
            trust = "motion inside it is mixed"
        out_moves.append({**m, "dx": m["dx"] * scale, "dy": m["dy"] * scale, "distance": m["distance"] * scale, "path": m["path"] * scale,
                          "peak_speed": m["peak_speed"] * scale, "start_speed": m["start_speed"] * scale, "end_speed": m["end_speed"] * scale, "overshoot": m["overshoot"] * scale, "box_net": box_net * scale, "trust": trust})
    dt = float(np.median(np.diff(times)))
    frame_w_src = aw * scale
    out_moves = [m for m in out_moves if m["t1"] - m["t0"] >= 2.5 * dt or m["distance"] >= 0.03 * frame_w_src]
    total_path = sum(m["path"] for m in out_moves)
    net = min(float(np.hypot(*(centres[-1] - centres[0]))) * scale, total_path)
    area_share = float(w * h / (aw * ah))
    churn = bool(out_moves) and (area_share >= 0.35 or (len(out_moves) >= 4 and net < 0.4 * total_path))
    return {"churn": churn, "path_total": total_path, "net_travel": net, "label": label, "first": ia - 1, "last": ib, "t0": float(t[ia - 1]), "t1": float(t[ib - 1]), "w": float(w * scale), "h": float(h * scale),
            "x": float(cx * scale), "y": float(cy * scale), "area_share": float(w * h / (aw * ah)), "where": place_word(cx, cy, aw, ah),
            "size": size_word(float(w * h / (aw * ah))), "colour": colour_word(*colour.astype(int), np.median(fills)),
            "seen_frames": len(tr["idx"]), "mean_coherence": float(np.mean(coh)), "moves": out_moves}


def camera_model(scanned, first, last):
    """Pan, push and roll for one shot: what the fits add up to, per step."""
    t, cams, aw, ah, scale = scanned["t"], scanned["cams"], scanned["aw"], scanned["ah"], scanned["scale"]
    n = last - first - 1
    if n <= 0:
        return {"state": "too short to read", "moves": [], "zooms": [], "wander": 0.0, "coverage": 0.0, "low_texture": False}
    pan, zoom, roll = np.zeros((n, 2)), np.zeros(n), np.zeros(n)
    known = np.zeros(n, bool)
    no_texture = 0
    cx, cy = (aw - 1) / 2, (ah - 1) / 2
    for k, i in enumerate(range(first + 1, last)):
        status, M, _, _ = cams[i]
        if status == "repeat":
            known[k] = True
            continue
        if status == "no_texture":
            no_texture += 1
        if M is None:
            continue
        known[k] = True
        M = np.array(M)
        s = math.hypot(M[0, 0], M[1, 0])
        zoom[k] = math.log(max(s, 1e-6))
        roll[k] = math.degrees(math.atan2(M[1, 0], M[0, 0]))
        pan[k] = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx, M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy)
    times = t[first:last]
    k = max(3, int(round(0.2 / max(float(np.median(np.diff(times))), 1e-6)))) | 1
    pan_smooth = np.column_stack([_box(pan[:, 0], k), _box(pan[:, 1], k)])
    moves = [m for m in moves_from(pan_smooth, times, 0.06, 2.0, 0.25, _bridge(scanned, first + 1, last)) if m["distance"] >= 0.015 * aw and m["t1"] - m["t0"] >= 0.2]
    zoom_v = np.column_stack([_box(zoom, k), np.zeros(n)])
    zooms = [z for z in moves_from(zoom_v, times, 0.00025, 0.008, 0.002) if z["t1"] - z["t0"] >= 0.2]
    out_zoom = []
    cum = np.exp(np.cumsum(zoom))
    for z in zooms:
        k0 = int(np.searchsorted(times, z["t0"]))
        k1 = min(n - 1, int(np.searchsorted(times, z["t1"])) - 1)
        from_s, to_s = float(cum[max(0, k0 - 1)]) if k0 > 0 else 1.0, float(cum[k1])
        out_zoom.append({**z, "from": from_s, "to": to_s})
    out_moves = [{**m, "dx": m["dx"] * scale, "dy": m["dy"] * scale, "distance": m["distance"] * scale, "path": m["path"] * scale, "peak_speed": m["peak_speed"] * scale, "start_speed": m["start_speed"] * scale, "end_speed": m["end_speed"] * scale} for m in moves]
    path = np.cumsum(pan, axis=0)
    wander = 0.0
    if len(path) >= 4:
        drift = np.linspace(path[0], path[-1], len(path))
        wander = float(np.percentile(np.hypot(*(path - drift).T), 95)) * scale
    coverage = float(known.mean())
    state = "unknown" if coverage < 0.5 else ("moving" if out_moves or out_zoom else "locked")
    return {"state": state, "moves": out_moves, "zooms": out_zoom, "wander": wander, "coverage": coverage, "low_texture": no_texture > 0.5 * n,
            "net_roll": float(np.sum(roll))}


def still_spans(scanned, first, last, tracks_model, cam):
    """Stretches with no movement at all, marked frame-identical or noise-only, with how they were entered and left."""
    t, e, regs = scanned["t"], scanned["e"], scanned["regs"]
    n = last - first
    quiet = np.zeros(n, bool)
    exact = np.zeros(n, bool)
    for i in range(first + 1, last):
        exact[i - first] = scanned["repeat"][i] > 0
        quiet[i - first] = exact[i - first] or (e[i] < QUIET and not [r for r in regs[i] if r.kind == 0])
    out, k = [], 1
    while k < n:
        if quiet[k]:
            j = k
            while j + 1 < n and quiet[j + 1]:
                j += 1
            t0, t1 = float(t[first + k - 1]), float(t[first + j])
            inside_steps = bool(scanned["stepped_mask"][first + k:first + j + 2].any())
            if t1 - t0 >= STILL_MIN and not (inside_steps and t1 - t0 <= MAX_HOLD + 0.05):
                frac = float(exact[k:j + 1].mean())
                kind = "frame-identical" if frac > 0.97 else "nothing moves, noise only" if frac < 0.3 else "nearly frame-identical"
                out.append({"t0": t0, "t1": t1, "dur": t1 - t0, "kind": kind, **_context(tracks_model, cam, t0, t1, scanned, first, last)})
            k = j + 1
        else:
            k += 1
    return out


def _context(things, cam, t0, t1, scanned, first, last):
    """Whether anything is at speed as this still begins and as it ends: a still that interrupts motion reads differently."""
    near = 0.14
    candidates = [(th["label"], m) for th in things for m in th["moves"]] + [("camera", m) for m in cam["moves"]]
    sound_before = {id(m): speed_is_sound(m) for _, m in candidates}
    entered = max(((m["end_speed"], who, sound_before[id(m)]) for who, m in candidates if t0 - near <= m["t1"] <= t0 + near and m["end_speed"] >= 0.5 * m["peak_speed"]), default=(0.0, None, False))
    left = max(((m["start_speed"], who, sound_before[id(m)]) for who, m in candidates if t1 - near <= m["t0"] <= t1 + near), default=(0.0, None, False))
    t, e = scanned["t"], scanned["e"]
    i0, i1 = int(np.searchsorted(t, t0)), int(np.searchsorted(t, t1))
    before = float(np.median(e[max(first + 1, i0 - 4):max(first + 2, i0)])) if i0 > first + 1 else 0.0
    after = float(np.median(e[min(last - 1, i1 + 1):min(last, i1 + 5)])) if i1 + 2 < last else 0.0
    step = float(e[i1 + 1]) if i1 + 1 < last else 0.0
    usual = float(np.median(e[max(first + 1, i0 - 12):max(first + 2, i0 - 1)])) if i0 > first + 2 else 0.0
    untracked = not candidates   # with nothing tracked, the only evidence of motion around the still is the change in the picture
    return {"entered_at_speed": entered[0] >= 40 or (untracked and before >= 1.0), "left_at_speed": left[0] >= 40 or (untracked and after >= 1.0), "speed_before": entered[0] if entered[2] else None, "speed_after": left[0] if left[2] else None,
            "who_before": entered[1], "who_after": left[1], "release_step": step, "usual_step": usual, "e_before": before, "e_after": after}


def cadence(scanned, shots):
    """How often the picture is really new, while something is moving: the film's norm, and where it departs from it."""
    t, e = scanned["t"], scanned["e"]
    n = scanned["n"]
    dt = float(np.median(np.diff(t)))
    win = max(4, int(round(0.5 / dt)))
    rep = scanned["repeat"] > 0
    baseline_shares, spans = [], []
    moving = e >= 0.35  # measure.py's MOVE, though there it is read at 320x180 and here at 480 px wide
    for shot in shots:
        a, b = shot["first"] + 1, shot["last"]
        if b - a < win:
            continue
        share = np.convolve(rep[a:b].astype(float), np.ones(win) / win, mode="same")
        movingness = np.convolve(moving[a:b].astype(float), np.ones(win) / win, mode="same")
        valid = movingness > 0.2
        baseline_shares.extend(share[valid].tolist())
    base = float(np.median(baseline_shares)) if baseline_shares else 0.0
    for shot in shots:
        a, b = shot["first"] + 1, shot["last"]
        if b - a < win:
            continue
        share = np.convolve(rep[a:b].astype(float), np.ones(win) / win, mode="same")
        movingness = np.convolve(moving[a:b].astype(float), np.ones(win) / win, mode="same")
        bad = (share >= max(base + 0.3, 0.3)) & (movingness > 0.12)
        k = 0
        while k < len(bad):
            if bad[k]:
                j = k
                while j + 1 < len(bad) and bad[j + 1]:
                    j += 1
                i0, i1 = a + k, a + j
                # trim to the frames that are actually repeats at each end
                while i0 < i1 and not rep[i0]:
                    i0 += 1
                while i1 > i0 and not rep[i1]:
                    i1 -= 1
                new_here = 1.0 - float(rep[i0:i1 + 1].mean())
                if t[i1] - t[i0] >= 0.15 and rep[i0:i1 + 1].sum() >= 3 and new_here >= 0.12 and (i1 + 1 < b and not rep[i1 + 1] or i1 + 1 >= b) and (i0 - 1 >= a and not rep[i0 - 1] or i0 - 1 < a):
                    runs, c, seen = [], 0, 0
                    for x in rep[i0:i1 + 1]:
                        if x:
                            c += 1
                        else:
                            if c:
                                runs.append(c + 1)
                            c = 0
                    if c:
                        runs.append(c + 1)
                    new_share = 1.0 - float(rep[i0:i1 + 1].mean())
                    spans.append({"t0": float(t[max(a, i0 - 1)]), "t1": float(t[i1]), "new_share": new_share, "holds": runs[:12], "shot": shot["id"]})
                k = j + 1
            else:
                k += 1
    label = "every frame is new" if base < 0.1 else (f"about {1 - base:.0%} of frames are new" if base < 0.9 else "most frames repeat")
    return {"base_repeat_share": base, "label": label}, spans


def colour_events(scanned, shots):
    """Sudden colour changes inside a shot: most of the picture's blocks change colour in one to three frames, and stay."""
    n, t = scanned["n"], scanned["t"]
    hue, hue_coh, sat = scanned["hue"], scanned["hue_coh"], scanned["sat"]
    frames = np.memmap(scanned["colour_blocks"], dtype=np.uint8, mode="r", shape=(n, 9, 16, 3)).astype(np.float32)
    frames[..., 0] /= 2.55
    dmag = np.zeros(n)
    for i in range(1, n):
        dmag[i] = float(np.median(np.linalg.norm(frames[i] - frames[i - 1], axis=2)))
    events = []
    for shot in shots:
        a, b = shot["first"] + 1, shot["last"]
        i = a
        while i < b:
            around = np.r_[dmag[max(a, i - 8):max(a, i - 1)], dmag[min(b, i + 2):min(b, i + 9)]]
            local = float(np.median(around)) if len(around) else 0.0
            around_hue = np.r_[hue[max(a, i - 8):max(a, i - 1)], hue[min(b, i + 2):min(b, i + 9)]]
            hue_step = abs(hue[i]) >= max(6.0, 4 * float(np.median(np.abs(around_hue)) if len(around_hue) else 0.0) + 2.0) and hue_coh[i] >= 0.75 and sat[i] >= 12
            if hue_step or (dmag[i] >= max(2.5, 3.0 * local + 0.8) and (i + 1 >= n or dmag[i + 1] < 0.75 * dmag[i] + 0.4)):
                j = i
                while j + 1 < min(b, i + 3) and dmag[j + 1] >= 0.6 * dmag[i]:
                    j += 1
                before = np.mean(frames[max(a - 1, i - 3):i], axis=0)
                after = np.mean(frames[j:min(b, j + 3)], axis=0)
                delta = after - before
                ab0, ab1 = before[..., 1:] - 128, after[..., 1:] - 128
                chroma = np.minimum(np.hypot(ab0[..., 0], ab0[..., 1]), np.hypot(ab1[..., 0], ab1[..., 1]))
                rot, rot_cons = 0.0, 0.0
                pick = chroma >= 8
                if pick.sum() >= 8:
                    c0, c1 = ab0[..., 0] + 1j * ab0[..., 1], ab1[..., 0] + 1j * ab1[..., 1]
                    z = c1[pick] / np.where(np.abs(c0[pick]) > 1e-6, c0[pick], 1)
                    u = z / np.maximum(np.abs(z), 1e-6)
                    mean = u.mean()
                    rot, rot_cons = float(np.degrees(np.angle(mean))), float(np.abs(mean))
                events.append({"t": float(t[i]), "t_end": float(t[j]), "dL": float(delta[..., 0].mean()), "da": float(delta[..., 1].mean()), "db": float(delta[..., 2].mean()),
                               "here": float(dmag[i:j + 1].max()), "size": max(float(dmag[i:j + 1].sum()), 2.5), "rotation": float(hue[i]) if hue_step else (rot if rot_cons >= 0.7 else 0.0), "shot": shot["id"], "first": i, "last": j})
                i = j + 3
            else:
                i += 1
    used = set()
    for k, ev in enumerate(events):
        if k in used:
            continue
        i0 = ev["first"]
        before = np.mean(frames[max(0, i0 - 3):i0], axis=0)
        for m in range(k + 1, len(events)):
            other = events[m]
            if other["shot"] != ev["shot"] or m in used:
                continue
            after = np.mean(frames[other["last"]:min(n, other["last"] + 3)], axis=0)
            opposite = ev["rotation"] * other["rotation"] < 0 and abs(ev["rotation"] + other["rotation"]) <= max(5.0, 0.5 * abs(ev["rotation"]))
            if opposite or float(np.median(np.linalg.norm(after - before, axis=2))) <= 0.45 * ev["size"]:
                ev["reverts_at"] = other["t"]
                other["revert_of"] = ev["t"]
                used.add(m)
                break
    usual = float(np.median(dmag[1:])) if n > 1 else 0.0
    for ev in events:
        ev["usual"] = usual
    return [e for e in events if "revert_of" not in e]


def colour_phrase(ev):
    words = []
    if abs(ev["rotation"]) >= 12:
        return f"shifts in hue by about {abs(ev['rotation']):.0f} degrees" + (" (brighter)" if ev["dL"] > 2.5 else " (darker)" if ev["dL"] < -2.5 else "")
    if abs(ev["dL"]) >= 1.5:
        words.append("brighter" if ev["dL"] > 0 else "darker")
    a, b = ev["da"], ev["db"]
    if abs(b) >= 1.5 or abs(a) >= 1.5:
        if abs(b) >= abs(a):
            words.append("warmer" if b > 0 else "cooler")
        else:
            words.append("towards magenta" if a > 0 else "towards green")
    return "turns " + " and ".join(words) if words else "changes colour balance"


def sharpness_events(scanned, shots, thumbs):
    """Sudden falls and returns of fine detail inside one unchanged picture."""
    t, d = scanned["t"], np.maximum(scanned["detail"], 1e-3)
    dt = float(np.median(np.diff(t)))
    win = max(4, int(round(0.25 / dt)))
    out = []
    for shot in shots:
        a, b = shot["first"], shot["last"]
        if b - a < 2 * win + 2:
            continue
        i = a + win
        while i < b - win:
            before, after = float(np.median(d[max(a, i - win):i])), float(np.median(d[i:i + win]))
            ratio = after / max(before, 1e-3)
            if ratio <= 0.62:
                # sharpen the edge to the frame where the fall actually happens
                k = i - win + int(np.argmin(np.diff(np.log(d[i - win:i + win]))))
                edge = k + 1
                after_frame = thumbs[min(b - 1, edge + 2)]
                same_picture = float(after_frame.std()) >= 6 and _ncc(_edges(thumbs[max(a, edge - 2)].astype(np.float32)), _edges(after_frame.astype(np.float32))) >= 0.75
                if same_picture and float(np.median(d[max(a, edge - win):edge])) / max(float(np.median(d[edge:edge + win])), 1e-3) >= 1.5:
                    j, recovered = edge + win, None
                    while j < b:
                        now = float(np.median(d[j:min(b, j + win)]))
                        if now >= 0.8 * before:
                            k2 = j - win + int(np.argmax(np.diff(np.log(d[max(a, j - win):min(b, j + win)]))))
                            recovered = max(edge + 1, k2 + 1)
                            break
                        j += 1
                    low = float(np.median(d[edge:(recovered if recovered else b)]))
                    fall_frames = int(np.sum(np.diff(np.log(d[max(a, edge - 4):edge + 3])) < -0.08))
                    out.append({"t": float(t[edge]), "t_end": float(t[recovered]) if recovered else None, "ratio": low / max(before, 1e-3), "sudden": fall_frames <= 3, "shot": shot["id"]})
                    i = (recovered if recovered else b) + win
                    continue
            i += 1
    return out


def mark_unexplained(shots, colours, sharp, scanned):
    """Flag whole-picture colour or sharpness changes that coincide with no cut and no movement, and compare each with the rest of the film."""
    t, aw, ah = scanned["t"], scanned["aw"], scanned["ah"]
    by_id = {s["id"]: s for s in shots}
    def nothing_at(ev, i0, i1):
        shot = by_id[ev["shot"]]
        if i0 - shot["first"] <= 3 or shot["last"] - 1 - i1 <= 3:
            return False
        at = float(t[i0])
        for m in [m for th in shot["things"] for m in th["moves"]] + shot["camera"]["moves"] + shot["camera"]["zooms"]:
            if m["t0"] - 0.1 <= at <= m["t1"] + 0.1:
                return False
        for i in range(max(shot["first"] + 1, i0 - 2), min(shot["last"], i1 + 3)):
            if sum(r.area for r in scanned["regs"][i] if r.kind == 0) >= 0.01 * aw * ah:
                return False
        return True
    for k, ev in enumerate(colours):
        ev["unexplained"] = nothing_at(ev, ev["first"], ev["last"])
        others = [o["size"] for j, o in enumerate(colours) if j != k]
        ev["others"] = len(others)
        ev["others_as_large"] = sum(x >= ev["size"] for x in others)
        ev["largest_other"] = max(others) if others else 0.0
    for k, ev in enumerate(sharp):
        i0 = int(np.searchsorted(t, ev["t"]))
        ev["unexplained"] = nothing_at(ev, i0, i0)
        ev["others"] = len(sharp) - 1
        ev["others_as_deep"] = sum(o["ratio"] <= ev["ratio"] for j, o in enumerate(sharp) if j != k)


def timecheck_findings(path, shots):
    """timecheck.py's own freeze and stutter findings, placed in the shots they fall in."""
    try:
        data = timecheck.scan(str(path))
        found = [f for f in timecheck.detect(data) if f["kind"] in ("freeze", "stutter")]
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        return {"ran": False, "error": str(exc)[:200], "findings": []}
    for f in found:
        f["shot"] = next((s["id"] for s in shots if s["t0"] <= f["start"] <= s["t1"]), None)
    return {"ran": True, "findings": found}


def shot_relations(things):
    """Who starts while whom is still on the way, and how long after."""
    moves = sorted(((th["label"], m) for th in things for m in th["moves"]), key=lambda x: x[1]["t0"])
    rels = []
    for k, (lab, m) in enumerate(moves[1:], start=1):
        prev = [(l, x) for l, x in moves[:k] if l != lab and x["t0"] <= m["t0"]]
        if not prev:
            continue
        flying = [(l, x) for l, x in prev if x["t1"] > m["t0"] + 1e-3]
        if flying:
            l, x = max(flying, key=lambda p: p[1]["t0"])
            prog = float(np.clip((m["t0"] - x["t0"]) / max(x["dur"], 1e-3), 0, 1))
            rels.append({"who": lab, "after": l, "lead": m["t0"] - x["t0"], "progress_of_other": prog, "overlap": True, "t": m["t0"]})
        else:
            l, x = max(prev, key=lambda p: p[1]["t1"])
            rels.append({"who": lab, "after": l, "lead": m["t0"] - x["t1"], "progress_of_other": 1.0, "overlap": False, "t": m["t0"]})
    return rels


def in_place_events(tracks, scanned):
    """Regions that change without moving: what happened, where, how big."""
    t, aw, ah = scanned["t"], scanned["aw"], scanned["ah"]
    out = []
    for tr in tracks:
        regs = tr["regs"]
        total = float(sum(abs(r.change) for r in regs))
        net = float(sum(r.change for r in regs))
        box = (min(r.x0 for r in regs), min(r.y0 for r in regs), max(r.x1 for r in regs), max(r.y1 for r in regs))
        area = (box[2] - box[0]) * (box[3] - box[1]) / (aw * ah)
        peak = max(r.area for r in regs)
        if area < 0.002 or total < 20 or peak < 60:
            continue
        ink0, ink1 = regs[0].ink0, regs[-1].ink1
        what = "appears" if ink1 - ink0 > 0.4 else "disappears" if ink0 - ink1 > 0.4 else "brightens" if net > 0.4 * total else "dims" if net < -0.4 * total else "flickers"
        i0 = tr["idx"][0]
        i1 = tr["idx"][-1]
        out.append({"t0": float(t[i0 - 1]), "t1": float(t[i1]), "dur": float(t[i1] - t[i0 - 1]), "what": what, "where": place_word((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, aw, ah),
                    "area_share": float(area), "size": size_word(float(area))})
    return out


def shot_activity(scanned, first, last):
    """How much of the picture is in motion, and when it peaks: the account for footage with no discrete movers."""
    t, aw, ah = scanned["t"], scanned["aw"], scanned["ah"]
    area = aw * ah
    shares = np.array([sum(r.area for r in scanned["regs"][i] if r.kind == 0) / area for i in range(first + 1, last)])
    if len(shares) < 3:
        return {"median": 0.0, "peak": 0.0, "peak_t": None, "bursts": []}
    k = max(3, int(round(0.2 / max(float(np.median(np.diff(t[first:last]))), 1e-6)))) | 1
    smooth = _box(shares, k)
    median = float(np.median(smooth))
    peak_k = int(np.argmax(smooth))
    bursts = []
    floor = max(0.01, 2 * median)
    for i in np.argsort(-smooth):
        if smooth[i] < floor or len(bursts) >= 5:
            break
        at = float(t[first + 1 + int(i)])
        if all(abs(at - b["t"]) > 0.4 for b in bursts):
            bursts.append({"t": at, "share": float(smooth[i])})
    bursts.sort(key=lambda b: b["t"])
    return {"median": median, "peak": float(smooth[peak_k]), "peak_t": float(t[first + 1 + peak_k]), "bursts": bursts}


def _pace(m):
    return f"{direction_word(m['ux'], m['uy'])} {m['speed']:.0f} px/s" if m["speed"] is not None else f"{direction_word(m['ux'], m['uy'])}, too fast to measure"


def carry_through(shots):
    """Whether the movement at a shot's end continues into the next shot's start."""
    for a, b in zip(shots, shots[1:]):
        out_v, in_v = a.get("exit_motion"), b.get("enter_motion")
        note = None
        if out_v and in_v:
            ang = abs((math.degrees(math.atan2(out_v["uy"], out_v["ux"])) - math.degrees(math.atan2(in_v["uy"], in_v["ux"])) + 180) % 360 - 180)
            ratio = max(out_v["speed"] or 0, 1e-6) / max(in_v["speed"] or 0, 1e-6) if out_v["speed"] and in_v["speed"] else 1.0
            if ang <= 45 and 0.5 <= ratio <= 2:
                note = "the previous movement carries through the cut"
            else:
                note = f"movement changes across the cut ({_pace(out_v)}, then {_pace(in_v)})"
        elif out_v and not in_v:
            note = f"cuts from movement ({_pace(out_v)}) to stillness"
        elif in_v and not out_v:
            note = f"cuts from stillness into movement ({_pace(in_v)})"
        b["carry"] = note


def speed_is_sound(m):
    """Only a move followed over several frames, inside what flow can follow, has a speed worth printing."""
    return m.get("trust", "good") in ("good", "two estimates disagree") and m["shape"] != "too short to shape" and m["t1"] - m["t0"] >= 0.1


def boundary_motion(shot, scanned):
    """The fastest motion a shot has within 3 frames of its start and end."""
    t = scanned["t"]
    first, last = shot["first"], shot["last"]
    near_a, near_b = float(t[first]) + 0.13, float(t[last - 1]) - 0.13
    enter, leave = None, None
    best_e = best_l = 0.0
    def consider(m, source):
        nonlocal enter, leave, best_e, best_l
        speed = m["peak_speed"]
        length = max(math.hypot(m["dx"], m["dy"]), 1e-6)
        shown = speed if speed_is_sound(m) else None    # direction survives where a number wouldn't mean anything
        step = {"ux": m["dx"] / length, "uy": m["dy"] / length, "speed": shown}
        if m["t0"] <= near_a and speed > best_e and speed > 40:
            best_e, enter = speed, step
        if m["t1"] >= near_b - 1e-3 and speed > best_l and speed > 40:
            best_l, leave = speed, step
    for th in shot["things"]:
        for m in th["moves"]:
            consider(m, th["label"])
    for m in shot["camera"]["moves"]:
        consider(m, "camera")
    shot["enter_motion"], shot["exit_motion"] = enter, leave


def similar_setups(shots, thumbs, t):
    """Later shots that return to an earlier picture."""
    mid = []
    for s in shots:
        k = (s["first"] + s["last"]) // 2
        mid.append(_edges(thumbs[k].astype(np.float32)))
    for j in range(1, len(shots)):
        best, score = None, 0.0
        for i in range(0, j):
            if shots[j]["first"] == shots[i]["last"]:   # the neighbour is a separate question: a jump says so itself
                continue
            c = _ncc(mid[i], mid[j])
            if c > score:
                best, score = i, c
        if best is not None and score >= 0.88:
            shots[j]["same_setup_as"] = {"shot": best + 1, "similarity": round(score, 2)}


def repeated_content(thumbs, shots, t):
    """Whether a shot's opening frames replay frames from earlier in the film."""
    n = len(thumbs)
    tiny = np.stack([cv2.resize(thumbs[i], (16, 9), interpolation=cv2.INTER_AREA) for i in range(n)]).astype(np.float32)
    out = []
    for s in shots:
        a, b = s["first"], s["last"]
        if a < 10 or b - a < 8:
            continue
        probe_idx = list(range(a, min(b, a + 24), 3))[:8]
        if len(probe_idx) < 4:
            continue
        probe_frames = tiny[probe_idx]
        if float(probe_frames.std(axis=0).mean()) < 1.0:   # a static picture matches itself anywhere
            continue
        hits = []
        limit = a - (probe_idx[-1] - a)
        if limit > 0:
            first_match = np.abs(tiny[:limit] - probe_frames[0]).mean(axis=(1, 2)) < 3.0
            for off in np.flatnonzero(first_match):
                idx = [int(off) + (p - a) for p in probe_idx]
                d = float(np.abs(tiny[idx] - probe_frames).mean())
                if d < 2.2:
                    hits.append((d, int(off)))
        if hits:
            d, off = min(hits)
            if a - off > 8:
                out.append({"shot": s["id"], "t": float(t[a]), "from_t": float(t[off]), "frames": len(probe_idx), "difference": round(d, 2)})
    return out


def fnum(x, digits=2):
    return f"{x:.{digits}f}"


def px(x):
    return f"{int(round(x))} px"


def share(x):
    return f"{100 * x:.0f}%"


def write_motion(path, model):
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(x) for x in o]
        if isinstance(o, (np.floating, float)):
            return round(float(o), 3)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o
    Path(path).write_text(json.dumps(clean(model), indent=1), encoding="utf-8")


def census_numbers(shots, scanned):
    """Film-wide counts for how alive and how varied its motion is."""
    t = scanned["t"]
    n = scanned["n"]
    dur = float(t[-1] - t[0] + (t[1] - t[0] if n > 1 else 0))
    frame_active = np.zeros(n, bool)
    frame_count = np.zeros(n, int)
    durations, shapes, moves_total = [], [], 0
    big, overlap_starts, starts = 0, 0, 0
    for s in shots:
        cam_moving = bool(s["camera"]["moves"] or s["camera"]["zooms"])
        for m in s["camera"]["moves"] + s["camera"]["zooms"]:
            i0, i1 = int(np.searchsorted(t, m["t0"])), int(np.searchsorted(t, m["t1"]))
            frame_active[i0:i1 + 1] = True
        for th in s["things"]:
            for m in th["moves"]:
                moves_total += 1
                durations.append(m["dur"])
                if m["shape"] != "too short to shape":
                    shapes.append(m["shape"])
                if th["area_share"] >= 0.08:
                    big += 1
                i0, i1 = int(np.searchsorted(t, m["t0"])), int(np.searchsorted(t, m["t1"]))
                frame_active[i0:i1 + 1] = True
                frame_count[i0:i1 + 1] += 1
        for r in s["relations"]:
            starts += 1
            overlap_starts += int(r["overlap"])
    stills = sum(x["dur"] for s in shots for x in s["stills"])
    identical = sum(x["dur"] for s in shots for x in s["stills"] if x["kind"] == "frame-identical")
    active_share = float(frame_active.mean())
    two = float((frame_count >= 2).sum()) / max(1, int((frame_count >= 1).sum()))
    d = np.array(durations) if durations else np.array([0.0])
    return {"duration": dur, "shots": len(shots), "moves": moves_total, "moves_per_10s": 10 * moves_total / max(dur, 1e-3),
            "moving_share": active_share, "two_or_more_share": two, "max_at_once": int(frame_count.max()) if n else 0,
            "still_seconds": stills, "frame_identical_seconds": identical, "starts_overlapping": overlap_starts, "starts": starts,
            "big_moves": big, "move_dur_p10": float(np.percentile(d, 10)), "move_dur_median": float(np.median(d)), "move_dur_p90": float(np.percentile(d, 90)),
            "shape_counts": {k: shapes.count(k) for k in sorted(set(shapes))},
            "distinct_durations": len({round(x / 0.05) for x in durations})}


def analyse(path, out):
    info = probe(path)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        scanned = scan(path, info, tmp)
        thumbs = load_thumbs(scanned)
        t = scanned["t"]
        n = scanned["n"]
        signals = cut_signals(thumbs)
        stepped, scanned["stepped_mask"] = stepped_stretches(scanned, thumbs, signals)
        cuts = find_cuts(signals, scanned["stepped_mask"])
        dissolves = find_dissolves(thumbs, cuts, t, scanned)
        shots_raw, flashes = build_shots(n, t, cuts, dissolves, thumbs)
        shots = []
        for k, s in enumerate(shots_raw, start=1):
            s["id"] = k
            shots.append(s)
        for s in shots:
            first, last = s["first"], s["last"]
            s["t0"], s["t1"] = float(t[first]), float(t[last - 1]) if last - 1 > first else float(t[first])
            s["dur"] = s["t1"] - s["t0"]
            cam = camera_model(scanned, first, last)
            s["camera"] = cam
            tracks_raw = link_tracks(scanned["regs"], t, first, last, 0)
            tracks = merge_rests(merge_parts(tracks_raw), scanned["scale"])
            ordered = sorted((tr for tr in tracks if len(tr["idx"]) >= 2), key=lambda tr: tr["idx"][0])
            things, churn = [], []
            labels = _letters()
            for tr in ordered:
                m = track_model(tr, scanned, "?")
                if not m["moves"]:
                    continue
                m["salience"] = m["area_share"] * m["path_total"]
                (churn if m["churn"] else things).append(m)
            things.sort(key=lambda x: x["moves"][0]["t0"])
            for th in things:
                th["label"] = next(labels)
            s["things"] = things
            s["churn"] = sorted(({k: c[k] for k in ("t0", "t1", "where", "size", "w", "h", "path_total", "net_travel", "area_share")} for c in churn), key=lambda c: -c["area_share"])
            s["activity"] = shot_activity(scanned, first, last)
            s["scattered"] = scattered_in_shot(scanned, first, last)
            s["relations"] = shot_relations(things)
            s["changes"] = in_place_events(link_tracks(scanned["regs"], t, first, last, 1), scanned)
            s["stills"] = still_spans(scanned, first, last, things, cam)
            boundary_motion(s, scanned)
        carry_through(shots)
        cad, stutters = cadence(scanned, shots)
        moving_frames = max(1, int((scanned["e"] >= 0.35).sum()))
        film_wide = sum(r["last"] - r["first"] for r in stepped) >= 0.6 * moving_frames and bool(stepped)
        if film_wide:
            cad["stepped_throughout"] = int(round(float(np.median([r["hold_frames"] for r in stepped]))))
        for s in shots:
            mine = [r for r in stepped if s["first"] <= (r["first"] + r["last"]) / 2 < s["last"]]
            s["stepped"] = [] if film_wide else mine
            s["cadence"] = [x for x in stutters if x["shot"] == s["id"] and not any(x["t0"] <= r["t1"] and x["t1"] >= r["t0"] for r in stepped)]
        colours = colour_events(scanned, shots)
        sharp = sharpness_events(scanned, shots, thumbs)
        mark_unexplained(shots, colours, sharp, scanned)
        for s in shots:
            s["colour"] = [c for c in colours if c["shot"] == s["id"]]
            s["sharpness"] = [c for c in sharp if c["shot"] == s["id"]]
            d = scanned["detail"][s["first"]:s["last"]]
            s["detail"] = float(np.median(d))
        film_detail = float(np.median(scanned["detail"]))
        for s in shots:
            s["detail_vs_film"] = s["detail"] / max(film_detail, 1e-6)
        similar_setups(shots, thumbs, t)
        repeats = repeated_content(thumbs, shots, t)
        census = census_numbers(shots, scanned)
        del thumbs
    model = {"version": VERSION, "film": {"name": Path(path).name, **info, "frames_read": n, "analysis": {"aw": scanned["aw"], "ah": scanned["ah"]}}, "census": census, "timecheck": timecheck_findings(path, shots),
             "cadence": cad, "flashes": flashes, "repeats": repeats, "shots": [_shot_public(s) for s in shots]}
    Path(out).mkdir(parents=True, exist_ok=True)
    write_motion(Path(out) / "motion.json", model)
    (Path(out) / "SEE.md").write_text(transcript(model), encoding="utf-8")
    return model


def _letters():
    k = 0
    while True:
        k += 1
        if k <= 26:
            yield chr(64 + k)
        else:
            yield f"Z{k - 26}"


def _shot_public(s):
    keys = ("id", "t0", "t1", "dur", "first", "last", "camera", "things", "churn", "activity", "scattered", "stepped", "relations", "changes", "stills", "cadence", "colour", "sharpness", "detail_vs_film", "same_setup_as", "carry", "enter_motion", "exit_motion", "in")
    out = {k: s.get(k) for k in keys if s.get(k) is not None}
    out["join"] = {k: s["in"][k] for k in ("kind", "first", "last", "count") if k in s["in"]}
    out.pop("in", None)
    return out


JOIN_WORDS = {"flurry": "a fast whole-picture change over several frames", "fade_through": "fades through blank", "cut": "hard cut in", "jump": "jump cut in (most of the picture is unchanged)", "dissolve": "dissolve in", "fade_in": "fades in", "fade_out": "fades out", "start": "opens the film"}


def transcript(model):
    """Budgeted text: the plan is to fit a 60-second film in a few hundred lines, dropping the smallest movers first."""
    duration = model["census"]["duration"]
    limit = int(min(400, 60 + 5 * duration))
    for most in (8, 6, 4, 3, 2):
        for moves_each in (4, 3, 2):
            lines = _text(model, most, moves_each)
            if len(lines) <= limit:
                return "\n".join(lines) + "\n"
    lines = _text(model, 2, 1, compact=True)
    return "\n".join(lines) + "\n"


def _text(model, most, moves_each, compact=False):
    film, cen = model["film"], model["census"]
    lines = [f"# Motion transcript: {film['name']}", ""]
    every = [m for s in model["shots"] for th in s["things"] for m in th["moves"]]
    per_line = sum(m["trust"] != "good" for m in every) <= 0.5 * len(every)   # when most are estimates, one line at the top says so
    lines.append(f"Film: {cen['duration']:.1f} s, {film['w']}x{film['h']}, {film['fps']:.2f} fps, {film['frames_read']} frames read.")
    lines.append("How to read this: distances are in the film's own pixels; up, down, left and right mean on screen. A region is whatever moves together; nothing is named because nothing is recognised. \"About\" marks a number the two ways of measuring it disagree on. A thing's size is the box its moving edges enclose. Sound, meaning and what the picture shows are not read.")
    lines.append("")
    lines.append("## Whole film")
    lines += _census_lines(model)
    lines.append("")
    lines += _timecheck_lines(model)
    lines.append("")
    lines.append("## Shots")
    for s in model["shots"]:
        if not compact:
            lines.append("")
        lines += _compact_shot(s, film, per_line) if compact else _shot_lines(s, film, most, moves_each, per_line)
    return lines


def _compact_shot(s, film, per_line=True):
    """One or two lines for one shot, for films with so many shots that the full form won't fit."""
    full = _shot_lines(s, film, 2, 1, per_line)
    notable = [x for x in full[1:] if x.startswith(("- Still", "- Repeated", "- Stepped", "- Colour", "- Sharpness", "- Sudden", "- Scattered", "Returns", "Fine detail"))]
    movers = [x for x in full if x.startswith("- A:") or x.startswith("  - ")][:2]
    return [full[0] + " " + " ".join(x.strip() for x in full[1:2])] + movers + notable


def _timecheck_lines(model):
    tc = model.get("timecheck") or {}
    out = ["## Findings from timecheck.py (a separate check of the picture, for freezes and stutters)"]
    if not tc.get("ran"):
        out.append(f"- timecheck.py could not read this film: {tc.get('error', 'no reason given')}.")
    elif not tc["findings"]:
        out.append("- timecheck.py reports no freeze and no stutter.")
    for f in tc.get("findings", []):
        where = f" (shot {f['shot']})" if f.get("shot") else ""
        out.append(f"- timecheck.py {f['kind']}: {f['start']:.2f} to {f['end']:.2f} s{where}. {f['reason']}")
    return out


def _census_lines(model):
    c, film, cad, shots = model["census"], model["film"], model["cadence"], model["shots"]
    kinds = {}
    for s in shots[1:]:
        kinds[s["join"].get("kind", "cut")] = kinds.get(s["join"].get("kind", "cut"), 0) + 1
    lengths = [s["dur"] for s in shots]
    joins = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in kinds.items()) or "none"
    out = [f"- {len(shots)} shots, joined by: {joins}. Shot length: median {float(np.median(lengths)):.2f} s, longest {max(lengths):.2f} s, shortest {min(lengths):.2f} s."]
    out.append(f"- Something moves in {100 * c['moving_share']:.0f}% of the film. Moves counted: {c['moves']} ({c['moves_per_10s']:.1f} per 10 s), {c['big_moves']} by large things (8% of frame or more).")
    out.append(f"- When anything moves, two or more things move together {100 * c['two_or_more_share']:.0f}% of the time (most at once: {c['max_at_once']}). {c['starts_overlapping']} of {c['starts']} later starts begin before another thing has arrived.")
    if c["moves"]:
        shape = ", ".join(f"{v} {k}" for k, v in sorted(c["shape_counts"].items(), key=lambda x: -x[1]))
        out.append(f"- Move lengths: 10th percentile {c['move_dur_p10']:.2f} s, median {c['move_dur_median']:.2f} s, 90th percentile {c['move_dur_p90']:.2f} s; {c['distinct_durations']} distinct lengths to the nearest 0.05 s. Shapes: {shape}.")
    out.append(f"- Truly still (nothing moving): {c['still_seconds']:.1f} s, of which frame-identical {c['frame_identical_seconds']:.1f} s.")
    out.append(f"- Frame cadence while moving: {cad['label']}." + (f" The picture updates in steps of {cad['stepped_throughout']} frames right across the film." if cad.get("stepped_throughout") else ""))
    stretches = sum(len(s.get("stepped") or []) for s in shots)
    if stretches:
        out.append(f"- Stepped motion (a picture held for several frames, then jumping on) in {stretches} stretch{'es' if stretches != 1 else ''} of the film, listed in their shots.")
    doubt = sum(m["trust"] != "good" for s in shots for th in s["things"] for m in th["moves"])
    blind = sum(s["camera"]["state"] == "unknown" for s in shots)
    if doubt > 0.5 * c["moves"] and c["moves"]:
        out.append(f"- Precision: {doubt} of {c['moves']} moves in this film could only be estimated, so read every distance and speed below as approximate.")
    elif doubt:
        out.append(f"- Precision: {doubt} of {c['moves']} moves are marked \"about\".")
    if blind:
        out.append(f"- The camera couldn't be read in {blind} of {len(shots)} shots.")
    for fl in model["flashes"]:
        out.append(f"- One-off: at {fl['t']:.2f} s, {fl['frames']} frame(s) of a different picture between two matching ones.")
    for r in model["repeats"]:
        out.append(f"- Shot {r['shot']} opens at {r['t']:.2f} s with frames that match the film from {r['from_t']:.2f} s (mean difference {r['difference']}).")
    return out


def _shot_lines(s, film, most, moves_each, per_line=True):
    H, W = film["h"], film["w"]
    join = s.get("join", {})
    head = f"### Shot {s['id']}: {s['t0']:.2f} to {s['t1']:.2f} s ({s['dur']:.2f} s), {JOIN_WORDS.get(join.get('kind', 'cut'), join.get('kind', 'cut'))}"
    if join.get("kind") == "flurry":
        head += f" ({join.get('last', 0) - join.get('first', 0) + 1} frames)"
    if join.get("kind") in ("dissolve", "fade_in", "fade_out", "fade_through") and join.get("last", 0) > join.get("first", 0):
        head = head.replace(" in", " in", 1)
    if s.get("carry"):
        head += f"; {s['carry']}"
    out = [head + "."]
    if s.get("same_setup_as"):
        out.append(f"Returns to the picture of shot {s['same_setup_as']['shot']} (edge match {s['same_setup_as']['similarity']}).")
    if s.get("detail_vs_film") and (s["detail_vs_film"] < 0.55 or s["detail_vs_film"] > 1.8):
        out.append(f"Fine detail is {s['detail_vs_film']:.2f} times the film's usual level across this shot.")
    out.append("Camera: " + _camera_text(s["camera"], W, H))
    act = s.get("activity") or {}
    if act.get("peak", 0) >= 0.005:
        bursts = ", ".join(f"{b['t']:.2f} s ({100 * b['share']:.0f}%)" for b in act["bursts"]) or "none stand out"
        out.append(f"Activity: moving pixels are a median {100 * act['median']:.1f}% of the frame, peak {100 * act['peak']:.0f}% at {act['peak_t']:.2f} s. Bursts at: {bursts}.")
    things = sorted(s["things"], key=lambda x: -x["salience"])
    shown = sorted(things[:most], key=lambda x: x["moves"][0]["t0"])
    hidden = things[most:]
    n = len(things)
    if n:
        most_at_once = _max_overlap(s["things"])
        count = f" (at most {most_at_once} at once)" if n > 1 else ""
        out.append(f"{_count_word(n)} move" + ("s" if n == 1 else "") + (f" (the {most} largest are described)" if hidden else "") + count + ":")
    else:
        out.append("Nothing tracks as moving by itself.")
    for th in shown:
        out += _thing_lines(th, W, H, moves_each, per_line)
    for c in (s.get("churn") or [])[:2]:
        out.append(f"- Churn, no single direction: a {c['size']} region at {c['where']}, about {100 * c['w'] / W:.0f}% wide by {100 * c['h'] / H:.0f}% tall, {c['t0']:.2f} to {c['t1']:.2f} s (moves {int(round(c['path_total']))} px in all, ends {int(round(c['net_travel']))} px from where it started).")
    if hidden:
        out.append(f"- Plus {len(hidden)} smaller movers, biggest {max(x['area_share'] for x in hidden) * 100:.1f}% of the frame, starting from {min(x['moves'][0]['t0'] for x in hidden):.2f} s to {max(x['moves'][0]['t0'] for x in hidden):.2f} s.")
    rel_labels = {th["label"] for th in shown}
    rels = [r for r in s["relations"] if r["who"] in rel_labels and r["after"] in rel_labels]
    for r in rels[:max(4, most)]:
        if r["overlap"]:
            out.append(f"- {r['who']} starts {r['lead']:.2f} s after {r['after']} began, with {r['after']} {100 * r['progress_of_other']:.0f}% through its time.")
        elif r["lead"] <= 1.0:
            out.append(f"- {r['who']} starts {r['lead']:.2f} s after {r['after']} arrives.")
    for c in sorted(s["changes"], key=lambda x: -x["area_share"])[:3]:
        out.append(f"- In place, not moving: a {c['size']} region at {c['where']} {c['what']} from {c['t0']:.2f} to {c['t1']:.2f} s ({c['dur']:.2f} s), {100 * c['area_share']:.0f}% of the frame.")
    for x in s["stills"]:
        out.append("- " + _still_text(x))
    sc = s.get("scattered")
    if sc:
        kind = "travelling in their own directions" if sc["travelling"] >= 0.5 else "mostly changing in place"
        out.append(f"- Scattered small things: about {sc['count']} at a time (between {sc['count_low']} and {sc['count_high']}), each roughly {max(1, int(round(sc['size_px'])))} px across, spread over {sc['cells']} of 24 parts of the frame, {kind}, {sc['t0']:.2f} to {sc['t1']:.2f} s.")
    for x in s.get("stepped") or []:
        out.append(f"- Stepped motion: {x['t0']:.2f} to {x['t1']:.2f} s, one new picture every {x['hold_frames']} frames ({x['hold_s']:.2f} s), {x['steps']} steps, each picture held still in between.")
    for x in s["cadence"]:
        holds = ", ".join(str(v) for v in x["holds"][:10])
        out.append(f"- Repeated frames: {x['t0']:.2f} to {x['t1']:.2f} s, only {100 * x['new_share']:.0f}% of frames are new" + (f" (each picture held for {holds} frames)" if holds else "") + ".")
    for x in s["colour"]:
        rev = f", changing back at {x['reverts_at']:.2f} s" if x.get("reverts_at") else ", and it stays that way"
        out.append(f"- Colour: at {x['t']:.2f} s the whole picture {colour_phrase(x)} in {_frames_phrase(x)}{rev}. Mean change: brightness {x['dL']:+.1f}, red-green {x['da']:+.1f}, yellow-blue {x['db']:+.1f}.")
        if x.get("unexplained"):
            out.append("- " + _sudden_colour(x))
    for x in s["sharpness"]:
        back = f", returning at {x['t_end']:.2f} s" if x.get("t_end") else ", and it doesn't recover before the shot ends"
        speed = "suddenly" if x["sudden"] else "over several frames"
        out.append(f"- Sharpness: at {x['t']:.2f} s fine detail falls to {x['ratio'] * 100:.0f}% of what it was, {speed}{back}.")
        if x.get("unexplained"):
            out.append("- " + _sudden_sharpness(x))
    return out


def _sudden_colour(x):
    rest = "It is the only sudden whole-picture colour change in this film." if not x["others"] else f"This film has {x['others']} other sudden whole-picture colour change{'s' if x['others'] != 1 else ''}, {x['others_as_large']} of them at least this large."
    return f"Sudden whole-picture change at {x['t']:.2f} s, with no cut and nothing moving at that moment: the colour of the frame changes by {x['here']:.1f}, where it usually changes by {x['usual']:.1f} from one frame to the next. {rest}"


def _sudden_sharpness(x):
    rest = "It is the only sudden whole-picture sharpness change in this film." if not x["others"] else f"This film has {x['others']} other sudden whole-picture sharpness change{'s' if x['others'] != 1 else ''}, {x['others_as_deep']} of them at least this deep."
    return f"Sudden whole-picture change at {x['t']:.2f} s, with no cut and nothing moving at that moment: fine detail falls to {x['ratio'] * 100:.0f}% of the level just before. {rest}"


def _max_overlap(things):
    spans = [(m["t0"], m["t1"]) for th in things for m in th["moves"]]
    points = sorted([(a, 1) for a, _ in spans] + [(b, -1) for _, b in spans], key=lambda x: (x[0], -x[1]))
    now = best = 0
    for _, d in points:
        now += d
        best = max(best, now)
    return best


def _frames_phrase(x):
    return "one frame" if x["t_end"] == x["t"] else f"{x['t_end'] - x['t'] + 1 / 30:.2f} s"


def _count_word(n):
    words = ["Nothing", "One thing", "Two things", "Three things", "Four things", "Five things", "Six things", "Seven things", "Eight things"]
    return words[n] if n < len(words) else f"{n} things"


def _camera_text(cam, W, H):
    if cam["state"] == "too short to read":
        return "too short to read."
    if cam["state"] == "unknown":
        return "can't tell: frame-wide motion doesn't fit one camera move."
    bits = []
    for z in cam["zooms"]:
        verb = "pushes in" if z["to"] >= z["from"] else "pulls out"
        bits.append(f"{verb} {z['from']:.2f} to {z['to']:.2f}, {_shape_phrase(z)}, {z['t0']:.2f} to {z['t1']:.2f} s, peak at {z['peak_at']:.2f} s")
    ranked = sorted(cam["moves"], key=lambda m: -m["distance"])
    for m in sorted(ranked[:3], key=lambda m: m["t0"]):
        bits.append(f"pans {direction_word(m['dx'], m['dy'])} {px(m['distance'])} ({100 * m['distance'] / W:.0f}% of the frame width), {_shape_phrase(m)}, {m['t0']:.2f} to {m['t1']:.2f} s, peak at {m['peak_at']:.2f} s")
    if bits:
        return "; ".join(bits) + (f"; {len(ranked) - 3} smaller camera moves as well" if len(ranked) > 3 else "") + "."
    if cam["low_texture"]:
        return "no texture to measure against, treated as locked."
    if cam["wander"] > 4:
        return f"locked off with small wander (about {cam['wander']:.0f} px)."
    return "locked."


def _shape_phrase(m):
    s = m["shape"]
    if s == "decelerates":
        return "decelerates hard" if m["t50"] < 0.28 else "decelerates"
    if s == "accelerates":
        return "accelerates hard" if m["t50"] > 0.72 else "accelerates"
    return s


def _thing_lines(th, W, H, moves_each, per_line=True):
    head = f"- {th['label']}: a {th['size']} {th['colour']} region, {th['where']}, about {100 * th['w'] / W:.0f}% wide by {100 * th['h'] / H:.0f}% tall."
    moves = th["moves"]
    out = [head]
    for m in moves[:moves_each]:
        verb = verb_for(m["dx"], m["dy"])
        share_line = 100 * m["distance"] / (H if abs(m["dy"]) >= abs(m["dx"]) else W)
        too_fast = m["trust"] == "too fast to follow"
        dist = px(round(m["distance"] / 50) * 50) if too_fast else px(m["distance"])
        approx = "about " if m["trust"] != "good" and per_line else ""
        line = f"  - {m['t0']:.2f} to {m['t1']:.2f} s: {verb} {approx}{dist} ({share_line:.0f}% of the frame), {_shape_phrase(m)}"
        if not too_fast:
            if speed_is_sound(m):
                line += f", peak speed {int(round(m['peak_speed']))} px/s at {m['peak_at']:.2f} s"
            if m["overshoot"]:
                line += f", overshoots {int(round(m['overshoot']))} px at {m['overshoot_at']:.2f} s"
            if m["settled"]:
                line += f", settled by {m['settled']:.2f} s"
        if m["straight"] < 0.9:
            line += ", on a curved path"
        if m["trust"] != "good" and per_line:
            line += f" ({m['trust']})"
        out.append(line + ".")
    if len(moves) > moves_each:
        out.append(f"  - {len(moves) - moves_each} more moves until {moves[-1]['t1']:.2f} s.")
    return out


def _still_text(x):
    if x["entered_at_speed"]:
        who = (f"{x['who_before']} at {int(round(x['speed_before']))} px/s" if x.get("speed_before") else f"{x['who_before']} still going") if x.get("who_before") else f"picture changing {x['e_before']:.1f} levels a frame"
        lead = f" reached without slowing ({who} the frame before)"
    else:
        lead = " entered from rest"
    if x["left_at_speed"]:
        who = (f"{x['who_after']} at {int(round(x['speed_after']))} px/s" if x.get("speed_after") else f"{x['who_after']} already going") if x.get("who_after") else f"picture changing {x['e_after']:.1f} levels a frame"
        tail = f" and left at speed ({who} the frame after)"
    else:
        tail = ""
    jump = ""
    if x.get("release_step", 0) >= max(2.0, 3 * x.get("usual_step", 0) + 1.0) and x.get("release_step", 0) >= 3 * x.get("e_after", 0):
        jump = f" On release the picture jumps in one frame (change of {x['release_step']:.1f} levels against {x.get('usual_step', 0):.1f} usually)."
    return f"Still from {x['t0']:.2f} to {x['t1']:.2f} s ({x['dur']:.2f} s), {x['kind']};{lead}{tail}.{jump}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("film")
    ap.add_argument("--out", required=True, help="folder to hold motion.json and SEE.md")
    args = ap.parse_args()
    if int(cv2.__version__.split(".")[0]) >= 5:             # its optical flow reads fast and faint moves differently from OpenCV 4's
        print(f"warning: this is OpenCV {cv2.__version__}. The distances this tool reports were checked on OpenCV 4, and on 5.0.0 it gets fast and faint moves wrong. "
              "Installing the skill's requirements.txt puts 4 back.", file=sys.stderr)
    model = analyse(args.film, args.out)
    c = model["census"]
    lines = (Path(args.out) / "SEE.md").read_text(encoding="utf-8").count("\n")
    print(f"{model['film']['name']}: {c['duration']:.1f} s, {c['shots']} shots, {c['moves']} moves, {100 * c['moving_share']:.0f}% moving; {lines} transcript lines -> {args.out}")


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
