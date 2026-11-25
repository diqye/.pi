#!/usr/bin/env python3
"""How a film moves: as a scene does, or as a page does.

  python space.py FILM.mp4 [FILM.mp4 ...]

When a page moves, one flat sheet slides or zooms, or one thing moves over a still ground. When a scene moves, most of
the picture moves and no single slide or zoom explains it: near things pass far ones, several things travel at their
own rates, the view goes somewhere. This reads which of the two a film does, from its pixels, so it works on any film.

  scene_move   share of the film in which most of the picture moves and no one slide or zoom of a flat sheet explains it
  sheet_move   share of the film in which most of the picture moves and one does: the whole picture is a sheet being slid

Why it exists. Three films made by fresh agents with this skill read 0.01, 0.03 and 0.05 for scene_move, with 14 to 24
per cent of their length spent sliding a sheet, and every blind reader called them flat. The one film this skill made
that a person called finished read 0.05 at the cut they called flat and 0.31 at the next, with not one word or cue
changed between them. Of 83 launch films by studios, taken from a public list of them, 64 read 0.13 or more (the
middle one 0.21) and 16 read 0.1 or less. Among those 16 are films by some of the best-known teams, built on type and
the product's own screens. So a low reading is a question, not a fault: is this film quiet because someone chose that,
or because it was laid out as a page?

How. Twelve times a second, at 360 px high: corners in one picture are followed into the next, and each follow is checked
by following it back. When at least six in ten moved, one slide-turn-and-zoom is fitted to all of them. If a quarter of
the points sit further than 0.7 px from where that fit puts them, the move is a scene's.

What it can't see: a film with too few corners to follow (soft gradients, heavy blur) is not read, and `readable` says
how much was. A busy flat film, many things flying on one sheet, reads as a scene. Motion blur lifts a flat film's
reading by about 0.02. It reads how a film moves, and nothing about whether a move had a reason.
"""
import json
import subprocess
import sys

import cv2
import numpy as np

HIGH, FPS = 360, 12
MOST, MOVED, LEAST = 0.6, 0.6, 0.8   # most of the points; a point has moved past this many px; and the usual move is at least this
APART = 0.7                          # px, at 360 high: a quarter of the points this far from the one flat fit, and it isn't flat
SCENE = 0.1                          # the three agents' films read 0.05 at most (0.08 with motion blur), 64 of 83 studio films 0.13 or more
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def size(path):
    """The film's width and height in px, or a refusal in words."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        w, h = (int(v) for v in r.stdout.strip().split(",")[:2])
    except ValueError:
        raise SystemExit(f"{path}: can't read its size ({r.stderr.strip()[-200:] or 'ffprobe said nothing'})")
    return w, h


def frames(path, fps=FPS):
    """Grey pictures of the film, `fps` a second (every frame when None), HIGH px high at the film's own shape. Stops by
    itself at the end."""
    w, h = size(path)
    wide = max(2, int(round(w * HIGH / h / 2)) * 2)
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", (f"fps={fps}," if fps else "") + f"scale={wide}:{HIGH}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    try:
        while True:
            raw = p.stdout.read(wide * HIGH)
            if len(raw) < wide * HIGH:
                break
            yield np.frombuffer(raw, np.uint8).reshape(HIGH, wide)
    finally:
        # ffmpeg stops on the closed pipe and is waited for, killed only if it doesn't: killed at once, a launcher
        # (Chocolatey's ffmpeg) died and left the real ffmpeg holding the film (a council's finding; film_diff.stop_decoder)
        p.stdout.close()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()


def follow(a, b, corners=400, levels=3, least=0):
    """Corners of picture `a` followed into picture `b`: where the ones that came back to the same place when followed
    back again were, where they went, and how many corners there were. Fewer than `least` corners, and none is followed."""
    pts = cv2.goodFeaturesToTrack(a, maxCorners=corners, qualityLevel=0.01, minDistance=7)
    if pts is None or len(pts) < least:
        return np.zeros((0, 2), np.float32), np.zeros((0, 2), np.float32), 0 if pts is None else len(pts)
    nxt, ok, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, winSize=(21, 21), maxLevel=levels)
    back, ok2, _ = cv2.calcOpticalFlowPyrLK(b, a, nxt, None, winSize=(21, 21), maxLevel=levels)
    good = (ok.ravel() == 1) & (ok2.ravel() == 1) & (np.linalg.norm((back - pts).reshape(-1, 2), axis=1) < 1.0)  # followed there and back to the same place
    return pts.reshape(-1, 2)[good], nxt.reshape(-1, 2)[good], len(pts)


def pair(a, b):
    """What happened between two pictures: None when there is too little to follow, "still" when most of it stayed put,
    "sheet" when one slide, turn and zoom explains what moved, "scene" when it doesn't."""
    p0, p1, found = follow(a, b, least=40)
    if found < 40 or len(p0) < 40:
        return None
    move = np.linalg.norm(p1 - p0, axis=1)
    if (move > MOVED).mean() < MOST or np.median(move) < LEAST:
        return "still"
    fit, _ = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=1.5)
    if fit is None:
        return "scene"
    off = np.linalg.norm((fit[:, :2] @ p0.T).T + fit[:, 2] - p1, axis=1)
    return "scene" if np.percentile(off, 75) >= APART else "sheet"   # a quarter of the picture, so one thing moving by itself on a sliding sheet isn't a scene


# How far things travel from one frame to the next, for the shutter (vd.py `shoot`), which gives a fast frame more pictures
FAST = 95          # the percentile of the distances: one fast thing on a still picture is a fast frame, and a few corners followed wrong are not
FOLLOWED = 0.05    # under one corner in twenty followed, or under four corners, and nothing could be followed: a cut, which is not motion
LEVELS = 4         # the follow's pyramid: at 360 px high it follows a move of some 160 px a frame, about 480 px at 1080


def travel(path):
    """How far things travel from each frame of the film to the next, in px at the film's own size, one number a frame:
    the 95th percentile of how far its corners went. Corners are followed both ways, from each picture into the next and
    from the next back into it, so a card rising out of the top of the picture, whose corners leave it, is still read
    by the corners of the picture it rose into. None where almost nothing could be followed, as across a cut. The last
    frame has no next one, so it takes the move into it.

    Why both ways: followed one way only, the frames of a card rising out of a film's picture at 100 to 160 px a frame
    read as cuts (2 to 30 per cent of corners followed), and would have kept the fewest pictures where they need most."""
    scale = size(path)[1] / HIGH
    out, prev = [], None
    for f in frames(path, fps=None):
        if prev is not None:
            moved, found = [], 0
            for a, b in ((prev, f), (f, prev)):
                p0, p1, n = follow(a, b, corners=1000, levels=LEVELS)
                moved.append(np.linalg.norm(p1 - p0, axis=1))
                found += n
            moved = np.concatenate(moved)
            out.append(None if len(moved) < 4 or len(moved) < FOLLOWED * found else round(float(np.percentile(moved, FAST)) * scale, 1))
        prev = f
    if prev is not None:
        out.append(out[-1] if out else None)
    return out


def read(path):
    """{"scene_move", "sheet_move", "readable"}: shares of the film's length. The first two are None when under four in
    ten of its pictures had enough to follow, since a share of what couldn't be read isn't a measurement."""
    cv2.setRNGSeed(0)   # the fit draws its samples from OpenCV's own generator: the same film reads the same twice
    prev, found = None, []
    for f in frames(path):
        if prev is not None:
            found.append(pair(prev, f))
        prev = f
    n = len(found)
    readable = sum(x is not None for x in found) / n if n else 0.0
    if n < 6 or readable < 0.4:
        return {"scene_move": None, "sheet_move": None, "readable": round(readable, 2)}
    return {"scene_move": round(found.count("scene") / n, 3), "sheet_move": round(found.count("sheet") / n, 3), "readable": round(readable, 2)}


def says(r):
    if r["scene_move"] is None:
        return f"too little in its pictures to follow ({r['readable']:.0%} of them could be read), so how it moves wasn't measured"
    return (f"for {r['scene_move']:.0%} of it most of the picture moves and no one slide or zoom explains it (a scene), "
            f"and for {r['sheet_move']:.0%} the whole picture slides or zooms as one flat sheet (a page)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    out = {}
    for path in sys.argv[1:]:
        out[path] = read(path)
        print(f"{path}: {says(out[path])}")
    if len(out) > 1:
        print(json.dumps(out))


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
