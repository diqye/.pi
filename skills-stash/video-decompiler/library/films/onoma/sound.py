"""The sound of Onoma, built with no picture. In this film the soundtrack is the product's output: each typed word is
heard as the sound it names, and then the same sounds play together on one tempo (BOARD.md). Every event the picture
shows has its beat in the table T below, and this file writes that table to kit/times.gen.ts, so the film and the sound
read one clock.
  python sound.py     writes media/sound.wav (48 kHz stereo), kit/times.gen.ts (the clock, the table, the typed words,
                      the cues and the meant silence) and kit/waves.gen.ts (the shape of each sound and of each track of
                      the mix, taken from these samples, so what the film draws is what is heard)
Everything is made here from noise and sines. No samples, no service. 120 beats a minute: a beat is 30 frames."""
import json, pathlib, subprocess, wave
import numpy as np

SR, FPS, FB, BEATS = 48000, 60, 30, 58
FB = int((json.loads(pathlib.Path("score.json").read_text(encoding="utf-8")).get("music") or {}).get("fb") or FB)   # a track mapped by vd audio --tempo-map sets the beat
BEAT = FB / FPS
N = int(BEATS * BEAT * SR) + SR

# ---- the film's events, in beats. The picture imports these (kit/times.gen.ts); move one here, run this file, and the
# sound and the picture move together.
T = {
    "PARTS": {"rain": 0, "thunder": 4, "steps": 8, "clap": 12, "heart": 16, "hush": 20,                  # BOARD.md's beats table
              "name": 24, "ask": 30, "mix": 34, "more": 42, "take": 48, "end": 52},
    "TYPE": {"rain": [0.1, 4.5], "thunder": [3.7, 3.4], "steps": [6.9, 2.4], "clap": [12.4, 1.5],         # each word: the beat of its
             "heart": [15.05, 2.1], "hush": [20.05, 4.5], "request": [30.5, 1.64], "more": [40.2, 2.2]},   # first key, frames a key
    "RAIN": 1, "BOLT": 5, "STEPS": [9, 10, 11, 12], "CLAPS": [14, 14.5, 15, 15.5],                         # the sounds the words ask for
    "PULSES": [17, 19], "DUB": 0.56, "HUSH": 21, "SILENT": [22.5, 24],                                      # DUB: lub to dub, in beats
    "NAME": [24, 24.5, 25, 25.5, 26], "TAG": [27, 27.2, 27.4, 28.2, 28.4],                                  # the name said, and its line
    "LOOP": 4,                                                                                               # beats in the mix's loop
    "CLAIM": [48.6, 48.8, 49, 49.8, 50, 50.25, 50.5], "FILE": 49.5,                                         # take it away
    "NAME2": [52.5, 53, 53.5, 54, 54.5], "TAG2": [55.2, 55.4, 55.6, 56.2, 56.4],                            # the end
}
TEXT = {"rain": "rain.", "thunder": "thunder.", "steps": "footsteps.", "clap": "a clap, with echo.", "heart": "a heartbeat.",
        "hush": "hush.", "request": "rain, footsteps, a clap with echo, a heartbeat · 120 bpm", "more": "+ a music box"}
P = T["PARTS"]
rng = np.random.default_rng(5)
L = np.zeros(N); R = np.zeros(N)

def tt(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8) / np.sqrt(1 + (f / hi) ** 8); return np.fft.irfft(X, len(x))
def put(x, beat, gain=1.0, pan=0.0):
    a = int(round(beat * BEAT * SR)); n = min(len(x), N - a)
    if n <= 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[a:a + n] += x[:n] * gain * gl * 1.414; R[a:a + n] += x[:n] * gain * gr * 1.414

# ---- the sounds a word can ask for
def rain(d):
    t = tt(d); x = band(rng.standard_normal(len(t)), 1800, 9000) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.7 * t + 1))
    for _ in range(int(26 * d)):                                    # drops: short bright blips at random
        a = int(rng.random() * (len(t) - 2400)); f = 1600 + 3200 * rng.random(); k = np.arange(2400) / SR
        x[a:a + 2400] += 1.6 * np.sin(2 * np.pi * f * k) * np.exp(-k / 0.006) * rng.random()
    return x * np.minimum(1, t / 0.18) * np.minimum(1, (d - t) / 0.5) * 0.5
def thunder(d=3.0):
    t = tt(d); x = np.zeros(len(t))
    for at, g in [(0, 1.0), (0.07, 0.6), (0.16, 0.45), (0.31, 0.3)]:  # the crack, and its tearing
        a = int(at * SR); k = t[:len(t) - a]
        x[a:] += g * band(rng.standard_normal(len(k)), 500, 6000) * np.exp(-k / 0.05)
    roll = band(rng.standard_normal(len(t)), 30, 220) * 5 * np.exp(-t / 0.9) * (0.6 + 0.4 * np.sin(2 * np.pi * 2.3 * t) ** 2)
    sub = np.sin(2 * np.pi * 48 * t) * np.exp(-t / 0.6) * 0.6
    return (x + roll + sub) * np.minimum(1, (d - t) / 0.3) * 0.6
def step(g=1.0):
    t = tt(0.28); ph = 2 * np.pi * np.cumsum(46 + 40 * np.exp(-t / 0.03)) / SR
    return (0.6 * np.sin(ph) * np.exp(-t / 0.07) + band(rng.standard_normal(len(t)), 150, 700) * 3.2 * np.exp(-t / 0.02) + band(rng.standard_normal(len(t)), 1200, 2600) * 1.2 * np.exp(-t / 0.012)) * g * 0.9
def clap(g=1.0):
    t = tt(0.22); x = np.zeros(len(t))
    for at in (0, 0.009, 0.019):
        a = int(at * SR); k = t[:len(t) - a]; x[a:] += band(rng.standard_normal(len(k)), 900, 3600) * np.exp(-k / 0.012)
    x += band(rng.standard_normal(len(t)), 1000, 3000) * 0.5 * np.exp(-t / 0.06)
    return x * g * 2.2
def clap_echo():
    """one clap and three returns, on the beats in T["CLAPS"], each duller and smaller"""
    x = np.zeros(int(2.2 * SR))
    for i, g in enumerate((1.0, 0.5, 0.27, 0.14)):
        c = clap(g) if i == 0 else band(clap(g), 300, 2600 - 500 * i)
        a = int((T["CLAPS"][i] - T["CLAPS"][0]) * BEAT * SR); x[a:a + len(c)] += c
    return x
def heart():
    """lub-dub"""
    x = np.zeros(int(0.8 * SR))
    for at, f, d, g in ((0, 52, 0.13, 1.0), (T["DUB"] * BEAT, 66, 0.09, 0.7)):
        t = tt(d * 2.5); a = int(at * SR)
        x[a:a + len(t)] += g * np.sin(2 * np.pi * f * t) * np.sin(np.pi * np.minimum(1, t / (d * 2.5))) ** 2 * np.exp(-t / d)
    return x * 0.9 + band(x, 90, 400) * 0.6
def hush(d=1.1):
    t = tt(d); return band(rng.standard_normal(len(t)), 2200, 7500) * np.minimum(1, t / 0.08) * np.exp(-t / 0.33) * 0.7
def bell(m, d=1.2):
    t = tt(d); f = hz(m)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.4) + 0.5 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.12) + 0.25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.05)
    return x * np.minimum(1, t / 0.002) * 0.5
def pad(ms, d, g=1.0):
    t = tt(d); x = np.zeros(len(t))
    for m in ms:
        for det in (-0.003, 0.003): x += np.sin(2 * np.pi * hz(m) * (1 + det) * t) + 0.2 * np.sin(2 * np.pi * 2 * hz(m) * (1 + det) * t)
    return x / (2 * len(ms)) * np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.8) * g
def key(g=1.0):
    t = tt(0.03); return (np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.003) + band(rng.standard_normal(len(t)), 3000, 9000) * 0.5 * np.exp(-t / 0.0015)) * g

JNOTES = [74, 78, 81, 83, 86]
def jingle(beats):
    """the name: five letters, five notes on the given beats, and under each the sound that letter stands for"""
    minis = [rain(0.45), thunder(0.7), step(), clap(1.0), heart()]
    for i, (m, s, g, b) in enumerate(zip(JNOTES, minis, (0.8, 0.45, 0.6, 0.45, 0.85), beats)):
        put(bell(m, 1.4), b, 0.42, pan=-0.3 + 0.15 * i); put(s, b, g, pan=-0.3 + 0.15 * i)

def typing(name, g=0.16, keys=None):
    """a key for each letter of TEXT[name], from its first beat, `per` frames apart: the picture types it on the same frames"""
    b0, per = T["TYPE"][name]
    for i in range(len(TEXT[name]) if keys is None else keys): put(key(), b0 + i * per / FB, g, pan=-0.1 + 0.2 * (i % 3) / 2)

SOUNDS = {"rain": rain(1.9), "thunder": thunder(), "step": step(), "clap": clap_echo(), "heart": heart(), "hush": hush()}

# ---- the room: a breath of air and one low note under the six words, so the gaps between sounds are not dead. It stops for the hush.
ROOM = 22.8 * BEAT   # 11.4 s at the film's own beat: in beats, so a track mapped at another tempo keeps the room to the hush
room = pad([38, 50, 57], ROOM, 0.5) + band(rng.standard_normal(int(ROOM * SR)), 300, 2500) * 0.012 * np.minimum(1, tt(ROOM) / 0.5)
put(room, 0, 0.5)
# ---- the six words, each heard as it lands
typing("rain"); put(SOUNDS["rain"], T["RAIN"], 0.9)
typing("thunder"); put(SOUNDS["thunder"], T["BOLT"], 1.0)
typing("steps")
for i in range(4): put(step(), T["STEPS"][i], 0.95, pan=-0.6 + 0.4 * i)
typing("clap"); put(SOUNDS["clap"], T["CLAPS"][0], 0.9, pan=0.1)
typing("heart"); put(SOUNDS["heart"], T["PULSES"][0], 1.0); put(SOUNDS["heart"], T["PULSES"][1], 1.0)
typing("hush", 0.1); put(SOUNDS["hush"], T["HUSH"], 0.8)
# ---- the name: the first chord, and the request typed. The accepted cut struck 55 keys for the request's 56 letters,
# so its last letter is typed without a sound; `keys=` keeps that sound as it was. Drop it and every letter has its key.
put(pad([50, 57, 62, 66, 69], 3.2), P["name"], 0.5); jingle(T["NAME"])
typing("request", 0.13, keys=len(TEXT["request"]) - 1); put(pad([50, 57, 62, 66], 2.6), P["ask"] - 0.5, 0.2)

# ---- the mix: the same sounds on one grid. A bar is T["LOOP"] beats. Tracks are kept apart so each can be drawn.
LOOP = T["LOOP"]
BAR = int(LOOP * BEAT * SR)
def track(fn):
    x = np.zeros(BAR + SR); fn(x); return x[:BAR]        # one bar; tails are cut, the loop restarts them
def at(x, beat, s, g=1.0):
    a = int(beat * BEAT * SR); n = min(len(s), len(x) - a); x[a:a + n] += s[:n] * g
t_rain = track(lambda x: at(x, 0, rain(LOOP * BEAT) * (0.55 + 0.45 * np.abs(np.sin(2 * np.pi * (1 / BEAT) * tt(LOOP * BEAT)))), 0.7))    # rain, breathing on the half beats, a loop long
t_step = track(lambda x: [at(x, b, step(), 1.0) for b in range(LOOP)])
t_clap = track(lambda x: [at(x, b, clap(1.0), 0.8) or at(x, b + 0.5, band(clap(0.5), 300, 2000), 0.8) for b in (1, 3)])
t_heart = track(lambda x: [at(x, b, heart(), 0.95) for b in (0, 2)])
TUNE = [(0, 74), (0.5, 78), (1, 81), (1.5, 83), (2, 81), (2.5, 78), (3, 86), (3.5, 81)]                               # one bar, D major
t_box = track(lambda x: [at(x, b, bell(m, 0.9), 0.8) for b, m in TUNE])
MIX0, MIX1, BOX0 = P["mix"], P["end"], P["more"]       # the picture folds the tracks into one line at P["take"]; the sound plays on to the end
def part(x, n):
    y = x[:n].copy()
    if n < len(x): r = int(0.03 * SR); y[-r:] *= np.linspace(1, 0, r)
    return y
for bar in range(5):
    b0 = MIX0 + bar * LOOP
    if b0 >= MIX1: break
    n = int(min(LOOP, MIX1 - b0) * BEAT * SR)
    put(part(t_rain, n), b0, 0.55, pan=0.3); put(part(t_step, n), b0, 0.9); put(part(t_clap, n), b0, 0.75, pan=0.25); put(part(t_heart, n), b0, 0.9, pan=-0.15)
put(pad([38, 50, 57, 62, 66], 9.2), MIX0, 0.22)
typing("more", 0.12)
for bar in range(5):
    b0 = BOX0 + bar * LOOP
    if b0 >= MIX1: break
    n = int(min(LOOP, MIX1 - b0) * BEAT * SR); put(part(t_box, n), b0, 0.7, pan=-0.2)
# ---- take it away, and the end
put(pad([50, 57, 62, 66, 69], 3.4), P["end"], 0.45); jingle(T["NAME2"])

# ---- the silence under "hush." (T["SILENT"]), and the mix
g = np.ones(N); a, b = int(T["SILENT"][0] * BEAT * SR), int(T["SILENT"][1] * BEAT * SR); r = int(0.05 * SR)
g[a:b] = 0.0; g[a - r:a] = np.linspace(1, 0, r); g[b:b + r] = np.linspace(0, 1, r)
mix = np.stack([L * g, R * g], 1); mix = np.tanh(mix * 1.4) / np.tanh(1.4)
end = int(BEATS * BEAT * SR); fade = int(1.0 * SR); mix = mix[:end]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix *= 0.7 / np.abs(mix).max()
out = pathlib.Path("media"); out.mkdir(exist_ok=True); raw = out / "sound-raw.wav"; final = out / "sound.wav"
with wave.open(str(raw), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype("<i2").tobytes())
TARGET = -15.0
p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true", "-ar", str(SR), "-c:a", "pcm_s16le", str(final)], check=True)
raw.unlink()

# ---- the shapes the film draws: each sound's own loudness over its length, peak in each of `bins` slices, 0 to 1
def shape(x, bins):
    n = len(x) // bins; e = np.abs(x[:n * bins]).reshape(bins, n).max(1); return [round(float(v), 3) for v in e / (e.max() + 1e-9)]
waves = {"thunder": shape(SOUNDS["thunder"], 160), "clap": shape(SOUNDS["clap"], 160), "heart": shape(SOUNDS["heart"], 80),
         "tracks": {"rain": shape(t_rain, 200), "footsteps": shape(t_step, 200), "clap + echo": shape(t_clap, 200), "heartbeat": shape(t_heart, 200), "music box": shape(t_box, 200)},
         "sum": shape(0.55 * t_rain + 0.9 * t_step + 0.75 * t_clap + 0.9 * t_heart + 0.7 * t_box, 200),
         "tune": TUNE}
pathlib.Path("kit/waves.gen.ts").write_text("// generated by sound.py: the shapes of the sounds in media/sound.wav\nexport const WAVES = " + json.dumps(waves) + ";\n", encoding="utf-8", newline="\n")

# ---- the one clock, written for the picture (kit/times.gen.ts) and for vd: the rate, the beat, the length, the events,
# the typed words, the cues (each named event a sound starts on, in seconds), which vd sound checks the mix against, and
# the silence that is meant. One line each, `export const NAME = JSON;`, so vd reads the same file the picture imports.
CLOCK = {"FPS": FPS, "FB": FB, "BEATS": BEATS, "DURATION": round(BEATS * BEAT, 6), "BPM": round(60 / BEAT, 6)}
CUES = [["RAIN", T["RAIN"]], ["BOLT", T["BOLT"]], ["HUSH", T["HUSH"]], ["MIX", P["mix"]], ["MORE", P["more"]], ["END", P["end"]]]
CUES += [[f"{k}[{i}]", b] for k in ("STEPS", "CLAPS", "PULSES", "NAME", "NAME2") for i, b in enumerate(T[k])]
CUES = sorted(([n, round(b * BEAT, 4)] for n, b in CUES), key=lambda c: c[1])
RESTS = [["hush", T["SILENT"][0] * BEAT, T["SILENT"][1] * BEAT]]
pathlib.Path("kit/times.gen.ts").write_text("// generated by sound.py: the film's clock and its events in beats, the same numbers the sound was made from\n"
                                            + "".join(f"export const {k} = {json.dumps(v)};\n" for k, v in (("CLOCK", CLOCK), ("TIMES", T), ("TEXT", TEXT), ("CUES", CUES), ("RESTS", RESTS))),
                                            encoding="utf-8", newline="\n")
score = pathlib.Path("score.json"); s = json.loads(score.read_text(encoding="utf-8"))
if (s.get("fps"), s.get("duration"), s.get("bpm")) != (FPS, CLOCK["DURATION"], CLOCK["BPM"]):          # the score's clock is this one
    s.update(fps=FPS, duration=CLOCK["DURATION"], bpm=CLOCK["BPM"]); score.write_text(json.dumps(s, indent=1), encoding="utf-8", newline="\n")
mono = mix.mean(1); half = SR // 2
rows = [20 * np.log10(np.sqrt((mono[i:i + half] ** 2).mean()) + 1e-9) for i in range(0, len(mono) - half + 1, half)]
print(f"{final}: {BEATS * BEAT:.1f} s; before levelling {m['input_i']} LUFS, true peak {m['input_tp']} dBTP, range {m['input_lra']} LU; levelled to {TARGET} LUFS")
print("level each half second (dB):"); print(" ".join(f"{r:4.0f}" for r in rows))
X = np.abs(np.fft.rfft(mono)) ** 2; fr = np.fft.rfftfreq(len(mono), 1 / SR); tot = X.sum()
print("  ".join(f"{lo}-{hi} Hz {100 * X[(fr >= lo) & (fr < hi)].sum() / tot:.0f}%" for lo, hi in [(20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 16000)]))
