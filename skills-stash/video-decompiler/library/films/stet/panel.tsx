// The checks panel: the specimen the film opens on and comes back to (BOARD.md, ties). A sheet of glass on the page.
// Its "tests" status dot sits exactly on a dot of the page's grid, because the catch's flush swells from it.
import { C, D, FB, GLASS, M, R, T, clamp01, lerp, mw, status, tw, type Run } from "./kit/stet";

export const PX = 968, PY = 348, PW = 624, HEAD = 60, ROW = 72, FOOT = 96;
export const PH = HEAD + 3 * ROW + FOOT;
export const rowY = (i: number, y = PY) => y + HEAD + ROW * i + ROW / 2;
export const dotX = (x = PX) => x + 40;
export const BTN = { w: 156, h: 52 };
export const btnAt = (x = PX, y = PY, h = PH) => ({ x: x + PW - 28 - BTN.w, y: y + h - 22 - BTN.h });
export type RowS = { label: string; state: Run; note: string };
const RULE = "rgba(20, 20, 30, 0.10)";

/** the panel. `k` is how far its body has opened out of its third row (0: only that row; 1: whole). */
export function checks(key: string, f: number, o: { x?: number; y?: number; rows: RowS[]; k?: number; at?: number; commit?: string; btn?: { label: string; down?: number; solid?: boolean; done?: boolean } }) {
  const x = o.x ?? PX, y = o.y ?? PY, k = o.k ?? 1, out: any[] = [];
  const part = (delay: number) => (o.at === undefined ? clamp01((k - 0.3) / 0.5) : clamp01((f - o.at * FB - delay + 1) / 9));
  const body = part(3);
  const top = lerp(rowY(2, y) - ROW / 2, y, k), bot = lerp(rowY(2, y) + ROW / 2, y + PH, k);
  out.push(R(`${key}bg`, x, top, PW, bot - top, { ...GLASS, borderRadius: 14, boxSizing: "border-box" }));
  if (body > 0) {
    out.push(T(`${key}h`, x + 28, y + 39, 22, "Checks", { opacity: body }));
    const commit = o.commit ?? "main · 4f2a91c";
    out.push(M(`${key}c`, x + PW - 28 - mw(commit, 18), y + 38, 18, commit, { color: C.grey, opacity: body }));
    out.push(R(`${key}hl`, x + 1.5, y + HEAD, PW - 3, 1.5, { background: RULE, opacity: body }));
  }
  o.rows.forEach((r, i) => {
    const vis = i === 2 ? 1 : part(i === 1 ? 0 : 6);
    if (vis <= 0) return;
    const cy = rowY(i, y) + (i === 2 ? 0 : (1 - vis) * 12);
    if (r.state === "fail") out.push(R(`${key}w${i}`, x + 1.5, cy - ROW / 2 + 1, PW - 3, ROW - 2, { background: "rgba(255, 77, 31, 0.13)", opacity: vis }));
    if (i > 0 && body > 0) out.push(R(`${key}l${i}`, x + 1.5, rowY(i, y) - ROW / 2, PW - 3, 1.5, { background: RULE, opacity: body }));
    out.push(<div key={`${key}s${i}`} style={{ opacity: vis }}>{status(`${key}d${i}`, f, dotX(x), cy, 9, r.state)}</div>);
    out.push(M(`${key}t${i}`, dotX(x) + 30, cy + 8.5, 24, r.label, { opacity: vis }));
    out.push(M(`${key}n${i}`, x + PW - 32 - mw(r.note, 22), cy + 8, 22, r.note, { color: r.state === "fail" ? C.red : C.grey, opacity: vis }));
  });
  const foot = part(9);
  if (o.btn && foot > 0) {
    out.push(R(`${key}fl`, x + 1.5, y + PH - FOOT, PW - 3, 1.5, { background: RULE, opacity: foot }));
    const b = btnAt(x, y);
    out.push(button(`${key}b`, b.x, b.y - (1 - foot) * 8, o.btn.label, o.btn.down ?? 0, !!o.btn.solid, foot));
  }
  return out;
}

/** a button: an outline until it is pressed, then solid */
export function button(key: string, x: number, y: number, label: string, down = 0, solid = false, opacity = 1) {
  const on_ = solid || down > 0.2, s = 1 - 0.04 * down, lw = tw(label, 22);
  return [
    R(`${key}r`, x, y, BTN.w, BTN.h, { background: on_ ? C.ink : "rgba(255, 255, 255, 0.9)", border: `1.5px solid ${C.ink}`, borderRadius: 10, boxSizing: "border-box", opacity, transform: `scale(${s})` }),
    T(`${key}t`, x + (BTN.w - lw) / 2, y + 34, 22, label, { color: on_ ? C.white : C.ink, opacity }),
  ];
}
