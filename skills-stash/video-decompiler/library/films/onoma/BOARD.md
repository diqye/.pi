# Onoma: the board

A launch film for a made-up AI app that makes sound from a typed line, in moving type: one word at a time on a dark ground, each word turning into the thing it names. Written before the code, 12 November 2026. **This page describes the second cut: the board as it was written, with the three changes made after the first cut at its end. The accepted fourth cut kept every beat and changed how things arrive:** "rain." leaves a speck at a time, each at its own speed; "thunder." is blown outward off the bolt and gone, and a shock runs out along the line; each word has finished typing before it comes apart, and is typed where the camera already is; the request is typed with the whole prompt bar in frame while the camera pushes in (it no longer rides the caret); the clap's specks gather into a column that the spike takes over; each sound named in the request is underlined in its track's colour; the mix is framed closer, with one slow push; the file chip holds the finished sound's shape, playing; and the line under the name is "Type a sound. Hear it." both times (the end had said "Say it. Hear it."). `README.md` says what readers changed on the way.

## What the film is held against

Its idea comes from Bloom's film "From a single line": one word at a time on a dark ground, each word turning into the thing it names. Its making is held against Hightouch's "Styles" film, which blind readers had ranked highest of the four films they read that day: so the film keeps one system for every word (rule 6) and gives the product the frame (rule 3).

## One sentence

"You type a sound in words and it makes it; type a few and they play together."

## The product (made up)

**Onoma** turns a typed line into sound: weather, footsteps, a clap, a pulse, a tune. Everything it makes shares one tempo, so the sounds you ask for become a rhythm, and it exports the mix. The name is the root of "onomatopoeia": a word that sounds like the thing.

## The one idea

The film's soundtrack is the product's output. Each word typed on screen is heard as the sound it names, at the moment it turns into the picture of that sound. Then the same sounds are asked for in one line and play together as a beat: the demo is the music.

## What a viewer of this kind expects, all kept

A hook in two seconds · the trick shown before it is explained · the name · the real interface with a real request typed into it · the output · how you take it away · the name again.

## The world (written after the film, for this form)

- **Its line.** A typed word comes apart into the sound it names, and every sound is a shape on one line of light.
- **The name, the mark and the claim.** "Onoma" is the root of "onomatopoeia", a word that sounds like the thing. The mark is the name with the line under it, and its five letters are said as the film's five sounds. The claim: "Type a sound. Hear it."
- **What this kind usually looks like, and what it leaves.** A film of moving type gives each word its own effect. This one leaves that: every word becomes specks of the same light, and every sound a shape on the same line.
- **What it is made of.** Type (Geist 500 for the words, Geist 600 for the name, Geist Mono in the prompt bar), specks of warm white light, the line, one glass prompt bar, and the air: a dark ground whose soft colour is the sound being made (blue-grey rain, white-violet thunder, amber steps, teal echo, red heartbeat, black for the hush, warm for the name). No pictures.
- **The moves it is built on** (the skill's WORLD.md): the word does what it says (each word comes apart into its sound); one thing carries through (the line); the proof is the film (the soundtrack is what the product makes); the silence before the name (the hush).

## The cast

| Thing | Made of | Its one job |
|---|---|---|
| **The line** (conserved, from the rain to the last frame) | a thin line of light with a soft glow and its reflection | Sound. Every word falls into it and it takes that sound's shape. It is the ground the rain lands on, the path the bolt and the steps take, the pulse, the point the hush leaves, the underline of the name, the edge of the prompt bar and every track of the mix. |
| **A word** | large type; then the same letters as a few thousand specks of light | The request. When its full stop lands it comes apart into the thing it names. |
| **The air** | a dark ground with soft colour moving in it (`kit/field.tsx`) | The room the sound is in: blue-grey for rain, a white-violet flash for thunder, amber for steps, teal for the echo, red for the heartbeat, black for the hush, warm for the name. One family at a time. |
| **The prompt bar** | glass, rounded, with a caret | Onoma's interface. It grows out of the name's underline. |
| **The tracks** | one line a sound, each drawn from that sound's own samples | The proof. The shapes on screen are the audio you are hearing (`kit/waves.gen.ts`, written by `sound.py`). |

One accent: the line's own warm white. Type: Geist 500 for the words; Geist Mono in the prompt bar.

## The clock

120 beats a minute, 60 frames a second: a beat is 30 frames, a bar is 2 s. Every sound starts on a beat. 58 beats = 29 s. Every event's beat is a name in `sound.py`'s table `T`, which writes `kit/times.gen.ts` for the picture to import.

## The beats

| Beats (s) | Part | Typed | Picture: what moves, what caused it, what it carries into |
|---|---|---|---|
| 0-4 (0-2) | RAIN | "rain." | The word types; on its full stop the letters loosen into drops and fall, with more rain across the whole frame. Where the drops land they make **the line**. |
| 4-8 (2-4) | THUNDER | "thunder." | Typed upper left. A bolt cracks up from the line through the word; the frame flashes; the word is blown apart and what is left of it rolls along the line as the rumble. |
| 8-12 (4-6) | FOOTSTEPS | "footsteps." | Typed low. A quarter of the word drops on each beat: four steps that dent the line, left to right. The camera walks with them. |
| 12-16 (6-8) | CLAP | "a clap, with echo." | The word snaps into one tall spike on the line and a ring opens from it; the spike comes back three times, smaller each time, further along. |
| 16-20 (8-10) | HEARTBEAT | "a heartbeat." | The camera goes close on the line. It beats: two pulses, a second apart, travelling. The air beats with it. |
| 20-24 (10-12) | HUSH | "hush." | Typed small. Everything on the line dies down, the air goes dark, and the line draws in from both ends to a single point. **The one silence.** |
| 24-30 (12-15) | NAME | "onoma" · "Type a sound. Hear it." | The point stretches into a short line; the name sets above it, the line plays one soft wave under it. The first chord. |
| 30-34 (15-17) | ASK | `rain, footsteps, a clap with echo, a heartbeat · 120 bpm` | The underline lifts into the prompt bar, large. The request types. |
| 34-42 (17-21) | THE MIX | none | Return. Four lines unfold under the bar, each the true shape of its sound, and a playhead crosses them while all four play together: the sounds of the first twelve seconds, now a beat. The camera goes in to the tracks. |
| 42-48 (21-24) | ONE MORE | `+ a music box` | A fifth line: a tune on top. |
| 48-52 (24-26) | TAKE IT | "One line in. A finished sound out." | The five lines fold into one and a file drops from it: `storm-walk.wav · 0:08`. |
| 52-58 (26-29) | END | "onoma" · "Say it. Hear it." | The line is the name's underline again. One last heartbeat on it. |

## How each part hands to the next (written after the film, for this form)

The beats above say what moves; this says what each boundary is, by the kinds in the skill's WORLD.md.

| from | to | kind | what crosses |
|---|---|---|---|
| RAIN | THUNDER | carried | The line the rain made stays; "thunder." starts typing over the rain's last beat, and the bolt cracks up out of the line. The air turns violet into the bolt. |
| THUNDER | FOOTSTEPS | carried | The rumble rolls out along the line; "footsteps." is typed over its tail, and its letters drop into the same line. |
| FOOTSTEPS | CLAP | carried | The line and the camera: it moves on from the last step to where the clap is typed. |
| CLAP | HEARTBEAT | becomes | "a heartbeat." pours into the line at the point where the pulse starts. |
| HEARTBEAT | HUSH | carried | The line stills, the air goes dark, and the line draws in to a point. |
| HUSH | NAME | becomes | The point stretches into the name's underline. |
| NAME | ASK | becomes | The underline lifts into the lower edge of the prompt bar. |
| ASK | THE MIX | becomes | Return is pressed; the tracks and the playhead unfold out of the bar's edge. |
| THE MIX | ONE MORE | carried | The bar and the tracks stay; a fifth track opens under them. |
| ONE MORE | TAKE IT | becomes | The five tracks fold into one line, which goes on playing. |
| TAKE IT | END | becomes | The one line comes down and is the name's underline again. |

## The turn (written after the film, for this form)

Beat 24 (12.0 s), straight after the hush's silence. Before it: single words, each heard alone over a breath of air and a low drone, and the air changes colour for each. After it: the name, the first chord, the product's interface, and the same sounds asked for in one line and playing together on one grid.

## Ties

| What | First | Returns | What the return means |
|---|---|---|---|
| The line | made by the rain | in every scene, and under the name | Everything you type becomes this. |
| Each sound | alone, as its word | together in the mix | They were parts all along. |
| The heartbeat | beat 17 | in the mix; last thing in the film | It is alive. |
| The full stop | ends "rain." and starts the rain | every word; the hush leaves one point | The moment a request is sent. |

## Gifts (written after the film, for this form)

- **The name is said in the film's five sounds** (beats 24 to 26, again 52.5 to 54.5): each of its five letters lands on a half beat with one note, and under it the sound that letter stands for (rain, thunder, a footstep, a clap, a heartbeat), in that sound's colour and with that sound's shape on the underline. The music box's tune opens on the same first four notes and reaches the fifth.
- **The tracks are the sounds' own shapes** (beats 34 to 52): each track, and the one line they fold into, is drawn from the samples `sound.py` made, so what is seen is what is heard.
- **The file is playing** (beats 49.5 to 52): the chip holds the finished sound's shape, lit as far as the playhead has reached, and its bars pulse on every beat.

## Framings (none for more than a third)

Type as the picture, large (each word as it types) · wide, the whole frame of weather · a diagonal (the bolt) · a travelling shot (the steps) · depth (the echo's rings) · very close on the line (the heartbeat) · a point in the dark (the hush) · the name, centre · the interface at full frame · inside the tracks · the name.

## Rules of this film

1. A move takes 10 to 20 frames and decelerates into place; the camera eases in and out and carries its creep. Only a hit (the bolt, the clap) is instant, and it is heard.
2. A thing is carried across every change: the word becomes the specks, the specks become the line's shape, the line becomes the next scene's ground. Nothing is swapped.
3. The proof gets the frame: the prompt bar at 60 % of the width, the tracks at full width when they play.
4. Several things move at once: the air, the reflection, the line and the camera each at their own speed.
5. No hold without a reason. The one long stillness is the hush, and it is silent on purpose.
6. One system: everything is the line and specks of the same light. No second effect per word.
7. What is drawn is what is heard: each track's shape is computed from its samples.
8. No built 3D. Depth is the reflection under the line, the air behind, glass, and the camera.

## Hardest shot

Beats 0 to 4: a word comes apart into rain and the rain makes the line. If that reads, the film's device is established in two seconds. Prove it first.

## Three to six seconds that stand alone (for the teaser)

0 to 4 s: rain, then thunder.

## Sound

Every sound is made in `sound.py` from noise and sines: rain, thunder, four footsteps, a clap with three echoes, a heartbeat, a hush, a music box, one chord. In the mix the same sounds are placed on a grid at 120 beats a minute: steps on the beats, the clap on two and four with its echo, the heartbeat under them, rain as the top. No samples, no paid service.

## Sources and licences

Geist and Geist Mono (Vercel), SIL Open Font License 1.1: embedded in `kit/fonts.gen.ts`, with `media/fonts/Geist-VF.ttf` for `tools/glyphs.py` and the licence texts in `media/fonts/`. Everything else is drawn or synthesised in code. The product is invented.

## What changed after the first cut (12 November)

The board above was written before any code. Three things moved once the film could be watched:

- **The name is said, not shown.** "onoma" has five letters and the film has five sounds. Each letter lands on its own half beat (24, 24.5, 25, 25.5, 26) with one note of a rising figure, the sound it stands for, that sound's colour under it and that sound's shape on the underline: rain, thunder, a footstep, a clap, a heartbeat. The music box's tune opens on the same first four notes, and the name is said again the same way at 52.5 to 54.5. It replaces a three-second hold on the name, which measured as still.
- **The request is typed in close-up.** The camera sits tight on the prompt bar and rides the caret across it (beats 30 to 34), then pulls back as the tracks open. Typing in a small box in a wide frame measured as still for 1.6 s. (The accepted cut keeps the whole bar in frame and pushes in on it instead: see the top of this page.)
- **"A finished sound out" is shown.** At 48 the five tracks fold into the one line and it goes on playing to 52: the same bar, drawn as the sum of the five, with the playhead still crossing it and the file chip's dot keeping the beat. Before, the sound stopped at 48 and the claim sat over a still line: a second silence the board had ruled out.
