// A radial rush built from stacked, scaled copies: the last scene races past the lens and the next one lands under it.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "zoom-burst", kind: "transition",
  summary: "a radial blur rush built from stacked scaled copies, cut at its peak, that lands inside the next scene and settles",
  function: "pace: a change of scene at speed, the energy of one idea thrown into the next",
  params: {
    dur: { default: 0.72, min: 0.2, max: 2.5, note: "seconds, the whole join" },
    copies: { default: 18, min: 3, max: 30, note: "stacked copies at the peak of the rush; fewer at the ends of it" },
    cx: { default: 0.5, min: 0, max: 1, note: "where the rush points, of the frame width" },
    cy: { default: 0.5, min: 0, max: 1, note: "of the frame height" },
    reach: { default: 2.6, min: 1.1, max: 6, note: "how far the outgoing scene grows before the cut" },
    spread: { default: 0.032, min: 0, max: 0.2, note: "scale gap between neighbouring copies at the peak" },
    land: { default: 1.32, min: 1, max: 2.4, note: "how large the next scene starts, before it settles to rest" },
    cut: { default: 0.4, min: 0.2, max: 0.8, note: "share of the join before the cut" },
    soft: { default: 0.008, min: 0, max: 0.03, note: "blur at the peak of the rush, of the shorter frame side" },
  },
  seenIn: "study of a product film: a wall of pictures rushes into a radial blur and lands in a room, about 25.5 s",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
