import { Motion, prog } from "../lib/core";
// Holds as an outline, then fills solid in a couple of frames. The type that draws it reads the pose's fill.
export const meta = {
  name: "outline-to-fill", kind: "emphasis", summary: "outline type that snaps to a solid fill",
  function: "transformation",
  evidence: "the outline goes solid as the benefit lands: the drawn thing becomes real",
  params: { at: { default: 24, min: 0, max: 120, note: "frames after the element starts" }, frames: { default: 2, min: 1, max: 20 } },
  seenIn: "first benefit beat 11.20 s, as the zoom lands",
};
const m: Motion = { meta: meta as any, frames: (p) => p.at + p.frames, at: (t, _b, p) => ({ fill: prog(t, p.at, p.frames) } as any) };
export default m;
