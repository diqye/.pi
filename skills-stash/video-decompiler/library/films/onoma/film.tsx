// Onoma: a launch film for a made-up app that makes sound from a typed line (BOARD.md).
// One component reads the frame; everything else is a plain function of it. `offset` (frames) lets
// `vd render --from A --to B` draw only a stretch.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { C, CLOCK, FB, FONTS, TM, clamp01, inOutCubic, lerp, outCubic, rnd } from "./kit/core";
import { MOODS, field, grain, type Mood } from "./kit/field";
import { BOLT_F, PULSES, line } from "./line";
import { words } from "./words";
import { product } from "./product";

const S = score as unknown as { width: number; height: number };
export const FPS = CLOCK.FPS, W = S.width, H = S.height, FRAMES = CLOCK.BEATS * CLOCK.FB;    // the clock sound.py wrote
const P = TM.PARTS;                                     // the parts' first beats, as in BOARD.md's beats table

/** the framings: [beat, the point the frame is centred on, how close, frames the move takes (20 if not given)] */
const CAM: number[][] = [
  [0, 960, 430, 1.25], [TM.RAIN, 960, 540, 1, 26],                                                          // "rain." large, then wide as it falls
  [P.thunder, 640, 430, 1.2], [TM.BOLT, 960, 540, 1, 14],                                                   // "thunder.", then the bolt
  [P.steps, 600, 650, 1.2], [TM.STEPS[0] + 0.3, 1300, 660, 1.15, 81],                                       // "footsteps.", then walking with them
  [P.clap, 1100, 500, 1.05, 20], [TM.CLAPS[0], 800, 610, 1.2, 9], [TM.CLAPS[0] + 0.4, 1140, 560, 1.15, 56],   // the clap, then along its echoes
  [TM.PULSES[0], 1040, 735, 1.7, 26],                                                                       // close on the heartbeat
  [P.hush, 960, 620, 1.15, 24], [TM.HUSH + 0.3, 960, 720, 1.35, 60],                                        // "hush.", then in on the point
  [P.name, 960, 690, 1.3, 26], [P.ask, 960, 320, 1.28, 26], [P.ask + 1, 960, 310, 1.4, 80],                 // the name; the bar, pushing in
  [P.mix, 960, 540, 1.28, 24], [P.mix + 2, 960, 560, 1.36, 180], [P.take, 960, 590, 1.22, 24], [P.end, 960, 690, 1.3, 28],   // the mix; the one line; the end
];
const CREEP = 0.008;
function camera(f: number) {
  let c = [CAM[0][1], CAM[0][2], CAM[0][3]], since = CAM[0][0] * FB;
  for (let i = 1; i < CAM.length; i++) {
    const start = CAM[i][0] * FB;
    if (f < start - 1) break;
    c[2] *= 1 + (CREEP * (start - since)) / FPS;                            // the creep it gathered is where the next move starts from
    const k = inOutCubic(clamp01((f - start + 1) / (CAM[i][4] ?? 20)));     // a camera has weight: it eases in and out
    c = [lerp(c[0], CAM[i][1], k), lerp(c[1], CAM[i][2], k), lerp(c[2], CAM[i][3], k)];
    since = start;
  }
  const a = f - BOLT_F, shake = a >= 0 && a < 26 ? 22 * Math.exp(-a / 7) : 0;       // the thunder shakes it
  return [c[0] + (rnd(f) - 0.5) * shake, c[1] + (rnd(f + 9) - 0.5) * shake, c[2] * (1 + (CREEP * Math.max(0, f - since)) / FPS)];
}

/** the air: [beat, mood, frames to get there]. It takes the colour of the sound being made. */
const AIR: [number, string, number][] = [
  [0, "dark", 1], [P.rain + 0.4, "rain", 40], [TM.BOLT - 0.4, "thunder", 14], [P.steps, "steps", 30], [P.clap, "echo", 30], [P.heart, "heart", 30],
  [TM.HUSH - 0.4, "dark", 44], [P.name, "warm", 36],
];
function air(f: number): [Mood, number][] {
  const w: Record<string, number> = { dark: 1 };
  for (const [b, name, n] of AIR) {
    const k = outCubic(clamp01((f - b * FB + 1) / n));
    if (k <= 0) break;
    for (const key of Object.keys(w)) w[key] *= 1 - k;
    w[name] = (w[name] ?? 0) + k;
  }
  return Object.entries(w).map(([name, v]) => [MOODS[name], v] as [Mood, number]);
}

export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset;
  const [cx, cy, z] = camera(f);
  const flash = f >= BOLT_F ? 0.78 * Math.exp(-(f - BOLT_F) / 5) : 0;                // the bolt lights the whole room
  const beat = Math.max(0, ...PULSES.filter((p, i) => i % 2 === 0).map((p) => (f >= p && f < p + 40 ? Math.exp(-(f - p) / 11) * Math.min(1, (f - p + 1) / 3) : 0)));
  return (
    <AbsoluteFill style={{ background: C.night }}>
      <style>{FONTS}</style>
      {field(f, air(f), W, H, -(cx - W / 2) * 0.14 * z, -(cy - H / 2) * 0.14 * z)}
      {beat > 0.02 ? <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, background: "radial-gradient(closest-side, rgba(200, 40, 50, 0.5), rgba(200, 40, 50, 0))", opacity: beat * 0.7 }} /> : null}
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${(W / 2 - cx * z).toFixed(3)}px, ${(H / 2 - cy * z).toFixed(3)}px) scale(${z.toFixed(5)})` }}>
        {line(f)}
        {f < P.name * FB ? words(f) : null}
        {f >= P.name * FB ? product(f) : null}
      </div>
      {flash > 0.01 ? <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, background: "#E9E4FF", opacity: flash }} /> : null}
      {finish ? grain(f, W, H) : null}
    </AbsoluteFill>
  );
}
