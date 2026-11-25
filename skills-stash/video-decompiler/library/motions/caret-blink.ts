import { Motion } from "../lib/core";
// A text caret: solid while typing, then blinking on a fixed period.
export const meta = {
  name: "caret-blink", kind: "emphasis", summary: "caret solid while typing, then on/off blink",
  function: "continuity",
  evidence: "a live cursor says the tool is still running and ready",
  params: { period: { default: 32, min: 8, max: 90, note: "frames per on+off" }, duty: { default: 0.55, min: 0.1, max: 0.9 } },
  seenIn: "terminal 4.0-7.2 s and search field 9.8-10.8 s",
};
const m: Motion = { meta: meta as any, frames: () => 0, at: (t, _b, p) => ({ opacity: t < 0 ? 1 : ((t % p.period) / p.period < p.duty ? 1 : 0) }) };
export default m;
