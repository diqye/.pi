# Plus One

A product demo for a made-up invitation app: one task done in order, on real pictures, ending on people answering. 38.4 s.

1920x1080 at 60 frames a second, composition `film`. The person it was made for watched it once, at speed, with the
sound on, and said "this is genuinely incredible. it's done", and later that it had "strong connection between the
frames, everything played together ... cohesive, meaningful, and enjoyable to watch". Start from it when your product
is something a person uses and the film is them using it.

## Run it

In a copy made with `vd new NAME --like plusone`, not in the skill's own folder: only the copy's `score.json` names the
mix that `vd export` carries.

```
python sound.py                          # writes media/sound.wav and kit/times.gen.ts (run again whenever a beat moves; vd export stops until you do)
vd look --at 2,9,14,22,31,36             # six moments as one picture
vd export                                # the film with that sound, about two minutes, then the scan
```

The look's report names a few texts cut by the frame's edge (`!! FAULT`): the side cards at 14 s and two guests at
31 s leave the frame on purpose, and the film was accepted that way. A newer raea lists more of them than the one
the film was made on; the picture is the same.

## What is where

| file | holds |
|---|---|
| `BOARD.md` | the film on one page, as it was written before the code |
| `sound.py` | the music, every sound, and the table `T` of every event's beat. It writes `kit/times.gen.ts` |
| `film.tsx` | the camera table (framings as rows, eased between) and the order of the layers |
| `acts1.tsx` | the mess, the typed line, the line becoming the card, the large words, the pointer |
| `acts2.tsx` | the card wherever it is, the guests, the "+1"s, the fireworks, the end |
| `card.tsx` | the card and its looks (`LOOKS`); `invite` draws a card's face, `place` stands it in depth |
| `people.tsx` | the guests: where each stands, who answers and in what order |
| `kit/core.tsx` | the clock (`FB`, frames in a beat), the colours, the curves, the plain parts |
| `kit/field.tsx` | the room: soft moving colour that takes its palette from the picture on the card |
| `kit/fonts.gen.ts` | Geist and Geist Mono, embedded as data so they draw on any machine |
| `kit/metrics.gen.ts` | those faces' letter widths, which the kit sizes things to words with. Change the running face and make it again: `python SKILL_FOLDER/tools/metrics.py YOUR-SANS-VF.ttf YOUR-MONO-VF.ttf` |
| `kit/times.gen.ts` | the clock (`CLOCK`), every event's beat (`TIMES`), the typed line (`LINE`) and the named events `vd sound` checks the mix against (`CUES`), written by `sound.py` |
| `media/art/` | the pictures, with `SOURCES.md`: every work, its museum and its public-domain flag |
| `media/fonts/` | the display face of each look, which `kit/core.tsx` loads by name, with their SIL Open Font License texts and those of Geist and Geist Mono |
| `main.tsx`, `ids.ts` | the entry: `film`, and `film-look` (the same film without its grain) for `vd look` |
| `score.json` | the frame size, and the fps, length and bpm `sound.py` sets |
| `LICENSE-video-decompiler.txt` | the licence of this code |

## Keep (the kit: none of it is about invitations)

- **One clock.** Every beat the picture and the sound use is a name in `sound.py`'s table `T`, or a name plus an
  offset that belongs to the move itself (`TM.OPEN + 0.55`); the frames a part takes to fly to the card (`FLY`), which
  both use, are there too. Move a beat there, run `sound.py`,
  and the sound and the picture move together. The picture holds no beat numbers of its own: `sound.py` also writes the clock (`CLOCK`: frames a second, frames in a beat, beats, length) that `kit/core.tsx` and `film.tsx` import, sets `score.json`'s fps, duration and bpm, and writes `CUES`, the named events `vd sound` checks the mix against.
- **The curves** in `kit/core.tsx`: `arr` (an arrival that decelerates into place over 14 frames), `glide` (a move
  with weight: eases in and out), `pop` (a landing with spring), `ramp` (a fade). A thing at rest leaves with `glide`,
  never with an arrival curve: it would leave at full speed and read as a swap.
- **The camera** in `film.tsx`: a table of framings, eased in and out, that keeps pushing a little in every hold.
- **The room** in `kit/field.tsx`, and the rule that it takes its colours from what is on screen.
- **Cards in depth** (`place` in `card.tsx`): one vanishing point, far cards out of focus, drawn far to near.
- **The sound's shape**: single struck sounds on changes of picture, out of silence, for the opening; the chords
  arrive with the name; one chord a bar; the replies are the tune and climb with the count.

## Changing the clock

The tempo and the length live in one place: `FB` (frames in a beat) and `BEATS` at the top of `sound.py`. Change them,
run `sound.py`, and the picture and `score.json` follow. Then move the beats in its table `T`.

## Replace (the subject)

`BOARD.md`, the table `T`, the words, `acts1.tsx`, `acts2.tsx`, `people.tsx`, the `LOOKS` in `card.tsx`, and the
pictures in `media/art/`. The typed line, `LINE` in `sound.py`, goes with two things it does not set: the letter
ranges of its three parts (`PARTS` in `acts1.tsx`) and the card's words (`TITLE`, `WHEN`, `WHERE` in `card.tsx`).
Change all three together, or the underlines and the flying parts land on the wrong letters. Write the new board first and replace an act at a time, looking after each. This README
describes Plus One: rewrite it for your film, or delete it.

## What is in it (seen in the film; none of it is a rule)

- **One thing carried:** the card. A typed line becomes it; it is dressed, sent, answered, and ends as the mark.
- **One move, played twenty times:** an invitation is answered. Each "+1" adds a face, a count, a firework, a few words.
- **A high point at 82%:** the count goes from 19 to 20 on "can I bring Theo?". The question asked in the opening
  mess comes back and is answered by the product's own name.
- **Both sides of the product:** the host's screen, then one guest's own phone and her finger on "I'm in".
- **The real pictures are what the product makes** (the invitation's looks, chosen in the story), not decoration.

## What one round of readers changed, before the person saw it

| a reader said | what changed |
|---|---|
| No guest is ever shown answering; the claim rests on a counter | a guest's own phone, her press, her face first on the card |
| The card breaks up before Send is pressed | press, then "Sent to 24", then the copies leave from behind the card |
| The guests come from nowhere | the pointer taps "Add guests"; the button reads "Send to 24 guests" |
| Why is 20 the finish | "20 of 24 in" |
| The room changes colour in one frame | the flick eases in; the room follows on its own curve |
| The typed line spills over the card | its three parts leave together; nothing sits outside the card |

All but one are about the story. That is the order to fix in.

## Known limits

The sound is sines and noise made in code, with less low end and a narrower stereo picture than a studio's. Its wav
peaks at -3.1 dB and the export's AAC encode lifts that to -0.6, so `vd export` lowers this film's sound by 0.75 dB in
the exported file (-15.7 LUFS, -1.4 dBTP, measured 12 November 2026). The cut that was accepted went out at -15.0. The
guests' portraits are public-domain paintings standing in for made-up people (`media/art/SOURCES.md`).

As it comes, the tools say three more things about this film, each of the film as accepted:

- **`vd sound` leaves three of its 32 named events to the ear:** the tap (`TAP`, 23.60 s) reads 80 ms early, and two
  replies read late, `REPLIES[10]` by 27 ms and `REPLIES[11]` by 270 ms, at the moment of the reply after it.
- **`vd look`, at the six moments above, warns that 5.2% of the picture at 31 s clips to white** (the frame with the
  large cream "19 in."), and at 14 s prints `not applied: "transform in a style attribute"`. That is raea's note
  on one element's transform; it names no element. The cards there stand in depth by a long transform (`place` in
  `card.tsx`). It has not been traced further.
- **The scan asks nothing:** no pop, and no hold of a second or more.
