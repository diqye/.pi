# Linden Library

A brand film for a made-up public library, built on real still pictures: one camera backing out through worlds nested one inside the next, with no cut. 30.0 s. Start from it when the film is a brand shown through real material in one continuous move.

1920x1080 at 60 frames a second, composition `film`. It opens inside a sheet of old decorated paper and keeps backing
out: the paper is a book's cover, the book is one of a wall of books ("One of 400,000."), the wall sits in the window
of the library's mark on a member's card, the card lies on five grounds in turn, each with a museum plate and its
Dewey number, and everything ends inside the mark, over the paper the film began in. It was accepted at its fifth cut,
whose sound is played on recorded instruments. It suits a film whose world is real material (papers, prints, plates,
scans) and whose story can be told as one move: a thing, then what holds it, then what holds that.

## Run it

In a copy made with `vd new NAME --like linden`, not in the skill's own folder: only the copy's `score.json` names the
mix that `vd export` carries.

```
python sound.py                          # writes media/sound.wav and kit/times.gen.ts (vd new ran it once; run it again whenever a beat moves)
vd look --at 1,4,7.5,13,18.5,25.5        # six moments as one picture
vd export                                # the film as it was accepted: its camera's blur and that sound, then the scan
```

`vd export` draws this film with a camera's blur, as it was accepted: four pictures for every frame, three of each
four averaged, so a fast move reads as a camera's blur and not as a row of sharp pictures. `score.json` asks for it
(`"shutter": {"composition": "film-sub", "sub": 4, "open": 3}`), `main.tsx` registers the composition `film-sub`, and
`Film` takes `sub`. It draws all 7200 pictures, so an export takes several minutes here where the others take one or
two. For a quick sharp draft, take `"shutter"` out of `score.json`; put it back before a person or a reader sees the
film. `vd render --from A --to B` refuses a film with a shutter: a stretch drawn alone would be sharp beside the rest.

## What is where

| file | holds |
|---|---|
| `BOARD.md` | the film on one page: the board as written before the code, and what the accepted cut changed |
| `sound.py` | the film's clock (`FPS`, `FB`, `BEATS`), the music, every sound, and the table `T` of every beat the picture uses. It writes `kit/times.gen.ts` and sets `score.json`'s fps, duration and bpm |
| `score.json` | the size, and `shutter`, the camera's blur `vd export` draws; its rate, length and tempo are set by `sound.py`; `vd new` adds `sound_file`, the mix `vd export` carries |
| `main.tsx`, `ids.ts` | three compositions: `film`; `film-look`, the same film under the name `vd look` draws; `film-sub`, four pictures a frame for the blur. `ids.ts` holds the name `film` |
| `film.tsx` | the camera: `PATH`, a table of stretches (from beat, to beat, the world it is in, the view it ends on, its tilt), and `ACROSS`, the tilted path over the wall |
| `levels.tsx` | the nine worlds, each a canvas 1920 by 1080 in its own units: the book (1), the wall (2), the card (3), five grounds (4 to 8), the mark (9). `SLOTS` says where each world sits inside the next; `LENDS` lays out the five grounds |
| `kit/core.tsx` | the clock as the kit uses it (`FB`, frames in a beat, and `FPS`, both from `kit/times.gen.ts`), the colours, the curves, the faces, and the plain parts (`T`, `M`, `L`, `R`, `pic`) |
| `kit/times.gen.ts` | written by `sound.py`: the clock (`CLOCK`), the beats the picture imports (`TIMES`), and the named events `vd sound` finds in the mix (`CUES`) |
| `kit/fonts.gen.ts`, `kit/metrics.gen.ts` | Geist and Geist Mono embedded, and their character widths (for another face, make the widths again: `python SKILL_FOLDER/tools/metrics.py YOUR-SANS-VF.ttf YOUR-MONO-VF.ttf`) |
| `media/art/` | the papers (`papers/01.jpg` to `24.jpg`, and `hero.jpg`, paper 01 large), the plates (`plates/01.jpg` to `05.jpg`), and `SOURCES.md`: every work, its museum, its public page and its public-domain flag |
| `media/fonts/` | Fraunces and Bricolage Grotesque, with the licence texts of all four faces |
| `media/sounds/` | the recorded instruments, one folder each, with its `LICENCE.txt` |
| `LICENSE-video-decompiler.txt` | the MIT licence of this film's code |

## Keep

- **One clock.** Every beat the picture uses is a name in `sound.py`'s table `T`, written to `kit/times.gen.ts`. The
  picture times everything from those names (`TM.CARD + 1`, `land - 1.5`), and `sound.py` places every note from them
  too (`SIGN = T["CARD"] + 1`, the tune the name is signed to; only the first chord sits at a bare 0, the first frame):
  move a beat in `T`, run `sound.py`, and the sound and the picture move together. The picture holds no clock of its
  own either: `sound.py` also writes `CLOCK` (frames a second, frames in a beat, beats, length), which `kit/core.tsx`
  and `film.tsx` import, sets `score.json`'s fps, duration and bpm, and writes `CUES`, the named events `vd sound`
  checks the mix against (the knocks under the stamps, the bells on the five grounds, the chord on the name).
- **Nested worlds and one camera.** Each world is drawn at ordinary sizes in its own 1920 by 1080 units and seated in
  the next by a scale (`seat` in `levels.tsx`). `world(k, f, d)` draws world k and every world inside it that is more
  than 26 px wide on screen, so the depth costs nothing where it cannot be seen. A film that is one long move outward
  (or inward) needs no 3D and no cut.
- **The camera's backing-out** in `film.tsx`: the view's width changes by the same ratio every frame, so each step
  out feels as long as the last; when the camera leaves a world it starts framed on the slot that world sits in, and a
  slot that sits turned brings the outer world level as the view lands.
- **The one tilt**: the wall is one plane turned about two axes on a smooth path through four framings (`ACROSS`), each
  framing chosen so the block of words stays whole. The wall is drawn seven tiles by seven so the tilt never shows
  its edge.
- **The curves** in `kit/core.tsx`: `arr` (an arrival that decelerates), `glide` (a move with weight), `ramp`.
  Only a stamp is instant: it lands in one frame, a little large, and settles.
- **The sound's shape**: three piano notes inside the paper, a voice added as the view widens, one chord a bar, a soft
  knock wherever the picture stamps, a bell on each of the five grounds, each a step higher than the last, and the
  chord that was waited for on the name.

## Changing the clock

The tempo and the length live in one place: `FB` (frames in a beat) and `BEATS` at the top of `sound.py`. Change them,
run `sound.py`, and the picture and `score.json` follow. Then move the beats in its table `T`. The moves' own lengths
(an arrival's 14 frames, a cover's 18) are counted in frames, so they keep their speed at any tempo.

## Replace (the subject)

`BOARD.md`, the table `T`, the words, the nine worlds in `levels.tsx` (keep `seat`, `SLOTS`' form and `world`), the
`PATH` rows in `film.tsx` (`camera()` picks the steady holds and the tilt across the wall by row index, `i === 1 || …`
and `i === 5`: change those with the rows), the pictures in `media/art/` with `SOURCES.md`, and the notes in
`sound.py`. Write the new board first, then replace a world at a time from the inside out, looking after each. This
README describes Linden Library: rewrite it for your film, or delete it.

## What is in it (seen in the film; none of it is a rule)

- **One thing carried:** the paper. The film opens inside it and ends with it filling the mark's window.
- **One move, played nine times:** the view backs out and the world it was in becomes a part of a bigger one: a
  cover, a tile, a card's window, a card on a ground (five times), the mark.
- **A stamp on every landing:** a date stamp on the book's slip, the wall's words, MEMBER on the card, each Dewey
  number. The knock in the sound lands with it.
- **The brand's mark is a window:** two Ls round a frame. The card holds the wall in it, and at the end the mark holds
  everything; the two Ls of the name and the two of the mark light together once.
- **Real material:** 24 sheets of decorated paper and five plates, all public-domain museum works, are the brand's
  hand; nothing in the picture is drawn to imitate them.

## What readers and the person changed

One round of three readers read the second cut, on sheets (frames at two a second and every frame of the busiest
stretches), with no sound: two from different model families ranked it blind among four films, and a third read it
alone for faults. Both rankers put it second of four. What the third cut changed, from what two or more of them said,
or one of them said and was plainly right:

| readers said | what changed |
|---|---|
| "of 400,000." is cut by the frame while the camera crosses the wall, and "One book" is tiny beside it | the words became one block over four tiles, on the wall from the start, and every framing of the tilt holds it whole |
| The card sits almost still for three seconds | two beats shorter (the film went from 52 beats to 50); it floats in depth and light crosses it once |
| The five grounds are one layout five times, and each plate comes in the same way | five layouts, each plate from another side |
| The first move strobes | a shorter first move, and the camera's blur (four pictures a frame, three averaged) |
| A cover turning edge-on reads as a glitch | a new paper slides up over the old one |
| The mark does not read; the words fade in dim; the numbers are small | lighter strokes, the Ls lit with the name's; words at full strength in four frames; numbers 88 px in a colour that reads on each ground |

Not acted on: fewer subjects, and not carrying the whole last scene forward (the nesting is the film); the card as an
advertising graphic; the date slip; soft shadows; the muted paper beside the bright grounds (the paper is the real
thing). No reader saw the third cut or later.

The person watched the fourth cut with sound and found one fault: "i think the sound is the only issue here." Its
sound was an imitation piano made from sines, with noise standing in for pages and brushes. The fifth cut kept the
picture frame for frame and replaced the sound with recorded instruments (a grand piano, vibraphone, glockenspiel and
plucked strings), with no noise in it. An instrument made of sines was the one fault the person found, and recorded
samples fixed it.

## Known limits

- **The level is under the skill's aim.** The film's sound is levelled to -17.5 LUFS in `sound.py` (`TARGET`), and
  `vd export` measures -17.3 LUFS integrated, true peak -2.2 dBTP: 2.3 LU under -15. The accepted cut measures the same
  -17.3. Setting `TARGET = -15.0` is not a plain gain: the mix's peaks do not leave room, so the levelling compresses
  it (its loudness range falls from 5.7 LU to 3.4 LU, measured). It is left as accepted, so `vd sound` and the scan print
  the level as a fault for this film as it comes. A film you make from it is finished at -15: set `TARGET` when you
  write its sound, and thin the mix at its peaks rather than let the levelling compress it.
- **One rest the scan lists:** the card is nearly still for 0.87 s (15.10 to 15.97 s), between the end of the
  signature and the light crossing it. It is under a second, so the scan asks nothing about it.
- **`vd look`, at the six moments above, prints four `!! FAULT` lines, all at 13.00 s.** The view is backing out
  from the wall to the member's card there, and four of the card's texts ("Linden", "Library", the member's name
  and "Yours to open.") are part way into the frame. The film was accepted that way. In a film of your own,
  answer every such line.
- **`vd sound` leaves one event to the ear:** the first landing (`LANDS[0]`, 18.00 s) reads 40 ms late.
- **Small words on the card:** MEMBER (20 px) and the card's number (24 px) are under the skill's 30 px, and the
  label's first line is 17 px in its world (it is read while the camera is close, much larger on screen).
- **The sound is dark:** `sound.py` prints its spectrum, and almost none of it is above 2 kHz (the piano is filtered
  softer the more quietly it is played).
- **The instruments' range:** the vibraphone's recordings run from F2 to E5 and the glockenspiel's from G4 to C7; a
  note is played from the nearest recording, read faster or slower.
- **No reader has seen the accepted picture;** the readings were of the second cut.
- The library, the member's card, the name and number on it, and the count of books are made up. The plates' numbers are
  real Dewey classes.
