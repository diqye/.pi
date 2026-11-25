---
name: video-decompiler
description: "Make a short product film (a launch film, a demo, a brand film) as raea code, from a brief or from a film you were handed (\"make me one like this\"). Take a good film of the kind apart, write your own board on its shape, build it on one clock with its sound, have it read blind, and then show a person. Use when someone asks for a film about their product or idea. Not for cutting recorded footage (interviews, podcasts, tutorials, captions, sound for a finished picture): that is legible-film's."
metadata:
  raea-tested-against: 0.1.7
  raea-verbs: render
version: 0.1.9
---

# Video Decompiler

Every film here is made one way: **take a good film of its kind apart, write your own board on its shape, and build the board.** The good film is one you were handed, or one the person admires, or one of the worked films in `library/films/`. A **board** is the whole film on one page before any code (BOARD.md). raea is the medium: a page of type, cards, interface and pictures under a camera, drawn from code one frame at a time.

This is the method four films a person accepted were made by, written down and tightened after them. The steps, the rules and the readers' briefs come from their record, and each worked film's README says what its own history was: which cut its readers saw, and what was written afterwards.

All commands are `python SKILL_FOLDER/tools/vd.py ...`, run in the film folder (or from anywhere with `--film DIR`). `python` here, and wherever a page says `python sound.py`, is the Python of the environment this skill was set up with (step 0), never the system's. Run each in the foreground, and check that the file it names exists before you go on. Each says what it wrote and how long it took. What they render goes to `~/.vd/out/NAME`, outside the film folder, and what readers are given goes to `~/.vd/reads`; what `vd pin`, `vd measure` and `vd pack` measured of a film is kept under `~/.vd/measures`, so a second call on the same file is quick; `vd new` writes the film folder itself, and `vd pin` writes its targets into `score.json`. Where a command takes a finished film (`vd scan`, `vd pack`, `vd measure`), give the file's full path, which `vd export` prints: `~/.vd/out/NAME/NAME.mp4`, and an earlier cut is `~/.vd/out/NAME/cuts/NAME-cutN.mp4`.

**Not this skill:** a film cut from recorded footage (an interview, a podcast, a tutorial, a talking head), its captions, or sound for a picture that is already finished. Hand the person to [legible-film](https://github.com/JamesDimachkie/legible-film), a separate skill made for that. This one can still make the parts of such a film that are drawn in code (a title, a bumper, an animated insert); its export is an ordinary video file that legible-film or an editor can cut in.

## The steps

0. **Set up once, and `vd doctor` passes.** The skill runs in a Python environment of its own, `~/.venvs/video-decompiler`, outside the skill's folder. If it is not there, make it and install `SKILL_FOLDER/requirements.txt` into it (`python3 -m venv ~/.venvs/video-decompiler`, then `~/.venvs/video-decompiler/bin/python -m pip install -r SKILL_FOLDER/requirements.txt`; on Windows, `py -m venv` and `Scripts\python.exe` where those say `python3 -m venv` and `bin/python`. The repository's README has both in full under "Start"). Then run `vd doctor` with that Python: it says what is missing and the line that fixes it.

1. **Start from a worked film.** `vd new NAME --like plusone` for a product a person uses (one task done in order, with real pictures and people). `vd new NAME --like stet` for a technical product (a problem shown, the mechanism, a proof, how to start). `vd new NAME --like onoma` for moving type, when the product works on words or sound (each typed word comes apart into the thing it names, then the product is shown making them all from one line). `vd new NAME --like linden` for a brand film built on real still pictures (one continuous camera move outward through nested worlds, no cut). Read the copy's `README.md` and `BOARD.md` whole, then `vd look` it, before changing a line: it is a film a person accepted, and its kit, camera and clock are what you keep.
   *Done when the copy draws and you can say what each of its files is for.*

2. **Hold it against one good film of its kind.** Use the film you were handed, or ask the person for one they admire of this kind. Take it apart by TAKE-APART.md, which ends with its dossier in `REFERENCE.md`. With no film to be had, hold yours against the worked film you started from: make an untouched copy beside your film folder with `vd new NAME-anchor --like FILM` (NAME is your film's name, FILM the one you started from; outputs go by a folder's name, so give every film folder on a machine its own), then run `vd export` in it, which takes a few minutes. Use that file wherever a step says REF or asks for a worked film.
   *Done when `REFERENCE.md` is written, or you have said in the board that the worked film stands in.*

3. **Find the film's world and write your board.** Read WORLD.md first: a clean film with no world reads as a competent freelancer's, and the world is what the accepted films had. Then write `BOARD.md` in the film folder, by the form in the skill's BOARD.md. Replace the worked film's board; keep nothing of its subject.
   *Done when every heading of the form is filled and every check at its end passes but the first, which needs the sheet that step 4 makes. No film code before this.*

4. **Gather the real material the board names**, before building: the product's own screens, marks and pictures first; then public-domain or licensed pictures that have a job in the story (a museum's open-access collection for art; for photographs of ordinary things, such as food, Wikimedia Commons and Openverse can be searched by licence, and two test films each found ten CC0 photographs of food that way). Cut each to the size it is shown at, put it in `media/`, and write its source and licence down. Then lay the pictures, the colours, the faces of type and the mark out as one picture, the film's world on one sheet, and look at it before you build (WORLD.md, "Lay it out before building"). In the film that was liked best, real pictures gathered at this point changed what the film was.
   *Done when every picture the board names is in `media/` with its source line (or the board says the film uses none), the sheet is made and looked at, and the board's first check passes on it.*

5. **Sound first, on one clock.** In `sound.py`, write the table of events (every beat the picture needs, by name) and the music: a chord a bar, one pattern, a tune, the events played inside it. Run it (`python sound.py`; `vd new` ran it once already). It writes `media/sound.wav` and `kit/times.gen.ts`; the picture imports its beats from that file and from nowhere else.
   *Done when every row of the board's beat table has a named time, and `vd sound` prints `sound passes` and says sync was checked against the named events. If it says sync was not checked, the film has no named events yet: write them. (Started from `linden`, the level line fails until your own film's sound sets its level: that film is kept at the level it was accepted at, and its README says so.)*

6. **The hardest shot first.** Build the shot your board names as hardest, alone, with its real pictures in place. `vd look --at T` (one moment draws at the film's own size, up to 1920 px wide).
   *Done when you would publish those frames.*

7. **The whole film.** Replace the worked film's acts with yours, beat by beat from the board. `vd look --at T1,T2,...` after every change (several moments, one call). Then `vd export` (it carries the film's own `media/sound.wav`; each export is kept as `~/.vd/out/NAME/cuts/NAME-cutN.mp4`, and `NAME.mp4` is the latest; beside it are a share copy, `NAME-share.mp4`, and sheets of the whole film at four frames a second, `NAME-sheet_000.jpg` on, the quickest way to read the cut you just made).
   The first export is the first cut, not the film. The accepted films took several cuts to reach their readers: after each export, read the SCAN (pops, holds, level and flashes), make the story sheets (`vd pack FILM`) and read your own film on them as a stranger would, fix what you find, and export again. On the first cut, `vd measure FILM --against REF` lists up to forty gaps between your film and the one it is held against, the kinds that matter most first; each is a question for the frames, not an order. Keep a table in `NOTES.md`, a row a cut: what changed, and the scan's numbers. Every cut stays under `cuts/`; hold one against an earlier one with `vd pack ~/.vd/out/NAME/NAME.mp4 --against ~/.vd/out/NAME/cuts/NAME-cut1.mp4`.
   *Done when a cut's SCAN has every `fix before anyone watches` line either fixed or written down as a hit you meant, every `check` line answered, and a reading of your own story sheets finds nothing you would fix first.*

8. **Readers, one round** (EYES.md has the briefs, word for word). `vd pack` your film beside the film it is held against and the worked film you started from, exported (the anchor of step 2 if you made it; otherwise `vd new NAME-anchor --like FILM` beside your film folder, then `vd export` in it: a few minutes, once). Two readers, from different models, each read the blind line-up; one fault-finder reads your film alone, every frame of its ten busiest seconds. Write every reading in `READINGS.md`. If you cannot start other agents, there is no blind round: read your own sheets as a stranger would, and tell the person plainly that no reader has read the film.
   *Done when all three readings are written down. With no reader to start: when that is written in `READINGS.md` with your own reading of the sheets; then go to step 10.*

9. **Fix what they found, story first.** An action that does not read, a step that is missing, a claim that is said and never shown: these come before words cut by the frame or too small, and those before pops, swaps and dead holds. Export again, and give the new cut to a new fault-finder alone, once, with the same brief: hold its list against the first one's to see whether each fault is gone. A small fault it still finds you may fix without another reading; a device that has now failed twice goes (EYES.md). The film does not go round again.
   *Done when every story or words fault that reading finds is fixed, or the device causing it is cut. Say in the report which cut readers last read. Report what the line-up readers said about who made each film, and where they ranked yours against the worked film: it is a judgement to weigh, not a score to chase. If both called yours a beginner's or a hobbyist's, say so plainly, and question the film's world (WORLD.md) before you rebuild its finish: when the faults they named survive a repair, look to the premise before the polish.*

10. **Then the person.** They are the judge: readers find faults, they do not decide. Their time is for what you and the readers cannot judge (the sound, how it feels at speed, whether it is good), so hand over the share copy only now, one film, to watch alone with the sound on. Fix what they name and leave alone what they liked.
   *Done when the person accepts it. With no person to ask, say in the report that nobody has watched it.*

11. **Report.** How long it took (`vd profile` in Claude Code; your own clock in another agent). What the readers found and what you changed. Who watched it with sound, and their words. The weakest two seconds. Every picture's source and licence.

One film at a time: finish one, with its sound, before starting another.

## What every film owes

The rules the accepted films were built to. Each is in their boards.

- **Board first.** Every shot has a reason in the one before and sets up the one after.
- **Be the obvious choice for its kind, then add a point of view.** Keep everything a viewer of this kind of film expects: for a launch, the trouble in their own words first, the name, the product doing its job in pieces of its real interface, proofs, how to start.
- **One thing is carried through the film, and every change of scene is decided:** the thing becomes the next thing, or is carried, or is matched, or goes through a door, or the whole ground changes on the music (WORLD.md, "Every change of scene means something"). Nothing is swapped for want of a decision.
- **The proof of each claim gets the frame.**
- **Moves a viewer can watch:** a sixth to a third of a second (10 to 20 frames at 60 a second), decelerating into place. The camera eases in and out. A thing at rest eases in before it leaves. Only a hit is instant.
- **Several things move at once, and no hold where nothing moves for a reason.** A rest you chose is not a fault: it has a reason in the story, and one small thing in it stays alive. Do not keep things drifting only to look busy.
- **No framing for more than a third of the film.** A framing is where the camera sits: going close on the part that changes is a new one, in the same room.
- **The product is shown large, a piece at a time.** No worked film shows a whole app small in a wide frame. Plus One keeps the made thing in the middle of the frame, large, lets the interface shrink to a pointer and a few buttons, and goes close on a phone when the phone is the point. Stet shows panels of its interface, each filling the frame, and puts the camera on the row that changes. Onoma types its one request into a prompt bar nearly as wide as the frame, then goes in on the tracks while they play. When two panels must be seen together, hold them wide only for as long as it takes to see that there are two. A panel nobody is reading may be cut by the frame; a word being read and a control being pressed may not.
- **The ground has a character and a job.** Soft moving colour that answers what is happening, never a default flat field.
- **Music first, events inside it.** A chord a bar, a pattern, a tune. Finish at -15 LUFS, true peak under -1 dB.
- **Type, cards, interface and real pictures, as designed layers.** No rooms, terrain or rigs modelled in code. A real picture has a job in the story, and its source and licence are written down in the film's `media/` (as in `library/films/plusone/media/art/SOURCES.md`).
- **Words can be read.** Text that carries the story is 30 px or more at 1080p at the size it is shown on screen, after any camera scale (`vd look` names text set under 30 px by its own size, before the camera, so read the tiles for text a camera shrinks), a control is never cut by the frame, and a word has finished arriving 12 frames before anything happens to it. A word is typed where the camera already is.
- **Every fact on screen is true in every frame**, and every number is the count of what is drawn.
- **About 30 to 40 seconds** for a launch, a demo or a brand film. The accepted ones run 29 to 38.

## What this is proven for, and what is experimental

**Proven** (a person accepted films made this way): a product demo, a launch film for a technical product, moving type, a brand film built on real still pictures. All are type, cards, interface and pictures cut to music.

**Experimental** (it renders; no film of the kind has been accepted): lit 3D scenes (no starter ships for one; `library/recipes` holds 3D compositions that rendered, to copy from, and TECHNIQUES.md says what each costs), scenery drawn in code, real moving footage, generated pictures, a film under ten seconds. Build one only with a test first, and say in the report that it is unproven.

**Newer commands, not proven on a film.** These came after the four films and no accepted film was made through them, so none is a step above. Use one when the person asks for what it makes, say in the report that it is unproven, and check its output as you would a stranger's:
- `vd audio TRACK --clean-voice` cleans a recorded voice and refuses any step that costs the speech more than 3 dB (TECHNIQUES.md, "A recorded voice"). `--sheet` draws the track's sound as one picture. `--tempo-map` makes a music track the film's beat: it records the track in `score.json`'s `music` with the nearest whole frames a beat, and writes the track stretched to that beat (at most 3%) and placed so its first beat, or its drop with `--drop-at-beat N`, falls on a beat. Then run the film's `sound.py`, which takes its beat from it, so every event the picture shows moves onto the track's tempo; `vd sound` and `vd export` lay the track under the film's own mix, or in its place with `--replace-own-mix`, and stop if `sound.py` has not run since (a `--kind` starter has no `sound.py` and keeps its scenes in seconds: the track is mixed in, and the command says the beat's length so you can put the scenes' edges on it). A worked film's length in beats stays, so its length in seconds follows the track. A track whose beat is weak is refused unless you give its tempo with `--bpm` (a weak grid fits white noise too); where the tempo could be read at half or double, it takes the octave nearest the film's own beat and says so. A film's grid is one steady tempo, so it measures how far the track's beat slides from that grid, stretch by stretch (16 beats each), and refuses a track whose beat slides more than 40 ms, giving the number and each stretch's tempo and offset; it does not follow a changing tempo. The measure is a floor: a 1906 band record a listener heard speed up read 34 ms over its first 28 s, under the line, so still listen. `--bpm` takes 60 to 200 BPM; a tempo outside that is refused with its half or double to give instead.
- `vd bridge` writes the export's cuts for an editor or for legible-film, bound to that exact file (TECHNIQUES.md, "Handing a film to an editor"). It needs `vd export` first. Its Final Cut Pro 7 file and its OpenTimelineIO file place the picture and its sound alike, the host's in-point as a gap before them, and name the sound the file has (none for a silent one). legible-film's own readers read the cue list as fresh and its sound spotting takes it; no editing program has opened either timeline, so check them in the program before trusting them.
- `vd borrow REF` fits the reference's moves and colours into `dna.json` and `kit/dna.gen.ts`, beside what `vd pin` gives (EYES.md, "Measure"). Run `vd pin` too: `vd measure` reads pin's numbers, not borrow's.
- `vd capture` puts a repository's counts, or a real command's output lines with their times, into `kit/puppet.gen.ts` and a plane, `kit/PuppetPlane.tsx`, that your film must import itself. `vd launch REPO` copies `stet`, captures into it, writes the facts to `REPO-FACTS.md` for your board, and puts the plane in the film for four seconds from Stet's NUMBERS cue, on Stet's own paper: a start, to move where the board puts it.
- `vd foley` makes a track from moves it reads in the film's code, by rule, not by measuring the drawn picture; nothing plays it unless you mix it. `--mix` writes it into `media/sound.wav`, which `sound.py` owns: the next run of `sound.py` drops it, and a second `--mix` adds it twice. It adds the track 9.5 dB under that mix and moves the whole toward -15 LUFS by at most 6 dB with its true peak at -2.2 dBTP, and says the level it wrote (a quiet mix ends short of -15). Under a track mapped with `vd audio --tempo-map`, the level of the film's own mix, foley and all, is `score.json`'s `sound_file_gain`, in dB (0 when absent). The trace it reads the moves into is `~/.vd/out/NAME/telemetry.gen.json`, outside the film.
- `vd evolve NAME` packs four world sketches as a blind line-up. Without `--render` each sketch is a fixed drawing per worked film with your subject's name on it, not a design of yours; with it, the worked films are drawn untouched. Letters are dealt at random and the key file records them (`--seed` fixes them for a test); Each tournament's sketches are its own, under `~/.vd/out/NAME/tournaments/tN`, so running it again leaves earlier ones as they were. `--select` needs the letter chosen, promotes a sketch only as its readers saw it (one changed since is refused), keeps what `vd pin` and `vd borrow` saved in `score.json`, and makes the film folder the chosen sketch's film: what was in it is moved to `~/.vd/out/NAME/before-select-N`, not deleted. `--readings` picks by summed reader rank: readers rank sparse sketches higher (EYES.md, "Readers"), so the person picks the world, not the count.
- `vd playable` builds a browser page that imitates the film for scrubbing, the whole frame scaled to the window, with the sound the export lays under the picture. It is not the film: raea does not draw it, and parts of the kit (`Freeze` in `kit/lib/finish.tsx`, 3D) do not build.

## Where to read more

| When | Read |
|---|---|
| Finding the film's world: its subject, its picture board, what each change means, its moments of wonder | WORLD.md |
| Writing the board | BOARD.md |
| Taking a film apart | TAKE-APART.md |
| Choosing how a beat is drawn; what the kit holds | TECHNIQUES.md |
| A frame looks wrong, or raea refuses | TRAPS.md |
| Looking, the scan, measuring, the readers' briefs, the person | EYES.md |

## The commands

| Command | Does |
|---|---|
| `vd doctor` | is this machine ready, and the one line to fix it if not |
| `vd new NAME --like FILM` | a film folder that is a copy of a worked film (`vd new --help` lists them; `--kind` gives the older starters) |
| `vd pin REF.mp4` | a film's numbers, its story and move sheets, and moments at its own size (up to 1920 px wide) |
| `vd look --at T1,T2` | moments as one picture, with what did not draw |
| `vd sound` | the sound's own check, with no picture |
| `vd render --from A --to B` | a stretch of the picture again, spliced into the picture `vd export` last drew (the film itself is as it was until the next `vd export`) |
| `vd export` | the finished film and its share copy, then the scan (`--again` draws it afresh). Exit code 3 means the film was made and could not be scanned |
| `vd scan FILM.mp4` | pops, holds and level of any finished film |
| `vd pack FILM --against REF` | what readers read: a blind line-up, and your film alone |
| `vd measure FILM --against REF` | up to forty gaps between two films, the kinds that matter most first |
| `vd profile` | where the time went (it reads a Claude Code session log) |
| `vd clean` | what can go from `~/.vd/out` (the drawn pictures and part records an export makes again), and with `--yes` removes it; cuts stay unless `vd clean NAME --keep-cuts N` (one film's folder; `--keep CUT` protects one); `--orphans` names folders whose film folder is not there and never removes them |
| `vd audio TRACK` | not proven: clean a voice (`--clean-voice`), draw a track's sound (`--sheet`), make a music track the film's beat (`--tempo-map`) |
| `vd bridge` | not proven: the export's cuts for an editor (`cues.json`, Final Cut Pro 7 XML, OpenTimelineIO), bound to the exported file |
| `vd borrow REF` | not proven: a reference's fitted moves and colours (`dna.json`, `kit/dna.gen.ts`) |
| `vd capture`, `vd launch REPO` | not proven: a repository's counts or a command's output, as a plane your film imports |
| `vd foley` | not proven: a sound track made by rule from the moves in the film's code |
| `vd evolve NAME` | not proven: four world sketches as a blind line-up |
| `vd playable` | not proven: a browser page that imitates the film, for scrubbing |
| `python SKILL_FOLDER/tools/metrics.py SANS-VF.ttf MONO-VF.ttf` | a worked film's table of letter widths (`kit/metrics.gen.ts`), made again when you change its faces of type; both must be variable fonts with a weight axis |

One raea job runs at a time on a machine; `vd` waits its turn and says so. Look often and export rarely.
