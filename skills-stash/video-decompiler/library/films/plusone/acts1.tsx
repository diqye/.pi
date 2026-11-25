// Beats 0 to 20, and what runs through the whole film: the group chat, the line that is typed, the line becoming the
// card, the large words, and the pointer.
import { LINE, TIMES as TM } from "./kit/times.gen";
import { C, D, FB, L, M, R, SERIF, T, arr, clamp01, glide, inOutCubic, lerp, on, outCubic, pop, ramp, tw } from "./kit/core";
import { GUESTS, face } from "./people";

export const CX = 960, CY = 540, CL = CX - 310, CT = CY - 430;       // the card's home: its middle, and its top left corner

// ---- the group chat (beats 0 to 8): one thread, newest at the bottom, each message pushing the others up.
// [words, 1 if Mira's, which guest says it]
const BUB: [string, number, number][] = [
  ["party at mine saturday??", 1, -1], ["which saturday", 0, 1], ["what time", 0, 0], ["8ish", 1, -1], ["where’s ‘mine’ again", 0, 4], ["can I bring someone", 0, 6],
  ["wait is this the 14th", 0, 2], ["the 13th!!", 1, -1], ["who’s coming", 0, 8], ["??", 0, 3], ["is it still on", 0, 10],
];
const TH = { left: 540, right: 1380, bottom: 910, pitch: 124, h: 100, size: 44 };
const CARET = { x: 440, y: 600 };
const CARET_F = TM.CARET * FB;                                       // the frame the caret is there
export function mess(f: number) {
  const out: any[] = [];
  if (f >= CARET_F + 20) return out;
  BUB.forEach(([text, mine, who], i) => {
    const b0 = TM.BUBBLES[i];
    if (!on(f, b0)) return;
    const k = pop(f, b0, 14), w0 = tw(text, TH.size) + 88, h = TH.h;
    let up = 0;                                                       // how many rows the later messages have pushed it up
    for (let j = i + 1; j < BUB.length; j++) up += outCubic(clamp01((f - TM.BUBBLES[j] * FB + 1) / 12));
    const x = mine ? TH.right - w0 / 2 : TH.left + 84 + w0 / 2, y = TH.bottom - up * TH.pitch + (1 - Math.min(1, k)) * 34;
    const kc = inOutCubic(clamp01((f - TM.COLLAPSE * FB - (BUB.length - 1 - i) * 2) / 26));                // falling into the caret, the newest first
    if (kc >= 1) return;
    const w = lerp(w0, h, kc), sc = lerp(0.6 + 0.4 * k, 0.16, kc), px = lerp(x, CARET.x, kc), py = lerp(y, CARET.y, kc) - 70 * Math.sin(Math.PI * kc) * (i % 2 ? 1 : -0.6);
    const from = mine ? [58, 107, 224] : [255, 255, 255], col = from.map((v, j) => Math.round(lerp(v, [29, 26, 22][j], kc * kc)));
    const words = 1 - clamp01((f - TM.COLLAPSE * FB - (BUB.length - 1 - i) * 2 + 4) / 6), a = clamp01((f - b0 * FB + 1) / 5);
    out.push(
      <div key={`bb${i}`} style={{ position: "absolute", left: px - w / 2, top: py - h / 2, width: w, height: h, borderRadius: 50, background: `rgb(${col.join(",")})`, transform: `scale(${sc.toFixed(4)})`, boxShadow: "0 12px 30px rgba(50, 35, 10, 0.13)", opacity: a }}>
        {L("t", 0, 27, w, TH.size, text, { fontFamily: "Geist", fontWeight: 500, letterSpacing: "-0.02em", color: mine ? "#FFFFFF" : C.ink, opacity: words })}
      </div>,
    );
    if (who >= 0 && words > 0) out.push(face(`bf${i}`, GUESTS[who], TH.left + 34, y + 12, 34 * (0.6 + 0.4 * Math.min(1, k)), { opacity: words * a }));
  });
  return out;
}

// ---- the line (beats 8 to 12), and the line becoming the card (12 to 16)
const FIELD = { x: 380, y: 540, w: 1160, h: 120 }, TS = 42, TBASE = 617;
const PARTS: [number, number, string, number, number, number, number, string][] = [                          // [from, to, colour, x, baseline, size, weight, tracking] on the card
  [0, 11, C.coral, CL + 48, CT + 468.7, 78, 600, "-0.035em"], [13, 20, C.blue, CL + 92.4, CT + 601, 33, 500, "-0.015em"], [22, 40, C.gold, CL + 92.4, CT + 549, 33, 500, "-0.015em"],
];
const FLY = TM.FLY;                                                   // frames a part takes from the line to its place (sound.py's T, which plucks each part as it lands)
const typed = (f: number) => Math.max(0, Math.min(LINE.length, Math.floor((f - TM.TYPE0 * FB) / TM.TYPE_PER) + 1));
const RET = TM.RETURN * FB;
const LANDED = TM.PARTS.map((b) => b + (FLY + 4) / FB);              // the beat each part is in its place and the card takes it over
/** the card's parts during the name act: what the card itself shows, while the typed words are still on their way to it */
export function nameShow(f: number) {
  return { title: ramp(f, LANDED[0], 6), where: ramp(f, LANDED[1], 6), when: ramp(f, TM.ADDS[1], 8), kicker: ramp(f, TM.ADDS[0], 8), host: ramp(f, TM.ADDS[2], 8), rsvp: ramp(f, TM.ADDS[3], 8), empty: ramp(f, TM.EMPTY, 12) };
}
/** the field growing into the card: where its edges are, or null once it is the card */
export function morph(f: number) {
  if (f < RET) return null;
  const k = glide(f, TM.RETURN, 22);
  if (k >= 1) return null;
  return R("morph", lerp(FIELD.x, CL, k), lerp(FIELD.y, CT, k), lerp(FIELD.w, 620, k), lerp(FIELD.h, 860, k), { background: "#FFFFFF", borderRadius: lerp(60, 44, k), boxShadow: "0 40px 90px rgba(60, 40, 10, 0.22), 0 4px 14px rgba(60, 40, 10, 0.10)" });
}
export function name(f: number) {
  const out: any[] = [];
  if (f < CARET_F || f >= TM.DRESS * FB) return out;
  const n = typed(f), wr = tw(LINE.slice(0, n), TS);
  if (f < RET) {
    const k = arr(f, TM.NAME, 18);                                                                           // the field opens from the caret
    out.push(R("field", FIELD.x, FIELD.y, lerp(120, FIELD.w, k), FIELD.h, { background: "#FFFFFF", borderRadius: 60, boxShadow: "0 30px 70px rgba(60, 40, 10, 0.16), 0 3px 10px rgba(60, 40, 10, 0.08)", opacity: ramp(f, TM.NAME, 8) }));
    out.push(M("ret", FIELD.x + FIELD.w - 44 - 0.6 * 24 * 6, TBASE - 4, 24, "return", { color: n >= LINE.length ? C.ink : C.faint, opacity: ramp(f, TM.NAME + 0.4, 10) }));
    if (n > 0) out.push(T("line", CARET.x, TBASE, TS, LINE.slice(0, n)));
    PARTS.forEach(([a0, a1, col], j) => {                                                                    // each part is marked as its last letter lands
      if (n < a1) return;
      const g = clamp01((f - (TM.TYPE0 * FB + (a1 - 1) * TM.TYPE_PER)) / 12);
      out.push(R(`ul${j}`, CARET.x + tw(LINE.slice(0, a0), TS), TBASE + 14, tw(LINE.slice(a0, a1), TS) * (1 - Math.pow(1 - g, 3)), 5, { background: col, borderRadius: 3 }));
    });
    const typing = n > 0 && n < LINE.length;
    if (typing || Math.floor(f / 18) % 2 === 0) out.push(R("caret", CARET.x + wr + (n ? 5 : -2), CARET.y - 30, 4.5, 60, { background: C.ink, borderRadius: 2, transform: `scaleY(${pop(f, CARET_F / FB, 12).toFixed(3)})` }));
    return out;
  }
  // return is pressed: what is not a part goes at once; each part leaves the line for its place on the card as the field closes in
  const gone = 1 - clamp01((f - RET) / 5);
  const seg = (a: number, b: number, key: string) => { if (gone > 0 && b > a) out.push(T(key, CARET.x + tw(LINE.slice(0, a), TS), TBASE, TS, LINE.slice(a, b), { opacity: gone })); };
  seg(11, 13, "p0"); seg(20, 22, "p1"); seg(40, 41, "p2");
  const ALPHA = [1 - ramp(f, LANDED[0], 6), 1 - ramp(f, LANDED[1], 6), 1 - ramp(f, TM.ADDS[1], 6)];
  PARTS.forEach(([a0, a1, col, tx, tb, ts, tw_, tr], j) => {
    if (ALPHA[j] <= 0) return;
    const k = inOutCubic(clamp01((f - TM.PARTS[j] * FB) / FLY)), x0 = CARET.x + tw(LINE.slice(0, a0), TS);
    const arc = (j ? 30 : -40) * Math.sin(Math.PI * k);                                                      // the title rises to its place; the two rows dip under it, so nothing crosses
    out.push(T(`part${j}`, lerp(x0, tx, k), lerp(TBASE, tb, k) + arc, lerp(TS, ts, k), LINE.slice(a0, a1), { fontWeight: Math.round(lerp(500, tw_, k)), letterSpacing: k > 0.5 ? tr : "-0.02em", opacity: ALPHA[j] }));
    if (k < 1) out.push(R(`ulp${j}`, lerp(x0, tx, k), lerp(TBASE, tb, k) + arc + 14 * lerp(1, ts / TS, k), tw(LINE.slice(a0, a1), lerp(TS, ts, k)), 5, { background: col, borderRadius: 3, opacity: (1 - k) * ALPHA[j] }));
  });
  return out;
}

// ---- the large words, behind the card: one for each act, then the count
const WS = 180, WY = 438;                                           // their size, and the top of their line when they flank the card
const FLANK_L = CL - 44, FLANK_R = CX + 310 + 44;                   // "Name" ends here; "it." starts here
const EM: Record<string, number> = { Name: 2.325, "it.": 0.709 };  // widths in ems, to centre the two as one phrase before the card parts them
export function words(f: number, night: number, count: number) {
  const out: any[] = [], ink = night > 0.5 ? C.cream : C.ink;
  const st = { fontFamily: SERIF, fontWeight: 500, letterSpacing: "-0.03em", color: ink };
  const left = (key: string, text: string, a: number, dy = 0, dx = 0) => { if (a > 0.01) out.push(L(key, FLANK_L - 900 + dx, WY + dy, 900, WS, text, { ...st, textAlign: "right", opacity: a })); };
  const right = (key: string, text: string, a: number, dy = 0, dx = 0) => { if (a > 0.01) out.push(L(key, FLANK_R + dx, WY + dy, 700, WS, text, { ...st, textAlign: "left", opacity: a })); };
  if (f < TM.PICK * FB) {
    // "Name it." arrives as one phrase over the field; the card parts it; "Name" becomes "Dress"; both step back when the looks open
    const total = (EM.Name + EM["it."]) * WS + 40, pl = CX - total / 2 + EM.Name * WS, pr = pl + 40;      // where "Name" ends and "it." starts as a phrase
    const k = glide(f, TM.RETURN + 0.15, 26), away = ramp(f, TM.OPEN - 0.35, 9), inK = arr(f, TM.NAME, 16), a = ramp(f, TM.NAME, 8) * (1 - away);
    const dy = lerp(300 - WY, 0, k) + (1 - inK) * 40, swap = ramp(f, TM.DRESS, 8), in2 = arr(f, TM.DRESS + 0.2, 14);
    left("wl", "Name", a * (1 - swap), dy + swap * 30, lerp(pl - FLANK_L, 0, k) - away * 50);
    left("wl2", "Dress", ramp(f, TM.DRESS + 0.2, 8) * (1 - away), (1 - in2) * 40, -away * 50);
    right("wr", "it.", a, dy, lerp(pr - FLANK_R, 0, k) + away * 50);
  } else if (f < TM.GUEST * FB + 20) {
    const inK = arr(f, TM.SEND, 16), a = ramp(f, TM.SEND, 8) * (1 - ramp(f, TM.PRESS + 1.2, 12));
    left("ws", "Send", a, (1 - inK) * 40); right("wsr", "it.", a, (1 - arr(f, TM.SEND + 0.25, 16)) * 40);
  } else if (f < (TM.END + 1) * FB) {
    // the count: each number rises into place as the one before leaves
    const a = ramp(f, TM.REPLIES[0] - 0.25, 8) * (1 - ramp(f, TM.END, 12));
    const beats = [...TM.REPLIES, TM.LAST], last = beats.filter((b) => f >= b * FB).length, age = last > 0 ? f - beats[last - 1] * FB : 99, k = clamp01((age + 1) / 6);
    if (last > 1 && k < 1) left("cp", String(count - 1), a * (1 - k), -46 * k);
    if (last > 0) left("cn", String(count), a * k, 46 * (1 - k) * (1 - k));
    right("cr", "in.", a, (1 - arr(f, TM.REPLIES[0] - 0.25, 16)) * 40);
  }
  return out;
}

// ---- the pointer: a soft round touch point. Where it is on each beat, and when it is down.
const BTN = { x: 1160, y: 908 }, REST = { x: 1104, y: 612 }, SIDE = { x: 1128, y: 990 }, OFF = { x: 1580, y: 1280 };
const FL = TM.LOOKS.flatMap((b) => [[b - 0.9, REST.x, REST.y], [b - 0.3, 792, 600], [b + 0.6, REST.x, REST.y]]) as [number, number, number][];
export const ASK = { x: CL + 484, y: CT + 703 };                    // the "+1" on the question that comes back
const PATH: [number, number, number][] = [
  [TM.DRESS + 0.6, 1560, 1250], [TM.OPEN - 1.3, 976, 262], [TM.OPEN, 976, 262], [TM.OPEN + 0.55, REST.x, REST.y], ...FL,
  [TM.PICK - 0.75, REST.x, REST.y], [TM.PICK - 0.2, 980, 568], [TM.PICK + 0.6, 980, 568], [TM.HOST - 0.2, SIDE.x, SIDE.y],
  [TM.ADD - 0.9, SIDE.x, SIDE.y], [TM.ADD - 0.2, BTN.x, BTN.y], [TM.ADD + 0.4, BTN.x, BTN.y], [TM.ADD + 1.1, SIDE.x, SIDE.y],
  [TM.PRESS - 0.8, SIDE.x, SIDE.y], [TM.PRESS - 0.15, BTN.x, BTN.y], [TM.PRESS + 0.5, BTN.x, BTN.y], [TM.PRESS + 1.8, OFF.x, OFF.y],
  [TM.YES - 1.9, OFF.x, 1200], [TM.YES - 0.4, ASK.x, ASK.y], [TM.YES + 0.4, ASK.x, ASK.y], [TM.YES + 2, OFF.x, OFF.y],
];
const DOWN: [number, number][] = [[TM.OPEN - 0.5, TM.OPEN - 0.25], ...TM.LOOKS.map((b) => [b - 0.82, b - 0.3] as [number, number]), [TM.PICK, TM.PICK + 0.25], [TM.ADD, TM.ADD + 0.25], [TM.PRESS, TM.PRESS + 0.25], [TM.YES, TM.YES + 0.25]];
export function pointerAt(f: number) {
  const b = f / FB;
  if (b <= PATH[0][0]) return { x: PATH[0][1], y: PATH[0][2] };
  for (let i = 1; i < PATH.length; i++) if (b < PATH[i][0]) { const k = inOutCubic((b - PATH[i - 1][0]) / (PATH[i][0] - PATH[i - 1][0])); return { x: lerp(PATH[i - 1][1], PATH[i][1], k), y: lerp(PATH[i - 1][2], PATH[i][2], k) }; }
  return { x: PATH[PATH.length - 1][1], y: PATH[PATH.length - 1][2] };
}
/** a touch point at p; `downs` are the [beat down, beat up] of its presses; warm for a guest's own finger */
export function touch(key: string, f: number, p: { x: number; y: number }, downs: [number, number][], night: number, warm = false) {
  const b = f / FB, out: any[] = [];
  let down = 0;
  for (const [d0, d1] of downs) {
    if (b >= d0 && b < d1 + 0.2) down = Math.max(down, Math.min(1, ((b - d0) * FB) / 4, Math.max(0, ((d1 + 0.2 - b) * FB) / 6)));
    const age = f - d0 * FB;                                         // a ring leaves the place it touched
    if (age >= 0 && age < 22) out.push(D(`${key}r${d0}`, p.x, p.y, 24 + 50 * (1 - Math.pow(1 - age / 22, 2)), "rgba(0,0,0,0)", { border: `3.5px solid ${night > 0.5 ? "rgba(255, 244, 220, 0.95)" : "rgba(29, 26, 22, 0.6)"}`, boxSizing: "border-box", opacity: 1 - age / 22 }));
  }
  out.push(D(key, p.x, p.y, 25 * (1 - 0.22 * down), warm ? "rgba(255, 221, 150, 0.96)" : "rgba(255, 255, 255, 0.94)", { border: "2.5px solid rgba(29, 26, 22, 0.3)", boxSizing: "border-box", boxShadow: "0 8px 22px rgba(0, 0, 0, 0.3)" }));
  return out;
}
export const pointer = (f: number, night: number) => touch("ptr", f, pointerAt(f), DOWN, night);
