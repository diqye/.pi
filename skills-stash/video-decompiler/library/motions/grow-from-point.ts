import { Motion, ease, easeBy, prog, lerp } from "../lib/core";
// Grows out of a point at the centre, leaning and skewed, and straightens as it lands.
export const meta = {
  name: "grow-from-point", kind: "enter", summary: "scale from a point with a lean that settles",
  function: "continuity between ideas",
  evidence: "the second benefit grows out of the point the first collapsed into",
  params: {
    ease: { default: "inOutSine", options: ["inOutSine", "outCubic", "inCubic", "inOutCubic"] },
    shutter: { default: 1.0, min: 0, max: 8, note: "frames of exposure for motion blur" },
    frames: { default: 18, min: 6, max: 48 }, from: { default: 0.04, min: 0, max: 0.8 },
    lean: { default: -7, min: -30, max: 30 }, skew: { default: -10, min: -40, max: 40 },
  },
  seenIn: "second benefit beat 12.80-13.15 s (scale from ink area: 0.11, 0.27, 0.52, 0.76, 0.91, 0.98 every 3 frames)",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => {
    const k = easeBy(p.ease)(prog(t, 1, p.frames));
    return { shutter: p.shutter, scale: lerp(p.from, 1, k), rotate: lerp(p.lean, 0, ease.outCubic(prog(t, 0, p.frames * 1.25))), skewX: lerp(p.skew, 0, k), opacity: t < 0 ? 0 : 1 };
  },
};
export default m;
