import { Motion, ease, prog, frameOf } from "../lib/core";
// Arrives from off one side and brakes hard; the mirror of whip-out.
export const meta = {
  name: "whip-in", kind: "enter", summary: "fast slide in from off frame on a cubic ease-out, heavy motion blur",
  function: "pace",
  evidence: "the new subject brakes into place within 11 frames of the cut",
  params: {
    shutter: { default: 1.4, min: 0, max: 8, note: "frames of exposure for motion blur" },
    frames: { default: 11, min: 4, max: 30 }, distance: { default: 1600, min: 100, max: 2400, note: "px" },
    direction: { default: "right", options: ["left", "right", "up", "down"] },
  },
  seenIn: "platform list 14.40-14.58 s (+418 px at 4 frames, +8 px at 8); license and intro rise from below 17.20-17.37 s",
};
const dir = (d: string) => (d === "left" ? [-1, 0] : d === "right" ? [1, 0] : d === "up" ? [0, -1] : [0, 1]);
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, b, p) => {
    const k = 1 - ease.outCubic(prog(t, 0, p.frames));
    const [dx, dy] = dir(p.direction);
    const f = frameOf(b);
    return { shutter: p.shutter, x: (dx * k * p.distance * f.w) / 1920, y: (dy * k * p.distance * f.h) / 1080, opacity: t < 0 ? 0 : 1 };
  },
};
export default m;
