"""The sound of Plus One, written before the picture (BOARD.md, "Sound"). Music first: one chord a bar in F major, a
pattern under it, and the replies as its tune. Every event the picture shows has its beat here, and this file writes
those beats to kit/times.gen.ts, so the film and the sound read one clock.
  python sound.py     writes media/sound.wav (48 kHz stereo) and kit/times.gen.ts
Everything is made here from sines and noise. No samples, no service. 112.5 beats a minute: a beat is 32 frames."""
import json, pathlib, subprocess, wave
import numpy as np

SR, FPS, FB, BEATS = 48000, 60, 32, 72
FB = int((json.loads(pathlib.Path("score.json").read_text(encoding="utf-8")).get("music") or {}).get("fb") or FB)   # a track mapped by vd audio --tempo-map sets the beat
BEAT = FB / FPS
N = int(BEATS * BEAT * SR) + SR
rng = np.random.default_rng(11)
STEMS = {k: [np.zeros(N), np.zeros(N)] for k in ("keys", "bass", "drums", "tune", "fx")}

# ---- the film's events, in beats. The picture imports these (kit/times.gen.ts).
T = {
    "BUBBLES": [0, 0.75, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5],
    "COLLAPSE": 6.5, "CARET": 7.5625, "NAME": 8, "TYPE0": 8.5, "TYPE_PER": 2.3, "RETURN": 12, "PARTS": [12.05, 12.11, 12.17], "FLY": 18, "EMPTY": 12.6, "ADDS": [13.5, 14, 14.5, 15],
    "DRESS": 16, "OPEN": 20, "LOOKS": [21.5, 24, 25.75, 29], "PICK": 32, "SKY": [33.5, 35.25],
    "HOST": 34, "SEND": 36, "ADD": 36.5, "ROLL0": 37, "ROLL_STEP": 1 / 12, "READY": 39, "PRESS": 40,
    "GUEST": 41.5, "TAP": 44.25,
    "REPLIES": [45, 46.5, 47.5, 48, 49, 49.5, 50, 50.5, 51, 51.5, 52, 52.5, 53, 53.5, 54, 54.5, 55, 55.5, 56],
    "ASK": 57, "YES": 59.5, "LAST": 60, "AFTER": [61, 62.5], "END": 64, "MARK": 67, "FARS": [69, 70.2],
    "CORNERS": [48, 50, 52, 54, 56, 58],   # (picture) a firework in each corner while the replies come; the last, between the question and its yes, is heard
}
LINE = "Mira’s 30th. Rooftop, Saturday 13th at 8."

def tt(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8) / np.sqrt(1 + (f / hi) ** 8); return np.fft.irfft(X, len(x))
def put(stem, x, beat, gain=1.0, pan=0.0):
    a = int(round(beat * BEAT * SR)); n = min(len(x), N - a)
    if n <= 0 or a < 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    STEMS[stem][0][a:a + n] += x[:n] * gain * gl * 1.414; STEMS[stem][1][a:a + n] += x[:n] * gain * gr * 1.414

# ---- the instruments
def ep(m, d=1.6, bright=1.0):
    """an electric piano note: a sine bent by itself, with a short tine on top"""
    t = tt(d); f = hz(m)
    x = np.sin(2 * np.pi * f * t + 1.3 * bright * np.exp(-t / 0.22) * np.sin(2 * np.pi * f * t)) * np.exp(-t / (0.9 * d))
    x += 0.34 * bright * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.09) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.5)
    return x * np.minimum(1, t / 0.004) * np.minimum(1, (d - t) / 0.08) * 0.32
def chord(ms, d=1.6, bright=1.0):
    x = np.zeros(int(d * SR))
    for i, m in enumerate(ms):
        n = ep(m, d, bright); a = int(i * 0.008 * SR); x[a:] += n[:len(x) - a]         # rolled a little, as a hand does
    return x / np.sqrt(len(ms))
def bass(m, d=0.5):
    t = tt(d); f = hz(m)
    x = 0.6 * np.sin(2 * np.pi * f * t) + 0.8 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.2) + 0.35 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.1)
    return x * np.minimum(1, t / 0.006) * np.exp(-t / (0.7 * d)) * np.minimum(1, (d - t) / 0.04) * 0.5
def kick(g=1.0):
    t = tt(0.3); ph = 2 * np.pi * np.cumsum(46 + 70 * np.exp(-t / 0.03)) / SR
    return (np.sin(ph) * np.exp(-t / 0.09) + band(rng.standard_normal(len(t)), 1500, 5000) * 0.5 * np.exp(-t / 0.005)) * g * 0.8
def hat(g=1.0, d=0.03):
    t = tt(0.12); return band(rng.standard_normal(len(t)), 6500, 12000) * np.exp(-t / d) * g * 0.5
def shaker(g=1.0):
    t = tt(0.11); return band(rng.standard_normal(len(t)), 3200, 9000) * np.minimum(1, t / 0.012) * np.exp(-t / 0.035) * g * 0.45
def clap(g=1.0):
    t = tt(0.24); x = np.zeros(len(t))
    for at in (0, 0.009, 0.02):
        a = int(at * SR); k = t[:len(t) - a]; x[a:] += band(rng.standard_normal(len(k)), 900, 3600) * np.exp(-k / 0.012)
    x += band(rng.standard_normal(len(t)), 1000, 3000) * 0.5 * np.exp(-t / 0.07)
    return x * g * 1.3
def snap(g=1.0):
    t = tt(0.1); return (band(rng.standard_normal(len(t)), 1800, 5200) * np.exp(-t / 0.011) * 1.6 + np.sin(2 * np.pi * 1900 * t) * np.exp(-t / 0.008) * 0.3) * g
def pluck(m, g=1.0, d=0.7):
    """a wooden bar: the tune of the replies"""
    t = tt(d); f = hz(m)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.2) + 0.32 * np.sin(2 * np.pi * 4.0 * f * t) * np.exp(-t / 0.035) + 0.12 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t / 0.012)
    return (x + band(rng.standard_normal(len(t)), 1500, 5000) * 0.25 * np.exp(-t / 0.004)) * np.minimum(1, t / 0.002) * g * 0.5
def bubble(f0, g=1.0):
    """a message arriving: a short upward chirp"""
    t = tt(0.09); ph = 2 * np.pi * np.cumsum(f0 * (1 + 1.3 * t / 0.09)) / SR
    return np.sin(ph) * np.sin(np.pi * np.minimum(1, t / 0.09)) ** 2 * g * 0.5
def knock(g=1.0):
    t = tt(0.16); return (np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.035) + band(rng.standard_normal(len(t)), 350, 1400) * 1.5 * np.exp(-t / 0.014)) * g * 0.7
def key(g=1.0):
    t = tt(0.03); return (np.sin(2 * np.pi * 2100 * t) * np.exp(-t / 0.003) + band(rng.standard_normal(len(t)), 3000, 9000) * 0.5 * np.exp(-t / 0.0015)) * g
def tick(g=1.0):
    t = tt(0.05); return np.sin(2 * np.pi * 1250 * t) * np.exp(-t / 0.008) * g * 0.6
def swell(d=1.0):
    t = tt(d); return band(rng.standard_normal(len(t)), 1800, 9000) * (t / d) ** 2.2 * np.minimum(1, (d - t) / 0.02) * 0.5
def whoosh(d=0.5):
    t = tt(d); x = rng.standard_normal(len(t)); k = np.sin(np.pi * t / d) ** 2
    return (band(x, 500, 2500) * (1 - t / d) + band(x, 2500, 8000) * (t / d)) * k * 0.6
def firework(g=1.0, d=1.1):
    """far off: a soft thump, then a crackle that thins out"""
    t = tt(d); x = band(rng.standard_normal(len(t)), 40, 260) * 5 * np.exp(-t / 0.08)
    cr = np.zeros(len(t))
    for _ in range(int(70 * g) + 20):
        a = int((0.06 + rng.random() ** 1.6 * (d - 0.15)) * SR); k = np.arange(min(700, len(t) - a)) / SR
        cr[a:a + len(k)] += rng.random() * np.sin(2 * np.pi * (2500 + 5000 * rng.random()) * k) * np.exp(-k / 0.002)
    x += cr * np.exp(-t / 0.45) * 0.9 + band(rng.standard_normal(len(t)), 2500, 9000) * 0.25 * np.exp(-t / 0.3) * np.minimum(1, t / 0.05)
    return x * g * 0.55

# ---- the harmony: one chord a bar from the bar the name arrives in (bar 3, beat 8). [voicing, bass note]
CH = [([57, 60, 64, 65], 41), ([57, 60, 62, 65], 38), ([58, 62, 65, 69], 34), ([58, 60, 65, 67], 36)]     # Fmaj7, Dm7, B flat maj7, C7sus
BAR0 = int(T["NAME"]) // 4                                         # that bar, counting from 0
def bar_chord(bar): return CH[(bar - BAR0) % 4]

for bar in range(BAR0, BEATS // 4):
    b0 = bar * 4; ms, root = bar_chord(bar)
    night = b0 >= T["PICK"]; ending = b0 >= T["END"]
    if ending:
        if bar == T["END"] // 4: put("keys", chord([53, 57, 60, 64, 67], 6.0, 0.7), b0, 0.9)
        continue
    # the keys: on one, and pushed before three
    put("keys", chord(ms + [ms[1] + 12], 1.5, 1.0 if night else 0.8), b0, 0.8, pan=-0.15)
    put("keys", chord([n + 12 for n in ms[1:]], 0.9, 0.7), b0 + 1.5, 0.5, pan=0.15)
    if night: put("keys", chord(ms[1:], 0.6, 0.7), b0 + 3, 0.45, pan=0.15)
    # the bass
    if b0 >= T["RETURN"]:
        for at, m, d in ((0, root, 0.7), (1.5, root, 0.4), (2.5, root + 7, 0.4), (3.5, root + 12, 0.3)):
            put("bass", bass(m, d), b0 + at, 0.8)
    # the drums: a shaker from the name; a kick on one and three and a snap on two and four from the looks; four on the floor from the choice
    for e in range(8):
        put("drums", shaker(0.55 if e % 2 else 0.3), b0 + e * 0.5, 2.6, pan=0.3)
    if b0 >= T["OPEN"] and not night:
        put("drums", kick(0.7), b0, 0.7); put("drums", kick(0.6), b0 + 2, 0.7); put("drums", snap(), b0 + 1, 0.8, pan=-0.2); put("drums", snap(), b0 + 3, 0.8, pan=-0.2)
    if night:
        for q in range(4):
            put("drums", kick(), b0 + q, 0.8); put("drums", hat(0.7), b0 + q + 0.5, 1.8, pan=-0.3)
        put("drums", clap(), b0 + 1, 0.8, pan=0.1); put("drums", clap(), b0 + 3, 0.8, pan=0.1)

# ---- bars 1 and 2, the mess: no chord. A tick on each beat until it collapses, and every message a chirp out of tune with the last.
for b in range(int(T["NAME"])): put("drums", tick(), b, 0.35 if b < T["COLLAPSE"] else 0.0)
for i, b in enumerate(T["BUBBLES"]):
    put("fx", bubble(520 * 2 ** (rng.uniform(-5, 6) / 12)), b, 0.8, pan=(-0.5 if i % 3 else 0.5))
for i in range(11):                                                # they fall into one point
    put("fx", bubble(900 * 2 ** (-i / 4.0), 0.7), T["COLLAPSE"] + i * 0.085, 0.6, pan=0.6 - 0.12 * i)
put("fx", tick(1.2), T["CARET"] + 6 / FB, 0.5)                      # the caret, on the top of its pop
# ---- the line is typed; return; its three parts land; what the app adds
for i, ch in enumerate(LINE):
    if ch != " ": put("fx", key(), T["TYPE0"] + i * T["TYPE_PER"] / FB, 0.14, pan=-0.3 + 0.6 * i / len(LINE))
put("fx", knock(), T["RETURN"], 0.9)
for b, m in zip(T["PARTS"], (65, 69, 72)): put("tune", pluck(m), b + T["FLY"] / FB, 0.6)    # each lands FLY frames after it leaves
for b, m in zip(T["ADDS"], (77, 76, 72, 74)): put("tune", pluck(m, 0.6), b, 0.4, pan=0.2)
# ---- the looks: each lands with a knock and three notes of its own; the choice is led in by a swell
MOTIFS = [(72, 76, 79), (69, 74, 77), (70, 74, 81), (72, 77, 84)]
for b, mo in zip(T["LOOKS"], MOTIFS):
    put("fx", whoosh(0.4), b - 0.8, 0.35); put("fx", knock(0.8), b, 0.7)
    for i, m in enumerate(mo): put("tune", pluck(m, 0.8), b + 0.25 * i, 0.5, pan=-0.2 + 0.2 * i)
put("fx", swell(BEAT * 1.5), T["PICK"] - 1.5, 0.5); put("fx", knock(1.2), T["PICK"], 0.9); put("fx", firework(0.5), T["PICK"], 0.5, pan=-0.3)
# ---- send: the faces answer the roll one by one, then the cards go out
for i in range(24):
    put("tune", pluck([65, 67, 69, 72, 74, 77][i % 6] + 12 * (i // 12), 0.5, 0.25), T["ROLL0"] + i * T["ROLL_STEP"], 0.3, pan=-0.6 + 1.2 * rng.random())
put("fx", tick(1.0), T["ADD"], 0.5)                              # "Add guests" is pressed
put("fx", knock(), T["PRESS"], 0.9); put("fx", whoosh(0.9), T["PRESS"] + 0.15, 0.6)
put("fx", whoosh(0.5), T["GUEST"], 0.3, pan=-0.5); put("fx", tick(1.1), T["TAP"], 0.6, pan=-0.5); put("fx", knock(0.6), T["TAP"], 0.4, pan=-0.5)     # one guest's phone: she presses "I'm in"
for i in range(24): put("fx", tick(0.7), T["PRESS"] + 0.5 + i * 0.045 + 0.02 * rng.random(), 0.25, pan=-0.7 + 1.4 * rng.random())
# ---- the replies: the tune. Four-note cells that climb; each reply also a far firework, the bigger ones on the bar
CELLS = [65, 69, 72, 77, 67, 72, 74, 79, 69, 72, 77, 81, 72, 77, 81, 84, 77, 81, 84]
for i, (b, m) in enumerate(zip(T["REPLIES"], CELLS)):
    put("tune", pluck(m, 1.0), b, 0.75, pan=-0.3 + 0.6 * ((i * 7) % 10) / 10)
    put("fx", firework(0.9 if b % 4 == 0 else 0.45), b + 0.06, 0.5 if b % 4 == 0 else 0.3, pan=-0.6 + 1.2 * ((i * 3) % 10) / 10)
put("fx", bubble(698.5), T["ASK"], 0.7, pan=-0.4)                   # "can I bring Theo?": the same chirp, in tune now
put("fx", tick(1.0), T["YES"], 0.5)
put("tune", pluck(84, 1.0), T["LAST"], 0.8); put("tune", pluck(89, 1.0), T["LAST"] + 0.25, 0.8); put("fx", firework(1.3, 1.6), T["LAST"], 0.9)
for i, b in enumerate(T["AFTER"]): put("fx", firework(0.6), b, 0.35, pan=0.5 - i)
put("fx", firework(0.6), T["CORNERS"][-1], 0.3, pan=-0.6)                       # the corner burst between the question and its yes
# ---- the end: the mark says "plus one" as two notes, a fourth apart; one far firework
put("fx", whoosh(0.7), T["END"], 0.35)
put("tune", pluck(72, 1.0, 1.2), T["MARK"], 0.8); put("tune", pluck(77, 1.0, 1.6), T["MARK"] + 0.5, 0.9); put("fx", knock(0.7), T["MARK"], 0.5)
put("keys", chord([53, 60, 64, 67, 69], 4.5, 0.6), T["MARK"], 0.7)
for i, b in enumerate(T["SKY"]): put("fx", firework(0.45, 1.2), b, 0.3 - 0.04 * i, pan=-0.5 + i)       # the two after the choice
for i, b in enumerate(T["FARS"]): put("fx", firework(0.5, 1.4), b, 0.3 - 0.08 * i, pan=0.4 - 0.9 * i)   # the far ones behind the name

# ---- the mix
GAIN = {"keys": 0.95, "bass": 0.85, "drums": 1.0, "tune": 1.3, "fx": 1.3}
L = sum(STEMS[k][0] * GAIN[k] for k in STEMS); R = sum(STEMS[k][1] * GAIN[k] for k in STEMS)
def air(x):                                                     # a shelf: what is above about 2.5 kHz comes up 5 dB, so the top is not dull
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 + 0.8 / (1 + (2500 / np.maximum(f, 1)) ** 4); return np.fft.irfft(X, len(x))
L, R = air(L), air(R)
mix = np.stack([L, R], 1); mix = np.tanh(mix * 1.2) / np.tanh(1.2)
end = int(BEATS * BEAT * SR); fade = int(1.6 * SR); mix = mix[:end]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix *= 0.7 / np.abs(mix).max()
out = pathlib.Path("media"); out.mkdir(exist_ok=True); raw = out / "sound-raw.wav"; final = out / "sound.wav"
with wave.open(str(raw), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype("<i2").tobytes())
TARGET = -15.0
p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-2.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-2.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true", "-ar", str(SR), "-c:a", "pcm_s16le", str(final)], check=True)
raw.unlink()

# ---- the one clock, written for the picture (kit/times.gen.ts) and for vd: the rate, the beat, the length, the events,
# and the cues (each named event a sound starts on, in seconds), which vd sound checks the mix against. One line each,
# `export const NAME = JSON;`, so vd reads the same file the picture imports.
CLOCK = {"FPS": FPS, "FB": FB, "BEATS": BEATS, "DURATION": round(BEATS * BEAT, 6), "BPM": round(60 / BEAT, 6)}
CUES = [[n, T[n]] for n in ("RETURN", "PICK", "ADD", "PRESS", "TAP", "ASK", "YES", "LAST", "MARK")]
CUES += [[f"LOOKS[{i}]", b] for i, b in enumerate(T["LOOKS"])] + [[f"REPLIES[{i}]", b] for i, b in enumerate(T["REPLIES"])]
CUES = sorted(([n, round(b * BEAT, 4)] for n, b in CUES), key=lambda c: c[1])
pathlib.Path("kit/times.gen.ts").write_text("// generated by sound.py: the film's clock and its events in beats, the same numbers the sound was made from\n"
                                            + "".join(f"export const {k} = {json.dumps(v)};\n" for k, v in (("CLOCK", CLOCK), ("TIMES", T), ("LINE", LINE), ("CUES", CUES))), encoding="utf-8", newline="\n")
score = pathlib.Path("score.json"); s = json.loads(score.read_text(encoding="utf-8"))
if (s.get("fps"), s.get("duration"), s.get("bpm")) != (FPS, CLOCK["DURATION"], CLOCK["BPM"]):          # the score's clock is this one
    s.update(fps=FPS, duration=CLOCK["DURATION"], bpm=CLOCK["BPM"]); score.write_text(json.dumps(s, indent=1), encoding="utf-8", newline="\n")
mono = mix.mean(1); bar = int(4 * BEAT * SR)
rows = [20 * np.log10(np.sqrt((mono[i:i + bar] ** 2).mean()) + 1e-9) for i in range(0, len(mono) - bar + 1, bar)]
print(f"{final}: {BEATS * BEAT:.1f} s; before levelling {m['input_i']} LUFS, true peak {m['input_tp']} dBTP, range {m['input_lra']} LU; levelled to {TARGET} LUFS")
print("level each bar (dB):", " ".join(f"{r:4.0f}" for r in rows))
for k in STEMS:
    s = (STEMS[k][0] + STEMS[k][1]) * GAIN[k] / 2; print(f"  {k:6s} rms {20 * np.log10(np.sqrt((s[:end] ** 2).mean()) + 1e-9):6.1f} dB  peak {20 * np.log10(np.abs(s).max() + 1e-9):6.1f} dB")
X = np.abs(np.fft.rfft(mono)) ** 2; fr = np.fft.rfftfreq(len(mono), 1 / SR); tot = X.sum()
print("  ".join(f"{lo}-{hi} Hz {100 * X[(fr >= lo) & (fr < hi)].sum() / tot:.0f}%" for lo, hi in [(20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 16000)]))
