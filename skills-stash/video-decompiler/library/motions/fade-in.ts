import { Motion, ease, prog } from "../lib/core";
export const meta = {
  name: "fade-in", kind: "enter", summary: "plain opacity fade",
  function: "pace",
  evidence: "availability and the address arrive after the name, in the order they are read",
  params: { frames: { default: 10, min: 1, max: 60 } },
  seenIn: "end card subline and address 20.93-21.47 s",
};
const m: Motion = { meta: meta as any, frames: (p) => p.frames, at: (t, _b, p) => ({ opacity: t < 0 ? 0 : ease.outCubic(prog(t, 0, p.frames)) }) };
export default m;
