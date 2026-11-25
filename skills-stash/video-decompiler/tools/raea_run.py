#!/usr/bin/env python3
"""Run one raea render so a rebuild loop can trust it, and print one line.

  python raea_run.py ENTRY.tsx -o OUT [any raea render flags] [--timeout S] [--retries N] [--check-repeats [ORIGINAL]] [--trace]

What it does that a bare `raea render` doesn't:
- On Windows it takes Git's usr/bin (kill.exe) off PATH for raea. raea's stale-folder sweep asks `kill -0 PID` whether
  other renders still run, and Git's MSYS kill doesn't know Windows PIDs, so every live render looks dead and its work
  folder is deleted mid-bundle ("Could not resolve ..."). PowerShell started from Git Bash keeps that PATH, so running
  raea from PowerShell isn't enough.
- It sets RAEA_VELLO_BUMP=full. With raea's smaller page buffers a heavy frame silently repeats an earlier one.
- It deletes the old output first, so a failed render can't leave the last film behind to be scored.
- It kills and retries a render that all but stops using CPU or runs past --timeout, and retries the bundler's transient
  "Could not resolve" error. Output goes to a file, never a pipe a stalled child could hold open.
- It lets one render run at a time on the machine: a second waits for the first. Renders that share a graphics card
  run it out of memory, and that has stopped Windows.
- --check-repeats lists .mp4 frames identical to the one before (raea's silent drop). Given the original, it lists
  only frames that repeat where the original moves.
- --trace prints raea's own start-up phases (RAEA_STARTUP_TRACE), with its export cache off.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
TRANSIENT = re.compile(r"Could not resolve|cannot find the path|The system cannot find", re.I)
FILES = (".mp4", ".mov", ".webm", ".mkv", ".gif", ".png", ".jpg", ".jpeg", ".wav")  # what raea writes as one file; any other -o is a folder of stills
SOURCE = (".tsx", ".ts", ".jsx", ".js")                     # a composition, and never an output: -o is deleted before the render


PIN = "0.1.1-rc4"   # the raea this skill's tools and tests last passed on; an older one is refused (RAEA_ANY_VERSION=1 goes ahead)
KNOWN = [Path(p) for p in os.environ.get("VD_RAEA_KNOWN", "").split(os.pathsep) if p]  # more places this machine keeps a pinned build (VD_RAEA_KNOWN, a path list); none by default


def version_key(v):
    """An order for raea versions. A release 0.1.1 is the newest of its number; rcs count up below it (0.1.1-rc4 > rc3).
    A local build (0.1.0-local-HASH) is a build of its number from some commit that can't be placed against the tags
    without that repository's history, so it counts as older than every rc and release of its number: the fix a film
    needs may or may not be in it. Unreadable: None."""
    m = re.match(r"\s*v?(\d+)\.(\d+)\.(\d+)(?:-(rc|beta|alpha|local)[.-]?(\w*))?", v or "")
    if not m:
        return None
    triple = tuple(int(x) for x in m.groups()[:3])
    tag, rest = m.group(4), m.group(5) or ""
    if tag is None:
        return triple + (3, 0)
    rank = {"rc": 2, "beta": 1, "alpha": 0, "local": -1}[tag]
    n = int(re.match(r"\d*", rest).group(0) or 0) if tag != "local" else 0
    return triple + (rank, n)


_SEEN = {}


def binary_version(path):
    """`raea --version` of this binary, asked once a process."""
    if path not in _SEEN:
        try:
            p = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW)
            out = (p.stdout or p.stderr).strip()
            _SEEN[path] = out.splitlines()[0].strip() if out else "unknown"
        except (OSError, subprocess.TimeoutExpired):
            _SEEN[path] = "unknown"
    return _SEEN[path]


EXE = "raea.exe" if os.name == "nt" else "raea"


def candidates():
    """Every raea this machine has where a skill would look, in order: beside the skill, under ~/.raea, on PATH, and
    where this machine keeps builds (KNOWN). Returns (paths that exist, places looked)."""
    skill = Path(__file__).resolve().parent.parent
    places = [skill / "bin" / EXE, skill.parent.parent / "raea" / EXE, Path.home() / ".raea"]
    found, looked = [], []
    for place in places:
        looked.append(str(place))
        if place.is_file():
            found.append(place)
        elif place.is_dir():
            found += [f for f in place.rglob(EXE) if f.is_file() and len(f.relative_to(place).parts) <= 5]
    on_path = shutil.which("raea")
    looked.append("PATH")
    if on_path:
        found.append(Path(on_path))
    looked += [str(k) for k in KNOWN]
    found += [k for k in KNOWN if k.is_file()]
    seen, out = set(), []
    for f in found:
        r = str(f.resolve())
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out, looked


_FOUND = None


def find_raea():
    """(path, version): RAEA_BIN when it is set; otherwise the newest raea in candidates() that meets PIN, or, when none
    does, the newest there is (checked_binary then refuses it and says where it looked)."""
    global _FOUND
    if os.environ.get("RAEA_BIN"):
        p = Path(os.environ["RAEA_BIN"])
        if not p.is_file():
            raise SystemExit(f"RAEA_BIN names {p}, which isn't a file")
        return str(p.resolve()), binary_version(str(p.resolve()))
    if _FOUND is None:
        paths, looked = candidates()
        if not paths:
            raise SystemExit(f"raea not found. Looked in: {', '.join(looked)}. Install it with its own installer (`vd doctor` prints the "
                             f"line for this system), or set RAEA_BIN to a {EXE} of {PIN} or newer.")
        ranked = sorted(((version_key(binary_version(p)) or (-1,), p) for p in paths), reverse=True)
        _FOUND = (ranked[0][1], binary_version(ranked[0][1]))
    return _FOUND


def checked_binary(say=True):
    """raea's path, said on one line with its version, and refused when older than PIN. The film that lost 32 minutes
    to shapes that would not draw was rendered by an older raea on PATH, although the fix was in the pinned one. With no
    RAEA_BIN the newest raea that meets PIN is found, so a maker never has to set one to get a first look."""
    path, v = find_raea()
    if say:
        print(f"raea: {path} ({v}; this skill needs {PIN} or newer)", file=sys.stderr, flush=True)
    have, want = version_key(v), version_key(PIN)
    if os.environ.get("RAEA_ANY_VERSION") != "1" and (have is None or have < want):
        _, looked = candidates()
        raise SystemExit(f"FAILED wrong raea: the newest found is {path} ({v}), and this skill needs {PIN} or newer. "
                         f"Looked in: {', '.join(looked)}. Set RAEA_BIN to a raea {PIN} or newer "
                         "(or set RAEA_ANY_VERSION=1 to render with this one anyway).")
    return path


def raea_binary():
    """raea's full path (find_raea's choice). raea is started from the composition's folder, so it is always absolute."""
    return find_raea()[0]


def stills(out, extra=()):
    """Whether a render writes a folder of stills: frames asked for with --at, or an output with no file type raea writes.
    A folder named stills.v1 is a folder, not a file."""
    return any(x == "--at" or str(x).startswith("--at=") for x in extra) or Path(out).suffix.lower() not in FILES


def refuse_bad(entry, out):
    """Stop before anything is deleted when the two arguments can't be a render: the old output is cleared first, so
    `raea_run.py final.mp4 -o edit.final.tsx` would delete the film's source."""
    entry, out = Path(entry), Path(out)
    if not entry.is_file():
        raise SystemExit(f"no such composition: {entry}. Nothing was deleted. Run it as raea_run.py ENTRY.tsx -o OUT.")
    if entry.suffix.lower() not in SOURCE:
        raise SystemExit(f"{entry} isn't a composition ({', '.join(SOURCE)}). Nothing was deleted. Run it as raea_run.py ENTRY.tsx -o OUT.")
    if out.suffix.lower() in SOURCE or out.resolve() == entry.resolve():
        raise SystemExit(f"-o {out} is source code, and -o is deleted before a render. Nothing was deleted. Run it as raea_run.py ENTRY.tsx -o OUT.mp4.")


def raea_env(trace=False, bump_full=True):
    env = os.environ.copy()
    if os.name == "nt":
        keep = [d for d in env.get("PATH", "").split(os.pathsep) if d and not (Path(d) / "kill.exe").is_file()]
        env["PATH"] = os.pathsep.join(keep)
        assert shutil.which("kill", path=env["PATH"]) is None
    if bump_full:
        env.setdefault("RAEA_VELLO_BUMP", "full")
    # raea's export cache: on 0.1.0-local builds it keyed only some media types and handed back the old video after an
    # .svg edit, so it was turned off for every render. From rc3 it keys every file under the folder (raea #28), so it is
    # left on there: an unchanged film re-exports from cache (WHYS 7.3)
    try:
        old = (version_key(binary_version(raea_binary())) or (0,)) < version_key("0.1.1-rc3")
    except SystemExit:
        old = True
    if old:
        env.setdefault("RAEA_EXPORT_CACHE", "0")
    if trace:
        env["RAEA_STARTUP_TRACE"] = str(int(time.time() * 1000))
        env["RAEA_EXPORT_CACHE"] = "0"
    return env


def clear_output(out: Path, folder=None):
    if not (stills(out) if folder is None else folder):
        out.unlink(missing_ok=True)
    elif out.is_dir():
        for f in out.glob("frame-*.png"):
            f.unlink()


def die_with_us(proc):
    """On Windows, tie raea to this process: if it's stopped from outside, raea and its children stop too. Stopping a
    render by killing this script used to leave raea running and holding memory, which one run mistook for another job's."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class BASIC(ctypes.Structure):
        _fields_ = [("a", ctypes.c_longlong), ("b", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD), ("c", ctypes.c_size_t), ("d", ctypes.c_size_t),
                    ("e", wintypes.DWORD), ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

    class EXT(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IO), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t), ("d", ctypes.c_size_t)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = k.CreateJobObjectW(None, None)
    info = EXT()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    tied = bool(job) and bool(k.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))) and bool(k.AssignProcessToJobObject(job, int(proc._handle)))
    if not tied:
        # said, not fatal: what is drawn is good either way. Unsaid, a stopped command could leave its renderer at work
        # with the queue already open to the next one, and nothing told anyone to look
        print(f"note: could not tie the renderer's life to this command (Windows error {ctypes.get_last_error()}): if you stop this command, check that "
              "its renderer has stopped too", file=sys.stderr, flush=True)
    return job  # kept by the caller: the job closes, and takes raea with it, when this process ends


def kill_tree(proc):
    try:
        parent = psutil.Process(proc.pid)
        for p in parent.children(recursive=True) + [parent]:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
    proc.wait(timeout=30)


def cpu_seconds(proc):
    try:
        p = psutil.Process(proc.pid)
        total = sum(p.cpu_times()[:2])
        for c in p.children(recursive=True):
            try:
                total += sum(c.cpu_times()[:2])
            except psutil.NoSuchProcess:
                pass
        return total
    except psutil.NoSuchProcess:
        return None


def render(entry, out, extra=(), timeout=900.0, idle=90.0, retries=2, trace=False, bump_full=True):
    """Render ENTRY to OUT, waiting for the machine first. Returns (ok, seconds, message, raea's log text).

    The wait is here, not in the command line, because tools such as render_check.py call this directly, and a check
    that drew frames beside another render would share the card all the same. The arguments are checked first, here,
    because the old output is cleared before raea starts: every caller, not only the command line, is refused before
    anything is deleted."""
    global LOCK
    refuse_bad(entry, out)
    if LOCK is not None:  # this process already holds the machine, and the lock can't be taken twice
        return _render(entry, out, extra, timeout, idle, retries, trace, bump_full)
    LOCK = one_at_a_time(kind="look" if is_look(out, extra) else "render")
    try:
        return _render(entry, out, extra, timeout, idle, retries, trace, bump_full)
    finally:
        if LOCK is not None:
            LOCK.close()
            try:
                (QUEUE / "raea_run.lock.rendered").touch()   # when the last render let go, for heavy.py --when-idle
            except OSError:
                pass
        LOCK = None


def _render(entry, out, extra, timeout, idle, retries, trace, bump_full):
    """render() once the machine is ours."""
    entry, out = Path(entry).resolve(), Path(out).resolve()
    folder = stills(out, extra)
    (out if folder else out.parent).mkdir(parents=True, exist_ok=True)  # raea stops when a stills folder isn't there yet
    args = [checked_binary(), "render", entry.name, "-o", str(out) + (os.sep if folder else ""), *extra]
    env = raea_env(trace, bump_full)
    t_all = time.monotonic()  # a clock that can't be set back or forward, so a clock correction can't end or stretch a render
    text = ""
    for attempt in range(retries + 1):
        clear_output(out, folder)
        with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as log:
            # Off Windows nothing ends raea when this wrapper is killed, so raea is handed the lock too: an flock lives
            # until every holder of the open file has gone, and no other render starts while an orphan is still drawing.
            # (On Windows die_with_us ends raea with the wrapper.)
            keep = {"pass_fds": (LOCK.fileno(),)} if LOCK is not None and os.name != "nt" else {}
            proc = subprocess.Popen(args, cwd=entry.parent, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, creationflags=NO_WINDOW, **keep)
            job = die_with_us(proc)  # noqa: F841
            # A render that works uses more than a whole core. One that hung on the graphics card was seen ticking over at
            # 0.07 of a core for eleven minutes, so "no CPU at all" is too weak a test: under a tenth of a core for `idle`
            # seconds is a stall.
            t0, marks, why = time.monotonic(), [], None               # marks: (time, CPU seconds so far), one a second
            while proc.poll() is None:
                time.sleep(1.0)
                if proc.poll() is not None:
                    break  # it finished while we slept, so it neither stalled nor ran over
                c, now = cpu_seconds(proc), time.monotonic()
                if c is not None:
                    marks.append((now, c))
                    while len(marks) > 1 and now - marks[1][0] >= idle:
                        marks.pop(0)
                if marks and now - marks[0][0] >= idle and marks[-1][1] - marks[0][1] < 0.1 * idle:
                    why = f"under a tenth of a core for {idle:.0f} s"
                elif now - t0 > timeout:
                    why = f"over {timeout:.0f} s"
                if why:
                    kill_tree(proc)
                    break
            log.seek(0)
            text = log.read()
        if why:
            print(f"raea stalled ({why}), attempt {attempt + 1}", file=sys.stderr, flush=True)
            continue
        if proc.returncode == 0 and out.suffix.lower() == ".wav" and out.is_file() and out.stat().st_size > 44:
            # `-o OUT.wav` is raea's sound-only render (no frame drawn); it says so without an APPLIED line
            line = next((l for l in text.splitlines() if "of sound" in l), f"{out.name}: sound only").strip()
            return True, time.monotonic() - t_all, line, text
        if proc.returncode == 0 and "APPLIED" in text:
            line = next(l for l in text.splitlines() if "APPLIED" in l).strip()
            cached = " (raea's export cache)" if "from the export cache" in text else ""
            return True, time.monotonic() - t_all, line + cached, text
        if TRANSIENT.search(text) and attempt < retries:
            print(f"raea transient error, attempt {attempt + 1}: {TRANSIENT.search(text).group(0)}", file=sys.stderr, flush=True)
            time.sleep(2)
            continue
        bad = [l for l in text.splitlines() if re.search(r"REFUSED|error|panicked", l, re.I)] or text.splitlines()[-5:]
        return False, time.monotonic() - t_all, " | ".join(l.strip() for l in bad[:4]), text
    return False, time.monotonic() - t_all, f"stalled {retries + 1} times", text


def repeats(video, original=None, size=(192, 108)):
    """Frames identical to the frame before; with an original, only where the original changes."""
    import numpy as np

    def gray(path):
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"scale={size[0]}:{size[1]}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
        raw = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW).stdout
        return np.frombuffer(raw, np.uint8).reshape(-1, size[1], size[0]).astype(np.int16)

    a = gray(video)
    same = [i for i in range(1, len(a)) if not np.any(a[i] != a[i - 1])]
    if original is not None:
        o = gray(original)
        same = [i for i in same if i < len(o) and np.abs(o[i] - o[i - 1]).mean() > 0.5]
    return same


LOCK = None                                                 # the open lock file, while this process holds the machine


QUEUE = Path.home() / ".raea"
LOOKS_FIRST = 240.0                                         # the most a render or heavy job stands aside for waiting looks, seconds


def is_look(out, extra=()):
    """A short job: a few stills asked for with --at or --frame, or the sound alone. These go to the front of the queue."""
    ex = [str(x) for x in extra]
    few = any(x in ("--at", "--frame") or x.startswith(("--at=", "--frame=")) for x in ex)
    return few or Path(str(out)).suffix.lower() == ".wav"


def holder_file(lock):
    return Path(str(lock) + ".holder")


def read_holder(lock):
    """(pid, command, seconds held, kind) from the holder's note beside the lock; None when there is none or it has gone."""
    try:
        h = json.loads(holder_file(lock).read_text(encoding="utf-8"))
        if not psutil.pid_exists(int(h["pid"])):
            return None
        return int(h["pid"]), h.get("cmd", "?"), time.time() - float(h.get("since", time.time())), h.get("kind", "render")
    except (OSError, ValueError, KeyError):
        return None


def note_holder(lock, what, kind):
    try:
        holder_file(lock).write_text(json.dumps({"pid": os.getpid(), "cmd": what[:300], "since": time.time(), "kind": kind}), encoding="utf-8")
    except OSError:
        pass


def _alive(pid, born):
    """Whether `pid` is still the process that wrote `born` (its start time): a number Windows has handed to a newer
    process is not the waiter that left it."""
    try:
        return abs(psutil.Process(pid).create_time() - born) < 1.0
    except (psutil.Error, ValueError):
        return False


def waiting_pids(lock, name=".waiting"):
    """The living pids waiting for the queue: one file per waiter in a folder beside the lock, holding its start time.
    (One shared list, read, changed and written back by each waiter, lost a waiter whenever two arrived together: the
    second wrote back a list read before the first had added itself.) A file whose process has gone is removed here, so
    a waiter that was killed is not counted again when its number is reused."""
    w = Path(str(lock) + name + ".d")
    out = set()
    try:
        files = [p for p in w.iterdir() if p.name.isdigit()]
    except OSError:
        return out
    for f in files:
        try:
            born = float(f.read_text(encoding="utf-8") or "nan")
        except (OSError, ValueError):
            continue  # being written this moment: counted on the next look
        if _alive(int(f.name), born):
            out.add(f.name)
        else:
            try:
                f.unlink()
            except OSError:
                pass
    return out


def _waiting(lock, add, name=".waiting"):
    w = Path(str(lock) + name + ".d")
    me = w / str(os.getpid())
    try:
        if add:
            w.mkdir(exist_ok=True)
            tmp = w / f".{os.getpid()}.tmp"
            tmp.write_text(repr(psutil.Process().create_time()), encoding="utf-8")
            os.replace(tmp, me)  # whole or absent: a reader never sees a half-written start time
        else:
            me.unlink(missing_ok=True)
    except (OSError, psutil.Error):
        pass


def last_render(lock):
    """When a render last held the queue, in seconds since the epoch: now, while one holds it or waits for it."""
    stamp = Path(str(lock) + ".rendered")
    times = [stamp.stat().st_mtime] if stamp.exists() else []
    h = read_holder(lock)
    if (h and h[3] in ("render", "look")) or waiting_pids(lock) or waiting_pids(lock, ".looks"):
        times.append(time.time())
    return max(times, default=0.0)


HELD = "VD_QUEUE_HELD"   # set by a holder in its own environment, so every process it starts inherits it: "PID|LOCK;PID|LOCK"


def marks():
    """[(pid, lock path)] from this process's environment: every lock an ancestor (or this process) holds."""
    out = []
    for m in os.environ.get(HELD, "").split(";"):
        if "|" in m:
            pid, where = m.split("|", 1)
            if pid.isdigit():
                out.append((int(pid), where))
    return out


def set_marks(ms):
    if ms:
        os.environ[HELD] = ";".join(f"{p}|{w}" for p, w in ms)
    else:
        os.environ.pop(HELD, None)


def _try_lock(f):
    """Take the lock on an open lock file without waiting; OSError when another process has it."""
    if os.name == "nt":
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _drain(lock):
    """Wait until none of this process's own jobs is inside its .under.<pid> lock, and keep them out: a holder lets go
    of the machine only after the renders it admitted have finished (a review's finding). Returns the open file, locked."""
    under = Path(lock).with_name(f"{Path(lock).name}.under.{os.getpid()}")
    f, t0, said = open(under, "a+b"), time.monotonic(), None
    while True:
        try:
            _try_lock(f)
            return f
        except OSError:
            waited = time.monotonic() - t0
            if said is None or waited - said >= 30:
                print(f"queue: letting go of the machine once this process's own jobs finish (waited {waited:.0f} s)", file=sys.stderr, flush=True)
                said = waited
            time.sleep(0.25)


class Held:
    """The queue, held: the open lock file. close() lets it go, and takes this process's mark and note with it, so a
    later call in this process (or a child started after) waits as anyone would. It lets go only once the jobs this
    process admitted under it have finished, at close() or at the end of the process. A holder that is killed leaves
    the lock free at once (the system ends its lock); its jobs then check again before they draw (one_at_a_time)."""

    def __init__(self, f, lock):
        import atexit
        self.f, self.lock = f, Path(lock)
        set_marks(marks() + [(os.getpid(), str(self.lock.resolve()))])
        atexit.register(self.close)

    def fileno(self):
        return self.f.fileno()

    def close(self):
        if self.f is None:
            return
        gate = _drain(self.lock)
        try:
            set_marks([(p, w) for p, w in marks() if not (p == os.getpid() and Path(w) == self.lock.resolve())])
            h = read_holder(self.lock)
            if h and h[0] == os.getpid():
                try:
                    holder_file(self.lock).unlink()
                except OSError:
                    pass
            self.f.close()
            self.f = None
        finally:
            gate.close()
            try:
                Path(gate.name).unlink()  # this process's own gate: nobody can be under a holder that has let go
            except OSError:
                pass
            # and what its jobs left beside that gate: their waiting lists and the stamp of their last render
            Path(gate.name + ".rendered").unlink(missing_ok=True)
            for kind in (".waiting.d", ".looks.d"):
                shutil.rmtree(gate.name + kind, ignore_errors=True)


def lock_busy(lock):
    """Whether some process holds the lock file now (taking it without waiting fails)."""
    try:
        with open(lock, "a+b") as f:
            _try_lock(f)
            return False                     # free: closing the file lets it go again
    except OSError:
        return True


def held_above(lock):
    """The pid of an ancestor of this process, when that process holds this lock now (its mark, its note, alive), else
    None. 03:28 one night: heavy.py held the queue and started measure_film.py, whose transcriber asked the queue for
    its turn and waited an hour for the lock its own parent held, 0.7 s of CPU in 15 minutes, every film behind it."""
    try:
        here = Path(lock).resolve()
        h = read_holder(lock)
        line = [q.pid for q in psutil.Process(os.getpid()).parents()]
        for pid, where in marks():
            if Path(where) == here and pid in line and (h[0] == pid if h else lock_busy(lock)):
                # with no note (a disk too full to write it), the mark an ancestor left and the lock being held are enough:
                # the job waited on its own parent until its time ran out
                return pid
        return None
    except (ValueError, OSError, psutil.Error):
        return None


def one_at_a_time(wait=3600.0, lock=None, what=None, kind="render", gone=None):
    """Hold a lock for as long as this process lives, so two renders never share the graphics card.

    A raea render takes about 2 GB of memory and 4 GB of the card's. Three at once (a director and two helpers) ran an
    8 GB card out: the driver reset, raea lost its device, and Windows stopped with a kernel error, twice in one afternoon.
    Every agent on the machine renders through this script, so the queue is here. RAEA_RUN_ALONE=0 turns it off.

    The holder writes what it is (command, start, process id) beside the lock, and a process that waits says at once and
    then every 30 s what holds the queue and for how long: a compile once held it 45 minutes and nobody waiting saw why.

    Looks go first. A look (a few stills, the sound alone) is seconds and a full render is minutes; with seven makers on
    one card a look once waited ten minutes behind other films' renders, and the look is the step a maker repeats. So a
    job of kind "look" lists itself, and a render or a heavy job that sees a look waiting stands aside before it tries
    the lock, for up to LOOKS_FIRST seconds in all so a stream of looks can't starve it.
    """
    if os.environ.get("RAEA_RUN_ALONE") == "0":
        return None
    if lock is None:
        QUEUE.mkdir(exist_ok=True)
        lock = QUEUE / "raea_run.lock"
    above = held_above(lock)
    if above is not None:
        # exempt from the lock its ancestor holds, not from that ancestor's other children: they take turns on a lock of
        # the holder's own, so two renders started by one heavy job can never draw at once (a review's finding)
        under = Path(lock).with_name(f"{Path(lock).name}.under.{above}")
        print(f"queue: held by pid {above}, which started this process; taking its turn among that holder's own jobs ({under.name})",
              file=sys.stderr, flush=True)
        held = one_at_a_time(wait, under, what, kind, gone)
        h = read_holder(lock)
        if held is None or (psutil.pid_exists(above) and h and h[0] == above):
            return held
        # the holder let go of the machine (or was killed) while this waited: its turn there covers nothing now
        held.close()
        print(f"queue: pid {above} has let go of the machine; waiting for it like anyone else", file=sys.stderr, flush=True)
    what = what or " ".join([Path(sys.argv[0]).name] + sys.argv[1:])
    f = open(lock, "a+b")
    t0, said = time.monotonic(), None
    look, stood_aside = kind == "look", 0.0
    if kind == "render":
        _waiting(lock, True)
    if look:
        _waiting(lock, True, ".looks")
    try:
        while True:
            try:
                if not look and stood_aside < LOOKS_FIRST and waiting_pids(lock, ".looks"):
                    stood_aside += 1.0
                    raise OSError("a look is waiting")
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                note_holder(lock, what, kind)
                if kind in ("render", "look"):
                    try:
                        Path(str(lock) + ".rendered").touch()
                    except OSError:
                        # the lock is held; this stamp only tells heavy.py when the queue last drew. A stamp that could not be
                        # written (a full disk) was taken for someone else holding the queue, and the job waited an hour on itself
                        pass
                return Held(f, lock)                              # kept open by the caller: the lock goes when the process does
            except OSError:
                waited = time.monotonic() - t0
                if waited > wait:
                    f.close()
                    raise SystemExit(f"FAILED the render queue has been held for over {wait / 60:.0f} minutes; gave up waiting")
                if gone is not None and gone():
                    f.close()
                    raise SystemExit("FAILED stopped waiting for the render queue: the process that started this one has gone")
                if said is None or waited - said >= 30:
                    h = read_holder(lock)
                    who = f"pid {h[0]} ({h[3]}), holding it {h[2] / 60:.1f} min: {h[1]}" if h else "a process that left no note (an older wrapper)"
                    print(f"queue: waiting {waited:.0f} s; held by {who}", file=sys.stderr, flush=True)
                    said = waited
                time.sleep(0.25 if look else 1.0)
    finally:
        if kind == "render":
            _waiting(lock, False)
        if look:
            _waiting(lock, False, ".looks")


def main():
    # no abbreviations: raea's own --h (height) was read as short for --help, so the wrapper printed its help and stopped
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    ap.add_argument("entry")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--timeout", type=float, default=900.0, help="seconds before a render counts as stalled")
    ap.add_argument("--idle", type=float, default=90.0, help="seconds without CPU use before a render counts as stalled")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--check-repeats", nargs="?", const="", metavar="ORIGINAL")
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--no-bump-full", action="store_true", help="keep raea's own page buffer sizes")
    # a leading ~ is the home folder: the pages give paths that way, and PowerShell leaves ~ to the program
    a, extra = ap.parse_known_args([os.path.expanduser(x) if x == "~" or x[:2] in ("~/", "~" + chr(92)) else x for x in sys.argv[1:]])
    ok, secs, msg, text = render(a.entry, a.out, extra, a.timeout, a.idle, a.retries, a.trace, not a.no_bump_full)
    print(f"{'OK' if ok else 'FAILED'} {secs:.1f}s {msg}")
    if a.trace:
        for l in text.splitlines():
            if l.startswith("raea startup:"):
                print("  " + l)
    if ok and a.check_repeats is not None and a.out.lower().endswith((".mp4", ".mov")):
        same = repeats(a.out, a.check_repeats or None)
        print("repeated frames: " + (", ".join(map(str, same[:40])) + (" ..." if len(same) > 40 else "") if same else "none"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
