// The run matrix: Stet's own dark surface. Tests down, runs across. Beats 16 to about 48.6 on the middle acts' clock
// (BOARD.md: ANSWER, NUMBERS, HELD, RELEASE, and the fold into the checks panel). One function of the frame; every count
// shown is the count of what is drawn. Every beat is sound.py's (TM, from kit/times.gen.ts).
import { TIMES as TM } from "./kit/times.gen";
import { C, D, FB, GLASS, M, R, T, arr, brackets, clamp01, lerp, mw, on, shut } from "./kit/stet";
import { MARK, STING } from "./act1";
import { PW, PX, ROW, dotX, rowY } from "./panel";

export const MX = 920, MW = 880, MY = 288, HEADM = 52, RP = 54, DX0 = 366, DP = 20.4, DR = 6.5, COLS = 24;
export const YC = MY + HEADM + RP * 4;                      // the middle of the eight rows
export const colX = (c: number) => MX + DX0 + c * DP;
export const slotY = (s: number) => MY + HEADM + RP / 2 + RP * s;
export const BADGE = { x: MX + 44, y: MY + 27, w: 34, h: 26, r: 5 };   // the mark, small, at the head of the panel
export const NAMES = ["cart › adds an item", "checkout › applies coupon", "checkout › validates card", "login › remembers device", "search › debounces input", "orders › paginates", "upload › retries on 503", "profile › saves avatar"];
export const FLAKY = Object.keys(TM.FAILS).map(Number);     // tests 1, 4 and 6: the ones with failed runs
export const FAILS: Record<number, number[]> = TM.FAILS;
/** the beat each column of runs arrives on: one a half beat, then faster */
export const COL_AT: number[] = TM.COL_AT;
const FIRST = 150, MID = 153.5, TOTAL = 412;                // the eight rows are tests 150 to 157 of 412
const L8 = Math.log(8), L40 = Math.log(40);
/** how many rows the list shows on the way out: 8, then 40 (beat 28). From beat 28.5 the panel shows all 412. */
const rowsN = (f: number) => { const x = clamp01((f - TM.NUMBERS * FB + 1) / 13); return Math.exp(lerp(L8, L40, x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)); };   // it starts gently: the camera is close when it begins
const pitchOf = (n: number) => lerp(RP, 20, (Math.log(n) - L8) / (L40 - L8));
// the block: 412 tests as strips of 24 dots, 103 to a column, four columns. A strip is a matrix row at a third of its size.
const BLK = { x0: MX + 56, cp: 202.33, dp: DP / 3, y0: 166, rp: 780 / 102, per: 103, d: 4.4 };
const stripAt = (i: number) => ({ x: BLK.x0 + Math.floor(i / BLK.per) * BLK.cp, y: BLK.y0 + (i % BLK.per) * BLK.rp });
const BTOP = 166 - RP / 2 - HEADM, BBOT = 166 + 780 + RP / 2 + 20;      // the panel's top and bottom round the block
const K = { bg: "#161616", row: "#222220", line: "#30302E", text: "#ECEAE5", dim: "#8F8E89", dot: "#F6F5F1", bar: "#343432", wash: "rgba(255, 77, 31, 0.2)" };
const hash = (i: number) => { const x = Math.sin(i * 12.9898) * 43758.5453; return x - Math.floor(x); };

const STAY = [0, 2, 3, 5, 7], HELD = [1, 4, 6], STAY2 = [0, 2, 3, 4, 5, 7], HELD2 = [1, 6], CALL = [2.5, 3.5, 4.5];
const DROP = TM.DROP, BACK = TM.BACK;
/** which slot a row sits in from beat 36: its own; then (beat 37.5) the held ones under a line; then (46.5) one back */
export function slot(r: number, f: number) {
  const b = STAY.includes(r) ? STAY.indexOf(r) : 5.9 + HELD.indexOf(r);
  const c = STAY2.includes(r) ? STAY2.indexOf(r) : 6.9 + HELD2.indexOf(r);
  const own = FLAKY.includes(r) && f >= TM.HELD[0] * FB ? lerp(CALL[FLAKY.indexOf(r)], r, arr(f, TM.HELD[0], 8)) : r;    // the three come back from the call-out
  const turn = HELD.includes(r) ? HELD.indexOf(r) * 0.2 : 0.1 + STAY.indexOf(r) * 0.06;   // one after another, so each can be followed
  return lerp(lerp(own, b, arr(f, DROP + turn, 8)), c, arr(f, BACK, r === 4 ? 10 : 8));  // and the released test takes its time
}
// under "Held, not deleted" the matrix stays live: a new run every half beat from beat 38, thirteen of them
const TICK0 = TM.TICK0, NT = TM.NT, STEP = TM.TICK_STEP, RERUN0 = TM.RERUN0, RERUN1 = TM.RERUN1;
const LATE: Record<number, number[]> = TM.LATE;       // two of the held tests fail again on their new runs
const ORDERED = FLAKY.flatMap((r) => FAILS[r].map((c) => `${r}_${c}`));
const failed = (r: number, j: number) => (j < COLS ? !!FAILS[r]?.includes(j) : !!LATE[r]?.includes(j));
/** how far a row's window of 24 runs has moved on */
function windowAt(r: number, f: number) {
  const b = f / FB;
  const tk = b < TICK0 ? 0 : Math.min(NT, Math.floor((b - TICK0) / STEP) + 1);
  let k = tk > 0 ? tk - 1 + arr(f, TICK0 + (tk - 1) * STEP, 6) : 0;
  if (r === 4 && b >= RERUN0) k += COLS * clamp01((f - RERUN0 * FB) / ((RERUN1 - RERUN0) * FB));   // the fix: it runs 24 more, all passing
  return k;
}

/** one test's row: its name, its window of runs. `a` dims it; `s` and the offsets place a call-out */
function row(out: any[], key: string, r: number, f: number, y: number, o: { a?: number; fold?: number; nameA?: number; twinkle?: boolean; dotc?: string; dx?: number; lit?: number } = {}) {
  const a = o.a ?? 1, fold = o.fold ?? 0, kf = windowAt(r, f), dx = o.dx ?? 0;
  if ((o.nameA ?? 1) > 0) out.push(M(`${key}n`, MX + 28 + dx, y + 7.5, 21, NAMES[r], { color: K.text, opacity: a * (o.nameA ?? 1) }));
  for (let j = Math.floor(kf); j <= Math.floor(kf) + COLS; j++) {
    const pos = j - kf;                                                    // its place in the window of 24
    if (pos <= -1 || pos >= COLS) continue;
    const at = COL_AT[Math.min(j, COLS - 1)] + r * 0.035;                  // a column lands top to bottom
    if (kf === 0 && !on(f, at)) continue;
    const k = kf === 0 ? arr(f, at, 5) : 1, bad = failed(r, j), age = f - at * FB;
    const fresh = kf === 0 && bad && age < 9;                              // a failed run cannot make up its mind as it lands
    const breathe = bad && (o.lit ?? 0) > 0 ? 0.1 * (o.lit ?? 0) * Math.sin(f * 0.14 + j * 1.7) : 0;
    const edge = pos < 0 ? 1 + pos : pos > COLS - 1 ? COLS - pos : 1;      // leaving on the left, arriving on the right
    const ti = o.twinkle ? ORDERED.indexOf(`${r}_${j}`) : -1;
    const tw = ti < 0 ? 0 : clamp01(1 - Math.abs(f - (TM.TWINKLE + ti * TM.TWINKLE_STEP) * FB - 4) / 5);
    const x = lerp(colX(pos) + dx, dotX(), fold);
    const red = bad && fold < 0.5 && !(fresh && Math.floor(age / 2) % 2 === 1);
    const pop = kf > 0 && pos > COLS - 2 ? 0.8 * (pos - (COLS - 2)) / 2 : 0;       // the newest run in the window arrives large and settles
    out.push(D(`${key}d${j}`, x, y, lerp(DR, 9, fold) * k * (1 + 0.5 * tw + breathe + pop + (fresh ? 0.7 * (1 - age / 9) : 0)), red ? C.red : (o.dotc ?? K.dot), { opacity: a * edge * edge }));
  }
}

export function matrix(f: number) {
  const out: any[] = [], b = f / FB;
  const fold = arr(f, TM.PASSED[0], 9);
  if (b < TM.ANSWER || fold >= 1) return out;                       // after the fold the checks panel draws its own third row
  const n = rowsN(f), list = b >= TM.NUMBERS && b < TM.N412, block = b >= TM.N412 && b < TM.HELD[0], p = pitchOf(n);
  const back = arr(f, TM.HELD[0], 8), extra = 0.9 * RP * arr(f, DROP, 8);
  const i0 = Math.max(0, Math.ceil(MID - n / 2)), i1 = Math.min(TOTAL - 1, Math.floor(MID + n / 2 - 0.001));
  const yF = (i: number) => YC + (i - MID) * p;
  const top8 = MY, bot8 = MY + HEADM + 8 * RP + 20 + extra;
  let top = list ? yF(i0) - RP / 2 - HEADM : block ? BTOP : lerp(b >= TM.HELD[0] ? BTOP : top8, top8, b >= TM.HELD[0] ? back : 1);
  let bot = list ? yF(i1) + RP / 2 + 20 : block ? BBOT : lerp(b >= TM.HELD[0] ? BBOT : bot8, bot8, b >= TM.HELD[0] ? back : 1);
  let left = MX, right = MX + MW;
  if (fold > 0) { top = lerp(top, rowY(2) - ROW / 2, fold); bot = lerp(bot, rowY(2) + ROW / 2, fold); left = lerp(MX, PX, fold); right = lerp(MX + MW, PX + PW, fold); }
  const open = arr(f, TM.ANSWER, 9), fade = 1 - clamp01((f - TM.PASSED[0] * FB + 1) / 4), show = clamp01((f - TM.ANSWER * FB + 1) / 5);
  if (open < 1) {                                            // the mark opens into its own panel: its box grows out of the brackets
    left = lerp(STING.x - MARK.w / 2, left, open); right = lerp(STING.x + MARK.w / 2, right, open);
    top = lerp(STING.y - MARK.h / 2, top, open); bot = lerp(STING.y + MARK.h / 2, bot, open);
  }
  const glass = clamp01((fold - 0.65) / 0.35);                 // it stays Stet's dark panel until it is the size of a row, then turns to glass
  if (glass > 0) out.push(R("mbgw", left, top, right - left, bot - top, { ...GLASS, borderRadius: 14, boxSizing: "border-box", opacity: glass }));
  out.push(R("mbg", left, top, right - left, bot - top, { background: K.bg, borderRadius: 14, opacity: show * (1 - glass), boxShadow: "0 30px 70px rgba(20, 20, 40, 0.24)" }));
  const dotc = glass > 0.5 ? C.ink : K.dot;

  // ---- the head: the mark, what this is, and how many runs are drawn
  if (fade > 0 && on(f, TM.MARK_FIRES)) {
    const cols = COL_AT.filter((a) => on(f, a)).length, ran = Math.round(372 * clamp01((f - TM.RUN * FB) / FB));
    const rerun = Math.round(COLS * clamp01((f - RERUN0 * FB) / ((RERUN1 - RERUN0) * FB)));
    const txt = b >= RERUN0 ? `a81c3e0 · ${rerun} of 24 passed` : b >= DROP ? "passing · merge allowed" : b >= TM.RAN && b < TM.HELD[0] ? "ran in 6 min 12 s" : b >= TM.RUN && b < TM.RAN ? `running · ${Math.floor(ran / 60)}:${String(ran % 60).padStart(2, "0")}` : b >= TM.N412 && b < TM.RUN ? "412 tests · 24 runs each"
      : b >= TICK0 ? "last 24 runs · 4f2a91c" : `${cols} run${cols === 1 ? "" : "s"} each · 4f2a91c`;
    if (f >= TM.ANSWER * FB + 16) {
      // the mark fires each column of runs: it pulses, and a spark crosses the head of the panel to the column's place
      let pulse = 0;
      if (b < TM.INSIDE) COL_AT.forEach((at, c) => {
        const age = f - (at * FB - 5);
        if (age < 0 || age > 7) return;
        pulse = Math.max(pulse, 1 - Math.abs(age - 1) / 3);
        if (age < 5) out.push(D(`sp${c}`, lerp(BADGE.x + 20, colX(c), age / 5), top + 27 + (age / 5) ** 2 * 26, 3.4, K.dot, { opacity: 0.9 }));
      });
      out.push(<div key="bdg" style={{ opacity: fade }}>{brackets("bd", BADGE.x, top + 27, BADGE.w + 6 * Math.max(0, pulse), BADGE.h, K.text, { sw: 3.5, arm: 8 })}</div>);
      out.push(D("bdd", BADGE.x, top + 27, BADGE.r * (1 + 0.5 * Math.max(0, pulse)), C.red, { opacity: fade }));
    }
    out.push(T("mh", MX + 76, top + 35, 22, "Tests", { opacity: fade, color: K.text }));
    const chip = b >= DROP;                                   // while tests are held, the head says what holding buys
    out.push(M("mr", MX + MW - 28 - mw(txt, 18), top + 34, 18, txt, { color: chip ? K.text : K.dim, opacity: fade }));
    if (chip) out.push(D("mrd", MX + MW - 28 - mw(txt, 18) - 16, top + 27, 5.5, K.dot, { opacity: fade }));
  }

  /** the forty-row list: each column of runs one dotted line, each name a grey bar */
  const listRows = (alpha: number) => {
    const sw = Math.min(2 * DR, p * 0.62), y0 = yF(i0), y1 = yF(i1), hb = Math.min(10, p * 0.46);
    let bars = "";
    for (let i = i0; i <= i1; i++) { const w = (0.34 + 0.6 * hash(i)) * 300; bars += `M${MX + 28},${(yF(i) - hb / 2).toFixed(2)}h${w.toFixed(1)}v${hb.toFixed(2)}h${(-w).toFixed(1)}z`; }
    const lines: any[] = [];
    for (let c = 0; c < COLS; c++) lines.push(<line key={c} x1={colX(c)} x2={colX(c)} y1={y0} y2={y1 + 0.05} stroke={K.dot} strokeWidth={sw} strokeLinecap="round" strokeDasharray={`0.01 ${(p - 0.01).toFixed(4)}`} />);
    return [
      <svg key="field" style={{ position: "absolute", left: 0, top: 0, opacity: alpha }} width={1920} height={1080} viewBox="0 0 1920 1080">
        <path d={bars} fill={K.bar} opacity={clamp01((f - TM.NUMBERS * FB - 3) / 8)} />
        <g>{lines}</g>
      </svg>,
      ...FLAKY.flatMap((r) => FAILS[r].map((c) => D(`ff${r}_${c}`, colX(c), yF(FIRST + r), sw / 2, C.red, { opacity: alpha }))),
    ];
  };
  /** the wall, whole, at one strength: for the moment it gives way to the eight again */
  const wall = (alpha: number) => {
    const y1 = BLK.y0 + (BLK.per - 1) * BLK.rp, lines: any[] = [];
    for (let col = 0; col < 4; col++) for (let c = 0; c < COLS; c++) {
      const x = BLK.x0 + col * BLK.cp + c * BLK.dp;
      lines.push(<line key={`${col}_${c}`} x1={x} x2={x} y1={BLK.y0} y2={y1 + 0.05} stroke={K.dot} strokeWidth={BLK.d} strokeLinecap="round" strokeDasharray={`0.01 ${(BLK.rp - 0.01).toFixed(4)}`} />);
    }
    return <svg key="wall" style={{ position: "absolute", left: 0, top: 0, opacity: alpha }} width={1920} height={1080} viewBox="0 0 1920 1080"><g>{lines}</g></svg>;
  };

  if (block) {
    // ---- all of it: 412 strips of 24 dots. Every dot is one run. They run top to bottom (beat 29 to 30).
    const k = arr(f, TM.N412, 7), dim = arr(f, TM.N3, 7), y1 = BLK.y0 + (BLK.per - 1) * BLK.rp;
    const melt = clamp01((f - TM.N412 * FB) / 12);               // the forty rows squeeze into the first strip as the wall comes up
    if (melt < 1) out.push(<div key="melt" style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, opacity: 1 - melt, transformOrigin: `${colX(0)}px 556px`, transform: `scaleX(${lerp(1, 1 / 3, melt).toFixed(4)})` }}>{listRows(1)}</div>);
    const run = clamp01((f - TM.RUN * FB) / FB), ys = lerp(BLK.y0 - 4, y1, run);
    const lines: any[] = [], wait: any[] = [];
    for (let col = 0; col < 4; col++) for (let c = 0; c < COLS; c++) {
      const x = BLK.x0 + col * BLK.cp + c * BLK.dp, dash = `0.01 ${(BLK.rp - 0.01).toFixed(4)}`;
      if (run < 1) wait.push(<line key={`w${col}_${c}`} x1={x} x2={x} y1={BLK.y0} y2={y1 + 0.05} stroke={K.dot} strokeWidth={BLK.d} strokeLinecap="round" strokeDasharray={dash} />);
      if (ys >= BLK.y0) lines.push(<line key={`${col}_${c}`} x1={x} x2={x} y1={BLK.y0} y2={ys + 0.05} stroke={K.dot} strokeWidth={BLK.d} strokeLinecap="round" strokeDasharray={dash} />);
    }
    out.push(
      <svg key="block" style={{ position: "absolute", left: 0, top: 0, transform: `scale(${lerp(1.05, 1, k)})`, transformOrigin: `${MX + MW / 2}px 556px` }} width={1920} height={1080} viewBox="0 0 1920 1080">
        <g opacity={0.26 * melt}>{wait}</g>
        <g opacity={lerp(1, 0.2, dim)}>{lines}</g>
      </svg>,
    );
    FLAKY.forEach((r, j) => {
      const at = stripAt(FIRST + r);
      if (ys >= at.y && b < TM.N3) FAILS[r].forEach((c) => out.push(D(`bf${r}_${c}`, at.x + c * BLK.dp, at.y, BLK.d / 2 + 0.3, C.red)));
      if (b >= TM.N3) {
        // the three flaky tests come out of the block at full size: the same rows the film has been watching
        const kc = arr(f, TM.N3 + j * 0.125, 8), y = slotY(CALL[j]), s = lerp(1 / 3, 1, kc);
        const tx = (at.x - colX(0)) * (1 - kc), ty = (at.y - y) * (1 - kc);
        const inner: any[] = [R(`cb${r}`, MX + 14, y - 23, MW - 28, 46, { background: K.row, borderRadius: 8, opacity: kc })];
        row(inner, `c${r}`, r, f, y, { nameA: clamp01(kc * 1.5 - 0.5) });
        const ks = shut(f, TM.SHUT3 + j * TM.SHUT_STEP, 6);
        if (ks > 0) inner.push(...brackets(`cbk${r}`, MX + MW / 2, y, MW - 36, 44, K.text, { sw: 4, arm: 12, kl: ks, kr: ks, spread: 90 }));
        out.push(<div key={`call${r}`} style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: `${colX(0)}px ${y}px`, transform: `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${s.toFixed(4)})` }}>{inner}</div>);
      }
    });
    return out;
  }
  if (list) {
    // ---- backing out: forty tests
    out.push(...listRows(1));
    const nameOut = 1 - clamp01((f - TM.NUMBERS * FB) / 8);
    if (nameOut > 0) NAMES.forEach((nm, r) => out.push(M(`mn${r}`, MX + 28, yF(FIRST + r) + 7.5, 21 * Math.min(1, p / RP + 0.25), nm, { color: K.text, opacity: nameOut })));
    return out;
  }

  // ---- close: eight tests, each run a dot
  if (b >= TM.HELD[0] && b < TM.HELD[0] + 0.6) out.push(wall(0.2 * (1 - clamp01((f - TM.HELD[0] * FB) / 12))));     // the wall gives way to the eight
  const lit = arr(f, TM.WASH, 7) * (1 - clamp01((f - TM.FLAKE_OFF * FB) / 6));   // the dimming and the washes are gone before the list takes over, so nothing jumps there
  const words = arr(f, TM.INSIDE, 4) * (1 - arr(f, TM.WORDS_BACK, 3));           // two rows make room for the words that are said about the others
  const held = b >= DROP ? arr(f, DROP, 8) : 0;
  if (held > 0 && fade > 0) {
    const ly = slotY(lerp(5, 6, arr(f, BACK, 8))) - RP / 2 + 8;
    out.push(R("hl", MX + 28, ly, MW - 56, 1.5, { background: K.line, opacity: held * fade }));
    out.push(M("ht", MX + 28, ly + 29, 19, `held · ${b >= BACK ? 2 : 3}`, { color: "#B9B7B1", opacity: held * fade }));
    const notes = ["still runs", "can't block a merge", "issue opened"];
    let x = MX + MW - 28;
    for (let i = notes.length - 1; i >= 0; i--) {
      const t = i < notes.length - 1 ? notes[i] + " · " : notes[i], at = TM.NOTES + i * 0.5;
      x -= mw(t, 19);
      if (on(f, at)) out.push(M(`hn${i}`, x, ly + 29, 19, t, { color: "#B9B7B1", opacity: clamp01((f - at * FB + 1) / 3) * fade }));
    }
  }
  const focus = arr(f, TM.FIXED, 6) * (1 - arr(f, TM.FOCUS_OFF, 6));        // the release: every test but the fixed one steps back
  for (let r = 0; r < 8; r++) {
    const flaky = FLAKY.includes(r);
    const y = lerp(slotY(slot(r, f)), rowY(2), fold);
    const lift = flaky ? Math.sin(Math.PI * arr(f, DROP + HELD.indexOf(r) * 0.2, 8)) : 0;                 // travelling to the held group, a row lifts off the panel
    if (lift > 0.02 && fade > 0) out.push(R(`lf${r}`, MX + 10, y - 24, MW - 20, 48, { background: K.row, borderRadius: 9, opacity: Math.min(1, lift * 1.6), boxShadow: "0 10px 26px rgba(0, 0, 0, 0.5)" }));
    if (r === 4 && focus > 0) out.push(R("fxw", MX + 14, y - 22, MW - 28, 44, { background: "rgba(246, 245, 241, 0.10)", borderRadius: 8, opacity: focus }));
    const arrive = b >= TM.HELD[0] && !flaky ? clamp01((f - TM.HELD[0] * FB - 2) / 5) : 1;         // the other five come back round the three
    const a = (flaky ? 1 : lerp(1, 0.42, lit)) * arrive * (r === 4 ? 1 : lerp(1, 0.4, focus)) * (r === 2 || r === 3 ? 1 - words : 1);
    const sh = f - TM.CAUGHT * FB, dx = flaky && sh >= 0 && sh < 14 ? Math.sin(sh * 2.2) * 9 * (1 - sh / 14) : 0;     // caught: "That's a flake."
    if (flaky && lit > 0) out.push(R(`mw${r}`, MX + 14 + dx, y - 22, MW - 28, 44, { background: K.wash, borderRadius: 8, opacity: lit }));
    const nameAt = TM.MARK_FIRES + r * 0.045;
    row(out, `m${r}`, r, f, y, { a, fold, dotc, dx, lit: flaky ? lit : 0, twinkle: b >= TM.TWINKLE && b < TM.NUMBERS, nameA: on(f, nameAt) ? clamp01((f - nameAt * FB + 1) / 3) * fade : 0 });
    // the hold: the brackets that shut on each flaky test in the block stay on it; one pair opens again (beat 46)
    if (flaky && b >= TM.HELD[0] && fade > 0) {
      const ko = r === 4 ? arr(f, TM.RELEASED[0], 6) : 0;
      // a held test fails again: its brackets catch it (they squeeze), and nothing above them changes
      const caught = Math.max(0, ...(LATE[r] ?? []).map((j) => 1 - Math.abs(f - (TICK0 + (j - COLS) * STEP) * FB - 3) / 6));
      if (ko < 1) out.push(<div key={`hb${r}`} style={{ opacity: (1 - ko) * fade * (r === 4 ? 1 : lerp(1, 0.4, focus)) }}>{brackets(`hbk${r}`, MX + MW / 2, y, MW - 36 + ko * 70 - 16 * caught, 44, K.text, { sw: 4, arm: 12 })}</div>);
    }
  }
  // ---- the fix: a commit appears beside the question, flies to its test, and the test runs again
  if (b >= TM.COMMIT && b < RERUN0) {
    const k = arr(f, TM.COMMIT, 6), e = clamp01((f - TM.FLY * FB) / 6) ** 2, t = "a81c3e0  fix: debounce race", w = mw(t, 18) + 64;
    const x = lerp(480, MX + 20, e), y = lerp(706 + (1 - k) * 10, slotY(slot(4, f)) - 22, e), o = clamp01((f - TM.COMMIT * FB + 1) / 3) * (1 - e);
    out.push(R("fxb", x, y, w, 44, { background: K.bg, borderRadius: 22, opacity: o }));
    out.push(D("fxd", x + 24, y + 22, 6, K.dot, { opacity: o }));
    out.push(M("fxt", x + 42, y + 28, 18, t, { color: K.text, opacity: o }));
  }
  return out;
}
