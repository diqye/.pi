# Stet: the board

A launch film for a made-up developer tool, in the snap-and-hold style, held against a studio launch film for a developer tool (a film of this kind, taken apart and measured first). Written before the code, 12 November 2026. **This page describes the eighth cut; the accepted tenth kept every beat and restaged the middle** (the camera goes onto the proof: onto the panel for the fill, onto two flaky rows for "Same commit. Two answers. That's a flake." with those words set inside the panel, into the wall of 9,888 while it runs; arrivals take about 13 frames and decelerate; the four swaps are carried moves). `README.md` says what readers and the person changed on the way.

## One sentence

"It catches the tests that fail at random and holds them aside, so a pass means a pass."

## The product (made up)

**Stet** runs every test again on the same commit. A test that gives two answers is flaky. Stet holds it aside (it still runs, it cannot block a merge, a ticket is opened) and lets it back when it passes every time. The name is the proofreader's word for "let it stand", written as a row of dots under the words to keep.

## What a viewer of this kind expects, all kept

The problem in their own terms first · the mark early · pieces of the real interface (checks panel, run matrix, merge button, a command) · proofs with numbers · the name · what it works with · how to start · the logo.

## The world

- **Its line.** A test's result is a dot, and a proofreader's marks are what hold the ones that cannot be trusted.
- **The name, the mark and the claim.** "Stet" is the proofreader's word for "let it stand", written as a row of dots under the words to keep. The mark is a dot held between two brackets. The claim: a pass means a pass.
- **What it is made of.** Type, a checks panel, a matrix of runs, a pointer, and soft moving colour that takes the build's mood. One accent, vermilion, for a failed run and nothing else.
- **The moves it is built on** (the skill's WORLD.md): the answered opening ("It passed." returns as "Passed means passed."), one thing carries through (the dot), a colour is a noun, the silence before the name.

(This board was written before the skill's form asked for a world, a reason and a boundary for every row, and gifts. Its beats table keeps its own columns and has neither "why it follows" nor a boundary for each row, and it lists no gifts: a new board has all three.)

## The cast

| Thing | Made of | Its one job |
|---|---|---|
| **The dot** (conserved, first frame to last) | a circle | One run of one test. Neutral = passed, vermilion = failed. It is also the full stop of every claim, the grid of the page, and the mark's centre. |
| **The brackets** | two square brackets, drawn | Stet's hold. They shut on what is flaky. With the dot inside they are the mark, which is the badge on Stet's panel and, from the name on, the one thing that keeps its place. |
| **The air** | soft colour that moves like light through cloth (`kit/field.tsx`) | The build's mood: sky while it passes, a flush when it fails, sky again once the flake is held, morning from the release on. The person asked for a ground with character after an early cut on plain white. |
| **The page** | a faint grid of dots, 48 px, over the air | Every place a run could be. A ring passes through it where a thing lands. |
| **The pointer** | a black arrow with a ring where it presses | The cause: re-run, merge, copy. |
| **Specimens** | glass (the checks panel) and Stet's own dark panel (the run matrix), Geist Mono | checks · run matrix (tests x runs) · merge · command |
| **Stet marks** | a row of small dots under a key word | What to read if you read nothing else. |

One accent: vermilion `#FF4D1F` = a failed run = "look here". Type: Geist 500 for claims, Geist Mono for specimens.

## The clock

150 beats a minute, 60 frames a second: a beat is 0.4 s = 24 frames. In the accepted cut an arrival takes about 13 frames and slows into place, and the camera eases in and out and creeps in between (the first cuts snapped in 7 frames, and readers shown every frame read that as a swap). Act 1 is beats 0 to 11 on the film's clock. The acts after it are written on their own clock, beats 16 to 77, with a bar on every beat that divides by four, and drawn and heard five beats earlier (`SHIFT`). 72 beats = 28.8 s. The music has a chord a bar. Every beat lives once, by name, in the table in `sound.py` (`T1` for act 1, `T2` for the acts after it), which writes `kit/times.gen.ts` for the picture to import.

## The beats (later acts' clock; seconds on the film)

| Beats (s) | Part | Words | Picture |
|---|---|---|---|
| 0-5 film (0-2.0) | PROBLEM | "It passed." "You changed nothing." | Close on the sentence. The full stop flies in and lands (beat 1), hops to the head of the line, and the sentence is the "tests passed" row of a checks panel that builds round it. The pointer presses Re-run (beat 4). |
| 5-9 film (2.0-3.6) | THE FLIP | "It failed." | The camera pushes in, the air flushes. The pointer presses again and again: passed, failed, passed, failed, faster, word and dot flipping together. |
| 9-11 film (3.6-4.4) | THE CATCH | none | In the same close shot, two brackets shut on the flipping dot (beats 9 and 9.5) and it stops. The air clears, one flush passes through the page's dots, the scene falls away and the mark that is left grows. No name yet, and no full-frame card: the person and a reader both found an earlier orange card an interruption. |
| 16-22 (4.4-6.8) | ANSWER | "Run it again. And again. And again." | The mark goes to the head of its own dark panel and fires each column of runs: eight tests down, 24 runs across. A failed run flickers as it lands. |
| 22-28 (6.8-9.2) | | "Same commit. Two answers." "That's a flake." | The three speckled rows stay lit and the rest dim; their failed runs twinkle in turn; the three shake when they are named; the air warms a little. |
| 28-36 (9.2-12.4) | NUMBERS | "412 tests" · "9,888 runs" · "3 flakes" · "6 minutes" | The list backs out to forty, then to all 412 as strips of 24 dots in four columns. They run top to bottom with a clock. The three flaky strips come out of the block at full size and brackets shut on them. Every number is the count of what is drawn (412 x 24 = 9,888). |
| 36-44 (12.4-15.6) | HELD | "Held, not deleted." | Back to the eight; the three keep their brackets and drop under a line marked "held". The matrix stays live: a new run every half beat, the window sliding. |
| 44-48 (15.6-17.2) | RELEASE | "Fixed?" "Released." | Close on the held rows. A commit lands ("fix: debounce race"); that test runs 24 more, all passing; its brackets open; it climbs back. |
| 48-56 (17.2-20.4) | PASS | "Passed means passed." | Everything folds into the checks panel of the opening, large and centred: "tests · 410 passed · 2 held". The pointer presses Merge on the bar line (beat 52). The air clears. |
| 56-60 (20.4-22.0) | NAME | "Introducing" · "stet" | Everything folds into one dot; the brackets shut on it; the name types beside the mark. **The one silence**, half a second. |
| 60-64 (22.0-23.6) | FOR | "For" pytest · jest · playwright · "and 30+ more" | The mark keeps its place and what stands beside it changes, a name a beat. |
| 64-72 (23.6-26.8) | START | "One line to start" · `npx stet init` · "Free for open source." | The command types beside the mark like a prompt. The pointer presses Copy (beat 68). |
| 72-77 (26.8-28.8) | END | "stet" · "Let it stand." | The name again beside the mark, on the last chord, and the line under it. |

## The turn

The brackets shut and the flipping stops. Before it nothing on screen can be trusted and the air is flushed; after it everything holds and the air is sky. The music turns there too: the sour bar resolves to the home chord.

## Ties

| What | First | Returns | What the return means |
|---|---|---|---|
| The dot as full stop | "It passed." | every claim; vermilion on "It failed." and "That's a flake." | A claim is a verdict. |
| The brackets shutting | the catch | on the three flaky tests; on the dot again at the name | The same act: hold it. |
| The checks panel | beat 2 | PASS | The same panel, now telling the truth. |
| The pointer's press | Re-run | Merge; Copy | Re-running was the problem; the last two presses are the viewer's next two actions. |
| The mark | the catch | the panel's badge; the name; the prompt; the end card | It is the product, in every scene after it appears. |
| "It passed." / "Passed means passed." | the first words | PASS | The opening line, now true. |
| The tune | PASS | START to the end | The win, and the invitation. |

## Rules of this film

1. Arrive and hold: an arrival takes about 13 frames, slows into place and lands on a half beat; only a bracket shutting is instant. Between arrivals the camera creeps and the air moves, so nothing is frozen and nothing fidgets.
2. One copy of each thing at every instant. Things turn into the next thing.
3. The cause is on screen before the change: the pointer presses, then the dots run; the mark fires, then the column lands; the commit lands, then the test runs.
4. Vermilion is only ever a failed run, or the mark that holds one. The air may flush toward it; nothing else is that colour.
5. The air has one family of colour at a time, and its change of mood always has a cause in the story.
6. Every number on screen is the count of what is drawn.
7. No built 3D. Depth comes from the camera over the page, the air lagging behind it, glass and its shadow.

## Hardest shot

The flip and the catch (2.0 to 4.4 s): a word, a dot and the air changing state, faster each time, with the pointer's press as the cause, and then two brackets stopping it dead in the same shot.

## Three to six seconds that stand alone (for the teaser)

2.0 to 4.4 s: failed, the flip, the brackets shut, the mark.

## Sound

No voice. Music first: one tempo, D major, a chord a bar, one pattern from the first full stop to the last, and one tune (at PASS, and from START to the end). The picture's events are played inside it and in its key: passed and failed are two sounds, so the flip is heard; the brackets are wooden clacks; the columns of runs climb the scale. One silence, on the name. Synthesised in `sound.py`; no samples, no paid service.

## Sources and licences

Geist and Geist Mono (Vercel), SIL Open Font License 1.1, embedded from `kit/fonts.gen.ts`. Everything else is drawn in code. The product, its numbers and its interface are invented; the test-runner names in the "For" passage are real open-source tools named as words only. The studio film it was held against is other people's work: its shape was studied and nothing of it is in this folder.
