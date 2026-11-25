#!/usr/bin/env python3
"""Measure one film end to end, the same way for every film.

  python measure_film.py FILM OUTDIR [--judge JUDGEDIR] [--skip-tools]

Writes OUTDIR/measures.json, OUTDIR/REPORT.md, OUTDIR/curves.png, OUTDIR/windows/change-NN.jpg (8 frames each side of
every scene change) and OUTDIR/sheets/sheet-NN.jpg (4 frames a second, 4 x 4 tiles, 1920 wide). With --judge, copies
the sheets and windows there under neutral names (no film name anywhere in them).

Uses the product's own tools read-only: video-decompiler measure.py (its onset detector and its chance model for sync)
and see.py (its shot boundaries are the scene changes here, its camera moves and its move count). Everything else is
computed below, and every threshold is a named constant so the same numbers are applied to every film.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
def measure_versions(measure, see):
    """The versions of the measures this file holds: a cached one made by other code is measured again (lean.measures_of)."""
    return {"measure": measure.VERSION, "see": see.VERSION}


from measure import audio as vd_audio  # noqa: E402  product onset detector (10 ms hop, flux > mean + 2 sd, level > -50 dB)

NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ---- thresholds: one set for all films --------------------------------------------------------------------------
DIFF_W, DIFF_H = 320, 180   # frame-difference curve is measured at this size (as measure.py)
MOVE = 0.35                 # mean abs luma change (0-255) between frames at 320x180 above which the picture moves (measure.py's MOVE)
MERGE_GAP = 0.10            # s: a rest shorter than this inside a move is part of the move (measure.py's MIN_HOLD)
LARGE_MOVE = 2.0            # peak mean abs luma change in a frame-difference run (a sensitivity variant of the sync events only)
LARGE_AREA = 0.08           # a move is large when see.py's moving thing covers at least this share of the frame (see.py's own "big")
SYNC_FRAMES = 2             # a picture event within this many of the film's own frames of a sound onset lands on it
SAMPLE_EVERY = 0.25         # s between frames sampled for the frame measures and the judge sheets
FW, FH = 480, 270           # frame measures are read at this size
ACHROMA_S = 40              # HSV saturation (0-255) below which a pixel is grey/black/white, not a hue
FAMILY_MIN = 0.03           # a colour family counts if it covers at least this share of the frame
FLAT_BLOCK, FLAT_STD = 8, 3.0   # an 8x8 block (at 480x270) whose max channel std is below 3.0 is flat single colour
CANNY_LO, CANNY_HI = 100, 200   # edge pixels (at 480x270)
FG_DIST = 40                # RGB distance from the background colour beyond which a pixel belongs to a thing
GAP_MIN = 0.12              # s: a silence between words at least this long is a gap (for level-in-gaps)
EDGE_TRIM = 0.04            # s trimmed off each side of a gap and of a word before reading the level
WINDOW_SIDE = 8             # frames each side of a scene change in the fine window
BREATH = 0.25               # s: a pause between words this long counts as a gap between sentences
# -----------------------------------------------------------------------------------------------------------------


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, creationflags=NO_WINDOW)
    j = json.loads(p.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a, b = v["r_frame_rate"].split("/")
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": float(a) / float(b),
            "duration": float(j["format"]["duration"]), "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def frames(path, w, h):
    """Every picture of the film at w x h, checked (decode.py): a damaged film is an error, never a measure of part of it."""
    import decode
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=area",
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    for b in decode.pictures(cmd, w * h * 3, str(path), expect=decode.frame_count(path)):
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)


def font(size):
    for f in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# ---- frame measures ----------------------------------------------------------------------------------------------
def colour_families(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1], hsv[..., 2]
    lab = np.where(s >= ACHROMA_S, (h * 2 // 30) % 12, 0)            # 12 hue families of 30 degrees
    ach = (s < ACHROMA_S) | (v < 40)
    lab = np.where(ach, 12 + np.digitize(v, [70, 190]), lab)           # 12 dark, 13 grey, 14 light
    share = np.bincount(lab.ravel(), minlength=15) / lab.size
    return int((share >= FAMILY_MIN).sum()), float(s.mean() / 255), {str(t): int((share >= t).sum()) for t in (0.015, FAMILY_MIN, 0.06)}


def flat_share(rgb):
    h, w = rgb.shape[0] // FLAT_BLOCK * FLAT_BLOCK, rgb.shape[1] // FLAT_BLOCK * FLAT_BLOCK
    x = rgb[:h, :w].astype(np.float32).reshape(h // FLAT_BLOCK, FLAT_BLOCK, w // FLAT_BLOCK, FLAT_BLOCK, 3)
    sd = x.std(axis=(1, 3)).max(axis=-1)
    return {t: float((sd < t).mean()) for t in (1.5, FLAT_STD, 6.0)}


def largest_thing(rgb):
    q = (rgb // 32).astype(np.int32)
    code = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    bgc = np.bincount(code.ravel()).argmax()
    bg = (np.array([bgc // 64, (bgc // 8) % 8, bgc % 8]) * 32 + 16).astype(np.float32)
    fg = (np.linalg.norm(rgb.astype(np.float32) - bg, axis=-1) > FG_DIST).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, 8)
    if n <= 1:
        return 0.0, 0.0
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    area = stats[i, cv2.CC_STAT_AREA] / fg.size
    box = stats[i, cv2.CC_STAT_WIDTH] * stats[i, cv2.CC_STAT_HEIGHT] / fg.size
    return float(area), float(box)


def frame_measures(rgb):
    fam, sat, fam_sens = colour_families(rgb)
    luma = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    p5, p95 = np.percentile(luma, [5, 95])
    edges = cv2.Canny(luma, CANNY_LO, CANNY_HI)
    lap = cv2.Laplacian(luma, cv2.CV_32F)
    area, box = largest_thing(rgb)
    return {"families": fam, "families_by_min": fam_sens, "luma_mean": float(luma.mean() / 255), "saturation": sat, "spread": float((p95 - p5) / 255), "flat": flat_share(rgb),
            "edge": float((edges > 0).mean()), "detail": float(np.abs(lap).mean() / 255), "largest_area": area, "largest_box": box}


# ---- sheets ------------------------------------------------------------------------------------------------------
def stamp(im, text, size=14):
    d = ImageDraw.Draw(im)
    f = font(size)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.rectangle([0, im.height - (y1 - y0) - 8, x1 - x0 + 8, im.height], fill=(0, 0, 0))
    d.text((4, im.height - (y1 - y0) - 6 - y0), text, fill=(255, 255, 255), font=f)
    return im


def grid(tiles, cols, tw, th, pad=0):
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * tw + (cols - 1) * pad, rows * th + (rows - 1) * pad), (40, 40, 40))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * (tw + pad), (i // cols) * (th + pad)))
    return out


def window_frames(path, a, b, w=320, h=180):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf",
                        f"select='between(n\\,{a}\\,{b})',scale={w}:{h}:flags=area", "-fps_mode", "passthrough", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True, creationflags=NO_WINDOW)
    n = w * h * 3
    return [Image.frombytes("RGB", (w, h), p.stdout[i:i + n]) for i in range(0, len(p.stdout) - n + 1, n)]


# ---- words ------------------------------------------------------------------------------------------------------
def num(v, spec):
    """A number for the text report, or "none" where the film has nothing to measure (no voice, one shot)."""
    return "none" if v is None else format(v, spec)


# What the transcriber is known to hear in music with no voice (Whisper's false hearings: it was trained on subtitled
# video, so a quiet or musical stretch comes back as a subtitle's sign-off). A transcript that is only these is no voice.
FALSE_HEARINGS = ("thank you for watching", "thanks for watching", "thank you", "thank you so much for watching", "please subscribe",
                  "subtitles by", "subtitled by", "transcribed by", "you", "bye", "music", "applause")
# Whole sentences it hears in music, YouTube's sign-offs: a music film was transcribed as "Thank you so much for watching
# this video, and I'll see you in the next one." twice (30 words, 1.36 a second), and the list above, of short endings,
# let it through. A transcript that is nothing but these and the short ones, joined by a few small words, is no voice.
SIGN_OFFS = ("thank you so much for watching this video", "thank you for watching this video", "thanks for watching this video",
             "thank you so much for watching", "ill see you in the next one", "ill see you in the next video", "see you in the next one",
             "see you in the next video", "see you next time", "dont forget to like and subscribe", "like and subscribe",
             "please like and subscribe", "subscribe to my channel", "thank you very much")
JOINERS = {"and", "so", "i", "oh", "well", "okay", "ok", "um", "uh", "the", "a", "guys", "everyone"}
MIN_WORDS_PER_S = 1.0      # under this many words a second, with no gap between sentences, it is not a voice


def no_voice(ws, duration):
    """Why a transcript is no voice (a known false hearing, or too few words with no sentence gap), or None if it is one."""
    if not ws:
        return None
    said = re.sub(r"[^a-z ]", "", " ".join(w["w"] for w in ws).lower()).strip()
    if said in FALSE_HEARINGS or all(re.sub(r"[^a-z ]", "", w["w"].lower()).strip() in " ".join(FALSE_HEARINGS).split() for w in ws):
        return f"the transcriber heard only \"{said}\", one of its known false hearings in music"
    left = " " + re.sub(r"\s+", " ", said) + " "
    for phrase in sorted(SIGN_OFFS + FALSE_HEARINGS, key=len, reverse=True):
        left = left.replace(f" {phrase} ", " ")
    if not set(left.split()) - JOINERS:
        return f"the transcriber heard only sign-offs (\"{said[:80]}{'...' if len(said) > 80 else ''}\"), known false hearings in music"
    if duration and len(ws) / duration < MIN_WORDS_PER_S and not sentence_gaps(ws):
        return f"{len(ws)} words in {duration:.1f} s with no gap between sentences is not a voice"
    return None


TRANSCRIBED, TOLD, NOT_TRANSCRIBED = "transcribed", "no voice (--no-voice)", "not transcribed"
MODEL = "small"   # faster-whisper's model, read from the Hugging Face cache only (Systran/faster-whisper-small)
from lean import transcriber  # noqa: E402  why this machine can't transcribe, or None (doctor asks it too)


def words_of(path, out, skip=False):
    """(words with their times, how they were got: TRANSCRIBED, TOLD or "not transcribed: why"). The transcriber is
    the one heavy part of a measure, so only it waits in the machine's queue (and says so at once); --no-voice skips it
    and the queue. A transcriber that is missing (the package, or its model on this machine) is not a film with no voice:
    a spoken reference was measured as silent. Its words are unknown, said so, and not cached."""
    cache = out / "words.json"
    if skip:
        cache.write_text("[]", encoding="utf-8")
        return [], TOLD
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), TRANSCRIBED
    os.environ["HF_HUB_OFFLINE"] = "1"  # local model only; nothing is fetched
    why = transcriber()
    if why is None:
        from faster_whisper import WhisperModel
    else:
        print(f"measure_film: {NOT_TRANSCRIBED}: {why}; the film's word measures are left out, not counted as no voice "
              "(give --no-voice for a film that has none)", file=sys.stderr)
        return [], f"{NOT_TRANSCRIBED}: {why}"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                        "-f", "f32le", "-"], capture_output=True, creationflags=NO_WINDOW)
    x = np.frombuffer(p.stdout, np.float32)
    held = None
    try:
        import raea_run
        print("measure_film: loading the transcriber, which waits its turn in the render queue (give --no-voice to skip it)", file=sys.stderr, flush=True)
        held = raea_run.one_at_a_time(wait=3600.0, what=f"measure_film transcriber: {Path(path).name}", kind="heavy")
    except ImportError:
        pass
    try:
        try:
            model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=4)
        except Exception as e:   # the model is not in the Hugging Face cache, and nothing is fetched while measuring
            why = (f"its model (faster-whisper {MODEL}) could not be loaded from this machine's Hugging Face cache, and nothing is fetched "
                   f"while measuring ({type(e).__name__}: {str(e).splitlines()[0][:160] if str(e) else ''})")
            print(f"measure_film: {NOT_TRANSCRIBED}: {why}; the film's word measures are left out", file=sys.stderr)
            return [], f"{NOT_TRANSCRIBED}: {why}"
        segs, _ = model.transcribe(x, language="en", vad_filter=False, word_timestamps=True)
        ws = [{"w": w.word.strip(), "t0": round(w.start, 3), "t1": round(w.end, 3)} for s in segs for w in s.words]
    finally:
        if held is not None:
            held.close()
    why = no_voice(ws, len(x) / 16000)
    if why:
        print(f"measure_film: no voice: {why}", file=sys.stderr)
        (out / "heard.json").write_text(json.dumps(ws, indent=1), encoding="utf-8")   # kept, so a maker can see what was heard
        ws = []
    cache.write_text(json.dumps(ws, indent=1), encoding="utf-8")
    return ws, TRANSCRIBED


def sentence_gaps(ws):
    """A gap between sentences: after a word ending . ? ! (any length), or any pause of BREATH s or more (a breath at a
    comma, as in 'vision, and ...'). Whisper's punctuation alone misses comma breaths; pause length alone misses run-ons."""
    gaps = []
    for a, b in zip(ws, ws[1:]):
        if re.search(r"[.?!]$", a["w"]) or b["t0"] - a["t1"] >= BREATH:
            gaps.append((a["t1"], b["t0"]))
    return gaps


# ---- sound ------------------------------------------------------------------------------------------------------
def pcm(path, sr=16000):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True, creationflags=NO_WINDOW)
    return np.frombuffer(p.stdout, np.float32)


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-10)) if len(x) else None


def lufs(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, creationflags=NO_WINDOW)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    lra = re.findall(r"LRA:\s+(-?[\d.]+) LU", p.stderr)
    return (float(i[-1]) if i else None), (float(lra[-1]) if lra else None)


def sound(path, ws, dur):
    x = pcm(path)
    sr = 16000
    half = int(sr * 0.5)
    curve = [db(x[i:i + half]) for i in range(0, len(x), half)]
    word_parts, gap_parts = [], []
    for w in ws:
        a, b = w["t0"] + EDGE_TRIM, w["t1"] - EDGE_TRIM
        if b > a:
            word_parts.append(x[int(a * sr):int(b * sr)])
    for a, b in zip(ws, ws[1:]):
        if b["t0"] - a["t1"] >= GAP_MIN:
            gap_parts.append(x[int((a["t1"] + EDGE_TRIM) * sr):int((b["t0"] - EDGE_TRIM) * sr)])
    tail = x[int((ws[-1]["t1"] + 0.3) * sr):] if ws else np.array([], np.float32)
    head = x[:int(max(0, ws[0]["t0"] - 0.05) * sr)] if ws else np.array([], np.float32)
    word_db = db(np.concatenate(word_parts)) if word_parts else None
    gap_db = db(np.concatenate(gap_parts)) if gap_parts else None
    # level of the quietest 10% of 20 ms frames inside the gaps: what is left when the voice is truly off
    g = np.concatenate(gap_parts) if gap_parts else np.array([], np.float32)
    fr = int(sr * 0.02)
    gf = [db(g[i:i + fr]) for i in range(0, len(g) - fr, fr)]
    I, LRA = lufs(path)
    return {"curve_db_half_s": [round(c, 1) if c is not None else None for c in curve], "lufs_i": I, "lra": LRA,
            "word_db": word_db, "gap_db": gap_db, "gap_minus_word_db": (gap_db - word_db) if word_db and gap_db else None,
            "gap_seconds": round(len(g) / sr, 2), "gap_floor_db": float(np.percentile(gf, 10)) if gf else None,
            "head_db": db(head), "head_seconds": round(len(head) / sr, 2), "tail_db": db(tail), "tail_seconds": round(len(tail) / sr, 2)}


# ---- main --------------------------------------------------------------------------------------------------------
def runs(mask, fps):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for r in out:
        if merged and (r[0] - merged[-1][1]) / fps < MERGE_GAP:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("out")
    ap.add_argument("--judge")
    ap.add_argument("--skip-tools", action="store_true", help="reuse OUTDIR/vd and OUTDIR/see if present")
    ap.add_argument("--no-voice", action="store_true", help="the film has no voice: skip the transcriber, and with it the render queue")
    a = ap.parse_args()
    film, out = Path(a.film), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    info = probe(film)
    fps, dur = info["fps"], info["duration"]

    # product tools
    for name, cmd in (("vd", [sys.executable, str(TOOLS / "measure.py"), str(film), "--out", str(out / "vd")]),
                      ("see", [sys.executable, str(TOOLS / "see.py"), str(film), "--out", str(out / "see")])):
        if not (a.skip_tools and (out / name).exists()):
            subprocess.run(cmd, check=True, creationflags=NO_WINDOW, stdout=subprocess.DEVNULL)
    vd = json.loads((out / "vd" / "measure.json").read_text(encoding="utf-8"))
    see = json.loads((out / "see" / "motion.json").read_text(encoding="utf-8"))

    # A. scene changes = see.py shot boundaries (the join frames between shots)
    shots = see["shots"]
    changes = []
    for s in shots[1:]:
        j = s["join"]
        changes.append({"first": j["first"], "last": j["last"], "kind": j["kind"], "t0": round(j["first"] / fps, 3),
                        "t1": round((j["last"] + 1) / fps, 3), "t": round((j["first"] + j["last"] + 1) / 2 / fps, 3)})
    shot_lens = [s["dur"] for s in shots]
    ws, heard = words_of(film, out, skip=a.no_voice)
    unknown = heard.startswith(NOT_TRANSCRIBED)
    sgaps = sentence_gaps(ws)
    tol = SYNC_FRAMES / fps
    for c in changes:
        if unknown:
            c["voice"] = NOT_TRANSCRIBED
        elif not ws:
            c["voice"] = "no voice"   # a film with no words has no changes during speech (it counted all of them)
        elif c["t"] > ws[-1]["t1"]:
            c["voice"] = "after the last word"
        elif c["t"] < ws[0]["t0"]:
            c["voice"] = "before the first word"
        else:
            hit = [g for g in sgaps if g[0] - tol <= c["t"] <= g[1] + tol]
            c["voice"] = f"in sentence gap {hit[0][0]:.2f}-{hit[0][1]:.2f}" if hit else "during speech"
            # nearest word under it
            under = [w["w"] for w in ws if w["t0"] <= c["t"] <= w["t1"]]
            if under:
                c["under_word"] = under[0]
    voiced = [c for c in changes if c["voice"].startswith(("in sentence", "during"))]
    in_gap = sum(c["voice"].startswith("in sentence") for c in voiced)

    # one pass over the frames: difference curve + samples
    diffs, samples, prev = [], [], None
    targets = {int(round(k * SAMPLE_EVERY * fps)) for k in range(int(dur / SAMPLE_EVERY) + 1)}
    for i, f in enumerate(frames(film, FW, FH)):
        g = cv2.cvtColor(cv2.resize(f, (DIFF_W, DIFF_H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.int16)
        diffs.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
        prev = g
        if i in targets:
            samples.append((i, i / fps, frame_measures(f), Image.fromarray(f.copy())))
    d = np.array(diffs)
    n = len(d)

    # D. motion
    still = {t: float((d[1:] < t).mean()) for t in (0.2, MOVE, 0.7)}
    mv = runs(d > MOVE, fps)
    moves = [{"t0": round(r[0] / fps, 3), "t1": round(r[1] / fps, 3), "len": round((r[1] - r[0]) / fps, 3),
              "peak": round(float(d[r[0]:r[1]].max()), 2)} for r in mv]
    cam = []
    for s in shots:
        c = s["camera"]
        cam.append({"shot": s["id"], "state": c["state"], "pans": len(c["moves"]), "zooms": len(c["zooms"]), "pan_t": [round(m["t0"], 2) for m in c["moves"]], "zoom_t": [round(m["t0"], 2) for m in c["zooms"]]})
    cam_moves = sum(c["pans"] + c["zooms"] for c in cam)

    # C. sync: scene-change starts + starts of large moves, against product onsets, product chance model
    onsets = vd["sound"]["onsets"] if vd.get("sound") else []
    def dedupe(ts):
        out = []
        for t in sorted(ts):
            if not out or t - out[-1] > tol:
                out.append(round(t, 3))
        return out

    def see_starts(min_area):
        st = []
        for s in shots:
            for th in s["things"]:
                if th["area_share"] >= min_area:
                    st += [m["t0"] for m in th["moves"]]
            st += [m["t0"] for m in s["camera"]["moves"] + s["camera"]["zooms"]]
        return st
    # events: scene-change starts + starts of moves by large things (see.py, >= 8% of the frame, its own "big") + camera moves
    events = dedupe([c["t0"] for c in changes] + see_starts(LARGE_AREA))
    o = np.array(onsets)

    def near(ts):
        return float(np.mean([np.min(np.abs(o - t)) <= tol for t in ts])) if len(ts) and len(o) else None
    rng = np.random.default_rng(0)
    chance = float(np.mean([near((np.array(events) + rng.uniform(0, dur)) % dur) for _ in range(500)])) if events and len(o) else None
    hits = [e for e in events if len(o) and np.min(np.abs(o - e)) <= tol]
    sync_sens = {}
    for k in (1, 2, 3):
        t2 = k / fps
        hit_k = float(np.mean([np.min(np.abs(o - t)) <= t2 for t in events])) if events and len(o) else None
        ch_k = float(np.mean([np.mean([np.min(np.abs(o - t)) <= t2 for t in (np.array(events) + rng.uniform(0, dur)) % dur]) for _ in range(500)])) if events and len(o) else None
        sync_sens[f"{k}f"] = [hit_k, ch_k]
    large_sens = {}
    for lt in (0.02, LARGE_AREA, 0.20):
        ev = dedupe([c["t0"] for c in changes] + see_starts(lt))
        ch = float(np.mean([near((np.array(ev) + rng.uniform(0, dur)) % dur) for _ in range(500)])) if ev and len(o) else None
        large_sens[f"area>={lt}"] = {"events": len(ev), "hit": near(ev), "chance": ch}
    ev = dedupe([c["t0"] for c in changes] + [m["t0"] for m in moves if m["peak"] >= LARGE_MOVE])
    large_sens[f"framediff_runs_peak>={LARGE_MOVE}"] = {"events": len(ev), "hit": near(ev),
                                                     "chance": float(np.mean([near((np.array(ev) + rng.uniform(0, dur)) % dur) for _ in range(500)])) if ev and len(o) else None}

    # E. sound
    snd = sound(film, ws, dur) if info["audio"] else None
    if snd and unknown:   # the lengths around the words are unknown with the words, not zero
        snd.update(gap_seconds=None, head_seconds=None, tail_seconds=None)
    onset_rate = len(onsets) / dur

    # F. frame measures
    fm = [s[2] for s in samples]
    agg = lambda k: float(np.mean([m[k] for m in fm]))
    frame = {"samples": len(fm), "families_mean": agg("families"), "families_median": float(np.median([m["families"] for m in fm])),
             "families_by_min": {k: float(np.mean([m["families_by_min"][k] for m in fm])) for k in fm[0]["families_by_min"]}, "luma_mean": agg("luma_mean"),
             "saturation": agg("saturation"), "spread": agg("spread"), "edge": agg("edge"), "detail": agg("detail"),
             "flat": {k: float(np.mean([m["flat"][k] for m in fm])) for k in fm[0]["flat"]},
             "largest_area": agg("largest_area"), "largest_box": agg("largest_box")}

    # sheets (judge) and windows
    (out / "sheets").mkdir(exist_ok=True)
    (out / "windows").mkdir(exist_ok=True)
    for p in list((out / "sheets").glob("*.jpg")) + list((out / "windows").glob("*.jpg")):
        p.unlink()
    tiles = []
    for k, (i, t, _, im) in enumerate(samples):
        tiles.append(stamp(im.copy(), f"#{k + 1:03d}  {t:5.2f}s", 13))
    sheet_files = []
    for s in range(0, len(tiles), 16):
        g = grid(tiles[s:s + 16], 4, FW, FH)
        fn = out / "sheets" / f"sheet-{s // 16 + 1:02d}.jpg"
        g.save(fn, quality=88)
        sheet_files.append(fn)
    win_files = []
    for k, c in enumerate(changes):
        a0, b0 = max(0, c["first"] - WINDOW_SIDE), min(n - 1, c["last"] + WINDOW_SIDE)
        ims = window_frames(film, a0, b0)
        ims = [stamp(im, f"f{a0 + j} {(a0 + j) / fps:5.2f}s", 12) for j, im in enumerate(ims)]
        g = grid(ims, 6, 320, 180, 2)
        fn = out / "windows" / f"change-{k + 1:02d}.jpg"
        g.save(fn, quality=88)
        win_files.append(fn)
    if a.judge:
        jd = Path(a.judge)
        jd.mkdir(parents=True, exist_ok=True)
        for p in jd.glob("*.jpg"):
            p.unlink()
        for fn in sheet_files:
            shutil.copy(fn, jd / fn.name)
        for fn in win_files:
            shutil.copy(fn, jd / f"window-{fn.name}")

    # curves picture
    W, H = 1600, 520
    cv = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(cv)
    f12 = font(12)
    top = 20
    hgt = 220
    mx = max(8.0, float(d.max()))
    sx = lambda t: 40 + (W - 60) * t / dur
    for c in changes:
        dr.rectangle([sx(c["t0"]), top, sx(c["t1"]), top + hgt * 2 + 40], fill=(255, 225, 225))
    for w in ws:
        dr.rectangle([sx(w["t0"]), top + hgt + 30, sx(w["t1"]), top + hgt + 36], fill=(150, 150, 220))
    y = lambda v: top + hgt - hgt * min(v, mx) / mx
    dr.line([(sx(i / fps), y(v)) for i, v in enumerate(d)], fill=(0, 0, 0), width=1)
    dr.line([(40, y(MOVE)), (W - 20, y(MOVE))], fill=(0, 150, 0))
    dr.text((44, top), f"frame-to-frame change (mean abs luma, 320x180), max {d.max():.1f}; green line = {MOVE}", fill=(0, 0, 0), font=f12)
    if snd:
        c2 = snd["curve_db_half_s"]
        ya = lambda v: top + hgt * 2 + 40 - hgt * (max(v, -60) + 60) / 60
        pts = [(sx(i * 0.5 + 0.25), ya(v)) for i, v in enumerate(c2) if v is not None]
        dr.line(pts, fill=(200, 80, 0), width=2)
        for t in onsets:
            dr.line([(sx(t), top + hgt * 2 + 40), (sx(t), top + hgt * 2 + 30)], fill=(200, 80, 0))
        dr.text((44, top + hgt + 44), "loudness dBFS per 0.5 s (0 top, -60 bottom); ticks = onsets; blue = words; pink = scene changes", fill=(0, 0, 0), font=f12)
    for t in range(int(dur) + 1):
        dr.text((sx(t) - 4, H - 16), str(t), fill=(0, 0, 0), font=f12)
    cv.save(out / "curves.png")

    import measure as measure_py
    import see as see_py
    res = {"film": str(film), "probe": info, "versions": measure_versions(measure_py, see_py),
           "A_time": {"length_s": dur, "scene_changes": changes, "shots": len(shots), "shot_len_median": float(np.median(shot_lens)),
                      "shot_len_min": float(min(shot_lens)), "shot_len_max": float(max(shot_lens)),
                      # not transcribed: the word measures are unknown (None, left out of every gap table), never zero
                      "changes_during_voice": None if unknown else len(voiced), "changes_in_sentence_gap": None if unknown else in_gap,
                      "sentence_gaps": None if unknown else sgaps, "words": None if unknown else len(ws),
                      "words_per_s": len(ws) / (ws[-1]["t1"] - ws[0]["t0"]) if len(ws) > 1 else None},
           "C_sync": {"events": events, "onsets": onsets, "tolerance_s": tol, "hits": hits, "rate": near(events), "chance": chance,
                      "by_tolerance": sync_sens, "by_large_threshold": large_sens,
                      "product_measure_py": {"rate": vd["summary"]["sync_rate"], "chance": vd["summary"]["sync_chance"], "tolerance_s": 0.05}},
           "D_motion": {"still_share": still, "moves": moves, "move_count": len(moves),
                        "move_len_median": float(np.median([m["len"] for m in moves])) if moves else None,
                        "large_moves": sum(m["peak"] >= LARGE_MOVE for m in moves), "camera": cam, "camera_moves": cam_moves,
                        "see_census": see["census"], "measure_py": vd["summary"], "diff_curve": [round(v, 3) for v in diffs]},
           "E_sound": dict(snd or {}, onsets=len(onsets), onsets_per_s=onset_rate, tempo=vd["sound"].get("tempo") if vd.get("sound") else None),
           "F_frame": frame, "F_samples": [{"i": s[0], "t": round(s[1], 3), **s[2]} for s in samples], "words": ws, "voice": heard}
    (out / "measures.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

    A, C, D, E, F = res["A_time"], res["C_sync"], res["D_motion"], res["E_sound"], res["F_frame"]
    L = [f"# {film.name}", "", f"{dur:.2f} s, {fps:g} fps, " + (f"words {heard}." if unknown else f"{len(ws)} words heard ({heard})."), "",
         "## A. Time", f"- shots {A['shots']}; length median {num(A['shot_len_median'], '.2f')} s, shortest {num(A['shot_len_min'], '.2f')}, longest {num(A['shot_len_max'], '.2f')}",
         f"- scene changes during the voice: {A['changes_during_voice']}, of them in a gap between sentences: {A['changes_in_sentence_gap']}"]
    for c in changes:
        L.append(f"  - {c['t0']:.2f}-{c['t1']:.2f} s ({c['kind']}, frames {c['first']}-{c['last']}): {c['voice']}" + (f" (word \"{c['under_word']}\")" if c.get("under_word") else ""))
    L += ["", "## C. Sync", f"- {len(events)} picture events, {len(hits)} within {SYNC_FRAMES} frames of an onset: {C['rate']} against {C['chance']:.3f} by chance" if C["rate"] is not None else "- no events or onsets",
          f"- by tolerance (hit, chance): {sync_sens}", f"- by large-move threshold: {large_sens}", f"- product measure.py (0.05 s, its own events): {C['product_measure_py']}",
          "", "## D. Motion", f"- still share (diff < 0.2 / {MOVE} / 0.7): {still}", f"- moves {len(moves)} (median {D['move_len_median']} s), large {D['large_moves']}, camera moves (see.py) {cam_moves}: {cam}",
          f"- see.py census: {see['census']}", "", "## E. Sound"]
    if snd:
        L += [f"- integrated {E['lufs_i']} LUFS, LRA {E['lra']}", f"- words {num(E['word_db'], '.1f')} dBFS, gaps {num(E['gap_db'], '.1f')} dBFS ({E['gap_seconds']} s of gaps), gap floor {num(E['gap_floor_db'], '.1f')}, head {E['head_db']} ({E['head_seconds']} s), tail {E['tail_db']} ({E['tail_seconds']} s)",
              f"- onsets {len(onsets)} ({onset_rate:.2f}/s), tempo {E['tempo']}", f"- curve: {E['curve_db_half_s']}"]
    L += ["", "## F. Frame", f"- {json.dumps(F)}"]
    (out / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
