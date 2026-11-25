"""One checked way to read a film's pictures from ffmpeg, for the tools that judge a film from them (scan.py, sheet.py,
measure_film.py).

ffmpeg reading a damaged or cut-short film exits 0: it says "Invalid NAL unit size" and "missing picture" on stderr and
hands over what it could, half the film or every picture with holes in it. Read with no more than its exit status, that
was a reader's packet or a passed scan made from half a film. Here a decode is whole or it is an error: ffmpeg's exit
status, anything it says at -v error, a picture cut off part way, and (when the caller knows how many to expect) the
count of pictures.
"""
import os
import subprocess
import threading

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def pictures(cmd, size, what, expect=None, short=0.02):
    """Each raw picture of `size` bytes that `cmd` (an ffmpeg command writing rawvideo to stdout at -v error) writes.
    Raises SystemExit, naming `what`, when ffmpeg fails, reports an error, stops part way through a picture, or hands
    over fewer than `expect` pictures (less a `short` share and two, for a container's rounding). A caller that stops
    early ends ffmpeg and nothing is raised."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    said = []
    reader = threading.Thread(target=lambda: said.append(p.stderr.read()), daemon=True)   # drained as it goes, so a long
    reader.start()                                                                          # complaint can't stall the pipe
    n, rest, whole = 0, 0, False
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                rest, whole = len(buf), True
                break
            n += 1
            yield buf
    finally:
        if not whole:                     # the caller stopped early: end ffmpeg, raise nothing
            p.kill()
        p.stdout.close()
        p.wait()
        reader.join(timeout=10)
    err = (said[0] if said else b"").decode("utf-8", "replace").strip()
    if p.returncode or err:
        raise SystemExit(f"{what}: ffmpeg {'failed' if p.returncode else 'reported errors'} reading it, so nothing is made from it: {err[-300:] or f'exit {p.returncode}'}")
    if rest:
        raise SystemExit(f"{what}: ffmpeg stopped part way through picture {n + 1}, so nothing is made from it")
    if expect and n < expect * (1 - short) - 2:
        raise SystemExit(f"{what}: ffmpeg handed over {n} pictures of the {expect} the film says it holds, so nothing is made from it")


def frame_count(film):
    """How many pictures the film says it holds (its first video stream's frame count, else its length times its rate),
    or None when it says neither."""
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate:format=duration",
                        "-of", "default=noprint_wrappers=1", str(film)], capture_output=True, text=True, creationflags=NO_WINDOW)
    got = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    try:
        return int(got["nb_frames"])
    except (KeyError, ValueError):
        pass
    try:
        a, b = got["r_frame_rate"].split("/")
        return int(float(got["duration"]) * float(a) / float(b))
    except (KeyError, ValueError, ZeroDivisionError):
        return None
