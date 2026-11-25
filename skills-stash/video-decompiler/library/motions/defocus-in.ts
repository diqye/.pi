import { Motion, ease, easeBy, prog, lerp } from "../lib/core";
// Racks from a heavy blur to sharp, a lens pulling focus.
export const meta = {
  name: "defocus-in", kind: "enter", summary: "blur-to-sharp focus pull with a slight scale settle",
  function: "reveal",
  evidence: "after the dive the name racks into focus, like a lens finding it",
  params: {
    ease: { default: "inOutSine", options: ["inOutSine", "outCubic", "inCubic", "inOutCubic"] }, frames: { default: 26, min: 4, max: 60 }, blur: { default: 18, min: 0, max: 60 }, from: { default: 1.12, min: 0.9, max: 1.3 } },
  seenIn: "end card name 20.37-20.75 s",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => { const k = easeBy(p.ease)(prog(t, 0, p.frames)); return { blur: lerp(p.blur, 0, k), scale: lerp(p.from, 1, k) }; },
};
export default m;
