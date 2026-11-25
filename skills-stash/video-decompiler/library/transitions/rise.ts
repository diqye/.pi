// Vertical whip: the outgoing beat shoots up out of frame, cut, the incoming beat rises from below and brakes.
export const meta = {
  name: "rise", kind: "transition", summary: "motion-blurred exit upward, cut, entrance from below",
  function: "pace",
  evidence: "two vertical whips in a row make the closing beats read as one run",
  params: {
    exitFrames: { default: 9, min: 4, max: 24 }, enterFrames: { default: 10, min: 4, max: 30 },
    distance: { default: 1444, min: 200, max: 2400, note: "px the incoming beat rises" },
  },
  seenIn: "platform list to license 17.05-17.37 s; license to intro 17.85-18.17 s (top edge +312 px at 4 frames, +96 at 6, +12 at 8)",
};
export default {
  meta: meta as any,
  frames: (p: any) => ({ exit: p.exitFrames, enter: p.enterFrames, gap: 0 }),
  exit: (p: any) => ({ motion: "whip-out", params: { frames: p.exitFrames, direction: "up" } }),
  enter: (p: any) => ({ motion: "whip-in", params: { frames: p.enterFrames, direction: "down", distance: p.distance } }),
};
