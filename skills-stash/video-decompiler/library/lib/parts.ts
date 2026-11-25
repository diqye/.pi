// What every harvested part shares: its props, the run model, and colour picks that only ever read style tokens.
// A part draws from one film-wide frame number (t) and a list of runs: one run per beat the part appears in. Pure in t.
import { defaults } from "./core";

export type Run = { at: number; len: number; c: any; tone: string; id: string; params?: any };
export type PartProps = { t: number; fps: number; W: number; H: number; style: any; runs: Run[]; params?: any };

export const paramsOf = (meta: any, ...over: any[]) => Object.assign({}, defaults(meta), ...over);
// Tall frames stack things that sit side by side in a wide one.
export const stacked = (W: number, H: number) => H >= W;
export function runIndex(runs: Run[], t: number) { let k = -1; for (let i = 0; i < runs.length; i++) if (t >= runs[i].at) k = i; return k; }
// The run drawn at t, or -1 before the first run or past the end of the last (a part draws nothing outside its runs).
export function activeRun(runs: Run[], t: number) {
  const k = runIndex(runs, t);
  return k < 0 || t >= runs[k].at + runs[k].len ? -1 : k;
}
export const faceOf = (style: any, role: string) => style.type[role] ?? style.type.display;
// A colour token by name, looked up in the tone, then in style.color.
export const tokenOf = (style: any, tone: any, name: string) => tone[name] ?? style.color[name];
export function luma(hex: string) {
  if (!hex || hex[0] !== "#" || hex.length < 7) return 0.5;
  const n = parseInt(hex.slice(1, 7), 16);
  return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
}
// Of the given tokens, the one that reads best on `fill`.
export const readable = (fill: string, ...tokens: string[]) => tokens.filter(Boolean).reduce((a, b) => (Math.abs(luma(a) - luma(fill)) >= Math.abs(luma(b) - luma(fill)) ? a : b));
// A card reads as a card on either ground: the card token on a light tone, the surface token on a dark one.
export const cardFill = (style: any, tone: any) => (luma(tone.ground) < 0.5 ? style.color.surface : style.color.card);

// The source's stepped clock: `hz` steps a second, and every holdEvery-th step repeats the one before it.
export function stepAt(seconds: number, hz: number, holdEvery: number) {
  const f = Math.floor(seconds * hz);
  return holdEvery > 0 ? f - Math.floor((f + 1) / holdEvery) : f;
}
