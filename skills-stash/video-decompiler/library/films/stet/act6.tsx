// The last acts, beats 56 to 77 on the middle acts' clock: the name in the one silence, what it works with, how to
// start, and the end card. One thing keeps its place from here to the last frame: the mark. What stands beside it
// changes: the name, the runners, the command, the name again. Every beat is sound.py's (TM, from kit/times.gen.ts).
import { TIMES as TM } from "./kit/times.gen";
import { C, D, FB, GLASS, M, R, T, along, arr, brackets, claim, clamp01, lerp, mw, on, outCubic, pointer, press, ramp, ring, shut } from "./kit/stet";
import { MARK } from "./act1";
import { PW, PX, ROW, BTN, button, checks, dotX, rowY } from "./panel";

const TX = MARK.x + MARK.w / 2 + 46;                 // where the words beside the mark begin
const RUNNERS = ["pytest", "jest", "playwright"];
const CMD = "npx stet init";
const ROWS3 = [{ label: "build", state: "pass" as const, note: "passed" }, { label: "lint", state: "pass" as const, note: "passed" }, { label: "tests", state: "pass" as const, note: "410 passed · 2 held" }];
const { FOLD, NAME, FOR, MORE, START, END } = TM;

export function act6(f: number) {
  const out: any[] = [], b = f / FB;

  // ---- everything folds into one dot, and the dot comes to the mark's place
  if (b < TM.SHUT_MARK[0]) {
    const kc = shut(f, FOLD, 7), kr = shut(f, FOLD + 0.3, 6);
    if (kr < 1) {
      if (kc < 1) out.push(checks("p3", f, { k: 1 - kc, rows: ROWS3, btn: { label: "Merged", solid: true } }));
      else {
        const x0 = lerp(PX, dotX() - 14, kr), x1 = lerp(PX + PW, dotX() + 14, kr), hh = lerp(ROW, 28, kr);
        out.push(R("rowc", x0, rowY(2) - hh / 2, x1 - x0, hh, { ...GLASS, borderRadius: 12, boxSizing: "border-box", opacity: 1 - kr }));
        out.push(D("dotc", dotX(), rowY(2), 9, C.ink));
      }
    } else {
      const kd = outCubic(ramp(f, FOLD + 0.3 + 6 / FB, FOLD + 0.92));
      out.push(D("dotc", lerp(dotX(), MARK.x, kd), lerp(rowY(2), MARK.y, kd), lerp(9, MARK.r, kd), C.ink));
    }
    return out;
  }

  // ---- the mark: the brackets shut on the dot, and it is held
  out.push(D("dot", MARK.x, MARK.y, MARK.r, on(f, TM.SHUT_MARK[1]) ? C.red : C.ink));
  out.push(brackets("mk", MARK.x, MARK.y, MARK.w, MARK.h, C.ink, { sw: 18, arm: 38, kl: shut(f, TM.SHUT_MARK[0], 6), kr: shut(f, TM.SHUT_MARK[1], 6), spread: 520 }));

  // ---- the label above what stands beside it
  const label = (key: string, text: string, at: number, off: number) => {
    if (!on(f, at) || on(f, off)) return;
    out.push(T(key, TX + 4, MARK.y - 106 + (1 - arr(f, at, 6)) * 8, 44, text, { opacity: clamp01((f - at * FB + 1) / 3), color: "#55544F" }));
  };
  label("l1", "Introducing", NAME, FOR);
  label("l2", "For", FOR, MORE);
  label("l2b", "and", MORE, START);
  label("l3", "One line to start", START, END);

  // ---- what stands beside the mark
  const rise = (at: number) => (1 - arr(f, at, 6)) * 12;
  const name = (n: number, at: number) => out.push(T("name", TX, MARK.y + 55 + rise(at), 156, "stet".slice(0, n), { fontWeight: 600, letterSpacing: "-0.035em" }));
  if (b >= NAME && b < FOR) name(Math.min(4, Math.floor((f - NAME * FB) / 3) + 1), 0);
  else if (b >= FOR && b < MORE) { const i = Math.min(2, Math.floor(b - FOR)); out.push(M("rn", TX + 4, MARK.y + 37 + rise(FOR + i), 104, RUNNERS[i], { fontWeight: 500 })); }
  else if (b >= MORE && b < START) {
    out.push(T("mo", TX, MARK.y + 46 + rise(MORE), 128, "30+", { fontWeight: 600, letterSpacing: "-0.035em" }));
    if (on(f, MORE + 0.25)) out.push(T("mo2", TX + 262, MARK.y + 46 + rise(MORE + 0.25), 128, "more", { fontWeight: 600, letterSpacing: "-0.035em", color: "#6A6964", opacity: clamp01((f - (MORE + 0.25) * FB + 1) / 3) }));
  } else if (b >= START && b < END) {
    const n = Math.max(0, Math.min(CMD.length, Math.floor((f - TM.CMD * FB) / 2) + 1));
    if (n) out.push(M("cmd", TX + 4, MARK.y + 27, 72, CMD.slice(0, n), { fontWeight: 500 }));
    if (n < CMD.length || Math.floor((f - TM.CMD * FB) / 15) % 2 === 0) out.push(R("caret", TX + 4 + mw(CMD.slice(0, n), 72) + 6, MARK.y - 36, 5, 72, { background: C.ink }));
    // copy the line
    if (b >= TM.COPY) {
      const bx = TX + 4, by = MARK.y + 96, k = arr(f, TM.COPY, 6), down = press(f, TM.COPIED), done = f >= TM.COPIED * FB + 3;
      out.push(<div key="cbw" style={{ opacity: clamp01((f - TM.COPY * FB + 1) / 3), transform: `translateY(${(1 - k) * 10}px)` }}>{button("cb", bx, by, done ? "Copied" : "Copy", down, done)}</div>);
      const hx = bx + BTN.w * 0.84, hy = by + BTN.h * 0.74;
      const [px, py] = along(f, [[TM.POINTER3[0], 1640, 1150], [TM.POINTER3[1], hx, hy]]);
      out.push(ring("cr", f, TM.COPIED, hx, hy));
      if (b >= TM.POINTER3[0]) out.push(pointer("hand3", px, py, down));
    }
    out.push(claim("free", f, { x: TX + 4, cy: MARK.y + 236, size: 56, words: [{ w: "Free", at: TM.FREE[0] }, { w: "for", at: TM.FREE[1] }, { w: "open", at: TM.FREE[2] }, { w: "source", at: TM.FREE[3] }], stop: { at: TM.FREE[4] } }));
  } else if (b >= END) {
    // ---- the end card: the name again, and the line under it
    name(4, END);
    out.push(claim("tag", f, { x: 965, cy: 708, size: 60, center: true, color: "#55544F", words: [{ w: "Let", at: TM.LET[0] }, { w: "it", at: TM.LET[1] }, { w: "stand", at: TM.LET[2], mark: TM.LET_MARK }], stop: { at: TM.LET[3] } }));
  }
  return out;
}
