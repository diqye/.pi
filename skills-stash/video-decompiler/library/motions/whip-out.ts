import { Motion, ease, frameOf, prog } from "../lib/core";
// Accelerates off one side; the motion blur is what reads.
export const meta = {
  name: "whip-out", kind: "exit", summary: "accelerating slide off frame (cubic ease-in), heavy motion blur",
  function: "pace",
  evidence: "the subject changes with no dead frame: the benefit leaves left as the list arrives from the right",
  params: {
    shutter: { default: 1.4, min: 0, max: 8, note: "frames of exposure for motion blur" },
    frames: { default: 9, min: 4, max: 24 }, distance: { default: 1.25, min: 0.3, max: 2, note: "frame widths or heights" },
    direction: { default: "left", options: ["left", "right", "up", "down"] },
  },
  seenIn: "second benefit exit 14.25-14.40 s (right edge -264 px at 5 frames, -1078 px at 8); list exit up 17.05-17.20 s",
};
const dir = (d: string) => (d === "left" ? [-1, 0] : d === "right" ? [1, 0] : d === "up" ? [0, -1] : [0, 1]);
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, b, p) => {
    const k = ease.inCubic(prog(t, 0, p.frames));
    const [dx, dy] = dir(p.direction);
    const f = frameOf(b);
    return { shutter: p.shutter, x: dx * k * p.distance * f.w, y: dy * k * p.distance * f.h };
  },
};
export default m;
