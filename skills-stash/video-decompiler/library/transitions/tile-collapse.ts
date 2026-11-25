// A picture breaks into tiles that fly to a point and become a ring of dots; the dots then open onto whatever comes next.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "tile-collapse", kind: "transition",
  summary: "a picture breaks into a grid of tiles on staggered delays, the tiles fly to a point and shrink to a ring of dots, and the ring opens onto the next scene or stays for the next part to take over",
  function: "continuity: a whole picture reduced to something small enough to carry, so the next idea starts from what's left of the last",
  params: {
    dur: { default: 1.6, min: 0.5, max: 5, note: "seconds, the whole join" },
    cols: { default: 9, min: 2, max: 24, note: "tiles across" },
    rows: { default: 0, min: 0, max: 24, note: "tiles down; 0 follows the frame so tiles stay near square" },
    cx: { default: 0.5, min: 0, max: 1, note: "the point, of the frame width" },
    cy: { default: 0.5, min: 0, max: 1, note: "the point, of the frame height" },
    stagger: { default: 0.5, min: 0, max: 0.85, note: "share of the flight window spent spreading the tiles' starts" },
    order: { default: "scatter", options: ["scatter", "far-first", "near-first"], note: "which tiles leave first" },
    lift: { default: 6, min: 0, max: 30, note: "tiles that pop out of the picture before the rest break" },
    swirl: { default: 0.7, min: -4, max: 4, note: "radians the paths bend around the point" },
    dots: { default: 7, min: 3, max: 18, note: "dots in the ring" },
    ringR: { default: 0.042, min: 0.01, max: 0.2, note: "ring radius, of the shorter frame side" },
    dotR: { default: 0.0085, min: 0.002, max: 0.04, note: "dot radius, of the shorter frame side" },
    spin: { default: 1.6, min: -8, max: 8, note: "turns of the ring across the join; it accelerates so the ring never sits still" },
    ground: { default: "", note: "colour token behind the flying tiles; empty takes the next beat's ground" },
    ink: { default: "", note: "dot colour token; empty picks what reads on the ground" },
    handoff: { default: "open", options: ["open", "hold"], note: "open: the ring opens as a circle onto the next scene; hold: the dots stay till the join ends so the next part can start from them (see ringState)" },
    ease: { default: [0.62, 0.02, 0.16, 1], note: "the flight's curve" },
  },
  seenIn: "study of a product film: a full-bleed picture breaks into tiles that collapse to a spinner, about 3.4 to 5.1 s",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
