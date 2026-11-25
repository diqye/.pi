# Stet

A launch film for a made-up developer tool: a problem shown, the mechanism, a proof, how to start. 28.8 s.

1920x1080 at 60 frames a second, composition `film`. No real pictures: everything is type, panels and interface drawn
in code on a ground of soft moving colour. The person it was made for called it "a really good output ... I consider
this a success". Start from it when your product is technical and the film has to show a mechanism working.

## Run it

In a copy made with `vd new NAME --like stet`, not in the skill's own folder: only the copy's `score.json` names the
mix that `vd export` carries.

```
python sound.py                          # writes media/sound.wav and kit/times.gen.ts (run again whenever a sound or a beat changes)
vd look --at 3.7,10.4,15,19,24           # five moments as one picture
vd export                                # the film with that sound, about a minute and a half, then the scan
```

## What is where

| file | holds |
|---|---|
| `BOARD.md` | the film on one page |
| `sound.py` | the music and every sound, on the film's beats |
| `kit/times.gen.ts` | the clock and every event's beat, written by `sound.py` for the picture to import |
| `film.tsx` | the order of the acts and three tables at its top: `CAM` (framings), `AIR` (the ground's mood), `LANDS` (where ripples start) |
| `act1.tsx` | the problem: a check that flips with nothing changed |
| `act3.tsx`, `matrix.tsx` | the mechanism: every run of every test, three flaky ones found and held |
| `act6.tsx` | the proof ("Passed means passed"), how to start, the name |
| `panel.tsx` | the checks panel |
| `kit/stet.tsx` | the clock, the colours, the dot, the brackets, the pointer |
| `kit/field.tsx` | the ground: soft moving colour and glass |
| `kit/fonts.gen.ts`, `kit/metrics.gen.ts` | Geist and Geist Mono, embedded, and their letter widths, which the kit sizes brackets and marks to words with (for another face, make the widths again: `python SKILL_FOLDER/tools/metrics.py YOUR-SANS-VF.ttf YOUR-MONO-VF.ttf`) |
| `main.tsx`, `ids.ts`, `score.json` | the entry raea renders, the composition's name, and the frame's size, rate and sound file |
| `media/fonts/`, `LICENSE-video-decompiler.txt` | the fonts' licences, and the licence of the skill's code |

`kit/` is those five files and nothing else: this film uses none of the skill's page library. Its `arr` and `ramp` are
not the functions of those names in the other worked films: here `arr(f, b, n)` arrives over `round(n * 1.8)` frames
and `ramp(f, b0, b1)` runs between two beats, where theirs take a beat and a count of frames, so a call moved between
films changes speed.

## Keep

- **The shape:** the trouble first, in the viewer's own words ("You changed nothing"); the mechanism shown working on
  real-looking data; one case followed all the way through (held, fixed, released); the claim; how to start; the name
  late, and again on the end card.
- **The camera** (`CAM` in `film.tsx`): it goes onto whatever is the proof at that moment, eases in and out, and
  creeps in every hold.
- **Arrivals that decelerate** over about 13 frames; only a bracket shutting is instant.
- **The ground** (`kit/field.tsx`) taking the mood of what is happening.
- **Music first**: one tempo, one key, a chord a bar, one tune that comes back; each sound means one thing.

## Replace

`BOARD.md`, the acts, the panel, the words, the sounds' meanings. Keep `kit/` (`stet.tsx`, `field.tsx` and the three `.gen.ts` files) and the three tables' form. This README
describes Stet: rewrite it for your film, or delete it.

## Changing the clock

The tempo and the length live in one place: `FB` (frames in a beat) and `LAST` (the last beat) at the top of
`sound.py`. Change them, run `sound.py`, and the picture and `score.json` follow. Then move the beats in its table:
`T1` for act 1, on the film's clock, and `T2` for everything after, on the later acts' clock. `sound.py` says why
there are two clocks, and applies the shift between them itself.

## What is in it (seen in the film; none of it is a rule)

- **One thing carried:** a dot that is a test's result. It flips, is bracketed, held, released, and ends as the mark.
- **One move, played five times:** a run gives an answer. Each play adds something: the same commit gives two
  answers; 9,888 runs of 412 tests give three flakes; the three are held; one is fixed and released; the build passes.
- **Every claim is shown as a change of state** on screen ("Held, not deleted": the rows are still there, set aside).

## What readers changed, before the person's last viewing

"Fixed? Released." got its own close framing because three readers had only read it. The second logo card went: the
person agreed it "does interrupt without reason". Four one-frame swaps became moves that carry the thing across.

## Known limits

- **The sound is sines and noise made in code.** Its holds were set against the one film it was held against, a snap-and-hold
  film that is nearly still, creeping, for more than half its length: a film of another kind needs its own measure.
- **Small words under the held rows:** "still runs", "can't block a merge" and "issue opened" are set at 19 px and
  are about 23 px on screen, under the 30 px the skill's pages ask for. The film was accepted with them; do not
  copy the size.
- **Two places where picture and sound differ, kept as accepted and named in `sound.py`:** three taps are heard
  under the brackets with no press drawn (`TAPS`), and in the fast flips the sound alternates twice as often as
  the picture (`FAST`).
- **Two clocks in one table.** Act 1 is on the film's clock and the later acts on their own, drawn five beats
  earlier. `sound.py` stops when a beat is written in the wrong half, but new picture code that uses a later-acts
  beat without the shift (`g()` in `film.tsx`) is not caught.
- **`vd sound` marks one event to check by ear:** "412 tests" reads 80 ms early, because the swell leading into it
  hides where it starts.
- **The scan's four lines about this film are the film as accepted.** Its two `fix before anyone watches` lines: the
  one-frame flash at 8.28 s (frame 497) is one frame of the three flaky rows' shake as they are named ("caught" in
  `matrix.tsx`, with its two rim clicks in `sound.py`), and the jump at 20.40 s (frame 1224) is everything folding
  into one row, on its beat. Its two `check:` lines are the last holds: "Free for open source." under the command
  (25.47 to 26.80 s) and the name over "Let it stand." (27.08 to 28.80 s). In a film of your own, answer each such
  line.
- **`vd look`, at the five moments above, names 25 texts under 30 px.** The smallest are the panels' own small
  print at 18 px: the commit, the run time, "passing · merge allowed".
