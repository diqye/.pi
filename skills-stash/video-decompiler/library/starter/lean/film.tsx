// The film: a pure function of the time. Its timing is data: every beat, word and caption comes from score.json, so a
// new recording or a moved line changes the score, not this file. Replace the shots; keep the score as the clock.
// `offset` (frames) lets `vd render --from A --to B` draw only a stretch of it.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { C, Drift, FACE, Faces, Grain, Halo, MARGIN, Words, k01, lerp } from "./kit/base";

type Beat = { id: string; from: number; to: number; shot: string; words?: string; job?: "open" | "statement" | "proof" | "running"; key?: string[]; number?: string };
const S = score as unknown as { fps: number; width: number; height: number; duration: number; beats: Beat[] };
export const FPS = S.fps, W = S.width, H = S.height, FRAMES = Math.round(S.duration * S.fps);

/** a ground with depth: far ridge, a light in the world, a near shelf. Layers drift at their own rates (parallax). */
function Ground({ t, from }: { t: number; from: number }) {
  const ridge = (y: number, amp: number, seed: number) => {
    const pts = Array.from({ length: 9 }, (_, i) => `${(i / 8) * W * 1.2 - W * 0.1},${y + Math.sin(i * 1.7 + seed) * amp}`);
    return `M ${-W * 0.1},${H * 1.1} L ${pts.join(" L ")} L ${W * 1.1},${H * 1.1} Z`;
  };
  return (
    <>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${C.ground} 0%, ${C.ground2} 70%, ${C.far} 100%)` }} />
      <Drift t={t} from={from} depth={0.5}><Halo x={W * 0.72} y={H * 0.3} r={H * 0.42} /></Drift>
      <Drift t={t} from={from} depth={0.7} dx={-6}>
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={W} height={H}><path d={ridge(H * 0.62, H * 0.05, 1)} fill={C.far} /></svg>
      </Drift>
      <Drift t={t} from={from} depth={1.2} dx={-14}>
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={W} height={H}><path d={ridge(H * 0.78, H * 0.04, 4)} fill={C.mid} /></svg>
      </Drift>
    </>
  );
}

/** the one thing the film follows: a lit card with a shadow that sits apart from it (it has a height) */
function Thing({ t, from, to, x, y, s }: { t: number; from: number; to: number; x: number; y: number; s: number }) {
  const land = k01(t, from, from + 0.6, "spring");
  const lift = lerp(H * 0.12, 0, land);
  const w = H * 0.34 * s, h = H * 0.22 * s;
  return (
    <Drift t={t} from={from} depth={1.6} dx={-20}>
      <div style={{ position: "absolute", left: x - w / 2 + lift * 0.3, top: y + h * 0.62, width: w, height: h * 0.18, borderRadius: "50%", background: "rgba(3,4,12,0.55)", filter: `blur(${10 + lift * 0.15}px)` }} />
      <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2 - lift, width: w, height: h, borderRadius: h * 0.12, background: `linear-gradient(160deg, ${C.accent} 0%, ${C.accent2} 100%)`, boxShadow: `inset 0 ${h * 0.04}px 0 rgba(255,255,255,0.35)`, opacity: k01(t, from - 0.05, from + 0.15) * (1 - k01(t, to, to + 0.2)) }} />
    </Drift>
  );
}

/** one beat's shot: the starter's four shot kinds. Replace them with this film's own. */
function Shot({ b, t }: { b: Beat; t: number }) {
  const mid = b.shot === "wide" ? 0.38 : b.shot === "close" ? 1.6 : 1;
  return (
    <AbsoluteFill>
      <Ground t={t} from={b.from} />
      {b.shot === "number" && b.number ? (
        <Drift t={t} from={b.from} depth={1.4}>
          <div style={{ position: "absolute", left: W * MARGIN, width: W * (1 - 2 * MARGIN), top: H * 0.22, textAlign: "center", fontFamily: FACE, fontWeight: 900, fontSize: H * 0.3, color: C.paper,
            opacity: k01(t, b.from, b.from + 0.3), textShadow: `0 ${H * 0.012}px 0 ${C.ink}` }}>{b.number}</div>
        </Drift>
      ) : (
        <Thing t={t} from={b.from} to={b.to} x={W * (b.shot === "wide" ? 0.62 : 0.6)} y={H * 0.5} s={mid} />
      )}
    </AbsoluteFill>
  );
}

/** `finish` false leaves out the grain: `vd look` draws composition film-look so its masks can see under it */
export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset;
  const t = f / FPS;
  const b = S.beats.find((x) => t >= x.from && t < x.to) ?? S.beats[S.beats.length - 1];
  return (
    <AbsoluteFill style={{ background: C.ground }}>
      <Faces />
      <Shot b={b} t={t} />
      {S.beats.filter((x) => x.words).map((x) => (
        <Words key={x.id} t={t} from={x.from} to={x.to} text={x.words!} job={x.job ?? "running"} accent={x.key ?? []} w={W} h={H}
          at={x.job === "open" || x.job === "statement" ? "middle" : "low"} />
      ))}
      {finish ? <Grain f={f} w={W} h={H} /> : null}
    </AbsoluteFill>
  );
}
