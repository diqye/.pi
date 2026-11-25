#!/usr/bin/env python3
"""`vd borrow` (not proven on a film): a reference's moves fitted to springs and curves, and its held colours,
into dna.json, kit/dna.gen.ts and a REFERENCE.md to finish by TAKE-APART.md.

  python borrow.py REF.mp4 [--for REPO_DIR] [--out FILM_DIR]

What it does: measures the reference (vd pin's measure), fits each move's speed profile to physics.ts's spring
(frequency, damping) and a cubic curve, and takes its colours: every ground (a full-frame colour held 0.5 s or more,
read over the whole film four times a second, with its seconds and stretches), the accents set on them, and its holds'
swatches, near-identical colours merged. Which worked film it is like is chosen with
--like, never guessed. A move with no usable profile, a poor fit or a fit on the grid's edge is marked unfitted
(`fitted: false`), never a perfect fit. The film's spring and curve (DNA_SPRING, DNA_BEZIER) are the medians of the
moves that fit a spring with a readable speed; with none they are null and borrow says no move was fitted, never a
stand-in. It pins no targets: vd measure reads vd pin's numbers.
Known answer: tests/test_new_check_faults.py plants springs on moves of 0.2 to 1.2 s and recovers them within 0.15 Hz
and 0.06 damping, and calls an inOutCubic glide unfitted.
"""
import argparse
import functools
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))


FREQS = np.round(np.arange(0.5, 8.0001, 0.05), 2)     # Hz: physics.ts springs in the worked films run 1.5 to 5
DAMPS = np.round(np.linspace(0.20, 1.15, 20), 2)
FIT_MSE = 0.02    # above this the move is not a spring of this family (an inOutCubic glide fits damp 0.2 at 0.198)
GROUND_STEP = 0.25   # seconds between the samples a film's grounds and accents are read from
GROUND_HELD = 0.5    # seconds a full-frame colour must hold to be a ground: a shorter one is a flash or a card passing
GROUND_COVER = 0.3   # share of the frame within 40 levels of the border's commonest colour for that colour to be the frame's ground
NEAR = 8             # CIELAB distance (delta E) under which two colours are one: il's six off-white swatches lay within 3.1
                     # of each other and HEX's creams within 5.2, while its red accent is 13 from its orange ground, which an
                     # RGB distance of 40 called one colour (34 apart)
ACCENT_CHROMA = 80   # a pixel's max - min channel at least this for it to count toward an accent
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@functools.lru_cache(maxsize=64)
def spring_velocity_curves(dur):
    """Normalised speed profiles (measure.POINTS long) of physics.ts's spring(t, {freq, damp}) over a move lasting `dur`
    seconds, for every (freq, damp) on the grid. The grid is in real hertz at the move's own length: one made in
    move-relative units and divided by the length afterwards could not reach 2.2 Hz on a 0.2 s move (it read 5.0)."""
    import measure
    t = np.linspace(0.0, float(dur), measure.POINTS + 1)
    grid, curves = [], []
    for freq in FREQS:
        w = 2.0 * math.pi * float(freq)
        for damp in DAMPS:
            damp = float(damp)
            if damp < 1.0:
                wd = w * math.sqrt(1.0 - damp * damp)
                y = 1.0 - np.exp(-damp * w * t) * (np.cos(wd * t) + (damp * w / wd) * np.sin(wd * t))
            elif damp == 1.0:
                y = 1.0 - np.exp(-w * t) * (1.0 + w * t)
            else:
                r = math.sqrt(damp * damp - 1.0)
                a, b = -w * (damp - r), -w * (damp + r)
                c2 = a / (b - a)
                c1 = -1.0 - c2
                y = 1.0 + c1 * np.exp(a * t) + c2 * np.exp(b * t)
            v = np.abs(np.diff(y))
            curves.append(v / max(float(v.max()), 1e-9))
            grid.append((float(freq), damp))
    return tuple(grid), np.asarray(curves, dtype=np.float32)


def fit_spring_profile(profile, dur=0.5):
    """Fit a move's normalised speed profile to physics.ts's spring(t, {freq, damp}) over its `dur` seconds.
    Returns {'freq', 'damp', 'mse', 'fitted'}. `fitted` is False, with physics.ts's default spring, when there is no
    usable profile; and False beside the nearest spring when the fit is poor (mse over FIT_MSE) or lands on the edge of
    the grid, since then no spring of this family was found, only the closest it could reach."""
    import measure
    p = np.asarray(profile, dtype=np.float32)
    if len(p) != measure.POINTS or float(p.max(initial=0.0)) <= 0 or not dur or float(dur) <= 0:
        return {"freq": 2.2, "damp": 0.45, "mse": None, "fitted": False}
    grid, curves = spring_velocity_curves(round(float(dur), 3))
    p = p / float(p.max())
    errs = ((curves - p[None, :]) ** 2).mean(axis=1)
    idx = int(np.argmin(errs))
    freq, damp = grid[idx]
    mse = float(errs[idx])
    edge = freq in (float(FREQS[0]), float(FREQS[-1])) or damp in (float(DAMPS[0]), float(DAMPS[-1]))
    return {"freq": round(freq, 2), "damp": round(damp, 2), "mse": round(mse, 4), "fitted": bool(mse <= FIT_MSE and not edge)}


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) != 6:
        return (20, 20, 20)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_luma(rgb):
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgb_sat(rgb):
    mx, mn = max(rgb) / 255.0, min(rgb) / 255.0
    return 0.0 if mx <= 1e-6 else (mx - mn) / mx


def to_hex(c):
    return "#%02x%02x%02x" % tuple(int(round(float(v))) for v in c)


def lab(rgb):
    """CIELAB of RGB colours (0-255, any shape ending in 3): distances in it follow what an eye tells apart."""
    import cv2
    a = np.asarray(rgb, np.float32)
    return cv2.cvtColor(a.reshape(-1, 1, 3) / 255.0, cv2.COLOR_RGB2Lab).reshape(a.shape)


def apart(a, b):
    """How far apart two colours (RGB triples or hex) look: delta E in CIELAB."""
    a, b = (hex_to_rgb(x) if isinstance(x, str) else x for x in (a, b))
    return float(np.linalg.norm(lab(a) - lab(b)))


def merge_near(items):
    """(colour, weight, notes) merged into the heavier of any two within NEAR of each other: the weighted mean colour,
    the summed weight and both notes; heaviest first."""
    out = []
    for c, w, notes in sorted(items, key=lambda x: -x[1]):
        c = np.asarray(c, float)
        g = next((g for g in out if apart(g["c"], c) < NEAR), None)
        if g is None:
            out.append({"c": c, "w": float(w), "notes": list(notes)})
        else:
            g["c"] = (g["c"] * g["w"] + c * w) / max(g["w"] + w, 1e-9)
            g["w"] += float(w)
            g["notes"] += list(notes)
    return sorted(out, key=lambda g: -g["w"])


def film_colours(path, duration=None):
    """The film's grounds and accents, read from the whole film four times a second (each sample the frame on screen at
    its time), not from its holds alone: HEX rests 1.5 s of its 35, and its holds showed two of its seven grounds.
    A ground is a full-frame colour (the border's commonest, covering GROUND_COVER of the frame) held GROUND_HELD or
    longer; each distinct one is kept with its seconds on screen and its stretches, near-identical ones merged. An accent
    is a strongly coloured thing on a ground: weighed by its share of the screen over time, and never a ground."""
    import measure
    w, h = 160, 90
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={1 / GROUND_STEP:g}:round=up,scale={w}:{h}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, creationflags=NO_WINDOW).stdout
    frames = np.frombuffer(raw[:len(raw) - len(raw) % (w * h * 3)], np.uint8).reshape(-1, h, w, 3)
    end = float(duration) if duration else len(frames) * GROUND_STEP
    runs, hot = [], {}
    for k, rgb in enumerate(frames.astype(int)):
        g = measure.background(rgb)
        if float(np.mean(np.abs(rgb - g).max(axis=2) <= 40)) >= GROUND_COVER:
            if runs and runs[-1][1] == k and apart(np.mean(runs[-1][2], axis=0), g) < NEAR:
                runs[-1][1] = k + 1
                runs[-1][2].append(g)
            else:
                runs.append([k, k + 1, [g]])
        px = rgb.reshape(-1, 3)
        off = np.linalg.norm(lab(px) - lab(g), axis=1) >= NEAR
        sel = px[(px.max(axis=1) - px.min(axis=1) >= ACCENT_CHROMA) & off]
        keys = (sel // 32) @ np.array([64, 8, 1])
        for key in np.unique(keys):
            mine = sel[keys == key]
            got = hot.setdefault(int(key), [0, np.zeros(3), k * GROUND_STEP])
            got[0] += len(mine)
            got[1] += mine.sum(axis=0)
    held = [(np.mean(cols, axis=0), (b - a) * GROUND_STEP, [[round(a * GROUND_STEP, 2), round(min(b * GROUND_STEP, end), 2)]])
            for a, b, cols in runs if (b - a) * GROUND_STEP >= GROUND_HELD]
    grounds = [{"hex": to_hex(g["c"]), "seconds": round(g["w"], 2), "spans": sorted(g["notes"])} for g in merge_near(held)]
    spots = merge_near([(s / n, n / (w * h) * GROUND_STEP, [t]) for n, s, t in hot.values()])
    accents = [{"hex": to_hex(a["c"]), "screen_seconds": round(a["w"], 3), "first": round(min(a["notes"]), 2)} for a in spots
               if all(apart(a["c"], g["hex"]) >= NEAR for g in grounds)]
    return {"grounds": grounds, "accents": accents[:4]}


def extract_palette_and_ink(m, colours=None):
    """Aggregate hold palettes and ink-band histograms from measure.py's output, with the grounds and accents read from
    the whole film (film_colours) when given."""
    holds = m.get("holds") or []
    weights = {}
    bands = []
    occupancies = []
    details = []
    for h in holds:
        dur = max(0.05, float(h.get("t1", 0.0)) - float(h.get("t0", 0.0)))
        occupancies.append(float(h.get("occupancy", 0.1)))
        details.append(float(h.get("detail", 0.01)))
        if h.get("bands"):
            bands.extend(float(b) for b in h["bands"])
        for hex_col, share in h.get("palette") or []:
            weights[hex_col] = weights.get(hex_col, 0.0) + dur * float(share)
    # near-identical colours are one swatch, weighed as a share of the time held: il's swatches were six off-whites
    # within 16 levels of each other (weights summing to 26.6), so no other colour made the list
    total = sum(weights.values()) or 1.0
    ranked = [(to_hex(g["c"]), g["w"] / total) for g in merge_near([(hex_to_rgb(c), wt, []) for c, wt in weights.items()])]
    colors = [c for c, _ in ranked] if ranked else ["#121316", "#f4efe6", "#2a5bd7", "#e04f33"]
    found = (colours or {}).get("grounds") or []
    if found:   # the ground held longest over the whole film; a red end card was the longest hold of one that never rests
        ground = found[0]["hex"]
    else:
        # the ground is the frame's border colour held longest (measure.py's background), not the largest colour cluster:
        # a film of dark paintings on paper had its paintings' navy taken for its ground
        grounds = {}
        for h in holds:
            if h.get("ground"):
                k = tuple(v // 16 for v in hex_to_rgb(h["ground"]))
                grounds.setdefault(k, [0.0, h["ground"]])[0] += max(0.05, float(h.get("t1", 0.0)) - float(h.get("t0", 0.0)))
        ground = max(grounds.values())[1] if grounds else colors[0]
    colors = [ground] + [c for c in colors if c != ground]
    g_luma = rgb_luma(hex_to_rgb(ground))
    # Ink is the colour with highest luminance contrast against ground
    ink = max(colors, key=lambda c: abs(rgb_luma(hex_to_rgb(c)) - g_luma)) if len(colors) > 1 else ("#141413" if g_luma > 0.5 else "#f5f2eb")
    if abs(rgb_luma(hex_to_rgb(ink)) - g_luma) < 0.35:
        ink = "#141413" if g_luma > 0.5 else "#f5f2eb"
    # the accent: the most coloured (chroma, max - min) of the colours clearly apart from ground and ink. Saturation on
    # its own made a near-black teal the accent, and a colour one step from the ground counted as distinct from it
    far = lambda a, b: sum((x - y) ** 2 for x, y in zip(hex_to_rgb(a), hex_to_rgb(b))) ** 0.5 >= 48
    chroma = lambda c: max(hex_to_rgb(c)) - min(hex_to_rgb(c))
    # and never one of the film's grounds: those are the stage, the accent is what is set on it
    off = [c for c in colors if far(c, ground) and far(c, ink) and all(apart(c, g["hex"]) >= NEAR for g in found)]
    accents = (colours or {}).get("accents") or []
    if accents:   # read over the whole film: a small chip never shows in a hold's four-colour palette (il's blue)
        accent = accents[0]["hex"]
    else:
        accent = max(off, key=chroma) if off and chroma(max(off, key=chroma)) >= 40 else "#e04f33"
    surface = next((c for c in colors if all(apart(c, x) >= NEAR for x in (ground, ink, accent))), "#24262b" if g_luma <= 0.5 else "#e8e2d5")
    band_arr = np.asarray(bands, dtype=np.float32) if bands else np.array([0.08, 0.05, 0.036], dtype=np.float32)
    return {
        "ground": ground,
        "ink": ink,
        "accent": accent,
        "surface": surface,
        "is_dark": bool(g_luma < 0.45),
        "grounds": found,
        "accents": accents,
        "swatches": [{"hex": c, "weight": round(w, 3)} for c, w in ranked[:8]],
        "ink_bands": {
            "hero_share": round(float(np.percentile(band_arr, 90)), 3),
            "statement_share": round(float(np.percentile(band_arr, 60)), 3),
            "body_share": round(float(np.percentile(band_arr, 30)), 3),
            "occupancy_median": round(float(np.median(occupancies)) if occupancies else 0.18, 3),
            "detail_median": round(float(np.median(details)) if details else 0.015, 4),
        },
    }


def compile_beat_table(m, near_fb=None):
    """Snap measured visual events, cuts, holds and audio onsets onto one deterministic beat clock. Onsets cannot tell a
    tempo from its half or double (measure.py names both as `octave`); with `near_fb`, the frames a beat of the film
    being made, the one of the three nearest it is taken (Linden's 100 BPM was read as 200 and set 18 frames a beat)."""
    fps = 60
    dur = float(m.get("duration") or 30.0)
    snd = m.get("sound") or {}
    t = snd.get("tempo") or {}
    bpm = float(t.get("bpm") or 112.5)
    if near_fb and t.get("octave"):
        bpm = min([bpm, *map(float, t["octave"])], key=lambda b: abs(3600.0 / b - near_fb))
    # Choose an integer frames-per-beat FB near 60 * 60 / bpm
    fb = max(18, min(60, int(round(3600.0 / bpm))))
    beat_s = fb / fps
    beats_total = max(8, int( math.ceil(dur / beat_s)))
    events_s = [float(t) for t in (m.get("events") or [0.0])]
    onsets_s = [float(t) for t in (snd.get("onsets") or [])]

    def snap_sec(t):
        if onsets_s:
            nearest = min(onsets_s, key=lambda o: abs(o - t))
            if abs(nearest - t) <= 0.065:
                t = nearest
        return round(t / beat_s, 3)

    event_beats = sorted({snap_sec(t) for t in events_s if 0.0 <= t <= dur})
    if not event_beats:
        event_beats = [round(i * beats_total / 6.0, 2) for i in range(6)]
    cuts_beats = [snap_sec(t) for t in (m.get("cuts") or [])]
    # every event is a cue, each with its time in seconds and in beats: the cues stopped after 24 (at 23.4 s of 34.9)
    cues = [{"name": f"BEAT_{i + 1}", "s": round(b * beat_s, 4), "beat": b} for i, b in enumerate(event_beats)]
    clock = {
        "FPS": fps,
        "FB": fb,
        "BEATS": beats_total,
        "DURATION": round(beats_total * beat_s, 6),
        "BPM": round(60.0 / beat_s, 4),
    }
    times = {
        "OPEN": event_beats[0] if event_beats else 0.0,
        "TURN": event_beats[len(event_beats) // 3] if len(event_beats) >= 3 else round(beats_total * 0.33, 2),
        "PROOF": event_beats[(2 * len(event_beats)) // 3] if len(event_beats) >= 3 else round(beats_total * 0.66, 2),
        "END": event_beats[-1] if len(event_beats) else round(beats_total * 0.85, 2),
        "EVENTS": event_beats,
        "CUTS": cuts_beats,
    }
    # the unit, and the same times in seconds beside them: a reader took END 38.125 (beats) for seconds past a 17 s film
    sec = lambda b: round(b * beat_s, 3)
    times.update({"UNIT": "beats", "BEAT_S": round(beat_s, 6),
                  "SECONDS": {k: ([sec(b) for b in v] if isinstance(v, list) else sec(v)) for k, v in times.items()}})
    return clock, times, cues


def inspect_repo(repo_dir: Path):
    """Read a target repository's real metadata (name, tagline, CLI/scripts, languages, git stats) without running code."""
    repo_dir = Path(repo_dir).resolve()
    if not repo_dir.exists():
        raise SystemExit(f"--for {repo_dir}: no such folder")
    name = repo_dir.name
    tagline = f"{name}: built from source."
    commands = []
    # Check package.json, pyproject.toml, Cargo.toml, README.md
    pkg = repo_dir / "package.json"
    if pkg.is_file():
        try:
            pj = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            name = pj.get("name") or name
            if pj.get("description"):
                tagline = str(pj["description"]).strip()
            for k, v in list((pj.get("scripts") or {}).items())[:4]:
                commands.append(f"npm run {k}  # {v}")
        except ValueError:
            pass
    readme = next((repo_dir / f for f in ("README.md", "readme.md", "SKILL.md") if (repo_dir / f).is_file()), None)
    if readme:
        lines = [l.strip() for l in readme.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        for l in lines:
            if l.startswith("# ") and len(l) > 2:
                name = l[2:].strip()[:48]
                break
        for l in lines:
            if not l.startswith(("#", "<", "!", "|", "-", "`", "[")) and len(l) >= 16:
                tagline = re.sub(r"\*\*|\*|`|\[([^\]]+)\]\([^)]+\)", r"\1", l).strip()[:110]
                break
    py_files = [p for p in repo_dir.rglob("*.py") if ".git" not in p.parts and "node_modules" not in p.parts and "__pycache__" not in p.parts]
    ts_files = [p for p in list(repo_dir.rglob("*.ts")) + list(repo_dir.rglob("*.tsx")) if ".git" not in p.parts and "node_modules" not in p.parts]
    commits = 0
    try:
        p = subprocess.run(["git", "-C", str(repo_dir), "rev-list", "--count", "HEAD"], capture_output=True, text=True, timeout=5)
        if p.returncode == 0 and p.stdout.strip().isdigit():
            commits = int(p.stdout.strip())
    except Exception:
        pass
    return {
        "name": name,
        "path": repo_dir.as_posix(),
        "tagline": tagline,
        "python_files": len(py_files),
        "ts_files": len(ts_files),
        "total_code_files": len(py_files) + len(ts_files),
        "commits": commits,
        "commands": commands or [f"cd {repo_dir.name}"],
    }


SYNC_MARGIN = 0.1   # events must land on an onset this much more often than chance to follow the sound (measure compare's margin)

# TAKE-APART.md's headings that only a reader of the film can write. borrow once filled "The world" and "The formal
# idea" from its numbers ("Events lock to a 150.0 BPM grid" for a film whose events landed on the beat at chance)
TO_WRITE = [
    ("The world", "what everything on screen is made of and why that material belongs to the subject; its rules (ground, light, colour, type, what moves and how, what never appears); the ground's job. The held colours under Measured are numbers for it, not it"),
    ("The formal idea", "the one move the whole film is built on"),
    ("Ties", "each one: what it is, where it first appears, where it returns, what the return means"),
    ("Hand-overs", "a row for every boundary between two moments, with its time, and what carries the eye across"),
    ("Dynamics", "where it builds, peaks and rests, in the picture and in the loudness"),
    ("Flat notes", "every moment where the film drops, with the time"),
    ("Gifts", "details nobody asked for, with times"),
    ("Words, picture, sound", "what the words carry that the picture does not, and the other way"),
    ("Keeps and breaks", "the conventions of its kind that it keeps, and the one it breaks"),
    ("Hardest shot", "the stretch that would cost the most to make"),
]


def sync_line(s):
    """Whether the reference's events follow its sound, said against what chance gives."""
    rate, chance = s.get("sync_rate"), s.get("sync_chance")
    if rate is None or chance is None:
        return "Events on a sound onset: not measured (no sound, or no onsets in it)."
    said = ("above chance, so its events follow its sound" if rate > chance + SYNC_MARGIN else
            f"no more than chance (within {SYNC_MARGIN} of it), so nothing here says its events follow its sound")
    return f"Events on a sound onset (within 50 ms): {rate} of them, against {chance} by chance: {said}."


def write_reference_md(dest: Path, ref_path: Path, dna: dict):
    """Write REFERENCE.md, a start on the TAKE-APART.md dossier: borrow fills the headings it measured (spine, moves,
    measured) and leaves every heading a reader of the film must write with what to write there."""
    s = dna["summary"]
    pal = dna["palette"]
    springs = dna["springs"]
    archetype, why_arch = dna["archetype"], dna["archetype_reason"]
    clock = dna["clock"]
    fitted = sum(1 for x in springs if x["reliable"])
    write = lambda what, step=3: f"_To write (TAKE-APART.md, step {step}): {what}._"
    lines = [
        f"# {ref_path.stem} (decompiled by `vd borrow`)",
        "> The claim: " + write("one sentence, checkable against the film, saying what it does that makes it hold"),
        f"Post: local file `{ref_path.name}` · {dna['duration']:.1f} s · {dna['width']}x{dna['height']} at {dna['fps']:g} fps · "
        "credits and the maker's words: to find (TAKE-APART.md, step 2)",
        "Kind: " + write("what a shop would file it under") + (f" This folder was copied from the worked film `{archetype}` ({why_arch})." if archetype else f" ({why_arch})"),
        f"Evidence: measured every frame by `measure.py` and `space.py`; {fitted} of {len(springs)} move speed profiles fitted to closed-form springs and cubic-beziers.",
        "",
        "## Spine",
        write("its parts, its grounds and its ties on this ruler") + " Below: measure's holds and moves only.",
        "```text",
    ]
    for seg in (dna.get("segments") or [])[:16]:
        lines.append(f"{seg['t0']:6.2f}s .. {seg['t1']:6.2f}s  [{seg['kind'].upper():4s}]")
    lines += ["```", ""]
    for heading, what in TO_WRITE:
        lines += [f"## {heading}", write(what), ""]
    lines += [
        "## Moves (optical-flow spring + bezier fit)",
        f"{fitted} of {len(springs)} moves fitted. `DNA_SPRING` and `DNA_BEZIER`: {dna['motion']}.",
        "",
    ]
    if springs:
        lines += ["| t0 (s) | dur (s) | spring freq (Hz) | spring damp | cubic-bezier | reliable |", "|---|---|---|---|---|---|"]
    for mv in springs[:12]:
        lines.append(f"| {mv['t0']:.2f} | {mv['dur']:.2f} | {mv['spring']['freq']} | {mv['spring']['damp']} | `{mv['ease']}` | {mv['reliable']} |")
    tempo = s.get("tempo_bpm")
    lines += [
        "",
        "## Measured",
        f"- `events_per_10s`: {s.get('events_per_10s')} · `median_hold_s`: {s.get('median_hold_s')} · `median_move_s`: {s.get('median_move_s')} · moving {float(s.get('move_share') or 0):.0%} of the time",
        "- " + sync_line(s),
        f"- Beat clock in `kit/dna.gen.ts`: {clock['BPM']} BPM, {clock['FB']} frames a beat at 60 fps, "
        + (f"from the tempo read in its sound ({tempo} BPM; onsets cannot tell it from half or double)." if tempo else
           "but no tempo was read in its sound, so this clock is borrow's default, not the film's."),
        f"- Events and cuts: {len(dna['times']['EVENTS'])} events and {len(dna['times']['CUTS'])} cuts, in `DNA_TIMES` (and `dna.json` `times`) in beats of that clock "
        f"(one beat is {dna['times']['BEAT_S']:g} s), and in seconds in `DNA_TIMES.SECONDS`; `dna.json` `cues` names each event with both.",
        "- Grounds (full-frame colours held 0.5 s or more, longest on screen first): "
        + ("; ".join(f"`{g['hex']}` {g['seconds']:g} s ({', '.join(f'{a:g}-{b:g}' for a, b in g['spans'][:6])}{', ...' if len(g['spans']) > 6 else ''} s)"
                     for g in pal.get("grounds") or []) or "none held 0.5 s over the whole film (the ground below is from its holds)") + ".",
        "- Accents (strongly coloured things on a ground, by share of the screen over time): "
        + (", ".join(f"`{a['hex']}` (first at {a['first']:g} s)" for a in pal.get("accents") or []) or "none found") + ".",
        f"- Held colours: ground `{pal['ground']}` ({'dark' if pal['is_dark'] else 'light'}) · ink `{pal['ink']}` · accent `{pal['accent']}` · surface `{pal['surface']}`.",
        f"- Ink bands (share of frame height): hero {pal['ink_bands']['hero_share']}, statement {pal['ink_bands']['statement_share']}, body {pal['ink_bands']['body_share']}; median occupancy {pal['ink_bands']['occupancy_median']}.",
        f"- Space: scene motion {s.get('scene_move')}, sheet motion {s.get('sheet_move')}, lit middle with dark corners {s.get('dark_corners')}.",
        "",
        "## Not known",
        write("what you could not see, hear or find out"),
        "",
        "## What we take and what stays theirs",
        write("its shape: the order of its parts, its formal idea, its hand-overs, its pace, how its words arrive, the job its ground does; "
              "and what stays theirs: its subject, words, pictures, marks, characters, music. `kit/dna.gen.ts` holds what borrow measured: take from it "
              "only what this dossier finds is the film's shape", step=4),
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_dna_cartridge(ref_video: Path, out_dir: Path = None, repo_dir: Path = None, k: int = 5, like: str = None):
    """Fit `ref_video`'s moves and colours into dna.json, kit/dna.gen.ts and REFERENCE.md in `out_dir` (made with
    `vd new --like` when new)."""
    import lean
    import measure
    ref_video = Path(ref_video).resolve()
    if not ref_video.is_file():
        raise SystemExit(f"no such reference video: {ref_video}")

    # 1. Measure the reference video (cached in ~/.vd/measures)
    m_dir = Path.home() / ".vd" / "measures" / ("borrow-" + lean.hashlib.sha1(ref_video.read_bytes()).hexdigest()[:12])
    m = json.loads((m_dir / "measure.json").read_text(encoding="utf-8")) if (m_dir / "measure.json").is_file() else {}
    if m.get("version") != measure.VERSION:  # made by another measure.py, or never: its numbers are measured again
        measure.measure(ref_video, m_dir)
        m = json.loads((m_dir / "measure.json").read_text(encoding="utf-8"))

    # 2. Fit optical-flow velocity profiles to physics.ts springs + cubic-beziers
    springs = []
    for mv in m.get("moves") or []:
        sp = fit_spring_profile(mv.get("profile") or [], dur=float(mv.get("dur") or 0.4))
        springs.append({
            "t0": mv["t0"],
            "dur": mv["dur"],
            "peak": mv.get("peak"),
            "ease": mv.get("ease") or [0.2, 0.8, 0.2, 1.0],
            "spring": sp,
            "reliable": bool(mv.get("ease_reliable", True)) and sp["fitted"],
        })
    # the film's spring and curve are the medians of its moves that fitted a spring and whose speed could be read. With
    # none there is no spring of this film's: a fallback {2.4, 0.48} stood in here, unflagged, and a film imported it as
    # the reference's motion (HEX fitted 0 of 4 moves, il 0 of 27)
    reliable = [x for x in springs if x["reliable"]]
    default_spring = {"freq": round(float(np.median([x["spring"]["freq"] for x in reliable])), 2),
                      "damp": round(float(np.median([x["spring"]["damp"] for x in reliable])), 2)} if reliable else None
    default_bezier = [round(float(np.median([x["ease"][i] for x in reliable])), 2) for i in range(4)] if reliable else None
    motion = (f"the median of {len(reliable)} of {len(springs)} moves, the ones that fit a spring and whose speed could be read" if reliable else
              "no move was fitted: " + (f"none of its {len(springs)} moves fits a spring with a speed that could be read from the picture"
                                         if springs else "measure found no move of 0.15 to 3 s to fit")
              + ", so there is no spring or curve of this film's to take; read its moves from the frames")

    # 3. Extract palette, ink bands, archetype, and beat clock
    palette = extract_palette_and_ink(m, film_colours(ref_video, m.get("duration")))
    # Which worked film this is like is chosen, not measured: on the four accepted films the measures that once picked it
    # named all four `onoma`, and Onoma and Plus One are near twins on every one of them (6.2 and 6.5 events in 10 s,
    # largest type band 0.259 and 0.257). A kind is what a film shows; these numbers are how it moves.
    archetype = like
    arch_reason = "chosen with --like" if like else "not chosen: borrow does not guess a kind from the measures"
    near = None
    here = Path(out_dir) if out_dir is not None else lean.film_dir(None, required=False)
    if here is not None and (Path(here) / "kit" / "times.gen.ts").is_file():
        near = (lean.gen_data(Path(here)).get("CLOCK") or {}).get("FB")
    elif like:
        near = (lean.gen_data(TOOLS.parent / "library" / "films" / like).get("CLOCK") or {}).get("FB")
    clock, times, cues = compile_beat_table(m, near_fb=near)
    repo_info = inspect_repo(repo_dir) if repo_dir else None

    # 4. Create or bind target film folder
    if out_dir is None:
        existing = lean.film_dir(None, required=False)
        if existing is not None:
            out_dir = existing
        else:
            stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", (repo_info["name"] if repo_info else ref_video.stem).lower()).strip("-") or "stolen"
            out_dir = Path.cwd() / stem
    out_dir = Path(out_dir).resolve()
    if not (out_dir / "score.json").is_file():
        if not like:
            raise SystemExit(f"vd borrow: {out_dir} is not a film folder yet, and borrow makes one only as a copy of the worked "
                             "film you name with --like (plusone, stet, onoma or linden; SKILL.md, step 1, says which "
                             "fits): its measures cannot tell the kinds apart. Or run it inside your film folder.")
        class NewArgs:
            name = str(out_dir)
            like = archetype
            kind = None
            bare = False
        lean.cmd_new(NewArgs())

    # 5. Write dna.json, kit/dna.gen.ts, REFERENCE.md, and pin targets in score.json
    dna = {
        "source_video": ref_video.name,
        "width": m.get("w", 1920),
        "height": m.get("h", 1080),
        "fps": m.get("fps", 60.0),
        "duration": m.get("duration", 10.0),
        "archetype": archetype,
        "archetype_reason": arch_reason,
        "clock": clock,
        "times": times,
        "cues": cues,
        "default_spring": default_spring,
        "default_bezier": default_bezier,
        "motion": motion,
        "springs": springs,
        "palette": palette,
        "summary": m.get("summary") or {},
        "segments": m.get("segments") or [],
        "repo": repo_info,
    }
    (out_dir / "dna.json").write_text(json.dumps(dna, indent=1) + "\n", encoding="utf-8")
    (out_dir / "kit").mkdir(parents=True, exist_ok=True)
    ts_lines = [
        "// generated by `vd borrow`: moves fitted to springs and curves, and held colours, from " + ref_video.name,
        f"export const DNA_ARCHETYPE = {json.dumps(archetype)} as const;",
        f"export const DNA_CLOCK = {json.dumps(clock)} as const;",
        f"// DNA_SPRING and DNA_BEZIER: {motion}",
        f"export const DNA_SPRING = {json.dumps(default_spring)} as const;" if default_spring else "export const DNA_SPRING = null;",
        f"export const DNA_BEZIER = {json.dumps(default_bezier)} as [number, number, number, number];" if default_bezier else "export const DNA_BEZIER = null;",
        f"export const DNA_PALETTE = {json.dumps(palette)} as const;",
        f"export const DNA_MOVES = {json.dumps(springs)} as const;",
        f"// DNA_TIMES: in beats of DNA_CLOCK (one beat is {times['BEAT_S']:g} s); DNA_TIMES.SECONDS holds the same times in seconds",
        f"export const DNA_TIMES = {json.dumps(times)} as const;",
        f"export const DNA_REPO = {json.dumps(repo_info)} as const;",
    ]
    (out_dir / "kit" / "dna.gen.ts").write_text("\n".join(ts_lines) + "\n", encoding="utf-8", newline="\n")
    write_reference_md(out_dir / "REFERENCE.md", ref_video, dna)

    score = lean.score_of(out_dir)
    score["dna"] = "dna.json"  # `pinned` and `targets` are vd pin's: vd measure reads them in pin's shape, not this one
    (out_dir / "score.json").write_text(json.dumps(score, indent=1) + "\n", encoding="utf-8")
    lean.pin_material(ref_video, lean.outdir(out_dir), k=k)
    return out_dir, dna


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ref", help="reference video file (MP4/MOV/MKV/WEBM)")
    ap.add_argument("--for", dest="repo", help="also record this repository's counts in dna.json (nothing reads them yet)")
    ap.add_argument("--out", help="destination film folder (default: current film folder, or ./<name>)")
    ap.add_argument("--k", type=int, default=5, help="number of 1s busiest motion sheets to extract into pin/")
    ap.add_argument("--like", choices=("plusone", "stet", "onoma", "linden"), help="the worked film to copy when borrow makes a new film folder (plusone, stet, onoma, linden): chosen, never guessed")
    a = ap.parse_args(argv)
    out_dir, dna = compile_dna_cartridge(
        Path(a.ref),
        out_dir=Path(a.out) if a.out else None,
        repo_dir=Path(a.repo) if a.repo else None,
        k=a.k,
        like=a.like,
    )
    say(Path(a.ref), out_dir, dna)
    print(out_dir)


def say(ref, out_dir, dna):
    """What borrow read and wrote, for borrow.py and for vd borrow alike: through vd.py it once printed only the folder."""
    sp = dna["default_spring"]
    pal = dna["palette"]
    print(f"fitted {Path(ref).name} -> {out_dir}")
    print(f"  kind: {dna['archetype'] or '-'} ({dna['archetype_reason']})")
    print(f"  clock: {dna['clock']['BPM']} BPM ({dna['clock']['FB']} frames/beat at {dna['clock']['FPS']} fps), {len(dna['times']['EVENTS'])} snapped events")
    print(f"  spring fit: freq {sp['freq']} Hz, damp {sp['damp']}; bezier {dna['default_bezier']} ({dna['motion']})" if sp else f"  spring fit: {dna['motion']}")
    print(f"  grounds: {', '.join(g['hex'] + ' ' + format(g['seconds'], 'g') + ' s' for g in pal['grounds']) or 'none held 0.5 s'}")
    print(f"  palette: ground {pal['ground']}, ink {pal['ink']}, accent {pal['accent']}, hero band {pal['ink_bands']['hero_share']}")
    if dna.get("repo"):
        r = dna["repo"]
        print(f"  repo cast: {r['name']} ({r['total_code_files']} code files, {r['commits']} commits) — \"{r['tagline']}\"")
    print(f"  wrote: {out_dir / 'dna.json'}, {out_dir / 'kit' / 'dna.gen.ts'}, {out_dir / 'REFERENCE.md'} (to finish by TAKE-APART.md)")


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
