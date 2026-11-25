// The room: paper with soft colour moving in it. Its job is to say what the card is wearing: the colours are taken
// from the art of the look in front (BOARD.md, the cast). Only gradients, no filters. The same mechanism as the air
// in stet's and onoma's kit/field.tsx, with one palette a look.
import { FPS } from "./core";

export type Mood = { base: string; c: [string, string, string, string]; a: number };
export const MOODS: Record<string, Mood> = {
  paper: { base: "#F4EEE3", c: ["#F6D9B8", "#F3E3A8", "#EBCFC4", "#DCE6E0"], a: 0.75 },      // before anything is chosen: warm, plain
  mess: { base: "#EFEBE4", c: ["#DDD9D2", "#E4DDD0", "#D6D8DA", "#E6E0D6"], a: 0.7 },        // the group chat: the colour gone out of it
  irises: { base: "#EEF0E2", c: ["#7FA6D8", "#9CC39A", "#E9D277", "#5F7FCB"], a: 0.6 },
  wave: { base: "#EDE6D3", c: ["#2F4F86", "#8FA9C4", "#D9C9A3", "#1D3566"], a: 0.55 },
  banquet: { base: "#1A1512", c: ["#6B2A2F", "#3E4A2C", "#8A5A2A", "#2A1D24"], a: 0.75 },
  sunday: { base: "#EEF0DC", c: ["#8DB26A", "#E3C977", "#6FA38C", "#D98F5A"], a: 0.6 },
  night: { base: "#0A141B", c: ["#17424F", "#122C42", "#2B2A5C", "#0F3A4A"], a: 0.8 },       // the fireworks print's own night: its teal sky, with the blue of its river
};
const rgb = (h: string) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mix = (ws: [Mood, number][], pick: (m: Mood) => string) => {
  const o = [0, 0, 0]; let t = 0;
  for (const [m, w] of ws) { const c = rgb(pick(m)); o[0] += c[0] * w; o[1] += c[1] * w; o[2] += c[2] * w; t += w; }
  return o.map((v) => Math.round(v / (t || 1)));
};
/** how dark the room is, 0 (paper) to 1 (night): type that sits on the room reads it to choose its own colour */
export const dark = (ws: [Mood, number][]) => { const b = mix(ws, (m) => m.base); return 1 - Math.min(1, (0.3 * b[0] + 0.59 * b[1] + 0.11 * b[2]) / 235); };
const BLOBS: [number, number, number, number, number, number, number, number, number, number, number][] = [
  [0.20, 0.28, 0.10, 0.08, 1700, 1100, 0.21, 0.17, 0.0, 18, 0],
  [0.82, 0.22, 0.08, 0.10, 1500, 1000, 0.17, 0.23, 1.3, -12, 1],
  [0.72, 0.86, 0.12, 0.07, 1700, 1050, 0.19, 0.15, 2.1, 10, 2],
  [0.18, 0.88, 0.09, 0.09, 1400, 1000, 0.23, 0.20, 3.4, -20, 3],
  [0.50, 0.50, 0.18, 0.12, 1200, 820, 0.13, 0.11, 4.2, 0, 1],
];
/** the room at frame f. `ws`: how much of each mood is in it; (dx, dy): how far it lags behind the camera */
export function field(f: number, ws: [Mood, number][], w: number, h: number, dx = 0, dy = 0) {
  const t = f / FPS, out: any[] = [];
  const base = mix(ws, (m) => m.base), tot = ws.reduce((a, [, k]) => a + k, 0) || 1, alpha = ws.reduce((a, [m, k]) => a + m.a * k, 0) / tot;
  out.push(<div key="fbase" style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: `rgb(${base.join(",")})` }} />);
  BLOBS.forEach(([x0, y0, ax, ay, bw, bh, wx, wy, ph, rot, ci], i) => {
    const c = mix(ws, (m) => m.c[ci]).join(","), a = alpha * (i === 4 ? 0.5 : 1);
    const cx = (x0 + ax * Math.sin(wx * t * 2 + ph)) * w + dx, cy = (y0 + ay * Math.cos(wy * t * 2 + ph * 1.7)) * h + dy;
    out.push(<div key={`fb${i}`} style={{ position: "absolute", left: cx - bw / 2, top: cy - bh / 2, width: bw, height: bh, transform: `rotate(${(rot + 8 * Math.sin(0.11 * t * 2 + ph)).toFixed(2)}deg)`,
      background: `radial-gradient(closest-side, rgba(${c},${a.toFixed(3)}) 0%, rgba(${c},${(a * 0.86).toFixed(3)}) 22%, rgba(${c},${(a * 0.5).toFixed(3)}) 50%, rgba(${c},${(a * 0.15).toFixed(3)}) 78%, rgba(${c},0) 100%)` }} />);
  });
  return out;
}
/** grain over everything, new every frame */
export function grain(f: number, w: number, h: number, opacity = 0.2) {
  return (
    <svg key="grain" style={{ position: "absolute", left: 0, top: 0, mixBlendMode: "overlay", opacity }} width={w} height={h}>
      <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={String((f % 97) + 1)} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width={w} height={h} filter="url(#grainF)" />
    </svg>
  );
}
