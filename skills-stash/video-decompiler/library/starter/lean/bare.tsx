// A bare page film: the frame, the score's clock, the finish and nothing else, for a film that is a diagram (a ring, a
// board, a chart). Draw it in Film; every value a function of the time. `offset` (frames) lets `vd render --from A --to B`
// draw only a stretch; `finish` false leaves out the grain (vd look draws film-look so its masks can see under it).
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { C, Grain } from "./kit/base";

const S = score as unknown as { fps: number; width: number; height: number; duration: number };
export const FPS = S.fps, W = S.width, H = S.height, FRAMES = Math.round(S.duration * S.fps);

export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset, t = f / FPS;
  return (
    <AbsoluteFill style={{ background: C.ground }}>
      {/* the film, drawn from t */}
      {finish ? <Grain f={f} w={W} h={H} /> : null}
    </AbsoluteFill>
  );
}
