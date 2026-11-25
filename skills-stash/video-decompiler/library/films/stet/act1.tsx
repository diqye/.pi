// Act 1, beats 0 to 11: the problem ("It passed. You changed nothing. It failed."), the flip, and the catch: the
// brackets shut on the flipping dot where it is, and it stops. The music's bars fall on beats 1, 5 and 9, with a half
// bar from 9 to 11: the full stop lands on 1, the failure on 5, the brackets come on 9 and 9.5. Every beat is sound.py's
// (TM, from kit/times.gen.ts), on the film's clock.
import { TIMES as TM } from "./kit/times.gen";
import { C, D, FB, GLASS, H, M, R, T, W, along, arr, brackets, claim, claimLayout, clamp01, flush, inOutCubic, lerp, mw, outCubic, pointer, press, ring, shut, type Claim, type Run } from "./kit/stet";
import { PW, PX, ROW, btnAt, BTN, checks, dotX, rowY } from "./panel";

const SZ = 96;
const S: Claim = { x: W / 2, cy: 540, size: SZ, center: true, words: [{ w: "It", at: TM.IT[0] }, { w: "passed", at: TM.IT[1] }], stop: { at: TM.STOP1, hide: true } };
const SL = claimLayout(S);
export const LAND = SL.stop;
const FRONT = { x: SL.x0 - 0.36 * SZ, y: SL.stop.y };            // where the full stop lands when it hops to the head of the line
export const D1 = { x: dotX(), y: rowY(2) };                      // the tests row's status dot: a dot of the page's grid
export const MARK = { x: 816, y: 540, r: 35.5, w: 196, h: 152 };  // the mark beside the name
export const STING = { x: 960, y: 540 };                          // the mark alone stands in the middle
const PRESSES = [TM.RERUN, ...TM.PRESSES];

/** the tests row through the flip: what it shows, and the last verdict it gave */
export function tests(f: number): { state: Run; verdict: "pass" | "fail" } {
  const b = f / FB;
  if (b < TM.RERUN) return { state: "pass", verdict: "pass" };
  if (b < TM.FAIL1) return { state: "run", verdict: "pass" };
  // from the first failure on, the row shows each answer until the next one lands: the word, the dot and the air agree
  if (b < TM.FLIPS[0]) return { state: "fail", verdict: "fail" };
  if (b < TM.FLIPS[1]) return { state: "pass", verdict: "pass" };
  if (b < TM.FLIPS[2]) return { state: "fail", verdict: "fail" };
  if (b < TM.FLIPS[3]) return { state: "pass", verdict: "pass" };
  if (b < TM.FAST) return { state: "fail", verdict: "fail" };
  if (b >= TM.CATCH) return { state: "fail", verdict: "fail" };                                                   // caught: it stays what it is
  const v = (b < TM.FASTER ? Math.floor((f - TM.FAST * FB) / (FB / 4)) : Math.floor((f - TM.FASTER * FB) / (FB / 6))) % 2 === 0 ? "pass" : "fail";   // and faster: a quarter beat each, then a sixth
  return { state: v, verdict: v };
}

export function act1(f: number) {
  const scene: any[] = [], b = f / FB;
  const out = scene;                                              // everything of the scene; it falls away after the catch
  const tv = tests(f);

  // ---- the panel, growing out of the sentence
  if (b < TM.ROW) {
    out.push(claim("s", f, S));
    // the full stop: flies in over 21 frames, lands on its beat, hops to the head of the line
    const t0 = TM.STOP1 * FB - 21;
    const fly = outCubic(clamp01((f - t0) / 21)), hop = inOutCubic(clamp01((f - TM.HOP * FB + 1) / 10));
    const x = lerp(lerp(SL.stop.x + 560, SL.stop.x, fly), FRONT.x, hop);
    const y = lerp(SL.stop.y - 300, SL.stop.y, fly) - Math.sin(Math.PI * hop) * 92 - Math.sin(Math.PI * fly) * 26;
    if (f >= t0) out.push(D("dot", x, y, SL.stop.r, C.ink));
  } else {
    const km = arr(f, TM.ROW, 6);
    if (km < 1) {
      // the sentence becomes the row: its frame closes in, the words turn into the row's own
      const dx = lerp(FRONT.x, D1.x, km), dy = lerp(FRONT.y, D1.y, km), mono = km > 0.22;
      const x0 = lerp(FRONT.x - 48, PX, km), x1 = lerp(SL.x0 + SL.widest + 48, PX + PW, km), hh = lerp(160, ROW, km);
      out.push(R("rowbg", x0, dy - hh / 2 + lerp(-26, 0, km), x1 - x0, hh, { ...GLASS, borderRadius: 12, boxSizing: "border-box", opacity: clamp01(km * 4) }));
      const s1 = lerp(SZ, 24, km), s2 = lerp(SZ, 22, km), base = dy + lerp(SL.stop.r, 8.5, km);
      const lx = lerp(SL.xs[0], D1.x + 30, km), nx = lerp(SL.xs[1], PX + PW - 32 - mw("passed", 22), km);
      out.push(mono ? M("lab", lx, base, s1, "tests") : T("lab", lx, base, s1, "It"));
      out.push(mono ? M("note", nx, base, s2, "passed", { color: C.grey }) : T("note", nx, base, s2, "passed"));
      out.push(D("dot", dx, dy, lerp(SL.stop.r, 9, km), C.ink));
    } else {
      const note = (s: Run, n: string) => (s === "run" ? "running" : n);
      const build: Run = b >= TM.RERUN && b < TM.BUILD ? "run" : "pass", lint: Run = b >= TM.RERUN && b < TM.LINT ? "run" : "pass";
      const tnote = tv.state === "run" ? "running" : tv.state === "fail" ? "1 failed" : b >= TM.PANEL ? "412 passed" : "passed";
      const down = Math.max(...PRESSES.map((p) => press(f, p)));
      out.push(checks("p", f, {
        k: arr(f, TM.PANEL, 8), at: TM.PANEL,
        rows: [{ label: "build", state: build, note: note(build, "passed") }, { label: "lint", state: lint, note: note(lint, "passed") }, { label: "tests", state: tv.state, note: tnote }],
        btn: { label: "Re-run", down },
      }));
    }
  }

  // ---- the claims on the left
  const CH = TM.CHANGED;
  out.push(claim("c2", f, { x: 300, cy: 540, words: [{ w: "You", at: CH[0] }, { w: "changed", at: CH[1] }, { w: "nothing", at: CH[2], mark: TM.NOTHING, br: true }], stop: { at: CH[3] }, off: TM.FAIL1 }));
  if (b >= TM.FAIL1) {
    const fail = tv.verdict === "fail";
    out.push(claim("c3", f, { x: 480, cy: 588, words: [{ w: "It", at: TM.FAIL1 }, { w: fail ? "failed" : "passed", at: TM.FAIL1, mark: TM.FAIL1 + 0.25, red: fail }], stop: { at: TM.FAIL1, color: fail ? C.red : C.ink } }));
  }

  // ---- the pointer: it comes to Re-run and presses, and presses again
  if (b >= TM.POINTER[0]) {
    const bt = btnAt(), bx = bt.x + BTN.w * 0.84, by = bt.y + BTN.h * 0.74;
    const [px, py] = along(f, [[TM.POINTER[0], 1700, 1150], [TM.POINTER[1], bx, by]]);
    const down = Math.max(...PRESSES.map((p) => press(f, p)));
    PRESSES.forEach((p, i) => out.push(ring(`pr${i}`, f, p, bx, by)));
    out.push(pointer("hand", px, py, down));
  }

  // ---- the catch: two brackets shut on the flipping dot, and it stops. Then the scene falls away and the mark is left.
  const exit = b >= TM.CATCH ? clamp01((f - TM.CATCH * FB - 2) / 8) : 0, grow = arr(f, TM.CATCH + 0.3, 14);
  const all: any[] = [<div key="scene" style={{ position: "absolute", left: 0, top: 0, width: W, height: H, opacity: 1 - exit, transform: `translateY(${(exit * 22).toFixed(2)}px)` }}>{scene}</div>];
  if (b >= TM.BRACKET) {
    const cx = lerp(D1.x, STING.x, grow), cy = lerp(D1.y, STING.y, grow);
    all.push(flush("fl", f, TM.CATCH, D1.x, D1.y, C.red));
    if (b >= TM.CATCH) all.push(D("held", cx, cy, lerp(9, MARK.r, grow), C.red));
    all.push(brackets("br", cx, cy, lerp(48, MARK.w, grow), lerp(38, MARK.h, grow), C.ink, { sw: lerp(5, 18, grow), arm: lerp(10, 38, grow), kl: shut(f, TM.BRACKET, 6), kr: shut(f, TM.CATCH, 6), spread: 260 }));
  }
  return all;
}
