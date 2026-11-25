#!/usr/bin/env python3
"""The lean way to make a film: a film folder that starts from a working film, and one command per step.

  vd new NAME --kind explainer|launch|vertical     a film folder: a working film, its kit, score.json (the clock)
  vd new NAME --like FILM                           a film folder that is a copy of a whole worked film from library/films
  vd look [--at 1.2,4.5] [-o look.jpg]              many moments as one picture, and what did not draw
  vd sound [--onto FILM.mp4]                        the sound from score.json, mixed and checked, no picture render
  vd render --from A --to B                         render seconds A..B only, and splice it into the exported picture
  vd export                                         the finished film: the picture rendered once, the sound copied on, then scanned;
                                                    each one kept as cuts/NAME-cutN.mp4, NAME.mp4 the latest
  vd scan FILM.mp4                                  pops, holds and level of a finished film, the fixes first (tools/scan.py)
  vd measure FILM [--against REF]                   the gap table against a reference film: up to forty gaps, the kinds that matter most first
  vd pin REF                                        write the reference's numbers into score.json as targets
  vd profile [--transcript T.jsonl]                 minutes by class for the session that made this film

Every command appends one line to ~/.vd/usage.log (time, command, film, seconds), so the tools nobody calls are known.
A film folder is the nearest folder at or above the working directory that holds score.json, or --film DIR.
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SKILL = TOOLS.parent
STARTER = SKILL / "library" / "starter" / "lean"
KINDS = ("explainer", "launch", "vertical", "app")
# a page kind whose film isn't the starter's film.tsx: app is a light interface in a window, cut down from an earlier film, Clearing
PAGE_FILMS = {"app": "app.tsx"}
PY = sys.executable
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
ENGINE_NOTE = Path(os.environ["VD_ENGINE_NOTE"]) if os.environ.get("VD_ENGINE_NOTE") else None   # a note saying how to reach a stay-open look server, if a machine has one
SR = 48000
# The one level every film is held to, by vd sound, the scan after export and the pages: -15 LUFS within 1 LU either way,
# true peak under -1 dB. vd sound said "aim -14" while the scan and the pages said -15. The mix is levelled with a true
# peak of -2.5, because the export's AAC encode lifts peaks (plusone's wav, at -3.1, came out at -0.6 after export).
LUFS_AIM, LUFS_WITHIN, PEAK_UNDER, PEAK_BUILD = -15.0, 1.0, -1.0, -2.5
# What the tools render goes here, not under the film's folder (new and pin write the film's own files, and sound and
# render leave one small source stub beside it): raea's bundle key is the stat of every
# .ts/.tsx/.js/.json/.css under the entry's folder, so one manifest written beside the film (raea writes OUT.render.json
# next to every output) forces the next look or render to copy and rewrite the whole SDK again (+3-4 s, 20 s under load,
# measured here).
OUTROOT = Path(os.environ.get("VD_OUT") or Path.home() / ".vd" / "out")


OWNER = "film-folder.txt"   # in a film's output folder: the film folder it belongs to


BUSY = "exporting.txt"       # what holds the lock below, for the message a second command prints; never what keeps it out
LOCK = "exporting.lock"


class Busy(Exception):
    """Another process holds this film's output folder. Its text is what that process wrote of itself, or ""."""


@contextlib.contextmanager
def held(out, what):
    """The film's output folder, held by this process until the block ends: one export or stretch render of a film at a
    time, and nobody's picture cleared from under it. The system keeps the lock (a file held open and locked) and lets
    it go when the process ends, however it ends, so nothing is left to go stale. A note that named the process did
    go stale, and two commands that both found it stale could both take it over (a review's finding). Raises Busy
    without waiting when another process has it."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    f = open(out / LOCK, "a+b")
    try:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            try:
                said = (out / BUSY).read_text(encoding="utf-8").strip()
            except OSError:
                said = ""
            raise Busy(said) from None
        note = out / BUSY
        try:
            note.write_text(f"vd {what} (process {os.getpid()})\n", encoding="utf-8")
        except OSError:
            pass
        try:
            yield
        finally:
            try:
                note.unlink(missing_ok=True)        # ours: nobody else writes it while the lock is held
            except OSError:
                pass
    finally:
        f.close()                                   # the lock goes with the open file


@contextlib.contextmanager
def one_export(out, what):
    """One export or stretch render of a film at a time. Two at once took the same cut number and wrote the same part
    files, and whichever failed removed the other's: the render queue orders the drawing, not the whole command."""
    with contextlib.ExitStack() as stack:
        try:
            stack.enter_context(held(out, what))
        except Busy as b:
            raise SystemExit(f"stopped: {str(b) or 'another command'} is already running on this film, and two at once write over each other's cut. "
                             "Wait for it to end, or stop it, then run this again. Nothing was made.") from None
        yield


def alone_in(where, what):
    """A command that runs holding its film's output folder (one_export); where(a) is that folder."""
    def wrap(fn):
        def cmd(a):
            with one_export(where(a), what):
                return fn(a)
        cmd.__name__, cmd.__doc__ = fn.__name__, fn.__doc__
        return cmd
    return wrap


def outdir(d):
    """~/.vd/out/NAME, where everything made for the film folder NAME goes. The name is all that tells two film folders
    apart there, so the folder keeps a note of whose it is. When a film folder of the same name from another place
    comes, the note is rewritten and what the first left for reuse (its drawn picture, its built sound) is dropped:
    an export checks only that a kept picture is newer than its sources, and would have put this film's sound on the
    other film's picture. One line says so. Only what an export makes again is removed (a picture an export drew, the
    built sound, the scan); everything else of the other film's (its cuts, its latest film, share copy and sheets, its
    editor timelines, its evolve keys, a picture with no record of its draw) is moved aside to earlier-folder/N, so this
    folder's vd clean --keep-cuts never counts the other film's cuts as its own (a review's finding: B/Twin's cut 2
    made A/Twin's only cut "older" and clean removed it)."""
    d = Path(d).resolve()
    o = OUTROOT / d.name
    o.mkdir(parents=True, exist_ok=True)
    note, mine = o / OWNER, os.path.normcase(str(d))
    try:
        was = note.read_text(encoding="utf-8").strip() if note.exists() else None
    except OSError:
        was = None
    if was is None:
        try:
            note.write_text(str(d) + "\n", encoding="utf-8")
        except OSError:
            pass
    elif os.path.normcase(was) != mine:
        # held while it is cleared: a second folder's command, refused a moment later because the first was exporting,
        # had already removed the picture and sound that export was about to join (a review's finding)
        try:
            with held(o, f"taking {o.name} over for {d}"):
                # the other film's latest cut, its share copy, sheets and scan are copies or readings of what cuts/ keeps,
                # and left here they read as this folder's (an export that failed said "NAME.mp4 is still cut 1" of the
                # other film); its evolve keys are kept, moved aside, since nothing else holds them
                # each takeover its own folder: a second takeover once replaced the first one's keys there
                aside = next(o / "earlier-folder" / str(n) for n in range(1, 10000) if not (o / "earlier-folder" / str(n)).exists())
                drawn = [f for f in o.glob("*.picture.mp4") if is_drawn(f)]
                undrawn = [f for f in o.glob("*.picture.mp4") if f not in drawn]
                keep = [*o.glob("evolve-*-KEY.txt"), *o.glob("evolve-*-divergence.json"), o / "bridge", o / "cuts",
                        *hand_in_files(o / f"{d.name}.mp4"), *undrawn, *(picture_note(f) for f in undrawn)]
                for f in keep:
                    if os.path.lexists(f):
                        aside.mkdir(parents=True, exist_ok=True)
                        try:
                            os.replace(f, aside / f.name)
                        except OSError as e:
                            raise SystemExit(f"stopped: {o} holds the work of another film folder called {d.name} ({was}), and {f.name} could not be "
                                             f"moved aside to {aside} ({e.strerror or e}): something has it open. Close it, or give this folder another name, "
                                             "then run this again.") from None
                for f in [*drawn, *(picture_note(f) for f in drawn), o / "sound.wav", o / "sound-raw.wav", o / "scan.txt", o / "sound.txt"]:
                    try:
                        f.unlink(missing_ok=True)
                    except OSError as e:
                        raise SystemExit(f"stopped: {o} holds the picture and sound of another film folder called {d.name} ({was}), and {f.name} could not be "
                                         f"cleared ({e.strerror or e}): something has it open. Close it, or give this folder another name, then run this again.") from None
                try:
                    note.write_text(str(d) + "\n", encoding="utf-8")
                except OSError:
                    pass
        except Busy as b:
            raise SystemExit(f"stopped: another film folder called {d.name} ({was}) is making its film in {o} right now ({str(b) or 'a command that left no note'}), "
                             "and this folder's command would clear its picture and sound from under it. Wait for it to end, or give this folder another name. "
                             "Nothing was changed.") from None
        print(f"vd: {o} held the outputs of another film folder called {d.name} ({was}). It is this folder's now: the picture and sound kept there for "
              "reuse and its scan were dropped, so none of the other film's is taken for this one's; its cuts, latest film, share copy, sheets, "
              "timelines and evolve keys are in earlier-folder/N/, and this folder's cuts start again at 1. "
              "Two films on one machine want two names.", file=sys.stderr, flush=True)
    return o


def write_if_changed(path, text):
    """A stub raea must find beside the entry (_tone.tsx, _range.tsx): rewritten only when its content changes, so an
    unchanged one doesn't force a new bundle."""
    path = Path(path)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- usage log

def usage_log(cmd, film, seconds, path=None):
    """One line a command: ISO time, command, film folder, seconds. Never fails the command it records."""
    path = Path(path) if path else Path.home() / ".vd" / "usage.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{cmd}\t{film or '-'}\t{seconds:.1f}\n")
    except OSError:
        pass


NOT_PROVEN = {"borrow", "capture", "launch", "foley", "evolve", "playable", "audio", "bridge"}   # SKILL.md, "Newer commands"
LEAN_ONLY = {"look", "export", "pack", "pin", "profile", "scan", "clean", "borrow", "steal", "capture", "launch", "foley", "evolve", "playable", "audio", "bridge"}


def claims(argv):
    """Whether a `vd` command line is one of the lean commands (the old ones keep their own meaning)."""
    if not argv:
        return False
    cmd, rest = argv[0], argv[1:]
    if cmd in LEAN_ONLY:
        return True
    if cmd == "new":
        return any(r in ("--kind", "--like") or r.startswith(("--kind=", "--like=")) for r in rest)
    if cmd == "render":
        return "--from" in rest or "--to" in rest
    if cmd == "measure":
        return "--against" in rest or any(r.lower().endswith((".mp4", ".mov", ".mkv")) for r in rest)
    if cmd == "sound":
        return "--onto" in rest or any(r.lower().endswith((".tsx", ".ts", ".jsx")) for r in rest) or ("--palette" not in rest and "--project" not in rest and film_dir(None, required=False) is not None)
    return False


# ---------------------------------------------------------------- the film folder

def film_dir(given, required=True):
    if given:
        d = Path(given).resolve()
        if (d / "score.json").exists():
            return d
        if required:
            raise SystemExit(f"{d} has no score.json: make a film folder with `vd new NAME --kind KIND`")
        return None
    d = Path.cwd().resolve()
    for p in (d, *d.parents):
        if (p / "score.json").exists():
            return p
    if required:
        raise SystemExit("no score.json here or above: run this inside a film folder (vd new NAME --kind KIND), or pass --film DIR")
    return None


def score_of(d):
    return json.loads((d / "score.json").read_text(encoding="utf-8"))


def entry_of(d):
    return d / "main.tsx" if (d / "main.tsx").exists() else d / "film.tsx"


def where(a, need_score=False):
    """(folder, entry, score or None) for a command: ENTRY.tsx when one is given (any film, made by hand or not), else the
    film folder's main.tsx. score.json is read when it is there; only the commands that are built from it need it."""
    e = getattr(a, "entry", None)
    if e:
        entry = Path(e).resolve()
        if not entry.is_file():
            raise SystemExit(f"no such composition: {entry}")
        d = entry.parent
        s = score_of(d) if (d / "score.json").exists() else None
    else:
        d = film_dir(getattr(a, "film", None), required=need_score)
        if d is None:
            raise SystemExit("give the composition: vd COMMAND ENTRY.tsx --composition ID (or run inside a folder made by vd new, which has score.json)")
        entry, s = entry_of(d), score_of(d)
    if need_score and s is None:
        raise SystemExit(f"this needs a score.json beside {entry.name} (vd new writes one)")
    return d, entry, s


def shape_changes(world_json, fps=None):
    """Lines for the named 3D parts whose own size (the mesh before its transform's scale, raea world's Part.own) differs
    between frames. raea builds a mesh once and keeps it: one film's ring, <Torus major_radius={r(t)} />, kept the radius of the
    first frame drawn, and stills taken in one look call showed whatever size the first requested frame gave, so looks
    disagreed and hid it for two reader rounds. One film's maker hit the same with a Text3D whose words change."""
    try:
        frames = json.loads(world_json)
    except ValueError:
        return []
    sizes = {}
    for fr in frames if isinstance(frames, list) else [frames]:
        for e in fr.get("entities", []):
            part = (e.get("components") or {}).get("Part") or {}
            own, name = part.get("own"), part.get("name")
            if name and own and len(own) == 2:
                sizes.setdefault(name, []).append((fr.get("frame", 0), [round(b - a, 3) for a, b in zip(own[0], own[1])]))
    said = []
    at = (lambda f: f"{f / fps:.1f} s") if fps else (lambda f: f"frame {f}")
    for name, seen in sizes.items():
        (f0, s0), changed = seen[0], [(f, s) for f, s in seen[1:] if any(abs(x - y) > 1e-3 * max(1.0, abs(x)) for x, y in zip(seen[0][1], s))]
        if changed:
            f1, s1 = changed[-1]
            dims = lambda s: " x ".join(f"{v:g}" for v in s)
            said.append(f"{name}: its own size {dims(s0)} at {at(f0)}, {dims(s1)} at {at(f1)}; raea builds a mesh once and keeps the "
                        f"first: fix the shape and size it with withScale (a Text3D whose words change: one per wording, named after its words)")
    return said


def preflight(entry, comp=None, frame=0, frames=None, fps=None):
    """raea's own checks that need no render, run before a render takes its place in the queue: `scene lint` (3D parts
    floating, sunk, clipping; and the bundle itself) and `world --no-render` (the frame laid out as a world). A maker once
    waited 14 minutes in the queue for a render refused in 6 seconds for their own mistake. (ok, seconds, what failed)."""
    import raea_run
    if os.environ.get("VD_NO_PREFLIGHT") == "1":
        return True, 0.0, ""
    raea = raea_run.checked_binary(say=False)
    extra = (["--composition", comp] if comp else []) + ["--frame", str(frame)]
    # world lays out every moment of the look (no render), so a part whose shape changes between them is named
    span = (["--composition", comp] if comp else []) + (["--at", ",".join(map(str, frames)), "--json"] if frames and len(frames) > 1 else ["--frame", str(frame)])
    env = raea_run.raea_env()
    t0 = time.monotonic()
    procs = [(name, subprocess.Popen([raea, *cmd, entry.name, *args, *tail], cwd=entry.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW))
             for name, cmd, args, tail in (("scene lint", ["scene", "lint"], extra, []), ("world", ["world"], span, ["--no-render"]))]
    bad, notes = [], []
    for name, pr in procs:
        try:
            out, _ = pr.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            # a check that did not finish has not passed: killed and not waited for, its return code was still None,
            # which read as success, and the render was let through
            pr.kill()
            try:
                pr.communicate(timeout=30)
            except (subprocess.TimeoutExpired, OSError, ValueError):
                pass
            bad.append(f"raea {name}: timed out after 300 s, so it checked nothing (run it again; if it hangs every time, run `raea {name}` on the entry by hand)")
            continue
        if name == "world" and pr.returncode == 0:
            notes += [f"shape: {l}" for l in shape_changes(out, fps)]
        if pr.returncode == 0 or (name == "scene lint" and "has no 3D" in out):   # a page film has nothing for scene lint
            continue
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        refused = [l for l in lines if any(w in l for w in ("REFUSED", "couldn't", "timed out", "threw", "Error:"))]
        if name == "world" or refused:
            # what the render would refuse too: the bundle doesn't build, the composition throws, the frame can't be laid out
            bad.append(f"raea {name}: " + " | ".join((refused or lines[-3:])[:4]))
        else:
            # scene lint's placement findings (a part floating, sunk or clipping) don't stop a render, and a film that
            # rendered for its maker had several by design: said, not stopped on
            notes.append(f"raea {name} (not stopping): " + " | ".join(lines[:3]))
    for n in notes:
        print(n[:600], file=sys.stderr)
    return not bad, time.monotonic() - t0, "\n".join(bad)


def room(entry, need_gb, what, out=None):
    """Refuse before the queue when a drive the job writes to (the film's folder, the output folder, the temp folder) has
    under `need_gb` free. At 05:51 one night drive C had 0 bytes free, and a look learnt it from raea after its checks
    had passed ("There is not enough space on the disk"). The skill keeps no frame folders: export renders in one pass
    and look deletes its stills; what stays under the output folder is each cut's film, share copy, sheets and picture."""
    import tempfile
    seen = {}
    for place in (Path(entry).resolve().parent, OUTROOT, Path(tempfile.gettempdir()), *([Path(out).resolve()] if out else [])):
        try:
            place.mkdir(parents=True, exist_ok=True)
            # one line a disk, told apart by the disk itself: by a path's anchor every folder on macOS and Linux was "/",
            # and a full volume mounted elsewhere was never looked at
            disk = os.stat(place).st_dev
            if disk not in seen:
                seen[disk] = (Path(place.anchor) if os.name == "nt" else place, shutil.disk_usage(place).free / 1e9)
        except OSError:
            pass
    shown = {}
    for label, free in seen.values():                # two disks can share a label (a folder mounted on a drive): keep the lower
        shown[label] = min(free, shown.get(label, free))
    seen = shown
    low = {k: v for k, v in seen.items() if v < need_gb}
    if not low:
        return
    def size(folder):
        return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / 1e9
    big = sorted(((size(f), f) for f in OUTROOT.iterdir() if f.is_dir()), reverse=True)[:3] if OUTROOT.is_dir() else []
    raise SystemExit(f"stopped before the render queue: {', '.join(f'{k} has {v:.1f} GB free' for k, v in low.items())}, and this {what} needs "
                     f"about {need_gb:.1f} GB (estimated: 5 MB a second of film for each of the picture, the film and its share copy, "
                     f"and 1 GB for raea's own temporary files). The largest folders under {OUTROOT}: "
                     + (", ".join(f"{f.name} ({g:.1f} GB)" for g, f in big) or "none")
                     + ". The skill keeps no frame folders; a filed cut's folder there can go once its film is kept elsewhere.")


def must_preflight(entry, comp, frame=0, frames=None, fps=None):
    ok, secs, why = preflight(entry, comp, frame, frames, fps)
    if not ok:
        raise SystemExit(f"stopped before the render queue ({secs:.1f} s of checks, no render):\n{why}")
    if secs:
        print(f"preflight: scene lint and world ran in {secs:.1f} s, before the queue; nothing a render would refuse", file=sys.stderr)


def run(args, **kw):
    try:
        return subprocess.run([str(a) for a in args], creationflags=NO_WINDOW, **kw)
    except FileNotFoundError:
        # ffmpeg or ffprobe not on PATH: said in one line, where it used to be a traceback part-way through a step
        raise SystemExit(f"{Path(str(args[0])).name} is not on this machine's PATH and this step needs it: `vd doctor` says how to get it") from None


def streamed(args, **kw):
    """Run a tool whose stderr is what the person should see while it works (the render queue's "queue: waiting 30 s;
    held by ..." and raea's own progress): shown line by line as it comes, and kept; stdout kept. A CompletedProcess.
    vd look and vd export captured both and printed them after the wait was over, so a person waiting in the queue saw
    nothing of who held it."""
    import threading
    p = subprocess.Popen([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                         errors="replace", creationflags=NO_WINDOW, **kw)
    err = []

    def pump():
        for line in p.stderr:
            err.append(line)
            print(line, end="", file=sys.stderr, flush=True)
    th = threading.Thread(target=pump, daemon=True)
    th.start()
    out = p.stdout.read()
    p.wait()
    th.join(timeout=10)
    return subprocess.CompletedProcess(p.args, p.returncode, out, "".join(err))


def split_wait(total, line):
    """(seconds waiting in the queue, seconds rendering) from raea_run's last line ("OK 87.1s ...", rendering alone,
    timed once the queue was ours) and the whole call's time, or None. One film's cut 2 exported in 557 s against 87 s for cut
    1, and nothing said how much of it was waiting for other films."""
    m = re.match(r"(?:OK|FAILED)\s+([\d.]+)s", line or "")
    if not m:
        return None
    r = float(m.group(1))
    return max(0.0, total - r), r


def hand_in(dest):
    """What a hand-in asks for, beside the film (one maker made both by hand): NAME-share.mp4 (an earlier film's make.sh's
    line: x264 CRF 20, the sound copied, faststart; the BT.601 tags kept) and the timed sheets at four frames a second,
    16 tiles a sheet, 1920 x 1080 (the hand-in's own layout; vd pack gives readers the story at two a second and the
    motion frame by frame). (share copy, sheets)."""
    share = dest.with_name(dest.stem + "-share.mp4")
    run([PY, "-X", "utf8", TOOLS / "heavy.py", "--stall", "180", "--", "ffmpeg", "-y", "-v", "error", "-i", dest, "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-color_primaries", "smpte170m", "-color_trc", "smpte170m", "-colorspace", "smpte170m", "-c:a", "copy",
         "-movflags", "+faststart", share], check=True)
    for old in sheets_of(dest):      # one sheet keeps its name; several are NAME-sheet_000.jpg ...
        old.unlink()
    run([PY, "-X", "utf8", TOOLS / "sheet.py", dest, "-o", dest.with_name(dest.stem + "-sheet.jpg"), "--fps", "4", "--cols", "4", "--rows", "4",
         "--width", "480"], check=True, capture_output=True)
    return share, sheets_of(dest)


def sheets_of(film):
    """FILM's timed sheets beside it, NAME-sheet.jpg or NAME-sheet_NNN.jpg, matched as text: a glob built from the name
    took another film's sheets when the name held [ or ? (draft[1] matched draft1), a review's finding."""
    film = Path(film)
    return sorted(_named(film.parent, film.stem, r"-sheet(_\d+)?\.jpg"))


def raea_render(d, entry, out, *flags, env=None):
    """One render through the machine's queue (raea_run.py). Returns (ok, seconds, last line)."""
    t0 = time.monotonic()
    p = streamed([PY, "-X", "utf8", TOOLS / "raea_run.py", entry, "-o", out, *flags], cwd=d, env={**os.environ, **(env or {})})
    lines = [l for l in p.stdout.splitlines() if l.strip()] or [l for l in p.stderr.splitlines() if l.strip()]
    return p.returncode == 0, time.monotonic() - t0, (lines[-1] if lines else "")


# ---------------------------------------------------------------- new

LIBRARY = SKILL / "library"
# what kit/ holds for every page kind: the page library itself (raea refuses imports from outside the entry's folder,
# so a film that can't import the library writes its own; copied, it is beside the entry and the film can change it)
PAGE_KIT = {"base.tsx": STARTER / "base.tsx", "lib": LIBRARY / "lib", "motions": LIBRARY / "motions", "transitions": LIBRARY / "transitions",
            "finish.gen.ts": LIBRARY / "finish.gen.ts", "standins": LIBRARY / "standins",
            # the faces lib/faces.ts embeds keep their licence texts beside them
            "lib/Inter-OFL.txt": LIBRARY / "media" / "fonts" / "Inter-OFL.txt", "lib/JetBrainsMono-OFL.txt": LIBRARY / "media" / "fonts" / "JetBrainsMono-OFL.txt"}


def copy_any(src, dst):
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


IMPORT = re.compile(r"""(?:from|import)\s+["'](\.[^"']+)["']""")


def resolves(f, spec):
    base = (f.parent / spec).resolve()
    return any(Path(str(base) + ext).is_file() for ext in ("", ".ts", ".tsx", ".js", "/index.ts", "/index.tsx"))


def prune_unresolved(kit):
    """Remove the kit files whose relative imports, followed through, can't resolve: some of the page library still
    imports what only the old outline-kit build made (fonts.gen, media.gen, outline.json) or parts the cut removed.
    A file that can't bundle is worse than no file. Returns what was removed, relative to the kit."""
    gone = []
    while True:
        bad = [f for f in list(kit.rglob("*.ts")) + list(kit.rglob("*.tsx"))
               if any(not resolves(f, spec) for spec in IMPORT.findall(f.read_text(encoding="utf-8", errors="replace")))]
        if not bad:
            return sorted(gone)
        for f in bad:
            gone.append(f.relative_to(kit).as_posix())
            f.unlink()


MADE = []   # what this command made; main prints the last one as the command's last line (one film's maker hunted for paths)


def made_it(path):
    MADE.append(Path(path))
    return path


def kind_line(kind):
    """One line on what a kind starts and what a look of it costs. Every kind is a page film."""
    return f"{kind} starts a page film (type and shapes on a moving page): a look draws about 1 s a moment after a 5 s bundle on the laptop it was timed on."


FILMS = LIBRARY / "films"   # whole worked films, each a folder that draws as it is: vd new NAME --like FILM copies one
# the MIT notice for the library's code: every film folder holds a copy of that code, so the notice goes with it
CODE_NOTICE, NOTICE_NAME = LIBRARY / "LICENSE-library.txt", "LICENSE-video-decompiler.txt"


def give_notice(d):
    if not (d / NOTICE_NAME).exists():
        shutil.copy2(CODE_NOTICE, d / NOTICE_NAME)


def worked_films():
    """{name: one line on it} for every film under library/films: the first line of its README.md that is not a
    heading, else its folder's name."""
    out = {}
    for f in sorted(FILMS.iterdir()) if FILMS.is_dir() else []:
        if not f.is_dir() or not ((f / "main.tsx").exists() or (f / "film.tsx").exists()):
            continue
        line = f.name
        readme = f / "README.md"
        if readme.is_file():
            line = next((l.strip() for l in readme.read_text(encoding="utf-8", errors="replace").splitlines()
                         if l.strip() and not l.lstrip().startswith("#")), f.name)
        out[f.name] = line
    return out


def files_now(d):
    return {p.relative_to(d).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size) for p in d.rglob("*") if p.is_file()}


def cmd_new_like(a):
    """A copy of a whole worked film. Its sound.py, when it has one, runs in the copy (the wav is not shipped, and every worked
    film's sound.py also writes the times its picture imports); the one wav it writes under media/ becomes the score's sound_file,
    which vd export copies on as it is: the films master their own sound (to -15 LUFS; linden to the -17.5 it was accepted at), and score.json's own sound list is
    empty, so the export would otherwise have mixed silence."""
    films = worked_films()
    if a.like not in films:
        raise SystemExit(f"no worked film called {a.like!r} under {FILMS}: " + (", ".join(films) or "there are none"))
    src, d = FILMS / a.like, Path(a.name).resolve()
    if d.exists():
        raise SystemExit(f"{d} exists: give a name that doesn't, so nothing of yours is written over")
    t0 = time.monotonic()
    shutil.copytree(src, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    give_notice(d)
    print(f"film folder {d}: a copy of {a.like}" + (f", {films[a.like]}" if films[a.like] != a.like else " (its README.md, once it has one, says what it is)"))
    if (d / "sound.py").exists():
        before, t1 = files_now(d), time.monotonic()
        p = run([PY, "-X", "utf8", "sound.py"], cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise SystemExit(f"its sound.py failed after {time.monotonic() - t1:.1f} s (the copy is in {d}; fix and run `python sound.py` there):\n"
                             + "\n".join((p.stdout + p.stderr).strip().splitlines()[-8:]))
        after = files_now(d)
        wrote = sorted(f for f, v in after.items() if before.get(f) != v)
        print(f"sound.py ran in {time.monotonic() - t1:.1f} s and wrote {', '.join(wrote) or 'nothing'}" + (": " + p.stdout.strip().splitlines()[0][:160] if p.stdout.strip() else ""))
        wavs = [f for f in wrote if f.startswith("media/") and f.endswith(".wav")]
        if len(wavs) == 1 and (d / "score.json").exists():
            s = score_of(d)
            if not s.get("sound_file"):
                s["sound_file"] = wavs[0]
                (d / "score.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
                print(f"score.json: sound_file is {wavs[0]}, which vd export copies on as it is (change the sound in sound.py and run it again)")
    if (d / "score.json").exists():
        s = score_of(d)
        look = "-look`}" in entry_of(d).read_text(encoding="utf-8", errors="replace")
        print(f"{s.get('width')}x{s.get('height')}, {s.get('fps')} fps, {s.get('duration')} s; composition {s.get('composition') or 'film'}"
              + (" (vd look draws film-look: the film without its grain, where it has one)" if look else "") + ". BOARD.md, where there is one, says how it was made.")
    print(f"What the tools write goes to {OUTROOT / d.name}, outside the film's folder. ({time.monotonic() - t0:.1f} s)")
    print(f"Next:\n  cd {d}\n  vd look --at 2,9,14      moments as one picture\n  vd export                the finished film, scanned for pops, holds and level\n"
          f"  vd pack {OUTROOT / d.name / (d.name + '.mp4')} --against REF.mp4   a blind line-up (lineup/A..D, up to three --against) and ours alone (alone/)")
    return made_it(d)


def cmd_new(a):
    if getattr(a, "like", None):
        return cmd_new_like(a)
    d = Path(a.name).resolve()
    if d.exists() and any(d.iterdir()):
        raise SystemExit(f"{d} exists and is not empty")
    (d / "media").mkdir(parents=True, exist_ok=True)
    for f in ("main.tsx", "ids.ts"):
        shutil.copy2(STARTER / f, d / f)
    bare = getattr(a, "bare", False) and a.kind != "app"     # the frame, the clock and the finish only, for a diagram
    shutil.copy2(STARTER / ("bare.tsx" if bare else PAGE_FILMS.get(a.kind, "film.tsx")), d / "film.tsx")
    for name, src in PAGE_KIT.items():
        copy_any(src, d / "kit" / name)
    dropped = prune_unresolved(d / "kit")
    if dropped:
        print(f"kit/: left out {len(dropped)} library files that import what this build doesn't make: {', '.join(dropped)}")
    score = json.loads((STARTER / "scores" / f"{a.kind}.json").read_text(encoding="utf-8"))
    note = "It renders as it is. kit/ holds the starter kit (base.tsx) and the page library (lib, motions, transitions); TECHNIQUES.md lists them."
    (d / "score.json").write_text(json.dumps(score, indent=1), encoding="utf-8")
    give_notice(d)
    print(f"film folder {d} ({a.kind}, {score['width']}x{score['height']}, {score['fps']} fps, {score['duration']} s). {note}")
    print(kind_line(a.kind))
    print(f"What the tools write goes to {OUTROOT / d.name}, outside the film's folder; score.json is the one JSON kept beside the film.")
    print("Next: change score.json (beats, words, sounds), then `vd look`, `vd sound`, `vd export`. SKILL.md says which page to read at each step.")
    return made_it(d)


# ---------------------------------------------------------------- look

def stay_open_engine():
    """A stay-open look server, when VD_ENGINE_NOTE names a note that says how to reach one. Otherwise None, and look
    draws the ordinary way (one raea process for all the moments)."""
    if not ENGINE_NOTE or not ENGINE_NOTE.exists():
        return None
    text = ENGINE_NOTE.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?mi)^look-server:\s*(\S+)", text)   # the line the engine note (VD_ENGINE_NOTE) is asked to carry
    return m.group(1) if m else None


def default_moments(score):
    """A moment early in each beat and one at its middle: where a viewer first sees the beat, and where it rests. A score
    with no beats (a worked film keeps its clock in its own code) gets six moments spread over the film."""
    out = []
    for b in score.get("beats") or []:
        out += [round(b["from"] + min(0.4, (b["to"] - b["from"]) / 3), 2), round((b["from"] + b["to"]) / 2, 2)]
    return out or [round(score["duration"] * (i + 0.5) / 6, 2) for i in range(6)]


def cmd_look(a):
    d, entry, s = where(a)
    comp = a.composition or (s or {}).get("composition") or ("film" if s else None)
    if a.at:
        times = [float(x) for x in a.at.split(",")]
    elif s:
        times = default_moments(s)
    else:
        raise SystemExit("give --at (seconds, comma separated): with no score.json there are no beats to choose moments from")
    fps = (s or {}).get("fps") or look_fps(entry, comp)
    last = int(round(s["duration"] * fps)) - 1 if s else None
    frames = sorted({min(int(round(t * fps)), last) if last is not None else int(round(t * fps)) for t in times})
    out = Path(a.out).resolve() if a.out else outdir(d) / "look.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    maker, times = d / "sound.py", d / "kit" / "times.gen.ts"
    if maker.exists() and times.exists() and maker.stat().st_mtime > times.stat().st_mtime:
        # an export stops on this; a look goes on, and used to say nothing while it drew the old beats
        print(f"look: sound.py changed after kit/times.gen.ts was made, so this picture is drawn from the beats as they were. To draw the new ones first:\n{run_sound_py(d)}",
              file=sys.stderr, flush=True)
    room(entry, 0.5, "look", out.parent)
    must_preflight(entry, comp, frames[0], frames, fps)
    # the starter's film-look is the film without its grain: the masks keep only the frontmost layer, and a grain over
    # the whole frame blinded the report on every tile of a film that kept the starter's finish (seen on one film)
    if comp and not a.composition and f'id={{`${{FILM_ID}}-look`}}' in entry.read_text(encoding="utf-8", errors="replace") and comp == "film":
        comp = "film-look"
        print("look: drawn as film-look (the film without its grain, where it has one), so the report can see under it")
    server = stay_open_engine()
    if server:
        print(f"the engine note names a stay-open look ({server}); this build of look does not speak it yet, so it draws the ordinary way")
    p = streamed([PY, "-X", "utf8", TOOLS / "look.py", entry, "--at", ",".join(map(str, frames)), "--frames", *(["--composition", comp] if comp else []), "-o", out,
                  *(["--all"] if getattr(a, "all", False) else [])], cwd=d)
    print(p.stdout.strip())                     # its stderr (the queue's waiting, raea's notes) was shown as it came
    if p.returncode == 0:
        made_it(out)
    return p.returncode


def look_fps(entry, comp):
    import look
    return look.fps_of(entry, comp)


# ---------------------------------------------------------------- sound

def made(kind, pitch, dur=None, seed=1):
    """A small made sound, mono float32 at SR: hit, tick, ping, whoosh, drone. Free and repeatable."""
    import numpy as np
    rng = np.random.default_rng(seed)
    if kind == "tick":
        n = int(0.06 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * pitch * t) * np.exp(-t * 90)).astype(np.float32)
    if kind == "ping":
        n = int((dur or 1.4) * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * pitch * t) + 0.35 * np.sin(2 * np.pi * pitch * 2.01 * t) + 0.12 * np.sin(2 * np.pi * pitch * 3.03 * t)
        return (x * np.exp(-t * 3.2) * np.minimum(1, t / 0.004) / 1.5).astype(np.float32)
    if kind == "hit":
        n = int((dur or 1.2) * SR); t = np.arange(n) / SR
        body = np.sin(2 * np.pi * pitch * t * (1 + 0.6 * np.exp(-t * 18))) * np.exp(-t * 4.5)
        noise = rng.standard_normal(n) * np.exp(-t * 28) * 0.5
        return ((body + noise) * np.minimum(1, t / 0.002) / 1.4).astype(np.float32)
    if kind == "whoosh":
        n = int((dur or 0.7) * SR); t = np.arange(n) / SR
        x = np.convolve(rng.standard_normal(n), np.ones(24) / 24, mode="same")
        return (x * np.sin(np.pi * t / t[-1]) ** 2 * 1.6).astype(np.float32)
    if kind == "drone":
        n = int((dur or 10) * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * pitch * t) + 0.6 * np.sin(2 * np.pi * pitch * 1.5 * 1.003 * t) + 0.4 * np.sin(2 * np.pi * pitch * 2.002 * t)
        x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
        fade = np.minimum(1, np.minimum(t / 1.5, (t[-1] - t) / 1.5))
        return (x * fade / 2.2).astype(np.float32)
    raise SystemExit(f"no made sound called {kind!r}: hit, tick, ping, whoosh or drone")


def read_audio(path, start=0.0):
    """Any file ffmpeg reads, as stereo float32 at SR."""
    import numpy as np
    p = run(["ffmpeg", "-v", "error", "-ss", str(start), "-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    if p.returncode:
        raise SystemExit(f"ffmpeg could not read {path}: {p.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(p.stdout, np.float32).reshape(-1, 2).copy()


def place(mix, x, at, gain_db):
    import numpy as np
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    i = int(round(at * SR))
    if i >= len(mix):
        return
    j = max(0, -i)
    x = x[j:]
    i = max(0, i)
    n = min(len(x), len(mix) - i)
    mix[i:i + n] += x[:n] * (10 ** (gain_db / 20))


def word_mask(words, n, ramp=0.08, pad=0.05):
    """1 where a word is being said (padded), 0 between, with short ramps: the curve the bed ducks by."""
    import numpy as np
    m = np.zeros(n, np.float32)
    for w in words:
        a, b = int(max(0, (w["start"] - pad)) * SR), int(min(n / SR, w["end"] + pad) * SR)
        m[a:b] = 1
    k = max(1, int(ramp * SR))
    return np.convolve(m, np.ones(k) / k, mode="same").clip(0, 1)


def env_db(x, win=0.01):
    """The mix's level every `win` seconds, in dBFS (RMS of both channels)."""
    import numpy as np
    mono = x.mean(1) if x.ndim == 2 else x
    k = int(win * SR)
    n = len(mono) // k
    r = np.sqrt((mono[: n * k].reshape(n, k) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(r)


def hit_report(env, wanted, win=0.01, before=0.08, after=0.35, lead=0.3):
    """For each wanted hit (name, at): where it starts near `at`, and how far off that is, in ms. A sound is placed by its
    start, so its start is checked: the first moment in the window where the level rises above the level just before the
    window (the floor) by max(6 dB, half the way to the window's peak). One film: a whoosh peaks in its middle and a tick
    under a piano note peaks with the note, so checking the peak flagged both 300 ms off. With no such rise, the peak."""
    import numpy as np
    rows = []
    for name, at in wanted:
        a, b = max(0, int((at - before) / win)), min(len(env), int((at + after) / win) + 1)
        if b <= a:
            rows.append((name, at, None, None))
            continue
        w = env[a:b]
        pre = env[max(0, a - int(lead / win)):a]
        floor = float(np.median(pre)) if len(pre) else float(w.min())
        peak = float(w.max())
        bar = floor + max(6.0, 0.5 * (peak - floor))
        up = np.nonzero(w >= bar)[0]
        k = a + int(up[0] if len(up) else w.argmax())
        rows.append((name, at, k * win, round((k * win - at) * 1000)))
    return rows


def pause_report(env, words, win=0.01, min_gap=0.25, trim=0.04):
    """Each pause between words at least `min_gap` long: its level against the words' level around it, in dB."""
    import numpy as np
    rows = []
    for w0, w1 in zip(words, words[1:]):
        g0, g1 = w0["end"] + trim, w1["start"] - trim
        if g1 - g0 < min_gap - 2 * trim:
            continue
        gap = env[int(g0 / win):int(g1 / win)]
        said = np.concatenate([env[int((w0["start"]) / win):int(w0["end"] / win)], env[int(w1["start"] / win):int(w1["end"] / win)]])
        if len(gap) and len(said):
            rows.append((round(w0["end"], 2), round(w1["start"], 2), round(float(np.median(gap) - np.median(said)), 1)))
    return rows


def holes(env, win=0.01, floor=-50.0, longest=0.4, skip_end=0.3):
    """Silent stretches inside the film: runs below `floor` dBFS at least `longest` seconds (the last `skip_end` s is a tail)."""
    out, start = [], None
    n = len(env) - int(skip_end / win)
    for i in range(n + 1):
        quiet = i < n and env[i] < floor
        if quiet and start is None:
            start = i
        elif not quiet and start is not None:
            if (i - start) * win >= longest:
                out.append((round(start * win, 2), round(i * win, 2)))
            start = None
    return out


def loudness(path):
    """(integrated LUFS, true peak dBTP) by ffmpeg's ebur128."""
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return (float(i[-1]) if i else None, float(tp[-1]) if tp else None)


def tone_audio(d, s, music):
    """Music written for raea's Tone, as sound: raea's sound-only render (`-o OUT.wav`, raea 0.1.1-rc4 and later: React
    stepped for its sounds, no frame drawn) of a stub that imports only the music, cached by the music's source.
    --w/--h can't shrink a render instead: they only size a file with no <Composition> (raea says NOT APPLIED), and a
    2x2 composition stops the video encoder after two frames."""
    src = d / music
    stub = d / "_tone.tsx"
    stamp = hashlib.sha1((src.read_bytes() + json.dumps([s["fps"], s["duration"]]).encode())).hexdigest()[:12]
    wav = outdir(d) / f"tone-{stamp}.wav"
    if wav.exists():
        return wav, 0.0
    mod = "./" + Path(music).with_suffix("").as_posix()
    write_if_changed(stub, "// written by vd sound: the Tone music alone, rendered as sound only (-o OUT.wav draws no frame)\n"
                    'import { AbsoluteFill, Composition, registerRoot } from "raea";\n'
                    f'import "{mod}";\n'
                    f'registerRoot(() => <Composition id="tone" component={{() => <AbsoluteFill />}} width={{64}} height={{64}} fps={{{s["fps"]}}} durationInFrames={{{int(round(s["duration"] * s["fps"]))}}} />);\n')
    must_preflight(stub, "tone")
    ok, secs, line = raea_render(d, stub, wav)
    if not ok:
        raise SystemExit(f"the Tone music did not render: {line}")
    return wav, secs


FAILS = 2   # `vd sound` checked the sound and it fails: its own exit code, so nothing that reads exit codes takes "sound fails" for a pass


def verdict(text):
    return FAILS if any(l.startswith("sound fails") for l in str(text).splitlines()) else 0


def cmd_sound(a):
    t0 = time.monotonic()
    d, entry, s = where(a)
    if a.entry and not (s and a.from_score):
        # any film: raea's own sound-only render of the entry (its <Audio>, Tone and <Mix>; no frame drawn), then the check
        wav = Path(a.o).resolve() if a.o else outdir(d) / "sound.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        must_preflight(entry, a.composition)
        ok, secs, line = raea_render(d, entry, wav, *(["--composition", a.composition] if a.composition else []))
        if not ok:
            raise SystemExit(f"the sound did not render: {line}")
        said = check_sound(d, s or {"fps": 30}, wav, [f"raea's sound-only render in {secs:.1f} s"], to=wav.with_suffix(".txt"))
        if a.onto:   # -o names the sound here, so the film with it is FILM-sound.mp4 beside the film
            film = Path(a.onto).resolve()
            dest = film.with_name(film.stem + "-sound.mp4")
            mux(film, wav, dest)
            print(f"{dest}: the picture's video stream copied, the sound added")
        print(f"({time.monotonic() - t0:.1f} s, no frame drawn)")
        print(said)
        made_it(dest if a.onto else wav)
        return verdict(said)
    if s is None:
        raise SystemExit("vd sound builds from score.json (vd new writes one); for a film begun by hand give its entry: vd sound ENTRY.tsx --composition ID")
    if s.get("sound_file") and not s.get("voice") and not s.get("music"):
        wav = own_sound(d, s)
        if a.onto:
            film = Path(a.onto).resolve()
            dest = Path(a.o).resolve() if a.o else film.with_name(film.stem + "-sound.mp4")
            mux(film, wav, dest)
            print(f"{dest}: the picture's video stream copied, {s['sound_file']} added ({time.monotonic() - t0:.1f} s)")
            made_it(dest)
            return 0
        said = check_sound(d, s, wav, [f"{s['sound_file']} is this film's own mix (score.json's sound_file), checked as it is; its sound.py makes it"])
        print(f"({time.monotonic() - t0:.1f} s, nothing built)")
        print(said)
        made_it(wav)
        return verdict(said)
    out = outdir(d)
    wav = out / "sound.wav"
    if a.onto:
        build_sound(d, s)                   # every time: a mix built before a voice, a word or a sound changed went onto the film as it was
        film = Path(a.onto).resolve()
        dest = Path(a.o).resolve() if a.o else film.with_name(film.stem + "-sound.mp4")
        mux(film, wav, dest)
        print(f"{dest}: the picture's video stream copied, the sound added ({time.monotonic() - t0:.1f} s)")
        made_it(dest)
        return 0
    report = build_sound(d, s)
    print(f"({time.monotonic() - t0:.1f} s, no picture rendered{' except the Tone music' if s.get('tone') else ''})")
    print(report)
    made_it(wav)
    return verdict(report)


def music_beat(d, s):
    """Stop when a mapped track's beat is not yet the film's: the picture reads its beat from kit/times.gen.ts, which
    the film's sound.py writes from score.json's music, so a track mapped after sound.py last ran sits on another beat."""
    fb = (s.get("music") or {}).get("fb")
    if not (d / "sound.py").is_file():
        return      # a starter keeps its scenes in seconds (score.json's beats), with no beat of its own to move
    have = (gen_data(d).get("CLOCK") or {}).get("FB")
    if fb and have != fb:
        raise SystemExit(f"stopped: score.json's music is {s['music']['source']} at {fb} frames a beat, and kit/times.gen.ts still holds "
                         f"{have}. The film's beat is its sound.py's: run it, so its picture and sound move onto the track's beat, "
                         f"then this again:\n{run_sound_py(d)}")


def build_sound(d, s):
    """Voice, stems and made sounds placed from score.json; a bed and Tone music ducked under the words; the mix
    brought to LUFS_AIM with its true peak at PEAK_BUILD; then the check, written to out/sound.txt and returned."""
    import numpy as np
    n = int(round(s["duration"] * SR))
    voice = np.zeros((n, 2), np.float32)
    under = np.zeros((n, 2), np.float32)      # everything the voice sits on: ducked while words are said
    hits = np.zeros((n, 2), np.float32)       # the sound events: not ducked, they are cued between words
    notes = []
    v = s.get("voice")
    if v:
        v = {"file": v} if isinstance(v, str) else v
        place(voice, read_audio(d / v["file"]), v.get("at", 0.0), v.get("gain", 0.0))
    music = s.get("music")
    if music:
        music_beat(d, s)
    if s.get("sound_file") and not (music and music.get("replace")):
        # a worked film's own mix (its sound.py's) under score.json's voice: the copy's own sound was carried as it was,
        # so a voice added by the pages' route was dropped without a word. Ducked under the words like any bed.
        place(under, read_audio(own_sound(d, s)), 0.0, s.get("sound_file_gain", 0.0))
        notes.append(f"voice {v['file'] if v else '-'} over this film's own mix {s['sound_file']}"
                     + (f", the mix ducked {float(s.get('duck_db', 8.0)):g} dB under the words" if s.get("words") else
                        ", not ducked: score.json lists no words, and the mix is ducked only under their times"))
    for k, e in enumerate(s.get("sounds", [])):
        if not e.get("file") and not e.get("make"):
            continue    # a cue only: a moment the check reads (where the stems or the music should peak), nothing added
        x = read_audio(d / e["file"], e.get("from", 0.0)) if e.get("file") else made(e["make"], e.get("pitch", 440), e.get("dur"), seed=k + 1)
        if e.get("dur") and e.get("file"):
            x = x[: int(e["dur"] * SR)]
        place(hits, x, e["at"], e.get("gain", -6))
    if music:
        # an external track, fitted by vd audio --tempo-map to the film's beat and placed on it (score.json's music)
        place(under, read_audio(d / music["file"], music.get("from", 0.0)), music.get("at", 0.0), music.get("gain", 0.0))
        notes.append(f"music {music['source']} at {music['bpm']:g} BPM, fitted to {music['film_bpm']:g} BPM ({music['fb']} frames a beat), "
                     + ("in place of this film's own mix" if music.get("replace") else "under this film's own mix"))
    for e in s.get("stems", []):            # whole tracks on the film's clock (a recorded effects track, a music file)
        place(under, read_audio(d / e["file"], e.get("from", 0.0)), e.get("at", 0.0), e.get("gain", 0.0))
    if s.get("bed"):
        b = s["bed"]
        x = read_audio(d / b["file"]) if b.get("file") else made(b.get("make", "drone"), b.get("pitch", 110), s["duration"])
        place(under, x, 0.0, b.get("gain", -24))
    if s.get("tone"):
        tw, secs = tone_audio(d, s, s["tone"])
        place(under, read_audio(tw), 0.0, s.get("tone_gain", 0.0))
        notes.append(f"Tone music {s['tone']} rendered as sound in {secs:.1f} s" if secs else f"Tone music {s['tone']} from cache")
    words = s.get("words", [])
    duck = float(s.get("duck_db", 8.0))
    if words and duck:
        g = 10 ** (-duck * word_mask(words, n) / 20)
        under *= g[:, None]
    mix = voice + under + hits
    raw = outdir(d) / "sound-raw.wav"
    write_wav(raw, mix)
    final = outdir(d) / "sound.wav"
    # two-pass loudnorm, linear where it can be: the whole mix moves as one, the voice stays on top
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af", f"loudnorm=I={LUFS_AIM:g}:TP={PEAK_BUILD:g}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
         f"loudnorm=I={LUFS_AIM:g}:TP={PEAK_BUILD:g}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample={SR}",
         "-ar", str(SR), "-c:a", "pcm_s16le", final], check=True)
    raw.unlink(missing_ok=True)
    return check_sound(d, s, final, notes)


def write_wav(path, x):
    import numpy as np
    import wave
    y = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())


def level_faults(lufs, tp):
    """What is wrong with a level, in words ([] when nothing is): the one rule vd sound and the scan both apply."""
    out = []
    if lufs is None:
        out.append("the level could not be read")
    elif abs(lufs - LUFS_AIM) > LUFS_WITHIN:
        out.append(f"the level is {lufs:g} LUFS, {abs(lufs - LUFS_AIM):.1f} LU {'over' if lufs > LUFS_AIM else 'under'} {LUFS_AIM:g} (allowed {LUFS_WITHIN:g} either way)")
    if tp is None:
        out.append("the true peak could not be read")
    elif tp >= PEAK_UNDER:
        out.append(f"the true peak is {tp:g} dBTP, not under {PEAK_UNDER:g}")
    return out


def sound_verdict(lufs, tp, hs, sync=None, rests=()):
    """The last line of every sound check: does it pass, and if not, what fails; and whether its sync was checked.
    SKILL.md's steps end "when vd sound passes", and nothing printed said whether it had, nor that the named events of
    a worked film were never checked. `sync`: None when there was nothing named to check, else [(name, ms off or None)]
    for each named event, where None or more than 1.5 frames off is to check by ear (the rise a sound starts with can
    hide under a louder one: Plus One's 32 cues, made from the same numbers as its picture, show three such). `rests`:
    the silences meant, by name, which are not holes."""
    bad = level_faults(lufs, tp) + ([f"silent hole{'s' if len(hs) > 1 else ''} at " + ", ".join(f"{a}-{b} s" for a, b in hs)] if hs else [])
    meant = f", and {len(rests)} silence{'s' if len(rests) > 1 else ''} meant ({', '.join(n for n, *_ in rests)})" if rests else ""
    if sync is None:
        said = "sync not checked: no named events (score.json's sounds, or CUES in kit/times.gen.ts)"
    else:
        off = [(n, ms) for n, ms, bad_ in sync if bad_]
        said = f"sync checked on {len(sync)} named events, " + (f"{len(off)} to check by ear: " + ", ".join(f"{n} ({'not found' if ms is None else f'{ms:+d} ms'})" for n, ms in off)
                                                              if off else "each starting within 1.5 frames")
    if not bad:
        return f"sound passes: {lufs:g} LUFS (within {LUFS_WITHIN:g} of {LUFS_AIM:g}), true peak {tp:g} dBTP (under {PEAK_UNDER:g}), no silent hole{meant}; {said}"
    return "sound fails: " + "; ".join(bad) + f"; {said}"


GEN_LINE = re.compile(r"^export const (\w+) = (.+);\s*$", re.M)


def gen_data(d):
    """The clock a worked film's sound.py writes for its picture (kit/times.gen.ts, one `export const NAME = JSON;` a
    line): {NAME: value}, read by vd as the picture reads it. {} when the film has none."""
    f = Path(d) / "kit" / "times.gen.ts"
    out = {}
    if f.is_file():
        for name, value in GEN_LINE.findall(f.read_text(encoding="utf-8", errors="replace")):
            try:
                out[name] = json.loads(value)
            except ValueError:
                pass
    return out


def rests_of(d, s):
    """The silences a film means, by name: score.json's rests ([{"name", "from", "to"}], seconds) and the generated
    RESTS ([[name, from, to]]). The pages ask for silence on the name; the check failed any such half second as a hole."""
    out = [(r.get("name") or "rest", float(r["from"]), float(r["to"])) for r in s.get("rests") or []]
    return out + [(str(n), float(a), float(b)) for n, a, b in gen_data(d).get("RESTS") or []]


def meant_holes(hs, rests, slack=0.15):
    """(holes, rests heard): a hole inside a meant silence (give or take `slack` s) is that silence, not a hole."""
    left, heard = [], []
    for a, b in hs:
        r = next((r for r in rests if a >= r[1] - slack and b <= r[2] + slack), None)
        if r is None:
            left.append((a, b))
        elif r not in heard:
            heard.append(r)
    return left, heard


def check_sound(d, s, wav, notes=(), to=None):
    lufs, tp = loudness(wav)
    x = read_audio(wav)
    env = env_db(x)
    lines = [f"sound {wav.name}: {len(x) / SR:.2f} s, {lufs} LUFS (aim {LUFS_AIM:g}, within {LUFS_WITHIN:g}), true peak {tp} dBTP (must be under {PEAK_UNDER:g})"
             + ("" if not level_faults(lufs, tp) else "  <- OFF")]
    lines += list(notes)
    wanted = [(e.get("name") or e.get("make") or Path(e.get("file", "?")).stem, e["at"]) for e in s.get("sounds", [])]
    cues = [(str(n), float(at)) for n, at in gen_data(d).get("CUES") or []]     # a worked film's named events, in seconds
    sync = None
    if wanted or cues:
        sync = []
        lines.append("hits: where each starts (its first rise above the level before it) against where "
                     + " and ".join(w for w, have in (("the score wants it", wanted), ("kit/times.gen.ts names it", cues)) if have))
        for name, at, peak, off in hit_report(env, wanted + cues):
            bad_ = off is None or abs(off) > 1000 / s["fps"] * 1.5
            sync.append((name, off, bad_))
            lines.append(f"  {name:24} wants {at:6.2f} s  starts {peak if peak is None else round(peak, 2):>6} s  {off if off is not None else '-':>5} ms{'  <- check' if bad_ else ''}")
    words = s.get("words", [])
    if words:
        rows = pause_report(env, words)
        lines.append(f"pauses: level in each pause against the words beside it ({len(rows)} pauses of 0.25 s or more; aim about -5 dB)")
        for g0, g1, diff in rows:
            lines.append(f"  {g0:6.2f}-{g1:6.2f} s  {diff:+5.1f} dB" + ("  <- louder than the words" if diff > 0 else "  <- nearly silent" if diff < -30 else ""))
    hs, rests = meant_holes(holes(env), rests_of(d, s))
    if rests:
        lines.append("silences meant (named in score.json's rests or kit/times.gen.ts): " + ", ".join(f"{n} {a:g}-{b:g} s" for n, a, b in rests))
    lines.append("silent holes: none" if not hs else "silent holes (under -50 dBFS for 0.4 s or more): " + ", ".join(f"{a}-{b} s" for a, b in hs))
    lines.append(sound_verdict(lufs, tp, hs, sync, rests))
    text = "\n".join(lines)
    (Path(to) if to else outdir(d) / "sound.txt").write_text(text + "\n", encoding="utf-8")
    return text


# H.264 colour tags for BT.601 (6 = SMPTE 170M), what raea's ffmpeg media backend encodes with and doesn't say: untagged
# HD video is decoded as BT.709 by browsers and by raea itself, a visible shift in the darks (measured here)
TAG_601 = "h264_metadata=colour_primaries=6:transfer_characteristics=6:matrix_coefficients=6"


def untagged(film):
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_space", "-of", "csv=p=0", film], capture_output=True, text=True)
    return p.stdout.strip() in ("", "unknown")


def mux(film, wav, dest, tag601=False, gain_db=0.0):
    """The picture's video stream copied (tagged BT.601 when asked and it carries no tags), the sound added (lowered by
    -gain_db when asked). A sound shorter than the picture is padded with silence, so the picture is never cut short;
    a longer one ends with the picture."""
    bsf = ["-bsf:v", TAG_601] if tag601 and untagged(film) else []
    run(["ffmpeg", "-v", "error", "-y", "-i", film, "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", *bsf,
         "-af", (f"volume={gain_db:g}dB," if gain_db else "") + "apad", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", dest], check=True)


TRIMS = (0.25, 0.5, 0.75, 1.0)   # dB, tried in turn when the encode lifts the true peak over PEAK_UNDER
MARGIN_DB = 0.2                  # a trimmed file's peak must be this far under PEAK_UNDER: another decoder reads it a little differently


def held_under_peak(pic, wav, part, tag601=True):
    """The AAC encode lifts a mix's true peak, by how much depends on the mix and not smoothly on its level: Plus One's
    sound, -3.1 dBTP as a wav, came out at -0.6 (and at -0.6 again 0.5 dB lower, at -2.2 0.6 dB lower). So the encoded
    file is measured, and when its peak is not under PEAK_UNDER the sound is encoded again a little lower, the smallest
    of TRIMS that brings it MARGIN_DB under while the level stays within LUFS_WITHIN of LUFS_AIM. Returns a line saying what was
    done, or None when nothing was needed (or nothing helped: the scan then names the fault)."""
    lufs, tp = loudness(part)
    if tp is None or tp < PEAK_UNDER:
        return None
    for trim in TRIMS:
        mux(pic, wav, part, tag601=tag601, gain_db=-trim)
        l2, t2 = loudness(part)
        if not level_faults(l2, t2) and t2 < PEAK_UNDER - MARGIN_DB:
            return f"the AAC encode lifted the true peak to {tp:g} dBTP, so the sound is {trim:g} dB lower in this file ({l2:g} LUFS, {t2:g} dBTP)"
    mux(pic, wav, part, tag601=tag601)
    return f"the AAC encode lifts the true peak to {tp:g} dBTP and no trim up to {TRIMS[-1]:g} dB brought it under {PEAK_UNDER:g} within the level: give the mix more headroom"


# ---------------------------------------------------------------- render a range, export

def join_report(film, joins, w=320, h=180):
    """One line: is each join clean? The change into and out of each join frame against its ten neighbours (grey, mean).
    A join pops when either is over three times the neighbours' median (the rule of an earlier joins check). One film's
    stretches popped at frames 270 and 360, cause not yet known; whatever the cause, this catches the seam. A lead-in
    before the range was tried and dropped: on a motion-blurred film a range from frame N matched a whole render for its
    first 3 frames without one, and differed from frame N+3 on (mean under 0.05) with 8 frames of lead-in or without."""
    import numpy as np
    raw = run(["ffmpeg", "-v", "error", "-i", str(film), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    n = len(raw) // (w * h)
    f = np.frombuffer(raw[: n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32)
    d = np.abs(f[1:] - f[:-1]).mean(axis=(1, 2))          # d[i]: the change into frame i + 1
    said = []
    for j in joins:
        if not 0 < j < n:
            continue
        into, out = d[j - 1], (d[j] if j < len(d) else 0.0)
        near = [d[i] for i in range(max(0, j - 6), min(len(d), j + 6)) if i not in (j - 1, j)]
        base = max(float(np.median(near)) if near else 0.0, 0.15)
        if max(into, out) > 3 * base:
            said.append(f"frame {j} changes more than the frames round it ({max(into, out):.1f} against {base:.1f}): the film's own hit if something "
                        "happens on that frame, a seam if nothing does, so look at it")
        else:
            said.append(f"frame {j} clean ({max(into, out):.1f} against {base:.1f})")
    return "joins: " + ("; ".join(said) if said else "none inside the film")


def range_entry(d, s, f0, n):
    stub = d / "_range.tsx"
    write_if_changed(stub, "// written by vd render --from/--to: the film from frame " + str(f0) + " for " + str(n) + " frames\n"
                    'import { Composition, registerRoot } from "raea";\nimport { FPS, Film, H, W } from "./film";\n'
                    f'registerRoot(() => <Composition id="range" component={{() => <Film offset={{{f0}}} />}} width={{W}} height={{H}} fps={{FPS}} durationInFrames={{{n}}} />);\n')
    return stub


def splice_args(old, part, out, f0, f1, crf=12, total=None):
    """ffmpeg arguments that put `part` (frames f0..f1-1) into `old` in place of the same frames, encoded once more at crf.
    A range from the first frame, or to the last (`total`), has no piece before or after it: asking ffmpeg for an empty
    piece would make the concat fail."""
    pieces, names = [], []
    if f0 > 0:
        pieces.append(f"[0:v]trim=end_frame={f0},setpts=PTS-STARTPTS[a]")
        names.append("[a]")
    pieces.append("[1:v]setpts=PTS-STARTPTS[b]")
    names.append("[b]")
    if total is None or f1 < total:
        pieces.append(f"[0:v]trim=start_frame={f1},setpts=PTS-STARTPTS[c]")
        names.append("[c]")
    fc = ";".join(pieces) + f";{''.join(names)}concat=n={len(names)}:v=1:a=0[v]"
    return ["ffmpeg", "-v", "error", "-y", "-i", str(old), "-i", str(part), "-filter_complex", fc, "-map", "[v]", "-an",
            "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", str(out)]


def shutter_of(s, comp):
    """A film's camera blur, from score.json: "shutter": {"composition": ID, "sub": N, "open": K}. `vd export` then
    draws the film at N pictures a frame under the composition ID and averages the first K of each N into one frame
    (TRAPS.md, "A camera's blur"). (ID, N, K), or None for a film without one or a composition that is not the score's
    own. Linden's accepted cut was made this way, and its plain export was a sharper film than the one accepted."""
    sh = (s or {}).get("shutter")
    if not sh or comp != ((s or {}).get("composition") or "film"):
        return None
    try:
        sub_comp, sub, opened = str(sh["composition"]), int(sh["sub"]), int(sh["open"])
    except (KeyError, TypeError, ValueError):
        sub_comp, sub, opened = "", 0, 0
    if not sub_comp or not 1 <= opened <= sub:
        raise SystemExit('score.json\'s "shutter" must be {"composition": ID, "sub": N, "open": K}, K from 1 to N: the composition that draws N pictures a frame, '
                         'and how many of each N the shutter is open for')
    return sub_comp, sub, opened


def averaged(pictures, out, sub, opened, fps):
    """tools/blur.py on one file: the first `opened` of every `sub` pictures averaged into one frame of `out`."""
    import raea_run
    # a whole-film encode: it waits its turn like the share copy and the splice do. Run bare, it began the moment the
    # engine let the queue go, beside whatever render had been waiting behind it (a review's finding)
    turn = raea_run.one_at_a_time(wait=3600.0, what=f"blur {Path(out).name}", kind="heavy")
    try:
        p = run([PY, "-X", "utf8", TOOLS / "blur.py", pictures, out, "--sub", sub, "--open", opened, "--fps", f"{fps:g}"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        if turn is not None:
            turn.close()
    if p.returncode or not Path(out).exists():
        raise SystemExit(f"the blur failed: {(p.stdout + p.stderr).strip()[-400:] or 'blur.py gave no reason'}")


@alone_in(lambda a: outdir(film_dir(a.film)), "render")
def cmd_render(a):
    d = film_dir(a.film)
    s = score_of(d)
    if shutter_of(s, s.get("composition") or "film"):
        raise SystemExit('this film\'s picture is drawn at several pictures a frame and averaged (score.json\'s "shutter"), and a stretch drawn alone would be '
                         "sharp beside it: change the film and run `vd export`, which draws the whole picture again")
    fps = s["fps"]
    total = int(round(s["duration"] * fps))
    f0 = max(0, int(round(float(a.from_) * fps))) if a.from_ is not None else 0
    f1 = min(total, int(round(float(a.to) * fps))) if a.to is not None else total
    if f1 <= f0:
        raise SystemExit("--to must be after --from")
    out = outdir(d)
    part = out / f"range-{f0}-{f1}.mp4"
    stub = range_entry(d, s, f0, f1 - f0)
    must_preflight(stub, "range", 0)
    ok, secs, line = raea_render(d, stub, part, "--quality", "master")
    if not ok:
        raise SystemExit(f"render failed: {line}")
    pic = picture_path(out, d.name, entry_of(d), s.get("composition") or "film")   # what vd export rendered
    if not pic.exists():
        print(f"{part} ({f1 - f0} frames, {secs:.1f} s). There is no {pic} to splice into yet: `vd export` makes it.")
        made_it(part)
        return 0
    t0 = time.monotonic()
    tmp = out / "picture.splice.mp4"
    # an encode of the whole picture: through heavy.py, which gives ffmpeg its turn in the queue at once and says what it waits for
    run([PY, "-X", "utf8", TOOLS / "heavy.py", "--stall", "180", "--", *splice_args(pic, part, tmp, f0, f1, total=total)], check=True)
    tmp.replace(pic)
    note = picture_note(pic)
    try:
        seen = json.loads(note.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    # frames f0-f1 now come from today's sources and the rest from the last full draw: vd export draws it whole again
    note.write_text(json.dumps({**seen, "spliced": seen.get("spliced", []) + [[f0, f1]], "drawn": drawn_record(pic)}), encoding="utf-8")
    w = split_wait(secs, line)
    print(f"rendered frames {f0}-{f1 - 1} ({(f1 - f0) / fps:.2f} s of film) in {secs:.1f} s" + (f" ({w[0]:.0f} s waiting in the queue, {w[1]:.0f} s rendering)" if w else "")
          + f"; spliced into {pic} in {time.monotonic() - t0:.1f} s")
    print(join_report(pic, [j for j in (f0, f1) if 0 < j < total]))
    print(f"This is the picture alone, with no sound: {out / (d.name + '.mp4')} is as it was until `vd export` makes the next cut from this picture.")
    made_it(pic)
    return 0


STUBS = ("_tone.tsx", "_range.tsx")


def sources_newest(d):
    # the two stubs this tool writes beside the entry are not sources; every other file is, a name starting "_" included
    # (an edited _scene.tsx once left the old picture in place)
    files = [p for p in d.rglob("*") if p.is_file() and "out" not in p.relative_to(d).parts and p.name not in STUBS]
    return max((p.stat().st_mtime for p in files), default=0)


def source_files(d):
    """{relative path: [mtime, size]} of every source of the film's picture (the files sources_newest reads)."""
    files = [p for p in d.rglob("*") if p.is_file() and "out" not in p.relative_to(d).parts and p.name not in STUBS]
    return {p.relative_to(d).as_posix(): [round(p.stat().st_mtime, 3), p.stat().st_size] for p in files}


def picture_note(pic):
    """Beside the cached picture: what it was drawn from ({"files": source_files at the draw}), the stretches a
    vd render spliced in since ({"spliced": [[f0, f1], ...]}), and the picture file as the draw left it ({"drawn":
    drawn_record}), which tells it from anything later put at its name."""
    return pic.with_name(pic.name + ".sources.json")


def drawn_record(pic):
    st = Path(pic).stat()
    return {"size": st.st_size, "mtime_ns": st.st_mtime_ns}


def is_drawn(pic):
    """Whether PIC is the picture an export or a splice drew there, as its note recorded it: only such a picture is
    one an export makes again. A note alone said so of a finished film published at a former picture's name, and plain
    clean removed it (a review's finding). A picture whose note has no record (drawn before 0.2.2) is not counted."""
    pic = Path(pic)
    if not pic.is_file() or _linked(pic):
        return False
    try:
        seen = json.loads(picture_note(pic).read_text(encoding="utf-8"))
        return isinstance(seen, dict) and seen.get("drawn") == drawn_record(pic)
    except (OSError, ValueError):
        return False


def picture_current(d, pic):
    """(current, why not). The picture is current only when the film's sources are what it was drawn from, file for
    file: a newest-mtime test kept a picture after a scene it imported was deleted (no file left was newer), and a
    vd render splice made the whole picture look new though the frames outside the stretch came from older sources."""
    if not pic.exists():
        return False, "no picture yet"
    note = picture_note(pic)
    try:
        seen = json.loads(note.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, "no record of what the picture was drawn from"
    if seen.get("spliced"):
        return False, f"frames {', '.join(f'{a}-{b - 1}' for a, b in seen['spliced'])} were spliced in from newer sources than the rest"
    now = source_files(d)
    if seen.get("files") != now:
        was = seen.get("files") or {}
        gone, new = sorted(set(was) - set(now)), sorted(set(now) - set(was))
        changed = sorted(f for f in set(was) & set(now) if was[f] != now[f])
        bits = ([f"{', '.join(gone[:3])} removed"] if gone else []) + ([f"{', '.join(new[:3])} added"] if new else []) +                ([f"{', '.join(changed[:3])} changed"] if changed else [])
        return False, "; ".join(bits) or "its sources changed"
    return True, ""


def sound_inputs(d, s):
    """score.json and every file the sound is built from (voice, stems, sounds, bed, Tone music): an edit to any of them
    makes the built sound stale."""
    v = s.get("voice")
    named = [v if isinstance(v, str) else (v or {}).get("file"), s.get("tone"), (s.get("bed") or {}).get("file"), s.get("sound_file"),
             (s.get("music") or {}).get("file")]
    named += [e.get("file") for e in s.get("stems", []) + s.get("sounds", [])]
    return [d / "score.json"] + [d / f for f in named if f and (d / f).exists()]


def picture_path(out, stem, entry, comp):
    """The cached picture for one film, entry and composition: two compositions of one entry are two pictures."""
    return out / f"{stem}.{Path(entry).stem}.{comp or 'default'}.picture.mp4"


def export_paths(a):
    d, entry, s = where(a)
    comp = a.composition or (s or {}).get("composition") or ("film" if s else None)
    out = outdir(d)
    dest = Path(a.o).resolve() if a.o else out / f"{(d.name if s else entry.stem)}.mp4"
    if dest.suffix.lower() != ".mp4":
        # the cut, its share copy and its sheets are named from this file, and what is made is an .mp4: -o film.mov once
        # wrote film.mp4 and then scanned whatever film.mov was already there
        raise SystemExit(f"vd export makes an .mp4, and -o {dest.name} asks for another kind: give a name ending in .mp4")
    return d, entry, s, comp, out, dest


def spread(s, n=12, total=None):
    """n frames across the whole film (`total` frames, else the score's), for the check before the queue: Round's cut 3
    passed a check of one frame and threw at frame 423 of 513, a stretch no look had sampled. Laying out twelve costs
    about two seconds, drawing none."""
    if total is None:
        if not s:
            return None
        total = int(round(s["duration"] * s["fps"]))
    total = max(1, total)
    return sorted({round(i * (total - 1) / (n - 1)) for i in range(n)})


def comp_frames(entry, comp):
    """How many frames the composition has, from raea itself (`world` asked for a frame past the end says "the
    composition has frames 0 to N"), or None when raea can't say. A 2.5 s composition exported beside a 38.4 s score was
    checked out to frame 2303 and refused for a frame it doesn't have."""
    import raea_run
    if os.environ.get("VD_NO_PREFLIGHT") == "1":
        return None
    try:
        raea = raea_run.checked_binary(say=False)
        p = subprocess.run([raea, "world", entry.name, *(["--composition", comp] if comp else []), "--frame", "999999999", "--no-render"], cwd=entry.parent,
                           env=raea_run.raea_env(), capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                           creationflags=NO_WINDOW, timeout=300)
    except (SystemExit, OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"frames 0 to (\d+)", p.stdout + p.stderr)
    return int(m.group(1)) + 1 if m else None


def export_frames(s, entry, comp):
    """(frames, fps) of what an export draws: the score's clock when the composition is the score's own, else the
    composition's own length from raea (frames None when it can't say; then only frame 0 is checked)."""
    fps = (s or {}).get("fps")
    if s and comp == (s.get("composition") or "film"):
        return int(round(s["duration"] * fps)), fps
    return comp_frames(entry, comp), fps or look_fps(entry, comp)


CUT = re.compile(r"(.+)-cut(\d+)\.mp4")
def _named(folder, prefix, rest):
    """The files in FOLDER named PREFIX followed by something matching the pattern REST, as the filesystem itself
    names them. A pattern without case only proposes: a file counts when its name starts with PREFIX exactly, or when
    PREFIX spelled exactly, with the file's own ending, opens that very file. So on Windows draft's sheets are Draft's,
    on Linux and a case-sensitive Mac volume they are not, and STRASSE is never taken for Straße. Deciding sameness
    here took the platform's word, then Python's casefold: one deleted another film's only cut on a case-sensitive Mac
    volume, the other merged STRASSE and Straße, which Windows keeps apart (council findings)."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    proposed = re.compile(re.escape(prefix) + rest, re.IGNORECASE)
    found = []
    for f in folder.iterdir():
        if not proposed.fullmatch(f.name):
            continue
        if f.name.startswith(prefix):
            found.append(f)
            continue
        spelled = folder / (prefix + f.name[len(prefix):])
        try:
            if spelled.exists() and os.path.samefile(spelled, f):
                found.append(f)
        except OSError:
            pass                       # cannot tell: not ours, so it is kept
    return found


def cut_of(out, stem):
    """(N, path) of the next cut of `stem`: OUT/cuts/STEM-cutN.mp4, N one past the highest there, names matched as text.
    A glob built from the name missed draft[1]'s cuts (the [1] read as a set of characters), so cut 1 was given again,
    and the failed export's rollback deleted the cut already filed under it (a review's finding). A number whose names
    the filesystem says are taken is passed over: on Windows draft-cut1.mp4 is Draft-cut1.mp4, and draft's cut 1 was
    written over it (a council's finding). Whether two names are one is the filesystem's answer, never computed here."""
    cuts = out / "cuts"
    have = [int(m.group(2)) for f in (cuts.iterdir() if cuts.is_dir() else ()) if (m := CUT.fullmatch(f.name)) and m.group(1) == stem]
    n = max(have, default=0) + 1
    while (cuts / f"{stem}-cut{n}.mp4").exists() or (cuts / f"{stem}-cut{n}-share.mp4").exists():
        n += 1
    return n, cuts / f"{stem}-cut{n}.mp4"


def hand_in_files(film):
    """A film's hand-in as it lies beside it: the film, its share copy and its sheets."""
    film = Path(film)
    return [film, film.with_name(film.stem + "-share.mp4"), *sheets_of(film)]


def publish(src, dst):
    """dst becomes a copy of src, all at once, replacing what was there. A copy, not a hard link: a tool that rewrites
    NAME.mp4 in place (ffmpeg -y on the same name) would rewrite the kept cut through a link."""
    part = dst.with_name(dst.name + ".part")
    shutil.copy2(src, part)
    part.replace(dst)


def run_sound_py(d):
    """The exact lines that make a worked film's sound again: its sound.py, run in its folder by this Python."""
    q = lambda x: f'"{x}"' if " " in str(x) else str(x)
    return f"  cd {q(d)}\n  {q(PY)} sound.py"


def film_sound(d, s):
    """The sound the export lays under the picture, from score.json: the film's own mix as it is when nothing is added
    to it, else the mix built from score.json (a voice, a mapped track, stems over the own mix), built again when older
    than anything it is made from. vd export and vd playable both play this. (wav, what was done or None)."""
    if s.get("sound_file") and not s.get("voice") and not s.get("music"):
        return own_sound(d, s), f"sound is {s['sound_file']}, as it is"
    if s.get("sound_file"):
        own_sound(d, s)                 # stops on a stale own mix even when the built sound is newer than it
    wav = outdir(d) / "sound.wav"
    if not wav.exists() or wav.stat().st_mtime < max(p.stat().st_mtime for p in sound_inputs(d, s)):
        build_sound(d, s)
        return wav, "sound built from score.json" + (f": its voice over {s['sound_file']}, this film's own mix" if s.get("sound_file") else "")
    return wav, None


def own_sound(d, s):
    """The film's own finished mix (score.json's sound_file: a worked film's sound.py writes media/sound.wav), as it is.
    Stops when it is missing, and when the sound.py beside it is newer than it or than the times it writes for the
    picture (kit/times.gen.ts): a note was printed and the old sound exported under a picture moved to a new beat."""
    wav = d / s["sound_file"]
    if not wav.is_file():
        raise SystemExit(f"score.json names {s['sound_file']} as the film's sound and it isn't there. Make it, then run this again:\n{run_sound_py(d)}")
    maker = d / "sound.py"
    stale = [g for g in (wav, d / "kit" / "times.gen.ts") if maker.exists() and g.exists() and maker.stat().st_mtime > g.stat().st_mtime]
    if stale:
        raise SystemExit(f"stopped: sound.py changed after {' and '.join(g.relative_to(d).as_posix() for g in stale)} {'was' if len(stale) == 1 else 'were'} made, "
                         f"so the sound (and the beats the picture reads) are stale and nothing was made. Make them again, then run this again:\n{run_sound_py(d)}")
    return wav


@alone_in(lambda a: export_paths(a)[4], "export")
def cmd_export(a):
    """The picture rendered once (raea's master quality), the sound copied on. In a vd new folder the sound is built from
    score.json; for any entry, --sound WAV, else raea's own sound-only render of the same entry. Each export that works is
    a cut kept under its own number, OUT/cuts/NAME-cutN.mp4 with its share copy and sheets, and NAME.mp4 (or -o) is then
    made the latest. One that fails exits non-zero, removes only what it began of its own cut, and says which cut
    NAME.mp4 still is: Round's failed cut 3 left cut 2 under the same names and the next step filed it as cut 3, and the
    fix then deleted cut 2 itself, which the cut ledger and the second reading need."""
    d, entry, s, comp, out, dest = export_paths(a)
    n, cut = cut_of(out, dest.stem)
    done = {}
    # what is already there under this cut's names is never this export's to remove, whatever went wrong in numbering
    there = {f for f in [cut.with_name(cut.stem + ".part.mp4"), *hand_in_files(cut)] if f.exists()}
    try:
        dest = _export(a, cut, done)
    except BaseException:
        if not done.get("cut"):
            for f in [cut.with_name(cut.stem + ".part.mp4"), *hand_in_files(cut)]:
                if f not in there:
                    f.unlink(missing_ok=True)
        if done.get("cut"):
            # the cut was filed and stays: a step after it failed, and an agent told no cut was made would export again
            # and file the same film as the next cut
            print(f"export failed after cut {n} was made: cuts{os.sep}{cut.name} is kept, and the step after it failed (see above)",
                  file=sys.stderr)
            raise
        before = cut_of(out, dest.stem)[0] - 1
        print(f"export failed: no cut {n} was made" + (f"; {dest.name} is still cut {before}, cuts{os.sep}{dest.stem}-cut{before}.mp4" if before and dest.exists() else ""),
              file=sys.stderr)
        raise
    made_it(dest)
    # made and scanned is 0; made and not scanned is 3, so nothing that reads exit codes takes an unchecked film for a checked one
    return 0 if done.get("scanned", True) else 3


def _export(a, cut=None, done=None):
    d, entry, s, comp, out, dest = export_paths(a)
    cut = cut or cut_of(out, dest.stem)[1]
    done = {} if done is None else done
    pic = picture_path(out, dest.stem, entry, comp)
    t0 = time.monotonic()
    said = []
    if s and s.get("sound_file") and not a.sound:
        own_sound(d, s)                     # a stale or missing own mix stops the export before the picture's render
    if s and s.get("music"):            # with --sound too: the picture is timed on the beat as much as the sound is
        music_beat(d, s)                    # so does a mapped track whose beat sound.py has not yet made the film's
    current, stale_why = picture_current(d, pic)
    draw = a.again or not current
    drawn_from = source_files(d) if draw else None     # the sources as the draw begins: an edit during it is caught next time
    total, fps = export_frames(s, entry, comp) if draw else (None, (s or {}).get("fps"))
    # every export writes the cut, its share copy and (a link or a copy) the latest; drawing the picture needs the
    # picture's room and raea's own too
    dur = total / fps if total and fps else (s or {}).get("duration", 60)
    more = (shutter_of(s, comp) or (None, 0, 0))[1]             # a shutter's many pictures a frame are a larger file while they last
    room(entry, 1.0 + (5 + more) * 0.005 * dur if draw else 0.1 + 4 * 0.005 * dur, "export", dest.parent)
    if draw:
        must_preflight(entry, comp, 0, spread(s, total=total) if total else None, fps)
        # one pass: raea's ffmpeg media backend writes x264 at CRF 11 (master) as it draws. Measured on an earlier film (468 frames,
        # 3D): 43.7 s against 88.4 s for PNG frames plus 33.6 s to encode them, and as clean in the darks (mean luma error on
        # dark pixels of the 12 darkest frames 1.13 both, max 1.33 against 1.65). Its file is BT.601 and untagged: mux tags it.
        one_pass = shutil.which("ffmpeg") is not None
        # drawn beside the picture and moved into place only whole: a render that fails part way (the disk full one night)
        # left a truncated picture that the next export of unchanged sources took as current
        part = pic.with_name(pic.stem + ".part.mp4")
        shutter = shutter_of(s, comp)
        # with a shutter the engine draws the many-pictures composition into `drawn`, and blur.py averages it into `part`
        drawn = pic.with_name(pic.stem + ".pictures.part.mp4") if shutter else part
        ok, secs, line = raea_render(d, entry, drawn, *(["--composition", shutter[0] if shutter else comp] if shutter or comp else []), "--quality", "master",
                                     env={"RAEA_MEDIA": "ffmpeg"} if one_pass else None)
        if not ok:
            drawn.unlink(missing_ok=True)
            raise SystemExit(f"render failed: {line}")
        w = split_wait(secs, line)
        waited = f" ({w[0]:.0f} s waiting in the queue, {w[1]:.0f} s rendering)" if w else ""
        if shutter:
            t1 = time.monotonic()
            try:
                averaged(drawn, part, shutter[1], shutter[2], fps)
            except BaseException:
                part.unlink(missing_ok=True)
                raise
            finally:
                drawn.unlink(missing_ok=True)
            said.append(f"picture drawn at {shutter[1]} pictures a frame in {secs:.1f} s{waited} and {shutter[2]} of each {shutter[1]} averaged in "
                        f"{time.monotonic() - t1:.1f} s (a camera's blur, score.json's shutter)")
        else:
            said.append(f"picture rendered once in {secs:.1f} s{waited}")
        part.replace(pic)
        picture_note(pic).write_text(json.dumps({"files": drawn_from, "drawn": drawn_record(pic)}), encoding="utf-8")
        if stale_why and not a.again and stale_why != "no picture yet":
            said.append(f"(drawn again: {stale_why})")
    else:
        said.append("picture is current, not rendered again")
    if a.sound:
        wav = Path(a.sound).resolve()
    elif s:
        wav, did = film_sound(d, s)
        if did:
            said.append(did)
    else:
        wav = out / f"{dest.stem}.sound.wav"
        ok, secs, line = raea_render(d, entry, wav, *(["--composition", comp] if comp else []))
        if not ok:
            raise SystemExit(f"the sound did not render: {line}")
        said.append(f"sound rendered alone in {secs:.1f} s")
    cut.parent.mkdir(parents=True, exist_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = cut.with_name(cut.stem + ".part.mp4")              # moved into place only when it is whole
    mux(pic, wav, part, tag601=True)
    if part.exists():
        trimmed = held_under_peak(pic, wav, part)
        if trimmed:
            said.append(trimmed)
        if cut.exists():   # never written over: a filed cut is the ledger's (it cannot be here unless cut_of was wrong)
            raise SystemExit(f"stopped: {cut} is already there, so this export's film was not filed over it; nothing was replaced")
        part.replace(cut)
    share, sheets = hand_in(cut)
    done["cut"] = True
    # the latest: NAME.mp4 and its hand-in made the cut just finished, all of it only now
    for old in sheets_of(dest):
        old.unlink()
    for f in hand_in_files(cut):
        if f.exists():
            publish(f, dest.with_name(dest.stem + f.name[len(cut.stem):]))
    print(f"{dest}: {'; '.join(said)}; sound copied on ({time.monotonic() - t0:.1f} s in all)")
    print(f"this is cut {cut.stem.rsplit('-cut', 1)[1]}, kept as {cut} (its share copy and sheets beside it); {dest.name} is the latest cut")
    print(f"hand-in beside it: {dest.stem}-share.mp4 (the share copy) and {len(sheets)} timed sheets at 4 frames a second "
          f"({dest.stem + sheets[0].name[len(cut.stem):] if sheets else 'none'}{' ...' if len(sheets) > 1 else ''})")
    done["scanned"] = scanned(dest, out / "scan.txt") is not None
    return dest


def scanned(film, to, alone=False):
    """The scan of a finished film, printed and written to `to`. It never fails what it follows: a scan that cannot run
    says so, and writes that to `to` in place of the report before it, so the next step reads no old scan as this film's
    (a damaged export once passed a scan made from half its pictures, and a scan that failed left the last one there)."""
    t0 = time.monotonic()
    try:
        import scan
        text, fixes = scan.scan(film, to)
    except (Exception, SystemExit) as e:
        said = f"SCAN could not run on {Path(film).name}: {str(e)[-300:]}. " + ("Nothing was scanned (exit code 3)" if alone else
                "The film is made but NOT scanned: nothing here says it is clean (an export ends with exit code 3 for this)")
        print(said)
        try:
            Path(to).write_text(said + "\n", encoding="utf-8")
        except OSError:
            pass
        return None
    print(text)
    # the sound's own fault is in the count line too: a film with no sound, or far off the level, read "0 to fix"
    loud = next((l.strip() for l in text.splitlines() if l.strip().startswith("loudness:")), "")
    sound = "; the file has no sound" if "has no sound" in loud else "; the level is off (the loudness line says how)" if loud and not loud.endswith(": ok") else ""
    print(f"scan: {len(fixes)} to fix and {sum(l.startswith('check:') for l in text.splitlines())} to check{sound}, in {time.monotonic() - t0:.1f} s; written to {to}")
    return to


# ---------------------------------------------------------------- measure, pin

def hf_hub():
    """Where huggingface_hub keeps its models on this machine."""
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]) / "hub"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "huggingface" / "hub"


def transcriber():
    """None when this machine can transcribe a film's words (faster_whisper, and its small model already in the Hugging
    Face cache: measuring fetches nothing), else why not, in words."""
    import importlib.util
    if importlib.util.find_spec("faster_whisper") is None:
        return "faster_whisper is not installed in this Python"
    if not (hf_hub() / "models--Systran--faster-whisper-small").is_dir():
        return f"faster-whisper's small model is not in {hf_hub()}, and nothing is fetched while measuring"
    return None


def not_transcribed(m):
    """Why a measure has no words because none could be transcribed, or None (words heard, or told there are none)."""
    v = str((m or {}).get("voice") or "")
    return v.split(": ", 1)[-1] if v.startswith("not transcribed") else None


def measures_of(film, cache_root=None, no_voice=False):
    """measures.json for a film (or the file itself when given one), from tools/measure_film.py, cached by content. One
    measured when no transcriber was here is measured again once there is one: its words were unknown, not none."""
    film = Path(film).resolve()
    if film.suffix == ".json":
        return json.loads(film.read_text(encoding="utf-8")), film
    if film.is_dir() and (film / "measures.json").exists():
        return json.loads((film / "measures.json").read_text(encoding="utf-8")), film / "measures.json"
    h = hashlib.sha1()
    with film.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    out = Path(cache_root or Path.home() / ".vd" / "measures") / (h.hexdigest()[:16] + ("-novoice" if no_voice else ""))
    if (out / "measures.json").exists() and not_transcribed(json.loads((out / "measures.json").read_text(encoding="utf-8"))) and transcriber() is None:
        print(f"{film.name} was measured when no transcriber was here; measuring it again for its words", flush=True)
        (out / "measures.json").unlink()
    if (out / "measures.json").exists():
        import measure
        import see
        if json.loads((out / "measures.json").read_text(encoding="utf-8")).get("versions") != {"measure": measure.VERSION, "see": see.VERSION}:
            # measured by other code (an older tempo once read 240 for 120 BPM): comparisons never mix two ways of measuring
            print(f"{film.name} was measured by an earlier version of the tools; measuring it again", flush=True)
            (out / "measures.json").unlink()
    if not (out / "measures.json").exists():
        out.mkdir(parents=True, exist_ok=True)
        # not behind films: measure_film waits in the queue only to load the transcriber, and says so at once; output streams
        print(f"measuring {film.name} (cached afterwards in {out})", flush=True)
        p = run([PY, "-X", "utf8", TOOLS / "measure_film.py", film, out, *(["--no-voice"] if no_voice else [])], stdout=subprocess.PIPE, stderr=None, text=True,
                encoding="utf-8", errors="replace")
        if p.returncode or not (out / "measures.json").exists():
            raise SystemExit(f"measuring {film.name} failed: {(p.stdout or '')[-600:]} (its errors are above)")
    return json.loads((out / "measures.json").read_text(encoding="utf-8")), out / "measures.json"


def leaves(x, path=""):
    """Every numeric leaf of a measures tree as {dotted.path: number}; lists of numbers kept as lists."""
    out = {}
    if isinstance(x, dict):
        for k, v in x.items():
            out.update(leaves(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(x, bool):
        pass
    elif isinstance(x, (int, float)):
        out[path] = float(x)
    elif isinstance(x, list) and x and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
        out[path] = [float(v) for v in x]
    return out


# The order a gap is read in when there is no bare pass: what cost films most, first (tier 1 to 6). Within a tier,
# the larger difference first, measured as |ours - ref| / max(|ours|, |ref|), which stays between 0 and 1, so a measure
# whose reference is near zero cannot lead on a ratio.
IMPORTANCE = (
    ("sound besides the voice", ("E_sound.",)),
    ("frames still", ("D_motion.still_share", "D_motion.see_census.still_seconds", "D_motion.see_census.frame_identical_seconds")),
    ("words by job", ("text.", "A_time.words")),
    ("the main thing's share", ("F_frame.largest_", "D_motion.measure_py.largest_band", "D_motion.measure_py.occupancy")),
    ("changes on a breath", ("A_time.changes_in_sentence_gap", "A_time.changes_during_voice")),
)


def tier(name):
    return next((i for i, (_, keys) in enumerate(IMPORTANCE, 1) if name.startswith(keys)), len(IMPORTANCE) + 1)


def gap_rows(ours, ref, bare=None):
    """Rows (name, ours, ref, bare, tier, score, our times, ref times) for every number both films have, in reading order.
    With a bare pass (the same brief made with no direction), score = |ours - ref| / |ref - bare|: how far ours is from
    the reference in units of the distance direction has to cover; largest first, measures where the bare pass already
    equals the reference last. Without one, score = |ours - ref| / max(|ours|, |ref|) inside the IMPORTANCE tiers.
    Lists of times are rows too (their count), and their times are kept to print."""
    a, b = leaves(ours), leaves(ref)
    c = leaves(bare) if bare is not None else {}
    rows = []
    for k in sorted(set(a) & set(b)):
        x, y, z = a[k], b[k], c.get(k)
        times = (None, None)
        if isinstance(x, list) or isinstance(y, list):
            if not (isinstance(x, list) and isinstance(y, list)):
                continue
            times, x, y = (x, y), float(len(x)), float(len(y))
            z = float(len(z)) if isinstance(z, list) else None
            k += " (count)"
        rel = abs(x - y) / max(abs(x), abs(y)) if max(abs(x), abs(y)) > 0 else 0.0
        if bare is not None:
            spread = abs(y - z) if isinstance(z, (int, float)) else 0.0
            score = abs(x - y) / spread if spread > 1e-12 else -1.0 + rel   # no spread to measure in: after every row that has one
        else:
            score = rel
        rows.append((k, x, y, z if isinstance(z, (int, float)) else None, tier(k), score) + times)
    if bare is not None:
        rows.sort(key=lambda r: -r[5])
    else:
        rows.sort(key=lambda r: (r[4], -r[5]))
    return rows


def gap_table(rows, top=40, bare=False):
    fmt = lambda v: "" if v is None else f"{v:.4g}"
    if bare:
        lines = ["| # | measure | ours | reference | bare pass | gap in spreads |", "|---|---|---|---|---|---|"]
        for i, (k, x, y, z, t, g, xs, ys) in enumerate(rows[:top], 1):
            lines.append(f"| {i} | {k} | {fmt(x)} | {fmt(y)} | {fmt(z)} | {fmt(g) if g >= 0 else fmt(g + 1.0) + ' (no spread)'} |")
    else:
        lines = ["| # | tier | measure | ours | reference | gap |", "|---|---|---|---|---|---|"]
        for i, (k, x, y, z, t, g, xs, ys) in enumerate(rows[:top], 1):
            lines.append(f"| {i} | {t} | {k} | {fmt(x)} | {fmt(y)} | {fmt(g)} |")
        lines += ["", "Tiers: " + "; ".join(f"{i} {name}" for i, (name, _) in enumerate(IMPORTANCE, 1)) + f"; {len(IMPORTANCE) + 1} the rest."]
    timed = [(k, xs, ys) for k, x, y, z, t, g, xs, ys in rows if xs is not None and any(v > 0 for v in xs + ys) and len(xs) <= 40]
    if timed:
        lines += ["", "Times (s):", ""]
        for k, xs, ys in timed[:8]:
            lines.append(f"- {k}: ours {', '.join(f'{t:.2f}' for t in xs)} | reference {', '.join(f'{t:.2f}' for t in ys)}")
    return "\n".join(lines)


def cmd_measure(a):
    d = film_dir(a.film, required=False)
    ref = a.against
    if not ref and d is not None and score_of(d).get("pinned"):
        ref = score_of(d)["pinned"]
    if not ref:
        raise SystemExit("--against REF (a film, a measures.json, or a folder holding one), or `vd pin REF` first")
    # --no-voice: no film in this comparison has a voice, so none of them waits for the transcriber or hears words in music
    ours, _ = measures_of(a.target, no_voice=a.no_voice)
    theirs, src = measures_of(ref, no_voice=a.no_voice)
    bare = measures_of(a.bare, no_voice=a.no_voice)[0] if a.bare else None
    unknown = [f"- {Path(f).name}: words not transcribed ({why}); its word measures are left out, not read as no voice\n"
               for f, m in ((a.target, ours), (ref, theirs), (a.bare, bare)) if m is not None and (why := not_transcribed(m))]
    table = gap_table(gap_rows(ours, theirs, bare), bare=bare is not None)
    how = ("ordered by how far ours is from the reference in units of the spread between the reference and the bare pass "
           f"({Path(a.bare).name})" if bare is not None else "ordered by tier of importance, then by gap = |ours - ref| / max(|ours|, |ref|)")
    text = f"# Gap: {Path(a.target).name} against {Path(ref).name}\n\nUp to forty of the numbers both films have, {how}.\n\n" + "".join(unknown) + ("\n" if unknown else "") + f"{table}\n"
    dest = (outdir(d) / "GAP.md") if d is not None else Path(a.target).resolve().with_suffix(".gap.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print("\n".join(text.splitlines()[:28]))
    print(f"... written to {dest}")
    made_it(dest)
    return 0


PIN_KEYS = ("A_time.shot_len_median", "A_time.words_per_s", "A_time.changes_in_sentence_gap", "D_motion.still_share.0.35",
            "D_motion.see_census.moving_share", "D_motion.see_census.two_or_more_share", "D_motion.see_census.moves_per_10s",
            "D_motion.see_census.still_seconds", "D_motion.move_len_median")


# the measures built from the reference's words: wrong, not merely absent, when the transcriber heard words in music
WORD_MEASURES = ("A_time.words", "A_time.changes_in_sentence_gap", "A_time.changes_during_voice", "A_time.sentence_gaps")


def heard_in_music(m):
    """Why the reference's transcript is a false hearing (measure_film.no_voice, the rule vd measure applies when it
    measures), or None. Asked again here because a measure is cached: a music film measured before the rule knew a
    whole YouTube sign-off ("Thank you so much for watching this video, and I'll see you in the next one.") pinned 1.36
    words a second."""
    ws = [{"w": w.get("w", ""), "t0": w.get("t0", 0.0), "t1": w.get("t1", 0.0)} for w in m.get("words") or []]
    if not ws:
        return None
    import measure_film
    return measure_film.no_voice(ws, (m.get("A_time") or {}).get("length_s") or (ws[-1]["t1"] - ws[0]["t0"]))


def cmd_pin(a):
    d = film_dir(a.film)
    m, src = measures_of(a.ref, no_voice=getattr(a, "no_voice", False))
    num = {k: v for k, v in leaves(m).items() if not isinstance(v, list)}
    why = None if getattr(a, "no_voice", False) else heard_in_music(m)
    if not_transcribed(m):
        print(f"no words-per-second target: the reference's words were not transcribed ({not_transcribed(m)}); its word measures are unknown, "
              "not zero (give --no-voice if it has no voice)")
    if why:
        num = {k: v for k, v in num.items() if not k.startswith(WORD_MEASURES)}
        print(f"no words-per-second target: the reference's words look like a false hearing ({why}); its word measures are left out "
              "(give --no-voice to measure it without the transcriber)")
    s = score_of(d)
    s["pinned"] = str(src)
    s["targets"] = {k: round(num[k], 4) for k in PIN_KEYS if k in num} or {k: round(v, 4) for k, v in list(num.items())[:20]}
    s["targets_all"] = {k: round(v, 4) for k, v in num.items()}
    (d / "score.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    print(f"pinned {src}: {len(s['targets'])} targets in score.json (all {len(num)} numbers under targets_all)")
    made_it(d / "score.json")
    for k, v in s["targets"].items():
        print(f"  {k}: {v}")
    t0 = time.monotonic()
    got = pin_material(Path(a.ref), outdir(d), k=a.k)
    if got:
        story, moving = sorted(got.glob("story-*.jpg")), sorted(got.glob("move-*.jpg"))
        print(f"the pinned film to take apart, in {got} ({time.monotonic() - t0:.1f} s): the story, {len(story)} sheet{'s' if len(story) != 1 else ''} at two frames a second, and its "
              f"motion, every frame of the {len(moving)} one-second stretches where it changes most, laid out as vd pack lays out ours:")
        for f in story + moving:
            print(f"  {f}")
        keys = sorted(got.glob("key-*.jpg"), key=lambda f: int(f.stem.split("-")[1]))
        if keys:
            print(f"and {len(keys)} frames at full size, each in the middle of the quietest stretch of its sixth of the film, to read an interface by:")
            for f in keys:
                print(f"  {f}  {key_time(f)}")
        made_it(got)
    return 0


def key_time(f):
    """The time a pin key was taken at, from its JPEG comment."""
    try:
        from PIL import Image
        with Image.open(f) as im:                                 # closed at once: Windows keeps an open file from being removed
            return im.info.get("comment", b"").decode("utf-8", "replace")
    except Exception:
        return ""


def pin_material(ref, out, cache_root=None, k=None):
    """What a maker needs to take the pinned film apart, into OUT/pin: its story and motion sheets, made by vd pack's own
    code (pack.reader_material) and cached beside its measures. One film's maker measured the reference and then had to build a
    sheet of it with ffmpeg to see it, and four frames a second showed no motion. None when what was pinned is a
    measures.json, not a film."""
    if ref.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm", ".m4v"):
        return None
    import pack
    src = pack.ref_sheets(ref.resolve(), None, None, cache_root, pack.K if k is None else k)
    dst = out / "pin"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    for f in pack.pictures(src):
        shutil.copy2(f, dst / f.name)
    pack.rest_keys(ref.resolve(), dst)
    return dst


# ---------------------------------------------------------------- pack

def key_home(film):
    """Where a film's pack keys go when vd pack runs outside its folder: the film's own folder under OUTROOT when the film
    is one vd made (NAME.mp4, or cuts/NAME-cutN.mp4, both under OUTROOT/NAME), else OUTROOT/STEM. Keyed by each file's
    stem, a pack of cut 2 started again at pack 1 and dealt the letters pack 1 had."""
    f = Path(film).resolve()
    try:
        return OUTROOT / f.relative_to(OUTROOT.resolve()).parts[0]
    except (ValueError, IndexError):
        return OUTROOT / f.stem


def cmd_pack(a):
    """The blind pack (tools/pack.py): a line-up under letters and ours alone, in a folder of its own under ~/.vd/reads
    with a random name (no film's name anywhere in its path), its key file under ~/.vd/out/NAME, outside it."""
    import pack
    d = film_dir(a.film, required=False)
    out = outdir(d) if d is not None else key_home(a.target)
    folder, _key, _letters = pack.make(a.target, a.against or [], out, a.ref_first, a.ref_last, [float(t) for t in a.keys.split(",")] if a.keys else None,
                                       k=a.k, k_alone=a.k_alone)
    made_it(folder)
    return 0


# ---------------------------------------------------------------- scan

def cmd_scan(a):
    """tools/scan.py on a finished film, alone: what vd export prints after every export."""
    film = Path(a.target).resolve()
    if not film.is_file():
        raise SystemExit(f"no such film: {film}")
    d = film_dir(a.film, required=False)
    out = outdir(d) if d is not None else OUTROOT / film.stem
    out.mkdir(parents=True, exist_ok=True)
    # scan.txt is the scan of this folder's own film. A film from anywhere else, scanned while standing here, gets a
    # report under its own name: scanning a reference from inside a film folder once wrote over that film's scan
    own = film.parent.resolve() in (out.resolve(), (out / "cuts").resolve())
    got = scanned(film, out / ("scan.txt" if own else f"scan-{film.stem}.txt"), alone=True)
    if got:
        made_it(got)
    return 0 if got else 3


# ---------------------------------------------------------------- profile

NEW_CMD = re.compile(r"""(?:vd(?:\.py)?|\$\{?vd\}?)["']?\s+new\s+(?:"([^"]+)"|'([^']+)'|([^\s;&|]+))""", re.I)
CD_CMD = re.compile(r"""(?:^|&&|;|\n)\s*cd\s+(?:"([^"]+)"|'([^']+)'|([^\s;&|]+))""")


def made_here(line, d):
    """Does this transcript line hold a `vd new FOLDER` whose folder, resolved against the command's own `cd` or the
    session's working folder, is the film `d`? A review's finding: matching the folder's name alone missed `vd new C:/films/quiet`
    and accepted another folder's `new quiet`."""
    try:
        e = json.loads(line)
    except ValueError:
        return False
    want = os.path.normcase(str(Path(d).resolve()))
    for c in (e.get("message") or {}).get("content") or []:
        cmd = (c.get("input") or {}).get("command", "") if isinstance(c, dict) and c.get("type") == "tool_use" else ""
        for m in NEW_CMD.finditer(cmd):
            # from the session's folder, each `cd` before the command in its order, then the folder named: an absolute
            # one starts again, which is what joining paths does (a review's finding: only the last `cd` was applied)
            where = Path(e.get("cwd") or ".")
            for step in [*CD_CMD.finditer(cmd[:m.start()]), m]:
                folder = next(g for g in step.groups() if g)
                if os.name == "nt":                            # Git Bash writes C:/films as /c/films, which Python on
                    folder = re.sub(r"^/([A-Za-z])(/|$)", r"\1:/", folder)   # Windows reads as a folder named c
                where = where / folder
            if os.path.normcase(str(where.resolve())) == want:
                return True
    return False


def newest_transcript(d, days=7):
    """The session that made this film folder (a `vd new NAME` naming it), newest first; else the newest session from
    the last `days` days that names the folder. One maker got hundreds of another session's runs: that
    session, which named the folder in a brief, was newer than the maker's own."""
    root = Path.home() / ".claude" / "projects"
    key = str(d).replace("\\", "/").lower()
    keys = (key, key.replace("/", "\\\\"))
    cut = time.time() - days * 86400
    files = sorted((p for p in root.rglob("*.jsonl") if p.stat().st_mtime >= cut), key=lambda p: -p.stat().st_mtime) if root.exists() else []
    named = None
    for p in files:
        try:
            with p.open(encoding="utf-8", errors="replace") as fh:
                seen = False
                for line in fh:
                    low = line.lower()
                    if not seen and any(k in low for k in keys):
                        seen = True
                        named = named or p
                    if '"tool_use"' in low and "new" in low and made_here(line, d):
                        return p
        except OSError:
            pass
    return named


# ---------------------------------------------------------------- clean
# What a film's output folder holds that an export makes again, under the folder's lock, when it is missing: the drawn
# picture it reuses (an export redraws it when absent), the note of what it was drawn from, and raea's per-part records.
# Nothing else: folders such as sub/ or frames/ held finished films that nothing makes again, and files that vd sound
# or vd look write without the lock could go mid-build (a review's findings).
REBUILT = ("*.picture.mp4", "*.picture.mp4.sources.json", "*.part.render.json")


def _linked(p):
    """A symlink or a Windows junction: clean never follows one or removes through one (a linked output folder took
    clean outside VD_OUT, a review's finding). Other reparse points (a OneDrive or deduplicated file) are ordinary
    files that happen to be stored elsewhere, and are read as such."""
    try:
        st = os.lstat(p)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    tag = getattr(st, "st_reparse_tag", 0)
    return tag in (0xA0000003, 0xA000000C)    # IO_REPARSE_TAG_MOUNT_POINT (junction), IO_REPARSE_TAG_SYMLINK


def _size(p):
    p = Path(p)
    if _linked(p):
        return 0
    if p.is_file():
        return p.stat().st_size
    total = 0
    for root, dirs, files in os.walk(p, followlinks=False):
        dirs[:] = [d for d in dirs if not _linked(Path(root) / d)]
        total += sum((Path(root) / f).stat().st_size for f in files if not _linked(Path(root) / f))
    return total


def _rebuilt(o):
    """The files of output folder O that an export makes again: a picture only while it is the one its note recorded
    drawing (is_drawn), so a film folder called NAME.picture's own NAME.picture.mp4, `vd export -o OUT/custom.picture.mp4`
    and a finished film published at a former picture's name all stay (reviews' findings); a picture's note only with
    its picture or after it; raea's part records."""
    out = []
    for pat in REBUILT:
        for f in o.glob(pat):
            if not f.is_file() or _linked(f):
                continue
            if f.name.lower().endswith(".picture.mp4") and not is_drawn(f):
                continue
            if f.name.lower().endswith(".picture.mp4.sources.json"):
                pic = f.with_name(f.name[:-len(".sources.json")])
                if os.path.lexists(pic) and not is_drawn(pic):
                    continue
            out.append(f)
    return out


def _cut_files(o, stem, n):
    """Cut N of the film STEM in O/cuts, matched as text: NAME-cutN.mp4 and what an export writes beside it (its share
    copy, its sheets, a part left by a stopped export). A glob built from the name took a sibling film's cut when the
    name held [ or ? (film[1] matched film1); and any NAME-cutN-* took film-cut1-alt's only cut as film's cut 1's (both
    a review's findings)."""
    return [f for f in _named(o / "cuts", f"{stem}-cut{n}", r"(\.mp4|\.part\.mp4|-share\.mp4|-sheet(_\d+)?\.jpg)")
            if f.is_file() and not _linked(f)]


def clean_plan(o, keep_cuts=None, keep=()):
    """What vd clean would remove from one output folder O: [(path, bytes, why)]. Nothing is removed here. A finished
    film is listed only as an older cut the person asked to drop with --keep-cuts."""
    o = Path(o)
    plan = [(f, f.stat().st_size, "made again when needed") for f in _rebuilt(o)]
    if keep_cuts is not None and (o / "cuts").is_dir() and not _linked(o / "cuts"):
        cuts = {}
        # grouped by the name exactly as written: grouping without case merged STRASSE and Straße, which Windows keeps
        # apart, and removed one film's only cut (a council's finding). Where Draft and draft are one film this keeps
        # more than asked (Draft's cut 1 beside draft's newest), never less
        for f in (o / "cuts").iterdir():
            m = CUT.fullmatch(f.name)
            if m and f.is_file() and not _linked(f):
                cuts.setdefault(m.group(1), set()).add(int(m.group(2)))
        for stem, ns in sorted(cuts.items()):   # each film name keeps its own N newest (export -o gives a folder several)
            for n in sorted(ns)[:-keep_cuts]:
                if n in keep:   # a cut the person named with --keep, accepted or pinned, stays whatever its number
                    continue
                for f in _cut_files(o, stem, n):
                    plan.append((f, f.stat().st_size, f"{stem} cut {n}: older than its {keep_cuts} newest"))
    return plan


def orphan_note(o):
    """A line about an output folder whose film folder is not there, or None. Only said, never acted on: a film folder
    on an unplugged drive, an unmounted share or a moved project reads as missing too, and such folders hold cuts,
    blind-read keys and evolve keys that nothing else holds (a review's findings)."""
    try:
        owner = (Path(o) / OWNER).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not owner or os.path.lexists(owner):
        return None
    return f"its film folder {owner} is not there ({_size(o) / 2**20:,.0f} MB here); if it is gone for good, remove the folder yourself"


def _out_folder(name):
    """OUTROOT/NAME, for a NAME that is one folder in it and no link: clean reached outside VD_OUT through `../x`."""
    root = OUTROOT.resolve()
    if not name or name in (".", "..") or any(c in name for c in "/\\:") or Path(name).name != name:
        raise SystemExit(f"vd clean: {name!r} is not the name of one folder in {OUTROOT}")
    o = OUTROOT / name
    if not o.is_dir() or _linked(o) or o.resolve().parent != root:
        raise SystemExit(f"vd clean: no output folder called {name} in {OUTROOT}" + (" (it is a link; clean does not follow links)" if _linked(o) else ""))
    return o


def cmd_clean(a):
    """vd clean: what can go from ~/.vd/out (or VD_OUT), said before anything goes. Without --yes it only lists."""
    if a.keep_cuts is not None:
        # dropping cuts is done one film at a time: across every folder, one --keep meant for one film kept another's
        if a.keep_cuts < 1:
            raise SystemExit("vd clean: --keep-cuts takes 1 or more (the newest cut of each film always stays)")
        if len(a.names or ()) != 1:
            raise SystemExit("vd clean: --keep-cuts drops cuts of one film's folder at a time: name it (vd clean NAME --keep-cuts N)")
    if a.keep and a.keep_cuts is None:
        raise SystemExit("vd clean: --keep goes with --keep-cuts (plain clean never removes a cut)")
    # every folder the path passes through, as written: a relative VD_OUT stopped the walk up at ".", and abspath
    # folded link/.. away before it was looked at, while the walk itself went through the link (council findings)
    # and as Windows resolves it: a drive-relative VD_OUT (C:rel, the current folder on another drive) joined to the
    # current folder stayed C:rel and missed the junction under C:'s own current folder (a council's finding)
    given = OUTROOT if OUTROOT.is_absolute() else Path(os.getcwd()) / OUTROOT
    walks = (given, Path(os.path.abspath(OUTROOT)))
    linked = next((q for w in walks for q in (Path(*w.parts[:i]) for i in range(1, len(w.parts) + 1)) if _linked(q)), None)
    if linked is not None:
        # every file under a linked VD_OUT is reached through the link (a review's finding: a junction VD_OUT was listed)
        raise SystemExit(f"vd clean: {linked} is a link (to {linked.resolve()}), and clean never works through a link, so nothing was looked at. "
                         f"To clean the folder it points to, run it with VD_OUT set to that folder's own path.")
    if a.names:
        folders = [_out_folder(n) for n in a.names]
    else:
        folders = sorted(p for p in OUTROOT.iterdir() if p.is_dir() and not _linked(p)) if OUTROOT.is_dir() else []
    keep = set(a.keep or ())
    if keep:
        have = {int(m.group(2)) for f in ((folders[0] / "cuts").iterdir() if (folders[0] / "cuts").is_dir() else ())
                if (m := CUT.fullmatch(f.name)) and f.is_file() and not _linked(f)}   # a folder named like a cut is none
        wrong = sorted(k for k in keep if k not in have)
        if wrong:
            raise SystemExit(f"vd clean: no cut {', '.join(map(str, wrong))} in {folders[0].name}/cuts (its cuts: "
                             f"{', '.join(map(str, sorted(have))) or 'none'}); nothing was removed")
    total, freed, busy, stuck, unlisted = 0, 0, [], [], []
    for o in folders:
        plan = clean_plan(o, a.keep_cuts, keep)
        note = orphan_note(o) if a.orphans else None
        if note:
            print(f"{o.name}: {note}")
        unknown = [f for f in o.glob("*.picture.mp4") if f.is_file() and not _linked(f) and not is_drawn(f)]
        if unknown:
            # drawn before 0.2.2 (no record of the draw) or a finished film with a picture's name: never removed here
            print(f"{o.name}: left {len(unknown)} *.picture.mp4 ({sum(f.stat().st_size for f in unknown) / 2**20:,.0f} MB) with no record that an "
                  f"export drew {'it' if len(unknown) == 1 else 'them'} (drawn before 0.2.2, or a finished film); remove any that are old pictures yourself")
        if not plan:
            continue
        here = sum(b for _, b, _ in plan)
        total += here
        print(f"{o.name}: {here / 2**20:,.0f} MB")
        for f, b, why in plan:
            print(f"  {f.relative_to(OUTROOT)}  {b / 2**20:,.1f} MB  ({why})")
        if not a.yes:
            continue
        listed = {f for f, _, _ in plan}
        try:
            with held(o, "clean"):
                # what goes is decided again under the lock, and only what was listed goes: a cut that finished between
                # the list and the lock made cut 2 "older" and it went unnamed (a review's finding)
                left = set()   # pictures that stayed keep their notes, so a later clean still knows them as drawn
                for f, b, _ in clean_plan(o, a.keep_cuts, keep):
                    if f not in listed:
                        unlisted.append(str(f.relative_to(OUTROOT)))
                        continue
                    if f.name.endswith(".picture.mp4.sources.json") and f.name[:-len(".sources.json")] in left:
                        continue
                    try:
                        f.unlink()
                        freed += b
                    except FileNotFoundError:
                        pass
                    except OSError as e:   # open in a player, say: kept, and the rest still goes
                        stuck.append(f"{f.relative_to(OUTROOT)} ({e.strerror or e})")
                        left.add(f.name)
        except Busy as e:
            busy.append(f"{o.name} ({str(e) or 'in use'})")
    if not a.yes:
        print(f"\n{total / 2**20:,.0f} MB could go from {OUTROOT}. Nothing was removed: run again with --yes to remove it.")
    else:
        print(f"\nremoved {freed / 2**20:,.0f} MB from {OUTROOT}." + (" Skipped, in use: " + ", ".join(busy) if busy else "")
              + (" Not removed, open elsewhere: " + ", ".join(stuck) if stuck else "")
              + (" Not removed, not in the list above (the folder changed): " + ", ".join(unlisted) if unlisted else ""))
    return 0


def cmd_profile(a):
    d = film_dir(a.film)
    tr = [Path(t) for t in a.transcript] if a.transcript else [newest_transcript(d)]
    if not tr or tr[0] is None:
        raise SystemExit("no session transcript mentions this film folder: pass --transcript PATH.jsonl")
    out = outdir(d) / "profile"
    window = [*(["--since", a.since] if a.since else []), *(["--until", a.until] if a.until else [])]
    p = run([PY, "-X", "utf8", TOOLS / "profile_run.py", *tr, "-o", out, *window], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print((p.stdout + p.stderr).strip()[-2500:])
    print(f"written to {out} from {', '.join(t.name for t in tr)}")
    if p.returncode == 0:
        made_it(out)
    return p.returncode


# ---------------------------------------------------------------- borrow, capture, launch, foley, evolve, playable

def cmd_borrow(a):
    """vd borrow (not proven): a reference's moves fitted to springs and curves, and its held colours, into dna.json,
    kit/dna.gen.ts and REFERENCE.md."""
    import borrow
    d = Path(a.out).resolve() if getattr(a, "out", None) else film_dir(a.film, required=False)
    out_dir, dna = borrow.compile_dna_cartridge(
        ref_video=Path(a.ref),
        out_dir=d,
        repo_dir=Path(a.for_repo) if getattr(a, "for_repo", None) else None,
        k=getattr(a, "k", 5),
        like=getattr(a, "like", None),
    )
    borrow.say(a.ref, out_dir, dna)
    return made_it(out_dir)


def cmd_capture(a):
    """vd capture (not proven): a repository's counts, or a command's real output lines and times, into
    kit/puppet.gen.ts, and kit/PuppetPlane.tsx to show them."""
    import puppet
    d = film_dir(a.film)
    repo_dir = Path(a.repo).resolve() if getattr(a, "repo", None) else d
    repo_data = puppet.analyze_codebase(repo_dir)
    if getattr(a, "cmd_str", None):
        term_data = puppet.capture_command(a.cmd_str, repo_dir, timeout=a.timeout)
    else:
        term_data = puppet.counts_record(repo_data)
    gen_path, _comp_path = puppet.write_puppet_files(d, repo_data, term_data, cue=getattr(a, "cue", "hit") or "hit")
    return made_it(gen_path)


def cmd_launch(a):
    """vd launch (not proven): a copy of Stet with vd capture run into it, the counts in REPO-FACTS.md, and the plane
    put in the film for four seconds from its NUMBERS cue."""
    import puppet
    out_dir, _repo_data = puppet.build_launch_film(
        repo_dir=Path(a.repo or "."),
        out_dir=Path(a.out) if getattr(a, "out", None) else None,
        cmd=getattr(a, "cmd_str", None),
        like=getattr(a, "like", None) or "stet",
    )
    return made_it(out_dir)


def cmd_foley(a):
    """vd foley (not proven): media/foley.wav, made by rule from camera moves and cues read from the film's code
    (~/.vd/out/NAME/telemetry.gen.json); nothing is measured from the drawn picture."""
    import foley
    d = film_dir(a.film)
    out_wav = Path(a.o).resolve() if getattr(a, "o", None) else None
    wav_path, _tel_path, summary = foley.run_foley(d, out_wav=out_wav, mix_into_sound=getattr(a, "mix", False))
    print(summary)
    return made_it(wav_path)


def cmd_evolve(a):
    """vd evolve (not proven): four world sketches, one after each worked film, as a blind line-up
    (tournament/A..D), or the chosen one copied into the film folder with --select."""
    import evolve
    d = Path(a.name).resolve() if getattr(a, "name", None) else film_dir(a.film, required=False)
    if d is None:
        raise SystemExit("give a film folder name (`vd evolve NAME`) or run inside a film folder")
    if getattr(a, "select", None) or getattr(a, "readings", None):
        evolve.select_winner(
            root=d,
            letter=getattr(a, "select", None),
            against=Path(a.mutate) if getattr(a, "mutate", None) else None,
            readings=Path(a.readings) if getattr(a, "readings", None) else None,
            key_file=Path(a.key) if getattr(a, "key", None) else None,
        )
        return made_it(d)
    if getattr(a, "mutate", None):
        raise SystemExit("vd evolve --mutate goes with --select (or --readings): it fits the chosen sketch to a reference film")
    tourn_dir, _key_path, _brief_path, _mapping = evolve.build_tournament(
        name=str(d),
        brief=getattr(a, "brief", None),
        repo_dir=Path(a.for_repo) if getattr(a, "for_repo", None) else None,
        render=getattr(a, "render", False),
        seed=getattr(a, "seed", None),
    )
    return made_it(tourn_dir)


def cmd_playable(a):
    """vd playable (not proven): a browser page that builds the film's code against a stand-in for raea, for
    scrubbing, in ~/.vd/out/NAME/playable/index.html. It is not the film."""
    import playable
    d, entry, _s = where(a)
    out = Path(a.o).resolve() if getattr(a, "o", None) else outdir(d) / "playable"
    index_html, _bundle_js = playable.build_playable(d, entry=entry, out_dir=out)
    return made_it(index_html)


def cmd_audio(a):
    """vd audio (not proven), from legible-film: clean a recorded voice (voice_clean.py), make a music track the film's
    beat (tempo_map.py: score.json's music, which the film's sound.py and the mix read), or draw a track's sound (listen.py)."""
    import listen
    import tempfile
    import tempo_map
    import voice_clean
    # cleaning a voice and mapping a track write into a film folder, so they need one; only the sheet can stand alone
    d = film_dir(a.film, required=getattr(a, "clean_voice", False) or getattr(a, "tempo_map", False))
    src = Path(a.track).resolve()
    o = getattr(a, "o", None)
    sheet = getattr(a, "sheet", False) or (not getattr(a, "clean_voice", False) and not getattr(a, "tempo_map", False))
    if o and getattr(a, "clean_voice", False) and sheet:
        # one -o, two outputs: the cleaned voice was written to custom.png and the sheet over it, and score.json named the picture
        raise SystemExit("vd audio: -o names one file, and --clean-voice and --sheet each make one; run them apart")
    if o and sheet and not getattr(a, "clean_voice", False) and not str(o).lower().endswith(".png"):
        raise SystemExit(f"vd audio --sheet: -o {o} is not a .png, and the sheet is a picture")
    if not src.is_file():
        raise SystemExit(f"no such audio file: {src}")
    last_made = src
    if getattr(a, "clean_voice", False):
        (d / "media").mkdir(parents=True, exist_ok=True)
        cleaned = Path(a.o).resolve() if getattr(a, "o", None) else (d / "media" / f"{src.stem}-clean.wav")
        if cleaned == src:
            raise SystemExit("vd audio --clean-voice: -o names the take itself; give the cleaned voice a new name")
        # Nothing the command writes may be the take or the voice the film uses: the cleanup is made in a file of its own
        # beside the output, and a refused one goes to the first -partial name that is neither.
        voice = score_of(d).get("voice") if (d / "score.json").is_file() else None
        # the voice is a path, or {"file": path, "at": ..., "gain": ...} (TECHNIQUES.md, "A recorded voice"): both are the film's
        voice = voice.get("file") if isinstance(voice, dict) else voice
        voice = d / voice if isinstance(voice, str) and voice else None
        keep = {src, voice.resolve() if voice else None}
        partial = next(c for c in (cleaned.with_name(f"{cleaned.stem}-partial{'' if n == 1 else f'-{n}'}.wav") for n in range(1, 1000))
                       if c.resolve() not in keep)
        cleaned.parent.mkdir(parents=True, exist_ok=True)
        fd, fresh = tempfile.mkstemp(prefix=f".{cleaned.stem}-", suffix=".wav", dir=cleaned.parent)
        os.close(fd)
        fresh = Path(fresh)
        try:
            rep = voice_clean.clean_voice(src, fresh)
        except BaseException as e:  # a refusal to read, a failed ffmpeg step or a stop: this run's own file goes with it
            fresh.unlink(missing_ok=True)
            if isinstance(e, ValueError):
                raise SystemExit(f"vd audio --clean-voice: {e}")
            raise
        if rep["refused"]:
            os.replace(fresh, partial)
            print(f"voice_clean: {rep['refused']} (noise floor {rep['noise_floor_used_dbfs']} dBFS). The steps before it are in "
                  f"{partial.name}; {cleaned.name} and score.json's voice are unchanged. Listen before using it.")
            cleaned = partial
        else:
            os.replace(fresh, cleaned)
            print(f"voice_clean: every step applied (noise floor {rep['noise_floor_used_dbfs']} dBFS) -> {cleaned}")
        if not rep["refused"] and (d / "score.json").is_file():
            s = score_of(d)
            new = cleaned.relative_to(d).as_posix() if cleaned.is_relative_to(d) else str(cleaned)
            # a voice named as {"file", "at", "gain"} keeps where it starts and its level: only its file changes
            s["voice"] = {**s["voice"], "file": new} if isinstance(s.get("voice"), dict) else new
            (d / "score.json").write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
        last_made = cleaned
    if getattr(a, "tempo_map", False):
        try:
            res, gen_path = tempo_map.compile_into_film(d, src, bpm=getattr(a, "bpm", None), drop_at_beat=getattr(a, "drop_at_beat", None),
                                                        replace=getattr(a, "replace_own_mix", False))
        except ValueError as e:
            raise SystemExit(f"vd audio --tempo-map: {e}")
        m = score_of(d)["music"]
        if (d / "sound.py").is_file():
            print(f"tempo_map: {res['bpm']:.2f} BPM, fitted to {m['film_bpm']:g} BPM ({m['fb']} frames a beat, stretched x{m['stretch']:.4f}) "
                  f"-> {m['file']} and score.json's music{('; ' + m['octave']) if m.get('octave') else ''}; its beats sit {m['off_grid_ms']['median']:g} ms from the grid at the median, 90% within "
                  f"{m['off_grid_ms']['p90']:g} ms, and slide {m['off_grid_ms'].get('drift')} ms over the track (refused above {tempo_map.DRIFT_MAX_MS:g}; a floor, so listen). Now run the film's sound.py, so its beats, its picture and its sound move "
                  f"onto this tempo; then vd sound or vd export lays the track {'in place of' if m['replace'] else 'under'} the film's own mix:\n"
                  f"{run_sound_py(d)}")
        else:
            print(f"tempo_map: {res['bpm']:.2f} BPM, fitted to {m['film_bpm']:g} BPM -> {m['file']} and score.json's music; vd sound and vd export "
                  f"lay it {'in place of' if m['replace'] else 'under'} the rest. This film has no sound.py: its scenes are in seconds "
                  f"(score.json's beats), so put their edges on the track's beats, every {m['fb'] / int(score_of(d).get('fps') or 30):.4f} s "
                  f"from its first beat at {m['first_beat_s']:g} s.")
        last_made = gen_path
    if getattr(a, "sheet", False) or (not getattr(a, "clean_voice", False) and not getattr(a, "tempo_map", False)):
        # outside a film folder the sheet goes beside the track (it had made an output folder named after the folder run in)
        out_png = Path(o).resolve() if o else (outdir(d) / "listen-sheet.png" if d else src.with_name(f"{src.stem}-sheet.png"))
        cues = (gen_data(d).get("CUES") or []) if d else []
        heard = last_made if getattr(a, "clean_voice", False) and last_made.suffix.lower() == ".wav" else src   # the cleaned voice, when there is one
        prof = listen.measure(heard)
        sh = listen.sheet(heard, out_png, cues_list=cues)
        m = prof["measurements"]
        print(f"listen: {m['integrated_lufs']} LUFS, {m['true_peak_dbtp']} dBTP, width {m['side_to_mid_db']} dB, corr {m['correlation']}; sheet -> {sh['png']}")
        last_made = Path(sh["png"])
    return made_it(last_made)


def cmd_bridge(a):
    """vd bridge (not proven): cues.json bound to the exported file, picture-timing.json, a Final Cut Pro 7 XML
    file and an OpenTimelineIO file."""
    import bridge
    d = film_dir(a.film)
    out = Path(a.o).resolve() if getattr(a, "o", None) else (outdir(d) / "bridge")
    res = bridge.export_bridge(
        film_dir=d,
        video_path=Path(a.video) if getattr(a, "video", None) else None,
        out_dir=out,
        host_in_s=float(getattr(a, "host_in", 0.0) or 0.0),
    )
    print(f"bridge bundle in {res['out_dir']}: {res['cues_json'].name}, {res['timeline_xml'].name}, {res['timeline_otio'].name}")
    return made_it(res["timeline_xml"])


# ---------------------------------------------------------------- entry

def home(argv):
    """A leading ~ made the home folder. The pages give paths as ~/.vd/out/NAME/..., and a shell that leaves ~ to the
    program (PowerShell does, for a program that is not its own) handed the tools a folder called ~."""
    return [os.path.expanduser(x) if x == "~" or x[:2] in ("~/", "~" + chr(92)) else x for x in argv]


def main(argv=None):
    argv = home(list(sys.argv[1:] if argv is None else argv))
    if argv and argv[0] == "steal":   # 0.2.0's name for vd borrow: it still runs, and says what it is called now
        print("vd steal is now vd borrow; running vd borrow.", file=sys.stderr)
        argv[0] = "borrow"
    ap = argparse.ArgumentParser(prog="vd", description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    NP = 'Not proven on a film (SKILL.md, "Newer commands"). '  # the newer commands' help says so where an agent reads it
    sub = ap.add_subparsers(dest="cmd", required=True)
    films = worked_films()
    s = sub.add_parser("new", help="a film folder that starts from a working film", formatter_class=argparse.RawDescriptionHelpFormatter,
                       description="Needs nothing. --kind writes NAME/ with its entry, kit/ and score.json: explainer, launch, vertical and app (a light "
                                   "interface in a window), all page films. --like copies a whole "
                                   "worked film from library/films to NAME/ and runs its sound.py.",
                       epilog="Worked films (--like):\n" + ("\n".join(f"  {n:10} {line}" for n, line in films.items()) or "  none"))
    s.add_argument("name"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--kind", choices=KINDS); g.add_argument("--like", metavar="FILM", help="a worked film from library/films (listed below)")
    s.add_argument("--bare", action="store_true", help="explainer, launch, vertical: only the frame, the score's clock, finish and the grain")
    s.set_defaults(fn=cmd_new)
    s = sub.add_parser("look", help="many moments as one picture, and what did not draw",
                       description="Needs ENTRY.tsx (with --composition and --at), or a vd new folder (score.json gives the composition and the moments). "
                                   "Runs raea scene lint and world --no-render first and stops on a fault before taking a place in the render queue.")
    s.add_argument("entry", nargs="?"); s.add_argument("--at", help="seconds, comma separated. One moment gives that frame at full size (up to 1920 wide, a JPEG with its time in a "
                   "band above it), for checking type and edges; several make one contact sheet")
    s.add_argument("-o", dest="out"); s.add_argument("--composition")
    s.add_argument("--all", action="store_true", help="print every finding on every tile; by default each kind is said once with a count and its three "
                   "worst cases, text cut by the frame's edge first, and the whole report is written beside the picture under its name and -report.txt (look-report.txt, unless -o names another picture)"); s.set_defaults(fn=cmd_look)
    s = sub.add_parser("sound", help="the sound with no picture, mixed and checked",
                       description="In a film copied with --like and given no voice: the film's own mix (the wav its sound.py wrote) is checked as it is; nothing is built or levelled, and a change to the sound means running sound.py again. "
                                   "In any other vd new folder: built from score.json (voice, stems, made sounds, bed, Tone music), levelled to -15 LUFS with headroom under the -1 dB true-peak limit, then checked; "
                                   "a verdict line says whether the sound passes (-15 LUFS within 1, true peak under -1 dB, no silent hole) or what fails. "
                                   "For any film: vd sound ENTRY.tsx --composition ID renders the entry's own sound alone (no frame drawn) and checks it. --onto FILM.mp4 copies the picture and adds the sound.")
    s.add_argument("entry", nargs="?"); s.add_argument("--composition"); s.add_argument("--onto"); s.add_argument("-o")
    s.add_argument("--from-score", action="store_true", help="with ENTRY: build from the score.json beside it instead"); s.set_defaults(fn=cmd_sound)
    s = sub.add_parser("render", help="render seconds A..B only, and splice them in",
                       description="Needs a vd new folder: its film.tsx exports Film({offset}), and the picture vd export made (in ~/.vd/out/NAME) is what it splices into.")
    s.add_argument("--from", dest="from_"); s.add_argument("--to"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("export", help="the finished film: picture rendered once, sound copied on",
                       description="Needs ENTRY.tsx with --composition (any film), or a vd new folder. Sound: --sound WAV, else score.json's, else the entry's own rendered alone. "
                                   "Runs raea scene lint and world --no-render first. "
                                   f"The film goes to {OUTROOT}{os.sep}NAME{os.sep}NAME.mp4 (NAME: the folder's name, or the entry's) unless -o names it; "
                                   f"each export that works is also kept as a numbered cut, {OUTROOT}{os.sep}NAME{os.sep}cuts{os.sep}NAME-cutN.mp4 with its share copy "
                                   "and sheets (N counts up; the film named above is always the latest cut, and a failed export removes no finished cut); "
                                   f"the picture without sound stays in {OUTROOT}{os.sep}NAME. A folder whose score.json names a sound_file (a film copied with --like) "
                                   "carries that file as it is, or, when score.json also names a voice, the voice mixed over it (ducked under its words); "
                                   "it stops when sound.py is newer than that file or than kit/times.gen.ts. After the export, the film is scanned (vd scan: pops, holds, level); "
                                   "the last line printed is the film's path.")
    s.add_argument("entry", nargs="?"); s.add_argument("--composition"); s.add_argument("--sound")
    s.add_argument("-o", help=f"where the film goes (default {OUTROOT}{os.sep}NAME{os.sep}NAME.mp4)")
    s.add_argument("--again", action="store_true", help="render the picture even if it is current")
    s.set_defaults(fn=cmd_export)
    s = sub.add_parser("pack", help="a blind line-up of up to four films, and ours alone, for readers",
                       description="Needs our film; --against adds a film to the line-up, up to three times (a reference, a known-good film, an earlier cut: "
                                   "vd export keeps each as ~/.vd/out/NAME/cuts/NAME-cutN.mp4). "
                                   "Writes the pack to a folder of its own under ~/.vd/reads with a random name, so no film's name is in the path a reader is "
                                   "given: lineup/A to lineup/D, one folder a film under a letter dealt anew each pack (the same "
                                   "letters when that pack number is made again), each holding its story (the whole film at 2 frames a second, story-01.jpg "
                                   "..., sheets of 6 x 4 tiles, the time on each) and its motion (every frame of the --k one-second stretches where the "
                                   "picture changes most, move-1.jpg ... in time order, the time and frame on each); and alone/, ours for the fault-finder: "
                                   "its story, --k-alone stretches and five full-size keys. With no --against, only alone/. No film's name inside the pack; "
                                   "~/.vd/out/NAME/pack-N-KEY.txt, outside it, says where it is and which letter is which film. Both paths are printed.")
    s.add_argument("target", metavar="FILM"); s.add_argument("--against", action="append", metavar="REF", help="a film for the line-up; up to three times")
    s.add_argument("--ref-first", type=float, metavar="N", help="only each --against film's first N seconds (alone, or with --ref-last)")
    s.add_argument("--ref-last", type=float, metavar="M", help="only its last M seconds (alone, or with --ref-first)")
    s.add_argument("--keys", metavar="T1,T2,...", help="times of the five full-size keys in alone/")
    s.add_argument("--k", type=int, default=5, metavar="N", help="stretches of motion, every frame, for each film in the line-up (default 5)")
    s.add_argument("--k-alone", type=int, default=10, metavar="N", help="stretches of motion for ours alone (default 10)"); s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("measure", help="the gap table against a reference", description="Needs two films (or measures.json files); a vd new folder only to keep GAP.md in out/.")
    s.add_argument("target"); s.add_argument("--against"); s.add_argument("--bare", help="a bare pass (the brief made with no direction): rank gaps in units of its spread from the reference")
    s.add_argument("--no-voice", action="store_true", help="no film here has a voice (ours, the reference and the bare pass): skip the transcriber and the "
                   "render queue for all of them. Without it, a film whose words could not be transcribed (no transcriber here) says so, and its "
                   "word measures are left out"); s.set_defaults(fn=cmd_measure)
    s = sub.add_parser("pin", help="the reference's numbers into score.json", description="Needs a vd new folder (it writes score.json) and a reference film or measures.json. "
                       "For a film, also writes what a maker needs to take it apart into ~/.vd/out/NAME/pin: its story (2 frames a second) and the motion of its "
                       "--k busiest seconds, every frame, as vd pack lays them out, and six frames at full size (key-1.jpg to key-6.jpg), each "
                       "where the picture is at rest in its sixth of the film, its time beside it.")
    s.add_argument("ref"); s.add_argument("--k", type=int, default=5, metavar="N", help="how many one-second stretches of motion (default 5)")
    s.add_argument("--no-voice", action="store_true", help="the reference has no voice (music only): skip the transcriber, and pin no word targets. "
                   "Without it, words that look like a known false hearing are said in one line and left out"); s.set_defaults(fn=cmd_pin)
    s = sub.add_parser("scan", help="pops, holds and level of a finished film", description="Needs a finished film (vd export runs this on every export). "
                       "Frames that pop, stretches that stand still for 0.5 s or more, and the sound's level and true peak; a line starting "
                       "`fix before anyone watches:` for each pop, and one starting `check:` for each hold over 1 s (a hold can be chosen). Written to ~/.vd/out/NAME/scan.txt. Never fails.")
    s.add_argument("target", metavar="FILM"); s.set_defaults(fn=cmd_scan)
    s = sub.add_parser("clean", help="what can go from ~/.vd/out, and with --yes, remove it",
                       description="Lists, by output folder, what an export makes again when it is missing (the drawn picture it reuses, the note of what it was drawn from, raea's per-part records) and its size. "
                                   "Everything else stays: cuts, share copies, sheets, scans, keys, pins, notes and any folder. --keep-cuts N also lists all but the N newest cuts of each film name, except cuts named with --keep; --keep-cuts works on one named folder; --orphans also names folders whose film folder is not there, and removes nothing of theirs but the above. Nothing is removed without --yes, and a folder an export holds is skipped.")
    s.add_argument("names", nargs="*", metavar="NAME", help="output folders to look in (default: all of them)")
    s.add_argument("--keep-cuts", type=int, metavar="N", help="also list all but each film name's N newest cuts (N is 1 or more)")
    s.add_argument("--keep", type=int, action="append", metavar="CUT", help="with --keep-cuts: keep this cut number too, whatever its age (an accepted or pinned cut); repeat for more")
    s.add_argument("--orphans", action="store_true", help="also name folders whose film folder is not there (never removed: the drive may only be unplugged)")
    s.add_argument("--yes", action="store_true", help="remove what is listed"); s.set_defaults(fn=cmd_clean)
    s = sub.add_parser("profile", help="minutes by class for the session that made a film", description="Needs a vd new folder and a Claude Code session log: the newest that names the folder, or --transcript PATH.jsonl.")
    s.add_argument("--transcript", action="append")
    s.add_argument("--since", help="only the session from this UTC time (ISO), for a film made inside a longer session")
    s.add_argument("--until", help="only the session up to this UTC time (ISO)"); s.set_defaults(fn=cmd_profile)
    s = sub.add_parser("borrow", help="not proven: a reference's fitted moves and colours",
                       description=NP + "Fits each move the reference makes to a spring (how fast, how damped) and a curve, and takes its colours (every ground, a full-frame colour held 0.5 s or more, with its times; the accents on them), into dna.json, kit/dna.gen.ts and a REFERENCE.md to finish by TAKE-APART.md. A move with no usable profile is marked unfitted; when no move fits, DNA_SPRING and DNA_BEZIER are null and it says so. It pins no targets: run vd pin REF as well, since vd measure reads pin's numbers.")
    s.add_argument("ref", metavar="REF.mp4"); s.add_argument("--for", dest="for_repo", metavar="REPO", help="also record this repository's counts in dna.json (nothing reads them yet)")
    s.add_argument("-o", "--out", dest="out", help="destination film folder"); s.add_argument("--k", type=int, default=5)
    s.add_argument("--like", choices=("plusone", "stet", "onoma", "linden"), help="the worked film to copy when borrow makes a new film folder (plusone, stet, onoma, linden): chosen, never guessed"); s.set_defaults(fn=cmd_borrow)
    s = sub.add_parser("capture", help="not proven: a repository's counts or a command's output, as a plane your film imports",
                       description=NP + "Writes kit/puppet.gen.ts (the repository's counts, read by file and name patterns, so check them; or, with --cmd, the command's real output lines and times, every line whole) and kit/PuppetPlane.tsx, a plane that shows them, the latest eight at a time as a terminal scrolls. Your film must import the plane itself. The command runs with no shell.")
    s.add_argument("--cmd", dest="cmd_str", help="a program and its arguments, run with no shell, its output lines recorded with their times")
    s.add_argument("--repo", help="repository folder to count (default: the film folder)")
    s.add_argument("--timeout", type=float, default=30.0, help="seconds the command may run before it is stopped (default 30)")
    s.add_argument("--cue", default="hit", help="cue name in kit/times.gen.ts to sync terminal lines to"); s.set_defaults(fn=cmd_capture)
    s = sub.add_parser("launch", help="not proven: a copy of stet with a repository's counts on screen in it",
                       description=NP + "Copies Stet and runs vd capture into it, writing the counts to REPO-FACTS.md for your board, and puts the plane in the film for four seconds from Stet's NUMBERS cue, on Stet's own paper: a start, to move where your board puts it.")
    s.add_argument("repo", nargs="?", default=".", metavar="REPO"); s.add_argument("-o", "--out", dest="out")
    s.add_argument("--like", choices=("plusone", "stet", "onoma", "linden"), help="override archetype")
    s.add_argument("--cmd", dest="cmd_str", help="a program to run with no shell and record, as vd capture --cmd"); s.set_defaults(fn=cmd_launch)
    s = sub.add_parser("foley", help="not proven: a sound track made by rule from the moves in the film's code",
                       description=NP + "Reads camera moves and named cues from the film's code by pattern (sizes are guessed from cue names, not measured from the picture) into ~/.vd/out/NAME/telemetry.gen.json, outside the film, and makes media/foley.wav from them. Nothing plays it unless you mix it. "
                                   "Its level: --mix adds it 9.5 dB under media/sound.wav and moves the whole toward -15 LUFS by at most 6 dB with its true peak at "
                                   "-2.2 dBTP, and says the level it wrote. Under a track mapped with vd audio --tempo-map, the film's own mix (foley and all) "
                                   "plays at score.json's sound_file_gain, in dB (0 when absent): raise or lower it there.")
    s.add_argument("-o", help="output wav path (default media/foley.wav)")
    s.add_argument("--mix", action="store_true", help="also add it into media/sound.wav, which sound.py owns: its next run drops it, and a second --mix adds it twice; prints the level written"); s.set_defaults(fn=cmd_foley)
    s = sub.add_parser("evolve", help="not proven: four world sketches as a blind line-up",
                       description=NP + "Packs four sketches, one after each worked film, as a blind line-up (tournament/A..D, its key in evolve-N-KEY.txt). Without --render each sketch is a fixed drawing per worked film with your subject's name on it; with it, the worked films are drawn untouched. Letters are dealt at random (the key file records them); --seed fixes them for a test. The person picks the world (EYES.md, Readers).")
    s.add_argument("name", nargs="?", help="film folder name"); s.add_argument("--for", dest="for_repo", metavar="REPO", help="put this repository's counts on each sketch's board")
    s.add_argument("--render", action="store_true", help="draw each worked film's three moments with vd look instead of the fixed drawings")
    s.add_argument("--brief", help="the subject, in a line, written on each sketch's board (default: the repository's name or the folder's)")
    s.add_argument("--seed", type=int, default=None); s.add_argument("--select", choices=("A", "B", "C", "D"), help="make the film folder that sketch's film (what was in it moves to ~/.vd/out/NAME/before-select-N); refused if the sketch changed since it was read")
    s.add_argument("--readings", help="sum the readers' ranks in READINGS.md and promote the top sketch; readers rank sparse sketches higher, so prefer --select with the person's pick")
    s.add_argument("--key", help="explicit evolve-N-KEY.txt path"); s.add_argument("--mutate", help="nearest reference MP4 to pin/borrow into the winning candidate"); s.set_defaults(fn=cmd_evolve)
    s = sub.add_parser("playable", help="not proven: a browser page that imitates the film, for scrubbing",
                       description=NP + "Builds the film's code against a small stand-in for raea into ~/.vd/out/NAME/playable/index.html, scrubbed with the wheel, the whole frame scaled to any window, with the sound the export lays under the picture (the film's own mix, or the mix built from score.json with its voice and mapped track). It is not the film: raea does not draw it, nothing compares its frames with the export, and parts of the kit (Freeze in kit/lib/finish.tsx, 3D) do not build. Needs esbuild or bun.")
    s.add_argument("entry", nargs="?"); s.add_argument("-o", help="output directory (default ~/.vd/out/NAME/playable)"); s.set_defaults(fn=cmd_playable)
    s = sub.add_parser("audio", help="not proven: clean a voice, make a music track the film's beat, or draw a track's sound",
                       description=NP + "From legible-film. --clean-voice: five steps, each refused when it costs the speech more than 3 dB; a refusal keeps the steps before it in NAME-clean-partial.wav and leaves the film's voice as it was. --tempo-map: makes the track the film's beat: score.json's music holds its tempo and the nearest whole frames a beat, and media/NAME-fitted.wav the track stretched (at most 3%) and placed so its first beat, or its drop with --drop-at-beat, falls on a beat; run the film's sound.py next, which takes the beat from it, and the mix lays the track under the film's own (or in its place, --replace-own-mix). A track with no steady beat, needing more stretch, or whose beat slides more than 40 ms from one steady grid (measured stretch by stretch, 16 beats each; a floor, since it does not follow a beat) is refused with the numbers. --bpm takes 60 to 200. --sheet: the track's sound drawn as one picture.")
    s.add_argument("track", metavar="TRACK.wav"); s.add_argument("--clean-voice", action="store_true", help="five-step dialogue cleanup into media/")
    s.add_argument("--tempo-map", action="store_true", help="make the track the film's beat (then run the film's sound.py)")
    s.add_argument("--sheet", action="store_true", help="draw the track's sound, its onsets and the film's cues as one picture")
    s.add_argument("--bpm", type=float, help="narrow BPM prior for --tempo-map"); s.add_argument("--drop-at-beat", type=int, help="place the track so its loudest drop falls on this film beat")
    s.add_argument("--replace-own-mix", action="store_true", help="with --tempo-map: the track in place of the film's own mix, not under it")
    s.add_argument("-o", help="output path"); s.set_defaults(fn=cmd_audio)
    s = sub.add_parser("bridge", help="not proven: the export's cuts for an editor or legible-film",
                       description=NP + "Writes cues.json (the shape legible-film reads, bound to the exported file by its video stream's hash, picture.sha256; the whole file's is picture.file_sha256), picture-timing.json, a Final Cut Pro 7 XML file and an OpenTimelineIO file. Both place the picture and the sound the file has alike, --host-in a gap before them. No editing program has opened them: check them in the program.")
    s.add_argument("--video", help="the exported film (default ~/.vd/out/NAME/NAME.mp4); refused when missing")
    s.add_argument("--host-in", type=float, default=0.0, help="host timeline start offset in seconds")
    s.add_argument("-o", help="output directory (default ~/.vd/out/NAME/bridge)"); s.set_defaults(fn=cmd_bridge)
    for p in sub.choices.values():
        p.add_argument("--film", help="the film folder (default: the nearest folder at or above here with score.json)")
    if argv and argv[0] in NOT_PROVEN:
        # said where the command is called, not only in SKILL.md, and before its arguments are read, so a call that
        # stops on a usage error hears it too (it was said only once parsing passed: a review's finding)
        print(f"note: vd {argv[0]} is not proven on a film yet (no accepted film was made through it; SKILL.md, \"Newer "
              "commands\"). Prefer the older route when it does the job.", file=sys.stderr)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)   # so what is printed comes out in the order it was said, piped or not
    except (AttributeError, ValueError):
        pass
    MADE.clear()
    t0 = time.monotonic()
    code = 1
    try:
        r = a.fn(a)
        code = r if isinstance(r, int) else 0
        return code
    finally:
        place = Path(a.name).resolve() if a.cmd == "new" else (Path(a.entry).resolve().parent if getattr(a, "entry", None) else
                                                                (film_dir(getattr(a, "film", None), required=False) or Path.cwd()))
        usage_log(f"{a.cmd}{'' if code == 0 else ' (failed)'}", place, time.monotonic() - t0)
        sys.stdout.flush()
        print(f"vd {a.cmd}: {time.monotonic() - t0:.1f} s", file=sys.stderr, flush=True)
        if code in (0, FAILS, 3) and MADE:    # FAILS: a sound made, checked and failing; 3: an export made and kept, whose scan could not run
            print(MADE[-1], flush=True)   # the last line is always the path of what the command made


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
