// The picture's columns stretch and melt down the frame until nothing is left, and the next scene is there behind them.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "smear", kind: "transition",
  summary: "a picture's columns stretch downward and melt off the frame on staggered delays, uncovering the next scene behind them",
  function: "pace and material: a picture that gives way like something soft, so the change of scene feels physical",
  params: {
    dur: { default: 0.8, min: 0.25, max: 3, note: "seconds, the whole join" },
    cols: { default: 110, min: 8, max: 200, note: "columns across; more is finer streaks and more cost" },
    stretch: { default: 8, min: 1, max: 24, note: "how long a column gets before it falls" },
    drop: { default: 1.25, min: 1, max: 3, note: "how far a column's top falls, of the frame height" },
    stagger: { default: 0.55, min: 0, max: 0.9, note: "share of the join spent spreading the columns' starts" },
    wander: { default: 4, min: 0.5, max: 30, note: "how lumpy the melt front is: low is broad waves, high is fine drips" },
    feather: { default: 0.1, min: 0, max: 0.5, note: "how soft each column's falling top edge is, of the frame height" },
    pull: { default: 0.05, min: 0, max: 0.4, note: "how far the next scene rises as it's uncovered, of the frame height" },
    seed: { default: 3, min: 0, max: 1000 },
  },
  seenIn: "study of a product film: a word on a soft ground stretches into vertical streaks and drops away, about 4.8 s",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
