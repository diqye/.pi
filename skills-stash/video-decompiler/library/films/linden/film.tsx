// Linden Library: a rebrand film that is one move of the camera, outward (BOARD.md). One component reads the frame;
// everything else is a plain function of it. `offset` (frames) lets `vd render --from A --to B` draw only a stretch.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { CLOCK, TIMES as TM } from "./kit/times.gen";
import { C, FB, FONTS, clamp01, inOutCubic, lerp } from "./kit/core";
import { LAST, SLOTS, world } from "./levels";

const S = score as unknown as { width: number; height: number };
export const FPS = CLOCK.FPS, W = S.width, H = S.height, FRAMES = CLOCK.BEATS * CLOCK.FB;    // the clock sound.py wrote

type View = { x: number; y: number; w: number };                    // what the frame shows of a world, in that world's units (16 by 9)
const FULL: View = { x: 0, y: 0, w: 1920 };
/** the camera's path: [from beat, to beat, the world it is in, where it ends, the tilt it ends with (degrees about x and y)].
 *  Each stretch starts where the last one ended; when the world changes, it starts framed on the slot that holds the world before. */
const PATH: [number, number, number, View, [number, number]][] = [
  [0, TM.LABEL - 0.1, 1, { x: 782, y: 210, w: 420 }, [0, 0]],       // inside the paper, travelling up it
  [TM.LABEL - 0.1, TM.OUT1, 1, { x: 772, y: 204, w: 440 }, [0, 0]],   // the label is put down; the view holds on it
  [TM.OUT1, TM.BOOK, 1, FULL, [0, 0]],                                // out: it is a book
  [TM.BOOK, TM.OUT2, 1, { x: 34, y: 19, w: 1852 }, [0, 0]],
  [TM.OUT2, TM.WALL, 2, FULL, [0, 0]],                                // out: one of a wall of books
  [TM.WALL, TM.OUT3, 2, FULL, [0, 0]],                                // the camera tilts and travels across the wall (ACROSS, below)
  [TM.OUT3, TM.CARD, 3, FULL, [0, 0]],                                // out: the wall is on a card
  [TM.CARD, TM.OUT4, 3, { x: 40, y: 22, w: 1840 }, [0, 0]],
  [TM.OUT4, TM.LANDS[0], 4, FULL, [0, 0]], [TM.LANDS[0], TM.LANDS[1], 5, FULL, [0, 0]], [TM.LANDS[1], TM.LANDS[2], 6, FULL, [0, 0]],
  [TM.LANDS[2], TM.LANDS[3], 7, FULL, [0, 0]], [TM.LANDS[3], TM.LANDS[4], 8, FULL, [0, 0]],
  [TM.LANDS[4], TM.END, LAST, FULL, [0, 0]],                           // out: all of it is in the mark's window
  [TM.END, CLOCK.BEATS + 1, LAST, { x: 150, y: 60, w: 1620 }, [0, 0]],   // the last creep runs a beat past the end, so it never stops
];
const START: View = { x: 806, y: 372, w: 372 };
/** across the wall: four framings [middle x, middle y, width, tilt about x, tilt about y] and one smooth path through them */
const ACROSS = [[960, 540, 1920, 0, 0], [1150, 520, 1500, 20, -10], [1180, 640, 1440, 15, 9], [960, 540, 1920, 0, 0]];      // every framing holds the block of words whole
function across(raw: number) {
  const e = 0.45 * raw + 0.55 * inOutCubic(raw), p = Math.min(2.9999, e * 3), j = Math.floor(p), t = p - j;      // slower at the two ends, never still between
  const P = (n: number) => ACROSS[Math.max(0, Math.min(3, n))].map((v, q) => (q === 2 ? Math.log(v) : v));
  const a = P(j - 1), b = P(j), c = P(j + 1), d = P(j + 2);
  const o = b.map((_, q) => 0.5 * (2 * b[q] + (c[q] - a[q]) * t + (2 * a[q] - 5 * b[q] + 4 * c[q] - d[q]) * t * t + (3 * b[q] - a[q] - 3 * c[q] + d[q]) * t * t * t));
  const w = Math.exp(o[2]);
  return { K: 2, v: { x: o[0] - w / 2, y: o[1] - (w * 9) / 32, w }, tilt: [o[3], o[4]], un: 0 };
}
/** the view a stretch starts from */
function from(i: number): { v: View; t: [number, number] } {
  if (i === 0) return { v: START, t: [0, 0] };
  const p = PATH[i - 1], v = p[3];
  if (PATH[i][2] === p[2]) return { v, t: p[4] };
  const s = SLOTS[PATH[i][2]], k = s.w / 1920;                        // the same view, in the units of the world that holds it
  return { v: { x: s.x + v.x * k, y: s.y + v.y * k, w: v.w * k }, t: p[4] };
}
function camera(f: number) {
  const b = f / FB;
  let i = PATH.findIndex((p) => b < p[1]);
  if (i < 0) i = PATH.length - 1;
  const [b0, b1, K, B, tB] = PATH[i], { v: A, t: tA } = from(i);
  const lin = (i === 1 || i === 3 || i === 7 || i === PATH.length - 1) ? 1 : 0;   // a hold creeps at a steady rate; a move eases in and out
  if (i === 5) return across(clamp01((b - b0) / (b1 - b0)));
  const raw = clamp01((b - b0) / (b1 - b0)), u = lin ? raw : inOutCubic(raw);
  const w = Math.abs(B.w - A.w) < 1e-6 ? A.w : A.w * Math.pow(B.w / A.w, u), t = Math.abs(B.w - A.w) < 1e-6 ? u : (w - A.w) / (B.w - A.w);
  const turned = i > 0 && PATH[i - 1][2] !== K;                        // backing out of a slot that sits turned: the outer world starts turned the other way
  return { K, v: { x: lerp(A.x, B.x, t), y: lerp(A.y, B.y, t), w }, tilt: [lerp(tA[0], tB[0], u), lerp(tA[1], tB[1], u)], un: turned ? 1 - u : 0 };
}

export function Film({ offset = 0, sub = 1 }: { offset?: number; sub?: number }) {
  const f = useCurrentFrame() / sub + offset;            // sub: pictures drawn for each frame (tools/blur.py averages them into a camera's blur)
  const { K, v, tilt, un } = camera(f), s = 1920 / v.w, sl = SLOTS[K];
  const turn = sl && un > 0 ? ` translate(${sl.px}px, ${sl.py}px) rotate(${(-sl.rot * un).toFixed(4)}deg) translate(${-sl.px}px, ${-sl.py}px)` : "";
  const tilted = Math.abs(tilt[0]) + Math.abs(tilt[1]) > 0.01;
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <style>{FONTS}</style>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: tilted ? `perspective(2000px) rotateX(${tilt[0].toFixed(3)}deg) rotateY(${tilt[1].toFixed(3)}deg) scale(1.001)` : "none" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: "0 0", transform: `translate(${(-v.x * s).toFixed(3)}px, ${(-v.y * s).toFixed(3)}px) scale(${s.toFixed(6)})${turn}` }}>
          {world(K, f, s)}
        </div>
      </div>
    </AbsoluteFill>
  );
}
