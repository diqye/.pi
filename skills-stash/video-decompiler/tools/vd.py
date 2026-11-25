#!/usr/bin/env python3
"""The front door: is this machine ready, and the film folder's commands.

  doctor [--full]                     is this machine ready, and how to fix it if not; --full renders and looks at a film
  new NAME --kind KIND                a film folder that starts from a working page film (explainer, launch, vertical, app)
  new NAME --like FILM                a copy of a whole worked film from library/films (`vd new --help` lists them)
  look, sound, render, export, scan, pack, measure, pin, profile   the film's commands (tools/lean.py; `vd COMMAND --help`)
  borrow, capture, launch, foley, evolve, playable, audio, bridge    newer commands, not proven on a film (SKILL.md)

Every command leaves one line in ~/.vd/usage.log. What a command renders goes to ~/.vd/out/NAME, outside the film, and reader
packs to ~/.vd/reads; `new`, `pin`, `borrow`, `capture`, `launch`, `foley`, `evolve`, `audio` and a film's own sound.py write in the film folder. Nothing is sent anywhere.
"""
import argparse
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SKILL = TOOLS.parent
sys.path.insert(0, str(TOOLS))

RAEA = "0.1.1-rc4"  # the raea this skill pins: raea_run.PIN refuses an older one at every render (tests/test_queue.py keeps the two equal)
FFMPEG = 6  # the oldest ffmpeg the tools run on: they pass -fps_mode, which 4.4 doesn't have
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
VENV = Path.home() / ".venvs" / "video-decompiler"


def cmdline(*parts, system=os.name):
    """One command a person can paste. In PowerShell a program given by its path needs the call operator and quotes
    (& 'C:\\...\\python.exe' -m pip ...): without them the line does not parse, and doctor's own repair lines did not.
    Elsewhere every part is quoted for sh, so a home folder with a space in it still works."""
    parts = [str(p) for p in parts]
    if system == "nt":
        quoted = lambda p: "'" + p.replace("'", "''") + "'"
        return "& " + " ".join(quoted(p) if i == 0 or re.search(r"[^A-Za-z0-9_.:\\/=+-]", p) else p for i, p in enumerate(parts))
    return " ".join(shlex.quote(p) for p in parts)


PIP = cmdline(sys.executable, "-m", "pip", "install", "-r", SKILL / "requirements.txt")


def raea_fix(system=os.name):
    """How to get raea: its own installer's line for this system, which puts it under ~/.raea, one of the places
    raea_run looks, so nothing has to be set afterwards. It names the executable this system has (raea_run.EXE; vd.py
    can't import it before psutil is in): a Mac was told to point RAEA_BIN at a raea.exe."""
    line = "in PowerShell, `irm https://raea.io/install.ps1 | iex`" if system == "nt" else "`curl -fsSL https://raea.io/install | sh`"
    return (f"install raea {RAEA} or newer with its own installer ({line}; it goes under ~/.raea, where this looks), "
            f"or set RAEA_BIN to a {'raea.exe' if system == 'nt' else 'raea executable'} you already have")


FIXES = {"python": "install Python 3.10 or newer and set up again with it (an environment keeps the Python it was made with: remove ~/.venvs/video-decompiler first if you made one)", "numpy": "packages", "cv2": "packages", "PIL": "packages", "psutil": "packages",
         "ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "raea": raea_fix()}


def packages_fix():
    """How to install the packages. Off Windows and outside a virtual environment, pip refuses to install into the
    system's Python ("externally-managed-environment"), so make one first."""
    if os.name == "nt" or sys.prefix != sys.base_prefix:
        return PIP
    python = VENV / "bin" / "python"
    return ("make a virtual environment, install into it, and run vd.py with its Python:\n    "
            f"{cmdline('python3', '-m', 'venv', VENV)}\n    {cmdline(python, '-m', 'pip', 'install', '-r', SKILL / 'requirements.txt')}\n    {cmdline(python, TOOLS / 'vd.py', 'doctor')}")


def ffmpeg_fix():
    how = "brew install ffmpeg" if sys.platform == "darwin" else "winget install ffmpeg, then open a new terminal" if os.name == "nt" else \
        "your distribution's ffmpeg package if it is 6 or newer, or a static build from https://ffmpeg.org/download.html"
    return f"install ffmpeg {FFMPEG} or newer, which brings ffprobe with it: {how}"


def ffmpeg_version():
    try:
        line = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW).stdout.split("\n", 1)[0].strip()
    except OSError:
        return None, ""
    m = re.match(r"ffmpeg version n?(\d+)\.\d", line)
    return (int(m.group(1)) if m else None), line


def ffmpeg_filters():
    """The names of the audio and video filters this ffmpeg was built with, or None when it can't say."""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30, creationflags=0x08000000 if os.name == "nt" else 0).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    # each filter is a line of flags, its name, its pads and what it does: " T.C afftdn  A->A  Denoise audio samples ..."
    return {m.group(1) for m in re.finditer(r"^\s*[TSC.|]{2,4}\s+(\w+)\s+\S+->\S+", out, re.M)} or None


def optional_tools():
    """What the commands that only some films use need, said as optional: the machine is ready without them."""
    import playable
    import voice_clean
    found = playable.find_esbuild() or playable.find_bun()
    print(f"  ok   bundler (optional): {found}, for vd playable" if found else
          "  --   bundler (optional, not here): only vd playable needs esbuild or bun, to build the film for a browser. "
          "To add it: install bun from https://bun.sh (raea's own installer may already have put esbuild in ~/.raea/bin)")
    have = ffmpeg_filters()
    lack = None if have is None else [f for f in voice_clean.FILTERS if f not in have]
    print("  ?    ffmpeg's audio filters for vd audio --clean-voice: couldn't read `ffmpeg -filters`" if lack is None else
          f"  ok   ffmpeg's audio filters for vd audio --clean-voice ({', '.join(voice_clean.FILTERS)})" if not lack else
          f"  --   ffmpeg's audio filters (optional): this ffmpeg lacks {', '.join(lack)}, which vd audio --clean-voice needs; "
          f"the other commands do not. A full build of ffmpeg has them: {ffmpeg_fix()}")


def doctor(a):
    import platform
    print(f"vd doctor on {platform.system()} {platform.release()} ({platform.machine()}); if anything below says MISS or FAILED, paste this whole report to whoever gave you the skill")
    version = sys.version_info[:2]
    print(f"python {version[0]}.{version[1]}" + ("  NEEDS 3.10 or newer" if version < (3, 10) else ""))
    missing = ["python"] if version < (3, 10) else []
    for mod in ("numpy", "cv2", "PIL", "psutil"):
        ok = importlib.util.find_spec(mod) is not None
        print(f"  {'ok  ' if ok else 'MISS'} {mod}")
        missing += [] if ok else [mod]
    for exe in ("ffmpeg", "ffprobe"):
        ok, said = shutil.which(exe) is not None, ""
        if ok and exe == "ffmpeg":
            major, line = ffmpeg_version()
            if major is not None and major < FFMPEG:
                ok, said = False, f" {major}: NEEDS {FFMPEG} or newer ({line})"
            else:
                said = f" {major}" if major is not None else f" (couldn't read its version from \"{line}\")"
        print(f"  {'ok  ' if ok else 'MISS'} {exe}{said}")
        missing += [] if ok else [exe]
    if importlib.util.find_spec("psutil") is None:  # raea_run needs it to look for raea
        print("  ?    raea: not checked until the packages are in")
    else:
        import raea_run
        try:
            raea = raea_run.checked_binary(say=False)
            print(f"  ok   raea {raea_run.binary_version(raea)} ({raea})")
        except SystemExit as e:
            print(f"  MISS raea: {e}")
            missing.append("raea")
    import lean  # its top imports only the standard library
    why = lean.transcriber()
    # optional: only reading a spoken film's words needs it, and a machine without it is still ready
    print("  ok   transcriber (optional): faster_whisper and its small model, for the words of a spoken film in vd measure and vd pin" if why is None else
          f"  --   transcriber (optional, not here: {why}): needed only for vd measure and vd pin to read the words of a film with a voice; "
          f"without it they say \"not transcribed\" and leave its word measures out. To add it:  {cmdline(sys.executable, '-m', 'pip', 'install', 'faster-whisper')}  "
          f"and then once, online:  {cmdline(sys.executable, '-c')} \"from faster_whisper import WhisperModel; WhisperModel('small')\"")
    if missing:
        how = {"packages": packages_fix(), "ffmpeg": ffmpeg_fix()}
        fixes = {}
        for m in missing:
            fixes.setdefault(how.get(FIXES[m], FIXES[m]), []).append(m)
        print("\nTo fix:")
        for fix, names in fixes.items():
            print(f"  {', '.join(names)}: {fix}")
        raise SystemExit(1)
    optional_tools()
    if not a.full:
        print(f"Ready. This also makes a film and looks at it:  {cmdline(sys.executable, TOOLS / 'vd.py', 'doctor', '--full')}")
        return
    import tempfile
    import lean
    with tempfile.TemporaryDirectory() as tmp:
        film = Path(tmp) / "doctor-starter"     # names of their own: the README's first film is called `first`
        lean.main(["new", str(film), "--kind", "explainer"])
        code = lean.main(["look", str(film / "main.tsx"), "--composition", "film", "--at", "0.5,3.5,6"])
        if code:
            raise SystemExit("FAILED: the test film didn't draw: see what look printed above")
        # the film a new film really starts from: its pictures, its faces of type and its sound script, on this machine
        worked = Path(tmp) / "doctor-plusone"
        here = os.getcwd()
        try:
            lean.main(["new", str(worked), "--like", "plusone"])
            os.chdir(worked)
            code = lean.main(["look", "--at", "2,14,31"])
        finally:
            os.chdir(here)
        if code or not (worked / "media" / "sound.wav").is_file():
            raise SystemExit("FAILED: the worked film (plusone) didn't draw or its sound script wrote no sound: see what was printed above")
    # a first run that ends on FAULT lines about an accepted film reads as a broken install
    print("The worked film's report above names texts cut by the frame's edge: its side cards and its guests leave the frame on purpose, "
          "and it was accepted that way. In a film of your own, answer every `!! FAULT` line.")
    print(f"Made a starter film and a copy of a worked film (plusone), built its sound and looked at both. Ready. The looks are in {lean.OUTROOT / 'doctor-starter'} and {lean.OUTROOT / 'doctor-plusone'}.")


def _run_lean(argv):
    import lean
    return lean.main(argv)


def main(argv=None):
    t0 = time.monotonic()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("doctor", "-h", "--help"):
        return _run_lean(argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", metavar="COMMAND")
    s = sub.add_parser("doctor", help="is this machine ready, and how to fix it if not")
    s.add_argument("--full", action="store_true", help="also make a film and look at it (one short render)")
    s.set_defaults(fn=doctor)
    for name, what in (("new", "a film folder that starts from a working film"), ("look", "many moments as one picture"), ("sound", "the sound with no picture"),
                       ("render", "render seconds A..B only"), ("export", "the finished film, scanned"), ("scan", "pops, holds and level of a finished film"),
                       ("pack", "a blind side-by-side pack for readers"), ("measure", "the gap table"), ("pin", "a reference's numbers into score.json"),
                       ("profile", "minutes by class for the session"), ("clean", "what can go from ~/.vd/out; --yes removes it"), ("borrow", "not proven: a reference's fitted moves and colours"),
                       ("capture", "not proven: a repository's counts or a command's output, as a plane"), ("launch", "not proven: a copy of stet with a repository's counts beside it"),
                       ("foley", "not proven: a sound track made by rule from the film's code"), ("evolve", "not proven: four world sketches as a blind line-up"),
                       ("playable", "not proven: a browser page that imitates the film"), ("audio", "not proven: clean a voice, measure a track, draw its sound"),
                       ("bridge", "not proven: the export's cuts for an editor or legible-film")):
        p = sub.add_parser(name, help=what + " (vd " + name + " --help)", add_help=False)
        p.set_defaults(fn=lambda _a, _argv=argv: _run_lean(_argv))
    if not argv:
        ap.print_help()
        return 0
    code = 1
    try:
        a = ap.parse_args(argv)
        fn = getattr(a, "fn", None)
        if fn is None:
            ap.print_help()
            code = 0
            return 0
        r = fn(a)
        code = r if isinstance(r, int) else 0
        return code
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        raise
    finally:
        try:
            import lean
            lean.usage_log(f"{argv[0] if argv else '-'}{'' if code == 0 else ' (failed)'}", Path.cwd(), time.monotonic() - t0)
        except Exception:  # on a bare Python lean's imports are all standard, but never let the log break doctor
            pass


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
