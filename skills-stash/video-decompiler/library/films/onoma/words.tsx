// The six words, beats 0 to 24. Each types, and when its request is sent it comes apart into the thing it names:
// the same letters, as specks of light, doing what that sound does, and ending in the line.
import { GLYPHS } from "./kit/glyphs.gen";
import { C, FB, R, T, TM, TX, circ, clamp01, inCubic, inOutCubic, lerp, rnd, svg, tw } from "./kit/core";
import { BOLT_F, BOLT_X, CLAPS, HUSH_F, HY, PULSES, PULSE_X, RAIN_F, STEPS } from "./line";

type Word = { text: string; x: number; base: number; t0: number; per: number; hit: number };
/** a word's specks. The words are sound.py's (TEXT) and their specks are made by tools/glyphs.py from its own list
 *  (WORDS), so a word changed in one and not the other has none: say so, in place of a failure that names nothing */
const glyph = (text: string) => {
  const g = GLYPHS[text];
  if (!g) throw new Error(`no specks for "${text}": add it, with its size, to WORDS in tools/glyphs.py and run that script (it and TEXT in sound.py must hold the same words)`);
  return g;
};
const cx = (text: string, c: number) => c - glyph(text).w / 2;
/** where each word is set; its text, first key (beat) and frames a key are sound.py's (TX, TM.TYPE), so each key is heard
 *  on the frame its letter appears. `hit` is the frame it comes apart on: on its sound, or a few frames before it */
const set = (name: string, x: number, base: number, hit: number): Word => ({ text: TX[name], x, base, t0: TM.TYPE[name][0], per: TM.TYPE[name][1], hit });
export const WORDS: Record<string, Word> = {
  rain: set("rain", cx(TX.rain, 960), 470, RAIN_F),
  thunder: set("thunder", 200, 330, BOLT_F),
  steps: set("steps", 180, 640, STEPS[0].f0 - 22),
  clap: set("clap", cx(TX.clap, 1100), 400, CLAPS[0].f0 - 14),
  heart: set("heart", 760, 380, PULSES[0] - 18),
  hush: set("hush", cx(TX.hush, 960), 560, HUSH_F),
};
/** the bolt: one jagged path up from the line, the same on every frame */
const BOLT = (() => {
  let d = `M${BOLT_X},${HY}`, x = BOLT_X, y = HY;
  for (let i = 0; i < 15; i++) { y -= 60; x += 16 + (rnd(i * 3) - 0.5) * 92; d += `L${x.toFixed(0)},${y.toFixed(0)}`; }
  return d + `M${BOLT_X + 70},${HY - 240}l70,-46l-18,-58l64,-40M${BOLT_X + 150},${HY - 520}l-74,-38l10,-52`;
})();
const boltX = (y: number) => BOLT_X + ((HY - y) / 60) * 16;
const STEP_OF = [0, 0, 0, 1, 1, 2, 2, 2, 3, 3];           // which footstep each letter of "footsteps." falls on

/** one word on frame f: its type while it is being typed, then its specks */
function word(name: string, f: number, out: any[]) {
  const w = WORDS[name], g = glyph(w.text), size = g.size;
  const typed = Math.max(0, Math.min(w.text.length, Math.floor((f - w.t0 * FB) / w.per) + 1));
  if (typed <= 0) return;
  if (f < w.hit) {
    out.push(T(`${name}t`, w.x, w.base, size, w.text.slice(0, typed)));
    if (typed < w.text.length || Math.floor(f / 14) % 2 === 0) out.push(R(`${name}c`, w.x + tw(w.text.slice(0, typed), size) + size * 0.06, w.base - size * 0.74, Math.max(3, size * 0.035), size * 0.84, { background: C.light }));
    return;
  }
  // ---- the specks
  let dots = "", streaks = "", refl = "";
  const P = g.pts, n = P.length / 3, r = g.step * 0.56;
  for (let i = 0; i < n; i++) {
    const x0 = w.x + P[3 * i], y0 = w.base + P[3 * i + 1], ci = P[3 * i + 2];
    let x = x0, y = y0, gone = false, tail = 0, tx = 0, ty = -1;      // tail: how long its streak is; (tx, ty): which way the streak points
    if (name === "rain") {                                  // they fall, and stretch as they fall
      const a = f - w.hit - rnd(i) * 30 - 6 * (P[3 * i] / g.w), v = 13 + 20 * rnd(i + 11);      // each leaves in its own time, at its own speed
      if (a > 0) { const d = v * (a - 5 * (1 - Math.exp(-a / 5))); y = y0 + d; x = x0 + 0.035 * d; tail = Math.min(16 + 2 * v, d * 0.7); tx = -0.035; gone = y >= HY; }
    } else if (name === "thunder") {                        // blown off the bolt, then down
      const a = f - w.hit, by = w.base - size * 0.35, ang = Math.atan2(y0 - by, x0 - boltX(by)) + (rnd(i + 3) - 0.5) * 0.9;      // thunder does not fall: it is blown outward and gone
      const dx = Math.cos(ang), dy = 0.6 * Math.sin(ang), dl = Math.hypot(dx, dy), reach = 150 + 520 * rnd(i);
      const far = reach * (1 - Math.exp(-a / 9)), far0 = reach * (1 - Math.exp(-Math.max(0, a - 2) / 9));
      x = x0 + dx * far; y = y0 + dy * far; gone = a > 34; tail = (far - far0) * dl; tx = -dx / dl; ty = -dy / dl;
    } else if (name === "steps") {                          // a few letters to each step, in an arc
      const s = STEPS[STEP_OF[ci]], f0 = s.f0 - 16 - rnd(i) * 7, u = clamp01((f - f0) / (s.f0 - f0));
      if (u > 0) { x = lerp(x0, s.x + (rnd(i + 1) - 0.5) * 96, u); y = lerp(y0, HY, u * u) - 44 * Math.sin(Math.PI * u); gone = u >= 1; }
    } else if (name === "clap") {                           // into one spike
      const u = inOutCubic(clamp01((f - w.hit) / 12));      // they are a column two frames before the clap, and the spike takes its place
      x = lerp(x0, CLAPS[0].x + (rnd(i) - 0.5) * 14, u); y = lerp(y0, HY - rnd(i + 2) * 250, u); gone = f >= CLAPS[0].f0;
    } else if (name === "heart") {                          // they pour into the line where the pulse will start
      const u = clamp01((f - w.hit - rnd(i) * 12) / 18);
      x = lerp(x0, PULSE_X + (rnd(i + 4) - 0.5) * 30, inOutCubic(u)); y = lerp(y0, HY, inCubic(u)); gone = u >= 1;
    } else {                                                // hush: they settle like dust and go out
      const a = f - w.hit - rnd(i) * 22;
      if (a > 0) { y = y0 + 0.5 * a + 0.018 * a * a; x = x0 + Math.sin(a * 0.08 + rnd(i) * 6) * 7; gone = a > 52; }
    }
    if (gone) continue;
    if (tail > 2) streaks += `M${(x + tx * tail).toFixed(1)},${(y + ty * tail).toFixed(1)}L${x.toFixed(1)},${y.toFixed(1)}`;
    else dots += circ(x, y, r);
    if (y < HY - 6 && name !== "hush") refl += circ(x, 2 * HY - y, r);
  }
  const fade = name === "hush" ? 1 - clamp01((f - w.hit - 12) / 50) : name === "thunder" ? 1 - clamp01((f - w.hit - 10) / 22) : 1;
  out.push(svg(`${name}s`, [
    <path key="r" d={refl} fill={C.light} opacity={0.1} />,
    <path key="s" d={streaks} stroke={C.light} strokeWidth={r * 1.7} strokeLinecap="round" fill="none" />,
    <path key="d" d={dots} fill={C.light} />,
  ], { opacity: fade }));
}

/** the rain that is not the word: three depths of it, falling to the line, for three beats */
function weather(f: number) {
  const a = clamp01((f - RAIN_F) / 18) * (1 - clamp01((f - (RAIN_F + 74)) / 30));
  if (a <= 0) return null;
  const layers = ["", "", ""];
  for (let i = 0; i < 260; i++) {
    const l = i % 3, v = [19, 27, 37][l], len = [24, 40, 64][l];
    const x = rnd(i) * 2700 - 350 + (f - RAIN_F) * 0.5 * (l + 1), y = ((f - RAIN_F) * v + rnd(i + 7) * 1500) % 1340 - 260;
    if (y < HY && y > -100) layers[l] += `M${x.toFixed(1)},${(y - len).toFixed(1)}L${x.toFixed(1)},${y.toFixed(1)}`;
  }
  return svg("weather", layers.map((d, l) => <path key={l} d={d} stroke={C.light} strokeOpacity={[0.16, 0.28, 0.46][l]} strokeWidth={[1.4, 2, 2.8][l]} strokeLinecap="round" fill="none" />), { opacity: a });
}

/** the bolt, and the rings the clap and its echoes send out */
function strikes(f: number, out: any[]) {
  const a = f - BOLT_F, k = a < 0 ? 0 : a < 4 ? 1 : a === 7 || a === 8 ? 0.6 : a === 12 ? 0.35 : 0;
  if (k > 0) out.push(svg("bolt", [
    <path key="b2" d={BOLT} stroke="#C9C2FF" strokeOpacity={0.14} strokeWidth={46} fill="none" strokeLinejoin="round" />,
    <path key="b1" d={BOLT} stroke="#E4DFFF" strokeOpacity={0.35} strokeWidth={16} fill="none" strokeLinejoin="round" />,
    <path key="b0" d={BOLT} stroke="#FFFFFF" strokeWidth={5} fill="none" strokeLinejoin="round" />,
  ], { opacity: k }));
  CLAPS.forEach((c, i) => {
    const ag = f - c.f0;
    if (ag < 0 || ag > 44) return;
    const rr = 24 + (520 - 110 * i) * (1 - Math.pow(1 - ag / 44, 3));
    out.push(<div key={`ring${i}`} style={{ position: "absolute", left: c.x - rr, top: HY - rr * 0.3, width: 2 * rr, height: rr * 0.6, borderRadius: "50%", border: `${(3 - i * 0.5).toFixed(1)}px solid ${C.light}`, boxSizing: "border-box", opacity: (1 - ag / 44) * (0.7 - 0.13 * i) }} />);
  });
}

export function words(f: number) {
  const out: any[] = [];
  out.push(weather(f));
  strikes(f, out);
  for (const name of Object.keys(WORDS)) word(name, f, out);
  return out;
}
