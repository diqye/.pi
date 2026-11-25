// What a transition that draws both beats needs: its length in seconds against the film's frame rate, and the props a Join gets.
export const fpsOf = (p: any): number => p.fps ?? 60;
// The join's length in frames, from its duration in seconds, at the film's frame rate.
export const joinFrames = (p: any, seconds: number = p.dur): number => Math.max(2, Math.round(seconds * fpsOf(p)));

export type JoinProps = {
  from: any; to: any;      // the two beats, live, as nodes (each may be drawn many times)
  p: number;               // 0..1 across the join
  t: number;               // frames since the join began
  frames: number;          // the join's whole length
  fps: number;
  params: Record<string, any>;
  style: any; W: number; H: number;
  toneFrom: any; toneTo: any;
  look?: any;              // the outgoing layout's headline lines, when it has one
  earlier?: { id: string; node: any; tone: any }[]; // every beat so far, frozen at its end, oldest first; the outgoing beat is last
};

// A frame-sized layer. Every layer a join stacks is this size so scene nodes keep their layout.
export const layer = { position: "absolute", left: 0, top: 0 } as const;
