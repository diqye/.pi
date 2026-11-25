"""Run a heavy job (a compile, a model, a long encode) in the machine's one render queue, as a scheduled job.

  python heavy.py --when-idle 300 -- cargo build --release -p raea-cli
  python heavy.py --now -- python train.py
  python heavy.py -- ffmpeg -i frames/%05d.png film.mp4      (an encode: takes its turn at once, like a render)

A compile is scheduled, never dropped in. It waits until the queue is free and no render has held it or waited for it
for --when-idle seconds (default 120). It refuses to start at all while a file named FILMS-RUNNING lies beside the
queue's lock (~/.raea/FILMS-RUNNING), which says films are being made, unless --now is given. Once it starts it holds the
queue until it ends, and every render that arrives meanwhile waits and says what holds it. Two renders at once have
crashed this laptop, a compile beside a render stalls it, and one night a compile held the queue 45 minutes in front of
the films.

An encode is not a compile: it is the last minute of making a film, so ffmpeg and ffprobe always get --now. The same
night, with six films rendering, the queue was never idle for 120 s, and two makers' encodes sat unstarted for 20 minutes
each behind a rule written for compiles.

A heavy job neither waits nor holds for nothing. Its first line says at once what it waits for. It gives up waiting
after --give-up seconds (default 30 minutes), and at once if the process that started it has gone. (One case it may
not see on Linux and macOS: a starter that had gone before this process began. The system hands the waiter to init,
which looks like a starter that is still there, so that waiter leaves when --give-up runs out.) With --stall N, a
job known to be CPU-bound (an x264 encode) that uses under 1 % of a core for N seconds while holding the queue is
ended, the queue let go, and heavy.py exits 3 saying why; it is off by default, because a model loading from disk or
work on the graphics card uses little CPU and is not stalled. The queue is re-entrant for a holder's children
(raea_run.held_above), so the deadlock below cannot recur without the watch. One night a measure started at 00:19 was thought stopped, lived on waiting, took the
idle queue at 03:28, and its child waited an hour for the lock its own parent held, every film behind it.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

import raea_run

STALLED = 3


def span(s):
    return f"{s / 60:.0f} min" if s >= 120 else f"{s:.0f} s"


def started_by():
    """A test for 'the process that started this one has gone' (its pid gone, or reused by a newer process)."""
    try:
        me = psutil.Process()
        parent = me.parent()
        # a venv's python.exe on Windows is a launcher that starts the real Python as its child with the same arguments,
        # and lives as long as it does: the starter is the first ancestor that is not such a launcher
        while parent is not None and parent.cmdline()[1:] == me.cmdline()[1:]:
            me, parent = parent, parent.parent()
        if parent is None:
            return lambda: True
        born = parent.create_time()
    except psutil.Error:
        return lambda: True

    def gone():
        try:
            # a starter that has ended and not yet been collected by its own parent (a zombie, on Linux and macOS) still
            # has its number and its start time: it has gone all the same
            return not parent.is_running() or parent.create_time() != born or parent.status() == psutil.STATUS_ZOMBIE
        except psutil.Error:
            return True
    return gone


def cpu_by_pid(proc):
    """{pid: CPU seconds} of the job and its living descendants."""
    out = {}
    try:
        p = psutil.Process(proc.pid)
        for q in [p] + p.children(recursive=True):
            try:
                out[q.pid] = sum(q.cpu_times()[:2])
            except psutil.Error:
                pass
    except psutil.Error:
        pass
    return out


def accumulate(last, now):
    """(CPU seconds used since `last`, the readings to keep): only each process's own increase counts, and a process that
    has gone adds nothing. A total over the living descendants falls when a busy worker exits, and that fall once read
    as the next stage doing nothing (a review's finding)."""
    return sum(max(0.0, c - last.get(p, 0.0)) for p, c in now.items()), dict(now)


def watch(proc, idle, step=1.0):
    """Wait for the job; with `idle` (--stall), end it when it has used under 1 % of a core for that many seconds. (code, why)."""
    marks, last, used = [], {}, 0.0
    while proc.poll() is None:
        time.sleep(step)
        if proc.poll() is not None or not idle:
            continue
        add, last = accumulate(last, cpu_by_pid(proc))
        used += add
        now = time.monotonic()
        c = used
        marks.append((now, c))
        while len(marks) > 1 and now - marks[1][0] >= idle:
            marks.pop(0)
        if now - marks[0][0] >= idle and marks[-1][1] - marks[0][1] < 0.01 * idle:
            raea_run.kill_tree(proc)
            return STALLED, f"under 1 % of a core for {idle:.0f} s while holding the queue"
    return proc.returncode, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--when-idle", type=float, default=120.0, metavar="N", help="start only after no render has held or waited for the queue for N seconds (default 120)")
    ap.add_argument("--now", action="store_true", help="start even while FILMS-RUNNING exists, as soon as the queue is free")
    ap.add_argument("--give-up", type=float, default=1800.0, metavar="N", help="stop waiting for the queue after N seconds (default 1800)")
    ap.add_argument("--stall", type=float, default=0.0, metavar="N",
                    help="for a job known to be CPU-bound: end it if it uses under 1 %% of a core for N seconds while holding the queue (default: off)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- COMMAND [ARGS...]")
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        sys.exit("usage: python heavy.py [--when-idle N] [--now] -- COMMAND [ARGS...]")
    if Path(cmd[0]).stem.lower() in ("ffmpeg", "ffprobe"):
        a.now = True                                        # an encode takes its turn like a render; only compiles and models are scheduled
    raea_run.QUEUE.mkdir(exist_ok=True)
    lock = raea_run.QUEUE / "raea_run.lock"
    films = raea_run.QUEUE / "FILMS-RUNNING"
    if films.exists() and not a.now:
        sys.exit(f"heavy.py: not started. {films} says films are being made, and a heavy job would hold the render queue "
                 "in front of them. Run it when that file is gone, or give --now.")
    what = " ".join(cmd)
    gone = started_by()
    print(f"heavy.py: waiting for the render queue{'' if a.now else f' to be free of renders for {a.when_idle:.0f} s'}, then runs: "
          f"{what[:200]} (gives up after {span(a.give_up)})", flush=True)
    t0, said = time.monotonic(), None
    while not a.now:
        idle = time.time() - raea_run.last_render(lock)
        if idle >= a.when_idle:
            break
        waited = time.monotonic() - t0
        if waited > a.give_up:
            print(f"heavy.py: gave up after {span(waited)} waiting for an idle queue; {what[:200]} did not run", flush=True)
            return 2
        if gone():
            print(f"heavy.py: the process that started this one has gone, so {what[:200]} will not run", flush=True)
            return 2
        if said is None or waited - said >= 30:
            print(f"heavy.py: scheduled; the queue last had a render {idle:.0f} s ago, and this starts after {a.when_idle:.0f} s "
                  f"without one (waited {waited:.0f} s)", file=sys.stderr, flush=True)
            said = waited
        time.sleep(2.0)
    try:
        held = raea_run.one_at_a_time(wait=max(1.0, a.give_up - (time.monotonic() - t0)), lock=lock, what=what, kind="heavy", gone=gone)
    except SystemExit as e:
        print(f"heavy.py: {e}; {what[:200]} did not run", flush=True)
        return 2
    try:
        # off Windows nothing ends the job when this wrapper is killed by force, so the job holds the queue's lock too, as
        # raea_run's renders do: the queue stays shut while an orphaned job is still at work (on Windows die_with_us ends it)
        keep = {"pass_fds": (held.fileno(),)} if held is not None and os.name != "nt" else {}
        proc = subprocess.Popen(cmd, **keep)
        job = raea_run.die_with_us(proc)  # noqa: F841  the job ends if heavy.py is stopped
        code, why = watch(proc, a.stall)
        if why:
            print(f"heavy.py: stalled: {what[:200]} used {why}; ended it and let the queue go", flush=True)
        return code
    finally:
        if held is not None:
            held.close()


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
