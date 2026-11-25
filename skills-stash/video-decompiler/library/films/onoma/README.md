# Onoma

Moving type for a made-up app that turns typed words into sound: each word comes apart into the sound it names, then the sounds play together. Start from it when the product works on words or sound. 29.0 s.

1920x1080 at 60 frames a second, composition `film`. No pictures: type, specks of light, one line, a glass prompt bar
and soft moving colour, all drawn in code. The soundtrack is the product's output, made in `sound.py` from noise and
sines: each word is heard as it comes apart, and the mix at the end plays the same sounds on one grid. A person accepted
its fourth cut.

## Run it

In a copy made with `vd new NAME --like onoma`, not in the skill's own folder: only the copy's `score.json` names the
mix that `vd export` carries.

```
python sound.py                          # writes media/sound.wav, kit/times.gen.ts (the clock and every beat) and kit/waves.gen.ts (the shapes the film draws); run again whenever a sound or a beat changes
python tools/glyphs.py                   # writes kit/glyphs.gen.ts, the typed words as specks (run again when a word, its size or the font changes)
vd look --at 0.75,2.53,5.08,8.58,12.53,17.08,24.17   # seven moments as one picture
vd export                                # the film with that sound, about two minutes, then the scan
```

`vd new` has already run `sound.py` once in the copy. `vd export` stops when `sound.py` is newer than `media/sound.wav`.

## What is where

| file | holds |
|---|---|
| `BOARD.md` | the film on one page |
| `sound.py` | the clock, the table `T` of every event's beat, the typed words (`TEXT`), every sound, the music and the mix, at 120 beats a minute. It writes `media/sound.wav`, `kit/times.gen.ts` and `kit/waves.gen.ts` |
| `film.tsx` | the camera table `CAM` (framings, eased in and out), the air's table `AIR` (which colour the room takes, from which beat), the bolt's flash, and the order of the layers |
| `words.tsx` | beats 0 to 24: the six words (`WORDS`: where each is set and the frame it comes apart on; their text and typing are `sound.py`'s), what each one's specks do, the rain, the bolt and the clap's rings |
| `line.tsx` | the line: where it lies on each frame (`lie`) and what each sound does to its shape (`disp`), with where the steps, claps and pulses land and the name's five letters |
| `product.tsx` | beats 24 to 58: the name, the prompt bar and the request, the five tracks and the playhead, their fold into one line, the claim, the file, the name again |
| `kit/core.tsx` | the clock from `kit/times.gen.ts` (`FPS`, `FB`, frames in a beat) and the events (`TM`) and typed words (`TX`) it passes on, the colours, the curves (`arr`, `glide`), type (`T`, `M`, `tw`), glass |
| `kit/times.gen.ts` | the clock (`CLOCK`), every event's beat (`TIMES`), the typed words (`TEXT`), the named events `vd sound` checks the mix against (`CUES`) and the hush's silence (`RESTS`), written by `sound.py` |
| `kit/field.tsx` | the air (soft moving colour, one mood a sound: `MOODS`) and the grain |
| `kit/fonts.gen.ts`, `kit/metrics.gen.ts` | Geist and Geist Mono, embedded, and their advance widths (for another face, make the widths again: `python SKILL_FOLDER/tools/metrics.py YOUR-SANS-VF.ttf YOUR-MONO-VF.ttf`) |
| `kit/glyphs.gen.ts` | the six words as points inside their letters, written by `tools/glyphs.py` |
| `kit/waves.gen.ts` | the shapes of the sounds, written by `sound.py` from its own samples |
| `tools/glyphs.py` | rasterises each word in `media/fonts/Geist-VF.ttf` and keeps a point on a grid wherever the letter is |
| `media/fonts/` | `Geist-VF.ttf` (the Geist that `kit/fonts.gen.ts` embeds), and the SIL Open Font License texts for Geist and Geist Mono |
| `main.tsx`, `ids.ts` | the entry: `film`, and `film-look` (the same film without its grain) for `vd look` |
| `score.json` | the size; its rate, length and tempo are set by `sound.py`; `vd new` adds `sound_file`, the mix `vd export` carries |
| `LICENSE-video-decompiler.txt` | the MIT licence of this film's code |

## Keep (the kit: none of it is about sound)

- **One thing carried, and one system.** The line is on screen from the rain to the last frame and every sound is a
  shape on it; every word becomes specks of the same light. No word gets an effect of its own.
- **What is drawn is what is heard.** `sound.py` writes the shapes of the sounds it made into `kit/waves.gen.ts`, and
  the picture draws the thunder's rumble, the five tracks, the one line they fold into and the file's shape from them.
- **A word comes apart only once it is whole**, and is typed where the camera already is. Readers saw two words jump
  from half typed to whole in one frame; `WORDS` in `words.tsx` holds the frame each word comes apart on.
- **The camera** in `film.tsx`: a table of framings, eased in and out, that creeps in every hold.
- **The air** in `kit/field.tsx`: it takes the colour of the sound being made, one family at a time.
- **The curves** in `kit/core.tsx`: `arr` (an arrival that decelerates into place) and `glide` (a move that eases in
  and out). Only a hit is instant: the bolt and the clap, each with its sound on that frame.
- **The sound's shape:** single sounds out of a quiet room for the words, one silence (the hush) before the name, the
  first chord with the name, then everything together on one grid.

## Changing the clock

The frame rate, the tempo and the length live in one place: `FPS`, `FB` (frames in a beat) and `BEATS` at the top of
`sound.py`. Change them, run `sound.py`, and the picture and `score.json` follow. Then move the beats in its table `T`.
The typing speeds in `T["TYPE"]` and the few offsets the picture counts in frames (a word comes apart 22 frames before
the first step, say) stay in frames.

## Replace

`BOARD.md`; the words (`TEXT` in `sound.py`, the same words and sizes in `WORDS` in `tools/glyphs.py`, then run both);
the beats in `sound.py`'s table `T`; what each word's specks do; the sounds and the mix in `sound.py`; the air's
`MOODS`; and in `product.tsx` the name, the track labels, the claim and the file, and the letters of the request each
sound's underline spans (`TOK`, and `[[2, 13, 4]]` for the music box: set by hand, not found from the words). Keep
`kit/` and the form of the tables. This README describes Onoma: rewrite it for your film, or delete it.

## What is in it (seen in the film; none of it is a rule)

- **One thing carried:** the line. The rain makes it; every sound is a shape on it; the hush draws it in to a point; it
  is the name's underline, the prompt bar's lower edge, each track of the mix, the one finished sound, and the
  underline again.
- **One move, played six times:** a word is typed and comes apart into the sound it names (rain falls, thunder is blown
  off a bolt, footsteps drop onto the line, a clap becomes a spike with three echoes, a heartbeat pours into a pulse,
  a hush settles like dust). Then the same sounds are asked for in one line and play together.
- **The soundtrack is the demonstration:** what you hear is what the product would make, and the tracks are drawn
  from those samples.
- **The name is said in the film's five sounds:** "onoma" has five letters, and each lands on a half beat with one
  note and the sound it stands for. The music box's tune opens on the same four notes.
- **One silence**, the hush, from 11.25 to 12.0 s, just before the name.

## What readers and the person changed

The board was drawn end to end for the first cut. Each cut was scanned for still stretches before anyone read it: the
first cut was still for 31 % of its frames, with four dead holds (the name, the typed request, the claim, the end).
The second cut said the name in the five sounds, typed the request in close-up and kept the finished sound playing
under the claim, and was still for 17 %. The third let "rain." leave a speck at a time and blew "thunder." off the bolt
along its own flight.

Three readers then read the third cut on sheets, without the sound: two ranking it blind against three other films,
from different model families, and one fault-finder reading it alone, frame by frame through its busiest seconds. The
fourth cut answered what two or more of them saw:

| readers said | what changed |
|---|---|
| A word jumps from half typed to whole in one frame (all three) | Two words had come apart before they finished typing. Every word is now whole before it comes apart, and "thunder.", "footsteps." and "a heartbeat." start typing over the tail of the sound before |
| The prompt bar is cut by the frame while it is typed (all three) | The close-up that rode the caret is gone: the whole bar stays in frame and the camera pushes in on it |
| Words start at the frame's edge and are then centred | "a clap, with echo." and "a heartbeat." are typed where the camera already is |
| The track labels, "return" and the file are too small (all three) | Labels 30 px with a dot in the track's colour, "return" 26 px, the mix framed at 1.28 to 1.36 instead of 0.98, the file chip's name 34 px |
| The line under the name changes between its two times | "Type a sound. Hear it." both times |

Each was acted on though only one reader said it, because it was plainly right or cheap: thunder is now blown outward
and gone, with a shock along the line (it had fallen like the rain); the clap's specks form a column that the spike
takes over; each sound named in the request is underlined in its track's colour; the file chip holds the finished
sound's shape, playing; the camera makes one slow push over the mix (it had pulled out and pushed in twice).

Left as they were, and why: the product arrives after twelve seconds of single words (with the sound on, the first
second is the premise, and one line-up reader read it from the pictures alone); the name is built twice (its letters
are the film's tune, and the second time is the sign-off); the colour fields read as a template to one reader (a matter
of taste); "hush." delays the name (it is the film's one silence). None of those four could be judged without the
sound, which no reader heard.

The fourth cut was then checked by reading every frame of the four stretches the readers had named, and the person
accepted it. The person asked for no change.

## Known limits

- **`vd sound` leaves 10 of its 26 named events to the ear.** It finds where each sound starts by its first rise in
  level. The rain, the heartbeat's lub, the hush and the end's chord fade in, and some of the name's letters land on
  the tail of the one before, so it reads them 40 to 340 ms off, though the sound and the picture take them from the
  same table. The other 16 start within 1.5 frames. The request's last letter is typed without a key: the accepted cut
  struck 55 keys for its 56 letters, and `sound.py` keeps that (`keys=`, with a comment).
- **Three words are whole for fewer than 12 frames before they come apart**, the least the skill's pages ask for:
  "rain." for 9, "a clap, with echo." for 8 and "hush." for 10 ("thunder." is whole for 15, "footsteps." for 19 and
  "a heartbeat." for 17). None jumps from
  half typed to whole, which is what the readers saw.
- **"return" is set at 26 px**, under the 30 px the pages ask for; while the bar is open the camera holds it at 1.28
  times or more, so it is 33 px or more on screen. `vd look` names it.
- **The scan's one "fix before anyone watches" line is meant:** a one-frame jump at 2.50 s (frame 150), the bolt, with
  the thunder on that frame. Its two holds of half a second or more are the hush (11.25 to 12.0 s, silent on purpose)
  and the first half second of the typed request (15.4 to 15.9 s).
- **`sound.py` writes shapes the picture does not draw** (`clap`, `heart` and `tune` in `kit/waves.gen.ts`): the clap's
  spike and the heartbeat's trace on the line are drawn shapes, not taken from the samples.
- **`sound.py` limits its mix at -1.5 dB**, where the skill's pages now ask for -2.5 or lower in the wav; this film's
  export still peaks at -4.2 dBTP.
- **The sound is sines and noise made in code.** Exported on 13 November 2026 it measured -15.0 LUFS and a true peak of
  -4.2 dBTP. No reader heard it.
- **`tools/glyphs.py` was checked on one machine** (Windows, Python 3.12, Pillow 12.2): run there, it writes
  `kit/glyphs.gen.ts` byte for byte as shipped. Another FreeType build may place a point differently at a letter's
  edge.
