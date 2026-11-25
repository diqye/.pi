"""The sound of "Weight", built with no picture: a sampled piano played from a list of notes, one thud, one knock.
  python sound-from-notes.py   writes sound.wav (48 kHz stereo) and prints where the loud moments are
Piano: Salamander Grand Piano V2 (CC-BY 3.0, Alexander Holm), fetched with `raea sounds get salamander/piano`."""
import subprocess, numpy as np, wave, sys
SR, DUR = 48000, 14.6
SAMPLES = {39: "Ds2", 45: "A2", 51: "Ds3", 57: "A3", 63: "Ds4", 69: "A4", 75: "Ds5", 81: "A5", 87: "Ds6"}
def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"media/sounds/salamander-piano/{name}.mp3", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)
cache = {}
def lowpass(x, hz):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / np.sqrt(1 + (f / hz) ** 6); return np.fft.irfft(X, len(x))
def note(buf, t, midi, vel, hold):
    src = min(SAMPLES, key=lambda m: abs(m - midi)); s = cache.setdefault(src, load(SAMPLES[src]))
    ratio = 2 ** ((midi - src) / 12); n = int(min(len(s) / ratio, (hold + 2.5) * SR)); idx = np.arange(n) * ratio
    i = idx.astype(int); fr = idx - i; i1 = np.minimum(i + 1, len(s) - 1); y = s[i] * (1 - fr) + s[i1] * fr
    y = lowpass(y, 1500 + 2600 * vel)                       # a felt piano: soft notes are dull, louder ones open a little
    env = np.ones(n); rel = int(hold * SR)
    if rel < n: env[rel:] = np.exp(-np.arange(n - rel) / (0.9 * SR))
    a = int(t * SR); m = min(n, len(buf) - a); buf[a:a + m] += y[:m] * env[:m] * vel
def thud(buf, t, gain=1.0):                                # iron meeting a floor: a low body that drops in pitch, and a short dull knock on top
    n = int(3.4 * SR); x = np.arange(n) / SR
    body = np.sin(2 * np.pi * (46 * x + 30 * (1 - np.exp(-x * 30)) / 30)) * (np.exp(-x * 5.5) + 0.05 * np.exp(-x * 1.1))
    rng = np.random.default_rng(7); knock = lowpass(rng.standard_normal(n), 420) * np.exp(-x * 34) * 2.2
    a = int(t * SR); buf[a:a + n] += (body * 1.0 + knock) * gain
def knock(buf, t, gain=0.22):                              # wood coming back to the floor
    n = int(0.22 * SR); x = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 310 * x) + 0.5 * np.sin(2 * np.pi * 760 * x)) * np.exp(-x * 42)
    a = int(t * SR); buf[a:a + n] += y * gain
buf = np.zeros(int(DUR * SR))
D2, A2, E3, Bb3, D4, E4, Fs4, A4, D5, A5 = 38, 45, 52, 58, 62, 64, 66, 69, 74, 81
for t, m, v, h in [(0.15, D2, .30, 3.2), (0.21, A2, .25, 3.2), (0.70, E3, .20, 2.8), (1.90, D2, .22, 1.6), (1.96, A2, .18, 1.6),
                   (5.75, Bb3, .30, 2.0),
                   (8.05, D4, .34, 0.8), (8.5, E4, .36, 0.8),
                   (9.85, D4, .44, 3.0), (10.65, Fs4, .46, 3.0), (11.45, A4, .50, 3.0), (12.25, D5, .56, 3.0), (13.20, A5, .50, 1.6), (13.20, D2, .40, 1.6), (13.24, A2, .30, 1.6)]:
    note(buf, t, m, v, h)
music = buf.copy(); fx = np.zeros_like(buf); thud(fx, 3.90); knock(fx, 9.05)
mix = music * 4.2 + fx * 1.0
mix = np.tanh(mix * 1.5) / np.tanh(1.5)             # a soft ceiling: the thud stays the loudest thing without burying the piano
fade = int(0.6 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
peak = np.abs(mix).max(); mix *= 0.80 / peak
st = np.stack([mix, mix], 1); w = wave.open("sound.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
half = SR // 2; rows = [20 * np.log10(np.sqrt((mix[i:i + half] ** 2).mean()) + 1e-9) for i in range(0, len(mix), half)]
print("level each half second (dB):"); print(" ".join(f"{r:5.0f}" for r in rows))
print("loudest half second starts at", np.argmax(rows) / 2, "s; thud peak at", (np.abs(fx).argmax()) / SR, "s")
