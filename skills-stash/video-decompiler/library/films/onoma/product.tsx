// From the name to the end (TM.PARTS.name to the last beat): the name, the request, the mix, the file, the name again. The line carries through all of it:
// the name's underline lifts into the prompt bar's edge, the tracks unfold from it, they fold back into it as the one
// finished sound, and it comes down to be the underline again.
import { WAVES } from "./kit/waves.gen";
import { C, D, FB, GLASS, M, R, T, TM, TX, arr, clamp01, glide, lerp, mw, on, outCubic, svg, tw } from "./kit/core";
import { BAR, HY, JING, JING2, LX, NAME, NS, NW, TRACKS } from "./line";

const REQ: string = TX.request, MORE: string = TX.more;   // typed on the frames sound.py strikes their keys (TM.TYPE)
const LABELS = ["rain", "footsteps", "clap + echo", "heartbeat", "music box"];
const TX0 = 600, TW = 980;                              // where a track's shape starts, and how wide one loop of the mix is
const SX0 = 400, SW = 1120;                             // the same loop once the tracks are one line
const P = TM.PARTS, LOOP: number = TM.LOOP;             // the parts' first beats (BOARD.md's beats table); beats in the mix's loop
const MIX0 = P.mix, BOX0 = P.more, MIX1 = P.take, END = P.end, ASK = P.ask;
const TAG = (beats: number[]): [string, number][] => ["Type", "a", "sound.", "Hear", "it."].map((w, i) => [w, beats[i]]);
const MARK = ["96, 165, 250", "240, 170, 60", "45, 212, 191", "248, 96, 104", "250, 220, 140"];        // one colour a track: rain, footsteps, clap + echo, heartbeat, music box
const TOK: [number, number, number][] = [[0, 4, 0], [6, 15, 1], [17, 33, 2], [35, 46, 3]];              // the sounds named in the request: [first letter, one past the last, track]
const SOFT = "#CFC9BD";                                 // the lines under the name
const HUES = ["58, 120, 200", "124, 108, 240", "208, 138, 32", "34, 168, 162", "216, 44, 58"];      // rain, thunder, footsteps, clap, heartbeat

/** a short line of words, centred on x, each arriving on its own beat */
function say(key: string, f: number, x: number, base: number, size: number, words: [string, number][], color: string, off?: number) {
  const gone = off === undefined ? 0 : clamp01((f - off * FB + 1) / 8);
  if (gone >= 1) return [];
  const gap = 0.26 * size, ws = words.map(([w]) => tw(w, size)), total = ws.reduce((a, b) => a + b, 0) + gap * (ws.length - 1);
  let px = x - total / 2;
  return words.map(([w, at], i) => {
    const k = arr(f, at, 12), el = k > 0 ? T(`${key}${i}`, px, base + (1 - k) * size * 0.2, size, w, { color, opacity: clamp01((f - at * FB + 1) / 7) * (1 - gone) }) : null;
    px += ws[i] + gap;
    return el;
  });
}
/** the name: five letters, one to each of the five sounds, each landing on its own half beat with that sound's colour
 *  under it. Set as one run of type so its letters sit as the face spaces them. */
function name(key: string, f: number, beats: number[], out: any[], off?: number) {
  const n = beats.filter((jb) => f >= jb * FB).length, gone = off === undefined ? 0 : clamp01((f - off * FB + 1) / 8);
  if (n <= 0 || gone >= 1) return;
  beats.forEach((jb, i) => {
    const a = f - jb * FB;
    if (a >= 0 && a < 110) out.push(R(`${key}h${i}`, LX[i] - 310, HY - 310, 620, 480, { background: `radial-gradient(closest-side, rgba(${HUES[i]}, 0.6), rgba(${HUES[i]}, 0))`, opacity: Math.exp(-a / 26) * Math.min(1, (a + 1) / 3) * (1 - gone) }));
  });
  out.push(T(key, 960 - NW / 2, HY - 64 - gone * 22, NS, NAME.slice(0, n), { fontWeight: 600, letterSpacing: "-0.035em", opacity: 1 - gone }));
}

export function product(f: number) {
  const out: any[] = [], b = f / FB;

  // ---- the name, the request, the end
  name("nm", f, JING, out, ASK);
  out.push(...say("tg", f, 960, HY + 100, 58, TAG(TM.TAG), SOFT, ASK));
  if (b >= END) {
    name("nm2", f, JING2, out);
    out.push(...say("tg2", f, 960, HY + 100, 58, TAG(TM.TAG2), SOFT));
  }

  // ---- the prompt bar: the line is its lower edge
  if (b >= ASK && b < END) {
    const show = clamp01((f - (ASK + 0.2) * FB) / 12) * (1 - clamp01((f - MIX1 * FB) / 9));
    const sent = Math.max(0, ...[MIX0, BOX0].map((p) => (f >= p * FB ? Math.exp(-(f - p * FB) / 7) * Math.min(1, (f - p * FB + 1) / 3) : 0)));           // return is pressed: the bar lights
    out.push(R("bar", BAR.x, BAR.y, BAR.w, BAR.h, { ...GLASS, background: `rgba(255, 255, 255, ${(0.075 + 0.16 * sent).toFixed(3)})`, borderRadius: 28, boxSizing: "border-box", opacity: show }));
    const second = b >= BOX0 - 2, text = second ? MORE : REQ, [t0, per] = TM.TYPE[second ? "more" : "request"] as number[];     // the bar clears two beats before the music box
    const n = Math.max(0, Math.min(text.length, Math.floor((f - t0 * FB) / per) + 1)), fadeOut = second ? 1 : 1 - clamp01((f - (BOX0 - 2.3) * FB) / 7);
    if (n > 0) out.push(M("req", BAR.x + 40, BAR.y + 64, 32, text.slice(0, n), { color: C.text, opacity: show * fadeOut }));
    (second ? ([[2, 13, 4]] as [number, number, number][]) : TOK).forEach(([a0, a1, k], i) => {                // each sound it names is marked in that sound's colour as its last letter lands
      if (n < a1) return;
      const g = outCubic(clamp01((f - (t0 * FB + (a1 - 1) * per)) / 12));
      out.push(R(`tok${second ? 9 : i}`, BAR.x + 40 + mw(text.slice(0, a0), 32), BAR.y + 76, mw(text.slice(a0, a1), 32) * g, 4, { background: `rgb(${MARK[k]})`, borderRadius: 2, opacity: show * fadeOut }));
    });
    const typing = n < text.length, blink = typing || Math.floor(f / 16) % 2 === 0;
    if (blink && show > 0 && fadeOut > 0.5 && b < MIX1) out.push(R("car", BAR.x + 40 + mw(text.slice(0, n), 32) + 5, BAR.y + 30, 3.5, 46, { background: C.light, opacity: show }));
    out.push(M("ret", BAR.x + BAR.w - 40 - mw("return", 26), BAR.y + 62, 26, "return", { color: sent > 0.2 ? C.light : C.dim, opacity: show }));
  }

  // ---- the mix: one line a sound, each drawn from that sound's own samples, and a playhead crossing them. At MIX1 the
  // tracks fold into the one line and it goes on playing: the same bar, now drawn as the sum of them.
  if (b >= MIX0 && b < END + 0.5) {
    const fold = glide(f, MIX1, 18), shut = glide(f, END, 12), els: any[] = [];
    const frac = (((f - MIX0 * FB) / FB) % LOOP) / LOOP, x0 = lerp(TX0, SX0, fold), wd = lerp(TW, SW, fold), px = x0 + wd * frac;
    if (fold < 1) LABELS.forEach((label, k) => {
      const from = k < 4 ? MIX0 + k * 0.1 : BOX0;
      if (!on(f, from)) return;
      const open = arr(f, from, 16), y = lerp(lerp(BAR.y + BAR.h, TRACKS[k], open), TRACKS[2], fold);
      const env = (WAVES.tracks as Record<string, number[]>)[label], n = env.length, pitch = wd / n;
      const age = (f - from * FB) / FB, firstPass = age < LOOP;                 // on its first bar a track is drawn as the playhead reaches it
      let quiet = "", lit = "";
      for (let i = 0; i < n; i++) {
        const x = x0 + (i + 0.5) * pitch;
        if (firstPass && x > x0 + (wd * (age % LOOP)) / LOOP) break;
        const hh = Math.max(1.2, env[i] * 42 * open * (1 - fold));
        const piece = `M${(x - 1.6).toFixed(1)},${(y - hh).toFixed(1)}h3.2v${(2 * hh).toFixed(1)}h-3.2z`;
        if (px - x >= 0 && px - x < 70) lit += piece; else quiet += piece;
      }
      els.push(<path key={`q${k}`} d={quiet} fill={C.light} opacity={0.5 * (1 - fold)} />, <path key={`l${k}`} d={lit} fill={`rgb(${MARK[k]})`} opacity={1 - fold} />);
      els.push(<path key={`c${k}`} d={`M${x0.toFixed(1)},${y.toFixed(1)}H${(x0 + wd).toFixed(1)}`} stroke={C.light} strokeOpacity={0.35 * (1 - fold)} strokeWidth={1.6} />);
      const lo = clamp01((f - from * FB - 4) / 8) * (1 - clamp01((f - MIX1 * FB) / 7));
      out.push(D(`ld${k}`, BAR.x + 34, y, 7, `rgb(${MARK[k]})`, { opacity: lo }));
      out.push(M(`lb${k}`, BAR.x + 56, y + 10, 30, label, { color: C.text, opacity: 0.9 * lo }));
    });
    if (fold > 0 && shut < 1) {
      const env = WAVES.sum as number[], n = env.length, pitch = wd / n, y = lerp(BAR.y + BAR.h, TRACKS[2], glide(f, MIX1, 16)) + (shut > 0 ? (HY - TRACKS[2]) * glide(f, END, 18) : 0);
      let quiet = "", lit = "";
      for (let i = 0; i < n; i++) {
        const x = x0 + (i + 0.5) * pitch, hh = Math.max(1.2, env[i] * 66 * fold * (1 - shut));
        const piece = `M${(x - 1.7).toFixed(1)},${(y - hh).toFixed(1)}h3.4v${(2 * hh).toFixed(1)}h-3.4z`;
        if (px - x >= 0 && px - x < 80) lit += piece; else quiet += piece;
      }
      els.push(<path key="sq" d={quiet} fill={C.light} opacity={0.55 * fold * (1 - shut)} />, <path key="sl" d={lit} fill={C.light} opacity={fold * (1 - shut)} />);
    }
    const grow = arr(f, MIX0, 16), edge = BAR.y + BAR.h;                 // the playhead comes out of the bar's edge with the tracks
    const top = lerp(lerp(edge, 412, grow), TRACKS[2] - 86, fold), bottom = lerp(lerp(edge, lerp(800, 902, arr(f, BOX0, 16)), grow), TRACKS[2] + 86, fold);
    if (shut < 1) els.push(<path key="ph" d={`M${px.toFixed(1)},${top.toFixed(1)}V${bottom.toFixed(1)}`} stroke={C.light} strokeWidth={2.4} opacity={1 - shut} />, <path key="ph2" d={`M${px.toFixed(1)},${top.toFixed(1)}V${bottom.toFixed(1)}`} stroke={C.light} strokeOpacity={0.14 * (1 - shut)} strokeWidth={12} />);
    out.push(svg("mix", els));
  }

  // ---- take it away: the claim above the one line, the file below it
  if (b >= MIX1 && b < END + 1) {
    out.push(...say("tk", f, 960, 480, 62, ["One", "line", "in.", "A", "finished", "sound", "out."].map((w, i): [string, number] => [w, TM.CLAIM[i]]), C.text, END));
    const k = arr(f, TM.FILE, 16), gone = clamp01((f - END * FB + 1) / 8), label = "storm-walk.wav · 0:08", w = mw(label, 34) + 278, y = lerp(TRACKS[2] + 70, TRACKS[2] + 124, k);
    if (k > 0 && gone < 1) {
      const o = clamp01((f - TM.FILE * FB + 1) / 7) * (1 - gone), tick = Math.exp(-((f % FB) / 9));                     // the dot keeps the beat: it is playing
      out.push(R("chip", 960 - w / 2, y, w, 88, { ...GLASS, borderRadius: 44, boxSizing: "border-box", opacity: o }));
      const env = WAVES.sum as number[], frac = (((f - MIX0 * FB) / FB) % LOOP) / LOOP, x1 = 960 - w / 2 + 44;                // the file holds the same sound: its shape, small, playing
      let quiet = "", lit = "";
      for (let i = 0; i < 28; i++) { const hh = Math.max(1.5, 20 * Math.max(...env.slice(i * 7, i * 7 + 7))), piece = `M${(x1 + i * 6).toFixed(1)},${(y + 44 - hh).toFixed(1)}h3.4v${(2 * hh).toFixed(1)}h-3.4z`; if (i / 28 <= frac) lit += piece; else quiet += piece; }
      out.push(svg("chipw", [<path key="q" d={quiet} fill={C.light} opacity={0.4} />, <path key="l" d={lit} fill={C.light} opacity={0.6 + 0.4 * tick} />], { opacity: o }));
      out.push(M("chipt", x1 + 190, y + 56, 34, label, { color: C.text, opacity: o }));
    }
  }
  return out;
}
