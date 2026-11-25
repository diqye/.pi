#!/usr/bin/env python3
"""`vd evolve` (not proven on a film): four world sketches, one after each worked film, packed as a blind line-up
(tournament/A..D) for readers, and the chosen one copied into the film folder with --select.

  python evolve.py NAME [--brief TEXT] [--for REPO_DIR] [--against REF.mp4] [--select LETTER | --readings READINGS.md] [--render]
"""
import argparse
import json
import re
import secrets
import shutil
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

ARCHETYPES = (
    (
        "plusone",
        "The world is the subject + Case studies + Point of view",
        "Tactile cards dressed in real archival/museum material; the camera leaves the host once for the receiver's view.",
        {
            "far_thing": "An exhibition catalogue and a handwritten RSVP card on warm archival paper",
            "one_idea": "One tactile object stays in the middle of the frame from the first question until it is answered by a person",
            "boundary": "carried -> door (host to receiver) -> becomes mark",
            "display_face": "Fraunces (display serif, <= 3 words per card, -0.04em) + Geist (interface sans)",
            "bpm": 112.5,
            "fb": 32,
        },
    ),
    (
        "stet",
        "Parallels + One thing carries through + A colour is a noun",
        "Snap-and-hold technical proof: the broken state and the fixed state rhyme in the same panel; one accent colour means one fault.",
        {
            "far_thing": "A typesetter's proof galley where a single vermilion mark holds a line from flipping",
            "one_idea": "One row of the real interface is carried from the failing state through the mechanism to the verified proof",
            "boundary": "matched (broken vs fixed in the same frame) -> carried -> becomes mark",
            "display_face": "Geist 700 (-0.03em, 156 px over 60 px) + Geist Mono (+0.12em small caps)",
            "bpm": 150.0,
            "fb": 24,
        },
    ),
    (
        "onoma",
        "The word does what it says + Things become things + Hold the result back",
        "Kinetic typography: each typed word physically disintegrates into the phenomenon it names before the interface appears.",
        {
            "far_thing": "Concrete poetry on a dark soundstage where every typed noun turns into its physical waveform",
            "one_idea": "A single typed prompt bar spans the frame; each word comes apart into the thing it names before all parts play together",
            "boundary": "becomes (word -> physical phenomenon) -> change of ground -> becomes mark",
            "display_face": "Geist 700 (200 px over 58 px, word-by-word arrival on beat) + Geist Mono",
            "bpm": 120.0,
            "fb": 30,
        },
    ),
    (
        "linden",
        "The turn of scale + Two rooms, one door + The answered opening",
        "One continuous outward camera move through nested worlds seated in SLOTS, with subframe shutter motion blur and no hard cut.",
        {
            "far_thing": "Powers of Ten inside an archive: one slip of paper nested inside a book, a shelf, a reading room, and the city",
            "one_idea": "One continuous camera backs out through five nested frames (`SLOTS`) without a single hard cut, answering the opening at macro scale",
            "boundary": "door (continuous nested scale pullback) -> answered opening on the mark",
            "display_face": "Grotesque 140 px over serif italic 80 px + mono call numbers (+0.14em)",
            "bpm": 100.0,
            "fb": 36,
        },
    ),
)


def write_candidate_board(cand_dir: Path, like: str, moves_title: str, constraint: str, meta: dict, subject: str, repo_info: dict = None):
    """Write a complete 15-section BOARD.md following skills/video-decompiler/BOARD.md."""
    facts = (
        f"{repo_info['total_code_files']} code files, {repo_info['functions']} functions, {repo_info['tests']} tests ({repo_info['lines_of_code']} LOC)"
        if repo_info else f"Concrete workflow and verified numbers for {subject}"
    )
    tagline = repo_info["tagline"] if repo_info and repo_info.get("tagline") else f"{subject} shown through its real workflow and proof"
    board = [
        f"# Board: {subject} ({like} archetype)",
        "",
        "## One sentence",
        f"You see the trouble {subject} solves in one concrete item, watch the mechanism transform it on beat, and see the verified result come back.",
        "",
        "## The product, and the claim",
        f"- **Product:** {subject} — {tagline}.",
        f"- **True facts on screen:** {facts}.",
        "",
        "## What the film is held against",
        f"Held against the worked film `{like}` (`library/films/{like}`) and the pinned reference in `REFERENCE.md`. Keeps everything a viewer of this kind expects: the trouble in their own terms first, the product doing its job large one piece at a time, proof with true numbers, and the mark at the end.",
        "",
        "## The world",
        f"- **The line (subject x far thing):** {subject} crossed with *{meta['far_thing']}*.",
        f"- **Orthogonal WORLD.md moves:** {moves_title}.",
        f"- **World rule:** {constraint}",
        "",
        "## The one idea",
        f"{meta['one_idea']}.",
        "",
        "## The cast",
        "- **Hero object:** The one central card/row/word carried through every scene.",
        "- **Accent noun:** One high-chroma accent colour reserved strictly for the active change or fault.",
        f"- **Faces of type:** {meta['display_face']}.",
        "",
        "## Type",
        f"- Display type follows `{like}`: one display size per held frame, next tier at half size or less, tight tracking (-0.03 to -0.05em), and 4.5:1+ WCAG contrast verified against rendered pixels.",
        "",
        "## The clock",
        f"- `{meta['bpm']} BPM` (`{meta['fb']} frames/beat` at 60 fps). Every cut, camera move and word arrival lands on `kit/times.gen.ts`.",
        "",
        "## The beats",
        "| beats | part | words | picture | why it follows | how it hands to the next |",
        "|---|---|---|---|---|---|",
        f"| 0..8 | Opening trouble | The concrete problem | Close framing on the unfixed state | Starts in the viewer's own trouble | {meta['boundary'].split('->')[0].strip()} |",
        f"| 8..24 | Turn & mechanism | One action | The hero element transforms on beat | Answers the opening trouble | {meta['boundary']} |",
        "| 24..44 | Proof | True count / result | Receiver or proof panel at full scale | Proves the claim with real numbers | carried |",
        "| 44..56 | Answered opening | Name + one line | Returns to the opening question, resolved into the mark | Closes the loop | becomes |",
        "",
        "## The turn",
        "At beat 16 (hinge), the trouble state locks into the mechanism and the music opens into the full pattern.",
        "",
        "## Ties",
        "| what | first | returns | what the return means |",
        "|---|---|---|---|",
        "| Opening item | beat 0 (unsolved) | beat 44 (answered) | The exact trouble from frame 0 is now settled |",
        "",
        "## Gifts",
        "1. Beat 14: secondary motion with a sound on each contact.",
        "2. Beat 36: subtle environmental response in the ground colour as the proof locks.",
        "",
        "## Framings",
        "Macro opening (0..10 s) -> Mechanism close-up (10..20 s) -> Receiver/proof view (20..26 s) -> Resolved mark (26..30 s). None held over a third of the film.",
        "",
        "## Rules of this film",
        "- Moves take 10 to 20 frames (1/6 to 1/3 s) decelerating into rest; no text ever crosses a busy photograph below 4.5:1 WCAG contrast; no cut jumps the eye across the frame without something carried over it.",
        "",
        "## Hardest shot",
        "Beat 16..24 (14.0 s): the multi-layer handoff where the hero element transforms while the camera re-frames.",
        "",
        "## Sound",
        f"`sound.py` generates the {meta['bpm']} BPM score and `kit/times.gen.ts`; contacts get their own sounds in it.",
        "",
        "## Sources and licences",
        "Shipped OFL fonts (`library/media/fonts`) and verified CC0/public-domain art plates (`media/`).",
    ]
    (cand_dir / "BOARD.md").write_text("\n".join(board) + "\n", encoding="utf-8")
    siblings = [m["far_thing"] for lk, _, _, m in ARCHETYPES if lk != like]
    author_brief = [
        f"# Subagent Author Brief — Candidate `{like}` (`{cand_dir.name}`)",
        "",
        f"You are one of four isolated creative directors competing in a double-blind `WORLD.md` tournament for **{subject}**.",
        f"- **Your locked archetype:** `{like}` ({moves_title})",
        f"- **Your world line (subject x far thing):** {subject} crossed with *{meta['far_thing']}*.",
        f"- **Your clock:** `{meta['bpm']} BPM` (`{meta['fb']} frames/beat` at 60 fps).",
        f"- **Your display typography:** {meta['display_face']}.",
        "- **Anti-convergence constraint (forbidden sibling metaphors):** Do NOT stage any of these sibling concepts:",
        *[f"  - Forbidden: {s}" for s in siblings],
        "",
        "## Deliverable in this folder",
        "1. Replace `BOARD.md` with your concrete, product-specific 15-section board (no boilerplate).",
        "2. Update `sound.py` and run `python sound.py` so `kit/times.gen.ts` reflects your beat table.",
        "3. Stage your Opening (2.0 s), Hardest Shot (14.0 s), and Answered Opening (26.0 s) in `film.tsx` and verify `vd look --at 2,14,26` reports zero `!! FAULT` lines.",
    ]
    (cand_dir / "AUTHOR-BRIEF.md").write_text("\n".join(author_brief) + "\n", encoding="utf-8")


def make_placeholder_sheet(cand_dir: Path, like: str, subject: str, out_jpg: Path):
    """Draw a structurally distinct, high-contrast 3-moment world sheet (Opening, Hardest Shot, Answered Opening)
    reflecting each archetype's actual spatial topology, palette, BPM clock and `BOARD.md` claims when `--render` is off."""
    from PIL import Image, ImageDraw, ImageFont
    palettes = {
        "plusone": ((244, 238, 226), (22, 20, 18), (198, 62, 42), (228, 220, 204)),
        "stet": ((16, 19, 24), (240, 244, 248), (224, 68, 44), (28, 33, 42)),
        "onoma": ((12, 14, 20), (242, 238, 230), (76, 138, 248), (24, 28, 38)),
        "linden": ((24, 52, 112), (246, 240, 224), (228, 172, 40), (36, 70, 140)),
    }
    bg, ink, acc, surf = palettes.get(like, palettes["plusone"])
    meta = next((m for lk, _, _, m in ARCHETYPES if lk == like), ARCHETYPES[0][3])
    W, H, strip = 640, 360, 28
    img = Image.new("RGB", (W * 3, H + strip), (14, 14, 16))
    d = ImageDraw.Draw(img)
    font_small = font_title = font_body = ImageFont.load_default()
    ttf_candidates = list((cand_dir / "media").rglob("*.ttf")) + list((TOOLS.parent / "library").rglob("*.ttf"))
    if ttf_candidates:
        try:
            font_title = ImageFont.truetype(str(ttf_candidates[0]), 26)
            font_body = ImageFont.truetype(str(ttf_candidates[0]), 15)
            font_small = ImageFont.truetype(str(ttf_candidates[0]), 13)
        except Exception:
            pass

    short_subj = str(subject).strip().splitlines()[0][:30]
    beats_spec = {
        "plusone": [("02.00s  OPENING", f"{short_subj}: tactile card", "Archival ground"), ("14.00s  CAROUSEL TURN", "Swapped in one handoff", "Host -> Receiver"), ("26.00s  ANSWERED", "Replies lock into mark", f"{meta['bpm']} BPM")],
        "stet": [("02.00s  FAILING STATE", f"{short_subj}: fault row", "Vermilion noun"), ("14.00s  PARALLEL PROOF", "Before vs Fixed in place", "Snap-and-hold"), ("26.00s  VERIFIED", "Zero flakes · Mark", f"{meta['bpm']} BPM")],
        "onoma": [("02.00s  TYPED PROMPT", f"> {short_subj}", "Word -> phenomenon"), ("14.00s  DISINTEGRATION", "Letters split into wave", "Kinetic stage"), ("26.00s  SYNTHESIS", "All tracks play as one", f"{meta['bpm']} BPM")],
        "linden": [("02.00s  MACRO SLIP", f"Item 01 · {short_subj}", "Slot 1 (1.0x)"), ("14.00s  NESTED PULLBACK", "Shelf -> Room -> Archive", "No hard cuts"), ("26.00s  POWERS OF TEN", "Whole system in view", f"{meta['bpm']} BPM")],
    }[like]
    for k, (lab, headline, subline) in enumerate(beats_spec):
        x0 = k * W
        d.rectangle([x0, 0, x0 + W - 1, strip - 1], fill=(10, 10, 12))
        d.text((x0 + 10, 6), lab, fill=(248, 216, 72), font=font_small)
        d.rectangle([x0, strip, x0 + W - 1, strip + H - 1], fill=bg)
        cx, cy = int(x0 + W * 0.5), int(strip + H * 0.50)
        if like == "stet" and k == 1:
            # Split parallel panels (broken vs fixed)
            for side, col_b in ((-1, acc), (1, ink)):
                bx = cx + side * 145
                d.rounded_rectangle([bx - 125, cy - 92, bx + 125, cy + 92], radius=10, fill=surf, outline=col_b, width=3)
            d.text((cx - 250, cy - 18), headline[:24], fill=ink, font=font_title)
            d.text((cx + 35, cy + 20), subline, fill=ink, font=font_body)
        elif like == "linden":
            # Concentric nested Powers-of-Ten slots
            for ring_i in range(3 - k + 1):
                rw, rh = int(W * (0.76 - ring_i * 0.14)), int(H * (0.72 - ring_i * 0.13))
                d.rectangle([cx - rw // 2, cy - rh // 2, cx + rw // 2, cy + rh // 2], fill=surf if ring_i == (3 - k) else None, outline=acc if ring_i == (3 - k) else ink, width=2)
            d.text((cx - 130, cy - 16), headline[:24], fill=ink, font=font_title)
            d.text((cx - 130, cy + 22), subline, fill=ink, font=font_body)
        elif like == "onoma":
            # Full-width prompt / waveform bars
            d.rounded_rectangle([x0 + 48, cy - 68, x0 + W - 48, cy + 68], radius=8, fill=surf, outline=acc if k == 1 else ink, width=3)
            for bar_i in range(12):
                bh = 10 + ((bar_i * 7 + k * 5) % 24)
                bx = x0 + 72 + bar_i * 42
                d.rectangle([bx, cy + 34 - bh, bx + 18, cy + 34], fill=acc)
            d.text((x0 + 68, cy - 46), headline[:28], fill=ink, font=font_title)
        else:
            # Tactile centered hero card + side companion cards
            if k == 1:
                d.rounded_rectangle([x0 + 24, cy - 70, x0 + 110, cy + 70], radius=10, fill=surf, outline=ink, width=2)
                d.rounded_rectangle([x0 + W - 110, cy - 70, x0 + W - 24, cy + 70], radius=10, fill=surf, outline=ink, width=2)
            card_w, card_h = int(W * 0.62), int(H * 0.56)
            d.rounded_rectangle([cx - card_w // 2, cy - card_h // 2, cx + card_w // 2, cy + card_h // 2], radius=14, fill=surf, outline=acc if k == 1 else ink, width=3)
            d.rounded_rectangle([cx - card_w // 2 + 20, cy - card_h // 2 + 18, cx - card_w // 2 + 128, cy - card_h // 2 + 44], radius=6, fill=acc)
            d.text((cx - card_w // 2 + 22, cy - 10), headline[:26], fill=ink, font=font_title)
            d.text((cx - card_w // 2 + 22, cy + 30), subline, fill=ink, font=font_body)
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_jpg, quality=92)
    return out_jpg


def evaluate_sheet_perceptual(sheet_jpg: Path):
    """`look.py`'s Weber contrast and Sobel edge crowding over a candidate sheet, and the ratio between its darkest and
    brightest tones (1st and 99th percentile luminance). That ratio is the sheet's tonal range, not text against its
    ground: a sheet can span 21:1 with pale text on white, so nothing here says the sheet's words can be read."""
    import look
    from PIL import Image
    rgb = np.asarray(Image.open(sheet_jpg).convert("RGB"))
    weber, crowding, L = look.weber_contrast_map(rgb)
    p10, p90 = float(np.percentile(L, 1)), float(np.percentile(L, 99))
    span = float(look.wcag_contrast_ratio(p90, p10))
    return {
        "range_ratio": round(span, 2),
        "weber_p95": round(float(np.percentile(np.abs(weber), 95)), 3),
        "edge_crowding_mean": round(float(np.mean(crowding)), 4),
    }


def measure_divergence(made_cands):
    """Verify genuine multi-concept divergence across the 4 candidates: pairwise lexical Jaccard distance of `BOARD.md`,
    luminance histogram L1 distance across the 4 world sheets, and clock tempo spread."""
    from PIL import Image
    token_sets = []
    hists = []
    bpms = []
    for like, cdir, sheet_jpg, _moves, _metrics in made_cands:
        words = set(re.findall(r"[a-z]{4,}", (cdir / "BOARD.md").read_text(encoding="utf-8", errors="replace").lower()))
        token_sets.append(words)
        gray = np.asarray(Image.open(sheet_jpg).convert("L"), dtype=np.float32) / 255.0
        h, _ = np.histogram(gray, bins=16, range=(0.0, 1.0), density=True)
        hists.append(h / max(float(h.sum()), 1e-9))
        meta = next((m for lk, _, _, m in ARCHETYPES if lk == like), ARCHETYPES[0][3])
        bpms.append(float(meta["bpm"]))
    jaccards, l1s = [], []
    for i in range(len(made_cands)):
        for j in range(i + 1, len(made_cands)):
            union = len(token_sets[i] | token_sets[j])
            jaccards.append(1.0 - (len(token_sets[i] & token_sets[j]) / max(1, union)))
            l1s.append(float(np.abs(hists[i] - hists[j]).sum() * 0.5))
    return {
        "pairwise_board_jaccard_mean": round(float(np.mean(jaccards)) if jaccards else 0.0, 3),
        "pairwise_sheet_hist_l1_mean": round(float(np.mean(l1s)) if l1s else 0.0, 3),
        "bpm_spread": round(max(bpms) - min(bpms), 2) if bpms else 0.0,
        "divergent": bool((np.mean(jaccards) if jaccards else 0.0) >= 0.20 and (np.mean(l1s) if l1s else 0.0) >= 0.25),
    }


def build_tournament(name: str, brief: str = None, repo_dir: Path = None, against: Path = None, render: bool = False, reads_root: Path = None, seed: int = None):
    """Spawn 4 orthogonal candidates, evaluate their perceptual & divergence metrics, pack their 3-moment world sheets under
    dealt letters A..D in a neutral reads folder, and write the tournament key and two cross-family reader briefs."""
    import lean
    import pack
    import borrow
    root = Path(name).resolve()
    out_root = lean.outdir(root)
    n_tourn = 1
    while (out_root / f"evolve-{n_tourn}-KEY.txt").exists():
        n_tourn += 1
    # each tournament's sketches are its own, under the film's output folder: kept in the film folder and reused, a
    # second run wrote over boards an author had worked on, and the film folder held a candidates/ folder (TRAPS.md)
    cands_root = out_root / "tournaments" / f"t{n_tourn}"
    cands_root.mkdir(parents=True, exist_ok=True)
    import puppet  # one record of a repository's facts: puppet's, which adds the counts the boards print to borrow's
    repo_info = puppet.analyze_codebase(Path(repo_dir)) if repo_dir and Path(repo_dir).is_dir() else None
    subject = brief or (repo_info["name"] if repo_info else root.name)

    made_cands = []
    for idx, (like, moves_title, constraint, meta) in enumerate(ARCHETYPES, 1):
        cdir = cands_root / f"v{idx}-{like}"
        if not (cdir / "score.json").is_file():
            class NewArgs:
                pass
            na = NewArgs()
            na.name = str(cdir)
            na.like = like
            na.kind = None
            na.bare = False
            lean.cmd_new(na)
        write_candidate_board(cdir, like, moves_title, constraint, meta, subject, repo_info=repo_info)
        sheet_jpg = lean.outdir(cdir) / "look.jpg"
        if render:
            lean.main(["look", "--at", "2,14,26", "--film", str(cdir), "-o", str(sheet_jpg)])
        else:
            make_placeholder_sheet(cdir, like, subject, sheet_jpg)
        metrics = evaluate_sheet_perceptual(sheet_jpg)
        made_cands.append((like, cdir, sheet_jpg, moves_title, metrics))

    div_metrics = measure_divergence(made_cands)
    # the four sketches are always made in the same order, so a deal seeded by the tournament's number (as pack.deal is,
    # for line-ups of films) would be the same on every machine and readable from this code: the letters are drawn at
    # random instead, and the key file records them. `seed` fixes them for a test.
    dealt = pack.deal(seed, 4) if seed is not None else secrets.SystemRandom().sample(list(pack.LETTERS[:4]), 4)
    reads_base = Path(reads_root or pack.READS)
    pack_dir = reads_base / secrets.token_hex(6)
    while pack_dir.exists():
        pack_dir = reads_base / secrets.token_hex(6)
    tourn_dir = pack_dir / "tournament"
    mapping = {}
    for letter, (like, cdir, sheet_jpg, moves_title, metrics) in zip(dealt, made_cands):
        slot = tourn_dir / letter
        slot.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sheet_jpg, slot / "world-sheet.jpg")
        (slot / "perceptual-metrics.json").write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
        board_text = (cdir / "BOARD.md").read_text(encoding="utf-8")
        redacted_lines = []
        for l in board_text.splitlines():
            if l.startswith("# Board:") or l.startswith("- **Starter grammar:**"):
                continue
            # Redact archetype and folder names so blind readers judge pure visual/narrative form
            clean_l = re.sub(r"\b(plusone|stet|onoma|linden|" + re.escape(root.name) + r")\b", "CANDIDATE", l, flags=re.I)
            redacted_lines.append(clean_l)
        (slot / "BOARD-BLIND.md").write_text(f"# Candidate {letter}\n\n" + "\n".join(redacted_lines) + "\n", encoding="utf-8")
        mapping[letter] = {
            "archetype": like,
            "dir": str(cdir),
            "moves": moves_title,
            "sheet": str(sheet_jpg),
            "metrics": metrics,
            "fingerprint": fingerprint(cdir),
        }

    (out_root / f"evolve-{n_tourn}-divergence.json").write_text(json.dumps(div_metrics, indent=1) + "\n", encoding="utf-8")
    key_path = out_root / f"evolve-{n_tourn}-KEY.txt"
    key_lines = [
        f"evolve-{n_tourn}, 4-way WORLD.md tournament for {root.name}",
        f"the blind tournament pack: {tourn_dir}",
        f"divergence: board Jaccard {div_metrics['pairwise_board_jaccard_mean']}, sheet L1 {div_metrics['pairwise_sheet_hist_l1_mean']}, BPM spread {div_metrics['bpm_spread']}",
    ]
    for letter in sorted(mapping):
        m = mapping[letter]
        key_lines.append(
            f"tournament/{letter} = {m['archetype']} ({m['dir']}): {m['moves']} "
            f"[tonal range {m['metrics']['range_ratio']}:1, crowding {m['metrics']['edge_crowding_mean']}] fingerprint {m['fingerprint']}"
        )
    key_path.write_text("\n".join(key_lines) + "\n", encoding="utf-8")

    brief_path = out_root / f"evolve-{n_tourn}-BRIEF.md"
    brief_text = (
        "# Evolutionary Tournament Jury Brief (`vd evolve`)\n\n"
        f"> You are judging 4 competing visual-world sketches in `{tourn_dir}` (`A`, `B`, `C`, `D`).\n"
        "> Each folder holds `world-sheet.jpg` (3 moments: Opening, Hardest Shot, Answered Opening), `BOARD-BLIND.md`, and `perceptual-metrics.json`.\n"
        "> Apply the four tests from `WORLD.md` and `EYES.md`:\n"
        "> 1. Does the motion/world belong to the subject rather than generic decoration?\n"
        "> 2. Could a cold viewer name the visual metaphor and what the accent colour means?\n"
        "> 3. Is the product's proof shown large, a piece at a time, with >= 4.5:1 WCAG contrast?\n"
        "> 4. Does the ending answer the opening?\n"
        "> Start your response with `RANKING: X > Y > Z > W` (best first), kill the bottom 3, and name one mutation for the winner.\n"
    )
    brief_path.write_text(brief_text, encoding="utf-8")
    return tourn_dir, key_path, brief_path, mapping


def fingerprint(folder: Path):
    """A hash of every file in a candidate, by path and content: --select promotes only what the readers saw."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted(p for p in Path(folder).rglob("*") if p.is_file()):
        h.update(f.relative_to(folder).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def parse_winner_from_readings(readings_path: Path, mapping: dict = None):
    """Parse one or more blind reader rankings (`RANKING: B > A > D > C` or `1. B · 2. A ...`) from a markdown file
    and return the Borda-count consensus winning letter (`A`, `B`, `C`, or `D`), breaking ties by the sheet's tonal range."""
    text = Path(readings_path).read_text(encoding="utf-8", errors="replace")
    scores = {ltr: 0 for ltr in ("A", "B", "C", "D")}
    found_any = False
    for m in re.finditer(r"RANKING:\s*([A-D])\s*>\s*([A-D])\s*>\s*([A-D])(?:\s*>\s*([A-D]))?", text, re.I):
        found_any = True
        letters = [g.upper() for g in m.groups() if g]
        for pts, ltr in zip((4, 3, 2, 1), letters):
            scores[ltr] = scores.get(ltr, 0) + pts
    if not found_any:
        for m in re.finditer(r"\b1\.\s*\**([A-D])\b.*?\b2\.\s*\**([A-D])\b.*?\b3\.\s*\**([A-D])\b", text, re.S):
            found_any = True
            for pts, ltr in zip((4, 3, 2), (m.group(1).upper(), m.group(2).upper(), m.group(3).upper())):
                scores[ltr] = scores.get(ltr, 0) + pts
    if not found_any:
        raise ValueError(f"no `RANKING: A > B > C > D` or `1. A ... 2. B ...` lines found in {readings_path}")
    return max(
        scores.keys(),
        key=lambda k: (scores[k], ((mapping or {}).get(k, {}).get("metrics", {}).get("range_ratio", 0.0))),
    )


def select_winner(root: Path, letter: str = None, against: Path = None, readings: Path = None, key_file: Path = None):
    """Promote the winning candidate (`A`, `B`, `C`, or `D`, or parsed from `readings`) from `key_file` or the latest
    `evolve-N-KEY.txt` into `root`, and optionally fit `against`'s moves and colours with vd borrow."""
    import lean
    import borrow
    root = Path(root).resolve()
    out_root = lean.outdir(root)
    if key_file and Path(key_file).is_file():
        chosen_key_file = Path(key_file)
    else:
        keys = sorted(out_root.glob("evolve-*-KEY.txt"), key=lambda p: int(p.stem.split("-")[1]))
        if not keys:
            raise SystemExit(f"no evolve-N-KEY.txt found in {out_root}: run `vd evolve {root.name}` first")
        chosen_key_file = keys[-1]
    latest_key = chosen_key_file.read_text(encoding="utf-8")
    if readings and not letter:
        # the documented tie-break, the sheets' tonal range, read back from the key (it was called with no mapping)
        mapping = {m.group(1): {"metrics": {"range_ratio": float(m.group(2))}}
                   for m in re.finditer(r"^tournament/([A-D]) = .*?\[tonal range ([\d.]+):1", latest_key, re.M)}
        letter = parse_winner_from_readings(Path(readings), mapping)
    if not letter:
        raise SystemExit("vd evolve --select needs the letter the person or the readers chose (or --readings READINGS.md): "
                         "no letter is promoted by default")
    letter = letter.strip().upper()
    chosen_dir = None
    chosen_arch = None
    seen = None
    for line in latest_key.splitlines():
        if line.startswith(f"tournament/{letter} = "):
            rest = line.split(" = ", 1)[1]
            chosen_arch = rest.split(" (", 1)[0].strip()
            chosen_dir = Path(rest.split(" (", 1)[1].split("):", 1)[0].strip())
            fp = re.search(r"fingerprint ([0-9a-f]{16})", line)
            seen = fp.group(1) if fp else None
            break
    if not chosen_dir or not chosen_dir.is_dir():
        raise SystemExit(f"letter {letter!r} not found in {chosen_key_file}")
    if seen is None or fingerprint(chosen_dir) != seen:
        # a key promotes what its readers saw: a sketch changed since (or a key from before fingerprints) is not that
        raise SystemExit(f"vd evolve --select: candidate {letter} ({chosen_dir}) is not what its readers saw "
                         f"({'it has changed since' if seen else 'its key has no fingerprint'}). Run vd evolve again and have it read.")
    # what was pinned or borrowed into the film folder before (vd pin's targets, vd borrow's dna) is the film's, not the
    # sketch's: it is kept when the sketch's score.json is copied over
    kept = {}
    if (root / "score.json").is_file():
        old = json.loads((root / "score.json").read_text(encoding="utf-8"))
        kept = {k: old[k] for k in ("pinned", "dna", "targets", "targets_all") if k in old}
    # the film folder becomes the chosen sketch's film: what was in it is moved aside, whole, not mixed in (copied over
    # a worked film, it left that film's .tsx and kit beside the new one's) and not deleted
    root.mkdir(parents=True, exist_ok=True)
    present = [p for p in root.iterdir()]
    if present:
        aside = next(out_root / f"before-select-{n}" for n in range(1, 10000) if not (out_root / f"before-select-{n}").exists())
        aside.mkdir(parents=True)
        for p in present:
            shutil.move(str(p), str(aside / p.name))
    for item in chosen_dir.iterdir():
        dst = root / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    if kept:
        new = json.loads((root / "score.json").read_text(encoding="utf-8"))
        (root / "score.json").write_text(json.dumps({**new, **kept}, indent=1) + "\n", encoding="utf-8")
    (out_root / "EVOLVE-WINNER.json").write_text(
        json.dumps({"letter": letter, "archetype": chosen_arch, "source_dir": str(chosen_dir)}, indent=1) + "\n",
        encoding="utf-8",
    )
    if against and Path(against).is_file():
        borrow.compile_dna_cartridge(Path(against).resolve(), out_dir=root)
    return chosen_arch, chosen_dir


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("name", help="film folder for the tournament")
    ap.add_argument("--brief", help="one-line product brief or subject")
    ap.add_argument("--for", dest="repo", help="optional target repository to ground the 4 candidates")
    ap.add_argument("--against", help="optional reference film to pin and mutate the winner against")
    ap.add_argument("--select", metavar="LETTER", help="promote winning candidate A, B, C, or D into the main film folder")
    ap.add_argument("--readings", metavar="FILE", help="parse blind VLM reader rankings from READINGS.md and promote the winner")
    ap.add_argument("--render", action="store_true", help="render the 3-moment world sheets with raea")
    ap.add_argument("--reads", help="neutral root for blind tournament packs")
    a = ap.parse_args(argv)
    root = Path(a.name).resolve()
    if a.select or a.readings:
        arch, cdir = select_winner(
            root,
            letter=a.select,
            against=Path(a.against) if a.against else None,
            readings=Path(a.readings) if a.readings else None,
        )
        print(f"promoted winner ({arch}, from {cdir}) -> {root}")
        print(root)
        return
    tourn_dir, key_path, brief_path, _ = build_tournament(
        str(root),
        brief=a.brief,
        repo_dir=Path(a.repo) if a.repo else None,
        against=Path(a.against) if a.against else None,
        render=a.render,
        reads_root=Path(a.reads) if a.reads else None,
    )
    print(f"spawned 4 orthogonal WORLD.md candidates in {root / 'candidates'}")
    print(f"the blind tournament pack, to give readers: {tourn_dir}")
    print(f"the jury brief: {brief_path}")
    print(f"the key, never given to readers: {key_path}")
    print(tourn_dir)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
