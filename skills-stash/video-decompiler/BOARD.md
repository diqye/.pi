# The board

The whole film on one page, written before any film code. This form was drawn from the accepted films' boards. Each
worked film in `library/films/` carries its own board, written before the form was fixed, and says where it differs;
read one before writing yours. Write yours as `BOARD.md` in the film folder, under these headings, in this order.

## The form

**One sentence.** What a stranger says the film told them, in their words: the product, what it does, what comes of
it. ("You type one line, it becomes an invitation worth answering, and the yeses come back.")

**The product, and the claim.** What it is, who uses it, the one viewer this film is for, and the one claim it makes
to them. Real facts only. For a made-up product, say it is made up.

**What the film is held against.** The good film of this kind whose shape yours takes (`REFERENCE.md`, or the worked
film you started from). A few lines on what you take from it. Then **what a viewer of this kind expects, all kept**:
for a launch, the trouble in their own terms first, the mark early, pieces of the real interface, proofs with numbers,
the name, what it works with, how to start.

**The world** (WORLD.md says how to find it). In this order:
- its line: the subject, crossed with one far thing, true of how the subject works;
- the name, the mark and the claim as one idea;
- what a film of this kind usually looks like, and what of that treatment you leave;
- what everything on screen is made of: the real pictures, the few colours and what each means, the faces of type,
  the ground and the question it answers;
- the two or three moves the film is built on (WORLD.md, "Moves that carry meaning"), and what each means here.

**The one idea.** The one thing the film follows: where it first appears, what the film does with it, and what it
becomes at the end. Once it is on screen it stays there. ("The invitation is one card, and it is on screen from the
moment the typed line becomes it until it becomes the mark.")

**The cast.** The few things on screen, each with what it is made of and its one job. One accent colour and what it
means. The faces of type and what each is for.

**Type, as the four accepted films set it.** This is what is in their code: four films by one maker, so a record and
not a rule.
- Each face has one job, and the kit says which. Plus One: Fraunces for the large words and the name, Geist for the
  interface (`plusone/kit/core.tsx`). Linden: a grotesque for the large words, a serif italic for one sentence, a mono
  for call numbers (`linden/kit/core.tsx`). Stet and Onoma use one family, Geist and Geist Mono.
- A serif sets three words or fewer at a time: single large words, the name, one short italic line. Sentences are in
  the sans.
- A held frame has one line of display type, and the next type down is about half its size or less (180 over 78 in
  Plus One, 200 over 58 in Onoma). Where two are closer, the smaller is another face, in italic or capitals (Linden's
  name at 140 over an italic 80).
- Large type is tracked tight, -0.03 to -0.05em. Sentences in Geist are at -0.02em. Small capitals are in the mono,
  opened to between +0.10 and +0.16em.
- Claims and large words arrive a word at a time on the beat, or are typed (`claim()` in `stet/kit/stet.tsx`, `say()`
  in `onoma/product.tsx`). Under the name, Plus One and Linden bring the line in whole; Stet and Onoma bring it in a word at a time.
- Each film ends on its name, alone, with one line under it (150 over 44, 156 over 60, 200 over 58, 140 over 80).

Two test films that their viewer placed close to these four differed here: whole sentences set in the serif, two or
three display lines of nearly one size in a frame, lines faded in whole. Type was the one thing he named. Whether
these are why has not been tested.

**The clock.** Beats a minute, frames in a beat, bars, beats, frames, seconds. Every event lands on this grid.

**The beats.** One table, a row for each stretch of the film:

| beats | part | words | picture | why it follows | how it hands to the next |
|---|---|---|---|---|---|

(One accepted board keeps words and picture in one column, "what happens". Either is fine; "why it follows" is not optional. The last column names the kind of boundary: becomes, carried, matched, door, or change of ground.)

**The turn.** The one moment the film changes state, and what is different before and after it, in the picture and
in the music.

**Ties.** What appears early and comes back later, and what its return means:

| what | first | returns | what the return means |
|---|---|---|---|

**Gifts.** Two or three moments of wonder nobody asked for, each with its beat.

**Framings.** Each framing and what it is for. None is held for more than a third of the film.

**Rules of this film.** The few rules a viewer could feel: how things arrive, what a colour means, what is never cut
by the frame. Copy the worked film's rules that still apply and drop the rest.

**Hardest shot.** The stretch that will cost the most. It is built and looked at first, with its real pictures.

**Sound.** The key, the chord for each bar, the pattern, the tune, and what each sound means (one meaning each).

**Sources and licences.** Every picture, face of type and sample: where it came from and the licence it is under.

## The checks (the board is done when every one passes)

1. The world's line names the subject and the far thing, and a stranger shown only the world's picture sheet (made
   in SKILL.md's step 4, so this check closes there) would want to see the film.
2. Every row of the beats has a "why it follows" and a kind of boundary, and none of them is "next" or "cut" for want
   of a better idea.
3. Every row shows the one thing, or sets it up, or turns it into its next form.
4. Every claim in the words has a row where the picture does it, large: one number or one line, never a screen of
   small text.
5. Every tie has both its first appearance and its return in the beats, and the ending answers the opening.
6. There are two gifts or more, and no framing is held for more than a third of the film.
7. The hardest shot is named.
8. Every picture has a source line, and each real picture has a job in a row (it is chosen, sent, compared, opened).

A board that passes these can still make a dull film. The readers, and then the person, find that out.
