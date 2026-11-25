"""The sound of Stet, built with no picture: every sound is made here from sines and noise (no samples, no service).
Every event the picture shows has its beat here, in the table T, and this file writes those beats to kit/times.gen.ts,
so the film and the sound read one clock.
  python sound.py            writes media/sound.wav (48 kHz stereo) and kit/times.gen.ts, and prints the level each half second

After the person heard an early cut: "a little more cohesion/pattern to work along with the motion ... right now the
sounds are tied to what is on screen". So this is a piece of music first: one tempo (150), one key (D), a chord a bar,
a pattern that runs from the first full stop to the last, and one tune that comes back. The picture's events are
played inside it, on its grid and in its key, and quieter than before.
What each sound means: a tick is a word arriving; a pluck is a run that passed; the low blip is a run that failed;
the wooden clack is a bracket shutting; the tap is the pointer pressing; the swell is the page's dots."""
import subprocess, json, pathlib, wave
import numpy as np

# ---- the one clock: 60 frames a second, 24 frames a beat (150 beats a minute)
SR, FPS, FB = 48000, 60, 24
FB = int((json.loads(pathlib.Path("score.json").read_text(encoding="utf-8")).get("music") or {}).get("fb") or FB)   # a track mapped by vd audio --tempo-map sets the beat
BEAT = FB / FPS
ACT1, LATER, LAST = 11, 16, 77         # act 1 ends on the film's beat 11; the later acts begin on their beat 16 and end on 77
SHIFT = LATER - ACT1                   # so the later acts are drawn and heard SHIFT beats earlier than their numbers say
BEATS = LAST - SHIFT                   # the film's length in beats
DUR = BEATS * BEAT

# ---- the film's events, in beats, by name. The picture imports these (kit/times.gen.ts) and types none of its own.
# Two clocks, and the table has a half for each. T1 is act 1, on the film's clock: beat b is b * 0.4 s into the film.
# T2 is everything after, on the later acts' clock, which keeps the numbers the film was written on so that its bars
# fall on every beat that divides by four: beat b is (b - SHIFT) * 0.4 s into the film. To move an event, change its
# number in its own half and run this file: the sound, the picture and vd's cues all apply the shift; nobody does it by
# hand. A beat in T1 must be under ACT1 and a beat in T2 at least LATER (this file stops otherwise), so a number written
# on the wrong clock cannot pass unnoticed. Names marked (picture) have no sound of their own.
T1 = {
    "IT": [0, 0.33],                   # "It passed": a tick a word
    "STOP1": 1,                        # its full stop lands, and the pattern begins
    "HOP": 1.5,                        # the full stop hops to the head of the line
    "ROW": 2,                          # the sentence becomes the tests row
    "PANEL": 2.5,                      # the checks panel opens round it, a tick a row
    "CHANGED": [2.75, 3.125, 3.5, 3.75],   # "You changed nothing", and its full stop
    "POINTER": [3, 3.8],               # (picture) the pointer comes in, and reaches Re-run
    "NOTHING": 3.9,                    # (picture) the marks under "nothing"
    "RERUN": 4,                        # Re-run is pressed
    "BUILD": 4.5, "LINT": 4.75,        # build passes, lint passes
    "FAIL1": 5,                        # tests fail: the bar turns sour
    "PRESSES": [6.5, 7, 7.5, 7.75, 8, 8.25, 8.5, 8.67, 8.83],      # Re-run again, faster
    "TAPS": [9, 9.17, 9.33],           # three more taps heard under the brackets; the pointer is not drawn pressing them
    "FLIPS": [6.75, 7.25, 7.625, 7.875],   # each answer lands after its press: passed, failed, passed, failed
    "FAST": 8, "FASTER": 8.5,          # from here the answers flip on their own, and faster
    "BRACKET": 9,                      # the first bracket comes in
    "CATCH": 9.5,                      # the second shuts, and the flipping stops
}
T2 = {
    "ANSWER": LATER,                   # the mark opens into the run matrix
    "MARK_FIRES": 16.25,               # (picture) its head and names come up
    "COL_AT": [16.5 if c == 0 else 17.5 + c * 0.5 if c < 5 else 19.5 + (c - 4) * 0.25 if c < 7 else 20 + (c - 6) * 0.125 if c < 11 else 20.5 + (c - 10) * 0.5 / 13 for c in range(24)],   # each column of runs
    "RUN_IT": [17, 17.2, 17.4, 17.6],  # "Run it again", and its full stop
    "AND1": [17.8, 18, 18.2], "AND2": [18.4, 18.6, 18.8],          # "And again." "And again."
    "CLOSER": 19,                      # (picture) the camera goes in
    "INSIDE": 22,                      # (picture) the camera on two rows; the claims on the left go
    "SAME": [22.25, 22.5, 22.75],      # "Same commit."
    "WASH": 23,                        # (picture) the flaky rows light up
    "TWO": [23.25, 23.5, 23.75],       # "Two answers."
    "TWO_MARKS": [23.75, 23.85],       # (picture) the marks under them
    "TWINKLE": 24, "TWINKLE_STEP": 0.3,    # the failed runs, one after another
    "SAID": 24.7,                      # (picture) "Same commit. Two answers." go
    "FLAKE": [25, 25.2, 25.4, 25.6],   # "That's a flake.", its full stop the failed run
    "CAUGHT": 25.5,                    # the flaky rows shake
    "FLAKE_MARK": 25.7,                # (picture)
    "FLAKE_OFF": 27.7, "WORDS_BACK": 27.8,     # (picture) "That's a flake." goes; the two rows come back
    "NUMBERS": 28,                     # backing out: forty tests
    "N412": 28.5,                      # "412 tests": all of them
    "RUN": 29,                         # the block runs, top to bottom, in one beat
    "RAN": 30, "N9888": 30.25,         # "9,888 runs"
    "N3": 32,                          # "3 flakes": they come out of the block
    "SHUT3": 32.75, "SHUT_STEP": 0.25,     # and the brackets shut on each
    "N6": 34,                          # "6 minutes"
    "HELD": [36, 36.5, 36.75, 37],     # "Held, not deleted", and its full stop
    "DROP": 37.5,                      # the three go under a line, held
    "TICK0": 38, "NT": 13, "TICK_STEP": 0.5,   # still runs: a new run every half beat, thirteen of them
    "FAILS": {"1": [0, 7, 13], "4": [4, 19], "6": [2, 9, 10, 16, 22]},     # the runs, by column, that failed: of tests 1, 4 and 6
    "LATE": {"6": [27, 31], "1": [29, 33]},    # the new runs on which two held tests fail again (the brackets catch each)
    "NOTES": 39,                       # "still runs · can't block a merge · issue opened", a half beat apart
    "CAM_HELD": 40,                    # (picture) the camera eases on
    "FIXED": 44,                       # "Fixed?"
    "COMMIT": 44.25, "FLY": 44.75,     # a commit appears, and flies to its test
    "RERUN0": 45, "RERUN1": 46,        # it runs again, 24 times, all passing
    "RELEASED": [46.25, 46.5],         # "Released", and its full stop
    "BACK": 46.5,                      # the released test goes back among the others
    "FOCUS_OFF": 47.25,                # (picture)
    "PASSED": [48, 48.5, 49, 49.25],   # "Passed means passed", and its full stop
    "PASSED_MARK": 49.5,               # (picture)
    "CHECKS2": 48.75,                  # (picture) the checks panel again
    "POINTER2": [50, 51.6],            # (picture) the pointer comes to Merge
    "MERGE": 52,                       # Merge is pressed
    "FOLD": 56,                        # everything folds into one dot
    "SHUT_MARK": [57, 57.25],          # the brackets shut on the dot, left and right: the mark
    "NAME": 57.5,                      # and the name is typed
    "SILENCE": [58.25, 59.5],          # the one silence, on the name
    "FOR": 60,                         # "For" pytest, jest, playwright, a beat each
    "MORE": 63,                        # "and 30+ more"
    "START": 64,                       # "One line to start"
    "CMD": 64.5,                       # the command types, a letter every two frames
    "COPY": 66,                        # the Copy button comes in
    "POINTER3": [66.3, 67.6],          # (picture) the pointer comes to Copy
    "COPIED": 68,                      # Copy is pressed
    "FREE": [69, 69.25, 69.5, 69.75, 70],  # "Free for open source", and its full stop
    "END": 72,                         # the end card: the name again
    "LET": [72.5, 72.83, 73.17, 73.5], # "Let it stand", and its full stop
    "LET_MARK": 73.83,                 # the marks under "stand"
}
for half, ok in ((T1, lambda b: b < ACT1), (T2, lambda b: b >= LATER)):
    for k, v in half.items():
        if k in ("TWINKLE_STEP", "SHUT_STEP", "TICK_STEP", "NT", "FAILS", "LATE"): continue      # steps, counts and columns, not beats
        for b in (v if isinstance(v, list) else [v]):
            if not ok(b): raise SystemExit(f"sound.py: {k} = {b} is not on its half's clock (T1: under {ACT1}; T2: {LATER} or more)")
T = {**T1, **T2}

N = int(DUR * SR) + SR
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
OFF = 0.0

def put(x, beat, gain=1.0, pan=0.0):
    a = int(round((beat + OFF) * BEAT * SR)); n = min(len(x), N - a)
    if n <= 0 or a < 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[a:a + n] += x[:n] * gain * gl * 1.414; R[a:a + n] += x[:n] * gain * gr * 1.414

def tt(dur): return np.arange(int(dur * SR)) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y
def fft_band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8) / np.sqrt(1 + (f / hi) ** 8); return np.fft.irfft(X, len(x))

# ---- the instruments
def pluck(m, dur=0.55, bright=0.5):
    """a small wooden bar: the fundamental, and two short high partials"""
    t = tt(dur); f = hz(m); tau = 0.16 * (440 / f) ** 0.35
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
    x += bright * 0.42 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t / (tau * 0.22))
    x += bright * 0.16 * np.sin(2 * np.pi * 9.6 * f * t) * np.exp(-t / (tau * 0.07))
    return x * np.minimum(1, t / 0.0015)
def bell(m, dur=1.4):
    """the tune's voice: rounder and longer than the pluck"""
    t = tt(dur); f = hz(m)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.45) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.22)
    x += 0.2 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.12) + 0.08 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t / 0.05)
    return x * np.minimum(1, t / 0.003)
def bass(m, dur=0.5):
    t = tt(dur); f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.32 * np.sin(2 * np.pi * 2 * f * t) + 0.08 * np.sin(2 * np.pi * 3 * f * t)
    return x * np.minimum(1, t / 0.006) * np.exp(-t / (dur * 0.55)) * np.minimum(1, (dur - t) / 0.02)
def kick(g=1.0):
    t = tt(0.24); ph = 2 * np.pi * np.cumsum(46 + 85 * np.exp(-t / 0.022)) / SR
    return (np.sin(ph) * np.exp(-t / 0.085) * np.minimum(1, t / 0.0015) + fft_band(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t / 0.002) * 0.25) * g
def hat(g=1.0):
    t = tt(0.05); return fft_band(rng.standard_normal(len(t)), 7000, 15000) * np.exp(-t / 0.011) * g
def rim(g=1.0):
    t = tt(0.09); return (fft_band(rng.standard_normal(len(t)), 900, 3600) * np.exp(-t / 0.016) + 0.5 * np.sin(2 * np.pi * 820 * t) * np.exp(-t / 0.012)) * g
def pad(ms, dur, g=1.0, attack=0.03):
    t = tt(dur); x = np.zeros(len(t))
    for m in ms:
        f = hz(m)
        for d in (-0.003, 0.003): x += np.sin(2 * np.pi * f * (1 + d) * t) + 0.25 * np.sin(2 * np.pi * 2 * f * (1 + d) * t)
    return x / (2 * len(ms)) * np.minimum(1, t / attack) * np.exp(-t / (dur * 0.45)) * np.minimum(1, (dur - t) / 0.05) * g
def tick(f0=2400, g=1.0):
    t = tt(0.03); x = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.0035)
    n = fft_band(rng.standard_normal(len(t)), 3000, 11000) * np.exp(-t / 0.0012) * 0.6
    return (x + n) * g
def clack(g=1.0, pitch=1.0):
    t = tt(0.12); x = np.zeros(len(t))
    for f, tau, a in [(1150, 0.020, 1.0), (2750, 0.011, 0.6), (4100, 0.006, 0.35), (560, 0.028, 0.5)]:
        x += a * np.sin(2 * np.pi * f * pitch * t) * np.exp(-t / tau)
    x += fft_band(rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t / 0.0025) * 0.9
    return x * g * np.minimum(1, t / 0.0005)
def tap(g=1.0):
    t = tt(0.12); ph = 2 * np.pi * np.cumsum(110 + 70 * np.exp(-t / 0.012)) / SR
    x = np.sin(ph) * np.exp(-t / 0.022); k = tick(1700, 0.3); x[:len(k)] += k
    return x * g
def thup(g=1.0):
    t = tt(0.22); ph = 2 * np.pi * np.cumsum(52 + 60 * np.exp(-t / 0.02)) / SR
    return np.sin(ph) * np.exp(-t / 0.06) * np.minimum(1, t / 0.002) * g
def fail(g=1.0, m=46):
    """a run that failed: low, slightly sour, short"""
    t = tt(0.26); f = hz(m) * (1 - 0.06 * np.minimum(1, t / 0.2)); ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * ph) / k for k in (1, 3, 5, 7)) + 0.5 * np.sin(1.06 * 2 * ph)
    x = onepole_lp(x, 1300) * np.exp(-t / 0.07) * np.minimum(1, t / 0.002)
    return x * 0.8 * g
def swell(dur, up=True, g=1.0):
    """the page's dots: a band of noise that opens (or closes), with a grain of small pops in it"""
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur if up else 1 - t / dur
    x = np.zeros(n)
    for lo, hi, w in [(250, 700, 0.0), (700, 1800, 0.33), (1800, 4500, 0.66), (4500, 10000, 1.0)]:
        x += fft_band(rng.standard_normal(n), lo, hi) * np.exp(-((k - w) ** 2) / 0.09)
    pops = np.zeros(n)
    for _ in range(int(90 * dur / 0.3)):
        a = int((rng.random() ** (0.6 if up else 1.6)) * (n - 400)); pops[a:a + 300] += tick(1500 + 3000 * rng.random(), 0.25)[:300]
    env = (k ** 1.6) * np.minimum(1, (dur - t) / 0.02 if up else t / 0.004)
    return (x * 0.22 + pops * 0.5) * env * g

# ---- the harmony: a chord a bar. (bass note, four tones low to high)
CH = {"D": (38, [62, 66, 69, 76]), "Dsus": (38, [62, 64, 69, 74]), "Bm": (35, [59, 62, 66, 69]), "G": (31, [59, 62, 67, 69]),
      "A": (33, [57, 61, 64, 71]), "Bb": (34, [58, 62, 65, 69])}
ARP = [0, 2, 1, 2, 3, 2, 1, 2]                                  # the pattern: one figure, every bar, in the bar's chord
TUNE = [(0, 78), (2, 81), (4, 83), (5, 81), (7, 78), (8, 76), (10, 78), (12, 74)]     # two bars, in eighths: F# A B A F# | E F# D
def bar(b0, name, drums=1.0, arp=1.0, low=1.0, wash=1.0, beats=4, hats=True):
    """one bar of the pattern from beat b0, in chord `name`"""
    root, tones = CH[name]
    if wash: put(pad(tones, beats * BEAT + 0.5), b0, 0.20 * wash)
    for e in range(beats * 2):
        b = b0 + e * 0.5
        if arp: put(pluck(tones[ARP[e % 8]] + 12, 0.32, 0.6), b, (0.2 if e % 2 == 0 else 0.14) * arp, pan=0.25 * (1 if e % 2 else -1))
        if drums:
            if e % 8 in (0, 4): put(kick(), b, 0.34 * drums)
            if e % 8 in (2, 6): put(rim(), b, 0.16 * drums, pan=0.15)
            if hats: put(hat(), b, (0.11 if e % 2 else 0.06) * drums, pan=-0.2)
        if low:
            if e % 8 == 0: put(bass(root + 12, 0.55), b, 0.27 * low)
            if e % 8 == 3: put(bass(root + 12, 0.22), b, 0.2 * low)
            if e % 8 == 6: put(bass(root + 19, 0.25), b, 0.19 * low)
def tune(b0, g=0.2, upto=16):
    for e, m in TUNE:
        if e < upto: put(bell(m), b0 + e * 0.5, g, pan=0.1)

COL_AT = T["COL_AT"]
FAIL_COLS = {c for cols in T["FAILS"].values() for c in cols}
PENTA = [62, 64, 66, 69, 71]                                   # D major pentatonic: it sits on every chord here
def scale(i, base=0): return PENTA[i % 5] + 12 * (i // 5) + base
def words(beats, g=0.3, f0=2400):
    for i, b in enumerate(beats): put(tick(f0 * (1 + 0.04 * (i % 3)), 1.0), b, g, pan=-0.25)
def stop(b, m=81, g=0.2): put(pluck(m, 0.4, 0.3), b, g, pan=-0.2)
PASS_STAB = [74, 78, 81]
def passed(b, g=0.34):
    for m in PASS_STAB: put(pluck(m, 0.3, 0.5), b, g, pan=0.3)
def failed(b, g=0.8): put(fail(1.0), b, g, pan=0.3); put(pluck(58, 0.3, 0.2), b, 0.3, pan=0.3)

# ================= act 1, on the film's clock: the problem, the flip and the catch. Bars on 1 and 5; the brackets on 9.
words(T["IT"], 0.4)
put(pluck(86, 0.6, 0.5), T["STOP1"], 0.4); bar(T["STOP1"], "Dsus", drums=0, low=0.5)      # the full stop lands, and the pattern begins
put(tick(1800), T["HOP"], 0.3); put(thup(0.5), T["ROW"], 0.5); words([T["PANEL"], T["PANEL"] + 0.12, T["PANEL"] + 0.25], 0.22, 2000)
words(T["CHANGED"][:3]); stop(T["CHANGED"][3])
put(tap(), T["RERUN"], 0.8, pan=0.3)                                               # Re-run
put(pluck(74, 0.3), T["BUILD"], 0.26, pan=0.3); put(pluck(74, 0.3), T["LINT"], 0.26, pan=0.3)  # build and lint pass
failed(T["FAIL1"], 0.85); put(thup(), T["FAIL1"], 0.6); bar(T["FAIL1"], "Bb", drums=0, arp=0.9, low=0.9)      # tests fail: the bar turns sour
for p in T["PRESSES"] + T["TAPS"]: put(tap(), p, 0.55, pan=0.3)
FL = T["FLIPS"]; passed(FL[0]); failed(FL[1], 0.7); passed(FL[2]); failed(FL[3], 0.7)     # each answer lands after its press
for i in range(4): (passed if i % 2 == 0 else failed)(T["FAST"] + i / 8, 0.26 if i % 2 == 0 else 0.5)          # and faster
for i in range(6): (passed if i % 2 == 0 else failed)(T["FASTER"] + i / 6, 0.24 if i % 2 == 0 else 0.42)
for i in range(24): put(rim(), T["FAST"] + i / 16, 0.05 + 0.009 * i)                                            # a roll into the catch
# -- the catch (9 to 11, a half bar): two clacks and it stops on the home chord
put(clack(), T["BRACKET"], 0.9, pan=-0.6); put(clack(1.0, 1.06), T["CATCH"], 0.95, pan=0.6)
put(pad(CH["D"][1] + [50, 57], 1.6), T["CATCH"], 0.55); put(bass(50, 1.2), T["CATCH"], 0.4); put(kick(), T["CATCH"], 0.5); put(bell(86, 1.4), T["CATCH"], 0.2)
put(swell(0.3, False, 0.6), T["CATCH"], 0.35)                                                            # the flush through the page's dots
for e, m in enumerate((74, 78, 81)): put(pluck(m, 0.3, 0.5), T["CATCH"] + 0.5 + e * 0.33, 0.16)           # three notes up into the answer

# ================= everything after, on the later acts' clock
OFF = -SHIFT

# -- the pattern: a chord a bar from the answer to the end
PLAN = [(16, "D"), (20, "Bm"), (24, "G"), (28, "A"), (32, "Bm"), (36, "D"), (40, "A"), (44, "Bm"), (48, "D"), (60, "Bm"), (64, "G"), (68, "A")]
for b0, name in PLAN:
    thin = T["NUMBERS"] <= b0 < T["HELD"][0]                  # the numbers: the drums step back so each number can land
    bar(b0, name, drums=0.55 if thin else 1.0, hats=not thin)
bar(T["MERGE"], "G", beats=2); bar(T["MERGE"] + 2, "A", beats=2)      # the merge: the bar splits and lifts
bar(T["FOLD"], "D", drums=0, arp=0.6, low=0.6, beats=2)       # the fold: only the pattern, then the silence
tune(T["PASSED"][0], 0.2); tune(T["START"], 0.2)              # the tune: when it passes, and again at the end

# -- the answer: the mark fires each column, each a step up the scale; a failed run is the low blip
put(tick(2000), T["ANSWER"], 0.3)
words(T["RUN_IT"][:3]); stop(T["RUN_IT"][3]); words(T["AND1"][:2] + T["AND2"][:2]); stop(T["AND1"][2]); stop(T["AND2"][2])
for c in range(24):
    put(pluck(scale(c // 2) + 12, 0.25, 0.6), COL_AT[c], 0.2 + 0.003 * c, pan=0.35)
    if c in FAIL_COLS: put(fail(0.5), COL_AT[c], 0.34, pan=0.35)
words(T["SAME"][:2] + T["TWO"][:2]); stop(T["SAME"][2]); stop(T["TWO"][2])
for i in range(sum(map(len, T["FAILS"].values()))): put(pluck(74 + (i % 3) * 2, 0.15, 0.5), T["TWINKLE"] + i * T["TWINKLE_STEP"] + 4 / FB, 0.09, pan=0.35)   # the failed runs, one after another
words(T["FLAKE"][:3]); put(fail(), T["FLAKE"][3], 0.7, pan=-0.2); put(rim(), T["CAUGHT"], 0.25); put(rim(), T["CAUGHT"] + 3 / FB, 0.2)   # caught
# -- the numbers
put(thup(), T["NUMBERS"], 0.7); put(swell(0.16, True), T["NUMBERS"], 0.3); put(thup(), T["N412"], 0.7); put(swell(0.2, True), T["N412"], 0.4); words([T["N412"]], 0.4)
for i in range(20): put(pluck(scale(i // 2, 12), 0.1, 0.7), T["RUN"] + i / 20, 0.1, pan=0.4)                    # the block runs, top to bottom
put(bell(86, 0.8), T["RAN"], 0.16); words([T["N9888"]], 0.4)
words([T["N3"]], 0.4); put(thup(), T["N3"], 0.7); put(fail(), T["N3"] + 0.25, 0.5, pan=-0.2)
for j in range(3): put(clack(0.9, 1.0 - 0.07 * j), T["SHUT3"] + j * T["SHUT_STEP"], 0.7, pan=0.35)               # the brackets shut on the three
words([T["N6"]], 0.4); put(bell(81, 0.9), T["N6"], 0.2); put(bell(88, 0.9), T["N6"] + 0.25, 0.14)
# -- held, not deleted
words(T["HELD"][:3]); stop(T["HELD"][3])
put(pluck(57, 0.6, 0.3), T["DROP"], 0.4, pan=0.3); put(thup(0.7), T["DROP"], 0.5)
for i in range(T["NT"]): put(pluck(81 + (2 if i % 2 else 0), 0.12, 0.6), T["TICK0"] + i * T["TICK_STEP"], 0.1, pan=0.45)      # still runs: each new run arrives at the right
for b in sorted(T["TICK0"] + (j - 24) * T["TICK_STEP"] for js in T["LATE"].values() for j in js):                  # two of them still fail now and then
    put(fail(0.4), b, 0.24, pan=0.4); put(clack(0.5, 1.3), b + 3 / FB, 0.3, pan=0.4)                             # and the brackets catch it
words([T["NOTES"] + i * 0.5 for i in range(3)], 0.16, 3000)
# -- fixed? released
words([T["FIXED"]]); put(tick(1900), T["COMMIT"], 0.3); put(bell(81, 0.6), T["COMMIT"], 0.14); put(swell(0.1, True, 0.5), T["FLY"], 0.3)   # the commit flies to its test
for c in range(24): put(pluck(scale(c // 2 + 2, 12), 0.12, 0.6), T["RERUN0"] + c / 24, 0.15, pan=0.35)    # it runs again: 24, all passing
put(bell(86, 0.6), T["RERUN1"], 0.16); words([T["RELEASED"][0]]); put(clack(0.6, 1.5), T["RELEASED"][0], 0.45, pan=0.35); stop(T["RELEASED"][1])
put(pluck(86, 0.5), T["RELEASED"][1], 0.3, pan=0.3); put(pluck(90, 0.5), T["RELEASED"][1] + 8 / FB, 0.24, pan=0.3)
# -- passed means passed
put(swell(0.3, True, 0.7), T["PASSED"][0] - 0.75, 0.45); words(T["PASSED"][:3]); stop(T["PASSED"][3])
put(tap(), T["MERGE"], 0.8, pan=0.3); put(pad([55, 59, 62, 67, 71], 1.2), T["MERGE"] + 3 / FB, 0.3)
# -- the name, in the one silence
put(swell(0.18, False, 0.6), T["FOLD"], 0.35)
SM = T["SHUT_MARK"]
put(clack(), SM[0], 0.9, pan=-0.6); put(clack(1.0, 1.06), SM[1], 0.95, pan=0.6); put(kick(), SM[1], 0.5); put(bass(50, 0.5), SM[1], 0.35)
for i in range(4): put(tick(2600 + 150 * i), T["NAME"] + i * 3 / FB, 0.4)
# -- for: the mark keeps its place; three names, a beat each, each a step up; then the rest
for i in range(3): put(bell(scale(i + 1, 12), 0.5), T["FOR"] + i, 0.2); put(tick(2200), T["FOR"] + i, 0.3)
put(bell(86, 0.8), T["MORE"], 0.2); put(bell(90, 0.8), T["MORE"], 0.14); words([T["MORE"], T["MORE"] + 0.25])
# -- one line to start
words([T["START"]])
for i in range(13): put(tick(2500 + 60 * (i % 5)), T["CMD"] + i * 2 / FB, 0.24, pan=0.1 * (i % 3 - 1))
put(tick(2000), T["COPY"], 0.25)
put(tap(), T["COPIED"], 0.8); put(bell(86, 0.6), T["COPIED"] + 3 / FB, 0.18); put(bell(93, 0.7), T["COPIED"] + 0.33, 0.16)
words(T["FREE"][:4]); stop(T["FREE"][4])
# -- the end card: the name again on the last chord, and the line under it
E = T["END"]
put(pad(CH["D"][1] + [50, 57], 4.2, attack=0.02), E, 0.6); put(bass(50, 2.4), E, 0.42); put(kick(), E, 0.5); put(bell(86, 2.0), E, 0.22); put(bell(78, 2.0), E, 0.16)
words(T["LET"][:3], 0.22); stop(T["LET"][3], 81, 0.2)
for i in range(11): put(tick(3200, 0.6), T["LET_MARK"] + i / FB, 0.09)
put(bell(74, 2.2), E + 2.5, 0.2); put(bell(81, 2.2), E + 2.5, 0.12)

# ---- the one silence: half a second on the name, and the mix
def gate(b0, b1, floor=0.0):
    a, b = int((b0 + OFF) * BEAT * SR), int((b1 + OFF) * BEAT * SR); r = int(0.03 * SR)
    g = np.ones(N); g[a:b] = floor; g[a - r:a] = np.linspace(1, floor, r); g[b:b + r] = np.linspace(floor, 1, r)
    return g
g = gate(*T["SILENCE"], 0.02)
mix = np.stack([L * g, R * g], 1)
mix = np.tanh(mix * 1.5) / np.tanh(1.5)
end = int(DUR * SR); fade = int(1.2 * SR); mix = mix[:end]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix *= 0.7 / np.abs(mix).max()
out = pathlib.Path("media"); out.mkdir(exist_ok=True); raw = out / "sound-raw.wav"; final = out / "sound.wav"
with wave.open(str(raw), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype("<i2").tobytes())
TARGET = -15.0
p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(raw), "-af", f"loudnorm=I={TARGET}:TP=-2.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                f"loudnorm=I={TARGET}:TP=-2.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                "-ar", str(SR), "-c:a", "pcm_s16le", str(final)], check=True)
raw.unlink()

# ---- the one clock, written for the picture (kit/times.gen.ts) and for vd: the rate, the beat, the length, the two
# clocks, the events, the cues (each named event a sound starts on, in seconds into the film), which vd sound checks the
# mix against, and the one silence, which is meant. One line each, `export const NAME = JSON;`, so vd reads the same file
# the picture imports. The seconds come from sec(), the only place the shift is applied outside the picture's g() and h.
def sec(b): return round((b if b < ACT1 else b - SHIFT) * BEAT, 4)
CLOCK = {"FPS": FPS, "FB": FB, "BEATS": BEATS, "DURATION": round(DUR, 6), "BPM": round(60 / BEAT, 6), "ACT1": ACT1, "SHIFT": SHIFT}
CUES = [[n, T[n]] for n in ("STOP1", "RERUN", "FAIL1", "BRACKET", "CATCH", "ANSWER", "NUMBERS", "N412", "N3", "DROP", "MERGE", "FOR", "MORE", "END")]
CUES += [["FOLD+1", T["SHUT_MARK"][0]], ["START+4", T["COPIED"]]]      # the labels vd has always shown for these two
CUES = sorted(([n, sec(b)] for n, b in CUES), key=lambda c: c[1])
RESTS = [["SILENCE (the name)", sec(T["SILENCE"][0]), sec(T["FOR"])]]      # from the gate to "For", the next sound
pathlib.Path("kit/times.gen.ts").write_text("// generated by sound.py: the film's clock and its events in beats, the same numbers the sound was made from.\n"
                                            "// TIMES holds act 1's events on the film's clock and the later acts' on their own (drawn CLOCK.SHIFT beats earlier).\n"
                                            + "".join(f"export const {k} = {json.dumps(v)};\n" for k, v in (("CLOCK", CLOCK), ("TIMES", T), ("CUES", CUES), ("RESTS", RESTS))), encoding="utf-8", newline="\n")
score = pathlib.Path("score.json"); s = json.loads(score.read_text(encoding="utf-8"))
if (s.get("fps"), s.get("duration"), s.get("bpm")) != (FPS, CLOCK["DURATION"], CLOCK["BPM"]):          # the score's clock is this one
    s.update(fps=FPS, duration=CLOCK["DURATION"], bpm=CLOCK["BPM"]); score.write_text(json.dumps(s, indent=1), encoding="utf-8", newline="\n")

mono = mix.mean(1); half = SR // 2
rows = [20 * np.log10(np.sqrt((mono[i:i + half] ** 2).mean()) + 1e-9) for i in range(0, len(mono) - half + 1, half)]
print(f"{final}: {DUR:.1f} s; before levelling {m['input_i']} LUFS, true peak {m['input_tp']} dBTP, range {m['input_lra']} LU; levelled to {TARGET} LUFS")
print("level each half second (dB, before levelling):"); print(" ".join(f"{r:4.0f}" for r in rows))
q = int(np.argmin(rows[4:-4])) + 4; print(f"quietest half second inside the film starts at {q / 2:.1f} s ({rows[q]:.0f} dB)")
# how much of the energy is low, middle and high: a check that nothing is boomy or harsh, since the agent cannot hear it
X = np.abs(np.fft.rfft(mono)) ** 2; fr = np.fft.rfftfreq(len(mono), 1 / SR); tot = X.sum()
for lo, hi in [(20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 16000)]:
    print(f"  {lo:>5}-{hi:<5} Hz  {100 * X[(fr >= lo) & (fr < hi)].sum() / tot:5.1f} %")
