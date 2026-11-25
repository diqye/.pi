#!/usr/bin/env python3
"""`vd bridge` (not proven on a film): the export's cuts for an editor or for legible-film. Writes `cues.json` (the shape
legible-film's cue_list.py reads, bound by stream hash to the exported file), `picture-timing.json`, a Final Cut Pro 7 XML
file (`timeline.xml`) and an OpenTimelineIO file (`timeline.otio`). The XML counts the host in-point into the sequence's
length and the OTIO does not, and the XML always names two sound tracks. No editing program has opened either.

  python bridge.py [--film DIR] [--video HERO.mp4] [-o BridgeDir] [--host-in 0.0]
"""
import argparse
import fractions
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
TICKS_PER_SECOND = 254016000000


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_turned(stream):
    """Whether ffprobe's video stream is shown turned: a display matrix with a rotation, or a rotate tag other than "0"
    (the tag "0", upright, had been read as turned because a non-empty string is true)."""
    rotate_tag = str((stream.get("tags") or {}).get("rotate") or "0").strip()
    return bool(any(sd.get("rotation") for sd in stream.get("side_data_list") or []) or rotate_tag not in ("0", "-0", ""))


def picture_identity_and_schedule(video_path: Path):
    """Compute exact legible-film `cue_list.py` picture identity: packet stream SHA-256, display geometry,
    and microsecond frame presentation schedule (`picture-timing.json`)."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required on PATH")
    p_hash = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(video_path), "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, check=True,
    ).stdout
    m = re.search(r"SHA256=([0-9a-f]{64})", p_hash)
    if not m:
        raise RuntimeError(f"no video stream hash for {video_path}")
    stream_sha = m.group(1)

    streams_out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", str(video_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, check=True,
    ).stdout
    stream = (json.loads(streams_out).get("streams") or [{}])[0]
    w = int(stream.get("width") or 1920)
    h = int(stream.get("height") or 1080)
    cw = int(stream.get("coded_width") or w) or w
    ch = int(stream.get("coded_height") or h) or h
    # The geometry written below is square pixels, upright. A picture that is not would be stale to legible-film's reader
    # the moment it was written, so it is refused here, before anything is.
    sar = stream.get("sample_aspect_ratio") or "1:1"
    turned = is_turned(stream)
    if sar not in ("1:1", "0:1", "N/A") or turned:
        raise SystemExit(f"vd bridge: {Path(video_path).name} has non-square pixels ({sar}) or is turned; the bridge binds only "
                         "square, upright pictures. Export it square (vd export does).")
    geometry = {
        "width": w,
        "height": h,
        "coded_width": cw,
        "coded_height": ch,
        "sar": "1:1",
        "display_width": w,
        "display_height": h,
        "matrix": [1 << 16, 0, 0, 0, 1 << 16, 0, 0, 0, 1 << 30],
        "transform": {"rotate": 0, "hflip": False},
        "crop": None,
    }
    rate = Fraction(60, 1)
    for k in ("r_frame_rate", "avg_frame_rate"):
        try:
            cand = fractions.Fraction(stream.get(k) or "0/0")
            if cand > 0:
                rate = cand
                break
        except (ValueError, ZeroDivisionError):
            pass
    fps_exact = f"{rate.numerator}/{rate.denominator}"
    base = fractions.Fraction(stream.get("time_base") or "1/60")
    pkt_rows = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts,duration,flags", "-of", "compact=p=0:nk=0", str(video_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, check=True,
    ).stdout
    packets = []
    for line in pkt_rows.splitlines():
        fields = dict(part.split("=", 1) for part in line.strip().split("|") if "=" in part)
        if not fields or "D" in fields.get("flags", "") or fields.get("pts") in (None, "", "N/A"):
            continue
        dur = fields.get("duration")
        packets.append((int(fields["pts"]), None if dur in (None, "", "N/A") else int(dur)))
    packets.sort()
    to_us = lambda ticks: int(round(ticks * base * 1000000))
    pts_us = [to_us(p) for p, _ in packets]
    frame_us = int(round(1000000 / float(rate)))
    durations_us = []
    for i, (p, d) in enumerate(packets):
        if d:
            durations_us.append(to_us(d))
        elif i + 1 < len(packets):
            durations_us.append(to_us(packets[i + 1][0] - p))
        else:
            durations_us.append(frame_us)
    schedule = {
        "fps_exact": fps_exact,
        "frames": len(pts_us),
        "pts_us": pts_us,
        "duration_us": durations_us,
        "visible_start_us": pts_us[0] if pts_us else 0,
        "visible_end_us": max((p + d for p, d in zip(pts_us, durations_us)), default=0),
    }
    timing = {
        "fps_exact": fps_exact,
        "frames": schedule["frames"],
        "pts_file": "picture-timing.json",
        "pts_sha256": sha256_bytes(canonical_bytes(schedule)),
        "visible_start_us": schedule["visible_start_us"],
        "visible_end_us": schedule["visible_end_us"],
    }
    return {
        "kind": "picture",
        "sha256": stream_sha,
        "geometry": geometry,
        "timing": timing,
        "schedule": schedule,
        "fps_exact": fps_exact,
        "fps": float(rate),
        "width": w,
        "height": h,
        "frames": schedule["frames"],
        "duration_s": round(schedule["frames"] / float(rate), 6),
    }


def build_cues_v2(film_dir: Path, video_path: Path, pic_info: dict, out_dir: Path, host_in_s: float = 0.0):
    """Build a legible-film v2 `cues.json` + `picture-timing.json` bound to `video_path`."""
    import lean
    s = lean.score_of(film_dir) if (film_dir / "score.json").is_file() else {}
    gen = lean.gen_data(film_dir)
    dur = float(pic_info["duration_s"])

    # 1. Sections: only those the film declares (score.json's beats). TIMES is not a list of sections: it holds step
    # sizes and counts beside beats, and a worked film's later acts sit CLOCK.SHIFT beats off it. The named events are
    # CUES, in seconds on the film's clock, the list vd sound checks sync against; they become events below.
    sections = []
    if s.get("beats"):
        for i, b in enumerate(s["beats"]):
            a_t, b_t = float(b["from"]), min(dur, float(b["to"]))
            if b_t > a_t:
                sections.append({
                    "id": b.get("name") or f"beat_{i + 1}",
                    "a": round(a_t, 4),
                    "b": round(b_t, 4),
                    "clock": "speech" if s.get("voice") else "music",
                    "gain_db": {},
                })
    if not sections:
        sections.append({"id": "main", "a": 0.0, "b": round(dur, 4), "clock": "music", "gain_db": {}})

    # 2. Events (turns, contacts, silences)
    events = []
    seen_ids = set()

    def add_ev(ev):
        eid = str(ev["id"])
        if eid in seen_ids:
            k = 2
            while f"{eid}_{k}" in seen_ids:
                k += 1
            eid = f"{eid}_{k}"
            ev["id"] = eid
        seen_ids.add(eid)
        events.append(ev)

    for sec in sections:
        add_ev({
            "id": f"turn_{sec['id']}",
            "t": round(sec["a"], 4),
            "scale": "turn",
            "sound": "required",
            "sync": "attack",
            "role": "turn",   # legible-film's spot_cues.py refuses an audible event with no role
            "section": sec["id"],
            "decision": f"Section turn into {sec['id']} on the shared beat clock.",
        })

    for name, at in gen.get("CUES") or []:
        t = float(at)
        if 0.0 <= t <= dur:
            add_ev({
                "id": f"cue_{re.sub(r'[^a-zA-Z0-9_]+', '_', str(name))}",
                "t": round(t, 4),
                "scale": "contact",
                "sound": "required",
                "sync": "attack",
                "role": str(name),
            })

    for i, e in enumerate(s.get("sounds") or []):
        t = float(e.get("at", 0.0))
        if 0.0 <= t <= dur:
            role = e.get("name") or e.get("make") or f"sound_{i + 1}"
            add_ev({
                "id": f"snd_{i + 1}_{re.sub(r'[^a-zA-Z0-9_]+', '_', str(role))}",
                "t": round(t, 4),
                "scale": "contact",
                "sound": "required",
                "sync": "attack",
                "role": str(role),
            })

    for name, r_from, r_to in lean.rests_of(film_dir, s):
        if 0.0 <= r_from < r_to <= dur:
            add_ev({
                "id": f"silence_{re.sub(r'[^a-zA-Z0-9_]+', '_', str(name))}",
                "t": round(r_from, 4),
                "t_end": round(r_to, 4),
                "scale": "silence",
                "sound": "silent",
                "scope": "effects",
                "decision": f"Intentional musical rest ({name}).",
            })

    try:
        rel_video = os.path.relpath(video_path.resolve(), out_dir.resolve()).replace("\\", "/")
    except ValueError:
        # on Windows a file on another drive has no path relative to the folder (CI kept the repository on D: and its
        # temp folder on C:, and the bridge stopped): the whole path is written, which legible-film's reader also takes
        rel_video = video_path.resolve().as_posix()
    cues_doc = {
        "version": "v2",
        "provenance": "exported",
        "fps": pic_info["fps_exact"],
        "host_map": {
            "insert_in_s": round(host_in_s, 4),
            "insert_out_s": round(host_in_s + dur, 4),
            "time_map": f"host_t = insert_t + {host_in_s:g}",
        },
        "picture": {
            "kind": "picture",
            "path": rel_video,
            "sha256": pic_info["sha256"],
            # sha256 is the first video stream's, as legible-film binds a picture: beside the path with no word, a check of
            # the file the obvious way (sha256sum) gave another number. The file's own is given too
            "sha256_of": "the first video stream's packets (ffmpeg -map 0:v:0 -c copy -f hash -hash sha256), not the whole file; the file's own SHA-256 is file_sha256",
            "file_sha256": sha256_file(video_path),
            "geometry": pic_info["geometry"],
            "timing": pic_info["timing"],
        },
        "sections": sections,
        "events": events,
    }
    timing_path = out_dir / "picture-timing.json"
    timing_path.write_bytes((json.dumps(pic_info["schedule"], sort_keys=True) + "\n").encode("utf-8"))
    cues_path = out_dir / "cues.json"
    cues_path.write_bytes((json.dumps(cues_doc, indent=1) + "\n").encode("utf-8"))
    return cues_path, timing_path, cues_doc


def audio_of(video_path: Path):
    """(channels, sample rate) of the file's first sound stream, or None when it has none: the timelines name the sound
    the file really has (they had named two channels at 48 kHz for every file, a silent one too)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("vd bridge: ffprobe is not on PATH; vd doctor says how to get it")
    p = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels,sample_rate", "-of", "json",
                        str(video_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    streams = (json.loads(p.stdout or "{}").get("streams") or []) if p.returncode == 0 else []
    if not streams:
        return None
    return int(streams[0].get("channels") or 2), int(streams[0].get("sample_rate") or 48000)


def localhost_file_url(path: Path):
    uri = path.resolve().as_uri()
    if uri.startswith("file:///"):
        return "file://localhost/" + uri[len("file:///"):]
    return uri


def build_xmeml_and_otio(film_dir: Path, video_path: Path, pic_info: dict, cues_doc: dict, out_dir: Path, host_in_s: float = 0.0):
    """Write Final Cut Pro 7 XML (`timeline.xml`) and OpenTimelineIO JSON (`timeline.otio`) for Premiere/Resolve/OTIO."""
    rate = Fraction(pic_info["fps_exact"])
    # FCP7's NTSC rates are N*1000/1001 (29.97 = 30000/1001), timebase N; any other rate is its nearest whole one, not NTSC
    # (29.97 written as 2997/100 had become timebase 29, NTSC: 28.97 fps)
    ntsc_base = rate * Fraction(1001, 1000)
    is_ntsc = rate.denominator != 1 and abs(ntsc_base - round(ntsc_base)) < Fraction(1, 100)
    base = int(round(ntsc_base)) if is_ntsc else int(round(rate))
    ntsc = "TRUE" if is_ntsc else "FALSE"
    frames = int(pic_info["frames"])
    w, h = int(pic_info["width"]), int(pic_info["height"])
    start_frame = int(round(host_in_s * float(rate)))
    end_frame = start_frame + frames
    ticks_out = int(round(Fraction(frames) / rate * TICKS_PER_SECOND))
    url = localhost_file_url(video_path)
    sound = audio_of(video_path)

    root = ET.Element("xmeml", {"version": "5"})
    seq = ET.SubElement(root, "sequence", {"id": "sequence-1"})
    ET.SubElement(seq, "name").text = f"{film_dir.name} (Video Decompiler Insert)"
    ET.SubElement(seq, "duration").text = str(end_frame)
    r_node = ET.SubElement(seq, "rate")
    ET.SubElement(r_node, "timebase").text = str(base)
    ET.SubElement(r_node, "ntsc").text = ntsc

    for ev in cues_doc.get("events", []):
        m_node = ET.SubElement(seq, "marker")
        ET.SubElement(m_node, "name").text = str(ev["id"])
        ET.SubElement(m_node, "comment").text = f"{ev.get('scale', 'contact')} ({ev.get('role') or ev.get('decision') or ''})"
        ET.SubElement(m_node, "in").text = str(start_frame + int(round(float(ev["t"]) * float(rate))))
        ET.SubElement(m_node, "out").text = "-1"

    media = ET.SubElement(seq, "media")
    video = ET.SubElement(media, "video")
    fmt = ET.SubElement(video, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    r_sc = ET.SubElement(sc, "rate")
    ET.SubElement(r_sc, "timebase").text = str(base)
    ET.SubElement(r_sc, "ntsc").text = ntsc
    ET.SubElement(sc, "width").text = str(w)
    ET.SubElement(sc, "height").text = str(h)
    ET.SubElement(sc, "anamorphic").text = "FALSE"
    ET.SubElement(sc, "pixelaspectratio").text = "square"
    ET.SubElement(sc, "fielddominance").text = "none"

    v_track = ET.SubElement(video, "track")
    v_clip = ET.SubElement(v_track, "clipitem", {"id": "clip-1"})
    ET.SubElement(v_clip, "name").text = video_path.name
    ET.SubElement(v_clip, "enabled").text = "TRUE"
    r_vc = ET.SubElement(v_clip, "rate")
    ET.SubElement(r_vc, "timebase").text = str(base)
    ET.SubElement(r_vc, "ntsc").text = ntsc
    ET.SubElement(v_clip, "duration").text = str(frames)
    ET.SubElement(v_clip, "start").text = str(start_frame)
    ET.SubElement(v_clip, "end").text = str(end_frame)
    ET.SubElement(v_clip, "in").text = "0"
    ET.SubElement(v_clip, "out").text = str(frames)
    ET.SubElement(v_clip, "pproTicksIn").text = "0"
    ET.SubElement(v_clip, "pproTicksOut").text = str(ticks_out)

    f_node = ET.SubElement(v_clip, "file", {"id": "file-1"})
    ET.SubElement(f_node, "name").text = video_path.name
    ET.SubElement(f_node, "pathurl").text = url
    r_fn = ET.SubElement(f_node, "rate")
    ET.SubElement(r_fn, "timebase").text = str(base)
    ET.SubElement(r_fn, "ntsc").text = ntsc
    ET.SubElement(f_node, "duration").text = str(frames)
    f_med = ET.SubElement(f_node, "media")
    f_vid = ET.SubElement(f_med, "video")
    f_vsc = ET.SubElement(f_vid, "samplecharacteristics")
    r_fvsc = ET.SubElement(f_vsc, "rate")
    ET.SubElement(r_fvsc, "timebase").text = str(base)
    ET.SubElement(r_fvsc, "ntsc").text = ntsc
    ET.SubElement(f_vsc, "width").text = str(w)
    ET.SubElement(f_vsc, "height").text = str(h)
    if sound:
        f_aud = ET.SubElement(f_med, "audio")
        ET.SubElement(f_aud, "channelcount").text = str(sound[0])
        f_asc = ET.SubElement(f_aud, "samplecharacteristics")
        ET.SubElement(f_asc, "samplerate").text = str(sound[1])

    ET.SubElement(v_track, "enabled").text = "TRUE"
    ET.SubElement(v_track, "locked").text = "FALSE"

    audio = ET.SubElement(media, "audio")
    # a track per channel the file has: stereo panned left and right, mono and more than two centred
    channels = [] if not sound else [(1, -1), (2, 1)] if sound[0] == 2 else [(k, 0) for k in range(1, sound[0] + 1)]
    for ch_idx, pan_val in channels:
        a_track = ET.SubElement(audio, "track")
        a_clip = ET.SubElement(a_track, "clipitem", {"id": f"clip-{ch_idx + 1}"})
        ET.SubElement(a_clip, "name").text = f"{video_path.name} (Ch {ch_idx})"
        ET.SubElement(a_clip, "enabled").text = "TRUE"
        r_ac = ET.SubElement(a_clip, "rate")
        ET.SubElement(r_ac, "timebase").text = str(base)
        ET.SubElement(r_ac, "ntsc").text = ntsc
        ET.SubElement(a_clip, "duration").text = str(frames)
        ET.SubElement(a_clip, "start").text = str(start_frame)
        ET.SubElement(a_clip, "end").text = str(end_frame)
        ET.SubElement(a_clip, "in").text = "0"
        ET.SubElement(a_clip, "out").text = str(frames)
        ET.SubElement(a_clip, "pproTicksIn").text = "0"
        ET.SubElement(a_clip, "pproTicksOut").text = str(ticks_out)
        ET.SubElement(a_clip, "file", {"id": "file-1"})
        st = ET.SubElement(a_clip, "sourcetrack")
        ET.SubElement(st, "mediatype").text = "audio"
        ET.SubElement(st, "trackindex").text = str(ch_idx)
        filt = ET.SubElement(a_clip, "filter")
        eff = ET.SubElement(filt, "effect")
        ET.SubElement(eff, "name").text = "Audio Pan"
        ET.SubElement(eff, "effectid").text = "audiopan"
        ET.SubElement(eff, "effectcategory").text = "audiopan"
        ET.SubElement(eff, "effecttype").text = "audiopan"
        ET.SubElement(eff, "mediatype").text = "audio"
        param = ET.SubElement(eff, "parameter")
        ET.SubElement(param, "parameterid").text = "pan"
        ET.SubElement(param, "name").text = "Pan"
        ET.SubElement(param, "valuemin").text = "-1"
        ET.SubElement(param, "valuemax").text = "1"
        ET.SubElement(param, "value").text = str(pan_val)
        ET.SubElement(a_track, "enabled").text = "TRUE"
        ET.SubElement(a_track, "locked").text = "FALSE"

    xml_path = out_dir / "timeline.xml"
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding="unicode") + "\n"
    xml_path.write_text(xml_str, encoding="utf-8")

    # Also write OpenTimelineIO (OTIO) JSON representation
    otio_doc = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": f"{film_dir.name} (Video Decompiler Insert)",
        # the host's in-point is a gap before the clip, as the XML places it at start_frame: both files then hold the same
        # sequence, of the same length (the XML counted the in-point and the OTIO, as a start time, did not)
        "global_start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": 0.0},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "V1",
                    "kind": "Video",
                    "children": [
                        {
                            "OTIO_SCHEMA": "Clip.2",
                            "name": video_path.name,
                            "source_range": {
                                "OTIO_SCHEMA": "TimeRange.1",
                                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": 0.0},
                                "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": float(frames)},
                            },
                            "media_references": {
                                "DEFAULT_MEDIA": {
                                    "OTIO_SCHEMA": "ExternalReference.1",
                                    "target_url": url,
                                    "available_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": 0.0},
                                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": float(frames)},
                                    },
                                }
                            },
                            "markers": [
                                {
                                    "OTIO_SCHEMA": "Marker.2",
                                    "name": str(ev["id"]),
                                    "color": "GREEN" if ev.get("scale") == "turn" else "ORANGE",
                                    "marked_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": round(float(ev["t"]) * float(rate), 3)},
                                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": 0.0},
                                    },
                                }
                                for ev in cues_doc.get("events", [])
                            ],
                        }
                    ],
                }
            ],
        },
    }
    tracks = otio_doc["tracks"]["children"]
    video_clip = tracks[0]["children"][0]
    gap = [{"OTIO_SCHEMA": "Gap.1", "name": "host in",
            "source_range": {"OTIO_SCHEMA": "TimeRange.1",
                             "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": 0.0},
                             "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": float(start_frame)}}}] if start_frame else []
    tracks[0]["children"] = gap + [video_clip]
    if sound:
        # the film's sound, on its own track under the picture, from the same file
        tracks.append({"OTIO_SCHEMA": "Track.1", "name": "A1", "kind": "Audio",
                       "children": json.loads(json.dumps(gap)) + [{k: v for k, v in video_clip.items() if k != "markers"} | {"markers": []}]})
    otio_path = out_dir / "timeline.otio"
    otio_path.write_text(json.dumps(otio_doc, indent=1) + "\n", encoding="utf-8")
    return xml_path, otio_path


def ensure_hero_mp4(film_dir: Path, video_path: Path, out_dir: Path):
    """The picture the cues are bound to: `video_path` when given, else the film's latest export
    (`~/.vd/out/NAME/NAME.mp4`). cues.json names this file's exact stream hash, so a picture that does not exist is
    refused, never stood in for: cues timed on a stand-in would read as fresh against nothing an editor has."""
    import lean
    if video_path:
        if Path(video_path).is_file():
            return Path(video_path).resolve()
        raise SystemExit(f"vd bridge: no such picture: {video_path}")
    cand = lean.outdir(film_dir) / f"{film_dir.name}.mp4"
    if cand.is_file():
        return cand.resolve()
    raise SystemExit(f"vd bridge: {film_dir.name} has no export at {cand}. Run vd export in the film folder first, "
                     "or give the picture with --video FILM.mp4")


def export_bridge(film_dir: Path, video_path: Path = None, out_dir: Path = None, host_in_s: float = 0.0):
    """Export the complete legible-film insert/editor bridge bundle into `out_dir`."""
    import lean
    film_dir = Path(film_dir).resolve()
    out_dir = Path(out_dir).resolve() if out_dir else (lean.outdir(film_dir) / "bridge")
    out_dir.mkdir(parents=True, exist_ok=True)
    hero = ensure_hero_mp4(film_dir, video_path, out_dir)
    pic_info = picture_identity_and_schedule(hero)
    cues_path, timing_path, cues_doc = build_cues_v2(film_dir, hero, pic_info, out_dir, host_in_s=host_in_s)
    xml_path, otio_path = build_xmeml_and_otio(film_dir, hero, pic_info, cues_doc, out_dir, host_in_s=host_in_s)
    return {
        "out_dir": out_dir,
        "video": hero,
        "cues_json": cues_path,
        "picture_timing_json": timing_path,
        "timeline_xml": xml_path,
        "timeline_otio": otio_path,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--film", help="film folder")
    ap.add_argument("--video", help="the exported film (default: ~/.vd/out/NAME/NAME.mp4); refused when missing")
    ap.add_argument("-o", dest="out", help="destination bridge folder (default: ~/.vd/out/NAME/bridge)")
    ap.add_argument("--host-in", type=float, default=0.0, help="host timeline in-point in seconds")
    a = ap.parse_args(argv)
    import lean
    d = lean.film_dir(a.film, required=False) or Path.cwd().resolve()
    res = export_bridge(d, Path(a.video) if a.video else None, Path(a.out) if a.out else None, host_in_s=a.host_in)
    print(f"legible-film bridge bundle for {d.name} -> {res['out_dir']}")
    print(f"  v2 cues.json:        {res['cues_json']}")
    print(f"  picture-timing.json: {res['picture_timing_json']}")
    print(f"  FCP7 XML (xmeml):    {res['timeline_xml']}")
    print(f"  OpenTimelineIO:      {res['timeline_otio']}")
    print(res["timeline_xml"])
    return 0


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
