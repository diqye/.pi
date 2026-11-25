// The camera pulls back until every earlier beat is on one canvas, joined by lines, then pushes into the next one.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "recap-wall", kind: "transition",
  summary: "the camera pulls back so every earlier beat sits on one canvas joined by lines, holds there while the lines draw, then pushes into the next scene or an earlier one",
  function: "continuity and proof: the viewer sees that everything so far was one piece of work",
  params: {
    dur: { default: 3.0, min: 1, max: 10, note: "seconds, the whole join" },
    pull: { default: 0.3, min: 0.1, max: 0.5, note: "share of the join spent pulling back" },
    push: { default: 0.68, min: 0.5, max: 0.92, note: "where in the join the push in starts" },
    into: { default: "next", note: "the panel the camera lands in: next, or an earlier beat's id" },
    gap: { default: 0.26, min: 0.05, max: 1, note: "space between panels, of the frame width" },
    loose: { default: 0.1, min: 0, max: 0.5, note: "how far panels sit off the grid, of the gap" },
    fit: { default: 0.9, min: 0.5, max: 1, note: "how much of the frame the wall takes" },
    drift: { default: 0.05, min: 0, max: 0.25, note: "how much the camera keeps creeping in while it holds on the wall" },
    line: { default: 0.0024, min: 0.0005, max: 0.012, note: "line weight, of the shorter frame side" },
    ink: { default: "accent", note: "tone or colour token of the lines" },
    ground: { default: "", note: "colour token of the canvas; empty takes the next beat's ground" },
    corner: { default: 26, min: 0, max: 80, note: "corner radius of a panel on the wall, in px at the panel's full size" },
    drawDur: { default: 0.4, min: 0.1, max: 2, note: "seconds a line takes to draw" },
    labels: { default: null, note: "optional labels by beat id: { id: text }" },
    ease: { default: [0.66, 0, 0.14, 1], note: "the camera's curve" },
  },
  seenIn: "study of a studio film: the camera pulls back to show every earlier section joined by lines, then pushes into one, about 28.3 to 31 s",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
