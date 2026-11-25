// Beats 12 to the end: the card wherever it is (plain, in the row of looks, chosen, sent, filling up, becoming the
// mark), the guests round it, one guest's own phone, the replies and their fireworks, and the end.
import { TIMES as TM } from "./kit/times.gen";
import { C, D, FB, L, R, SERIF, arr, clamp01, glide, inCubic, inOutCubic, lerp, on, outBack, pic, pop, ramp, rnd, svg } from "./kit/core";
import { MOODS, dark, type Mood } from "./kit/field";
import { CH, CW, LOOKS, NIGHT, PAD, SHOWN, invite, place, type Show } from "./card";
import { FIRST, GUESTS, THEO, face, sentFrame } from "./people";
import { ASK, CL, CT, CX, CY, morph, nameShow, touch } from "./acts1";

const GOLD = "#F2C14E", NAVY = "#10202A";
const RETF = TM.RETURN * FB, OPENF = TM.OPEN * FB, PICKF = TM.PICK * FB, ENDF = TM.END * FB;

// ---- which look is in front: 0 the plain card, 4 the fireworks. Each flick lands on its beat, a little past and back.
export function lookAt(f: number) {
  let p = 0;
  for (const b of TM.LOOKS) { const k = clamp01((f - (b * FB - 19)) / 26); if (k > 0) p += outBack(Math.pow(k, 1.6), 1.1); }      // eases in, lands, a little past and back
  return p;
}
/** the room follows the look in front on its own slower curve, so its colour never changes in a frame or two */
function roomAt(f: number) {
  let p = 0;
  for (const b of TM.LOOKS) p += inOutCubic(clamp01((f - (b * FB - 16)) / 46));
  return p;
}
/** how far the art has pushed in inside card i: it starts when the card lands in front and holds when it leaves */
function push(i: number, f: number) {
  if (i < 1) return 0;
  const f0 = TM.LOOKS[i - 1] * FB, f1 = i < TM.LOOKS.length ? TM.LOOKS[i] * FB - 19 : 1e9;
  return 0.3 + 1.5 * clamp01((Math.min(f, f1) - f0) / 120);
}
/** the room: how much of each look's colours is in it */
export function air(f: number): [Mood, number][] {
  const w: Record<string, number> = {};
  if (f < OPENF) { const k = glide(f, TM.COLLAPSE + 0.1, 40); w.mess = 1 - k; w.paper = k; }
  else { const p = roomAt(f); LOOKS.forEach((lk, i) => { const v = Math.max(0, 1 - Math.abs(p - i)); if (v > 0) w[lk.mood] = (w[lk.mood] ?? 0) + v; }); }
  return Object.entries(w).filter(([, v]) => v > 0.001).map(([n, v]) => [MOODS[n], v] as [Mood, number]);
}

// ---- the guests who have answered by frame f, in the order they answered
const ORDERED = GUESTS.map((g, i) => ({ g, i })).filter((x) => x.g.reply >= 0).sort((a, b) => a.g.reply - b.g.reply);
export const countAt = (f: number) => TM.REPLIES.filter((b) => f >= b * FB).length + (f >= TM.LAST * FB ? 1 : 0);
const slot = (k: number) => ({ x: CL + 76 + Math.min(k, SHOWN) * 43, y: CT + 788 });
const MARK = { x: CX, y: 520 };
/** how far the view has gone to one guest's phone, 0 to 1: the host's card goes soft behind it */
const close = (f: number) => glide(f, TM.GUEST, 30) * (1 - glide(f, TM.TAP + 0.1, 34));

// ---- the card
function chosen(f: number): Show {
  const row = ORDERED.map(({ g }) => ({ who: g as { name: string; face: number; hue: string }, k: f >= TM.REPLIES[g.reply] * FB ? outBack(clamp01((f - TM.REPLIES[g.reply] * FB + 1) / 10)) : 0 }));
  if (f >= TM.LAST * FB) row.push({ who: THEO, k: outBack(clamp01((f - TM.LAST * FB + 1) / 10)) });
  const swaps = [TM.READY, TM.PRESS + 0.25], labelA = Math.min(1, ...swaps.map((s) => Math.abs(f - s * FB) / 6));          // the button's words change through a blink, not in one frame
  const hit = (b: number) => (f >= b * FB ? Math.exp(-(f - b * FB) / 8) : 0);
  return {
    rsvp: 1 - ramp(f, TM.HOST, 10), send: ramp(f, TM.HOST + 0.15, 10) * (1 - ramp(f, TM.REPLIES[0] - 0.5, 10)), labelA,
    sendLabel: f < TM.READY * FB ? "Add guests" : f < (TM.PRESS + 0.25) * FB ? `Send to ${GUESTS.length} guests` : `Sent to ${GUESTS.length}`,
    press: Math.max(hit(TM.ADD), hit(TM.PRESS)), going: ramp(f, TM.REPLIES[0] - 0.3, 10), row, count: countAt(f), drift: push(NIGHT, f),
  };
}
export function cards(f: number) {
  if (f < RETF) return [];
  const m = morph(f);
  if (m) return [m];
  if (f < OPENF) {                                                   // the plain card, alone
    const hover = clamp01((f - (TM.OPEN - 1.4) * FB) / 20), tap = f >= (TM.OPEN - 0.5) * FB ? Math.exp(-(f - (TM.OPEN - 0.5) * FB) / 6) : 0;   // "Add a look" is pressed half a beat before the looks open
    return [place("card", invite("s", 0, f < TM.DRESS * FB ? nameShow(f) : { rsvp: 1, ask: Math.min(1, hover + tap) }), CX, CY, { s: 1 - 0.012 * tap })];
  }
  const p = lookAt(f), open = glide(f, TM.OPEN, 26), out: [number, any][] = [], dk = dark(air(f));
  // a soft light behind the card in front, so a dark card stands off a dark room
  if (dk > 0.3) out.push([99, R("rim", CX - 680, CY - 680, 1360, 1360, { background: "radial-gradient(closest-side, rgba(150, 200, 210, 0.2), rgba(150, 200, 210, 0.08) 55%, rgba(150, 200, 210, 0))", opacity: clamp01((dk - 0.3) / 0.3) * (1 - glide(f, TM.END, 40)) })]);
  if (f < PICKF + 26) {                                              // the row of looks, in depth; after the choice the others fall away
    LOOKS.forEach((_, i) => {
      if (f >= PICKF && i === NIGHT) return;
      const d = (i - p) * open, ad = Math.abs(d), fall = f >= PICKF ? clamp01((f - PICKF - 2 * Math.abs(i - NIGHT)) / 18) : 0;
      if (fall >= 1) return;
      out.push([ad, place(`card${i}`, invite("s", i, { rsvp: 1, drift: push(i, f) }), CX, CY, { sway: 3.2 * Math.sin((f - OPENF) / 44) * open, tilt: 1.0 * Math.cos((f - OPENF) / 61) * open, dx: d * 548, dz: -Math.min(ad, 3) * 300, dy: 280 * inCubic(fall), turn: Math.max(-46, Math.min(46, -d * 22)), blur: Math.min(10, ad * 4.4), opacity: (i ? ramp(f, TM.OPEN + 0.04 * i, 10) : 1) * (1 - fall) * (1 - 0.12 * Math.min(1, ad)) })]);
    });
  }
  if (f >= PICKF) {                                                  // the chosen one: it takes each reply with a small bump, and at the end draws back to be the mark
    const last = [...TM.REPLIES, TM.LAST].filter((b) => f >= b * FB).pop(), bump = last === undefined ? 0 : 0.014 * Math.exp(-(f - last * FB) / 5);
    const k = glide(f, TM.END, 56), gone = ramp(f, TM.END + 1.35, 10), t = f - PICKF, fl = glide(f, TM.PICK + 0.5, 60) * (1 - k);          // it floats a little once it is chosen
    if (gone < 1) out.push([0, place("card", invite("s", NIGHT, chosen(f)), lerp(CX, MARK.x, k), lerp(CY, MARK.y, k), { s: lerp(1 + bump, 200 / 860, k), turn: 3.6 * Math.sin(t / 54) * fl, tilt: 1.8 * Math.sin(t / 73 + 1) * fl, blur: 7 * close(f), opacity: 1 - gone })]);
  }
  return out.sort((a, b) => b[0] - a[0]).map((x) => x[1]);
}
/** under the row of looks: which of the five is in front, and who made its art. On the choice, a tick on the card. */
export function chooser(f: number, darkness: number) {
  const out: any[] = [];
  if (f < OPENF || f >= PICKF + 3 * FB) return out;
  const p = lookAt(f), i = Math.round(p), open = glide(f, TM.OPEN, 26), away = 1 - ramp(f, TM.PICK + 0.3, 10), ink = darkness > 0.5 ? "255, 244, 220" : "29, 26, 22";
  if (away > 0) {
    for (let j = 1; j <= 5; j++) { const on_ = clamp01(1 - Math.abs(p - j)); out.push(D(`dot${j}`, CX + (j - 3) * 28, CY + 430 + 28, 5 + 2 * on_, `rgba(${ink}, ${(0.28 + 0.72 * on_).toFixed(2)})`, { opacity: open * away })); }
    const a = clamp01(1 - 3 * Math.abs(p - i)) * open * away;
    if (i >= 1 && a > 0) out.push(L("credit", CX - 800, CY + 430 + 48, 1600, 32, LOOKS[i].credit, { fontFamily: "Geist", fontWeight: 500, letterSpacing: "-0.005em", color: `rgba(${ink}, 0.8)`, opacity: a }));
  }
  if (f >= PICKF) {                                                  // chosen: a tick lands on its corner
    const k = pop(f, TM.PICK, 16), a = 1 - ramp(f, TM.PICK + 2.4, 12), x = CX + 310 - 8, y = CY - 430 + 8;
    out.push(D("okd", x, y, 30 * k, GOLD, { opacity: a, boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)" }));
    out.push(svg("okc", <path d={`M${x - 13},${y + 1}l9,9.5l15,-18`} stroke={NAVY} strokeWidth={5.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />, { opacity: a * Math.min(1, k) }));
  }
  return out;
}

// ---- the guests round the card. `front` false: those standing in their places; true: those on their way to the card
const home = (i: number, f: number) => ({ x: GUESTS[i].x + 3 * Math.cos(f * 0.037 + i), y: GUESTS[i].y + 5 * Math.sin(f * 0.045 + i * 1.7) });      // they bob where they stand
export function guests(f: number, front: boolean) {
  const out: any[] = [];
  if (f < TM.ROLL0 * FB || f >= ENDF + 16) return out;
  const away = 1 - ramp(f, TM.END, 12);
  GUESTS.forEach((g, i) => {
    const b0 = TM.ROLL0 + i * TM.ROLL_STEP, rb = g.reply < 0 ? -1 : TM.REPLIES[g.reply];
    if (!on(f, b0)) return;
    const k = pop(f, b0, 14), f0 = rb < 0 ? 1e9 : rb * FB - 22, h = home(i, f);
    if (f >= f0) {                                                   // answering: the face leaves its place for the card
      if (!front || f >= rb * FB) return;
      const u = inOutCubic((f - f0) / 22), s = slot(g.reply);
      out.push(face(`fly${i}`, g, lerp(h.x, s.x, u), lerp(h.y, s.y, u) - 90 * Math.sin(Math.PI * u), lerp(g.r, 28, u)));
      return;
    }
    if (front) return;
    const got = f - sentFrame(i), ring = got >= 0 ? Math.exp(-got / 5) : 0, dim = rb < 0 ? 1 - 0.45 * ramp(f, TM.REPLIES[TM.REPLIES.length - 1], 30) : 1;
    out.push(face(`f${i}`, g, h.x, h.y, g.r * k * (1 + 0.18 * ring), { opacity: away * dim, filter: g.soft > 0.7 ? `blur(${g.soft.toFixed(1)}px)` : "none" }));
    out.push(L(`n${i}`, h.x - 100, h.y + g.r + 10, 200, 28, g.name, { fontFamily: "Geist", fontWeight: 500, color: "rgba(255, 244, 220, 0.85)", opacity: ramp(f, b0 + 0.2, 8) * away * dim * (g.soft > 0.7 ? 0.75 : 1) }));
    const told = 1 - ramp(f, TM.REPLIES[0] - 0.5, 14);                 // the ticks go when the replies start: the "+1"s take over
    if (got >= 0 && told > 0) {                                      // the invitation has reached them: a tick
      const t = clamp01((got + 1) / 8), tx = h.x + g.r * 0.72, ty = h.y + g.r * 0.72;
      out.push(D(`tk${i}`, tx, ty, 13 * outBack(t), GOLD, { opacity: away * dim * told, boxShadow: "0 0 0 2.5px #0A141B" }));
      out.push(svg(`tkc${i}`, <path d={`M${tx - 5.5},${ty}l4,4.2l6.8,-7.8`} stroke={NAVY} strokeWidth={2.8} fill="none" strokeLinecap="round" strokeLinejoin="round" />, { opacity: t * away * dim * told }));
    }
  });
  return out;
}
/** the invitation going out: after the press, a small copy of the card leaves from behind it for each guest */
export function minis(f: number) {
  const out: any[] = [], p0 = TM.PRESS * FB + 5;
  if (f < p0 || f > p0 + 80) return out;
  GUESTS.forEach((g, i) => {
    const f0 = p0 + i * 0.5, f1 = sentFrame(i);
    if (f < f0 || f >= f1) return;
    const u = (f - f0) / (f1 - f0), e = inOutCubic(u), x = lerp(CX + (g.x < CX ? -150 : 150), g.x, e), y = lerp(CY + (g.y < CY ? -160 : 160), g.y, e) - (70 + 80 * rnd(i + 40)) * Math.sin(Math.PI * u), s = lerp(0.95, 0.42, e);
    out.push(<div key={`mini${i}`} style={{ position: "absolute", left: x - 46.5, top: y - 64.5, width: 93, height: 129, borderRadius: 13, overflow: "hidden", transform: `rotate(${((rnd(i + 9) - 0.5) * 70 * (1 - e)).toFixed(2)}deg) scale(${s.toFixed(3)})`, boxShadow: "0 10px 26px rgba(0, 0, 0, 0.4)", opacity: Math.min(1, (f1 - f) / 3) }}>{pic("m", "art/night-mini.jpg", 0, 0, 93, 129)}</div>);
  });
  return out;
}
/** one guest's own phone: the invitation as she sees it, and her finger on "I'm in". Shown once, before the count runs. */
const PH = { x: 240, y: 372, s: 0.6 };
const HER: [number, number, number][] = [[TM.TAP - 1.2, 40, 820], [TM.TAP - 0.3, PH.x - 8, PH.y + 219], [TM.TAP + 0.35, PH.x - 8, PH.y + 219], [TM.TAP + 1.1, 20, 860]];
export function guestView(f: number, night: number) {
  const out: any[] = [], g = GUESTS[FIRST], t1 = TM.TAP * FB;
  if (f < TM.GUEST * FB + 8 || f > t1 + 40) return out;
  const k = pop(f, TM.GUEST + 0.35, 18) * (1 - glide(f, TM.TAP + 0.12, 16));
  if (k > 0.01) {
    const w = CW * PH.s + 24, h = CH * PH.s + 24, left = PH.x - w / 2, top = PH.y - h / 2, yes = f >= t1 ? 1 : 0, pulse = f >= t1 ? Math.exp(-(f - t1) / 7) : 0;
    out.push(
      <div key="phone" style={{ position: "absolute", left, top, width: w, height: h, transformOrigin: `${(g.x - left).toFixed(1)}px ${(g.y - top).toFixed(1)}px`, transform: `scale(${k.toFixed(4)})`, opacity: Math.min(1, k * 2) }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, borderRadius: 40, background: "#0B0F14", boxShadow: "0 30px 80px rgba(0, 0, 0, 0.6), 0 0 0 2.5px rgba(255, 244, 220, 0.28)" }} />
        <div style={{ position: "absolute", left: 12 - PAD * PH.s, top: 12 - PAD * PH.s, width: CW + 2 * PAD, height: CH + 2 * PAD, transformOrigin: "0 0", transform: `scale(${PH.s})` }}>{invite("gv", NIGHT, { rsvp: 1, yes, pulse })}</div>
      </div>,
    );
    out.push(L("phl", left, top - 40, w, 26, `${g.name}’s phone`, { fontFamily: "Geist", fontWeight: 500, color: "rgba(255, 244, 220, 0.85)", opacity: clamp01((k - 0.8) / 0.2) }));
  }
  const b = f / FB;                                                  // her own finger
  if (b > HER[0][0] && b < HER[3][0]) {
    let p = { x: HER[0][1], y: HER[0][2] };
    for (let i = 1; i < HER.length; i++) if (b < HER[i][0]) { const u = inOutCubic((b - HER[i - 1][0]) / (HER[i][0] - HER[i - 1][0])); p = { x: lerp(HER[i - 1][1], HER[i][1], u), y: lerp(HER[i - 1][2], HER[i][2], u) }; break; }
    out.push(...touch("her", f, p, [[TM.TAP, TM.TAP + 0.25]], night, true));
  }
  return out;
}
/** each yes leaves a "+1" where the guest stood; at the end they all go to the mark */
export function plusOnes(f: number) {
  const out: any[] = [];
  ORDERED.forEach(({ g }) => {
    const n = g.reply, b = TM.REPLIES[n];
    if (!on(f, b)) return;
    const k = pop(f, b, 16), u = inOutCubic(clamp01((f - ENDF - 4 - n * 1.3) / 34));
    if (u >= 1) return;
    const bob = 4 * Math.sin((f + n * 17) * 0.06), px = lerp(g.x, MARK.x, u), py = lerp(g.y + bob, MARK.y, u) - 60 * Math.sin(Math.PI * u), s = lerp(0.87 * k, 0.5, u), tf = `scale(${s.toFixed(3)}) rotate(${(-6 + 12 * rnd(n + 3)).toFixed(1)}deg)`, a = 1 - clamp01((u - 0.8) / 0.2);
    out.push(R(`po${n}`, px - 31, py - 31, 62, 62, { borderRadius: 19, background: GOLD, transform: tf, boxShadow: "0 8px 22px rgba(0, 0, 0, 0.35), 0 0 34px rgba(242, 193, 78, 0.35)", opacity: a }));
    out.push(L(`pot${n}`, px - 31, py - 17, 62, 30, "+1", { fontFamily: "Geist", fontWeight: 700, letterSpacing: "-0.03em", color: NAVY, transform: tf, opacity: a }));
  });
  return out;
}

// ---- fireworks: [beat, x, y, how far the sparks reach, which colours]. One for the choice and two after it, a small one for
// each yes where that guest stood, bigger ones in the corners on the bars (clear of the count), the biggest behind the card
// on the last yes, and two far ones behind the name.
const PAL = [["#FFD36E", "#FFF4DC"], ["#FF8FA3", "#FFD36E"], ["#7FE3D4", "#FFF4DC"], ["#FF9B6A", "#FFD36E"], ["#B9A6FF", "#FFF4DC"]];
const CORNERS: [number, number][] = [[250, 190], [1680, 880], [1690, 200], [250, 880], [CX, 26], [230, 210]];
const BURSTS: [number, number, number, number, number][] = [
  [TM.PICK, CX, 470, 520, 0], [TM.SKY[0], 400, 300, 210, 2], [TM.SKY[1], 1530, 770, 180, 1],
  ...ORDERED.map(({ g }, n) => [TM.REPLIES[g.reply] + 0.06, g.x + (rnd(n) - 0.5) * 40, g.y - 16, 100 + 50 * rnd(n + 5), n % PAL.length] as [number, number, number, number, number]),
  ...CORNERS.map(([x, y], n) => [TM.CORNERS[n], x, y, 250 + 40 * (n % 3), (n + 1) % PAL.length] as [number, number, number, number, number]),
  [TM.LAST, CX, 500, 600, 0], [TM.LAST + 0.12, 300, 240, 340, 1], [TM.LAST + 0.24, 1620, 230, 340, 2], [TM.LAST + 0.5, 280, 860, 280, 4], [TM.LAST + 0.62, 1640, 850, 280, 3],
  [TM.AFTER[0], 1500, 780, 200, 4], [TM.AFTER[1], 420, 800, 200, 3], [TM.FARS[0], 1480, 290, 170, 0], [TM.FARS[1], 420, 330, 130, 2],
];
export function sky(f: number) {
  const out: any[] = [];
  BURSTS.forEach(([b, cx, cy, reach, pi], n) => {
    const a = f - b * FB;
    if (a < 0 || a > 66) return;
    const rays = Math.round(26 + reach / 6), fade = 1 - clamp01((a - 24) / 42), sw = 2 + reach / 150;
    const d = ["", "", ""];
    let heads = "";
    for (let j = 0; j < rays; j++) {
      const inner = j % 3 === 2, th = (2 * Math.PI * j) / rays + (rnd(n * 31 + j) - 0.5) * 0.3, far = reach * (inner ? 0.3 + 0.25 * rnd(n * 17 + j * 3) : 0.6 + 0.4 * rnd(n * 17 + j * 3));
      const at = (q: number) => { const r = far * (1 - Math.exp(-q / 10)); return [cx + Math.cos(th) * r, cy + Math.sin(th) * r + 0.02 * q * q * (reach / 200)]; };
      const p1 = at(a), p0 = at(Math.max(0, a - 5));
      if (a > 26 && rnd(n * 7 + j + Math.floor(f / 3)) < 0.3) continue;                  // they flicker as they die
      d[inner ? 2 : j % 2] += `M${p0[0].toFixed(1)},${p0[1].toFixed(1)}L${p1[0].toFixed(1)},${p1[1].toFixed(1)}`;
      if (!inner) { const hr = sw * 1.1; heads += `M${(p1[0] - hr).toFixed(1)},${p1[1].toFixed(1)}a${hr.toFixed(1)},${hr.toFixed(1)} 0 1,0 ${(2 * hr).toFixed(1)},0a${hr.toFixed(1)},${hr.toFixed(1)} 0 1,0 ${(-2 * hr).toFixed(1)},0`; }
    }
    const glow = Math.exp(-a / 9) * Math.min(1, (a + 1) / 3);
    if (glow > 0.03) out.push(R(`fg${n}`, cx - reach, cy - reach, reach * 2, reach * 2, { background: `radial-gradient(closest-side, rgba(255, 236, 190, ${(0.6 * glow).toFixed(3)}), rgba(255, 236, 190, 0))` }));
    out.push(svg(`fw${n}`, [
      <path key="a" d={d[0]} stroke={PAL[pi][0]} strokeWidth={sw} strokeLinecap="round" fill="none" />,
      <path key="b" d={d[1]} stroke={PAL[pi][1]} strokeWidth={sw * 0.8} strokeLinecap="round" fill="none" />,
      <path key="c" d={d[2]} stroke={PAL[(pi + 1) % PAL.length][0]} strokeWidth={sw * 0.7} strokeLinecap="round" fill="none" />,
      <path key="h" d={heads} fill="#FFFBEF" />,
    ], { opacity: fade }));
  });
  return out;
}
/** the night's own small lights, there while the room is night */
export function stars(f: number, w: number, h: number, night: number) {
  if (night < 0.02) return null;
  let d = "";
  for (let i = 0; i < 70; i++) {
    const tw = 0.5 + 0.5 * Math.sin(f * 0.05 * (0.6 + rnd(i + 80)) + rnd(i) * 6.28), r = (0.8 + 1.6 * rnd(i + 20)) * (0.6 + 0.4 * tw), x = rnd(i + 1) * w, y = rnd(i + 50) * h;
    d += `M${(x - r).toFixed(1)},${y.toFixed(1)}a${r.toFixed(2)},${r.toFixed(2)} 0 1,0 ${(2 * r).toFixed(2)},0a${r.toFixed(2)},${r.toFixed(2)} 0 1,0 ${(-2 * r).toFixed(2)},0`;
  }
  return <svg key="stars" style={{ position: "absolute", left: 0, top: 0, opacity: 0.5 * night }} width={w} height={h}><path d={d} fill="#FFF4DC" /></svg>;
}

// ---- what comes back with the yeses: a few words, said from a face on the card. The last one asks to bring someone.
const SAYS: [number, number, number, string, boolean][] = [[TM.REPLIES[7], TM.REPLIES[7] + 2.1, 3, "bringing cake", false], [TM.REPLIES[13], TM.REPLIES[13] + 2.1, 6, "finally!!", false], [TM.ASK, TM.LAST + 0.5, 2, "can I bring Theo?", true]];
export function talk(f: number) {
  const out: any[] = [];
  SAYS.forEach(([b0, b1, k, text, asks], n) => {
    if (!on(f, b0) || f >= b1 * FB + 10) return;
    const a = pop(f, b0, 14), gone = ramp(f, b1, 10), tw_ = text.length * 15.6 + 56 + (asks ? 80 : 0), s = slot(k);
    const right = asks ? ASK.x + 44 : Math.min(CL + 620 - 30, s.x - 30 + tw_), x = right - tw_, y = CT + 671;
    const yes = f >= TM.YES * FB ? Math.exp(-(f - TM.YES * FB) / 7) : 0;
    out.push(
      <div key={`say${n}`} style={{ position: "absolute", left: x, top: y, width: tw_, height: 64, borderRadius: 32, background: C.cream, boxShadow: "0 12px 30px rgba(0, 0, 0, 0.4)", transform: `scale(${(0.6 + 0.4 * a).toFixed(3)})`, transformOrigin: `${Math.max(24, s.x - x)}px 70px`, opacity: Math.min(1, a * 2) * (1 - gone) }}>
        <div style={{ position: "absolute", left: Math.max(20, Math.min(tw_ - 40, s.x - x - 9)), top: 53, width: 18, height: 18, background: C.cream, transform: "rotate(45deg)" }} />
        {L("t", 28, 16, tw_, 30, text, { fontFamily: "Geist", fontWeight: 500, letterSpacing: "-0.015em", color: C.ink, textAlign: "left" })}
        {asks ? <div style={{ position: "absolute", left: tw_ - 70, top: 6, width: 52, height: 52, borderRadius: 26, background: GOLD, transform: `scale(${(1 + 0.16 * yes - 0.1 * clamp01(1 - Math.abs(f - TM.YES * FB) / 5)).toFixed(3)})`, boxShadow: yes > 0.05 ? `0 0 0 ${(12 * yes).toFixed(1)}px rgba(242, 193, 78, ${(0.4 * yes).toFixed(2)})` : "none" }}>{L("c", 0, 12, 52, 25, "+1", { fontFamily: "Geist", fontWeight: 700, letterSpacing: "-0.03em", color: NAVY })}</div> : null}
      </div>,
    );
  });
  if (f >= TM.YES * FB + 4 && f < TM.LAST * FB) {                     // Theo: out of the "+1" and onto the card
    const u = inOutCubic(clamp01((f - TM.YES * FB - 4) / (TM.LAST * FB - TM.YES * FB - 4))), s = slot(19);
    out.push(face("theo", THEO, lerp(ASK.x, s.x, u), lerp(ASK.y, s.y, u) - 50 * Math.sin(Math.PI * u), lerp(20, 28, u)));
  }
  return out;
}

// ---- the end: the mark, the name, the line
export function lockup(f: number) {
  const out: any[] = [];
  if (f < ENDF + 30) return out;
  const k = pop(f, TM.END + 1.3, 20), open = glide(f, TM.MARK - 0.4, 26), NAMEW = 560;
  out.push(
    <div key="lock" style={{ position: "absolute", left: 0, top: MARK.y - 110, width: 1920, height: 220, display: "flex", flexDirection: "row", justifyContent: "center", alignItems: "center" }}>
      <div style={{ flex: "none", width: 200, height: 200, borderRadius: 52, background: GOLD, position: "relative", transform: `scale(${k.toFixed(3)})`, boxShadow: "0 30px 70px rgba(0, 0, 0, 0.45), 0 0 90px rgba(242, 193, 78, 0.3)", opacity: Math.min(1, k * 2) }}>
        {L("m", 0, 44, 200, 104, "+1", { fontFamily: "Geist", fontWeight: 700, letterSpacing: "-0.04em", color: NAVY })}
      </div>
      <div style={{ flex: "none", width: (NAMEW + 56) * open, height: 220, position: "relative", overflow: "hidden" }}>
        {L("nm", 56, 22, NAMEW + 40, 150, "Plus One", { fontFamily: SERIF, fontWeight: 500, letterSpacing: "-0.03em", color: C.cream, textAlign: "left", opacity: ramp(f, TM.MARK - 0.2, 10), transform: `translateX(${((1 - open) * -40).toFixed(1)}px)` })}
      </div>
    </div>,
  );
  const t = arr(f, TM.MARK + 1.5, 16);
  if (t > 0) out.push(L("tag", 0, MARK.y + 150 + (1 - t) * 18, 1920, 44, "Invitations people answer.", { fontFamily: "Geist", fontWeight: 500, letterSpacing: "-0.015em", color: "rgba(255, 244, 220, 0.86)", opacity: ramp(f, TM.MARK + 1.5, 9) }));
  return out;
}
