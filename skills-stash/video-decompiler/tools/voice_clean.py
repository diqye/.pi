#!/usr/bin/env python3
"""Conservative five-step dialogue cleanup with speech-band loss guard, ported from legible-film.

  python voice_clean.py dialogue.wav --out dialogue-clean.wav [--max-speech-loss-db 3] [--json clean.json]

Applies:
  1. 80 Hz 2-pole highpass (`highpass=f=80:p=2`)
  2. FFT noise reduction (`afftdn=nr=6:nf=<p10_rms_dbfs>:tn=0`, noise floor clamped to -80..-20 dBFS)
  3. 5-9 kHz sibilance de-esser (`deesser=i=0.1:m=0.2:f=0.5:s=o`)
  4. Gentle 1.5:1 compression (`acompressor=threshold=0.125:ratio=1.5:attack=20:release=150:makeup=1`)
  5. Level toward -20 LUFS (gain clamped to +/-6 dB)
Each stage is verified against the 200 Hz - 5 kHz speech band; if speech-band power drops by more than
`--max-speech-loss-db` (default 3.0 dB), the stage is refused and the prior clean stage is kept.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
RATE = 48000
# the cleanup's steps in order; `{nf}` is the measured noise floor. The final level step adds `volume`, and the meter `loudnorm`.
STAGES = (
    ("highpass", "highpass=f=80:p=2"),
    ("noise_reduction", "afftdn=nr=6:nf={nf:.3f}:tn=0"),
    ("de_ess", "deesser=i=0.1:m=0.2:f=0.5:s=o"),
    ("compression", "acompressor=threshold=0.125:ratio=1.5:attack=20:release=150:makeup=1"),
)
# the ffmpeg filters this tool needs, read by `vd doctor` from here so the two lists cannot drift
FILTERS = tuple(dict.fromkeys([g.split("=", 1)[0] for _, g in STAGES] + ["volume", "loudnorm"]))


def db(amp):
    return float(20.0 * math.log10(max(float(amp), 1e-12)))


def meter_loudness(ffmpeg, path):
    cmd = [
        ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", str(path), "-map", "0:a:0",
        "-af", "loudnorm=I=-20:LRA=11:TP=-1:print_format=json", "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    matches = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.DOTALL)
    if not matches:
        return {"integrated_lufs": None, "true_peak_dbtp": None, "lra_lu": None}
    data = json.loads(matches[-1])

    def val(k):
        try:
            v = float(data[k])
            return v if math.isfinite(v) else None
        except (KeyError, TypeError, ValueError):
            return None

    return {"integrated_lufs": val("input_i"), "true_peak_dbtp": val("input_tp"), "lra_lu": val("input_lra")}


def measure_file(ffmpeg, path):
    """Measure overlapping spectral windows (200-5000 Hz speech body vs 5000-9000 Hz sibilance) and 20 ms RMS."""
    cmd = [ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-ac", "2", "-ar", str(RATE), "-f", "f32le", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    hop = RATE // 2
    block_bytes = hop * 2 * 4
    previous = np.empty((0, 2), dtype=np.float32)
    powers = np.zeros(2, dtype=np.float64)
    rms_list = []
    peak = 0.0
    total = 0
    win_20ms = int(0.02 * RATE)
    while True:
        raw = p.stdout.read(block_bytes)
        if not raw:
            break
        if len(raw) % 8:
            raise ValueError("invalid decoded audio")
        block = np.frombuffer(raw, dtype="<f4").reshape(-1, 2)
        if not np.isfinite(block).all():
            raise ValueError("non-finite audio")
        total += len(block)
        peak = max(peak, float(np.max(np.abs(block))))
        n_frames = len(block) // win_20ms
        if n_frames > 0:
            env = np.sqrt(np.mean(block[:n_frames * win_20ms].reshape(n_frames, win_20ms, 2).astype(np.float64) ** 2, axis=(1, 2)))
            rms_list.extend(env.tolist())
        window = np.concatenate((previous, block))
        if len(window) >= 2:
            freqs = np.fft.rfftfreq(len(window), 1.0 / RATE)
            spec = np.fft.rfft(window.astype(np.float64) * np.hanning(len(window))[:, None], axis=0)
            energy = np.sum(np.abs(spec) ** 2, axis=1)
            powers[0] += energy[(freqs >= 200) & (freqs < 5000)].sum()
            powers[1] += energy[(freqs >= 5000) & (freqs < 9000)].sum()
        previous = block.copy()
    p.stdout.close()
    stderr = p.stderr.read()
    code = p.wait()
    if code or not total:
        raise ValueError("cannot decode audio: " + stderr.decode(errors="replace")[-400:])
    p10_rms = float(np.percentile(rms_list, 10)) if rms_list else 1e-4
    return {
        "noise_floor_p10_dbfs": db(p10_rms),
        "loudness": meter_loudness(ffmpeg, path),
        "sample_peak_dbfs": db(peak),
        "sibilance_to_body_db": float(10.0 * math.log10(max(powers[1], 1e-24) / max(powers[0], 1e-24))),
        "speech_power": float(powers[0]),
        "peak": peak,
        "samples": total,
    }


def public_metrics(m):
    return {k: v for k, v in m.items() if k not in ("speech_power", "peak", "samples")}


def clean_voice(input_path, out_path, max_speech_loss_db=3.0, json_out=None):
    """Run the guarded dialogue cleanup from `input_path` to `out_path`. Returns report dict."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("ffmpeg is required on PATH")
    src, dst = Path(input_path).resolve(), Path(out_path).resolve()
    if src == dst:
        raise ValueError("output must be a new file distinct from input")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vd-voice-clean-") as temp:
        current = Path(temp) / "source.wav"
        p = subprocess.run(
            [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(src), "-ac", "2", "-ar", str(RATE), "-c:a", "pcm_f32le", str(current)],
            capture_output=True, creationflags=NO_WINDOW,
        )
        if p.returncode:
            raise ValueError(f"cannot read {src.name} as sound: " + p.stderr.decode(errors="replace").strip()[-300:])
        initial = measure_file(ffmpeg, current)
        nf = max(-80.0, min(-20.0, initial["noise_floor_p10_dbfs"]))
        filters = [(name, graph.format(nf=nf)) for name, graph in STAGES]
        rows = []
        refused = None
        before = initial
        for index, (name, graph) in enumerate(filters + [("final_level", None)]):
            if graph is None:
                loud = before["loudness"]["integrated_lufs"]
                if loud is None or loud <= -70:
                    refused = "final level cannot be determined for silence"
                    break
                gain = max(-6.0, min(6.0, -20.0 - loud))
                graph = f"volume={gain:.6f}dB"
            candidate = Path(temp) / f"step-{index}.wav"
            subprocess.run(
                [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(current), "-ac", "2", "-ar", str(RATE), "-af", graph, "-c:a", "pcm_f32le", str(candidate)],
                check=True, creationflags=NO_WINDOW,
            )
            after = measure_file(ffmpeg, candidate)
            if after["samples"] != before["samples"]:
                raise ValueError("filter returned invalid audio length")
            loss = 10.0 * math.log10(max(before["speech_power"], 1e-30) / max(after["speech_power"], 1e-30))
            accepted = loss <= max_speech_loss_db
            rows.append({
                "step": name,
                "filter": graph,
                "before": public_metrics(before),
                "after": public_metrics(after),
                "speech_band_loss_db": round(loss, 4),
                "accepted": accepted,
            })
            if not accepted:
                refused = f"{name} exceeded speech-band loss limit ({loss:.2f} dB > {max_speech_loss_db:g} dB)"
                break
            current = candidate
            before = after
        if before["peak"] >= 1.0:
            refused = refused or "output reaches 0 dBFS; lower the level and listen"
        subprocess.run(
            [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(current), "-c:a", "pcm_s24le", "-map_metadata", "-1", "-bitexact", str(dst)],
            check=True, creationflags=NO_WINDOW,
        )
    report = {
        "input": str(src),
        "output": str(dst),
        "noise_floor_used_dbfs": round(nf, 3),
        "max_speech_loss_db_per_step": max_speech_loss_db,
        "steps": rows,
        "refused": refused,
        "exit_code": 1 if refused else 0,
        "limit": "A measured starting point; speech damage and intelligibility need listening. Unheard.",
    }
    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-speech-loss-db", type=float, default=3.0)
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    rep = clean_voice(a.input, a.out, max_speech_loss_db=a.max_speech_loss_db, json_out=a.json_out)
    print("Voice cleanup: " + (rep["refused"] or "steps applied") + f" -> {rep['output']}. Unheard.")
    return rep["exit_code"]


if __name__ == "__main__":
    import utf8  # noqa: F401
    sys.exit(main())
