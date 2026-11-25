// The incoming beat fades up over the outgoing one, which holds: two different scenes joined without a jump.
export const meta = {
  name: "dissolve", kind: "transition", summary: "the next beat fades in over the last, which holds still underneath",
  function: "continuity between ideas",
  evidence: "a mix's weakest join was a hard cut from a dense page to a nearly empty frame",
  params: { frames: { default: 14, min: 4, max: 60 } },
  seenIn: "the joins of an earlier film",
};
export default {
  meta: meta as any,
  fadeWhole: true,
  frames: (p: any) => ({ exit: p.frames, enter: p.frames, gap: -p.frames }),
};
