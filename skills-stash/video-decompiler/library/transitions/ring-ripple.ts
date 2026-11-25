// Concentric rings run out from a point, each showing more of the next scene through it, until they close up over the frame.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "ring-ripple", kind: "transition",
  summary: "concentric rings expand from a point, each one a window onto the next scene, and close up until the next scene fills the frame",
  function: "continuity: the next idea spreads out from a point the viewer is already looking at",
  params: {
    dur: { default: 1.05, min: 0.3, max: 4, note: "seconds, the whole join" },
    rings: { default: 5, min: 1, max: 12, note: "one ring is a plain circle wipe" },
    cx: { default: 0.5, min: 0, max: 1, note: "the point, of the frame width" },
    cy: { default: 0.5, min: 0, max: 1, note: "of the frame height" },
    stagger: { default: 0.42, min: 0, max: 0.8, note: "share of the join spent launching the rings" },
    flood: { default: 0.44, min: 0.2, max: 0.9, note: "where in the join the last ring starts filling the frame from the point out" },
    thick: { default: 0.2, min: 0.005, max: 0.6, note: "a ring's width while it travels, of its radius" },
    refract: { default: 0.05, min: 0, max: 0.2, note: "how magnified the next scene is inside each ring, so the rings read as glass" },
    line: { default: 0.0016, min: 0, max: 0.01, note: "the thin rule on a ring's edge, of the shorter frame side" },
    ink: { default: "", note: "colour token for the rule; empty takes the next beat's ink" },
  },
  seenIn: "study of two product films: soft concentric rings opening behind a line of type, about 12.3 s, and circle wipes between scenes",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
