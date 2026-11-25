#!/usr/bin/env python3
"""`vd foley` (not proven on a film): media/foley.wav, made by rule from camera moves, springs and cues read from the
film's code by pattern (~/.vd/out/NAME/telemetry.gen.json). Sizes are guessed from cue names; nothing is measured from the picture.

  python foley.py [--film DIR] [-o media/foley.wav] [--telemetry ~/.vd/out/NAME/telemetry.gen.json]

What it does: reads camera paths (CAM, PATH, SLOTS) and named cues from the film's code by pattern into
~/.vd/out/NAME/telemetry.gen.json, and makes a track from them in NumPy: a whoosh swept by the camera's turning and zooming speed, a
thud whose pitch and decay follow a size guessed from the cue's name, and a click as a word locks into place. Nothing is
measured from the drawn picture, and nobody has listened to it on a finished film. Nothing plays media/foley.wav unless
it is mixed; --mix adds it into media/sound.wav, which sound.py owns and writes over.
"""
import argparse
import json
import math
import re
import sys
import wave
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

SR = 48000


def band(x, lo, hi, sr=SR):
    """Zero-phase 4th-order Butterworth-like FFT bandpass."""
    if len(x) == 0:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    H = 1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1.0)) ** 8) / np.sqrt(1.0 + (f / max(hi, lo + 10.0)) ** 8)
    return np.fft.irfft(X * H, len(x)).astype(np.float32)


def pan_gains(pan):
    """Constant-power stereo gains (gl, gr) for pan in -1..1."""
    p = max(-1.0, min(1.0, float(pan)))
    angle = (p + 1.0) * math.pi / 4.0
    return math.cos(angle) * 1.4142, math.sin(angle) * 1.4142


def thud_from_mass(mass, velocity=1.0, seed=1):
    """Resonant physical impact thud scaled by screen-space bounding-box mass (0..1) and impact velocity.
    Larger bounding boxes have lower fundamental modal frequency and longer decay; smaller ones are tight knocks."""
    rng = np.random.default_rng(seed)
    m = max(0.002, min(1.0, float(mass)))
    vel = max(0.05, min(3.0, float(velocity)))
    dur = min(0.55, 0.08 + 0.28 * (m ** 0.35))
    n = max(64, int(round(dur * SR)))
    t = np.arange(n, dtype=np.float32) / SR
    f0 = 240.0 * ((1.0 + 18.0 * m) ** -0.38)   # ~230 Hz for a small badge, ~68 Hz for a full-frame card slam
    decay = 14.0 + 38.0 * ((1.0 - m) ** 1.5)
    pitch_env = f0 * (1.0 + 0.85 * np.exp(-t * 45.0))
    phase = 2.0 * np.pi * np.cumsum(pitch_env) / SR
    body = np.sin(phase) * np.exp(-t * decay)
    mode2 = 0.32 * np.sin(2.38 * phase) * np.exp(-t * decay * 1.9)
    # 1-5 kHz contact transient so impacts stay audible on phone speakers
    click_hi = min(5500.0, max(1600.0, 4200.0 - 2200.0 * m))
    contact = band(rng.standard_normal(n).astype(np.float32), 700.0, click_hi) * np.exp(-t * 95.0) * 0.55
    attack = np.minimum(1.0, t / 0.0018)
    gain = vel * (0.28 + 0.52 * (m ** 0.25))
    return ((body + mode2 + contact) * attack * gain).astype(np.float32)


def slide_from_mass(mass, velocity=1.0, dur=0.22, seed=2):
    """Paper/card friction slide scaled by mass and speed."""
    rng = np.random.default_rng(seed)
    m = max(0.002, min(1.0, float(mass)))
    vel = max(0.05, min(3.0, float(velocity)))
    d = max(0.06, min(0.8, float(dur)))
    n = int(round(d * SR))
    t = np.arange(n, dtype=np.float32) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    lo = max(350.0, 1400.0 - 800.0 * m)
    hi = max(lo + 600.0, 5200.0 - 2000.0 * m)
    win = np.sin(np.pi * t / max(d, 1e-4)) ** 1.6
    return (band(noise, lo, hi) * win * vel * 0.35).astype(np.float32)


def click_from_lock(mass=0.005, velocity=0.7, seed=3):
    """Sub-millisecond mechanical kerning-lock click for arriving typography."""
    rng = np.random.default_rng(seed)
    m = max(0.0005, min(0.1, float(mass)))
    vel = max(0.05, min(2.0, float(velocity)))
    n = int(0.024 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f_res = 3400.0 - 9000.0 * m
    ping = np.sin(2.0 * np.pi * f_res * t) * np.exp(-t / 0.0022)
    snap = band(rng.standard_normal(n).astype(np.float32), 2200.0, 9500.0) * np.exp(-t / 0.0012) * 0.65
    return ((ping + snap) * vel * 0.28).astype(np.float32)


def whoosh_from_camera(camera_samples, duration_s, seed=7):
    """Continuous stereo aerodynamic whoosh modulated by instantaneous angular/zoom camera velocity omega(t)."""
    total = int(round(duration_s * SR))
    out = np.zeros((total, 2), dtype=np.float32)
    if not camera_samples or total == 0:
        return out
    rng = np.random.default_rng(seed)
    ts = np.array([float(c["t"]) for c in camera_samples], dtype=np.float32)
    omegas = np.array([float(c.get("omega", 0.0)) for c in camera_samples], dtype=np.float32)
    pans = np.array([float(c.get("pan", 0.0)) for c in camera_samples], dtype=np.float32)
    if float(omegas.max(initial=0.0)) < 1.5:
        return out
    # Normalize omega above quiet drift floor so slow hold creep stays silent
    active = np.maximum(0.0, omegas - 2.0)
    peak = float(np.percentile(active[active > 0], 95)) if np.any(active > 0) else 1.0
    norm = np.clip(active / max(peak, 8.0), 0.0, 1.5)
    t_audio = np.arange(total, dtype=np.float32) / SR
    env = np.interp(t_audio, ts, norm).astype(np.float32)
    pan_curve = np.interp(t_audio, ts, pans).astype(np.float32)
    noise = rng.standard_normal(total).astype(np.float32)
    low_band = band(noise, 240.0, 1400.0)
    high_band = band(noise, 1400.0, 5600.0)
    # Faster angular velocity shifts energy from warm low air to bright high air
    air = (low_band * (1.0 - 0.55 * np.clip(env, 0.0, 1.0)) + high_band * (0.35 + 0.65 * np.clip(env, 0.0, 1.0))) * (env ** 1.4) * 0.32
    angles = (pan_curve + 1.0) * (np.pi / 4.0)
    out[:, 0] = air * np.cos(angles) * 1.4142
    out[:, 1] = air * np.sin(angles) * 1.4142
    return out


def synthesize(telemetry, duration_s=None, seed=11):
    """Synthesize a 48 kHz stereo float32 physical foley stem from a TelemetryTrace dict."""
    fps = float(telemetry.get("fps") or 60.0)
    frames = int(telemetry.get("frames") or round((duration_s or 10.0) * fps))
    dur = float(duration_s or (frames / fps))
    total = int(round(dur * SR))
    mix = whoosh_from_camera(telemetry.get("camera") or [], dur, seed=seed)
    for k, ev in enumerate(telemetry.get("impacts") or []):
        at = float(ev.get("t", 0.0))
        kind = ev.get("kind", "slam")
        mass = float(ev.get("mass", 0.05))
        vel = float(ev.get("velocity", 1.0))
        pan = float(ev.get("pan", 0.0))
        if kind == "lock":
            sig = click_from_lock(mass=mass, velocity=vel, seed=seed + k + 1)
        elif kind == "slide":
            sig = slide_from_mass(mass=mass, velocity=vel, seed=seed + k + 1)
        else:
            sig = thud_from_mass(mass=mass, velocity=vel, seed=seed + k + 1)
        idx = int(round(at * SR))
        if idx < 0 or idx >= total:
            continue
        n = min(len(sig), total - idx)
        gl, gr = pan_gains(pan)
        mix[idx:idx + n, 0] += sig[:n] * gl
        mix[idx:idx + n, 1] += sig[:n] * gr
    peak = float(np.abs(mix).max()) if len(mix) else 0.0
    if peak > 0.85:
        mix *= 0.85 / peak
    return mix


def extract_telemetry_from_film(d: Path):
    """Extract a deterministic TelemetryTrace from a film folder (score.json, kit/times.gen.ts, film.tsx and any
    render.json), without needing a GPU render."""
    import lean
    s = lean.score_of(d) if (d / "score.json").is_file() else {"fps": 60, "width": 1920, "height": 1080, "duration": 10.0}
    gen = lean.gen_data(d)
    clock = gen.get("CLOCK") or {}
    fps = float(clock.get("FPS") or s.get("fps") or 60.0)
    fb = float(clock.get("FB") or 32.0)
    beat_sec = fb / fps
    dur = float(clock.get("DURATION") or s.get("duration") or 10.0)
    W, H = int(s.get("width") or 1920), int(s.get("height") or 1080)
    total_frames = int(round(dur * fps))

    # 1. Camera keyframes from film.tsx (CAM or PATH or score beats)
    film_src = ""
    for f in sorted(d.glob("*.tsx")):
        film_src += "\n" + f.read_text(encoding="utf-8", errors="replace")
    times_dict = gen.get("TIMES") or {}
    # names that stand for a part of TIMES (Onoma's `const P = TM.PARTS`): its camera keys written P.thunder were read
    # as nothing, and half its film made no sound
    aliases = dict(re.findall(r"const\s+(\w+)\s*=\s*TM\.(\w+)\s*[;,]", film_src))

    def resolve_beat(expr: str):
        expr = expr.strip()
        try:
            return float(expr)
        except ValueError:
            pass
        m = re.match(r"^(?:g\()?(\w+)\.(\w+)(?:\[(\d+)\])?\)?(?:\s*([+-])\s*([\d.]+))?$", expr)
        if m and (m.group(1) == "TM" or m.group(1) in aliases):
            obj, key, idx, op, off = m.groups()
            val = times_dict.get(key) if obj == "TM" else (times_dict.get(aliases[obj]) or {}).get(key)
            if isinstance(val, list) and idx is not None and int(idx) < len(val):
                val = val[int(idx)]
            if isinstance(val, (int, float)):
                v = float(val)
                if op and off:
                    v += float(off) if op == "+" else -float(off)
                shift = float(clock.get("SHIFT") or 0.0) if expr.startswith("g(") else 0.0
                return v - shift
        return None

    cam_keys = []
    if "const CAM" in film_src:
        block = film_src.split("const CAM", 1)[1].split("];", 1)[0]
        for row in re.findall(r"\[([^\[\]]+)\]", block):
            parts = [p.strip() for p in row.split(",")]
            if len(parts) >= 4:
                b = resolve_beat(parts[0])
                try:
                    cx, cy, z = float(parts[1]), float(parts[2]), float(parts[3])
                    frames_len = float(parts[4]) if len(parts) >= 5 else 20.0
                    if b is not None:
                        cam_keys.append((b * fb, cx, cy, z, frames_len))
                except ValueError:
                    pass
    elif "const PATH" in film_src:
        # Linden-style nested outward zoom: each step doubles/triples view width across beats
        for k, b in enumerate(times_dict.get("LANDS") or []):
            cam_keys.append((float(b) * fb - 24, W / 2, H / 2, 2.2, 24.0))
            cam_keys.append((float(b) * fb, W / 2, H / 2, 1.0, 24.0))
        for name in ("OUT1", "OUT2", "OUT3", "OUT4"):
            if isinstance(times_dict.get(name), (int, float)):
                b = float(times_dict[name])
                cam_keys.append((b * fb, W / 2, H / 2, 2.5, 36.0))
                cam_keys.append(((b + 2.0) * fb, W / 2, H / 2, 1.0, 36.0))

    cam_keys.sort(key=lambda r: r[0])

    def cam_at(f):
        if not cam_keys:
            return W / 2.0, H / 2.0, 1.0
        cx, cy, z = cam_keys[0][1], cam_keys[0][2], cam_keys[0][3]
        for start, tx, ty, tz, flen in cam_keys[1:]:
            if f < start:
                break
            u = max(0.0, min(1.0, (f - start) / max(1.0, flen)))
            k = 4 * u * u * u if u < 0.5 else 1 - ((-2 * u + 2) ** 3) / 2
            cx = cx + (tx - cx) * k
            cy = cy + (ty - cy) * k
            z = z + (tz - z) * k
        return cx, cy, z

    camera_samples = []
    for f in range(total_frames):
        x0, y0, z0 = cam_at(max(0, f - 0.5))
        x1, y1, z1 = cam_at(min(total_frames - 1, f + 0.5))
        vx = (x1 - x0) * fps
        vy = (y1 - y0) * fps
        z_rate = math.log(max(1e-4, z1) / max(1e-4, z0)) * fps
        omega = math.hypot(vx / (W * 0.04), vy / (H * 0.04), z_rate * 45.0)
        pan = max(-1.0, min(1.0, (x1 - W / 2.0) / (W / 2.0)))
        camera_samples.append({
            "frame": f,
            "t": round(f / fps, 5),
            "vx": round(vx, 2),
            "vy": round(vy, 2),
            "zoomRate": round(z_rate, 4),
            "omega": round(omega, 3),
            "pan": round(pan, 3),
        })

    # 2. Impacts from CUES, score.json beats/sounds, stamps, and typed lines
    impacts = []
    for cue_name, cue_sec in gen.get("CUES") or []:
        t = float(cue_sec)
        low_name = str(cue_name).lower()
        is_big = any(k in low_name for k in ("return", "pick", "press", "last", "mark", "end", "book", "wall", "card", "land", "bolt", "clap"))
        mass = 0.24 if is_big else 0.035
        vel = 1.15 if is_big else 0.75
        kind = "slam" if is_big else "slide"
        cx, _, _ = cam_at(t * fps)
        pan = max(-1.0, min(1.0, (cx - W / 2.0) / (W / 2.0)))
        impacts.append({
            "name": str(cue_name),
            "t": round(t, 5),
            "frame": round(t * fps, 2),
            "mass": round(mass, 4),
            "velocity": round(vel, 3),
            "pan": round(pan, 3),
            "kind": kind,
        })

    for b in s.get("beats") or []:
        t = float(b.get("from", 0.0))
        impacts.append({
            "name": str(b.get("id") or "beat"),
            "t": round(t, 5),
            "frame": round(t * fps, 2),
            "mass": 0.16,
            "velocity": 0.9,
            "pan": 0.0,
            "kind": "slam",
        })

    # 3. Kerning locks from LINE + TYPE0 / TYPE_PER when present
    line_text = gen.get("LINE")
    if isinstance(line_text, str) and "TYPE0" in times_dict:
        t0 = float(times_dict["TYPE0"]) * beat_sec
        step = float(times_dict.get("TYPE_PER", 2.0)) / fps
        for i, ch in enumerate(line_text):
            if ch == " ":
                continue
            at = t0 + i * step
            pan = -0.35 + 0.7 * (i / max(1, len(line_text) - 1))
            impacts.append({
                "name": f"LINE[{i}]",
                "t": round(at, 5),
                "frame": round(at * fps, 2),
                "mass": 0.003,
                "velocity": 0.65,
                "pan": round(pan, 3),
                "kind": "lock",
            })

    impacts.sort(key=lambda x: x["t"])
    return {
        "fps": fps,
        "frames": total_frames,
        "width": W,
        "height": H,
        "camera": camera_samples,
        "impacts": impacts,
    }


def write_wav(path: Path, mix: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    y = (np.clip(mix, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def blend_into_sound_wav(sound_wav: Path, foley_mix: np.ndarray, foley_gain_db: float = -9.5):
    """Blend stereo `foley_mix` into an existing `media/sound.wav` and re-level it toward -15.0 LUFS, by at most 6 dB and
    keeping its true peak at -2.2 dBTP or under, so a quiet mix ends short of -15. Returns the written file's measured
    (LUFS, dBTP), or None when nothing was written."""
    import os
    import shutil
    import subprocess
    import lean
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not sound_wav.is_file():
        return None
    no_win = 0x08000000 if os.name == "nt" else 0
    p = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-i", str(sound_wav), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, creationflags=no_win,
    )
    if p.returncode != 0 or not p.stdout:
        return None
    base = np.frombuffer(p.stdout, dtype="<f4").reshape(-1, 2).copy()
    n = min(len(base), len(foley_mix))
    gain = 10.0 ** (foley_gain_db / 20.0)
    base[:n] += foley_mix[:n] * gain
    # Keep sample peak safely below -2.2 dBFS so AAC muxing never clips over -1 dBTP
    pk = float(np.max(np.abs(base))) if len(base) else 0.0
    if pk > 0.77:
        base *= 0.77 / pk
    tmp_wav = sound_wav.with_name(sound_wav.stem + ".foley-tmp.wav")
    write_wav(tmp_wav, base)
    try:
        lufs, tp = lean.loudness(tmp_wav)
        if lufs is not None:
            delta_db = max(-6.0, min(6.0, -15.0 - float(lufs)))
            if tp is not None and float(tp) + delta_db > -2.2:
                delta_db = -2.2 - float(tp)
            if abs(delta_db) > 0.15:
                base = np.clip(base * (10.0 ** (delta_db / 20.0)), -0.88, 0.88)
                write_wav(tmp_wav, base)
        tmp_wav.replace(sound_wav)
    finally:
        tmp_wav.unlink(missing_ok=True)
    return lean.loudness(sound_wav)     # what was written, measured: the note said -15 LUFS of a file at -24.7


def run_foley(film_dir: Path, out_wav: Path = None, out_json: Path = None, mix_into_sound: bool = False):
    """Extract telemetry for film_dir, write ~/.vd/out/NAME/telemetry.gen.json and media/foley.wav, and return (wav_path, json_path, summary_line)."""
    film_dir = Path(film_dir).resolve()
    import lean
    # the trace is an output, kept beside the film's other outputs: in kit/ it was a .json inside the film (TRAPS.md)
    tel_path = Path(out_json).resolve() if out_json else (lean.outdir(film_dir) / "telemetry.gen.json")
    if mix_into_sound and not (film_dir / "media" / "sound.wav").is_file():
        raise SystemExit("vd foley --mix: there is no media/sound.wav to mix into (a film copied with --like has one, made by its "
                         "sound.py); nothing was made. Without --mix the track is written alone, to media/foley.wav")
    wav_path = Path(out_wav).resolve() if out_wav else (film_dir / "media" / "foley.wav")
    if tel_path.is_file() and out_json:
        tel = json.loads(tel_path.read_text(encoding="utf-8"))
    else:
        tel = extract_telemetry_from_film(film_dir)
        tel_path.parent.mkdir(parents=True, exist_ok=True)
        tel_path.write_text(json.dumps(tel, indent=1) + "\n", encoding="utf-8")
    mix = synthesize(tel)
    write_wav(wav_path, mix)
    mixed_note = ""
    if mix_into_sound and (film_dir / "media" / "sound.wav").is_file():
        got = blend_into_sound_wav(film_dir / "media" / "sound.wav", mix)
        if got and got[0] is not None:
            lufs, tp = float(got[0]), float(got[1])
            mixed_note = (f"; blended into media/sound.wav, which now measures {lufs:.1f} LUFS, true peak {tp:.1f} dBTP"
                          + (" (short of the -15 aimed at: the level is raised at most 6 dB and its true peak kept at -2.2 dBTP)" if lufs < -16 else ""))
        elif got:
            mixed_note = "; blended into media/sound.wav, whose level could not be measured"
    mono = mix.mean(axis=1) if len(mix) else np.zeros(1, dtype=np.float32)
    rms_db = 20.0 * math.log10(float(np.sqrt(np.mean(mono ** 2))) + 1e-9)
    peak_db = 20.0 * math.log10(float(np.max(np.abs(mix))) + 1e-9) if len(mix) else -90.0
    n_impacts = len(tel.get("impacts") or [])
    n_locks = sum(1 for e in (tel.get("impacts") or []) if e.get("kind") == "lock")
    max_omega = max((float(c.get("omega", 0.0)) for c in (tel.get("camera") or [])), default=0.0)
    summary = (f"foley {wav_path.name}: {len(mix) / SR:.2f} s, {n_impacts} physical events ({n_locks} kerning locks), "
               f"peak camera omega {max_omega:.1f} deg/s, rms {rms_db:.1f} dBFS, peak {peak_db:.1f} dBFS{mixed_note}; "
               "each impact's size is guessed from its cue's name, not measured")
    return wav_path, tel_path, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--film", help="film folder (default: current directory)")
    ap.add_argument("-o", dest="out", help="output wav path (default: FILM/media/foley.wav)")
    ap.add_argument("--telemetry", help="telemetry JSON path (default: ~/.vd/out/NAME/telemetry.gen.json)")
    a = ap.parse_args(argv)
    d = Path(a.film).resolve() if a.film else Path.cwd().resolve()
    wav_path, tel_path, summary = run_foley(d, Path(a.out) if a.out else None, Path(a.telemetry) if a.telemetry else None)
    print(summary)
    print(f"telemetry: {tel_path}")
    print(wav_path)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
