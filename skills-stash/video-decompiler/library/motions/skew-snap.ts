import { Motion, ease, prog, lerp } from "../lib/core";
// Arrives already leaning, with a skew and a little extra size that snap out in a few frames; the lean stays.
export const meta = {
  name: "skew-snap", kind: "enter", summary: "hard-cut entrance that snaps from a skewed, oversized lean to a resting tilt",
  function: "contrast",
  evidence: "only the negation leans; every other line in the film sits level",
  params: {
    shutter: { default: 1.0, min: 0, max: 8, note: "frames of exposure for motion blur" },
    frames: { default: 8, min: 3, max: 20 }, rest: { default: -3.2, min: -12, max: 12, note: "resting rotation, deg" },
    fromRotate: { default: -7, min: -30, max: 30 }, fromSkew: { default: -16, min: -40, max: 40 },
    fromScale: { default: 1.08, min: 0.8, max: 1.6 }, blur: { default: 5, min: 0, max: 30 },
  },
  seenIn: "turn beat 1.20-1.33 s (motion only in frames 73-80, then a still tilted hold)",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => {
    const k = ease.outCubic(prog(t, 0, p.frames));
    return { shutter: p.shutter, rotate: lerp(p.fromRotate, p.rest, k), skewX: lerp(p.fromSkew, 0, k), scale: lerp(p.fromScale, 1, k), blur: lerp(p.blur, 0, k) };
  },
};
export default m;
