#!/usr/bin/env python3
"""What to fix in a finished film before anyone watches it: frames that pop, stretches that stand still, and the level.

  python scan.py FILM.mp4 [-o scan.txt]           (vd export runs it on every export; `vd scan FILM.mp4` alone)

Pops: a frame whose change from the one before is far larger than the change on either side of it (over FLOOR, and
TIMES the larger neighbour), an earlier rule; and a one-frame flash, which that rule cannot see (the
change into the flash and out of it are both large, so neither is TIMES its neighbour): a frame that differs from both
its neighbours by that much while they agree with each other. Holds: every stretch of 0.5 s or more in which no frame
differs from the one before by more than 0.35 (stills.py's rule), in seconds at the film's own rate. Change is the mean
absolute difference between frames, grey, 0 to 255, at 480 x 270, and the film is decoded once for both. Loudness:
integrated LUFS and true peak of the sound (lean.loudness, what vd sound reports), judged by lean.level_faults:
-15 LUFS within 1 either way, true peak under -1 dB, the one target vd sound and the pages hold too.

A scan never fails anything: it prints one SCAN block, a line starting `fix before anyone watches:` for each pop (a pop
that is a hit the maker meant, with its sound on that frame, stays and is written down as meant: the accepted films
kept theirs), and a
line starting `check:` for each hold longer than 1.0 s. A long hold is not always a fault: studio films hold still on
purpose (a median 14% of their time in holds of 0.5 s or more, the longest about 2 s), so a hold is asked about, not
condemned. The rule that picks the stretches with the most change (vd pack, vd pin) lives here
too, so the readers' pack and the scan read motion the same way.
"""
import argparse
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
W, H = 480, 270               # change is read at this size, as the two earlier scripts this replaced read it
FLOOR, TIMES = 6.0, 2.2       # a pop's change is over FLOOR and TIMES the larger change beside it
STILL, LEAST = 0.35, 0.5      # stills.py: a frame is still under STILL; a hold is LEAST seconds or more of them
LONG = 1.0                    # a hold longer than this gets a `check:` line


def rate(film):
    """The film's own frame rate (r_frame_rate, read as a fraction: an eval of "60/1" would run whatever ffprobe prints)."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(film)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        r = float(Fraction(p.stdout.strip().split(",")[0]))
    except (ValueError, ZeroDivisionError):
        raise SystemExit(f"{film}: ffprobe could not read its frame rate ({p.stderr.strip()[-200:] or 'no video stream'})")
    if r <= 0:
        raise SystemExit(f"{film}: ffprobe gave a frame rate of {r}")
    return r


def uneven(film, fps):
    """The film's average frames a second when its frames are not evenly spaced (a phone or screen recording), else
    None. Every time here is a frame number over one rate, so on such a film the seconds drift from what a player
    shows; the frame numbers stay right."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", str(film)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        avg = float(Fraction(p.stdout.strip().split(",")[0]))
    except (ValueError, ZeroDivisionError):
        return None
    return avg if avg > 0 and abs(avg - fps) > 0.01 * fps else None


def changes(film, w=W, h=H, two=False):
    """d[i], the change from frame i to frame i + 1; with two, also d2[i], from frame i to frame i + 2 (a flash's
    neighbours). Decoded frame by frame and never held whole: 38 s at 60 a second is 600 MB as the scripts held it."""
    import decode
    cmd = ["ffmpeg", "-v", "error", "-i", str(film), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    size, d, d2, back = w * h, [], [], []
    # checked: a damaged film read by ffmpeg exits 0 with half its pictures, and its scan passed (decode.py)
    for buf in decode.pictures(cmd, size, str(film), expect=decode.frame_count(film)):
        f = np.frombuffer(buf, np.uint8).astype(np.int16)
        if back:
            d.append(float(np.abs(f - back[-1]).mean()))
        if two and len(back) == 2:
            d2.append(float(np.abs(f - back[0]).mean()))
        back = (back + [f])[-2:]
    return (np.array(d), np.array(d2)) if two else np.array(d)


def pops(d, d2=None, floor=FLOOR, times=TIMES):
    """[(frame, kind)] in frame order. 'jump': the first rule (the frame i + 1 whose change d[i] is over floor
    and times the larger of d[i - 1] and d[i + 1]). 'flash': frame k whose change in and change out are both over floor
    and times the changes around them, while frame k - 1 and frame k + 1 agree (their change is under 1/times of it)."""
    at = lambda i: d[i] if 0 <= i < len(d) else 0.0       # past either end of the film there is no change to hold against
    # every frame is asked, the first and last too: the rule once began two frames in and stopped two short, and a
    # flash on the film's second frame, or a jump onto its last, was never looked at
    out = [(i + 1, "jump") for i in range(len(d)) if d[i] > floor and d[i] > times * max(at(i - 1), at(i + 1))]
    if d2 is not None and len(d2):
        for k in range(1, len(d)):
            low = min(d[k - 1], d[k])
            if low > floor and low > times * max(at(k - 2), at(k + 1)) and k - 1 < len(d2) and d2[k - 1] * times < low:
                out.append((k, "flash"))
    return sorted(out)


def holds(d, fps, still=STILL, least=LEAST):
    """[(from s, to s)]: each run of changes under `still` at least `least` seconds of the film's own frames long
    (stills.py's rule; it took 60 frames a second and printed 24-frame beats). Changes i..j-1 still means frames i..j
    show one picture, from frame i's time until frame j + 1 replaces it."""
    out, i, n = [], 0, len(d)
    calm = d < still
    while i < n:
        if not calm[i]:
            i += 1
            continue
        j = i
        while j < n and calm[j]:
            j += 1
        if j - i >= fps * least:
            out.append((i / fps, (j + 1) / fps))
        i = j
    return out


def windows(film, fps, k, win=1.0, spans=None):
    """The k one-second stretches with the most change, not overlapping, as start times in time order (an earlier
    script's rule: change at 320 x 180, summed over each second, the largest taken and its neighbourhood shut). With
    spans [(from s, to s)], only stretches wholly inside one of them (a long reference shown by its ends)."""
    d = changes(film, 320, 180)
    n = max(1, int(round(win * fps)))
    if len(d) < n:                          # a film shorter than the stretch: the whole film is the one stretch
        return [0.0] if len(d) and k > 0 else []
    score = np.convolve(d, np.ones(n), mode="valid")
    if spans:
        keep = np.zeros(len(score), bool)
        for a, b in spans:
            keep[max(0, int(np.ceil(a * fps))):max(0, int(np.floor(b * fps)) - n + 1)] = True
        score[~keep] = -1
    picks = []
    for _ in range(k):
        i = int(np.argmax(score))
        if score[i] <= 0:
            break
        picks.append(i)
        score[max(0, i - n):i + n] = -1
    return sorted(i / fps for i in picks)


def has_sound(film):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(film)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    return bool(p.stdout.strip())


def scan(film, to=None):
    """(the SCAN block, the fix lines: pops only). The block ends with the fix lines, then the `check:` lines (holds
    over LONG). Written to `to` as well when given."""
    import lean   # its loudness is the one vd sound reports
    film = Path(film)
    fps = rate(film)
    d, d2 = changes(film, two=True)
    n = len(d) + 1
    lines = [f"SCAN {film.name}: {n} frames at {fps:g} a second ({n / fps:.2f} s)"]
    avg = uneven(film, fps)
    if avg:
        lines.append(f"  timing: this film's frames are not evenly spaced (about {avg:.3g} a second on average, counted here at {fps:g}), so the seconds below can be off: "
                     f"trust the frame numbers, or scan a copy made at one rate (ffmpeg -i FILM -fps_mode cfr -r {round(avg):g} COPY.mp4)")
    fixes, checks = [], []
    found = pops(d, d2)
    if found:
        lines.append("  pops (frame, seconds, change, kind): " + ", ".join(f"f{f} {f / fps:.2f} s {max(d[f - 1], d[f] if kind == 'flash' else 0):.1f} {kind}"
                                                                              for f, kind in found))
        fixes += [f"fix before anyone watches: a pop at {f / fps:.2f} s (frame {f}, a one-frame {kind}); a hit you meant, with its sound on that frame, stays: write it down as meant" for f, kind in found]
    else:
        lines.append("  pops: none")
    still = d < STILL
    hs = holds(d, fps)
    lines.append(f"  holds: still (change under {STILL}) in {still.mean() if len(d) else 0:.1%} of frames, median change {np.median(d) if len(d) else 0:.3f}; "
                 + (f"{len(hs)} of {LEAST} s or more" if hs else f"none of {LEAST} s or more"))
    for a, b in hs:
        lines.append(f"    {a:6.2f} to {b:6.2f} s  ({b - a:4.2f} s)")
        if b - a > LONG:
            checks.append(f"check: the picture stands still from {a:.2f} to {b:.2f} s ({b - a:.2f} s); keep it only if you chose it: a chosen hold creeps or breathes")
    lines.append(f"    long holds total {sum(b - a for a, b in hs):.2f} s")
    if has_sound(film):
        lufs, tp = lean.loudness(film)
        off = lean.level_faults(lufs, tp)
        lines.append(f"  loudness: {lufs} LUFS integrated, true peak {tp} dBTP (aim {lean.LUFS_AIM:g} within {lean.LUFS_WITHIN:g}, peak under {lean.PEAK_UNDER:g})"
                     + ("; " + "; ".join(off) if off else ": ok"))
    else:
        lines.append("  loudness: the file has no sound")
    import flash_scan
    fl = flash_scan.screen_video(film)
    gb, cb, rb = fl["busiest_general"], fl["busiest_classic"], fl["busiest_red"]
    # Calibrated to WCAG 2.3.1's own terms: a 10-degree field (341 x 256 px on a 1024 x 768 screen), and only paired,
    # same-direction changes over area-averaged pixels. On the four accepted films the busiest such second holds 3 or 4
    # changes (the limit is 6: three flashes), so none is over it. A flash over it is a fault to fix. Motion and
    # patterns (pans, slides, a fine grid aliased by sampling) are said on a line of their own, as not WCAG flashes.
    confirmed = bool(fl["classic_flagged"])
    b = max((cb, rb), key=lambda x: x["transitions_in_1s"])
    lines.append(f"  flash (WCAG 2.3.1): {cb['transitions_in_1s']} paired changes in a second at most (at {cb['at_s']} s), "
                 f"red {rb['transitions_in_1s']}: " + ("over the limit of 6" if confirmed else "ok"))
    if confirmed:
        kind = "red flashing" if b is rb else "flashing"
        fixes.append(f"fix before anyone watches: {kind} over WCAG 2.3.1's three flashes a second: {b['transitions_in_1s']} "
                     f"changes at {b['at_s']} s, over a quarter of the viewer's central ten degrees. Slow it, shrink it, or lower its contrast")
    elif fl["flagged"]:
        # the busiest of what was flagged, luminance or red (a red-only pattern printed "0 changes in a second at None s")
        n, when = max(((r[k + "_max_per_s"], r[k + "_at_s"]) for r in fl["flagged"] for k in ("general", "red", "red_coherent")
                       if r.get(k + "_at_s") is not None), default=(gb["transitions_in_1s"], gb["at_s"]), key=lambda x: x[0])
        lines.append(f"  motion or patterns (not WCAG flashes): {n} changes in a second at {when} s; "
                     "a stripe or checkerboard reversing there is worth a look at full size")
    text = "\n".join(lines + fixes + checks)
    if to:
        Path(to).parent.mkdir(parents=True, exist_ok=True)
        Path(to).write_text(text + "\n", encoding="utf-8")
    return text, fixes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("film")
    ap.add_argument("-o", dest="out", help="also write the block here")
    a = ap.parse_args(argv)
    print(scan(a.film, a.out)[0])


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
