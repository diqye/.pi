import { Motion, ease, easeBy, prog, lerp } from "../lib/core";
// Comes in from slightly larger and soft; the motion blur draws the echoes of its larger self.
export const meta = {
  name: "ghost-zoom", kind: "enter", summary: "quick zoom-down from oversized and soft, with motion-blur echoes",
  function: "reveal",
  evidence: "the promise arrives as an after-image of itself, softer than the hard cut before it",
  params: { frames: { default: 6, min: 3, max: 24 }, from: { default: 2.2, min: 1, max: 3 }, ease: { default: "outQuad", options: ["outQuad", "outCubic", "outExpo"] }, blur: { default: 2, min: 0, max: 20 }, shutter: { default: 3, min: 0, max: 8, note: "frames of exposure: long, so the echoes separate" } },
  seenIn: "claim beat 1.93-2.03 s (motion in frames 117-122)",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => {
    const k = easeBy(p.ease)(prog(t, 0, p.frames));
    return { scale: lerp(p.from, 1, k), blur: lerp(p.blur, 0, k), opacity: t < 0 ? 0 : lerp(0.5, 1, Math.min(1, k * 1.5)), shutter: p.shutter } as any;
  },
};
export default m;
