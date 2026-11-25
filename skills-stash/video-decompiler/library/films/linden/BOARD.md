# Linden Library: the board

A rebrand film for a made-up library. Written before any code, 12 November 2026. **This page is that first board; the
accepted fifth cut kept its one move and changed** the clock (50 beats, 30.0 s: the label lands a beat earlier and the
card is held two beats less), "Stars 523" for "Maps 912", the wall's words (one block, "One of 400,000.", that every
framing of the tilt holds whole), the five grounds (five layouts, each plate from another side), the covers on the wall
(a new paper slides up over the old), the export (a camera's blur), and the sound (recorded instruments in place of
sines and noise). "The beats, as accepted" and the sections marked *written after the film, for this form* describe
the accepted cut. `README.md` says what readers and the person changed on the way.

## One sentence

Start as close as a sheet of old paper and keep backing out: it is a book, the book is one of a wall of books, the
wall is on a library card, and all of it is inside the library's mark.

## The brand (made up)

Linden Library, a city's public library, rebranded. Its mark is two letter Ls that make an open frame: one at the
bottom left, one turned round at the top right. The frame is a window, and whatever the library holds can sit in it.
The line: "Yours to open."

## What the film is held against

A studio's rebrand film (HEX's for dessn), taken apart before this board: every ground is the face of a bigger thing,
the grounds are the brand's colours at full strength, the cut is a change of ground, and the brand's own hand is on
everything. Here the hand is not drawn: it is real decorated paper, the kind books were bound in.

## What this film tests

What readers of earlier films still gave only to studio films is a camera that travels through the material: it
tilts across things, dives into a detail, moves down a row. This whole film is one move of the camera, outward,
through real material, with a tilt across the wall of books on the way.

## The world (*written after the film, for this form*)

- **Its line.** A library is worlds inside worlds: a sheet of paper is a book's cover, the book is one of a wall, the
  wall is what a card opens. The film is that line as one move.
- **The name, the mark and the claim.** Linden Library; two Ls round a window; "Yours to open." The window is the
  thing opened, and at the end it holds everything the film passed through.
- **What a rebrand film usually looks like, and what this one leaves.** Flat colour grounds and the mark animated on
  its own. It keeps the full-strength grounds and leaves the drawn shapes: everything in the windows is real material.
- **What it is made of.** Twenty-four sheets of decorated paper and five plates, all public-domain museum works; seven
  colours at full strength (tomato, cobalt, sun, forest, rose, cream, ink) for the grounds and the wall's tiles, none
  with a meaning of its own; a grotesque for large words, a serif for a sentence, a mono for call numbers and dates. The
  ground is never soft colour here: it is the face of the next, bigger thing, which is the question each landing
  answers ("and what is this inside?").
- **The moves it is built on** (WORLD.md): one thing carried (the paper, first frame and last); every change of scene
  is a *becomes* (the world the camera was in becomes a part of the next); the answered opening ("Start anywhere."
  on the first label, "Yours to open." under the name).

## The cast

- **The paper.** A real sheet of decorated paper from a museum's open-access collection. The film opens inside it.
- **The grounds.** Seven colours at full strength: tomato, cobalt, sun, forest, rose, cream, ink. No gradients.
- **The mark.** The frame of two Ls. It is on the card as a window with the wall of books in it, and it is the last
  thing left, with everything inside it.
- **The stamp.** A library's date stamp. Each time the view lands on a new ground, a stamp lands with it.
- **The type.** One grotesque for the large words, one serif for a sentence, one mono for call numbers. The call
  numbers are real Dewey numbers.

## The clock

As first written: 100 beats a minute: a beat is 36 frames, a bar is 4 beats (2.4 s). 13 bars, 52 beats, 1872 frames,
31.2 s. As accepted: 50 beats, 1800 frames, 30.0 s.

## The beats, as first written

| beats | what happens | words |
|---|---|---|
| 0 to 4 | Inside the paper: its colour and grain fill the frame, drifting. | a book label at the frame's edge: "Start anywhere." |
| 4 to 8 | The view backs out. The paper is the cover of a book lying on a tomato ground, with its date slip. Lands on 8. | "One book" |
| 8 to 12 | A breath, then out again: the tomato ground is one tile in a wall of tiles, a book on each, every cover a different paper. Lands on 12. | |
| 12 to 20 | The camera tilts and travels across the wall. Covers change in place. Two tiles of the wall are words. | "of 400,000." |
| 20 to 24 | Out again: the wall is the picture in the window of the mark on a library card, on a cobalt ground. Lands on 24. | |
| 24 to 30 | The card. A name is signed on it. | "All yours, with this." |
| 30 to 40 | Out, five times, two beats each: each ground is a card on the next ground, and on each ground lies one kind of thing a library holds, with its number. | "Birds 598", "Maps 912", "Music 780", "Gardens 635", "Moths 595.7" |
| 40 to 44 | The last ground is cream, and all of it sits in the window of the mark. | |
| 44 to 52 | The name. The window fills with paper after paper and ends on the first one. | "Linden Library", "Yours to open." |

## The beats, as accepted, and how each part hands to the next (*written after the film, for this form*)

Each beat is a name in `sound.py`'s table `T`; seconds are at 0.6 s a beat.

| beats | seconds | what happens | words | how it hands to the next |
|---|---|---|---|---|
| 0 to 3 | 0 to 1.8 | Inside the paper, drifting. The label comes down onto it at 1.5 (`LABEL`) and the view holds on it. | "LINDEN LIBRARY · 761", "Start anywhere." | becomes: the paper is a cover |
| 3 to 8 | 1.8 to 4.8 | Out (`OUT1`): a book on a tomato ground, with its date slip. Lands on 8 (`BOOK`): today's date is stamped. | "One book" | becomes: the ground is one tile |
| 8 to 12 | 4.8 to 7.2 | A breath, then out (`OUT2`): the book is the middle tile of a wall, a book on each, every cover another paper. Lands on 12 (`WALL`): the block of words lands like a stamp. | "One of 400,000." | carried: the same wall, crossed |
| 12 to 20 | 7.2 to 12.0 | The camera tilts and travels across the wall. Three waves of covers change, a new paper sliding up over the old (`FLIPS`). | | becomes: the wall is a window |
| 20 to 24 | 12.0 to 14.4 | Out (`OUT3`): the wall is in the mark's window on a member's card, on cobalt. Lands on 24 (`CARD`): MEMBER is stamped. | | |
| 24 to 28 | 14.4 to 16.8 | The card floats in depth; a name is signed; light crosses it once. It is flat again before the view leaves. | "All yours, with this.", "Linden Library", "Yours to open." | becomes: the card lies on a ground |
| 28 to 38 | 16.8 to 22.8 | Out (`OUT4`), then five grounds two beats apart (`LANDS`): each holds the last as a card, with one plate, its word and its number stamped. Five layouts. | "Birds 598", "Stars 523", "Music 780", "Gardens 635", "Moths 595.7" | becomes: each ground is a card on the next |
| 38 to 42 | 22.8 to 25.2 | Out: the last ground sits in the mark's window on cream. | | the ground changes: the window fills with paper |
| 42 to 50 | 25.2 to 30.0 | The name lands like a stamp (`END`); the Ls of the name and of the mark light together once; the window fills with paper after paper (`SWATCH`) and ends on the first one. | "Linden Library", "Yours to open." | the end |

## Ties (*written after the film, for this form*)

| what | first | returns | what the return means |
|---|---|---|---|
| The paper the film opens inside (paper 01) | beat 0 | last in the mark's window, beat 46.75 | everything the film backed out through was inside this one sheet, and the library holds it |
| "Yours to open." | under the card's window, beat 24 | under the name, beat 43.6 | the card's promise is the brand's line |
| The mark's window | on the card, holding the wall, beat 20 | holding everything, beat 38 | the card opens the whole library |
| The stamp | the date due, beat 8 | MEMBER, each Dewey number, and the name | every landing is a library's mark of use |

## Gifts (*written after the film, for this form*)

- Beats 13.5 to 17.5: while the camera crosses the wall, covers change under it, a new paper sliding up over the old.
- Beat 43.1: the two Ls of the name and the two Ls of the mark light together once: the mark is made of the name.
- Beats 42.75 to 46.75: paper after paper fills the window and the last is the first.

## Rules of this film

- One move. No cut anywhere: each ground is carried into the next as a card.
- A move from rest eases in. A landing decelerates. Nothing changes in one frame, except a stamp.
- Text that carries the story is 30 px or more on screen when it is read.
- No control or line of words is cut by the frame while it is being read.
- Every hold has something moving for a reason: the camera drifts or tilts, covers change, a name is written.
- Music first; the stamps are its downbeats.
- Every export is scanned for pops and holds.

## Hardest shot

Beats 0 to 20: from inside the paper, out to the book, out to the wall, and the tilt across the wall. Built and
looked at first, with real paper.

## Three to six seconds that stand alone (for the teaser)

Beats 4 to 12: paper to book to wall.

## Sound

As accepted (the fifth cut's): played on recorded instruments, with no noise in it. A grand piano carries it, in E flat,
one chord a bar; a vibraphone and a glockenspiel ring on the landings; plucked strings are the bass; a soft knock, like
a book set down, marks each landing where the picture stamps. It starts with three piano notes inside the paper and
adds a voice as the view widens. The first sound, made from sines and noise (an imitation piano, noise for pages and
brushes, a thud for each stamp), was the one fault the person found; the beats did not move when it was replaced.

## Sources and licences

Papers and plates: public-domain works from the open-access collections of the Metropolitan Museum of Art, the Art
Institute of Chicago and the Cleveland Museum of Art, each flagged public domain or CC0 by the museum's own record;
the list is `media/art/SOURCES.md`. Fonts: Bricolage Grotesque, Fraunces, Geist and Geist Mono, SIL Open Font License
1.1. Instruments: Salamander Grand Piano (Alexander Holm, CC BY 3.0), FluidR3_GM pizzicato strings (Frank Wen, CC BY
3.0), VCSL vibraphone and glockenspiel (CC0); the two CC BY ones must be credited wherever the film is published.
