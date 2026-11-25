# Eyes

How you see the film without being its maker. Four eyes, cheapest first, used in that order: a look, a number, a
reader, a person. Readers find faults; they do not decide. Only the person can say the film is good.

## Look: `vd look`
`vd look` draws the moments you ask for in one raea process and lays them out as one picture, each tile with its time and frame in a band above it. With no `--at`, it takes moments spread over the film. One moment alone is drawn at the film's own size, up to 1920 px wide. Use it after every change to a shot, before any clip.

Read its report first: it names faults a picture hides. Most of it reads raea's own record of what was drawn: text beyond the frame, a layer that is frontmost nowhere, a refusal. A line marked `!! FAULT` is text whose letters cross the frame's edge while on screen. Where the letters lie is worked out from the text's box, its size and its alignment, on the wide side, so now and then a line that is whole is called cut: look at the tile. Two newer kinds read the drawn pixels and are not yet proven on an accepted film, so read the tile before acting on them: text over a busy picture whose contrast is under WCAG's floor (4.5:1, or 3:1 for text 24 px and larger), found where raea's layer mask shows a busy ground under the text: a picture, or any drawn ground that is not text, with see-through ink mixed with what it shows; and a cut where the eye's likely point (the largest text, else the busiest place) jumps more than 45 degrees, a limit nobody has measured. That one runs only when two moments asked for are adjacent frames (`--at T,T2` with T2 one frame after T) and the two differ as a cut does; a `join` mark in raea's record would silence it, and nothing writes one yet. Neither is marked `!! FAULT`. The other kinds print once each, with a count and their three worst cases. The whole report is in `look-report.txt` beside the picture, and `--all` prints it.

What the report still cannot see: one text lying over another text on a plain ground, non-text shapes colliding, or whether a balanced layout looks cramped or empty. Read the tiles for that.

The picture goes to `~/.vd/out/NAME/look.jpg`. For one frame of a finished file at its own size: `ffmpeg -ss SECONDS -i FILM.mp4 -frames:v 1 frame.png`.

## Scan: inside `vd export`, or `vd scan FILM.mp4`
Four checks on the finished file, printed as one block headed SCAN and kept in `~/.vd/out/NAME/scan.txt`, NAME being the film folder you are in. A film from anywhere else, scanned from there, is kept beside it as `scan-ITSNAME.txt`, so your own film's scan is never written over. The block ends with a count line (`scan: 2 to fix and 1 to check`), which also says when the file has no sound or its level is off. A hold close to half a second can come and go between two exports of one film: the encoder's own noise moves it across the line.
- **pops**: a frame that changes far more than the frames on either side of it. Each is a thing swapped, reset or flashed in one frame.
- **holds**: every stretch of half a second or more where nothing moves, with the share of frames that are still. A hold you chose creeps or breathes; one you did not is a dead second. "Still" here is what a viewer would call still: a slow push on a plain card changes too little to count, or to be seen. To keep a long hold alive, move something a viewer can name (a line arriving late, a mark settling, light crossing). The scan measures change over the whole frame, so small things changing in place (rows flipping, a list rewriting itself) can still print as a hold: look at that stretch on the sheets, and if a viewer can see and name what is changing, write that down as your answer and go on.
- **level**: loudness and true peak against -15 LUFS and -1 dB. A film finished quieter than the films beside it sounds weaker. The export's AAC encode lifts peaks, by 2 to 3.5 dB on a bright mix: leave the wav's own true peak at -2.5 dB or lower, and when the scan still shows the exported peak over -1, bring down the top end (above about 2.5 kHz), not the whole level. `vd export` tries lowering such a file's sound, by up to 1 dB, and keeps the smallest step that brings the peak under while the level stays in range; when none does, it leaves the level as it was and the scan names the fault.
- **flashes**: the safety rule for flashing (WCAG 2.3.1, by `tools/flash_scan.py`). A flash is a pair of opposing changes in brightness over a quarter of the viewer's central ten degrees (a third of the frame's width by 4/9 of its height, for a 16:9 film on a 1024 by 768 screen), or in saturated red; more than three in a second is a `fix before anyone watches` line. On the 720p copies of the four accepted films the busiest second holds 3 or 4 such changes, under the limit of 6, and none is flagged. Motion and patterns that are not WCAG flashes (a pan over stripes, a slide, a stripe or checkerboard reversing) get a line of their own, `motion or patterns (not WCAG flashes)`: look at that second at full size, since a high-contrast pattern reversing can still trouble a viewer. The field assumes a full screen at a usual distance; a phone held close is stricter.
A line that starts `fix before anyone watches` is a pop or a flash. A pop you may keep if it is a hit you meant, with its sound on that frame (a bolt, a key pressed): the accepted films kept theirs and wrote each down as meant. A flash over WCAG 2.3.1's limit has no such exemption: fix it before any reader sees the film. A line that starts `check` is a hold over a second: keep it only if you chose it. On the first cut of one accepted film this scan found fourteen seconds of holds in a film that looked busy on its board.

## Measure: `vd measure FILM --against REF`, `vd pin REF`
Every number the measure takes (pace, shots, words a second, still share, moves, sync, colour, levels), ours against a reference, with times: the gaps that matter most first (sound, stillness, words, then the rest), forty rows at most. `pin` writes the reference's numbers into score.json as `targets` and its story sheets, move sheets and six moments at the film's own size (up to 1920 px wide) under `~/.vd/out/NAME/pin/` (TAKE-APART.md). A reference can be a film, a `measures.json`, or a folder holding one, and measures are cached by the file's content. A gap is a question for the frames, not an order: a film's kind sets its own numbers (one accepted film is still in over half its frames, as the film it was held against is). The transcriber can hear words in music: when no film in the comparison has a voice, `--no-voice` skips it for ours, the reference and the bare pass. Without a transcriber on the machine (`vd doctor` lists it as optional), a film's words are `not transcribed` and its word measures are left out, never read as no voice. Out: `~/.vd/out/NAME/GAP.md`.

`vd borrow REF` writes the same sheets as `pin` (but no `targets`: run `pin` for those) and also fits the reference's moves (a spring's speed and damping, a curve) and its colours into `dna.json` and `kit/dna.gen.ts`: every ground (a full-frame colour held half a second or more, read over the whole film four times a second, with its seconds and stretches), the accents set on them, and the swatches of its holds, with a `REFERENCE.md` to finish by TAKE-APART.md: it fills the headings it measured (spine, moves, measured, with its events' sync to the sound against chance) and leaves the world, the formal idea and every other reading to you. When no move fits a spring, it says so and `DNA_SPRING` and `DNA_BEZIER` are `null`: there is then no spring of that film's to take. No accepted film has been held against those fits yet: read them as `pin`'s numbers are read, as questions for the frames.

## Sound: `vd sound`
The sound's own check, with no picture: loudness and true peak, where each cued hit starts (its first rise, else its peak) against the score's sounds and a worked film's named events (`CUES` in `kit/times.gen.ts`), and any silent hole that is not a silence named in `rests`. It prints a verdict line, `sound passes` or `sound fails:` with what failed (and ends with exit code 2 when it fails), and says whether sync was checked and which events to check by ear (no agent can: a hit can hide under a louder one a fraction of a beat away, so name those events and their times to the person when they watch). Out: `~/.vd/out/NAME/sound.txt`. Nobody but the person can hear the film: a level is not a tune.

## Readers

A reader is a new agent that knows only what its brief gives it. One round is three readings, and it is the round every accepted film had before its person saw it:

- **Two line-up readers**, from different models, each reading a blind line-up of up to four films: yours, the film it is held against, and a worked film from `library/films/` that you exported. (After the person's notes, a later line-up can hold your earlier cut as its fourth film.) With only one family of model to hand, use two different models of it (or the one model twice), and say in the report that the readers were not independent. With no way to start another agent at all, there is no blind round: say so, and tell the person no reader has read the film.
- **One fault-finder**, reading your film alone, every frame of its ten busiest seconds.

Make what they read with `vd pack FILM --against REF --against WORKED.mp4` (each a full path; SKILL.md says where exports are). It writes the pack to a folder of its own under `~/.vd/reads/`, with a random name, so no film's name is in any path a reader is given: `lineup/` (a folder for each film under a letter, the letters dealt afresh each pack: story sheets at two frames a second, and every frame of its five busiest seconds) and `alone/` (your film: story sheets, every frame of its ten busiest seconds, five moments at full size). The key, `~/.vd/out/NAME/pack-N-KEY.txt`, is outside it, and `vd pack` prints both paths. Give readers only the pack's folder. On a story sheet a tile's time sits in a band above it, and on a motion sheet its time and frame, never on the picture, and the tiles are smaller than the film: a story tile is 400 px wide and a motion tile 320, and only the keys are at the film's own size (the briefs below say so: a reader has taken a 30 px label for a 12 px one). Readers cannot hear.

### What to do with what they say

- Keep every reading, in the reader's words, in `READINGS.md`: what was said, then what the next cut changed.
- Fix story faults first: an action that does not read, a step that is missing, a claim only said. In the film that was liked best, a reader's "no guest is ever shown answering" became one new shot, and it is the clearest second in the film.
- Act on what two readers name, and on any fault you can see for yourself on the frames. One reader's taste is not a finding.
- Count the line-up readers' answers to "who made it". When both say a beginner or a hobbyist, that is an alarm: their reasons say where to look, and the report says plainly that readers placed it there. No second vote is taken. The person settles it, as they do when readers say a freelancer or a studio. Weigh the fault-finder's answer less: a film read alone is marked lower than the same film read beside others. And when the faults they named survive a repair, question the film's world before its finish.
- The worked film in the line-up is the yardstick: a person accepted it. When both readers rank yours below it, take yours as not yet at its level, whatever label they give it, and say so in the report with their reasons. Two readers of stills can share a mistake: this is a working rule, and it is the person's eye that settles it. (On four test films this held, and the person, watching them afterwards, placed none above the worked film.) A studio's own film will usually win the line-up; read the ranking for where yours sits against the worked film, not for the win.
- Do not use their ranking to choose between good films. Reading stills, a reader prefers a clean, sparse frame; the person, watching at speed with sound, preferred a full one that the readers had marked down. (In one later line-up of three, a reader ranked that accepted film last, for its fullness, and a reader from another family of model ranked it first: this is why there are two, from different models.) "Busy" is a note to pass on, never a reason to thin the frame.
- `vd evolve NAME` packs four world sketches, one after each worked film, as a blind line-up (`tournament/A..D`, with its brief). The rule above holds there too: readers of stills prefer the sparse sketch, so read their answers for what each sketch fails to say, and let the person choose the world when one can be asked. No film has yet been made from a sketch chosen this way.
- When readers disagree about a device, do not cut it on that alone: look for what both were reaching for. A line or a device that still does not read after two stagings goes.
- One round, then one more reading of the fixed cut by a new fault-finder alone, with the same brief: hold its list against the first one's to see that each fault is gone. Small faults it still finds can be fixed without another reading. A film held behind round after round of readers gets no better for it.

Send each brief as it is, filling in the capitals.

### The line-up (two readers, different models, the same pack)

> You are a reader in a blind comparison of N short product films. This is a read-only task: do not edit, create or delete any file, do not use the network, and do not start subagents.
>
> WHAT YOU HAVE
> The folder FOLDER (the `lineup` folder inside the pack `vd pack` printed) holds N subfolders named by letters, one per film. Each subfolder holds:
> - story sheets: the whole film at two frames a second, in order, with the time printed on each tile.
> - move-1.jpg to move-5.jpg: EVERY frame of five one-second stretches of that film, the stretches where the most changes (the frame number and time are printed on each tile). These sheets are how you see the motion. Read them tile by tile and compare each tile with its neighbours.
> You cannot hear the films. Judge picture and motion only. Between the story's tiles and outside the five stretches you have seen nothing: where a judgement rests on what happens there, say so.
> The sheets show each film smaller than it is: a story tile is 400 px wide and a motion tile 320 px wide. Allow for that when you judge the size of text.
> Look only inside that folder. Do not open other folders, and do not search the disk or the web for these films or for notes about them: knowing who made which one would spoil the reading.
>
> WHAT TO DO
> Open every image in all the subfolders and look at each one as an image. Then answer, in plain text, in this order:
>
> 1. RANKING. Rank the films as motion design craft, best made first. For each neighbouring pair in your ranking, name the specific things that put one above the other, citing folder letter, sheet and frame number or time.
> 2. For each film, in two sentences: what is being sold, and what happens.
> 3. For each film: who do you think made it? Pick one: a beginner, a skilled hobbyist, a freelance motion designer, a professional studio. Say how sure you are and the one thing that most pushes you to that answer.
> 4. For each film: its strongest moment and its weakest stretch, with times.
> 5. For each film: every place where the motion looks wrong when read frame by frame. For example: a jump between two neighbouring frames; something that appears or vanishes within one frame and is not a deliberate hit; a move that starts or stops abruptly; a hold where nothing moves for more than half a second; text that is cut off, overlapping, or too small or dim to read; something cut awkwardly by the frame edge. Cite sheet and frame.
> 6. If these were shown publicly side by side, would any of them embarrass its maker? Which, and why? If none, say so.
>
> Be specific and blunt. Do not soften, and do not balance criticism with praise for its own sake. Where you cannot tell, say so. Your final message is the whole deliverable: put the ranking first.

### The fault-finder (one reader, your film alone)

> You are the fault-finder for one LENGTH-second KIND OF FILM: WHAT IT IS FOR, IN A FEW WORDS. Your job is to find what is wrong with it. Praise is not needed. This is a read-only task: do not edit, create or delete any file, do not use the network, and do not start subagents.
>
> WHAT YOU HAVE
> The folder FOLDER (the `alone` folder inside the pack `vd pack` printed) holds:
> - story sheets: the whole film at two frames a second, in order, with the time printed on each tile.
> - move-1.jpg to move-10.jpg: EVERY frame of ten one-second stretches of the film, the stretches where the most changes (frame number and time are printed on each tile; the film runs at RATE frames a second). These sheets are how you see the motion. Read them tile by tile and compare each tile with its neighbours.
> - key-1 to key-5: five moments at full size.
> The sheets show the film smaller than it is: a story tile is 400 px wide and a motion tile 320 px wide. Only the keys are at the film's own size, so judge the size of text on them.
> The film has music and sound, which you cannot hear. Judge picture and motion only, and say where the picture seems to depend on sound you cannot check. Between the story's tiles and outside the ten stretches you have seen nothing: where a judgement rests on what happens there, say so.
> Look only inside that folder. Do not open other folders, and do not search the disk or the web for this film or for notes about it.
>
> WHAT TO DO
> Open every image in the folder and look at each one as an image. Then answer, in plain text, in this order:
>
> 1. From the picture alone, in two sentences: what is being presented, and what does the film claim about it? If you cannot tell, say exactly what is missing.
> 2. Tell the film back in order, one line a step, as a stranger would understand it. Mark any step you had to guess.
> 3. Every fault you can find, most damaging first. For each: the sheet and frame or time, what you see, why it is a fault, and what you would change. Look for: a jump between two neighbouring frames; something that appears or vanishes within one frame and is not a deliberate hit; a move that starts or stops abruptly; a hold where nothing moves for more than half a second; a framing where something is cut by the frame edge or sits awkwardly; text that is too small, too dim, overlapping, misaligned or misspelt; a layout that is unbalanced, crowded or empty; colour that looks muddy or garish; anything that looks like a rendering error; an idea that does not read, or a step that does not follow from the one before; anything that looks cheap, generic or like a template; anything in the brand's own design (its mark, its type, its colours) that a designer would fault.
> 4. The three faults you would fix first, and why those.
> 5. Any stretch you would cut or shorten, with times.
> 6. Who made this? Pick one: a beginner, a skilled hobbyist, a freelance motion designer, a professional studio. Say how sure you are and the one thing that most pushes you to that answer.
>
> Be specific and blunt. Do not soften. Where you cannot tell, say so. Your final message is the whole deliverable.

## The person

The judge, and the only eye that hears the film and sees it at speed. Their time is for what readers cannot judge, so hand over the share copy once the readers' round and your fixes are done, and never a cut with a fault a reader could have caught. Show one film, alone, not in a line of others. Ask them to watch it once with the sound on, then ask one open question ("what did you make of it?") and write their words down exactly. Their notes on the sound are the only notes on the sound you will get. Fix what they name, and leave alone what they liked: never rework an approved look for a reader.

## Profile: `vd profile`
Minutes by class (making, rework, waiting, engine faults, looking) for the session that made this film, written to `~/.vd/out/NAME/profile/`. Run it when a film is done. It reads a Claude Code session log on this machine (among those changed in the last seven days under `~/.claude/projects`: the newest session that made this film folder, else the newest that names it; or the one you give with `--transcript`) and sends nothing anywhere; minutes it cannot place are printed as not classed. Another agent's log is not in that form: there, report the time from your own clock.

---

Several of the principles in WORLD.md were learned from Interface Lineage, an archive of interface designs taken apart. They are restated here in our own words.
