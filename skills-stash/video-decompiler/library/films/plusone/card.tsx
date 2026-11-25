// The card: one invitation, 620 by 860, and the looks it can wear. A look is a work of art, a face of type, a place for
// each part and a palette; the words and the parts are the same in every look. `invite` draws the card's own surface;
// `place` stands it somewhere in depth.
import { C, D, L, R, pic } from "./kit/core";
import { GUESTS, MIRA, face } from "./people";

export const CW = 620, CH = 860, CR = 44, PAD = 96;        // PAD: room round the card for its shadow and for the blur of a far card
export const SHOWN = 7;                                    // faces the card's row holds before it counts the rest
export const TITLE = "Mira’s 30th", WHEN = "Sat 13 June · 8:00 pm", WHERE = "Rooftop";

type Txt = { y: number; size: number; color: string; font?: string; weight?: number; style?: string; track?: string; lh?: number; lines?: string[] };
export type Look = {
  id: string; name: string; credit: string; mood: string;
  art: string | null; box: [number, number, number, number]; pos: string; radius?: number;
  bg: string; scrim?: string; align: "left" | "center";
  kicker: Txt; title: Txt; rows: Txt & { gap: number }; host: Txt | null;
  btn: { bg: string; ink: string; line: string; ghost: string };
  shade: string;                                         // the card's shadow in its room
};
const GEIST = { font: "Geist", weight: 500 };
export const LOOKS: Look[] = [
  { id: "plain", name: "No look yet", credit: "", mood: "paper", art: null, box: [0, 0, CW, 330], pos: "50% 50%", bg: "#FFFFFF", align: "left",
    kicker: { y: 371, size: 22, color: C.soft }, title: { y: 398, size: 78, color: C.ink, ...GEIST, weight: 600, track: "-0.035em", lines: [TITLE] },
    rows: { y: 548, gap: 52, size: 33, color: C.ink }, host: { y: 677, size: 25, color: C.soft },
    btn: { bg: C.ink, ink: "#FFFFFF", line: "rgba(29, 26, 22, 0.25)", ghost: C.ink }, shade: "0 40px 90px rgba(60, 40, 10, 0.22), 0 4px 14px rgba(60, 40, 10, 0.10)" },
  { id: "irises", name: "Garden", credit: "Irises · Vincent van Gogh, 1890 · The Met", mood: "irises", art: "art/irises.jpg", box: [0, 0, CW, 440], pos: "50% 50%", bg: "#F8F2DF", align: "left",
    kicker: { y: 469, size: 22, color: "#3E5FB8" }, title: { y: 492, size: 86, color: "#22402F", font: "Fraunces", weight: 500, style: "italic", track: "-0.02em", lines: [TITLE] },
    rows: { y: 622, gap: 46, size: 31, color: "#22402F" }, host: { y: 716, size: 23, color: "#5C6B55" },
    btn: { bg: "#3E5FB8", ink: "#FFFFFF", line: "rgba(34, 64, 47, 0.3)", ghost: "#22402F" }, shade: "0 40px 90px rgba(30, 50, 20, 0.25), 0 4px 14px rgba(30, 50, 20, 0.12)" },
  { id: "wave", name: "Tide", credit: "Under the Wave off Kanagawa · Katsushika Hokusai, about 1831 · The Met", mood: "wave", art: "art/wave.jpg", box: [0, 392, CW, 468], pos: "50% 50%", bg: "#F1E8D0", align: "left",
    kicker: { y: 55, size: 22, color: "#8A7B5A" }, title: { y: 84, size: 92, color: "#1D3566", font: "Bricolage Grotesque", weight: 800, track: "-0.03em", lh: 0.94, lines: ["Mira’s", "30th"] },
    rows: { y: 312, gap: 46, size: 31, color: "#1D3566" }, host: null,
    btn: { bg: "#1D3566", ink: "#F1E8D0", line: "rgba(241, 232, 208, 0.9)", ghost: "#F1E8D0" }, shade: "0 40px 90px rgba(20, 30, 60, 0.28), 0 4px 14px rgba(20, 30, 60, 0.12)" },
  { id: "banquet", name: "Banquet", credit: "A Bouquet of Flowers in a Crystal Vase · Nicolaes van Veerendael, 1662 · The Met", mood: "banquet", art: "art/banquet.jpg", box: [0, 0, CW, CH], pos: "50% 0%", bg: "#100F0C", align: "center",
    scrim: "linear-gradient(180deg, rgba(16, 15, 12, 0) 48%, rgba(16, 15, 12, 0.86) 63%, rgba(16, 15, 12, 0.97) 78%)",
    kicker: { y: 543, size: 22, color: "#D9B36A" }, title: { y: 566, size: 80, color: "#F6EBD6", font: "Playfair Display", weight: 500, style: "italic", track: "-0.01em", lines: [TITLE] },
    rows: { y: 692, gap: 38, size: 29, color: "#F6EBD6" }, host: null,
    btn: { bg: "#D9B36A", ink: "#1A1410", line: "rgba(246, 235, 214, 0.5)", ghost: "#F6EBD6" }, shade: "0 40px 90px rgba(0, 0, 0, 0.5), 0 4px 14px rgba(0, 0, 0, 0.3)" },
  { id: "night", name: "Fireworks", credit: "Fireworks at Ryōgoku · Utagawa Hiroshige, 1858 · Cleveland Museum of Art", mood: "night", art: "art/night.jpg", box: [0, 0, CW, CH], pos: "50% 50%", bg: "#17262B", align: "left",
    scrim: "linear-gradient(180deg, rgba(10, 18, 24, 0) 76%, rgba(10, 18, 24, 0.6) 100%)",
    kicker: { y: 315, size: 22, color: "#F2C14E" }, title: { y: 338, size: 112, color: "#FFF4DC", font: "Anton", weight: 400, track: "0.005em", lines: ["MIRA’S 30TH"] },
    rows: { y: 500, gap: 42, size: 31, color: "#FFF4DC" }, host: null,
    btn: { bg: "#F2C14E", ink: "#10202A", line: "rgba(255, 244, 220, 0.6)", ghost: "#FFF4DC" }, shade: "0 40px 100px rgba(0, 0, 0, 0.55), 0 0 70px rgba(70, 130, 160, 0.22)" },
  { id: "sunday", name: "Sunday", credit: "A Sunday on La Grande Jatte · Georges Seurat, 1884–86 · Art Institute of Chicago", mood: "sunday", art: "art/sunday.jpg", box: [34, 34, CW - 68, 400], pos: "50% 50%", radius: 20, bg: "#FBF7EA", align: "center",
    kicker: { y: 467, size: 22, color: "#5E8A4B" }, title: { y: 490, size: 82, color: "#2B3A22", font: "DM Serif Display", weight: 400, track: "-0.01em", lines: [TITLE] },
    rows: { y: 622, gap: 46, size: 31, color: "#2B3A22" }, host: null,
    btn: { bg: "#2B3A22", ink: "#FBF7EA", line: "rgba(43, 58, 34, 0.3)", ghost: "#2B3A22" }, shade: "0 40px 90px rgba(30, 50, 20, 0.25), 0 4px 14px rgba(30, 50, 20, 0.12)" },
];
export const NIGHT = 4;

const clock = (c: string, s: number) => <svg width={s} height={s} viewBox="0 0 24 24" style={{ flex: "none" }}><circle cx="12" cy="12" r="9" fill="none" stroke={c} strokeWidth="2" /><path d="M12 7v5.3l3.4 2" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
const pin = (c: string, s: number) => <svg width={s} height={s} viewBox="0 0 24 24" style={{ flex: "none" }}><path d="M12 21.2c4.4-4.6 6.6-8 6.6-10.8A6.6 6.6 0 0 0 5.4 10.4c0 2.8 2.2 6.2 6.6 10.8z" fill="none" stroke={c} strokeWidth="2" strokeLinejoin="round" /><circle cx="12" cy="10.2" r="2.3" fill={c} /></svg>;

export type Show = {
  title?: number; when?: number; where?: number; kicker?: number; host?: number;      // how much of each part is there (0 to 1); 1 when absent
  rsvp?: number; send?: number; going?: number;                                        // the bottom of the card: what a guest sees, the host's button, who is coming
  press?: number;                                                                      // the button under a finger, 0 to 1
  sendLabel?: string;
  row?: { who: { name: string; face: number; hue: string }; k: number }[]; count?: number;
  drift?: number;                                                                      // the art moves a little inside its window, 0 to 1
  ask?: number;                                                                        // the plain card's "Add a look", lit under the pointer
  empty?: number;                                                                      // how much of the plain card's empty place for a look is there
  labelA?: number;                                                                     // the host's button's words, fading through a change
  yes?: number; pulse?: number;                                                        // a guest has pressed "I'm in"
};
const v = (x: number | undefined, d = 1) => (x === undefined ? d : x);

/** the card's own surface, CW by CH, drawn from its top left corner */
export function invite(key: string, li: number, o: Show = {}) {
  const k = LOOKS[li], els: any[] = [], left = k.align === "left", x0 = 48, w = CW - 96;
  const line = (id: string, t: Txt, text: string, i: number, a: number, st: Record<string, any> = {}) => L(`${id}${i}`, x0, t.y + i * t.size * (t.lh ?? 1.04), w, t.size, text, { fontFamily: t.font ?? "Geist", fontWeight: t.weight ?? 500, fontStyle: t.style ?? "normal", letterSpacing: t.track ?? "-0.01em", color: t.color, textAlign: left ? "left" : "center", opacity: a, lineHeight: `${Math.round(t.size * 1.1)}px`, ...st });
  if (k.art) {
    const [bx, by, bw, bh] = k.box, s = 1.03 + 0.05 * v(o.drift, 0);
    els.push(<div key="art" style={{ position: "absolute", left: bx, top: by, width: bw, height: bh, overflow: "hidden", borderRadius: k.radius ?? 0 }}>{pic("a", k.art, 0, 0, bw, bh, { objectPosition: k.pos, transform: `scale(${s.toFixed(4)})` })}</div>);
  } else {
    const a = v(o.ask, 0), e = v(o.empty);                // the plain card: a place where a look will go
    els.push(R("ph", 0, 0, CW, 330, { background: "#F1ECE2", opacity: e }));
    els.push(R("phd", 40, 40, CW - 80, 250, { border: `2.5px dashed rgba(29, 26, 22, ${(0.2 + 0.3 * a).toFixed(2)})`, borderRadius: 26, boxSizing: "border-box", background: `rgba(255, 255, 255, ${(0.5 * a).toFixed(2)})`, opacity: e }));
    els.push(D("php", CW / 2, 142, 26 * (1 + 0.12 * a), C.ink, { opacity: 0.85 * e }), R("ph1", CW / 2 - 11, 140.5, 22, 3, { background: "#fff", borderRadius: 2, opacity: e }), R("ph2", CW / 2 - 1.5, 131, 3, 22, { background: "#fff", borderRadius: 2, opacity: e }));
    els.push(L("pht", 0, 186, CW, 27, "Add a look", { fontFamily: "Geist", fontWeight: 500, color: C.soft, opacity: e }));
  }
  if (k.scrim) els.push(R("scrim", 0, 0, CW, CH, { background: k.scrim }));
  els.push(line("kick", { ...k.kicker, font: "Geist Mono", weight: 500, track: "0.16em" }, "YOU’RE INVITED", 0, v(o.kicker)));
  (k.title.lines ?? [TITLE]).forEach((t, i) => els.push(line("ti", k.title, t, i, v(o.title))));
  const row = (id: string, i: number, icon: any, text: string, a: number) => (
    <div key={id} style={{ position: "absolute", left: x0, top: k.rows.y + i * k.rows.gap - k.rows.size * 0.92, width: w, height: k.rows.size * 1.2, display: "flex", flexDirection: "row", alignItems: "center", justifyContent: left ? "flex-start" : "center", gap: 14, opacity: a, fontFamily: "Geist", fontWeight: 500, fontSize: k.rows.size, letterSpacing: "-0.015em", color: k.rows.color, whiteSpace: "nowrap" }}>{icon}<span>{text}</span></div>
  );
  els.push(row("when", 0, clock(k.rows.color, k.rows.size * 0.92), WHEN, v(o.when)), row("where", 1, pin(k.rows.color, k.rows.size * 0.92), WHERE, v(o.where)));
  if (k.host) {
    els.push(face("hf", MIRA, x0 + 22, k.host.y - 9, 22, { opacity: v(o.host), boxShadow: "none" }));
    els.push(L("ht", x0 + 58, k.host.y - k.host.size * 0.86, w - 58, k.host.size, "Mira is hosting", { fontFamily: "Geist", fontWeight: 500, color: k.host.color, textAlign: "left", opacity: v(o.host) }));
  }
  // ---- the bottom of the card
  const by = 752, bh = 72, rs = v(o.rsvp, 0), sd = v(o.send, 0), go = v(o.going, 0), pr = v(o.press, 0);
  const label = (id: string, x: number, bw: number, text: string, color: string, a: number) => L(id, x, by + 19, bw, 29, text, { fontFamily: "Geist", fontWeight: 600, letterSpacing: "-0.015em", color, opacity: a });
  if (rs > 0) {
    const pu = v(o.pulse, 0);
    els.push(R("b1", x0, by, 306, bh, { background: k.btn.bg, borderRadius: 36, opacity: rs, transform: `scale(${(1 - 0.05 * pu).toFixed(3)})`, boxShadow: pu > 0.03 ? `0 0 0 ${(14 * pu).toFixed(1)}px rgba(242, 193, 78, ${(0.45 * pu).toFixed(2)})` : "none" }), label("b1t", x0, 306, v(o.yes, 0) > 0 ? "You’re in" : "I’m in", k.btn.ink, rs));
    els.push(R("b2", x0 + 322, by, w - 322, bh, { border: `2.5px solid ${k.btn.line}`, borderRadius: 36, boxSizing: "border-box", opacity: rs }), label("b2t", x0 + 322, w - 322, "Can’t", k.btn.ghost, rs));
  }
  if (sd > 0) {
    const sc = 1 - 0.04 * pr;
    els.push(R("bs", x0, by, w, bh, { background: k.btn.bg, borderRadius: 36, opacity: sd, transform: `scale(${sc.toFixed(3)})`, boxShadow: pr > 0 ? `0 0 0 ${(10 * pr).toFixed(1)}px rgba(255, 255, 255, ${(0.25 * pr).toFixed(2)})` : "none" }), label("bst", x0, w, o.sendLabel ?? `Send to ${GUESTS.length} guests`, k.btn.ink, sd * v(o.labelA)));
  }
  if (go > 0) {
    const rowf = o.row ?? [], shown = rowf.slice(0, SHOWN);
    shown.forEach((g, i) => { if (g.k > 0) els.push(face(`g${i}`, g.who, x0 + 28 + i * 43, by + 36, 28 * Math.min(1.15, g.k), { opacity: go * Math.min(1, g.k * 2), boxShadow: `0 0 0 3px ${k.bg}` })); });
    const more = rowf.filter((g) => g.k >= 1).length - SHOWN;
    if (more > 0) els.push(R("mo", x0 + 28 + SHOWN * 43 - 28, by + 8, 56, 56, { borderRadius: 28, background: k.btn.bg, boxShadow: `0 0 0 3px ${k.bg}`, opacity: go }), L("mot", x0 + 28 + SHOWN * 43 - 28, by + 23, 56, 22, `+${more}`, { fontFamily: "Geist", fontWeight: 600, color: k.btn.ink, opacity: go }));
    els.push(L("cnt", x0, by + 20, w, 29, `${o.count ?? 0} of ${GUESTS.length} in`, { fontFamily: "Geist", fontWeight: 600, letterSpacing: "-0.02em", color: k.rows.color, textAlign: "right", opacity: go }));
  }
  return <div key={key} style={{ position: "absolute", left: PAD, top: PAD, width: CW, height: CH, borderRadius: CR, overflow: "hidden", background: k.bg, boxShadow: k.shade }}>{els}</div>;
}

/** stand a card in the world: its middle at (cx, cy), at a size, pushed sideways and back and turned (for the row of looks),
 *  soft if it is out of focus. The outer box is bigger than the card so the shadow and the blur have room. */
export function place(key: string, child: any, cx: number, cy: number, o: { s?: number; dx?: number; dy?: number; dz?: number; turn?: number; tilt?: number; sway?: number; blur?: number; opacity?: number } = {}) {
  const s = o.s ?? 1, tf = `perspective(2400px) rotateY(${(o.sway ?? 0).toFixed(3)}deg) translate3d(${(o.dx ?? 0).toFixed(2)}px, ${(o.dy ?? 0).toFixed(2)}px, ${(o.dz ?? 0).toFixed(2)}px) rotateY(${(o.turn ?? 0).toFixed(3)}deg) rotateX(${(o.tilt ?? 0).toFixed(3)}deg) scale(${s.toFixed(4)})`;
  return (
    <div key={key} style={{ position: "absolute", left: cx - CW / 2 - PAD, top: cy - CH / 2 - PAD, width: CW + 2 * PAD, height: CH + 2 * PAD, transform: tf, opacity: o.opacity ?? 1, filter: (o.blur ?? 0) > 0.25 ? `blur(${(o.blur as number).toFixed(2)}px)` : "none" }}>{child}</div>
  );
}
