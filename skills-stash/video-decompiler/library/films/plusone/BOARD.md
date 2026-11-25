# Plus One: the board

A consumer app, an interface demo. First written before any code on 12 November 2026, and brought up to date here
with the cut the person accepted (the clock was rewritten once, after readers: see `README.md`).

## One sentence

You type one line, it becomes an invitation worth answering, and the yeses come back.

## The product (made up)

Plus One, an invitation app for a phone. Its mark is "+1": the thing a guest sends back when they are coming. The
film's claim is in the name: every reply is a +1.

## What the film is held against

Linearity's launch film for its AI design tool: a mess stated first, then the name, then one task done in order on a plain
ground, a prompt box, the made thing in the middle of the frame, two large words naming each action, and the made
thing multiplied in depth at the end. Taken from it: that order, and the two-word names for the acts.

## The world

- **Its line.** An invitation is one card, and museum paintings are its clothes. The room wears what the card wears.
  Every yes is a "+1", and a "+1" is a small firework.
- **The name, the mark and the claim.** "Plus One": the mark is "+1", the thing a guest sends back. The last reply in
  the film asks to bring a plus one.
- **The usual look it leaves** (written after the film, for this form). The usual app demo floats screenshots on a gradient. This one keeps the made thing itself in the middle of the frame, large, and lets the interface shrink to a pointer and a few buttons.
- **What it is made of.** Five public-domain works as the invitation's looks; sixteen painted portraits as faces (fifteen
  guests and the host); a warm paper room that takes each work's colours and becomes the fireworks print's night; a soft serif for
  the large words, a grotesk for the interface, a different display face on each look.

## The one idea

The invitation is one card, and it is on screen from the moment the typed line becomes it until it becomes the mark.
The room takes the colours of whatever the card is wearing. Every reply is a +1, and a +1 is a small firework.

## Ties (what returns, and what the return means)

| what | first | returns | what the return means |
|---|---|---|---|
| "can I bring someone" | the mess, beat 3 | "can I bring Theo?", beat 57 | The product's name is the answer to a real question |
| The fireworks print | the fourth look, beat 29 | the room at night; every reply is a firework | The look that was chosen becomes the world |
| The card | beat 12 | every beat after; the mark | One object from the typed line to the logo |

## The cast

- **The card.** 620 by 860, rounded. Plain, then five looks, then the one chosen.
- **The room.** Warm paper with soft colour in it, taken from the art on the card. Night once the fireworks are chosen.
- **The pointer.** A soft round touch point. It leads; the view follows it.
- **The large words.** One for each act, behind the card in depth: "Name it." "Dress it." "Send it." Then the count.
- **The guests.** Twenty-four friends with short names; fifteen have a painted portrait as their picture.

## The clock

112.5 beats a minute at 60 frames a second: a beat is 32 frames, a bar is 4 beats (2.13 s). 18 bars, 72 beats, 2304
frames, 38.4 s. Every event's beat is a name in `sound.py`'s table `T`.

## The beats

| beats | what happens | why it follows |
|---|---|---|
| 0 to 8 | **The mess.** A group chat fills the frame, eleven bubbles, about one a half beat (the first three are three quarters of a beat apart): "party at mine saturday??", "which saturday", "what time", "8ish", "where's 'mine' again", "can I bring someone", "wait is this the 14th", "the 13th!!", "who's coming", "??", "is it still on". At 6.5 the bubbles lose their words, shrink to dots and fall into one point: a caret. | The trouble, in the guests' own words. The mess becomes the caret, so nothing is cut away |
| 8 to 12 | **Name it.** The large words arrive behind. A field opens round the caret and the line is typed: "Mira's 30th. Rooftop, Saturday 13th at 8." Each part is underlined in its own colour: what, where, when. | The whole input is one line. The caret is where the mess went |
| 12 to 16 | Return. The field grows into the card: the same object, taller. The three parts leave the line together and take their places: the title, the place with a pin, the day and hour. The app adds what was not said: a host line, "I'm in", "Can't". | The line is now an invitation: the claim, as one move. Return is pressed |
| 16 to 32 | **Dress it.** The plain card steps back among its five looks, a row of six in depth, each the same invitation in another look, each a real work of art with its credit under it. The pointer flicks; a look lands in front on beats 21.5, 24, 25.75 and 29 (the fifth, Sunday, stays in the row); the room takes each one's colours; five dots under the row show where we are. | The same invitation, five ways, and a room that changes with it. The plain card asks for a look ("Add a look") |
| 32 to 36 | The pointer taps the fireworks print: a tick. The other five fall away, the card comes forward, the room is night. | The choice. Night sets up the fireworks to come |
| 36 to 41.5 | **Send it.** The pointer taps "Add guests" and twenty-four faces roll in round the card. The button reads "Send to 24 guests". Press: "Sent to 24", then small copies of the card leave from behind it to every face. | Who it goes to, and the act of sending. The dressed card is ready |
| 41.5 to 45 | One guest's own phone: the invitation on it, her finger on "I'm in", which becomes "You're in". Her face is the first on the card. | The other side of the product: her tap is the first reply. A copy flew to her |
| 45 to 57 | **The replies.** Nineteen of them. Each is a face landing on the card's guest row, a "+1" that pops where that guest stood, a small firework behind the card, the count behind the card one higher. They come faster. A few words arrive with them ("bringing cake", "finally!!"). | Plays 1 to 19, starting with her reply reaching the card, each adding a face, a count and a firework. She answered; so do they |
| 57 to 61 | A close shot: "can I bring Theo?" The pointer taps "+1" on it. The count goes from 19 to 20, "20 of 24 in". The biggest burst. | **The high point.** The opening's question, answered by the product's name. It is the one reply that asks something |
| 61 to 64 | Two more far fireworks; the view draws back. | A breath |
| 64 to 72 | **The end.** The card draws back; the "+1"s go to the middle and are the mark: a rounded square with "+1" on it. The name beside it, and the line "Invitations people answer." Far fireworks to the end. | The card ends as the mark; the mark is the reply. Everything on screen was a +1 |

### How each part hands to the next

| from, to | kind | what it means |
|---|---|---|
| the mess, the caret | becomes | the trouble is what the product starts from |
| the typed line, the card | becomes | one line is the whole invitation |
| the card, the row of its looks | carried | the same invitation steps back among its own looks |
| the chosen look, the night | change of ground | the choice makes the world the rest happens in |
| the card, a guest's phone | door | a copy flies to her, and the film follows it in |
| her press, the replies | carried | her face is the first on the card |
| the replies, the question | carried, by the camera | one reply out of twenty is worth stopping on |
| the card, the mark | becomes | the invitation was the product's name all along |

## The words on screen

The chat lines (0 to 5.5) · "Name it." (8) · the typed line (8.5) · on the card: "YOU'RE INVITED", "Mira's 30th", the
date and hour, "Rooftop", "Mira is hosting", "I'm in", "Can't" (12 to 15) · "Dress it." (16) · "Add a look" · the credit
under each look (21.5 to 29) · "Send it." (36) · "Add guests", "Send to 24 guests", "Sent to 24" (36.5 to 40) · the guests'
names under their faces (37 on) · "Zoe's phone" (41.5) · "You're in" (44.25) · the count and "in" (45 on) · "bringing cake", "finally!!", "can I bring Theo?" · "20 of 24 in" (60) · "+1",
"Plus One", "Invitations people answer." (67 on).

## Gifts

- The print chosen as the look, fireworks over a bridge at night, becomes the night the rest of the film happens in,
  and every reply after it is a firework.
- The guests' faces are old painted portraits.
- At the end every "+1" leaves the guest it stood by and gathers in the middle to make the mark.

## Framings (none for more than a third)

Wide and drifting back (the mess) · close on the field · the card at reading size · the row of five in depth, wide,
pushing in through it · the chosen card close · the card among the guests, wide · one guest's phone, close · the
replies, pulling back slowly · close on the question · the mark, close.

## Rules of this film

- Arrivals take 12 frames or more and decelerate; the camera eases in and out; only a hit is instant.
- The card is carried across every change. Nothing is swapped in one frame.
- The proof of each claim gets the frame: the typed line, the looks, the send, one guest's press, the count.
- Several things move at once, then a quieter stretch; no hold where nothing moves for a reason.
- A word finishes typing 12 frames or more before anything happens to it. Words are typed where the camera already is.
- A control is never cut by the frame.
- Small text that carries the story is 30 px or more at the size it is shown.
- Music first: one chord a bar, a pattern, the +1s as its tune. Events land inside it.

## Hardest shot

Beats 16 to 32: five dressed cards in depth, flicked through, with the room changing. It was built and looked at
first, with the real art, before the rest of the film was written.

## Sound

Made in `sound.py` from sines and noise: no samples, no service. F major, one chord a bar (Fmaj7, Dm7, B♭maj7, C7sus).
Bars 1 and 2 have no chord: only the bubbles' pops, each on a change of picture, slightly out of tune with each other,
and a tick. The chord arrives with the name on beat 8. Each look lands with a soft knock. From the choice the beat is
on every quarter. Each +1 is a wooden pluck, and the plucks climb the scale as the count climbs. The fireworks are
short soft bursts.

## What changed between the first board and the accepted cut

- The first board ran 84 beats (44.8 s). After one round of readers the clock was rewritten to 72 beats: the browse
  through the looks is shorter and uneven; a guest's own phone is shown before the count; the pointer taps "Add
  guests" before the faces come; the send is press, then "Sent to 24", then the copies; the typed line carries the
  date; "of 24" is in the count.
- The question that comes back, "can I bring Theo?", and the "+1"s gathering into the mark, were added after the
  first cut.
- A scan of the first cut found fourteen seconds of holds. They were filled by depth: the row sways, the art drifts
  in its windows, the chosen card floats, the faces bob, the camera keeps pushing.
- The last cut gave the flick through the looks an ease in: it had left at full speed, and the room's colour changed
  in a frame.

## Sources and licences

Art: public-domain works from the open-access collections of the Metropolitan Museum of Art, the Art Institute of
Chicago and the Cleveland Museum of Art, each flagged public domain or CC0 by the museum's own record; the list with
titles, artists and links is `media/art/SOURCES.md`. Fonts: Geist and the display faces are under the SIL Open Font
Licence; the list is in the same file. Nothing else is used.
