import { Motion, ease, prog } from "../lib/core";
// Scale from nothing with a small overshoot: markers and pins.
export const meta = {
  name: "pop", kind: "enter", summary: "scale-from-zero with a spring overshoot",
  function: "enumeration",
  evidence: "found places pop onto the result one by one, so the viewer counts them",
  params: { frames: { default: 9, min: 3, max: 30 }, overshoot: { default: 0.18, min: 0, max: 0.5 } },
  seenIn: "result beat markers 9.27-9.67 s",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => (t < 0 ? { scale: 0, opacity: 0 } : { scale: ease.spring(prog(t, 0, p.frames), p.overshoot) }),
};
export default m;
