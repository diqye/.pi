// Plus One: an interface demo for a made-up invitation app (BOARD.md). One component reads the frame; everything else
// is a plain function of it. `offset` (frames) lets `vd render --from A --to B` draw only a stretch.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { CLOCK, TIMES as TM } from "./kit/times.gen";
import { C, FB, FONTS, clamp01, inOutCubic, lerp } from "./kit/core";
import { dark, field, grain } from "./kit/field";
import { mess, name, pointer, pointerAt, words } from "./acts1";
import { air, cards, chooser, countAt, guestView, guests, lockup, minis, plusOnes, sky, stars, talk } from "./acts2";

const S = score as unknown as { width: number; height: number };
export const FPS = CLOCK.FPS, W = S.width, H = S.height, FRAMES = CLOCK.BEATS * CLOCK.FB;    // the clock sound.py wrote

/** the framings: [beat, the point the frame is centred on, how close, frames the move takes (20 if not given)] */
const CAM: number[][] = [
  [0, 960, 760, 1.3], [TM.BUBBLES[0] + 0.2, 960, 540, 1.0, 200],                                    // the chat: from its newest line out to the whole thread
  [TM.COLLAPSE + 0.5, 960, 585, 1.2, 34], [TM.TYPE0, 960, 590, 1.3, 112],                          // the field, and in on it as the line is typed
  [TM.RETURN, 960, 540, 1.0, 28], [TM.RETURN + 1, 960, 524, 1.08, 100], [TM.DRESS + 0.4, 960, 512, 1.12, 80],   // the card forming; "Add a look"
  [TM.OPEN, 960, 574, 0.9, 28], [TM.OPEN + 2, 960, 574, 0.95, 300],                                 // the row of looks, pushing in through it
  [TM.PICK, 960, 540, 1.12, 32], [TM.SEND, 960, 540, 0.94, 32],                                     // the choice; the guests
  [TM.GUEST, 340, 362, 1.65, 30], [TM.TAP + 0.1, 960, 540, 0.98, 34], [TM.REPLIES[2], 960, 540, 0.9, 330],   // one guest's phone, then back out as the replies come
  [TM.ASK - 0.4, 960, 745, 1.45, 38], [TM.LAST - 0.15, 960, 540, 0.9, 30],                            // in on the question that comes back, and out for the last yes
  [TM.END, 960, 530, 1.0, 44], [TM.END + 2.6, 960, 552, 1.26, 64],                                  // the mark
];
const CREEP = 0.006;
function camera(f: number) {
  let c = [CAM[0][1], CAM[0][2], CAM[0][3]], since = CAM[0][0] * FB;
  for (let i = 1; i < CAM.length; i++) {
    const start = CAM[i][0] * FB;
    if (f < start - 1) break;
    c[2] *= 1 + (CREEP * (start - since)) / 60;                              // the creep it gathered is where the next move starts from
    const k = inOutCubic(clamp01((f - start + 1) / (CAM[i][4] ?? 20)));     // a camera has weight: it eases in and out
    c = [lerp(c[0], CAM[i][1], k), lerp(c[1], CAM[i][2], k), lerp(c[2], CAM[i][3], k)];
    since = start;
  }
  const p = pointerAt(f), lead = clamp01((1150 - p.y) / 150);                // the view follows the pointer a little
  return [c[0] + (p.x - 960) * 0.035 * lead, c[1] + (p.y - 540) * 0.02 * lead, c[2] * (1 + (CREEP * Math.max(0, f - since)) / 60)];
}

export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset;
  const [cx, cy, z] = camera(f), ws = air(f), dk = dark(ws), night = clamp01((dk - 0.35) / 0.3);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <style>{FONTS}</style>
      {field(f, ws, W, H, -(cx - W / 2) * 0.14 * z, -(cy - H / 2) * 0.14 * z)}
      {stars(f, W, H, night)}
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${(W / 2 - cx * z).toFixed(3)}px, ${(H / 2 - cy * z).toFixed(3)}px) scale(${z.toFixed(5)})` }}>
        {sky(f)}
        {words(f, night, countAt(f))}
        {guests(f, false)}
        {plusOnes(f)}
        {minis(f)}
        {cards(f)}
        {chooser(f, dk)}
        {mess(f)}
        {name(f)}
        {guests(f, true)}
        {talk(f)}
        {guestView(f, night)}
        {lockup(f)}
        {pointer(f, night)}
      </div>
      {finish ? grain(f, W, H) : null}
    </AbsoluteFill>
  );
}
