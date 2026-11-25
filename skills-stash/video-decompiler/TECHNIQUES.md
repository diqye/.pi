# Techniques

The palette: what has been proven to draw well in raea 0.1.1-rc4. With raea 0.1.2, the release of the day this was published, the four worked films draw the same: 24 moments on their look sheets and one busy moment of each at full size, compared pixel for pixel on Windows, with no pixel different. Its look report names more texts at the frame's edge than rc4's did. Timings are from one Windows laptop with an 8 GB RTX 4070; nothing here has been timed on a Mac. Read this when you choose how a beat is made. Every `.tsx` in `library/recipes/` is a composition that rendered here (`screen-art.tsx` is a helper for `screen-layer.tsx`, and `weight-cut9.tsx` needs textures that are not shipped). Copy a recipe into the film folder, since raea refuses imports from outside the entry's folder; `screen-art.tsx` imports the embedded faces from `../lib/faces`, so copy `library/lib/faces.ts` too and point that import at where you put it (`./kit/lib/faces` in a `--kind` film). Three recipes read pictures by `staticFile` (`layers-parallax-focus`, `camera-whip-blur`, `particles-depth`); bring your own pictures for them. Costs are raea's own ms a frame for a 1080p clip, encode included, with 1 to 3 runs each.

## What the accepted films are made of

Start here. Each of these is in a film a person accepted, in `library/films/`.

| Technique | For | Recipe | ms/frame | How it fails |
|---|---|---|---|---|
| **One clock from the sound script** | every event in step with its sound through any number of cuts | `library/films/plusone/sound.py`, and every worked film's (`stet`'s keeps two clocks in one table; `onoma`'s and `stet`'s also name their one meant silence): the table `T` holds every event's beat, the script writes `kit/times.gen.ts`, the picture imports it | seconds, no render | beats typed into the picture as numbers: they drift from the sound the first time one moves |
| **Cards in depth, the far ones soft** | a row of things to choose between; depth without a 3D scene | `library/films/plusone/card.tsx`, `place` | page cost | a blur cut off at the card's edge: put the filter on a box 96 px bigger on every side |
| **A room that takes its colours from the picture** | a ground with character that belongs to what is on screen | `library/films/plusone/kit/field.tsx` | page cost | a ground that changes in one frame: give it its own slow curve |
| **A word that comes apart into what it names** | moving type where every word becomes its thing by one system | `library/films/onoma/words.tsx`, with the points inside each letter from `library/films/onoma/tools/glyphs.py` | the whole film draws at 41 to 52 ms a frame | a word that comes apart before it has finished typing: readers see it jump from half typed to whole |
| **Worlds nested in worlds, one camera** | one continuous move outward (or inward) through things that hold each other, with no cut and no 3D | `library/films/linden/levels.tsx` (`seat`, `SLOTS`, `world`) and `PATH` in `library/films/linden/film.tsx` | page cost; worlds under 26 px on screen are not drawn | a slot that sits turned: the outer world starts turned the other way and levels as the view lands |
| **A camera table over a page** | framings that change for a reason, eased, never still | `library/films/plusone/film.tsx` (and `CAM` in `library/films/stet/film.tsx`) | none | a creep that restarts at each key: carry it into the next move |

## Everything else that has been seen to draw

Much of this is lit 3D. No film built on it has been accepted yet: use it only with a test first (SKILL.md, "What this is proven for").

| Technique | For | Recipe | ms/frame | How it fails |
|---|---|---|---|---|
| **The starter kit** (words by job, drift, grain, halo, plate) | every film: words a stranger can read, no frozen frame, a finish | `library/starter/lean/base.tsx` (a `vd new --kind` page starter copies it to `kit/base.tsx`; a `--like` film has its own kit) | page cost | a beat whose words you set by hand at another size; a shot that never drifts |
| **Flat art as layers in 3D** | an illustrated world (a character, a town, a clock, big type) under a real camera, depth of field and motion blur | `screen-layer.tsx` + `screen-art.tsx` | 57-84 for two 1200x800 layers | an ImagePlane or a data-URL texture in its place drops text and freezes (TRAPS); a Screen turned away vanishes |
| **Layers, parallax, focus pull** | depth from flat cut-outs: near passes far, focus moves the eye | `layers-parallax-focus.tsx` | 27 | `alpha_mode="Blend"` layers write no depth, so DOF blurs the wrong ones: use `{ Mask: 0.5 }` |
| **Glass you see through, with bending** | a lens, a bubble, a bottle over type or a picture: the thing behind it bends | `<StandardMaterial base_color="#f4f8f6" perceptual_roughness={0.02} specular_transmission={1} ior={1.5} thickness={0.3} />` on a mesh, with what it bends behind it in the same 3D scene | 50 | a shader that only reflects reads as chrome, not glass |
| **Fast move with real blur** | a whip or spin that reads as a camera's | `camera-whip-blur.tsx` | 26 | blur a moving part over a still ground and its silhouette stays sharp: orbit the camera instead |
| **Type with thickness under a raking light** | a word or mark as a solid with shadow and contact darkening | `solid-word-light.tsx` | 21 | a clockwise outline is silently empty; `manifold.text3d` is not centred |
| **Glowing type, a flare** | emphasis | `glow-type.tsx` | 20 | the glow is flat white with no bevel or rays: it looks cheaper than studio type |
| **Particles at depth, a burst** | dust, sparks, many small things | `particles-depth.tsx` | 231 | spheres plus DOF fail; use sprites sized by the circle of confusion |
| **Grain, halo, fringe** | the finish inside a raea film | `grain-halo-fringe.tsx`; the starter's `Grain` | about 1 | a vignette on every frame makes every frame the same frame (`dark_corners`) |
| **A camera on a page (CSS planes)** | a flat layout seen as a table under a camera | `library/lib/scene.tsx` (`kit/lib/scene.tsx` in a `--kind` page film) | page cost | each plane takes room the size of its box: size planes to what they draw (TRAPS) |
| **Sunlight shaped by a window out of frame** | a room with real light: a wall you never see, with a window cut in it, throws a bright shape and shadows across what you do see | `library/recipes/weight-cut9.tsx` lines 38-69 (`SUN`, `WIN`, `SHADE`, `Room`) | not measured here | the sun must pass through the cut: aim it from the window to the subject, and give the wall shadows (`shadow_maps_enabled`) |
| **A figure as a spine of rigid blocks** | something that stoops, bows or recoils without stretching: blocks placed along a curve, so the joints open as it bends | `library/recipes/weight-cut9.tsx` lines 15-34 (`BLOCKS`, `curve`) and 77-111 (`Letter`, `It`) | not measured here | one bent mesh stretches like rubber; keep each block rigid and move only where it sits |
| **Words as lettering on a wall** | words that belong to the place, lit by its light, revealed letter by letter | `library/recipes/weight-cut9.tsx` lines 178-205 (`RichText` on the wall at z -1.58, `WALL`; each word let in by `glyph`) | not measured here | RichText faces and the "fl" pair (TRAPS) |
| **Sound from a list of notes, no picture** | a score played on sampled instruments, with one thud and one knock made in code, and the level printed every half second | `library/recipes/sound-from-notes.py`: a fixed example, one earlier film's score. Its notes and its length are lists in the script; it reads the Salamander piano from `media/sounds` and writes `sound.wav` beside itself | seconds, no render | samples stop at their range: shift at most four semitones from the nearest one |
| **A film whose clock is music** | picture and sound on one score | the notes in one JSON beside the film (`notes.json`, `[{"t": 0.0, "pitch": 60, "dur": 0.5}, ...]`); `film.tsx` imports it for what moves on each note, the sound script reads the same file, and `score.json`'s duration is the last note's end. A pattern to build, not a recipe here: `sound-from-notes.py` keeps its notes in the script | none | two copies of the notes drift apart: keep one file |
| **The library's moves** | named motions and transitions with measured timing | `kit/motions`, `kit/transitions` (named below, under what kit/ holds) | page cost | three facts in one effect read as a preset |

What raea does better than a page: real light, depth of field, per-pixel motion blur, refraction, glTF models, and thousands of copies. A single lit shot with depth of field costs about 25 ms a frame; in these tests the number of separate meshes set the cost far more than any effect did (2,000 separate meshes: 350 to 500 ms a frame; 20,000 copies as instances: 60 to 110), so draw many copies as instances. What a page does better: exact flat colour, Windows faces, CSS layout, and `backdrop-filter` frost. Combine them with the Screen: draw the page, put it in the world.

Real material, in one world. A thing drawn out of shapes where a real one exists reads as clip-art, so use real pictures: the person's own files first, then public-domain or CC0 archives (the Met, the Art Institute of Chicago and the Cleveland Museum of Art answer without a key and flag public domain in every record), with each file's source and licence written in the film's folder. But a real picture needs a job in the story and a designed place to live: a card's face, a cover, a profile picture, a thing that is chosen or sent. Photographs stood up inside scenery drawn in code read as pasted on, and the film that did it was turned down. Scenery drawn in code is not proven: type, cards and interface are.

Photographs, where paintings would be wrong (food, places, people at work): no accepted film is built on them yet. What two test films found: Wikimedia Commons has CC0 and CC BY photographs of most things; photographs by ten different people read as amateur side by side, so take few, show them large, crop them to one shape and bring them to one palette; and check each against the words beside it (a "risotto" with chicken in it was caught by a reader). A CC BY picture's credit has to be published with the film, in its post or on its last card, and not only kept in the folder.

Before you draw an interface, look at real screens of that kind of product: the product's own, or a library of real app screens if you have one (Mobbin is one). Take what such screens share (what sits on a row, how a week or a list is shown, where colour and pictures carry state) and nothing that is one brand's own. Not yet proven on an accepted film.

Then draw it at the film's size, not the device's. A phone app shown whole in a 1920 by 1080 frame puts its words near 20 px: two test films did this, and every reader called their middles small. Lay a row, a card or a list out as wide as the frame needs, as the worked films do (SKILL.md, "The product is shown large"), and show the device, if at all, once and close.

- **Planet maps that are small and known good** (found after a 404, a timeout and a 555 MB original that could not be resized):
  NASA SVS CGI Moon Kit `lroc_color_poles_1k.jpg` (svs.gsfc.nasa.gov/4720, NASA, public domain) and Wikimedia Commons
  `Land_ocean_ice_2048.jpg` (NASA Blue Marble, public domain). Take the 1k and 2k files, not the full-resolution originals.
- **The sound recipe's samples are fetched, not shipped:** `sound-from-notes.py` reads `media/sounds/salamander-piano/`,
  which `raea sounds get salamander/piano` writes (Salamander Grand Piano V2 by Alexander Holm, CC BY 3.0: credit it).
- **A count-up shows false numbers on the way.** One film's count from 0.0 to 3.8 cm showed "1.9 cm farther every year" at 3.0 s.
  The rule that every fact on screen is true in every frame applies to it: count a quantity that is true at each value
  (time passing, distance covered), or show the true number and move something else.

Not proven, so build only with a test still first: real glass in a model, grass, convincing people drawn from shapes.

## Sound

Nobody but the person can hear the film, so the sound is built from rules that held on the accepted films.

- **Music first.** One tempo, one key, a chord a bar, one pattern, a tune that comes back. Every event the picture shows is played inside it, on its grid and in its key.
- **Each sound means one thing**, and keeps that meaning: a tick is a word arriving, a pluck is a reply.
- **An opening can be struck.** One accepted film opens on single sounds out of silence, each on a change of picture, and brings the chords in with the name.
- **An acoustic instrument is a recorded one.** A piano imitated with sines was the one fault a person found in an otherwise accepted film (`linden`); on recorded samples it passed. The other three films' music is frankly electronic (plucks, bells and keys made in code) and was accepted as it is. `raea sounds` lists open sample libraries, and `library/films/linden/media/sounds` holds four with their licences (a piano, plucked strings, a vibraphone, a glockenspiel); shift a note at most four semitones from its nearest sample; credit the library. Sounds that are frankly synthetic (ticks, blips, swells) are fine made in code.
- **Make the sounds that matter audible on a phone**: presence between 1 and 5 kHz. A mix that measures well and has none reads as a flat bed at speed.
- **Give it a floor and some width.** Films made here measure thinner in the low end and narrower in stereo than the films they were held against: a bass line under the chords, and events panned where they happen on screen.
- **Rest before an arrival, and stop just before the name.**
- **Two sound tools no accepted film has used.** `vd foley` makes a track (`media/foley.wav`) by rule from moves it reads in the film's code: camera turns, a word locking into place, and a size guessed from a cue's name. Nothing is measured from the drawn picture. `vd audio TRACK --tempo-map` makes a finished music track the film's beat: `score.json`'s `music` holds its tempo and the nearest whole frames a beat a 60 fps film can hold, and the film's `sound.py` takes its beat from there, so the picture's events, its own sound and the track share one clock; the track is stretched by at most 3% to that beat and placed so its first beat or its drop lands on one. It refuses a track with no steady beat rather than guess one, a track whose beat is weak unless you give its tempo as you hear it (`--bpm`): a weak grid fits noise as well as music, and a track whose beat slides more than 40 ms from one steady grid over its length, saying by how much stretch by stretch (a floor: it does not follow a beat, and music made to a grid reads 0 to 14 ms). Where the tempo could be read at its half or double, it takes the one nearest the film's own beat and says so. With no track mapped, the four worked films' clocks and mixes are byte for byte what they were. Nobody has listened to either tool on a finished film.
- **Finish at -15 LUFS**, the wav's own true peak at -2.5 dB or lower (the export's encode lifts peaks, 2 to 3.5 dB on a bright mix; `vd export` measures the file and lowers its sound by up to 1 dB when that brings the peak under and keeps the level in range).

## Small things that removed faults

Each of these fixed a fault a reader or a scan had found on an accepted film.

- **Three cheap things end most dead holds:** everything in depth sways a little together, pictures drift inside their windows, and the camera never stops pushing.
- **Text typed into a small box in a wide frame measures as still, and reads as nothing happening.** Put the camera on it.
- **Type a word where the camera already is.** A word that starts at the frame's edge and is then centred reads as a jump.
- **Words read while the camera moves stay whole in every framing of the move.** Set the framings from the words' box.
- **A fast move with no blur reads as a strobe** to anyone who sees every frame. Draw four pictures for each frame and average three (`tools/blur.py`): every function of the frame then has to accept a fraction.
- **One continuous backing-out needs no cut and no 3D:** nested canvases under one camera, each world drawn at normal sizes and seated in the next by a scale. Draw only the worlds large enough to see.
- **A zero-length dash with a round cap draws a dot,** so a few dashed lines draw thousands of dots.
- **When the premise is "what you see is what you hear", every stretch needs a sound that is the thing drawn,** or it reads as a second silence.
- **Museums flag almost no marbled paper as public domain; printed and paste papers are flagged and are as rich.**

## Handing a film to an editor

What this skill delivers is one finished film. `vd bridge` hands its timing on: a `cues.json` (the shape legible-film reads) bound by hash to the exported file it was timed on, so a cue list read against any other file says so (the binding `picture.sha256` is the file's video stream's hash, as legible-film binds; the whole file's is `picture.file_sha256`), and its cuts as a Final Cut Pro 7 XML file and an OpenTimelineIO file, which place the picture and its sound alike (the host's in-point a gap before them) and name the sound the file has. It needs the export (`vd export` first, or `--video`). A test reads them back with legible-film's own readers when legible-film is on the machine; no editing program has opened one. Other parts an editor can work with are possible and not built into a command, so say so if you are asked for them. What was proven in pieces: `raea render --alpha` writes straight-alpha PNGs of a composition with no ground; a layer can be drawn alone only if it is a contiguous run of the film's paint order, and an effect that blends with what is under it (grain, a backdrop blur) comes out empty on its own; stems that are each limited on their own do not add back up to the mix, so hand over stems taken before the final limiter, with the finished mix beside them; a timeline file was written and read back by code, and no editing program has opened one.

## What `kit/` holds

A film started with `--like` gets that film's own kit and nothing else:

| film | its kit |
|---|---|
| `plusone` | `kit/core.tsx` (the clock, the curves, the plain parts) and `kit/field.tsx` (the room) |
| `stet` | `kit/stet.tsx` (the clock, the colours, the dot, the brackets, the pointer) and `kit/field.tsx` (the ground: soft moving colour and glass) |
| `onoma` | `kit/core.tsx` (the clock, the curves, type and glass), `kit/field.tsx` (the air and its grain), and two tables it makes: the typed words as specks (`kit/glyphs.gen.ts`, written by `tools/glyphs.py`) and the shapes of its sounds (`kit/waves.gen.ts`, written by `sound.py`) |
| `linden` | `kit/core.tsx` (the clock, the curves, the plain parts); its camera is `PATH` in `film.tsx` and its nested worlds are `SLOTS` and `world` in `levels.tsx` |

Every worked film's `sound.py` writes its clock and every event's beat to `kit/times.gen.ts`.

`vd capture` (and `vd launch`, which makes a film folder and captures into it) adds two files to any film's kit: `kit/puppet.gen.ts`, the counts read from a repository and a command's output lines with their times, and `kit/PuppetPlane.tsx`, a plane that shows them in its own embedded faces. `vd launch` also puts the plane in its copy of Stet for four seconds from the NUMBERS cue, on Stet's paper; `vd capture` leaves where to put it to your film. The command runs with no shell, and a command still running at its timeout is stopped and recorded as stopped. No accepted film uses them.

Each kit sizes things to words from `kit/metrics.gen.ts`, the letter widths of its own faces. For another face, make that table again: `python SKILL_FOLDER/tools/metrics.py SANS-VF.ttf MONO-VF.ttf`. Both must be variable fonts with a weight axis, and it refuses a static one. (A test film that changed its headline face without it typed its sentences with no caret.)

To use one of the library's named moves in such a film, copy its file and whatever it imports from `library/` into your `kit/`. The lists below are what the older `--kind` starters copy.

`vd new NAME --kind KIND` copies these into the film folder as `kit/`, beside the entry, so the film imports them and can change them. raea refuses imports from outside the entry's folder, which is why films used to write their own instead.

**explainer, launch, vertical, app** (a page film on score.json's clock; `app` is a light interface in a window, with its own `film.tsx`):
- `kit/base.tsx`: the starter kit. `Words` (sized by job: open 8 %, statement 5 %, proof 5.5 %, running 3.6 % of the height, on a band or with a shadow, inside a 6 % margin), `Drift`, `Grain`, `Halo`, `Plate`, `env`, `k01` and the palette `C`.
- `kit/lib/`: beat, core, faces, finish, join, optics, parts, physics, scene, and the licence texts of the two faces `faces` embeds. `scene` is the CSS camera over planes, `finish` the grain and halation, `core` the easings.
- `kit/motions/`: card-drop, caret-blink, defocus-in, fade-in, fade-step, ghost-zoom, grow-from-point, hold-drift, outline-to-fill, pop, shrink-to-point, skew-snap, whip-in, whip-out, zoom-settle.
- `kit/transitions/`: carry-match, collapse, cut, dissolve, recap-wall, ring-ripple, rise, smear, tile-collapse, type-matte, whip, zoom-burst.
- `kit/standins/`: meeting.
- `kit/finish.gen.ts`: the finish's generated grain and overlays.

There is no starter for a lit 3D scene. For one, read the 3D recipes in `library/recipes/` (the table above names each and what it costs) and copy what you need into the film folder; `weight-cut9.tsx`, below, is a whole 3D film to read, and it needs textures that are not shipped.

## A recorded voice

No film with a voice has been accepted yet; what follows is the mechanism, and two rules seen in the reference films: change scene in the breath between two sentences, and show a named thing on its name. A voice runs at about three words a second.

Put the take in the film's `media/` and name it in `score.json`: `"voice": "media/voice.mp3"`, or
`{"file": "media/voice.mp3", "at": 0.0, "gain": 0}` to start it later or change its level. The word times go in
`"words"` as `[{"text": "Lightning.", "start": 0.0, "end": 0.38}, ...]`, in seconds on the film's clock: the shape
raea writes (`raea cut TAKE "line"` transcribes a take into `words.json`), so copy that list in. `vd sound` reads them:
it ducks the bed, the Tone music and, in a film copied with `--like`, the film's own mix under the words and checks the level in each pause against the words beside it.
Your film's own code can read `score.words` to put a caption or a move on a word.

A recorded take can be cleaned first: `vd audio TAKE --clean-voice` takes out rumble below 80 Hz, steady noise, harsh s sounds and a little of the level's swing, and brings it toward -20 LUFS, into `media/` and `score.json`'s `voice`. Each step is measured, and one that costs the speech more than 3 dB is refused and named, with the steps before it kept. Listen to the result: the measure cannot tell a clean voice from a dulled one.

When someone else records the voice, the words are frozen once they record. So settle them on the cards, read by
strangers, and build the hardest shot as one frame before the recording, since that is the last moment a line can still
change for free. After that a changed line is a pickup: record the new words with the lines around them and splice
only those.

## A performance, from an earlier film (Weight)

`library/recipes/weight-cut9.tsx` is a snapshot of the whole film (it reads `lib/ground.ts` beside it and Poly Haven's
plaster, oak and sky from media/, which are not shipped). Line numbers below are in that file.

**A posture from named parts, driven by keys.** The figure's shape is one curve with three named controls: the stoop
(`level`, curling more the higher it goes), the neck alone (`nod`) and the waist (`bow`), lines 19-34. Each control is a
list of `[time, value, easing]` keys read by `keys()` (lines 121-130) with three easings: `s` smoothstep, `o` ease-out,
`i` ease-in; the lists are lines 133-138. Change the acting by changing the keys, not the geometry.

**A set-down solved so two things meet exactly.** To lay the iron on the floor from the figure's head, the bow and the
nod were solved outside the film so the head comes level with the floor's rise and the face is upright (`BOW`, `NOD`,
lines 131-133); `restOn` carries the object on the head and `itAt` hands it to the floor at that instant (lines 150-161).
Nothing slides or pops at the hand-over because the two poses are the same pose.

**A spine of blocks on a dark core.** The letter is 14 rigid oak blocks threaded on 16 dark core pieces along the curve
(lines 15-17, 76-95), so it bends without stretching and an open joint shows dark, not daylight. The pieces overlap by
design, so each carries `allowOverlap` (raea refuses overlapping meshes otherwise).

**One object by a cast bar.** Two Text3D letters are two solids; a thin iron bar under both (`BAR`, lines 96-111) makes
them one cast thing that tips and lands together.

**Words that act.** The words are `RichText` on the room's wall (z -1.58), arriving a word at a time with a little
weight (lines 174-212). The opening lines sag with the posture (`sagOf`, lines 180-183); "down." comes down with the iron,
as slowly, and lands with it; "I didn't fall." is tipped as far as the figure and comes level with it; the last line
starts bowed and straightens as it stands (lines 218-235).

**A room that gives light back.** The sun comes through a window in a wall out of frame (lines 38-46); a `RectLight` at
the window gives the sky's soft light, and a second at the sunlit wall gives the warm light it bounces back on the
backs of things (lines 48-70). The sun's `soft_shadow_size={0.6}` keeps shadow edges clean (TRAPS: above about 1 they
dither).

**Shots as a function of time.** `shotAt(t)` returns the camera, its target, focus and aperture for four shots, each a
change of what matters, each drifting inside itself (lines 163-172).
