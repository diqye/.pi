#!/usr/bin/env python3
"""Real motion blur for a film made in code: draw extra pictures between frames, then average them.

  python blur.py IN.mp4 OUT.mp4 [--sub 8] [--open 4] [--fps 24] [--crf 12]

A frame drawn by code is perfectly sharp, so a fast move reads as a row of separate pictures. A camera's frame is the
sum of everything that passed while its shutter was open. To get that, render the film at `sub` times its frame rate,
with the film's clock running at the normal speed (divide the renderer's frame number by `sub`), then run this. It
averages the first `open` pictures of each group of `sub` and keeps one frame per group. 4 of 8 is a half-open shutter,
the usual look. Things that hold still stay sharp, and anything that steps a whole frame at a time (a photograph shown
for one frame, a counter) is unchanged as long as it steps on whole frame numbers.

Keep every function of the clock continuous, and take `Math.floor` of the clock before indexing a list with it.

A caller that gives each frame its own number of pictures doesn't use this command line: it averages with `groups`
below, which takes the size of each frame's group.
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
TAGS = (("color_range", "-color_range"), ("color_space", "-colorspace"), ("color_transfer", "-color_trc"), ("color_primaries", "-color_primaries"))


def groups(src, sizes, out, first=None, fps=30, crf=12):
    """Average each frame's own group of pictures: the first sizes[0] pictures of SRC make frame 0 of OUT, the next
    sizes[1] frame 1, and so on, however many each frame has. With FIRST, also write the first picture of each group to
    it, which is each frame drawn at its own time. The pictures are read one at a time from ffmpeg and the frames written
    one at a time to it, so a film of tens of thousands of pictures is never held in memory, and the planes are averaged
    as they are stored, as ffmpeg's tmix does, so no colour is converted. The colour tags of SRC are kept, which tmix
    dropped. Returns how many pictures SRC held, counting any past the last group, so a caller can tell a render that
    stopped early, or drew more than it was asked for, from a whole one."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height," + ",".join(t for t, _ in TAGS), "-of", "json", str(src)],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        info = json.loads(r.stdout)["streams"][0]
        w, h = int(info["width"]), int(info["height"])
    except (ValueError, KeyError, IndexError):
        raise SystemExit(f"{src}: can't read its pictures ({r.stderr.strip()[-200:] or 'ffprobe said nothing'})")
    tags = [x for t, flag in TAGS if info.get(t) not in (None, "", "unknown") for x in (flag, info[t])]
    size = w * h + 2 * ((w + 1) // 2) * ((h + 1) // 2)  # one yuv420p picture
    wide = np.uint16 if max(sizes, default=1) <= 257 else np.uint32  # 257 pictures of 255 still fit in sixteen bits

    def encoder(path):
        # the tags go with the input: given for the output instead, ffmpeg converts the levels by one step and keeps two
        return subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}", "-r", f"{fps:g}", *tags, "-i", "-",
                                 "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
                                stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    said = tempfile.TemporaryFile()  # a file, not a pipe: a stream of errors can't fill it and stall ffmpeg
    decode = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                              stdout=subprocess.PIPE, stderr=said, creationflags=NO_WINDOW)
    writers = [encoder(out)] + ([encoder(first)] if first else [])
    # Reading a picture from the pipe and adding it each take about 1.5 ms at 1080p, and both let go of Python's lock, so
    # a second thread reads while this one adds: 6.9 ms a picture done one after the other
    waiting = queue.Queue(maxsize=8)

    def reader():
        try:
            while len(raw := decode.stdout.read(size)) == size:
                waiting.put(raw)
        except (OSError, ValueError):
            pass
        waiting.put(None)

    def picture():
        raw = waiting.get()
        if raw is None:
            raise EOFError
        return raw

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    read, stopped, broke = 0, False, None
    try:
        for n in sizes:
            total = np.zeros(size, wide)
            for j in range(n):
                raw = picture()
                read += 1
                if j == 0 and first:
                    writers[1].stdin.write(raw)
                np.add(total, np.frombuffer(raw, np.uint8), out=total)
            writers[0].stdin.write(((total + n // 2) // n).astype(np.uint8).tobytes())
        while picture():                             # pictures past the last group: the render isn't the one the sizes describe
            read += 1
    except EOFError:
        pass                                         # fewer pictures than the groups ask for: the caller is told how many there were
    except OSError as e:
        broke = e                                    # an encoder went away while it was being written to
    finally:
        if decode.poll() is None and thread.is_alive():
            stopped = True
            decode.kill()                            # stopped early: the reader may be waiting on a full queue
        while thread.is_alive():
            try:
                waiting.get(timeout=0.1)
            except queue.Empty:
                pass
        decode.stdout.close()
        decode.wait()
        for x in writers:
            try:
                x.stdin.close()
            except OSError as e:                     # closing sends what was still waiting, to an encoder that may be gone
                broke = broke or e
            x.wait()
        said.seek(0)
        why = said.read().decode("utf-8", "replace").strip()
        said.close()
    made = [Path(x) for x in (out, first) if x]
    # the decoder can hand over every picture asked for and still have failed on the way: its word is taken with the count
    if decode.returncode and not stopped:
        for x in made:
            x.unlink(missing_ok=True)
        raise SystemExit(f"ffmpeg failed while reading {src}, so no film was made from it: {why[-300:] or 'it gave no reason'}")
    if broke or any(x.returncode for x in writers):
        for x in made:
            x.unlink(missing_ok=True)
        raise SystemExit(f"ffmpeg couldn't write {out}" + (f" or {first}" if first else "") + (f": {broke}" if broke else ""))
    return read


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--sub", type=int, default=8, help="pictures rendered for each frame of the film")
    ap.add_argument("--open", type=int, default=4, help="how many of them the shutter is open for")
    ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--crf", type=int, default=12)
    # a leading ~ is the home folder: the pages give paths that way, and PowerShell leaves ~ to the program
    a = ap.parse_args([os.path.expanduser(x) if x == "~" or x[:2] in ("~/", "~" + chr(92)) else x for x in sys.argv[1:]])
    if not 1 <= a.open <= a.sub:
        raise SystemExit("--open must be between 1 and --sub")
    weights = " ".join(["1"] * a.open)
    comma = chr(92) + ","                                   # ffmpeg wants the comma inside mod() escaped
    vf = f"tmix=frames={a.open}:weights='{weights}',select='not(mod(n-{a.open - 1}{comma}{a.sub}))',setpts=N/({a.fps:g}*TB)"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.src, "-vf", vf, "-r", f"{a.fps:g}", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True, creationflags=NO_WINDOW)
    count = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", a.out],
                           capture_output=True, text=True, creationflags=NO_WINDOW).stdout.strip().strip(",")
    if not count.isdigit() or count == "0":  # ffmpeg writes a file with no picture when the input has fewer than --open pictures
        os.remove(a.out)
        raise SystemExit(f"{a.src} gave no frames at --sub {a.sub} --open {a.open}: it holds fewer pictures than one group, or none. The empty file ffmpeg wrote was removed.")
    print(f"wrote {a.out}: one frame for every {a.sub} pictures, shutter open for {a.open}; {count} frames")


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
