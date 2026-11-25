// A hard cut: the outgoing beat's last frame is followed by the incoming beat's first.
export const meta = {
  name: "cut", kind: "transition", summary: "hard cut, no overlap",
  function: "pace",
  evidence: "one hard cut per clause of the opening sentence; the tone flips on the negation",
  params: {},
  seenIn: "0-1.2-1.93 s (hook, turn, claim), 7.20 s (demo to pile), 10.80 s (result to benefit)",
};
export default { meta: meta as any, frames: () => ({ exit: 0, enter: 0, gap: 0 }) };
