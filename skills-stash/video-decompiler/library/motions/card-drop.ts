import { Motion, ease, prog, lerp, hash } from "../lib/core";
// A card falls toward the table from above the lens: big and high, then small and settled, with a turn.
// p.i (the card's index) only varies the turn and drift.
export const meta = {
  name: "card-drop", kind: "enter", summary: "falls in from above the lens: oversized and high to resting, with a turn",
  function: "demonstration",
  evidence: "the viewer's own items arrive as a messy pile: the before state of the transformation",
  params: {
    frames: { default: 16, min: 6, max: 40 }, from: { default: 1.9, min: 1, max: 4 }, lift: { default: 280, min: 0, max: 900, note: "px above rest" },
    turn: { default: 18, min: 0, max: 60, note: "deg of extra turn" },
  },
  seenIn: "input pile 7.20-8.00 s, one card about every 3.3 frames",
};
const m: Motion = {
  meta: meta as any, frames: (p) => p.frames,
  at: (t, _b, p) => {
    if (t < 0) return { opacity: 0, scale: p.from };
    const k = ease.outCubic(prog(t, 0, p.frames));
    const i = p.i ?? 0;
    const sgn = hash(i, 3) > 0.5 ? 1 : -1;
    return { scale: lerp(p.from, 1, k), y: lerp(-p.lift, 0, k), x: lerp(sgn * 90 * hash(i, 5), 0, k), rotate: lerp(sgn * p.turn, 0, k), opacity: Math.min(1, t / 2) };
  },
};
export default m;
