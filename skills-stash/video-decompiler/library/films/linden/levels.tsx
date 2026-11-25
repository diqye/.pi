// The worlds. Each is a canvas 1920 by 1080, drawn in its own units, and each holds the one before it in a slot:
// the paper is the cover of a book (1), the book's ground is a tile of a wall (2), the wall is in the window of the
// mark on a library card (3), the card's ground is a card on a ground five times over (4 to 8), and the last ground
// is in the window of the mark (9). `world(k, f, d)` draws world k with every world inside it that is big enough to
// see; d is how large world k is on screen (1 = it fills the frame).
import { TIMES as TM } from "./kit/times.gen";
import { C, FB, GROT, L, M, R, SERIF, arr, clamp01, glide, outCubic, pic, ramp, rnd } from "./kit/core";

export type Slot = { x: number; y: number; w: number; rot: number; px: number; py: number };       // where the world before sits, how it is turned, and about what point
export const SLOTS: Record<number, Slot> = {
  2: { x: 768, y: 432, w: 384, rot: 0, px: 960, py: 540 },
  3: { x: 520, y: 309, w: 512, rot: -3, px: 960, py: 540 },
  4: { x: 130, y: 440, w: 800, rot: 2.5, px: 530, py: 665 },
  5: { x: 1000, y: 112, w: 780, rot: -3, px: 1390, py: 331.4 },
  6: { x: 150, y: 250, w: 860, rot: 1.5, px: 580, py: 491.9 },
  7: { x: 960, y: 480, w: 820, rot: -2, px: 1370, py: 710.6 },
  8: { x: 140, y: 128, w: 800, rot: 3, px: 540, py: 353 },
  9: { x: 620, y: 150, w: 680, rot: 0, px: 960, py: 341.25 },
};
export const LAST = 9;
const INK = C.ink, CREAM = C.cream;
const PAPERS = 24;                                                    // media/art/papers/01.jpg to 24.jpg; 01 is the one the film opens inside (media/art/hero.jpg is the same sheet, large)
const pad2 = (n: number) => String(n).padStart(2, "0");

/** seat the world before in its slot */
function seat(key: string, s: Slot, inner: any, radius = 0, shadow = "none") {
  return (
    <div key={key} style={{ position: "absolute", left: s.x, top: s.y, width: s.w, height: (s.w * 9) / 16, overflow: "hidden", borderRadius: radius, boxShadow: shadow, transform: s.rot ? `rotate(${s.rot}deg)` : "none", transformOrigin: `${s.px - s.x}px ${s.py - s.y}px` }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: "0 0", transform: `scale(${(s.w / 1920).toFixed(6)})` }}>{inner}</div>
    </div>
  );
}
/** a stamp: it lands in one frame, a little big, and settles */
function stamp(key: string, x: number, y: number, text: string, size: number, color: string, f: number, beat: number, turn = -6) {
  const a = f - beat * FB;
  if (a < 0) return null;
  const s = 1 + 0.28 * Math.exp(-a / 3);
  return <div key={key} style={{ position: "absolute", left: x, top: y, padding: `${size * 0.16}px ${size * 0.34}px`, border: `${Math.max(2, size * 0.075)}px solid ${color}`, borderRadius: size * 0.16, fontFamily: "Geist Mono", fontWeight: 600, fontSize: size, lineHeight: `${size}px`, letterSpacing: "0.04em", color, whiteSpace: "nowrap", transform: `rotate(${turn}deg) scale(${s.toFixed(3)})`, opacity: 0.92 }}>{text}</div>;
}
/** the mark: two Ls round a window. (x, y, w) is the window; t the thickness of the strokes; g the gap between window and stroke */
export function mark(key: string, x: number, y: number, w: number, t: number, g: number, color: string, a = 1) {
  const h = (w * 9) / 16, x0 = x - g - t, y0 = y - g - t, W = w + 2 * (g + t), H = h + 2 * (g + t), cut = 0.2;
  return [
    R(`${key}a`, x0, y0 + H * cut, t, H * (1 - cut), { background: color, opacity: a }), R(`${key}b`, x0, y0 + H - t, W * (1 - cut), t, { background: color, opacity: a }),       // the L at the bottom left
    R(`${key}c`, x0 + W * cut, y0, W * (1 - cut), t, { background: color, opacity: a }), R(`${key}d`, x0 + W - t, y0, t, H * (1 - cut), { background: color, opacity: a }),       // the L turned round, at the top right
  ];
}

// ---- world 1: one book on a ground. The same drawing, smaller and plainer, is every other tile of the wall.
const BOOK = { x: 660, y: 140, w: 600, h: 800, spine: 64 };
const DUE = ["02 MAR", "19 APR", "07 JUN", "23 SEP"];
function tile(f: number, ground: string, paper: string, hero: boolean, d: number, next: string | null = null, nk = 0) {
  const out: any[] = [R("g", 0, 0, 1920, 1080, { background: ground })];
  if (hero) {
    const cap = ground === C.cream ? INK : CREAM;
    ["One", "book"].forEach((w, i) => { const k = arr(f, TM.BOOK + 0.25 + 0.3 * i, 16); if (k > 0) out.push(L(`cap${i}`, 96, 300 + i * 178 + (1 - k) * 36, 540, 190, w, { fontFamily: GROT, fontWeight: 800, letterSpacing: "-0.04em", color: cap, textAlign: "left", opacity: ramp(f, TM.BOOK + 0.25 + 0.3 * i, 8) })); });
    // the date slip: stamped dates, and today's lands as the view does
    out.push(
      <div key="slip" style={{ position: "absolute", left: 1404, top: 236, width: 330, height: 500, background: "#F6EEDC", borderRadius: 6, boxShadow: "0 18px 40px rgba(0, 0, 0, 0.25)", transform: "rotate(5deg)" }}>
        {M("h", 34, 62, 27, "DATE DUE", { color: INK, letterSpacing: "0.14em", fontWeight: 500 })}
        {R("r", 30, 84, 270, 3, { background: INK, opacity: 0.8 })}
        {DUE.map((t, i) => M(`d${i}`, 40 + (i % 2) * 14, 150 + i * 70, 36, t, { color: i % 2 ? C.cobalt : C.tomato, fontWeight: 600, letterSpacing: "0.03em", opacity: 0.82, transform: `rotate(${[-3, 2, -1.5, 3][i]}deg)` }))}
        {[0, 1, 2, 3, 4].map((i) => R(`l${i}`, 30, 166 + i * 70, 270, 1.5, { background: INK, opacity: 0.18 }))}
        {stamp("today", 30, 396, "12 NOV", 38, C.tomato, f, TM.BOOK, -5)}
      </div>,
    );
  }
  out.push(R("pg", BOOK.x + 12, BOOK.y + 10, BOOK.w, BOOK.h, { background: "#EFE6D2", borderRadius: 8, boxShadow: "0 34px 70px rgba(0, 0, 0, 0.34), 0 6px 16px rgba(0, 0, 0, 0.2)" }));
  out.push(
    <div key="cover" style={{ position: "absolute", left: BOOK.x, top: BOOK.y, width: BOOK.w, height: BOOK.h, borderRadius: 8, overflow: "hidden", background: "#2A2521" }}>
      {pic("p", paper, BOOK.spine, 0, BOOK.w - BOOK.spine, BOOK.h)}
      {next ? pic("p2", next, BOOK.spine, BOOK.h * (1 - nk), BOOK.w - BOOK.spine, BOOK.h) : null}
      {R("cr", BOOK.spine - 2, 0, 5, BOOK.h, { background: "rgba(0, 0, 0, 0.3)" })}
      <div style={{ position: "absolute", left: 172, top: 110, width: 320, height: 130, background: "#F6EEDC", borderRadius: 7, boxShadow: "0 3px 10px rgba(0, 0, 0, 0.3)", opacity: hero ? ramp(f, TM.LABEL, 7) : 1, transform: hero ? `scale(${(1.16 - 0.16 * arr(f, TM.LABEL, 11)).toFixed(3)})` : "none" }}>
        {d * 17 > 5 ? M("n", 0, 40, 17, "LINDEN LIBRARY · 761", { color: INK, letterSpacing: "0.1em", width: 320, textAlign: "center" }) : R("nb", 60, 28, 200, 8, { background: INK, opacity: 0.5 })}
        {hero ? L("t", 0, 56, 320, 44, "Start anywhere.", { fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, letterSpacing: "-0.01em", color: INK }) : R("tb", 40, 70, 240, 22, { background: INK, opacity: 0.75, borderRadius: 3 })}
      </div>
    </div>,
  );
  return out;
}

// ---- world 2: the wall. Seven by seven tiles, a book on each; two tiles are words. Some covers change while the camera crosses.
const GROUNDS = [C.cobalt, C.sun, C.forest, C.tomato, C.rose, C.cream, C.ink];
const WAVES = TM.FLIPS as number[];
function wall(f: number, inner: any, d: number) {
  const out: any[] = [];
  for (let r = -1; r <= 5; r++) for (let c = -1; c <= 5; c++) {
    if (c === 2 && r === 2) continue;
    if ((r === 2 || r === 3) && c === 4) continue;                   // the rest of the block of words
    if (r === 3 && c === 3) continue;
    const x = c * 384, y = r * 216, n = (c + 1) * 7 + (r + 1);
    if (r === 2 && c === 3) {                                        // four tiles are one block of words; it lands with the view, as a stamp does
      out.push(R("wt", x, y, 768, 432, { background: CREAM }));
      const a = f - TM.WALL * FB, sc = a >= 0 ? 1 + 0.16 * Math.exp(-a / 3) : 1;
      ["One of", "400,000."].forEach((w, i) => out.push(L(`wt${i}`, x + 38, y + 38 + i * 176, 720, 170, w, { fontFamily: GROT, fontWeight: 800, letterSpacing: "-0.05em", color: INK, textAlign: "left", transform: `scale(${sc.toFixed(3)})`, transformOrigin: `346px ${178 - i * 176}px` })));
      continue;
    }
    const turn = (q: number, j: number) => 2 + ((q - 2 + 5 + j) % (PAPERS - 1));
    let p = 2 + ((c * 5 + r * 7 + 49) % (PAPERS - 1)), nx = 0, nk = 0;      // which paper is on this cover; a wave of the camera's crossing may slide the next one over it
    WAVES.forEach((b, j) => {
      if (rnd(n * 3 + j) > 0.42) return;
      const k = clamp01((f - b * FB - rnd(n + j * 11) * 16) / 18);
      if (k >= 1) p = turn(p, j); else if (k > 0) { nx = turn(p, j); nk = outCubic(k); }
    });
    const g = GROUNDS[(((c * 2 + r * 3) % 7) + 7) % 7];
    out.push(
      <div key={`t${n}`} style={{ position: "absolute", left: x, top: y, width: 384, height: 216, overflow: "hidden", background: g }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: "0 0", transform: "scale(0.2)" }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080 }}>{tile(f, g, `art/papers/${pad2(p)}.jpg`, false, d * 0.2, nx ? `art/papers/${pad2(nx)}.jpg` : null, nk).slice(1)}</div>
        </div>
      </div>,
    );
  }
  out.push(seat("in", SLOTS[2], inner));
  return out;
}

// ---- world 3: the card. The wall is in the window of the mark; a name is signed.
const CARD = { x: 460, y: 225, w: 1000, h: 630 };
function card(f: number, inner: any, _d: number) {
  const out: any[] = [R("g", 0, 0, 1920, 1080, { background: C.cobalt })];
  const s = SLOTS[3], lx = s.x - CARD.x, ly = s.y - CARD.y, sign = clamp01((f - (TM.CARD + 1) * FB) / 40);
  const t = f - TM.CARD * FB, fl = glide(f, TM.CARD + 0.15, 44) * (1 - glide(f, TM.OUT4 - 0.7, 24));          // held, the card floats; it is flat again before the view backs out of it
  const sh = clamp01((f - (TM.CARD + 2.6) * FB) / 46);                                                         // light crosses it once
  out.push(
    <div key="cap" style={{ position: "absolute", left: 0, top: 64, width: 1920, height: 140, display: "flex", flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 34 }}>
      {"All yours, with this.".split(" ").map((w, i) => { const b = TM.CARD + 0.3 + i * 0.22, k = arr(f, b, 16); return <div key={i} style={{ flex: "none", fontFamily: GROT, fontWeight: 800, fontSize: 108, lineHeight: "130px", letterSpacing: "-0.04em", color: CREAM, whiteSpace: "nowrap", opacity: ramp(f, b, 8), transform: `translateY(${((1 - k) * 30).toFixed(1)}px)` }}>{w}</div>; })}
    </div>,
  );
  out.push(
    <div key="card" style={{ position: "absolute", left: CARD.x, top: CARD.y, width: CARD.w, height: CARD.h, borderRadius: 38, background: "#F6EEDC", boxShadow: "0 50px 110px rgba(0, 0, 20, 0.45), 0 8px 22px rgba(0, 0, 20, 0.25)", transform: `perspective(1700px) rotate(${s.rot}deg) rotateY(${(8 * Math.sin(t / 52) * fl).toFixed(3)}deg) rotateX(${(4 * Math.sin(t / 71 + 1) * fl).toFixed(3)}deg)` }}>
      {seat("in", { x: lx, y: ly, w: s.w, rot: 0, px: 0, py: 0 }, inner)}
      {mark("mk", lx, ly, s.w, 22, 10, INK)}
      {L("n1", 632, 96, 330, 70, "Linden", { fontFamily: GROT, fontWeight: 800, letterSpacing: "-0.04em", color: INK, textAlign: "left" })}
      {L("n2", 632, 164, 330, 70, "Library", { fontFamily: GROT, fontWeight: 800, letterSpacing: "-0.04em", color: INK, textAlign: "left" })}
      {stamp("mb", 634, 262, "MEMBER", 20, C.tomato, f, TM.CARD, -4)}
      <div style={{ position: "absolute", left: 632, top: 306, width: 330 * sign, height: 70, overflow: "hidden" }}>{L("sg", 0, 4, 330, 46, "Noor Adeyemi", { fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, color: C.cobalt, textAlign: "left" })}</div>
      {R("ul", 632, 372, 300, 2, { background: INK, opacity: 0.35 })}
      {M("no", 636, 420, 24, "2046 1009 3577", { color: INK, letterSpacing: "0.06em" })}
      {L("yo", lx - 32, ly + 288 + 54, 400, 34, "Yours to open.", { fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, color: INK, textAlign: "left" })}
      {sh > 0 && sh < 1 ? <div style={{ position: "absolute", left: 0, top: 0, width: CARD.w, height: CARD.h, borderRadius: 38, overflow: "hidden" }}>{R("sh", -700 + 2100 * sh, -100, 420, CARD.h + 200, { background: "linear-gradient(100deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5) 50%, rgba(255, 255, 255, 0))", transform: "skewX(-18deg)" })}</div> : null}
      {Array.from({ length: 34 }, (_, i) => R(`bc${i}`, 636 + i * 9, 470, 2 + 4 * (rnd(i + 3) > 0.55 ? 1 : 0) + 1.5 * rnd(i), 66, { background: INK }))}
    </div>,
  );
  return out;
}

// ---- worlds 4 to 8: what a library holds. Each ground is a card on the next; on each lies one plate, a word and its number.
// No two are laid out alike: [where the plate's middle is, its height, its turn, the side it comes in from (x, y)],
// [the word's box: x, y, alignment], [where the number is stamped, its turn].
type Lend = { word: string; num: string; ground: string; ink: string; hit: string; plate: number; pw: number; ph: number; at: [number, number, number, number, number, number]; wd: [number, number, "left" | "right"]; nm: [number, number, number] };
export const LENDS: Lend[] = [
  { word: "Birds", num: "598", ground: C.sun, ink: INK, hit: C.cobalt, plate: 1, pw: 947, ph: 1400, at: [1440, 540, 780, 4, 1, 0], wd: [126, 96, "left"], nm: [700, 140, -6] },
  { word: "Stars", num: "523", ground: C.forest, ink: CREAM, hit: C.sun, plate: 2, pw: 1123, ph: 1400, at: [500, 590, 800, -5, -0.3, 1], wd: [894, 770, "right"], nm: [1000, 640, 5] },
  { word: "Music", num: "780", ground: C.rose, ink: INK, hit: C.cobalt, plate: 3, pw: 944, ph: 1400, at: [1470, 520, 820, 6, 0.3, -1], wd: [126, 800, "left"], nm: [760, 850, -5] },
  { word: "Gardens", num: "635", ground: C.tomato, ink: CREAM, hit: CREAM, plate: 4, pw: 1046, ph: 1400, at: [470, 520, 840, -3, -1, 0], wd: [894, 110, "right"], nm: [820, 330, 6] },
  { word: "Moths", num: "595.7", ground: C.ink, ink: CREAM, hit: C.sun, plate: 5, pw: 983, ph: 1400, at: [1430, 560, 800, 5, 0.6, 0.8], wd: [126, 780, "left"], nm: [800, 660, -6] },
];
function lend(k: number, f: number, inner: any, _d: number) {
  const q = LENDS[k - 4], s = SLOTS[k], land = TM.LANDS[k - 4], out: any[] = [R("g", 0, 0, 1920, 1080, { background: q.ground })];
  out.push(seat("in", s, inner, 26, "0 40px 90px rgba(0, 0, 0, 0.38), 0 6px 18px rgba(0, 0, 0, 0.22)"));
  // the plate: it lies nearer the eye than the ground, so it comes in from its side, large and soft, and settles as the view lands
  const [cx, cy, ph, turn, ex, ey] = q.at, k1 = outCubic(clamp01((f - (land - 1.5) * FB) / (1.5 * FB))), pw = (ph * q.pw) / q.ph, far = 1 - k1;
  out.push(
    <div key="pl" style={{ position: "absolute", left: cx - pw / 2 - 16 + far * ex * 280, top: cy - ph / 2 - 16 + far * ey * 280, width: pw + 32, height: ph + 32, background: "#F6EEDC", boxShadow: "0 40px 90px rgba(0, 0, 0, 0.4)", transform: `rotate(${(turn + far * 5 * Math.sign(turn)).toFixed(2)}deg) scale(${(1 + 0.16 * far).toFixed(3)})`, filter: k1 < 0.96 ? `blur(${(7 * far).toFixed(1)}px)` : "none" }}>
      {pic("pi", `art/plates/${pad2(q.plate)}.jpg`, 16, 16, pw, ph)}
    </div>,
  );
  const kw = arr(f, land - 0.38, 15);
  if (kw > 0) out.push(L("w", q.wd[0], q.wd[1] + (1 - kw) * 40, 900, 210, q.word, { fontFamily: GROT, fontWeight: 800, letterSpacing: "-0.045em", color: q.ink, textAlign: q.wd[2], opacity: ramp(f, land - 0.38, 4) }));
  out.push(stamp("num", q.nm[0], q.nm[1], q.num, 88, q.hit, f, land, q.nm[2]));
  return out;
}

// ---- world 9: the mark, the name, the line. The window ends on the paper the film began inside.
function end(f: number, inner: any, _d: number) {
  const s = SLOTS[9], out: any[] = [R("g", 0, 0, 1920, 1080, { background: CREAM })];
  out.push(seat("in", s, inner));
  const beats = TM.SWATCH as number[], n = beats.filter((b) => f >= b * FB).length;              // paper after paper in the window, each sliding up over the last
  if (n > 0) {
    const idx = [8, 6, 22, 24, 1], a = f - beats[n - 1] * FB, k = outCubic(clamp01((a + 1) / 14)), h = (s.w * 9) / 16;
    out.push(
      <div key="sw" style={{ position: "absolute", left: s.x, top: s.y, width: s.w, height: h, overflow: "hidden" }}>
        {n > 1 ? pic("p0", `art/papers/${pad2(idx[n - 2])}.jpg`, 0, 0, s.w, h) : null}
        {pic("p1", `art/papers/${pad2(idx[n - 1])}.jpg`, 0, h * (1 - k), s.w, h)}
      </div>,
    );
  }
  // the two Ls of the name and the two Ls of the mark light together, once: that is what the mark is made of
  const t = f - (TM.END + 1.1) * FB, lit = t > 0 ? Math.sin(Math.PI * clamp01(t / 44)) ** 2 : 0, mix = (a: number[], b: number[]) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * lit)).join(",")})`;
  const LL = mix([22, 19, 15], [228, 71, 47]);
  out.push(...mark("mk", s.x, s.y, s.w, 32, 16, LL));
  if (f >= TM.END * FB) {
    const sc = 1 + 0.16 * Math.exp(-(f - TM.END * FB) / 3), part = (w: string, c: string) => <span style={{ color: c }}>{w}</span>;
    out.push(
      <div key="nm" style={{ position: "absolute", left: 0, top: 610, width: 1920, height: 170, textAlign: "center", fontFamily: GROT, fontWeight: 800, fontSize: 140, lineHeight: "170px", letterSpacing: "-0.035em", color: INK, whiteSpace: "pre", transform: `scale(${sc.toFixed(3)})` }}>
        {part("L", LL)}{part("inden ", INK)}{part("L", LL)}{part("ibrary", INK)}
      </div>,
    );
  }
  const kl = arr(f, TM.END + 1.6, 18);
  if (kl > 0) out.push(L("ln", 0, 806 + (1 - kl) * 20, 1920, 80, "Yours to open.", { fontFamily: SERIF, fontStyle: "italic", fontWeight: 500, color: INK, opacity: ramp(f, TM.END + 1.6, 9) }));
  return out;
}

/** world k and everything inside it that is big enough to see. d: how large world k is on screen (1 = it fills the frame) */
export function world(k: number, f: number, d: number): any[] {
  const di = k > 1 ? (d * SLOTS[k].w) / 1920 : 0;
  const inner = k > 1 && di * 1920 > 26 ? world(k - 1, f, di) : null;
  if (k === 1) return tile(f, C.tomato, d > 1.15 ? "art/hero.jpg" : "art/papers/01.jpg", true, d);
  if (k === 2) return wall(f, inner, d);
  if (k === 3) return card(f, inner, d);
  if (k === LAST) return end(f, inner, d);
  return lend(k, f, inner, d);
}
