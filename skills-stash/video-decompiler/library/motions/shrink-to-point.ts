import { Motion, ease, easeBy, prog, lerp } from "../lib/core";
// Leaves by tipping over and collapsing into the centre of the frame.
export const meta = {
  name: "shrink-to-point", kind: "exit", summary: "accelerating collapse to a point with a lean and skew",
  function: "continuity between ideas",
  evidence: "the first benefit collapses to the centre, handing that point to the next",
  params: {
    ease: { default: "inOutSine", options: ["inOutSine", "outCubic", "inCubic", "inOutCubic"] },
    shutter: { default: 1.0, min: 0, max: 8, note: "frames of exposure for motion blur" },
    frames: { default: 18, min: 6, max: 40 }, to: { default: 0.05, min: 0, max: 0.6 },
    lean: { default: -8, min: -30, max: 30 }, skew: { default: 12, min: -40, max: 40 },
  },
  seenIn: "first benefit beat exit 12.43-12.78 s (scale from ink area: 0.99, 0.91, 0.72, 0.49, 0.24, 0.11 every 3 frames)",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => {
    const k = easeBy(p.ease)(prog(t, 1, p.frames));
    return { shutter: p.shutter, scale: lerp(1, p.to, k), rotate: lerp(0, p.lean, ease.outCubic(prog(t, 0, p.frames))), skewX: lerp(0, p.skew, k), opacity: t > p.frames ? 0 : 1 };
  },
};
export default m;
