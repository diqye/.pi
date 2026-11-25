# Take a film apart

Every film is held against one good film of its kind. This is how that film is read, in the form used before the
accepted films were made. You take its **shape** and leave everything that is its own. The result is its dossier,
`REFERENCE.md`, in your film folder.

A dossier is evidence first. Keep four things apart: what you saw in frames, what a tool measured, what the maker
said, and what is your own reading. Give times.

## The steps

1. **Pin it.** `vd pin REF.mp4` (add `--no-voice` for a film with music and no voice: the measure otherwise hears
   words in the music; with no transcriber on the machine its word measures are left out, and `vd pin` says so). If you
   do not know whether it has a voice, pin it once and read the words it heard: stock phrases that say nothing about
   the product are music misheard, so pin again with `--no-voice`. It writes the film's numbers into `score.json` as `targets` and prints the paths of what it
   wrote under `~/.vd/out/NAME/pin/`: the story (the whole film at two frames a second, the time on each tile), the
   moves (every frame of its five busiest seconds) and six moments at the film's own size (up to 1920 px wide; a wider film's are reduced, so allow for that), for reading small type.
   *Done when you have opened every picture it printed.*

2. **Find out who made it and what they said.** The post or page it came from: its maker, its credits, the maker's
   own words, quoted exactly. Whoever posted a film is often not its maker: say which you know. Search the web for
   it when you can (its title, or a line of its text, usually finds the post); if you cannot, write "not known" and
   ask the person.

3. **Write the dossier** in `REFERENCE.md`, under these headings:

   ```
   # TITLE (maker, year)
   > The claim: one sentence, checkable against the film, saying what it does that makes it hold.
   Post: link · length · size and rate · sound · credits as stated · the maker's words, quoted
   Kind: what a shop would file it under, and what it borrows from other kinds
   Evidence: which sheets were read, at what rate; what was not seen or heard
   ```
   - **Spine.** A text diagram of the film on a time ruler: its parts, its grounds, and its ties drawn across.
   - **The world.** What everything on screen is made of, and why that material belongs to the subject. Its rules:
     ground, light, colour, type, what moves and how, what never appears. The ground's job.
   - **The formal idea.** The one move the whole film is built on.
   - **Ties.** Each one: what it is, where it first appears, where it returns, what the return means.
   - **Hand-overs.** A row for every boundary between two moments, with its time: what carries the eye across (a
     thing that becomes the next thing, a thing that stays, a matched cut, a change of ground, a plain cut).
   - **Dynamics.** Where it builds, peaks and rests, in the picture and in the loudness, and whether they move together.
   - **Flat notes.** Every moment where the film drops, with the time and what a viewer would notice. A film you were
     handed is not good in every second: find where it is weak. "None found" is an answer, and a rare one.
   - **Gifts.** Details nobody asked for: the small departures and moments of wonder, with times.
   - **Words, picture, sound.** What the words carry that the picture does not, and the other way; where a word lands
     on an event in the picture; where the loud moments fall against the cuts (measured, not heard: say so).
   - **Keeps and breaks.** The conventions of its kind that it keeps. The one it breaks, and what the break buys.
   - **Hardest shot.** The stretch that would cost the most to make.
   - **Moves.** How a thing arrives, from the move sheets: how many frames, whether it slows into place.
   - **Measured.** The numbers `vd pin` gave. They describe a film. They do not grade it.
   - **Not known.** What you could not see, hear or find out.
   *Done when every second of the film is on the spine, and Flat notes and Gifts each have an answer.*

4. **Say what you take and what stays theirs**, at the end of `REFERENCE.md`. Take its shape: the order of its
   parts, its formal idea, its hand-overs, its pace, how its words arrive, the job its ground does. Leave its flat
   notes behind. What stays theirs: its subject, its words, its pictures, its marks, its characters, its music.
   *Done when a person who saw both films would say "the same kind of film" and never "a copy".*

5. **Write your own board** (SKILL.md, step 3) against it. Where your product has no honest answer to one of its
   parts, cut the part. A handed film may break one of the rules in "What every film owes" (no words, a different
   length). Keep the rule unless breaking it is what makes the handed film what it is, and say in your report which
   way you went and why.

If the film is carried by something you do not have (footage, a shoot, a rendered world, characters), tell the person
before building: say what you cannot match, and offer the nearest film that type, cards and interface can carry.

## What a reading of sheets cannot give you

How it feels at speed, and anything about its sound beyond the measures. Ask the person who handed it to you what they
like in it and what they do not: one sentence from them is worth more than the sheets.
