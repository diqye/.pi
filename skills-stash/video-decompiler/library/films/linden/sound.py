"""The sound of Linden Library, and the film's clock. It is played on recorded instruments and has no noise in it: a
grand piano, a vibraphone and a glockenspiel on the landings, plucked strings for the bass, and a soft knock where the
picture stamps. (An earlier version made from sines and noise was the one fault the person who accepted the film found;
the beats did not move when it was replaced.) This file holds the film's one clock: the rate, the frames in a beat and
the number of beats (the first line below), and the table T of every beat the picture uses. It writes them to
kit/times.gen.ts, which the picture imports, and sets score.json's fps, duration and bpm from them.
  python sound.py     writes media/sound.wav (48 kHz stereo) and kit/times.gen.ts, and score.json's clock
Instruments (media/sounds, each with its LICENCE.txt): Salamander Grand Piano V2 by Alexander Holm, CC BY 3.0;
Versilian Community Sample Library vibraphone and glockenspiel, CC0; FluidR3_GM pizzicato strings by Frank Wen,
CC BY 3.0. A recording is read by ffmpeg, so MP3, WAV and FLAC all serve. 100 beats a minute: a beat is 36 frames."""
import json, pathlib, subprocess, wave
import numpy as np

SR, FPS, FB, BEATS = 48000, 60, 36, 50
FB = int((json.loads(pathlib.Path("score.json").read_text(encoding="utf-8")).get("music") or {}).get("fb") or FB)   # a track mapped by vd audio --tempo-map sets the beat
BEAT = FB / FPS
N = int(BEATS * BEAT * SR) + 4 * SR
STEMS = {k: [np.zeros(N), np.zeros(N)] for k in ("piano", "mallets", "bass", "touch")}

# ---- the film's events, in beats. The picture imports these (kit/times.gen.ts).
T = {
    "LABEL": 1.5, "OUT1": 3, "BOOK": 8, "OUT2": 10, "WALL": 12, "FLIPS": [13.5, 15.5, 17.5], "OUT3": 20, "CARD": 24, "OUT4": 28,
    "LANDS": [30, 32, 34, 36, 38], "END": 42, "SWATCH": [42.75, 43.75, 44.75, 45.75, 46.75],
}

# ---- the instruments: recorded notes, each played at the pitch asked for by reading the nearest recording faster or slower
NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
def midi_of(name): n = name[:-1]; return 12 * (int(name[-1]) + 1) + NAMES.index(n)
def kit(folder):
    out = {}
    for p in sorted(pathlib.Path("media/sounds", folder).iterdir()):
        if p.suffix not in (".mp3", ".wav", ".flac"): continue
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.float32).astype(np.float64); x = x / (np.abs(x).max() + 1e-9)
        first = int(np.argmax(np.abs(x) > 0.03)); out[midi_of(p.stem)] = x[max(0, first - 96):]      # start each recording 2 ms before its attack, so a note lands on its frame
    return out
PIANO, VIBES, GLOCK, PIZZ = kit("salamander-piano"), kit("vcsl-vibraphone"), kit("vcsl-glockenspiel"), kit("fluid-pizzicato_strings")
def lowpass(x, hz):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / np.sqrt(1 + (f / hz) ** 6); return np.fft.irfft(X, len(x))
def play(stem, bank, beat, midi, vel, hold, pan=0.0, soft=None, ring=1.2):
    """one note: `hold` beats held, then let go over `ring` seconds. vel 0 to 1 is how hard; a soft note is duller too"""
    src = min(bank, key=lambda m: abs(m - midi)); s = bank[src]
    ratio = 2 ** ((midi - src) / 12); n = int(min(len(s) / ratio, (hold * BEAT + ring * 3) * SR)); idx = np.arange(n) * ratio
    i = idx.astype(int); fr = idx - i; y = s[i] * (1 - fr) + s[np.minimum(i + 1, len(s) - 1)] * fr
    if soft is not None: y = lowpass(y, soft + 9000 * vel)
    env = np.ones(n); rel = int(hold * BEAT * SR)
    if rel < n: env[rel:] = np.exp(-np.arange(n - rel) / (ring * SR))
    a = int(round(beat * BEAT * SR)); m = min(n, N - a)
    if m <= 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    STEMS[stem][0][a:a + m] += y[:m] * env[:m] * vel * gl * 1.414; STEMS[stem][1][a:a + m] += y[:m] * env[:m] * vel * gr * 1.414
def pn(beat, midi, vel, hold=1.0): play("piano", PIANO, beat, midi, vel, hold, pan=(midi - 66) / 60, soft=3000, ring=0.9)       # low notes a little left, high a little right, as at a piano
def vb(beat, midi, vel, hold=2.0, pan=0.25): play("mallets", VIBES, beat, midi, vel, hold, pan=pan, ring=1.6)
def gk(beat, midi, vel, pan=-0.25): play("mallets", GLOCK, beat, midi, vel, 1.5, pan=pan, ring=1.4)
def pz(beat, midi, vel): play("bass", PIZZ, beat, midi, vel, 1.2, ring=0.7)
def touch(beat, vel=1.0):
    """something set down on a table: a soft low knock, no hiss. It marks a landing the way the stamp does in the picture"""
    t = np.arange(int(0.25 * SR)) / SR
    y = (np.sin(2 * np.pi * (70 * t + 20 * (1 - np.exp(-t * 40)) / 40)) * np.exp(-t * 26) + 0.25 * np.sin(2 * np.pi * 240 * t) * np.exp(-t * 60)) * np.minimum(1, t / 0.003)
    a = int(round(beat * BEAT * SR)); STEMS["touch"][0][a:a + len(y)] += y * vel; STEMS["touch"][1][a:a + len(y)] += y * vel

# notes, by name: E flat major
Eb2, Ab2, Bb2, C3, Eb3, F3, G3, Ab3, Bb3 = 39, 44, 46, 48, 51, 53, 55, 56, 58
C4, D4, Eb4, F4, G4, Ab4, Bb4, C5, D5, Eb5, F5, G5, Ab5, Bb5, C6, D6, Eb6 = 60, 62, 63, 65, 67, 68, 70, 72, 74, 75, 77, 79, 80, 82, 84, 86, 87
def run(b0, notes, v0, v1, step=0.5, hold=0.9):                          # notes one after another, growing or fading
    for i, m in enumerate(notes): pn(b0 + i * step, m, v0 + (v1 - v0) * i / max(1, len(notes) - 1), hold)
def chord(b, notes, vel, hold=3.0, roll=0.04):                           # a chord, rolled a little from the bottom
    for i, m in enumerate(notes): pn(b + i * roll, m, vel * (0.85 if i else 1.0), hold)

# ---- inside the paper (0 to 8): one piano, quietly. Three notes; the third is the label being put down.
chord(0, [Eb3, Bb3], 0.22, 6)                                         # the film's first frame: the one note no beat in T can move
pn(T["LABEL"] - 1.0, G4, 0.28, 1.5); pn(T["LABEL"] - 0.5, Bb4, 0.30, 1.5); pn(T["LABEL"], Eb5, 0.36, 2.5); touch(T["LABEL"], 0.35)
run(T["OUT1"], [Eb3, Bb3, Eb4, G4, Bb4, Eb5, G5, Bb5], 0.20, 0.42)       # the view backs out: the same chord, climbing
pn(T["OUT1"] + 4, F5, 0.40); pn(T["OUT1"] + 4.5, D5, 0.38)               # the climb's last two notes, falling
# ---- it is a book (8): C minor, and the date is stamped
chord(T["BOOK"], [C3, G3, Eb4, G4, Bb4], 0.46, 3.5); vb(T["BOOK"], G4, 0.5); pz(T["BOOK"], C3, 0.6); touch(T["BOOK"], 0.8)
pn(T["BOOK"] + 1, C5, 0.36); pn(T["BOOK"] + 1.5, Bb4, 0.32)
run(T["OUT2"], [C4, Eb4, G4, C5], 0.30, 0.46)                            # out again, a shorter climb
# ---- the wall (12 to 20): it flows. A flat, then B flat; a pluck on every other beat; a vibraphone note where covers change
chord(T["WALL"], [Ab2, Eb3], 0.44, 3.8); vb(T["WALL"], Eb5, 0.55); touch(T["WALL"], 0.7)
for bar, (pat, low) in enumerate((([Ab4, C5, Eb5, G5, Eb5, C5, Ab4, C5], [Ab2, Eb3]), ([Bb4, D5, F5, Bb5, F5, D5, Bb4, D5], [Bb2, F3]))):
    b0 = T["WALL"] + bar * 4
    if bar: chord(b0, low, 0.42, 3.8)
    run(b0 + (0.5 if not bar else 0), pat[(1 if not bar else 0):], 0.34, 0.40)
    for q, m in ((0, low[0]), (2, low[1])): pz(b0 + q, m, 0.55)
for b, m in zip(T["FLIPS"], (G5, F5, Eb5)): vb(b, m, 0.42, 1.5, pan=0.5)
# ---- out to the card (20 to 24): a scale up to it
chord(T["OUT3"], [C3, G3], 0.40, 3.5); pz(T["OUT3"], C3, 0.5)
run(T["OUT3"], [G4, Ab4, Bb4, C5, D5, Eb5, F5, G5], 0.30, 0.50)
# ---- the card (24 to 28): home. A short tune while the name is signed.
chord(T["CARD"], [Eb2, Bb2, Eb3, G4, Bb4, Eb5], 0.52, 3.8); vb(T["CARD"], Bb4, 0.5); vb(T["CARD"] + 0.04, Eb5, 0.5); pz(T["CARD"], Eb2 + 12, 0.6); touch(T["CARD"], 0.8)
SIGN = T["CARD"] + 1                                                     # the name is signed from a beat after CARD, as the picture signs it (levels.tsx, card)
for b, m, v in ((0, G5, 0.40), (0.5, F5, 0.36), (1, Eb5, 0.38), (1.5, Bb4, 0.32), (2, C5, 0.36), (2.5, Bb4, 0.32)): pn(SIGN + b, m, v, 1.2)
chord(SIGN + 1, [Ab2, Eb3], 0.34, 1.0); chord(SIGN + 2, [Bb2, F3], 0.34, 1.0)
run(T["OUT4"], [Bb3, D4, F4, Ab4], 0.32, 0.46)                            # the pick-up into the five grounds
chord(T["OUT4"], [Bb2, F3], 0.38, 1.8)
# ---- five grounds (30 to 38), a step up each time: E flat, F minor, G minor, A flat, B flat. Each lands with a bell.
STEPS = [([Eb3, Bb3, Eb4, G4, Bb4], G5), ([F3, C4, F4, Ab4, C5], Ab5), ([G3, D4, G4, Bb4, D5], Bb5), ([Ab3, Eb4, Ab4, C5, Eb5], C6), ([Bb3, F4, Bb4, D5, F5], D6)]
for i, (b, (ch, top)) in enumerate(zip(T["LANDS"], STEPS)):
    chord(b, ch, 0.46 + 0.03 * i, 1.7, roll=0.03); gk(b, top, 0.30 + 0.02 * i); vb(b, top - 12, 0.42); pz(b, ch[0] - 12 if ch[0] - 12 >= 38 else ch[0], 0.6); touch(b, 0.6)
    if i < 4: nxt = STEPS[i + 1][0]; pn(b + 1.0, nxt[2] - 2, 0.34, 0.6); pn(b + 1.5, nxt[2] - 1 if i == 0 else nxt[2] - 2 + (1 if i % 2 else 0), 0.36, 0.6)
# ---- the last backing-out (38 to 42) and the mark (42): the chord that was waited for
run(T["LANDS"][4] + 1, [F4, Bb4, D5, F5, Ab5, Bb5], 0.34, 0.50)
chord(T["END"], [Eb2, Bb2, Eb3, G4, Bb4, Eb5, G5], 0.60, 7.0, roll=0.05); vb(T["END"], Eb5, 0.6, 4); gk(T["END"], Eb6, 0.36); pz(T["END"], Eb2 + 12, 0.65); touch(T["END"], 0.9)
for b, m in zip(T["SWATCH"], (Bb5, G5, Eb5, G5, Bb5)): gk(b, m, 0.22, pan=0.0); vb(b, m - 12, 0.30, 1.2, pan=0.4)      # a paper, a note
chord(T["END"] + 5.5, [Eb2, Eb3], 0.30, 3.0)                            # the low E flat after the last paper lands

# ---- the mix
GAIN = {"piano": 1.0, "mallets": 0.8, "bass": 0.75, "touch": 0.5}
L = sum(STEMS[k][0] * GAIN[k] for k in STEMS); R = sum(STEMS[k][1] * GAIN[k] for k in STEMS)
mix = np.stack([L, R], 1); mix *= 0.8 / np.abs(mix).max()              # no squashing: the loudest chord sits well under the ceiling, and only its very top is rounded
mix = np.tanh(mix * 0.9) / np.tanh(0.9)
end = int(BEATS * BEAT * SR); fade = int(2.2 * SR); mix = mix[:end]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix *= 0.7 / np.abs(mix).max()
out = pathlib.Path("media"); raw = out / "sound-raw.wav"; final = out / "sound.wav"
with wave.open(str(raw), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype("<i2").tobytes())
TARGET = -17.5
p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true", "-ar", str(SR), "-c:a", "pcm_s16le", str(final)], check=True)
raw.unlink()

# ---- the one clock, written for the picture (kit/times.gen.ts) and for vd: the rate, the beat, the length, the events,
# and the named events vd sound finds in the mix (CUES, in seconds). The cues are the struck hits: the knock under every
# stamp (the label, the date, the wall's words, MEMBER, the five numbers), the bell on each ground, the chord on the name.
# The softer entries on named beats (the climbing runs at OUT1 to OUT4, the vibraphone on FLIPS, the swatch notes) are
# placed from the same numbers, but they start under a chord still ringing, so vd sound cannot find where they begin.
# score.json's fps, duration and bpm are set from the same numbers, so nothing else holds the clock.
CLOCK = {"FPS": FPS, "FB": FB, "BEATS": BEATS, "DURATION": round(BEATS * BEAT, 6), "BPM": round(60 / BEAT, 6)}
CUES = [[n, T[n]] for n in ("LABEL", "BOOK", "WALL", "CARD", "END")] + [[f"LANDS[{i}]", b] for i, b in enumerate(T["LANDS"])]
CUES = sorted(([n, round(b * BEAT, 4)] for n, b in CUES), key=lambda c: c[1])
pathlib.Path("kit/times.gen.ts").write_text("// generated by sound.py: the film's clock and its events in beats, the same numbers the sound was made from\n"
                                            + "".join(f"export const {k} = {json.dumps(v)};\n" for k, v in (("CLOCK", CLOCK), ("TIMES", T), ("CUES", CUES))), encoding="utf-8", newline="\n")
score = pathlib.Path("score.json"); s = json.loads(score.read_text(encoding="utf-8"))
if (s.get("fps"), s.get("duration"), s.get("bpm")) != (FPS, CLOCK["DURATION"], CLOCK["BPM"]):          # the score's clock is this one
    s.update(fps=FPS, duration=CLOCK["DURATION"], bpm=CLOCK["BPM"]); score.write_text(json.dumps(s, indent=1), encoding="utf-8", newline="\n")
mono = mix.mean(1); bar = int(4 * BEAT * SR)
rows = [20 * np.log10(np.sqrt((mono[i:i + bar] ** 2).mean()) + 1e-9) for i in range(0, len(mono) - bar + 1, bar)]
print(f"{final}: {BEATS * BEAT:.1f} s; before levelling {m['input_i']} LUFS, true peak {m['input_tp']} dBTP, range {m['input_lra']} LU; levelled to {TARGET} LUFS")
print("level each bar (dB):", " ".join(f"{r:4.0f}" for r in rows))
for k in STEMS:
    s = (STEMS[k][0] + STEMS[k][1]) * GAIN[k] / 2; print(f"  {k:7s} rms {20 * np.log10(np.sqrt((s[:end] ** 2).mean()) + 1e-9):6.1f} dB  peak {20 * np.log10(np.abs(s).max() + 1e-9):6.1f} dB")
X = np.abs(np.fft.rfft(mono)) ** 2; fr = np.fft.rfftfreq(len(mono), 1 / SR); tot = X.sum()
print("  ".join(f"{lo}-{hi} Hz {100 * X[(fr >= lo) & (fr < hi)].sum() / tot:.0f}%" for lo, hi in [(20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 16000)]))
