import { Motion, easeBy, prog, lerp } from "../lib/core";
// Starts far bigger than the frame and decelerates hard into place.
export const meta = {
  name: "zoom-settle", kind: "enter", summary: "big-to-rest zoom on an exponential ease-out",
  function: "emphasis on a key word",
  evidence: "the benefit line slams down from 1.9x and lands on the frame it fills solid",
  params: {
    shutter: { default: 0.6, min: 0, max: 8, note: "frames of exposure for motion blur" }, frames: { default: 24, min: 6, max: 60 }, from: { default: 1.9, min: 1.05, max: 4 }, ease: { default: "outExpo", options: ["outExpo", "outQuad", "outCubic", "outQuart"] } },
  seenIn: "first benefit beat 10.80-11.20 s (ink width 1.46x at 6 frames, 1.27x at 9, 1.07x at 15, 1.0 at 24)",
};
const m: Motion = { meta: meta as any, frames: (p) => p.frames, at: (t, _b, p) => ({ scale: lerp(p.from, 1, easeBy(p.ease)(prog(t, 0, p.frames))) }) };
export default m;
