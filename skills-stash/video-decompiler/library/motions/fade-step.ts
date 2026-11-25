import { Motion, ease, prog, lerp } from "../lib/core";
// An item joining a list: a short rise and a fade (the layout also steps its colour up from the muted tone).
export const meta = {
  name: "fade-step", kind: "enter", summary: "short rise with fade, for an item joining a list or a printed line",
  function: "enumeration",
  evidence: "each platform steps in from grey, each terminal step prints on its own beat, so they are counted",
  params: { frames: { default: 7, min: 2, max: 20 }, rise: { default: 14, min: 0, max: 80, note: "px" } },
  seenIn: "platform list items at 14.80 s and 15.20 s; terminal output lines 5.00-5.50 s",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => { const k = ease.outCubic(prog(t, 0, p.frames)); return { y: lerp(p.rise, 0, k), opacity: t < 0 ? 0 : k }; },
};
export default m;
