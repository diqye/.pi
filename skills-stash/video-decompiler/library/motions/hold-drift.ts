import { Motion } from "../lib/core";
// A slow push on a resting element, so a hold never reads as a freeze.
export const meta = {
  name: "hold-drift", kind: "hold", summary: "slow linear scale push while an element rests",
  function: "mood",
  evidence: "a held name keeps creeping closer, so a 3 s hold never reads as a freeze",
  params: { rate: { default: 0.0003, min: 0, max: 0.002, note: "scale gained per frame" } },
  seenIn: "end card 20.8-24.0 s (the name grows about 5% over 3 s, ink box measured every 6 frames); intro 18.4-20.0 s",
};
const m: Motion = { meta: meta as any, frames: () => 0, at: (t, _b, p) => ({ scale: 1 + Math.max(0, t) * p.rate }) };
export default m;
