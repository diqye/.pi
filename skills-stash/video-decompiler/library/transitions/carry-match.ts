// The last thing in one scene becomes the first thing in the next, by shape and by place.
// One move flies a card between two rectangles and another morphs shapes; this joins them and owns the cut.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "carry-match", kind: "transition",
  summary: "give it the end state of a thing in one scene and its start state in the next, and it moves the thing across the join by place and by shape while the scenes change behind it",
  function: "continuity: the viewer follows one thing across the cut, so two scenes read as one thought",
  params: {
    dur: { default: 1.05, min: 0.3, max: 4, note: "seconds, the whole join" },
    a: { default: null, note: "where it ends in the outgoing scene: { t: rect, capsule, circle, ellipse or heart, at: [x, y], w, h, r }; at, w and h are fractions of the frame; r is a fraction of its shorter side" },
    b: { default: null, note: "where it starts in the next scene, the same fields" },
    fill: { default: "accent", note: "colour token, or any CSS colour, of the thing" },
    fillB: { default: "", note: "colour it turns on the way; empty keeps fill" },
    aContent: { default: null, note: "what it shows at the start: { text, role, size, ink } or { src }" },
    bContent: { default: null, note: "what it shows at the end" },
    arc: { default: 0.16, min: -0.6, max: 0.6, note: "how far the path bows off the straight line, of the distance travelled" },
    cut: { default: 0.5, min: 0.2, max: 0.8, note: "where in the join the scenes change behind it" },
    fadeBy: { default: 0, min: 0, max: 0.3, note: "share of the join at the end over which it fades; leave at 0 when the layout leaves the thing out while it's being carried (the joining prop), so the swap to the scene's own copy is invisible" },
    ease: { default: [0.62, 0, 0.14, 1], note: "the move's curve" },
  },
  seenIn: "built on a carry and a morph of outlines, so the shape and the place land together",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
