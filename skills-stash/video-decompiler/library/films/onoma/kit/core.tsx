// Onoma's kit: the clock, the colours, the curves and the plain parts. Everything is a function of the frame number,
// called from the one component that reads the frame (TRAPS: stills in one call are not independent).
// The curves keep the skill's rule for moves (SKILL.md, "Moves a viewer can watch"): an arrival decelerates into place
// over 12 frames or more, a camera eases in and out, and only a hit is instant.
import { GEIST, GEIST_MONO } from "./fonts.gen";
import { ADV } from "./metrics.gen";
import { CLOCK, TEXT as TX, TIMES as TM } from "./times.gen";

// the clock and the events are sound.py's (kit/times.gen.ts): 60 frames a second, 30 frames a beat (120 beats a minute)
export const W = 1920, H = 1080, FPS = CLOCK.FPS;
export const FB = CLOCK.FB;
export { CLOCK, TM, TX };
export const BASE = 0.855;                 // Geist's baseline below the top of a line box one em tall
export const C = { night: "#0A0B10", light: "#FFF1D6", text: "#F4EFE6", dim: "#A9A498", faint: "#6E6A62", red: "#FF5A3C" };
export const FONTS = `@font-face { font-family: "Geist"; src: url(${GEIST}); font-weight: 100 900; } @font-face { font-family: "Geist Mono"; src: url(${GEIST_MONO}); font-weight: 100 900; }`;

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const outCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const inCubic = (x: number) => x * x * x;
export const inOutCubic = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
/** an arrival you can watch: 0 to 1 from beat b, decelerating into place over n frames */
export const arr = (f: number, b: number, n = 14) => outCubic(clamp01((f - b * FB + 1) / n));
/** a move with weight: eases in and out over n frames from beat b */
export const glide = (f: number, b: number, n = 20) => inOutCubic(clamp01((f - b * FB + 1) / n));
export const on = (f: number, b: number) => f >= b * FB;
export const rnd = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
export const gauss = (x: number, s: number) => Math.exp(-(x * x) / (s * s));
export const tw = (s: string, px: number, face = "geist500", ls = -0.02) => { let w = 0; for (const ch of s) w += ADV[face][ch] ?? 0.6; return (w + ls * s.length) * px; };
export const mw = (s: string, px: number) => 0.6 * px * s.length;

type St = Record<string, any>;
export const T = (key: string, x: number, base: number, size: number, text: any, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: base - BASE * size, fontFamily: "Geist", fontWeight: 500, fontSize: size, lineHeight: `${size}px`, letterSpacing: "-0.02em", color: C.text, whiteSpace: "nowrap", ...st }}>{text}</div>
);
export const M = (key: string, x: number, base: number, size: number, text: any, st: St = {}) => T(key, x, base, size, text, { fontFamily: "Geist Mono", fontWeight: 400, letterSpacing: "0em", ...st });
export const D = (key: string, cx: number, cy: number, r: number, color: string, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: "50%", background: color, ...st }} />
);
export const R = (key: string, x: number, y: number, w: number, h: number, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: y, width: w, height: h, ...st }} />
);
/** an svg the size of the world that does not clip what the camera sees beyond it */
export const svg = (key: string, children: any, st: St = {}) => (
  <svg key={key} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", ...st }} width={W} height={H} viewBox={`0 0 ${W} ${H}`}>{children}</svg>
);
/** a small circle as a path piece */
export const circ = (x: number, y: number, r: number) => `M${(x - r).toFixed(1)},${y.toFixed(1)}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0`;
/** glass on a dark ground */
export const GLASS = { background: "rgba(255, 255, 255, 0.075)", border: "1.5px solid rgba(255, 255, 255, 0.22)", boxShadow: "0 30px 80px rgba(0, 0, 0, 0.45)" };
