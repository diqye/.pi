// Whip pan: the outgoing beat accelerates off one side, hard cut, the incoming beat brakes in from the other.
export const meta = {
  name: "whip", kind: "transition", summary: "motion-blurred slide out one side, cut, slide in from the other",
  function: "pace",
  evidence: "a horizontal whip moves from benefits to coverage without a pause",
  params: {
    exitFrames: { default: 9, min: 4, max: 24 }, enterFrames: { default: 11, min: 4, max: 30 },
    direction: { default: "left", options: ["left", "right", "up", "down"], note: "the way the picture travels" },
    distance: { default: 1600, min: 200, max: 2400, note: "px the incoming beat travels" },
  },
  seenIn: "second benefit to platform list 14.25-14.58 s",
};
const opposite: Record<string, string> = { left: "right", right: "left", up: "down", down: "up" };
export default {
  meta: meta as any,
  frames: (p: any) => ({ exit: p.exitFrames, enter: p.enterFrames, gap: 0 }),
  exit: (p: any) => ({ motion: "whip-out", params: { frames: p.exitFrames, direction: p.direction } }),
  enter: (p: any) => ({ motion: "whip-in", params: { frames: p.enterFrames, direction: opposite[p.direction], distance: p.distance } }),
};
