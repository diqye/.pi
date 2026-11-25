// The outgoing beat tips and collapses into the centre; the incoming beat grows out of the same point.
export const meta = {
  name: "collapse", kind: "transition", summary: "shrink to a point, then grow the next beat from that point",
  function: "continuity between ideas",
  evidence: "two benefits share one point on screen, so they read as one thought",
  params: { exitFrames: { default: 21, min: 6, max: 40 }, enterFrames: { default: 21, min: 6, max: 48 } },
  seenIn: "first benefit to second benefit 12.43-13.15 s",
};
export default {
  meta: meta as any,
  frames: (p: any) => ({ exit: p.exitFrames, enter: p.enterFrames, gap: 0 }),
  exit: (p: any) => ({ motion: "shrink-to-point", params: { frames: p.exitFrames - 2 } }),
  enter: (p: any) => ({ motion: "grow-from-point", params: { frames: p.enterFrames } }),
};
