// Stet: a launch film for a made-up developer tool, in the snap-and-hold style (BOARD.md).
// One component reads the frame; everything else is a plain function of it. `offset` (frames) lets
// `vd render --from A --to B` draw only a stretch.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { CLOCK, TIMES as TM } from "./kit/times.gen";
import { C, FB, FONTS, clamp01, grid, inOutCubic, lerp, outCubic, ripples } from "./kit/stet";
import { MOODS, field, grain, type Mood } from "./kit/field";
import { D1, LAND, MARK, act1 } from "./act1";
import { MW, MX, colX, slotY } from "./matrix";
import { PH, PW, PX, PY } from "./panel";
import { act3 } from "./act3";
import { act6 } from "./act6";

const S = score as unknown as { fps: number; width: number; height: number; duration: number };
export const FPS = CLOCK.FPS, W = S.width, H = S.height, FRAMES = CLOCK.BEATS * CLOCK.FB;    // the clock sound.py wrote

// Act 1 runs on the film's own clock, beats 0 to CLOCK.ACT1. The acts after it keep the beat numbers they were written
// on (TM.ANSWER onward) and are drawn SHIFT beats earlier (sound.py, where the table is, says why). g(b) is such a beat
// on the film's clock.
const SHIFT = CLOCK.SHIFT;
const g = (b: number) => b - SHIFT;
const MC = MX + MW / 2;
/** where things land, for the page to answer: [beat, x, y] */
const LANDS: [number, number, number][] = [
  [TM.STOP1, LAND.x, LAND.y], [TM.FAIL1, D1.x, D1.y], [TM.CATCH, D1.x, D1.y], [g(TM.COL_AT[0]), colX(0), slotY(1)], [g(TM.NUMBERS), MC, 556], [g(TM.N412), MC, 556], [g(TM.N3), MC, 556], [g(TM.HELD[0]), MC, 556],
  [g(TM.DROP), MC, slotY(6.9)], [g(TM.RERUN1), MC, slotY(6.9)], [g(TM.BACK), MC, slotY(3)], [g(TM.PASSED[0]), D1.x, D1.y],
  [g(TM.MERGE + 3 / FB), PX + PW - 100, PY + PH - 48], [g(TM.SHUT_MARK[0]), MARK.x - 98, 540], [g(TM.SHUT_MARK[1]), MARK.x + 98, 540], [g(TM.FOR), 1100, 540], [g(TM.FOR + 1), 1100, 540],
  [g(TM.FOR + 2), 1100, 540], [g(TM.MORE), 1100, 540], [g(TM.START), 1100, 540], [g(TM.COPIED + 3 / FB), 1080, 680], [g(TM.END), MARK.x, MARK.y], [g(TM.LET[3]), 1130, 720],
];

/** the framings: [beat, the point the frame is centred on, how close]. The camera eases to each from its beat, over 20 frames. */
const CAM: [number, number, number, number][] = [
  [0, 960, 540, 1.3], [TM.ROW, 1150, 560, 1.3], [TM.CHANGED[0], 1020, 540, 1.12], [TM.FAIL1, 1060, 588, 1.45], [TM.CATCH, 960, 540, 1], [g(TM.ANSWER), 960, 540, 1],
  [g(TM.CLOSER), 1360, 590, 1.62], [g(TM.INSIDE), 1360, 476, 2], [g(TM.NUMBERS), 1240, 546, 1.05], [g(TM.RUN), 1360, 540, 2.1], [g(TM.N9888), 1240, 546, 1.05], [g(TM.N3), 1244, 548, 1.07], [g(TM.HELD[0]), 1110, 600, 1.2], [g(TM.CAM_HELD), 1114, 604, 1.22],
  [g(TM.FIXED), 1120, 686, 1.26], [g(TM.BACK), 960, 540, 1], [g(TM.PASSED[0]), 1280, 520, 1.5], [g(TM.MERGE), 1284, 524, 1.54], [g(TM.FOLD), 965, 540, 1], [g(TM.NAME), 965, 540, 1.25],
  [g(TM.FOR), 1040, 540, 1], [g(TM.MORE), 1040, 540, 1.04], [g(TM.START), 1060, 560, 1], [g(TM.COPIED), 1060, 572, 1.04], [g(TM.END), 965, 566, 1.14],
];
const CREEP = 0.009;                       // between moves the camera creeps in, this much of its closeness a second
function camera(f: number) {
  let c = [CAM[0][1], CAM[0][2], CAM[0][3]], since = CAM[0][0] * FB;
  for (let i = 1; i < CAM.length; i++) {
    const start = CAM[i][0] * FB;
    if (f < start - 1) break;
    c[2] *= 1 + (CREEP * (start - since)) / 60;                            // the creep it had gathered is where the next move starts from
    const k = inOutCubic(clamp01((f - start + 1) / 20));                   // it eases in as well as out: a camera has weight
    c = [lerp(c[0], CAM[i][1], k), lerp(c[1], CAM[i][2], k), lerp(c[2], CAM[i][3], k)];
    since = start;
  }
  return [c[0], c[1], c[2] * (1 + (CREEP * Math.max(0, f - since)) / 60)];
}

/** the air's mood: [beat, how much of calm, alarm, held, clear, frames to get there]. It follows the build: calm while it
 * passes, flushed when it fails (twice, with the first two flips, then it stays), calm again once the flake is held,
 * a little warm when the flake is named, and clear from the release on. */
const AIR: [number, number, number, number, number, number][] = [
  [0, 1, 0, 0, 0, 1], [TM.FAIL1, 0.15, 0.85, 0, 0, 8], [TM.FLIPS[0], 0.8, 0.2, 0, 0, 7], [TM.FLIPS[1], 0.1, 0.9, 0, 0, 7], [TM.FAST, 0, 1, 0, 0, 20],
  [TM.CATCH, 0, 0, 1, 0, 14], [g(TM.WASH), 0, 0.3, 0.7, 0, 16], [g(TM.CAUGHT), 0, 0.45, 0.55, 0, 12], [g(TM.NUMBERS), 0, 0, 1, 0, 16], [g(TM.RERUN1), 0, 0, 0.5, 0.5, 16], [g(TM.PASSED[0]), 0, 0, 0, 1, 16],
];
function air(f: number): [Mood, number][] {
  let w = [AIR[0][1], AIR[0][2], AIR[0][3], AIR[0][4]];
  for (let i = 1; i < AIR.length; i++) {
    const k = outCubic(clamp01((f - AIR[i][0] * FB + 1) / AIR[i][5]));
    if (k <= 0) break;
    w = w.map((v, j) => lerp(v, AIR[i][j + 1], k));
  }
  return [[MOODS.calm, w[0]], [MOODS.alarm, w[1]], [MOODS.held, w[2]], [MOODS.clear, w[3]]];
}

export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset;
  const h = f + SHIFT * FB;                // the same moment on the later acts' clock
  const [cx, cy, z] = camera(f);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <style>{FONTS}</style>
      {field(f, air(f), W, H, -(cx - W / 2) * 0.12 * z, -(cy - H / 2) * 0.12 * z)}
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${(W / 2 - cx * z).toFixed(3)}px, ${(H / 2 - cy * z).toFixed(3)}px) scale(${z.toFixed(5)})` }}>
        {grid("grid")}
        {ripples("rip", f, LANDS)}
        {f < CLOCK.ACT1 * FB ? act1(f) : null}
        {h >= TM.ANSWER * FB && h < TM.FOLD * FB ? act3(h) : null}
        {h >= TM.FOLD * FB ? act6(h) : null}
      </div>
      {finish ? grain(f, W, H) : null}
    </AbsoluteFill>
  );
}
