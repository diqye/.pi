// The line: the one thing in the film from its second second to its last frame (BOARD.md, the cast). A thin line of
// light. Every sound is a shape on it. One function of where and when gives its shape; another gives where it lies.
import { WAVES } from "./kit/waves.gen";
import { C, D, FB, TM, clamp01, gauss, glide, lerp, rnd, svg, tw } from "./kit/core";

const P = TM.PARTS;                                      // the parts' first beats, as in BOARD.md's beats table

export const HY = 780;                                   // where the rain lands: the line's first place
export const PULSE_X = 1180;                             // where the heartbeat starts on the line
export const BAR = { x: 310, y: 248, w: 1300, h: 104 };  // the prompt bar; the line is its lower edge while it is open
export const TRACKS = [450, 552, 654, 756, 858];         // the five tracks of the mix
export const NAME_HALF = 285;
export const NAME = "onoma", NS = 200, NW = tw(NAME, NS, "geist600", -0.035);
/** where each letter of the name stands over the line, and the half beats its letters land on, the first time and the last */
export const LX = [0, 1, 2, 3, 4].map((i) => 960 - NW / 2 + tw(NAME.slice(0, i), NS, "geist600", -0.035) + tw(NAME[i], NS, "geist600", -0.035) / 2);
export const JING: number[] = TM.NAME, JING2: number[] = TM.NAME2;

/** the frames the sounds land on, from sound.py's table */
export const RAIN_F = TM.RAIN * FB, BOLT_F = TM.BOLT * FB, HUSH_F = TM.HUSH * FB;
const RIP = Array.from({ length: 16 }, (_, i) => ({ x: 520 + rnd(i) * 900, f0: RAIN_F + 24 + rnd(i + 50) * 54 }));  // where drops land
export const STEPS = [0, 1, 2, 3].map((k) => ({ x: 420 + 300 * k, f0: TM.STEPS[k] * FB }));
export const CLAPS = [[620, 250], [920, 150], [1180, 90], [1400, 54]].map(([x, h], i) => ({ x, f0: TM.CLAPS[i] * FB, h }));  // the clap and its three returns
const DUB = Math.round(TM.DUB * FB);                                                                                // lub to dub, in frames
export const PULSES = (TM.PULSES as number[]).flatMap((b) => [b * FB, b * FB + DUB]);                              // lub, dub, lub, dub
export const BOLT_X = 560;
/** a heartbeat's trace about u = 0; up is negative */
const ecg = (u: number, s: number) => s * (-150 * gauss(u, 9) + 36 * gauss(u - 24, 10) + 16 * gauss(u + 26, 9) - 12 * gauss(u + 120, 34) - 26 * gauss(u - 130, 42));

/** the name's five letters are the five sounds: what letter i does to the line, u from under it, a frames after it lands */
function letter(i: number, u: number, a: number) {
  if (i === 0) return 9 * Math.exp(-a / 20) * Math.sin(Math.abs(u) * 0.09 - a * 0.55) * Math.exp(-Math.abs(u) / 80);            // rain
  if (i === 1) return 15 * Math.exp(-a / 22) * Math.sin(u * 0.03 - a * 0.4) * Math.exp(-Math.abs(u) / 220);                     // thunder
  if (i === 2) return 22 * gauss(u, 42) * Math.exp(-a / 8) * Math.cos(a * 0.42);                                                // a footstep
  if (i === 3) return -48 * gauss(u, 9) * Math.exp(-a / 8) + 5 * gauss(u, 60) * Math.exp(-a / 14) * Math.sin(a * 0.6);          // a clap
  return ecg((u + 9 * a) * 1.6, 0.3) * Math.min(1, a / 3) + (a > 17 ? ecg((u + 9 * (a - 17)) * 1.6, 0.14) * Math.min(1, (a - 17) / 3) : 0);   // a heartbeat, running back under the name
}

/** how far the line is pushed off its level at x on frame f (positive is down) */
export function disp(x: number, f: number) {
  if (f >= P.ask * FB && f < P.end * FB) return 0;         // while it is the edge of the prompt bar it is still
  let d = 0;
  if (f < RAIN_F + 170) for (const r of RIP) { const a = f - r.f0; if (a > 0) d += 7 * Math.exp(-a / 26) * Math.sin(Math.abs(x - r.x) * 0.045 - a * 0.5) * Math.exp(-Math.abs(x - r.x) / 170); }
  const at = f - BOLT_F;                                   // thunder: the rumble rolls out from where the bolt stood, with the sound's own loudness
  if (at > 0 && at < 180) d += 48 * WAVES.thunder[Math.min(159, Math.floor((at / 180) * 160))] * Math.sin(Math.abs(x - BOLT_X) * 0.011 - at * 0.33) * Math.exp(-Math.abs(x - BOLT_X) / 1100);
  if (at > 0 && at < 70) d -= 110 * gauss(Math.abs(x - BOLT_X) - 30 * at, 70) * Math.exp(-at / 18);       // the crack: a shock runs out along the line, both ways
  for (const s of STEPS) { const a = f - s.f0; if (a >= 0 && a < 60) d += 46 * gauss(x - s.x, 64) * Math.exp(-a / 9) * Math.cos(a * 0.42); }
  for (const c of CLAPS) { const a = f - c.f0; if (a >= 0 && a < 100) d += -c.h * gauss(x - c.x, 13) * Math.exp(-a / 15) + 10 * gauss(x - c.x, 90) * Math.exp(-a / 16) * Math.sin(a * 0.6); }
  PULSES.forEach((f0, i) => { const a = f - f0; if (a >= 0 && a < 120) d += ecg(x - (PULSE_X - 13 * a), i % 2 ? 0.45 : 1) * Math.min(1, a / 3); });
  for (const J of [JING, JING2]) J.forEach((jb, i) => { const a = f - jb * FB; if (a >= 0 && a < 90) d += letter(i, x - LX[i], a); });   // the name is said
  return d * (1 - clamp01((f - HUSH_F) / 34) * (f < P.name * FB ? 1 : 0));    // the hush stills it
}

/** where the line lies on frame f: its level, the middle of it, half its length, and how strongly it shows */
export function lie(f: number) {
  let y = HY, cx = 960, half = 1700;
  const a = clamp01((f - (RAIN_F + 22)) / 34);             // the first drops land and the line shows
  half = lerp(half, 0, glide(f, TM.HUSH + 0.3, 52));       // the hush draws it in to a point
  if (f >= P.name * FB) half = lerp(0, NAME_HALF, glide(f, P.name, 18));
  if (f >= P.ask * FB) { const k = glide(f, P.ask, 18); y = lerp(HY, BAR.y + BAR.h, k); half = lerp(NAME_HALF, BAR.w / 2, k); }
  if (f >= P.take * FB) { const k = glide(f, P.take, 16); y = lerp(BAR.y + BAR.h, TRACKS[2], k); half = lerp(BAR.w / 2, 640, k); }
  if (f >= P.end * FB) { const k = glide(f, P.end, 18); y = lerp(TRACKS[2], HY, k); half = lerp(640, NAME_HALF, k); }
  return { y, cx, half, a };
}

/** the line itself, with its glow */
export function line(f: number) {
  const L = lie(f);
  if (L.a <= 0) return null;
  if (L.half < 5) {                                        // a point in the dark, breathing
    const br = 0.5 + 0.5 * Math.sin(f * 0.14);
    return [D("pt2", L.cx, L.y, 14 + 14 * br, `rgba(255, 241, 214, ${(0.07 + 0.09 * br).toFixed(3)})`), D("pt", L.cx, L.y, 5, C.light)];
  }
  let d = "";
  for (let x = L.cx - L.half; x <= L.cx + L.half; x += 4) d += `${d ? "L" : "M"}${x.toFixed(1)},${(L.y + disp(x, f)).toFixed(1)}`;
  return svg("line", [
    <path key="g2" d={d} stroke={C.light} strokeOpacity={0.06} strokeWidth={16} fill="none" strokeLinecap="round" strokeLinejoin="round" />,
    <path key="g1" d={d} stroke={C.light} strokeOpacity={0.16} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />,
    <path key="g0" d={d} stroke={C.light} strokeWidth={2.6} fill="none" strokeLinecap="round" strokeLinejoin="round" />,
  ], { opacity: L.a });
}
