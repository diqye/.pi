// Plus One's kit: the clock, the colours, the curves and the plain parts. Everything is a function of the frame number,
// called from the one component that reads the frame. The curves keep the skill's rule for moves (SKILL.md, "Moves a
// viewer can watch"): an arrival decelerates into place over 12 frames or more, a camera eases in and out, and only a
// hit is instant.
import { staticFile } from "raea";
import { GEIST, GEIST_MONO } from "./fonts.gen";
import { ADV } from "./metrics.gen";
import { CLOCK } from "./times.gen";

// the clock is sound.py's (kit/times.gen.ts): 60 frames a second, 32 frames a beat (112.5 beats a minute), a bar four beats.
// W and H are the world the kit draws in (svg below); the film's frame size is score.json's (film.tsx): change both together
export const W = 1920, H = 1080, FPS = CLOCK.FPS;
export const FB = CLOCK.FB;
export const BASE = 0.855;                 // Geist's baseline below the top of a line box one em tall
export const C = { paper: "#F4EEE3", ink: "#1D1A16", soft: "#6F685E", faint: "#A9A296", white: "#FFFFFF", coral: "#EE5B3A", blue: "#3A6BE0", gold: "#E0A01C", cream: "#FFF4DC" };
/** the faces: Geist for the interface (embedded), and the display faces read from media/fonts */
const FACES: [string, string, string, string][] = [
  ["Fraunces", "fraunces.ttf", "normal", "100 900"], ["Fraunces", "fraunces-italic.ttf", "italic", "100 900"],
  ["Playfair Display", "playfair.ttf", "normal", "400 900"], ["Playfair Display", "playfair-italic.ttf", "italic", "400 900"],
  ["Anton", "anton.ttf", "normal", "400"], ["Bricolage Grotesque", "bricolage.ttf", "normal", "200 800"],
  ["DM Serif Display", "dmserif.ttf", "normal", "400"],
];
export const FONTS = `@font-face { font-family: "Geist"; src: url(${GEIST}); font-weight: 100 900; } @font-face { font-family: "Geist Mono"; src: url(${GEIST_MONO}); font-weight: 100 900; } `
  + FACES.map(([fam, file, style, weight]) => `@font-face { font-family: "${fam}"; src: url("${staticFile("fonts/" + file)}"); font-style: ${style}; font-weight: ${weight}; }`).join(" ");
export const SERIF = "Fraunces";           // the large words and the name

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const outCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const inCubic = (x: number) => x * x * x;
export const inOutCubic = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
/** past the mark a little, then back onto it: for a thing that lands with some spring */
export const outBack = (x: number, s = 1.4) => 1 + (s + 1) * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
/** an arrival you can watch: 0 to 1 from beat b, decelerating into place over n frames */
export const arr = (f: number, b: number, n = 14) => outCubic(clamp01((f - b * FB + 1) / n));
/** a move with weight: eases in and out over n frames from beat b */
export const glide = (f: number, b: number, n = 20) => inOutCubic(clamp01((f - b * FB + 1) / n));
/** a landing with spring from beat b over n frames */
export const pop = (f: number, b: number, n = 16) => { const k = clamp01((f - b * FB + 1) / n); return k <= 0 ? 0 : outBack(k); };
/** 0 to 1, straight, from beat b over n frames: for fades */
export const ramp = (f: number, b: number, n = 8) => clamp01((f - b * FB + 1) / n);
export const on = (f: number, b: number) => f >= b * FB;
export const rnd = (i: number) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
export const gauss = (x: number, s: number) => Math.exp(-(x * x) / (s * s));
export const tw = (s: string, px: number, face = "geist500", ls = -0.02) => { let w = 0; for (const ch of s) w += ADV[face][ch] ?? 0.6; return (w + ls * s.length) * px; };
export const mw = (s: string, px: number) => 0.6 * px * s.length;

type St = Record<string, any>;
/** a line of Geist with its baseline at `base` */
export const T = (key: string, x: number, base: number, size: number, text: any, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: base - BASE * size, fontFamily: "Geist", fontWeight: 500, fontSize: size, lineHeight: `${size}px`, letterSpacing: "-0.02em", color: C.ink, whiteSpace: "nowrap", ...st }}>{text}</div>
);
export const M = (key: string, x: number, base: number, size: number, text: any, st: St = {}) => T(key, x, base, size, text, { fontFamily: "Geist Mono", fontWeight: 400, letterSpacing: "0em", ...st });
/** a line in any face, set in a box so it can be centred or ranged right without measuring it */
export const L = (key: string, x: number, y: number, w: number, size: number, text: any, st: St = {}) => (
  <div key={key} style={{ position: "absolute", left: x, top: y, width: w, fontSize: size, lineHeight: `${Math.round(size * 1.06)}px`, color: C.ink, whiteSpace: "nowrap", textAlign: "center", ...st }}>{text}</div>
);
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
export const circ = (x: number, y: number, r: number) => `M${(x - r).toFixed(1)},${y.toFixed(1)}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0`;
/** a picture from media/, covering its box */
export const pic = (key: string, file: string, x: number, y: number, w: number, h: number, st: St = {}) => (
  <img key={key} src={staticFile(file)} style={{ position: "absolute", left: x, top: y, width: w, height: h, objectFit: "cover", ...st }} />
);
