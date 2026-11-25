#!/usr/bin/env python3
"""`vd capture` and `vd launch` (not proven on a film): a repository's counts, read by file and name patterns, or a
command's real output lines and times (run with no shell), into kit/puppet.gen.ts, with kit/PuppetPlane.tsx to show them.

  python puppet.py capture [--cmd "pytest -q"] [--repo DIR] [--film DIR]
  python puppet.py launch [REPO_DIR] [--out FILM_DIR] [--cmd "..."]

What it does: `vd capture` counts a repository's files, functions, tests and commits by file and name patterns (check
them before they go on screen), or runs a command with no shell, stopped at its timeout, and records its output lines
with their times; both go into `kit/puppet.gen.ts`, shown by `kit/PuppetPlane.tsx`, which the film must import itself.
With no command, the record says nothing ran (`ran: false`). `vd launch` copies a worked film, captures into it and
writes the counts to REPO-FACTS.md; it does not put them in the film.
"""
import argparse
import ast
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def windows_argv(line):
    """Split a command line as Windows' CommandLineToArgvW does, the split every Windows program applies to its own."""
    import ctypes
    from ctypes import wintypes
    f = ctypes.windll.shell32.CommandLineToArgvW
    f.argtypes, f.restype = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)], ctypes.POINTER(wintypes.LPWSTR)
    n = ctypes.c_int()
    p = f(line, ctypes.byref(n))
    try:
        return [p[i] for i in range(n.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(p)


def command_argv(cmd):
    """The program and its arguments, split as a shell would split words but run by no shell: `;`, `|`, `&&` and `$(...)`
    reach the program as plain words. The program is looked up on PATH, so `npm` finds `npm.cmd` on Windows."""
    if isinstance(cmd, (list, tuple)):
        argv = [str(x) for x in cmd]
    elif not cmd.strip():  # Windows' splitter would read an empty line as the running program itself
        argv = []
    elif os.name == "nt":  # Windows' own rules: posix ones eat a path's backslashes, and quotes can open mid-word
        argv = windows_argv(cmd.strip())  # stripped: a leading space would make the program's name empty
    else:
        argv = shlex.split(cmd)
    if not argv:
        raise SystemExit("vd capture: --cmd is empty")
    found = shutil.which(argv[0])
    if not found:
        raise SystemExit(f"vd capture: no program called {argv[0]!r} on PATH. The command runs without a shell, so name a "
                         f"program, not a shell line; for pipes or `&&`, put them in a script and name the script.")
    if os.name == "nt" and Path(found).suffix.lower() in (".cmd", ".bat"):
        # Windows runs a batch file through cmd.exe whatever Popen is told, and cmd.exe reads & | < > ^ % ! ( ) and quotes
        # in its arguments as its own: `tool.cmd SAFE & echo INJECTED` ran the second command. A batch file is run only
        # when none of its arguments holds one of those (npm test, npx tsc --noEmit still run).
        bad = [x for x in argv[1:] if any(c in x for c in '&|<>^%!()"\n\r')]
        # its own path too, for the characters cmd.exe acts on in a name (tool&echo.x&.cmd ran echo); parentheses in a
        # path such as Program Files (x86) are quoted with its space and harmless
        bad += [found] if any(c in found for c in '&|<>^%!') else []
        if bad:
            raise SystemExit(f"vd capture: {Path(found).name} is a batch file, which Windows runs through cmd.exe, and the argument(s) "
                             f"{', '.join(repr(x) for x in bad)} hold characters cmd.exe would run as commands. Name a program, or "
                             "put the line in a script and name the script with no such arguments.")
    return [found] + argv[1:]


def capture_command(cmd, cwd: Path, timeout: float = 30.0):
    """Run `cmd` (a string split into words, or a list) in `cwd` with no shell, recording each output line with its time in
    seconds from the start. A command still running at `timeout` seconds is stopped whether or not it is printing, and the
    record says so (`timed_out`), so a silent hang cannot stall the capture."""
    argv = command_argv(cmd)
    t0 = time.monotonic()
    p = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=NO_WINDOW,
    )
    got = queue.Queue()

    def read():  # a thread reads, so the deadline below holds even while the command prints nothing
        for raw in p.stdout:
            got.put((round(time.monotonic() - t0, 4), raw))
        got.put(None)

    threading.Thread(target=read, daemon=True).start()
    lines, timed_out, deadline = [], False, t0 + timeout
    while True:
        try:
            item = got.get(timeout=max(0.0, deadline - time.monotonic()))
        except queue.Empty:
            timed_out = True
            p.kill()
            break
        if item is None:
            break
        dt, raw = item
        clean = strip_ansi(raw.rstrip("\r\n"))
        if clean.strip():   # whole: the plane clips a long line itself, and a cut at 120 characters lost git's verdict's end
            lines.append({"t": dt, "text": clean})
    try:  # the output can close before the command ends: the same deadline holds until it exits
        p.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        p.kill()
        p.wait()
    return {
        "command": cmd if isinstance(cmd, str) else subprocess.list2cmdline(argv),
        "ran": True,
        "exit_code": p.returncode,
        "timed_out": timed_out,
        "duration_s": round(time.monotonic() - t0, 4),
        "lines": lines,   # every line: the first 24 were kept, silently, and a bisect's verdict (line 33) was lost
    }


def n(count, word):
    """'1 test', '2 tests': a count on screen says its noun as English does ("1 source files" did not)."""
    return f"{count} {word}{'' if count == 1 else 's'}"


def counts_record(repo_data):
    """What the terminal plane shows when no command was given: the repository's counts, said as counts. Nothing ran,
    so there is no command, exit code or timing to show, and the record says so (`ran: false`)."""
    return {
        "command": None,
        "ran": False,
        "exit_code": None,
        "timed_out": False,
        "duration_s": None,
        "lines": [
            {"t": None, "text": f"{n(repo_data['total_code_files'], 'source file')} ({n(repo_data['lines_of_code'], 'line')})"},
            {"t": None, "text": f"{n(repo_data['functions'], 'function')}, {n(repo_data['tests'], 'test')}"},
            {"t": None, "text": f"{n(repo_data['commits'], 'commit')} in git history"},
        ],
    }


def analyze_codebase(repo_dir: Path):
    """Extract verified AST & git facts from `repo_dir`: functions, classes, files, tests, commits, and real lines."""
    import borrow
    base = borrow.inspect_repo(repo_dir)
    repo_dir = Path(repo_dir).resolve()
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    py_funcs, py_classes, test_count, total_lines = 0, 0, 0, 0
    top_modules = []

    for p in sorted(repo_dir.rglob("*")):
        if not p.is_file() or (skip & set(p.parts)):
            continue
        if p.suffix in (".py", ".ts", ".tsx", ".js", ".rs", ".go"):
            try:
                src = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            n_lines = len(src.splitlines())
            total_lines += n_lines
            top_modules.append((n_lines, p.relative_to(repo_dir).as_posix()))
            if p.suffix == ".py":
                try:
                    tree = ast.parse(src)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            py_funcs += 1
                            if node.name.startswith("test_"):
                                test_count += 1
                        elif isinstance(node, ast.ClassDef):
                            py_classes += 1
                except SyntaxError:
                    pass
            elif p.suffix in (".ts", ".tsx", ".js"):
                py_funcs += len(re.findall(r"\b(?:export\s+)?function\s+\w+", src))
                test_count += len(re.findall(r"\b(?:test|it)\s*\(", src))

    top_modules.sort(reverse=True)
    recent_commits = []
    try:
        p = subprocess.run(
            ["git", "-C", str(repo_dir), "log", "-5", "--format=%h %s"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, creationflags=NO_WINDOW
        )
        if p.returncode == 0:
            recent_commits = [l.strip()[:80] for l in p.stdout.splitlines() if l.strip()]
    except Exception:
        pass

    return {
        **base,
        "functions": py_funcs,
        "classes": py_classes,
        "tests": test_count,
        "lines_of_code": total_lines,
        "top_files": [{"file": f, "lines": n} for n, f in top_modules[:6]],
        "recent_commits": recent_commits,
    }


PUPPET_COMPONENT_TSX = """// generated by `vd capture`: live codebase & terminal puppet on a 3D projective plane
import { INTER_600, INTER_700, JETBRAINS_MONO } from "./lib/faces";
import { Cam, head, lie, planeCss, stand } from "./lib/scene";
import { PUPPET_CUE_SEC, PUPPET_DATA, PUPPET_TERMINAL } from "./puppet.gen";

export const PUPPET_FONTS = `
@font-face { font-family: "PuppetSans"; font-weight: 600; src: url("${INTER_600}") format("woff2"); }
@font-face { font-family: "PuppetSans"; font-weight: 700; src: url("${INTER_700}") format("woff2"); }
@font-face { font-family: "PuppetMono"; font-weight: 400; src: url("${JETBRAINS_MONO}") format("woff2"); }
`;

export function PuppetTerminal({
  frame,
  fps = 60,
  startFrame,
  cam,
  x = 260,
  y = 170,
  z = 24,
  tilt = 0,
}: {
  frame: number;
  fps?: number;
  startFrame?: number;
  cam?: Cam;
  x?: number;
  y?: number;
  z?: number;
  tilt?: number;
}) {
  const c = cam ?? head(1920, 1080);
  const m = tilt ? stand(x + 700, y + 370, z, [700, 370], 0, 90 - tilt) : lie(x, y, z);
  const f0 = startFrame ?? Math.round(PUPPET_CUE_SEC * fps);
  const elapsed = Math.max(0, (frame - f0) / fps);
  // a record of counts (ran: false) has no command and no times: it is headed as counts, its lines a beat apart
  const said = PUPPET_TERMINAL.ran ? "$ " + PUPPET_TERMINAL.command : "counted from the repository";
  const lines = PUPPET_TERMINAL.lines.filter((row, i) => elapsed >= (row.t ?? 0.4 * (i + 1)));
  const cmdChars = Math.min(said.length, Math.floor(elapsed * 32));
  // its faces mounted with it: named and never loaded, raea fell back to a system face without a word (TRAPS.md)
  return (
    <>
    <style>{PUPPET_FONTS}</style>
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: 1400,
        height: 740,
        transformOrigin: "0 0",
        transform: planeCss(c, m),
        background: "#121418",
        borderRadius: 22,
        border: "2px solid #2b303c",
        boxShadow: "0 42px 96px rgba(0, 0, 0, 0.45)",
        padding: "36px 44px",
        fontFamily: "PuppetMono, monospace",
        color: "#eef2f6",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
        <div style={{ width: 14, height: 14, borderRadius: 7, background: "#e05246" }} />
        <div style={{ width: 14, height: 14, borderRadius: 7, background: "#e5a93c" }} />
        <div style={{ width: 14, height: 14, borderRadius: 7, background: "#3fb950" }} />
        <div style={{ marginLeft: 18, fontSize: 30, color: "#8b949e" }}>{PUPPET_DATA.name}</div>
      </div>
      <div style={{ fontSize: 36, lineHeight: "52px", color: "#58a6ff", marginBottom: 20 }}>
        {said.slice(0, cmdChars)}
      </div>
      {/* the latest eight lines to have appeared, as a terminal scrolls: the first eight never showed a command's verdict */}
      {lines.slice(-8).map((row, i) => (
        <div key={i} style={{ fontSize: 32, lineHeight: "46px", color: "#d2dce6", whiteSpace: "pre" }}>
          {row.text}
        </div>
      ))}
    </div>
    </>
  );
}
"""


def _resolve_cue_sec(film_dir: Path, cue_name: str) -> float:
    if not cue_name:
        return 0.0
    import lean
    gen = lean.gen_data(film_dir)
    for cname, csec in gen.get("CUES") or []:
        if str(cname).lower() == cue_name.lower() or cue_name.lower() in str(cname).lower():
            return round(float(csec), 4)
    times = gen.get("TIMES") or {}
    clock = gen.get("CLOCK") or {}
    beat_sec = float(clock.get("FB") or 32.0) / float(clock.get("FPS") or 60.0)
    if cue_name.upper() in times and isinstance(times[cue_name.upper()], (int, float)):
        return round(float(times[cue_name.upper()]) * beat_sec, 4)
    return 0.0


def write_puppet_files(film_dir: Path, repo_data: dict, term_data: dict, cue: str = "hit"):
    """Write `kit/puppet.gen.ts` and `kit/PuppetPlane.tsx` into `film_dir`."""
    kit = film_dir / "kit"
    kit.mkdir(parents=True, exist_ok=True)
    # Ensure kit/lib/faces.ts and kit/lib/scene.tsx and kit/lib/core.ts exist so imports resolve
    import lean
    for name, src in lean.PAGE_KIT.items():
        dst = kit / name
        if not dst.exists():
            lean.copy_any(src, dst)
    lean.prune_unresolved(kit)
    cue_sec = _resolve_cue_sec(film_dir, cue)
    gen_ts = (
        "// generated by `vd capture`: a repository's counts, read by file and name patterns, and a command's output if one ran\n"
        f"export const PUPPET_CUE = {json.dumps(cue or 'hit')} as const;\n"
        f"export const PUPPET_CUE_SEC = {cue_sec};\n"
        f"export const PUPPET_DATA = {json.dumps(repo_data, indent=2)} as const;\n"
        f"export const PUPPET_TERMINAL = {json.dumps(term_data, indent=2)} as const;\n"
    )
    (kit / "puppet.gen.ts").write_text(gen_ts, encoding="utf-8", newline="\n")
    (kit / "PuppetPlane.tsx").write_text(PUPPET_COMPONENT_TSX, encoding="utf-8", newline="\n")
    return kit / "puppet.gen.ts", kit / "PuppetPlane.tsx"


def cmd_capture(a):
    import lean
    d = lean.film_dir(a.film, required=False) or Path.cwd().resolve()
    repo_dir = Path(a.repo).resolve() if a.repo else d
    repo_data = analyze_codebase(repo_dir)
    if a.cmd:
        term_data = capture_command(a.cmd, repo_dir, timeout=a.timeout)
    else:
        term_data = counts_record(repo_data)
    gen_path, comp_path = write_puppet_files(d, repo_data, term_data, cue=getattr(a, "cue", "hit") or "hit")
    print(f"captured {repo_data['name']}: {repo_data['total_code_files']} files, {repo_data['functions']} functions, "
          f"{repo_data['tests']} tests, {len(term_data['lines'])} terminal lines")
    print(f"wrote {gen_path} and {comp_path}")
    print(gen_path)
    return 0


LAUNCH_SHOW_S = 4.0     # how long the plane holds the screen, from its cue


def mount_puppet(film_dir: Path):
    """Put the plane in the film's own composition (film.tsx): imported, and drawn on the film's own paper for LAUNCH_SHOW_S
    from its cue, under the grain. True when mounted; False when film.tsx has no place this knows (then nothing changes).
    Before this, launch wrote the plane and its facts and nothing imported them: the film was the worked film unchanged."""
    f = film_dir / "film.tsx"
    if not f.is_file():
        return False
    s = f.read_text(encoding="utf-8")
    if "PuppetTerminal" in s:
        return True
    under = "      {finish ? grain(f, W, H) : null}"
    after = 'import { act6 } from "./act6";'
    if s.count(under) != 1 or s.count(after) != 1:
        return False
    s = s.replace(after, after + '\nimport { PuppetTerminal } from "./kit/PuppetPlane";\nimport { PUPPET_CUE_SEC } from "./kit/puppet.gen";', 1)
    s = s.replace(under, "      {f >= PUPPET_CUE_SEC * FPS && f < (PUPPET_CUE_SEC + " + str(LAUNCH_SHOW_S)
                  + ") * FPS ? <><div style={{ position: \"absolute\", left: 0, top: 0, width: W, height: H, background: C.paper }} />"
                  + "<PuppetTerminal frame={f} fps={FPS} /></> : null}\n" + under, 1)
    f.write_text(s, encoding="utf-8", newline="\n")
    return True


def build_launch_film(repo_dir: Path, out_dir: Path = None, cmd: str = None, like: str = "stet"):
    """Copy a worked film into `out_dir` (stet unless `like`), capture `repo_dir` into it, write its counts to
    REPO-FACTS.md, and mount the plane in the film from its NUMBERS cue (Stet's proof) for LAUNCH_SHOW_S."""
    import lean
    repo_dir = Path(repo_dir).resolve()
    repo_data = analyze_codebase(repo_dir)
    if out_dir is None:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", repo_data["name"].lower()).strip("-") or "launch"
        out_dir = Path.cwd().resolve() / f"{slug}-film"
    out_dir = Path(out_dir).resolve()
    chosen_like = like or "stet"
    if not (out_dir / "score.json").is_file():
        class NewArgs:
            name = str(out_dir)
            like = chosen_like
            kind = None
            bare = False
        lean.cmd_new(NewArgs())

    term_data = capture_command(cmd, repo_dir) if cmd else counts_record(repo_data)
    write_puppet_files(out_dir, repo_data, term_data, cue="NUMBERS")
    mounted = mount_puppet(out_dir)

    # The repository's facts go beside the board for it to use; the board is the agent's to write (SKILL.md step 3),
    # and a folder launched into may already hold one.
    board_lines = [
        f"# Facts read from {repo_data['name']}, for BOARD.md",
        "",
        f"- **Product:** {repo_data['name']} — {repo_data['tagline']}",
        f"- **Counts read from the code (by file and name patterns; check each before it goes on screen):** {repo_data['total_code_files']} code files, {repo_data['functions']} functions, {repo_data['tests']} tests, {repo_data['lines_of_code']} lines of code.",
        "- **World:** Live terminal and architecture cards on a projective plane (`kit/PuppetPlane.tsx`), driven on one clock from `sound.py`.",
        "- **Hardest shot:** The live terminal trace projecting in 3D space as every test/module count locks on beat.",
    ]
    board_lines.append("- **On screen:** " + ("the plane, from the NUMBERS cue for " + str(LAUNCH_SHOW_S) + " s (film.tsx)" if mounted else
                       "not yet: film.tsx has no place launch knows; import kit/PuppetPlane.tsx where the board puts it") + ".")
    (out_dir / "REPO-FACTS.md").write_text("\n".join(board_lines) + "\n", encoding="utf-8")
    return out_dir, repo_data


def cmd_launch(a):
    out_dir, repo_data = build_launch_film(
        Path(a.repo or "."),
        out_dir=Path(a.out) if a.out else None,
        cmd=a.cmd,
    )
    print(f"launched film folder {out_dir} for {repo_data['name']} ({repo_data['total_code_files']} files, {repo_data['functions']} functions, {repo_data['tests']} tests)")
    print(out_dir)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="subcmd", required=True)
    c = sub.add_parser("capture", help="not proven: a repository's counts or a command's output, into kit/puppet.gen.ts")
    c.add_argument("--cmd", help="command to run and record with millisecond timestamps")
    c.add_argument("--repo", help="repository folder to inspect (default: current directory)")
    c.add_argument("--film", help="film folder to write kit/puppet.gen.ts into")
    c.add_argument("--timeout", type=float, default=30.0)
    c.set_defaults(fn=cmd_capture)

    l = sub.add_parser("launch", help="not proven: a copy of stet with a repository's counts captured beside it")
    l.add_argument("repo", nargs="?", default=".", help="repository folder (default: .)")
    l.add_argument("--out", help="destination film folder")
    l.add_argument("--cmd", help="optional CLI command to capture live for the terminal plane")
    l.set_defaults(fn=cmd_launch)

    a = ap.parse_args(argv)
    sys.exit(a.fn(a))


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
