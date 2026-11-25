// The middle acts, beats 16 to 56 on their own clock (the film draws them CLOCK.SHIFT beats earlier): the answer, the
// numbers, the hold, the release, and "Passed means passed." Every beat is sound.py's (TM, from kit/times.gen.ts).
import { TIMES as TM } from "./kit/times.gen";
import { C, D, FB, along, arr, brackets, claim, claimLayout, lerp, pointer, press, ring, type Claim } from "./kit/stet";
import { MARK, STING } from "./act1";
import { BADGE, MX, matrix, slotY } from "./matrix";
import { BTN, btnAt, checks } from "./panel";

const X = 192, LH = 100;
const GREY = { color: "#6A6964" };

export function act3(f: number) {
  const out: any[] = [], b = f / FB;

  // ---- the specimen
  out.push(matrix(f));
  // out of the sting: the mark goes to the head of its own panel
  if (f < TM.ANSWER * FB + 16) {
    const k = arr(f, TM.ANSWER, 9), x = lerp(STING.x, BADGE.x, k), y = lerp(STING.y, BADGE.y, k);
    out.push(brackets("lb", x, y, lerp(MARK.w, BADGE.w, k), lerp(MARK.h, BADGE.h, k), k > 0.55 ? "#ECEAE5" : C.ink, { sw: lerp(18, 3.5, k), arm: lerp(38, 8, k) }));
    out.push(D("ld", x, y, lerp(MARK.r, BADGE.r, k), C.red));
  }

  // ---- the claims
  const RI = TM.RUN_IT, A1 = TM.AND1, A2 = TM.AND2;
  out.push(claim("a1", f, { x: X, cy: 540 - LH, words: [{ w: "Run", at: RI[0] }, { w: "it", at: RI[1] }, { w: "again", at: RI[2] }], stop: { at: RI[3] }, off: TM.INSIDE }));
  out.push(claim("a2", f, { x: X, cy: 540, words: [{ w: "And", at: A1[0] }, { w: "again", at: A1[1] }], stop: { at: A1[2] }, off: TM.INSIDE }));
  out.push(claim("a3", f, { x: X, cy: 540 + LH, words: [{ w: "And", at: A2[0] }, { w: "again", at: A2[1] }], stop: { at: A2[2] }, off: TM.INSIDE }));
  // these three are said inside the panel, in its own light type, between the two rows they are about: the camera is on them
  const IN = { x: MX + 28, color: "#ECEAE5" };
  const B1: Claim = { ...IN, cy: slotY(2.5) - 6, size: 44, words: [{ w: "Same", at: TM.SAME[0] }, { w: "commit", at: TM.SAME[1] }], stop: { at: TM.SAME[2] }, off: TM.SAID };
  out.push(claim("b1", f, B1));
  out.push(claim("b2", f, { ...IN, x: IN.x + claimLayout(B1).widest + 30, cy: slotY(2.5) - 6, size: 44, words: [{ w: "Two", at: TM.TWO[0], mark: TM.TWO_MARKS[0] }, { w: "answers", at: TM.TWO[1], mark: TM.TWO_MARKS[1] }], stop: { at: TM.TWO[2] }, off: TM.SAID }));
  const FL = TM.FLAKE;
  out.push(claim("b3", f, { ...IN, cy: slotY(2.5) - 6, size: 58, words: [{ w: "That’s", at: FL[0] }, { w: "a", at: FL[1] }, { w: "flake", at: FL[2], mark: TM.FLAKE_MARK, red: true }], stop: { at: FL[3], color: C.red }, off: TM.FLAKE_OFF }));
  const N = (key: string, row: number, at: number, num: string, word: string, red = false) =>
    claim(key, f, { x: 440, cy: 546 + (row - 1.5) * LH, words: [{ w: num, at }, { w: word, at, ...GREY }], stop: red ? { at: at + 0.25, color: C.red } : undefined, off: TM.HELD[0] });
  out.push(N("n1", 0, TM.N412, "412", "tests"), N("n2", 1, TM.N9888, "9,888", "runs"), N("n3", 2, TM.N3, "3", "flakes", true), N("n4", 3, TM.N6, "6", "minutes"));
  const HD = TM.HELD;
  out.push(claim("h", f, { x: 440, cy: 600, size: 68, words: [{ w: "Held,", at: HD[0], mark: HD[3] }, { w: "not", at: HD[1], br: true }, { w: "deleted", at: HD[2] }], stop: { at: HD[3] }, off: TM.FIXED }));
  out.push(claim("r1", f, { x: 480, cy: 646, size: 64, words: [{ w: "Fixed?", at: TM.FIXED }], off: TM.PASSED[0] }));
  out.push(claim("r2", f, { x: 480, cy: 826, size: 64, words: [{ w: "Released", at: TM.RELEASED[0] }], stop: { at: TM.RELEASED[1] }, off: TM.PASSED[0] }));
  const PS = TM.PASSED;
  out.push(claim("p", f, { x: 1280, cy: 252, size: 64, center: true, words: [{ w: "Passed", at: PS[0] }, { w: "means", at: PS[1] }, { w: "passed", at: PS[2], mark: TM.PASSED_MARK }], stop: { at: PS[3] }, off: TM.FOLD }));

  // ---- the checks panel again, now telling the truth, and the merge
  if (f >= TM.PASSED[0] * FB + 16) {
    const merged = f >= TM.MERGE * FB + 3, down = press(f, TM.MERGE);
    out.push(checks("p2", f, {
      k: arr(f, TM.CHECKS2, 8), at: TM.CHECKS2,
      rows: [{ label: "build", state: "pass", note: "passed" }, { label: "lint", state: "pass", note: "passed" }, { label: "tests", state: "pass", note: "410 passed · 2 held" }],
      btn: { label: merged ? "Merged" : "Merge", down, solid: merged },
    }));
    if (b >= TM.POINTER2[0]) {
      const bt = btnAt(), bx = bt.x + BTN.w * 0.84, by = bt.y + BTN.h * 0.74;
      const [px, py] = along(f, [[TM.POINTER2[0], 1720, 1050], [TM.POINTER2[1], bx, by]]);
      out.push(ring("mr", f, TM.MERGE, bx, by));
      out.push(pointer("hand2", px, py, down));
    }
  }
  return out;
}
