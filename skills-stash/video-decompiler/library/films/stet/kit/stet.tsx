// Stet's own kit: the clock, the colours, and the few things the whole film is made of (BOARD.md, "The cast").
// Everything is a plain function of the frame number `f`, called from the one component that reads the frame, so no
// part can keep an earlier frame's picture (TRAPS: stills in one call are not independent).
import { GEIST, GEIST_MONO } from "./fonts.gen";
import { ADV } from "./metrics.gen";
import { CLOCK } from "./times.gen";

// the clock is sound.py's (kit/times.gen.ts): 60 frames a second, 24 frames a beat (150 beats a minute)
export const W = 1920, H = 1080, FPS = CLOCK.FPS;     // the kit draws to this size; film.tsx takes the frame's from score.json: change both together
export const FB = CLOCK.FB;
export const G = 48;                       // the page's grid
export const BASE = 0.855;                 // Geist's baseline below the top of a line box one em tall (hhea 1005/-295)
export const C = { paper: "#F6F5F1", ink: "#141414", red: "#FF4D1F", grey: "#8F8E89", soft: "#BDBCB6", white: "#FFFFFF" };
/** a sheet of glass on the page: a little of the air shows through, and it lifts off with a soft shadow */
export const GLASS = { background: "rgba(255, 255, 255, 0.84)", border: "1.5px solid rgba(255, 255, 255, 0.95)", boxShadow: "0 24px 60px rgba(30, 30, 60, 0.10), 0 2px 8px rgba(30, 30, 60, 0.06)" };
export const FONTS = `@font-face { font-family: "Geist"; src: url(${GEIST}); font-weight: 100 900; } @font-face { font-family: "Geist Mono"; src: url(${GEIST_MONO}); font-weight: 100 900; }`;

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const outExpo = (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
export const outCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const inOutCubic = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
/** an arrival you can watch: 0 to 1, starting on beat b's own frame and decelerating into place over about 1.8 n
 * frames (13 by default). Readers shown every frame called the old curve (7 frames, 63 % in the first) a one-frame swap. */
export const arr = (f: number, b: number, n = 7) => outCubic(clamp01((f - b * FB + 1) / Math.round(n * 1.8)));
/** a shut: fast and hard, for a bracket closing or a thing that should snap */
export const shut = (f: number, b: number, n = 7) => outExpo(clamp01((f - b * FB + 1) / n));
/** a plain ramp between two beats */
export const ramp = (f: number, b0: number, b1: number) => clamp01((f - b0 * FB) / ((b1 - b0) * FB));
export const on = (f: number, b: number) => f >= b * FB;
/** a string's width in px (no kerning: good to a few px at claim size) */
export const tw = (s: string, px: number, face = "geist500", ls = -0.02) => {
  let w = 0;
  for (const ch of s) w += ADV[face][ch] ?? 0.6;
  return (w + ls * s.length) * px;
};
export const mw = (s: string, px: number) => 0.6 * px * s.length;      // Geist Mono: every letter is 0.6 em

type St = Record<string, any>;
/** words in Geist, placed by their baseline */
export const T = (key: string, x: number, base: number, size: number, text: any, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: base - BASE * size, fontFamily: "Geist", fontWeight: 500, fontSize: size, lineHeight: `${size}px`, letterSpacing: "-0.02em", color: C.ink, whiteSpace: "nowrap", ...st }}>{text}</div>
);
/** words in Geist Mono */
export const M = (key: string, x: number, base: number, size: number, text: any, st: St = {}) =>
  T(key, x, base, size, text, { fontFamily: "Geist Mono", fontWeight: 400, letterSpacing: "0em", ...st });
/** the dot */
export const D = (key: string, cx: number, cy: number, r: number, color: string, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: "50%", background: color, ...st }} />
);
export const R = (key: string, x: number, y: number, w: number, h: number, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: y, width: w, height: h, ...st }} />
);

// ---- the page: a faint dot every 48 px, with one at the frame's exact centre
export const GX = (i: number) => i * G, GY = (j: number) => 12 + j * G;
const circ = (x: number, y: number, r: number) => `M${(x - r).toFixed(1)},${y.toFixed(1)}a${r.toFixed(2)},${r.toFixed(2)} 0 1,0 ${(2 * r).toFixed(2)},0a${r.toFixed(2)},${r.toFixed(2)} 0 1,0 ${(-2 * r).toFixed(2)},0`;
const GRID_D = (() => {
  let d = "";
  for (let j = -4; j <= 26; j++) for (let i = -6; i <= 46; i++) d += circ(GX(i), GY(j), 1.7);
  return d;
})();
export const grid = (key: string, color = C.ink, alpha = 0.14) => (
  <svg key={key} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }} width={W} height={H} viewBox={`0 0 ${W} ${H}`}><path d={GRID_D} fill={color} opacity={alpha} /></svg>
);

/** where a thing lands, a ring passes through the page's dots. evs: [beat, x, y] */
export function ripples(key: string, f: number, evs: [number, number, number][]) {
  let d = "";
  for (const [b, x, y] of evs) {
    const age = f - b * FB;
    if (age < 0 || age > 36) continue;
    const k = age / 36, rad = outCubic(k) * 620, band = 84, a = 1 - k;
    const i0 = Math.max(0, Math.floor((x - rad - band) / G)), i1 = Math.min(40, Math.ceil((x + rad + band) / G));
    const j0 = Math.max(0, Math.floor((y - rad - band - 12) / G)), j1 = Math.min(22, Math.ceil((y + rad + band - 12) / G));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const w = 1 - Math.abs(Math.hypot(GX(i) - x, GY(j) - y) - rad) / band;
      if (w > 0) d += circ(GX(i), GY(j), 1.7 + 3.0 * w * a);
    }
  }
  if (!d) return null;
  return <svg key={key} style={{ position: "absolute", left: 0, top: 0 }} width={W} height={H} viewBox={`0 0 ${W} ${H}`}><path d={d} fill={C.ink} opacity={0.2} /></svg>;
}

/** one flush through the page's dots from (x, y): a ring of them swells in `color` and is gone */
export function flush(key: string, f: number, b: number, x: number, y: number, color: string, frames = 22, reach = 900) {
  const age = f - b * FB;
  if (age < 0 || age > frames) return null;
  const k = age / frames, rad = outCubic(k) * reach, band = 150, a = 1 - k;
  let d = "";
  for (let j = -4; j <= 26; j++) for (let i = -6; i <= 46; i++) {
    const w = 1 - Math.abs(Math.hypot(GX(i) - x, GY(j) - y) - rad) / band;
    if (w > 0) d += circ(GX(i), GY(j), 1.7 + 11 * w * a);
  }
  if (!d) return null;
  return <svg key={key} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }} width={W} height={H} viewBox={`0 0 ${W} ${H}`}><path d={d} fill={color} opacity={0.85 * a} /></svg>;
}

// ---- a claim: words that arrive one at a time, a full stop that is a dot, stet marks under the word that matters
export type CW = { w: string; at: number; mark?: number; red?: boolean; br?: boolean; still?: boolean; color?: string };
export type Claim = { x: number; cy: number; size?: number; words: CW[]; stop?: { at: number; color?: string; hide?: boolean }; off?: number; center?: boolean; color?: string; weight?: number };
export const GAP = 0.25, STOP_R = 0.1, STOP_GAP = 0.075, LEAD = 1.25;
/** where a claim's words and its full stop sit. `cy` is the middle of the block; a word with `br` starts a new line. */
export function claimLayout(o: Claim) {
  const size = o.size ?? 80, face = `geist${o.weight ?? 500}`;
  const lines: number[][] = [[]];
  o.words.forEach((c, i) => { if (c.br) lines.push([]); lines[lines.length - 1].push(i); });
  const ws = o.words.map((c) => tw(c.w, size, face));
  const xs: number[] = [], bases: number[] = [];
  let stop = { x: 0, y: 0, r: STOP_R * size }, widest = 0;
  lines.forEach((ids, li) => {
    const last = li === lines.length - 1;
    const text = ids.reduce((a, i) => a + ws[i], 0) + GAP * size * (ids.length - 1);
    const whole = text + (last && o.stop ? (STOP_GAP + 2 * STOP_R) * size : 0);
    widest = Math.max(widest, whole);
    const base = o.cy + 0.265 * size + (li - (lines.length - 1) / 2) * LEAD * size;
    let x = o.center ? o.x - whole / 2 : o.x;
    const x0 = x;
    ids.forEach((i) => { xs[i] = x; bases[i] = base; x += ws[i] + GAP * size; });
    if (last) stop = { x: x0 + text + (STOP_GAP + STOP_R) * size, y: base - STOP_R * size, r: STOP_R * size };
  });
  return { size, xs, ws, bases, stop, widest, x0: xs[0] };
}
export function claim(key: string, f: number, o: Claim) {
  const gone = o.off === undefined ? 0 : clamp01((f - o.off * FB + 1) / 6);           // it leaves over six frames, not in one
  if (gone >= 1) return null;
  const L = claimLayout(o), size = L.size, out: any[] = [];
  o.words.forEach((c, i) => {
    const k = c.still ? (on(f, c.at) ? 1 : 0) : arr(f, c.at, 6);
    if (k <= 0) return;
    const col = c.color ?? o.color ?? C.ink;
    out.push(T(`${key}w${i}`, L.xs[i], L.bases[i] + (1 - k) * size * 0.16, size, c.w, { opacity: (c.still ? 1 : clamp01((f - c.at * FB + 1) / 7)) * (1 - gone), color: col, fontWeight: o.weight ?? 500 }));
    if (c.mark !== undefined && on(f, c.mark)) {
      const pitch = 0.2 * size, r = 0.043 * size, n = Math.max(2, Math.floor((L.ws[i] + pitch * 0.45) / pitch));
      const shown = Math.ceil(n * clamp01((f - c.mark * FB + 1) / 7));
      const left = L.xs[i] + (L.ws[i] - (n - 1) * pitch) / 2;
      for (let j = 0; j < shown; j++) out.push(D(`${key}m${i}_${j}`, left + j * pitch, L.bases[i] + 0.21 * size, r, c.red ? C.red : col, { opacity: 1 - gone }));
    }
  });
  if (o.stop && !o.stop.hide) {
    const k = arr(f, o.stop.at, 6);
    if (k > 0) out.push(D(`${key}stop`, L.stop.x, L.stop.y, L.stop.r * k, o.stop.color ?? o.color ?? C.ink, { opacity: 1 - gone }));
  }
  return out;
}

// ---- the brackets: Stet's hold. kl and kr are how far each has shut (0 open, 1 shut)
export function brackets(key: string, cx: number, cy: number, w: number, h: number, color: string, o: { sw?: number; arm?: number; kl?: number; kr?: number; spread?: number } = {}) {
  const sw = o.sw ?? Math.max(3, Math.round(h * 0.085)), arm = o.arm ?? Math.round(h * 0.2), spread = o.spread ?? 340;
  const kl = o.kl ?? 1, kr = o.kr ?? 1, out: any[] = [];
  const t = cy - h / 2, st = { background: color };
  if (kl > 0) {
    const L = cx - w / 2 - (1 - kl) * spread;
    out.push(R(`${key}l0`, L, t, sw, h, st), R(`${key}l1`, L, t, arm, sw, st), R(`${key}l2`, L, t + h - sw, arm, sw, st));
  }
  if (kr > 0) {
    const Rr = cx + w / 2 + (1 - kr) * spread;
    out.push(R(`${key}r0`, Rr - sw, t, sw, h, st), R(`${key}r1`, Rr - arm, t, arm, sw, st), R(`${key}r2`, Rr - arm, t + h - sw, arm, sw, st));
  }
  return out;
}

// ---- the pointer: the cause
export function pointer(key: string, x: number, y: number, down = 0) {
  const s = 2.7 * (1 - 0.14 * down);
  return (
    <svg key={key} style={{ position: "absolute", left: x - 3 * s, top: y - 3 * s, overflow: "visible" }} width={64} height={80} viewBox="0 0 64 80">
      <path d="M3 3 L3 20.5 L7.4 16.6 L10.6 23.8 L13.6 22.5 L10.5 15.4 L16.4 15.4 Z" transform={`scale(${s})`} fill={C.ink} stroke="#fff" strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}
/** the ring a press leaves */
export function ring(key: string, f: number, b: number, x: number, y: number, color = C.ink) {
  const k = (f - b * FB) / 16;
  if (k < 0 || k >= 1) return null;
  const r = lerp(8, 44, outCubic(k));
  return <div key={key} style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: "50%", border: `2.5px solid ${color}`, boxSizing: "border-box", opacity: (1 - k) * 0.55 }} />;
}
/** how far down a press is at frame f: down in 3 frames on beat b, up again by 10 */
export const press = (f: number, b: number) => { const d = f - b * FB; return d < 0 || d > 10 ? 0 : d < 3 ? (d + 1) / 3 : 1 - (d - 3) / 7; };
/** a place along keyed points [beat, x, y], easing between them */
export function along(f: number, keys: [number, number, number][]): [number, number] {
  if (f <= keys[0][0] * FB) return [keys[0][1], keys[0][2]];
  for (let i = 1; i < keys.length; i++) {
    if (f <= keys[i][0] * FB) {
      const k = inOutCubic(clamp01((f - keys[i - 1][0] * FB) / ((keys[i][0] - keys[i - 1][0]) * FB)));
      return [lerp(keys[i - 1][1], keys[i][1], k), lerp(keys[i - 1][2], keys[i][2], k)];
    }
  }
  const l = keys[keys.length - 1];
  return [l[1], l[2]];
}

// ---- a status dot: passed (ink), failed (vermilion), running (a ring with a blinking heart)
export type Run = "pass" | "fail" | "run";
export function status(key: string, f: number, cx: number, cy: number, r: number, s: Run) {
  if (s === "run") {
    return [
      <div key={`${key}ring`} style={{ position: "absolute", left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: "50%", border: `${Math.max(2, r * 0.28)}px solid ${C.soft}`, boxSizing: "border-box" }} />,
      Math.floor(f / 5) % 2 === 0 ? D(`${key}heart`, cx, cy, r * 0.3, C.grey) : null,
    ];
  }
  return D(key, cx, cy, r, s === "pass" ? C.ink : C.red);
}
