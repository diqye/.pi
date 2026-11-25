#!/usr/bin/env python3
"""A blind pack for readers: a line-up of up to four films under letters, and our film alone for the fault-finder. The
films this skill is built from were read that way: four films lettered A to D read by two readers, and one fault-finder
reading ours alone with ten every-frame stretches. It grew out of two earlier scripts.

  python pack.py FILM [--against REF.mp4 ...] [--k 5] [--k-alone 10] [--ref-first N --ref-last M] [--keys T1,...] [--out DIR]

What it writes: the pack, a folder under a neutral root (~/.vd/reads/<random>, or --reads) whose path holds no film's
name, since a reader is given that path and a parent folder named after the product unblinds the line-up (one film's folder did);
and its key under OUT (pack-N-KEY.txt, N counts up, one a pack), outside the pack:
  lineup/A ... lineup/D   one folder a film, ours and each --against film (up to three: a reference, a known-good film,
                          an earlier cut), the letters dealt in an order that changes with each pack number and is the same
                          whenever that number is made again (deal); ours never keeps the letter it had in the pack before.
                          Each holds story-01.jpg ... and move-1.jpg ... move-K.jpg (--k, default 5). Made only with --against.
  alone/                  ours alone: story-01.jpg ..., move-1.jpg ... move-K.jpg (--k-alone, default 10), and five keys at
                          full size, key-1-T.png ... key-5-T.png (evenly spaced unless --keys; T is its time in seconds).
  OUT/pack-N-KEY.txt      outside the pack: where the pack is, which letter is which film, each film's stretch times, the keys.

Story: the whole film at two frames a second on sheets of 6 x 4 tiles 400 px wide (the film's own shape), the time on every
tile. Motion: every frame of the one-second stretches where the picture changes most (scan.windows: change
summed over each second, the largest taken, never overlapping), drawn by sheet.py --native, in time
order, the time and frame number on every tile. A reader at four frames a second saw a story and no motion: a stutter or
an ease is only visible frame by frame. --ref-first and --ref-last give only the first N and last M seconds of each
--against film, and its stretches are picked inside them. Each --against film's material is made by this same code and
cached beside its measures (~/.vd/measures/<its hash>-sheets2/reader-...). No film's name is in any file name, text or picture
inside the pack. vd pin gives a reference alone the same material (reader_material).
"""
import argparse
import hashlib
import os
import random
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
W, COLS, ROWS, FPS = 400, 6, 4, 2                # the story: 2 frames a second, 24 tiles a sheet, 400 px tiles
K, MOVE_COLS, MOVE_ROWS, MOVE_W = 5, 8, 8, 320   # the motion: K stretches of one second, every frame, 8 x 8 tiles of 320 px
K_ALONE = 10                                     # the fault-finder reads ours with ten stretches
LETTERS = "ABCD"                                 # a line-up holds ours and up to three --against films
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
PY = sys.executable
READS = Path(os.environ.get("VD_READS") or Path.home() / ".vd" / "reads")   # the neutral root reader packs go under


def trim_words(first, last):
    """" (only its first N s and last M s)" for the ends that were given, "" for none: either alone is allowed."""
    ends = [f"first {first:g} s" if first else "", f"last {last:g} s" if last else ""]
    return f" (only its {' and '.join(e for e in ends if e)})" if first or last else ""


def duration(film):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(film)], capture_output=True, text=True, creationflags=NO_WINDOW)
    try:
        return float(p.stdout.strip())
    except ValueError:
        raise SystemExit(f"{film}: ffprobe could not read its length")


def tile_h(film):
    """A story tile's height: 400 px wide at the film's own shape (225 for 16:9), so a vertical film is not squashed."""
    from film_diff import ffprobe
    v = ffprobe(film)
    return max(1, int(W * v["h"] / v["w"] + 0.5))       # raw RGB frames need no even height


BATCH = 48   # story tiles picked per ffmpeg call: ffmpeg's expression parser refuses a select of about 100 terms
             # (120 failed on a 110 s film), and one command for a whole long film was too long for Windows


def tiles(film, start=0.0, length=None, h=None):
    """(time, picture) at FPS a second from `start`, for `length` seconds (all when None), each the frame on screen at its
    time: the last frame whose own time is at or before it, read from the file's packets. ffmpeg's fps filter picked
    by its own rounding: half a second late centred on each tick (the tile labelled 31.00 s showed 31.167), and with
    round=up still a frame out, and a whole tile late from a start between frames (a pack from 9.008 s showed frame 570
    twice where 540 was on screen; a review's finding). The seek lands on the first frame wanted, as seek_to's do."""
    import numpy as np
    from PIL import Image
    from film_diff import clock, ffprobe
    h = h or tile_h(film)
    times = clock(film)
    end = ffprobe(film)["duration"] if length is None else min(start + length, ffprobe(film)["duration"])
    ticks = [start + k / FPS for k in range(int((end - start) * FPS) + 2) if start + k / FPS < end - 1e-9]
    if not ticks:
        return []
    want = [max(0, int(np.searchsorted(times, t + 1e-6, side="right")) - 1) for t in ticks]
    frames, got = sorted(set(want)), {}
    # in batches, each from its own seek: one select of every tile's frame made a command line too long for Windows on
    # a film over about 21 minutes (a council's finding)
    for b in range(0, len(frames), BATCH):
        part = frames[b:b + BATCH]
        first = part[0]
        ss = 0.0 if first == 0 else float(times[first - 1] + times[first]) / 2      # half way back: the seek lands on `first`
        pick = "+".join(f"eq(n\\,{f - first})" for f in part)
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.6f}", "-i", str(film), "-vf", f"select='{pick}',scale={W}:{h}", "-fps_mode", "passthrough",
               "-frames:v", str(len(part)), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        raw = subprocess.run(cmd, capture_output=True, check=True, creationflags=NO_WINDOW).stdout
        got.update({f: Image.frombytes("RGB", (W, h), raw[k * W * h * 3:(k + 1) * W * h * 3]) for k, f in enumerate(part)
                    if (k + 1) * W * h * 3 <= len(raw)})
    return [(t, got[f]) for t, f in zip(ticks, want) if f in got]


STRIP = 24   # px: the band above each story tile that holds its time, so no stamp covers the picture


def sheets(items, out):
    """Write story-01.jpg ... from (time, picture) tiles, the time in a band above every tile (the stamp on the tile's
    corner covered a film's act lines there, and two readers could not check them). Returns how many sheets."""
    from PIL import Image, ImageDraw, ImageFont
    out.mkdir(parents=True, exist_ok=True)
    font = None
    for face in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(face, 17)
            break
        except OSError:
            pass
    if font is None:
        try:
            font = ImageFont.load_default(17)
        except TypeError:
            font = ImageFont.load_default()
    per = COLS * ROWS
    w, h = items[0][1].size if items else (W, 225)
    for s in range(0, len(items), per):
        sheet = Image.new("RGB", (w * COLS, (h + STRIP) * ROWS), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(items[s:s + per]):
            x, y = (k % COLS) * w, (k // COLS) * (h + STRIP)
            sheet.paste(im, (x, y + STRIP))
            d.rectangle([x, y, x + w - 1, y + STRIP - 1], fill=(0, 0, 0))
            d.text((x + 6, y + 2), f"{t:.2f}s", fill=(255, 255, 255), font=font)
        sheet.save(out / f"story-{s // per + 1:02d}.jpg", quality=90)
    return (len(items) + per - 1) // per


def spans_of(film, first=None, last=None):
    """The stretches of the film a reader is shown: None for all of it, else its first N and last M seconds."""
    if first is None and last is None:
        return None
    dur = duration(film)
    out = [(0.0, first)] if first else []
    if last:
        out.append((max(first or 0.0, dur - last), dur))
    return out


def film_tiles(film, first=None, last=None):
    spans = spans_of(film, first, last)
    if spans is None:
        return tiles(film)
    h = tile_h(film)
    return [t for a, b in spans for t in tiles(film, a, b - a, h)]


def moves(film, out, k=K, spans=None):
    """move-1.jpg ... in time order: every frame of each of the k stretches with the most change (scan.windows), drawn by
    sheet.py --native. Returns the stretches' start times."""
    import scan
    from film_diff import ffprobe
    fps = scan.rate(film)
    dur = ffprobe(film)["duration"]                    # the length sheet.py checks --to against
    starts = scan.windows(film, fps, k, spans=spans)
    out.mkdir(parents=True, exist_ok=True)
    for n, t in enumerate(starts, 1):
        p = subprocess.run([PY, "-X", "utf8", str(TOOLS / "sheet.py"), str(film), "-o", str(out / f"move-{n}.jpg"), "--native", "--from", f"{t:.4f}",
                            "--to", f"{min(t + 1.0, dur):.4f}", "--cols", str(MOVE_COLS), "--rows", str(MOVE_ROWS), "--width", str(MOVE_W)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        if p.returncode:
            raise SystemExit(f"sheet.py could not draw the stretch from {t:.2f} s: {(p.stdout + p.stderr).strip()[-300:]}")
    return starts


def reader_material(film, out, k=K, first=None, last=None):
    """What a reader is given of one film, into `out`: its story sheets and its motion sheets. (story sheets, stretch starts)."""
    n = sheets(film_tiles(film, first, last), out)
    return n, moves(film, out, k, spans_of(film, first, last))


def file_hash(path):
    h = hashlib.sha1()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


SHEETS = 2   # bump when the sheets change, so a set cached the old way is made again (2: each story tile shows the frame at its time)


def sheets_root(ref, cache_root=None):
    """Where a reference's sheets are cached: beside its measures, under this version of the sheets."""
    return Path(cache_root or Path.home() / ".vd" / "measures") / f"{file_hash(ref)}-sheets{SHEETS}"


def ref_sheets(ref, first=None, last=None, cache_root=None, k=K):
    """The reference's story and motion sheets, made once by reader_material and kept beside its measures. Made in a
    folder of its own and moved into place whole, so a run stopped half way is never taken as made."""
    root = sheets_root(ref, cache_root)
    folder = root / f"reader-{first or 'all'}-{last or 'all'}-k{k}"
    if not (folder / "story-01.jpg").exists():
        part = folder.with_name(folder.name + ".part")
        shutil.rmtree(part, ignore_errors=True)
        _, at = reader_material(ref, part, k, first, last)
        # the note is the folder's whole name and ".times": with_suffix cut a trim like 1.5 at its point, so two trims shared one note
        folder.with_name(folder.name + ".times").write_text(" ".join(f"{t:.4f}" for t in at), encoding="utf-8")
        shutil.rmtree(folder, ignore_errors=True)
        part.replace(folder)
    return folder


def keys(film, times, out, name="key-{i}-{t:.2f}s.png", widest=None):
    """One frame at each time, full size (or at most `widest` px wide, the film's own shape). A .jpg carries its time in
    its comment, so a key named key-N.jpg still says when it is."""
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for i, t in enumerate(times, 1):
        f = out / name.format(i=i, t=t)
        scale = ["-vf", f"scale='min({widest},iw)':-2"] if widest else []
        if f.suffix.lower() == ".jpg":
            from io import BytesIO
            from PIL import Image
            png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(film), "-frames:v", "1", *scale, "-f", "image2pipe", "-vcodec", "png", "-"],
                                 capture_output=True, check=True, creationflags=NO_WINDOW).stdout
            Image.open(BytesIO(png)).convert("RGB").save(f, quality=92, comment=f"{t:.2f} s".encode())
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(film), "-frames:v", "1", *scale, str(f)], check=True, creationflags=NO_WINDOW)
        made.append(f)
    return made


def rest_times(film, n=6):
    """n times spread over the film where the picture is at rest: in each nth of it, the middle of its longest quiet
    stretch (changes at or under the quietest third of the film's own changes, or under scan.STILL if that is higher),
    else its quietest frame. The first frame of a busy stretch is the wrong moment to read an interface."""
    import numpy as np
    import scan
    fps = scan.rate(film)
    d = scan.changes(film)
    if not len(d):
        return [0.0]
    calm = d <= max(scan.STILL, float(np.percentile(d, 33)))
    out = []
    for k in range(n):
        a, b = int(len(d) * k / n), max(int(len(d) * (k + 1) / n), int(len(d) * k / n) + 1)
        best, i = None, a
        while i < b:
            if not calm[i]:
                i += 1
                continue
            j = i
            while j < b and calm[j]:
                j += 1
            if best is None or j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        # changes i..j-1 calm: frames i..j stand still; the middle one. With none calm, the frame after the smallest change
        frame = (best[0] + best[1]) // 2 if best else a + int(np.argmin(d[a:b])) + 1
        out.append(round(frame / fps, 3))
    return out


def rest_keys(film, out, n=6, widest=1920):
    """key-1.jpg ... key-n.jpg in `out`: rest_times at full size (at most `widest` wide), each with its time in its comment."""
    for old in Path(out).glob("key-*.jpg"):
        old.unlink()
    return keys(film, rest_times(film, n), Path(out), name="key-{i}.jpg", widest=widest)


def pictures(folder):
    return sorted(Path(folder).glob("*.jpg"))


def deal(n_pack, count, before=None):
    """The letter each film gets in pack n_pack, ours first: a shuffle seeded by the pack number and the number of films,
    so a pack made again gets the same letters; and ours never keeps the letter it had in the pack before (a random pick
    put ours on the same side four packs running, and readers who see several packs learn a fixed place). `before` is
    the letter ours really had in the last pack with a line-up (its key file says), whatever that pack's count: a maker
    who packed against a reference (three films), exported a cut and packed again with the earlier cut too (four) was
    dealt A both times, as the rule was kept only between packs of the same count."""
    order = list(LETTERS[:count])
    prev = None
    for n in range(1, n_pack + 1):
        rng = random.Random(f"pack {n} of {count}")
        order = list(LETTERS[:count])
        rng.shuffle(order)
        avoid = before if n == n_pack and before is not None else (prev[0] if prev else None)
        if avoid is not None and count > 1 and order[0] == avoid:
            j = 1 + rng.randrange(count - 1)
            order[0], order[j] = order[j], order[0]
        prev = order
    return order


def ours_before(out_root, n_pack):
    """The letter ours had in the last pack before n_pack that had a line-up, from its key file, or None."""
    for n in range(n_pack - 1, 0, -1):
        try:
            text = (Path(out_root) / f"pack-{n}-KEY.txt").read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("lineup/") and " = ours" in line:
                return line[len("lineup/"):].split(" ", 1)[0]
    return None


def make(film, against, out_root, ref_first=None, ref_last=None, key_times=None, cache_root=None, k=K, k_alone=K_ALONE, reads_root=None):
    """Write a pack under reads_root (READS) in a folder of its own with a random name, and its key file, pack-N-KEY.txt,
    under out_root. Returns (pack folder, key file, {letter: film}).

    `against`: a film, or a list of up to three (a reference, a known-good film, an earlier cut); none makes alone/ only.
    Each reader gets one folder holding only what it may see (one film's stranger had to be pointed at two subfolders, and
    an eye's folder that held our full-size keys would have unblinded it): lineup/, the films under letters, sheets
    only; alone/, ours with more stretches and its keys. The key file is outside both."""
    film, out_root = Path(film).resolve(), Path(out_root)
    against = [Path(r).resolve() for r in ([against] if isinstance(against, (str, Path)) else list(against or []))]
    if len(against) > len(LETTERS) - 1:
        raise SystemExit(f"a line-up holds {len(LETTERS)} films: ours and up to {len(LETTERS) - 1} --against, not {len(against)}")
    for f in [film, *against]:
        if not f.is_file():
            raise SystemExit(f"no such film: {f}")
    out_root.mkdir(parents=True, exist_ok=True)
    n_pack = 1
    while (out_root / f"pack-{n_pack}-KEY.txt").exists() or (out_root / f"pack-{n_pack}").exists():   # (pack-N: a pack made before packs moved)
        n_pack += 1
    reads_root = Path(reads_root or READS)
    pack = reads_root / secrets.token_hex(6)
    while pack.exists():
        pack = reads_root / secrets.token_hex(6)
    alone = pack / "alone"
    said = [f"pack-{n_pack}"]
    letters = {}
    if against:
        dealt = deal(n_pack, 1 + len(against), ours_before(out_root, n_pack))
        lineup = pack / "lineup"
        n, ours_at = reader_material(film, lineup / dealt[0], k)
        letters[dealt[0]] = (film, "ours", n, ours_at)
        for i, ref in enumerate(against, 1):
            src = ref_sheets(ref, ref_first, ref_last, cache_root, k)
            (lineup / dealt[i]).mkdir(parents=True)
            for f in pictures(src):
                shutil.copy2(f, lineup / dealt[i] / f.name)
            letters[dealt[i]] = (ref, f"--against {i}" + trim_words(ref_first, ref_last),
                                 len(list(src.glob("story-*.jpg"))), stretch_times(src, ref, k, ref_first, ref_last))
    n_alone, alone_at = reader_material(film, alone, k_alone)
    if not key_times:
        dur = duration(film)
        key_times = [round(dur * (i + 0.5) / 5, 2) for i in range(5)]
    keys(film, key_times, alone)
    key = out_root / f"pack-{n_pack}-KEY.txt"
    text = [f"pack-{n_pack}, made from {film.name}" + (f" against {', '.join(r.name for r in against)}" if against else " alone"), f"the pack: {pack}"]
    for letter in sorted(letters):
        f, who, n, at = letters[letter]
        text.append(f"lineup/{letter} = {who}: {f.name} ({f}); {n} story sheet{'s' if n != 1 else ''}; stretches from {', '.join(f'{t:.2f}' for t in at) or 'none'} s")
    text.append(f"alone/ = ours: {n_alone} story sheets; stretches from {', '.join(f'{t:.2f}' for t in alone_at) or 'none'} s; "
                f"keys at {', '.join(f'{t:.2f}' for t in key_times)} s")
    key.write_text("\n".join(text) + "\n", encoding="utf-8")
    if letters:
        said.append(f"the line-up {pack / 'lineup'} (" + ", ".join(f"{l}: {letters[l][2]} story sheet{'s' if letters[l][2] != 1 else ''} and {len(letters[l][3])} stretches" for l in sorted(letters)) + ")")
    said.append(f"ours alone {alone} ({n_alone} story sheet{'s' if n_alone != 1 else ''}, {len(alone_at)} stretches, {len(key_times)} keys)")
    print(f"pack-{n_pack}: " + "; ".join(said[1:]) + ".")
    print(f"the pack, to give readers: {pack}")
    print(f"the key, never given to readers: {key}")
    return pack, key, {l: v[0] for l, v in letters.items()}


def stretch_times(folder, film, k, first=None, last=None):
    """The stretch starts of a cached film's material, for the key file: kept in a note beside its cache folder (outside
    it, so only pictures are copied into a pack), and worked out again by the same rule for a cache made before the note."""
    note = Path(folder).with_name(Path(folder).name + ".times")
    try:
        return [float(t) for t in note.read_text(encoding="utf-8").split()]
    except (OSError, ValueError):
        import scan
        at = scan.windows(film, scan.rate(film), k, spans=spans_of(film, first, last))
        note.write_text(" ".join(f"{t:.4f}" for t in at), encoding="utf-8")
        return at


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("film")
    ap.add_argument("--against", action="append", metavar="REF", help="a film for the line-up beside ours; up to three times (a reference, a known-good "
                    "film, an earlier cut). With none, only alone/ is made")
    ap.add_argument("--k", type=int, default=K, metavar="N", help=f"stretches of motion, every frame, for each film in the line-up (default {K})")
    ap.add_argument("--k-alone", type=int, default=K_ALONE, metavar="N", help=f"stretches of motion for ours alone (default {K_ALONE})")
    ap.add_argument("--ref-first", type=float, help="give only each --against film's first N seconds ...")
    ap.add_argument("--ref-last", type=float, help="... and its last M seconds")
    ap.add_argument("--keys", help="times in seconds for the five full-size keys in alone/ (default five evenly spaced)")
    ap.add_argument("--out", help="where the key, pack-N-KEY.txt, goes (default ~/.vd/out/<film's stem>)")
    ap.add_argument("--reads", help=f"the neutral root the pack goes under (default {READS})")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else Path.home() / ".vd" / "out" / Path(a.film).stem
    make(a.film, a.against or [], out, a.ref_first, a.ref_last, [float(t) for t in a.keys.split(",")] if a.keys else None, k=a.k, k_alone=a.k_alone, reads_root=a.reads)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
