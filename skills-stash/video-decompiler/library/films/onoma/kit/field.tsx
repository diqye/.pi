// The air: a dark room with soft colour moving in it, which takes the colour of the sound being made. One family at a
// time (BOARD.md, the cast). Only gradients, no filters. The same mechanism as Stet's ground (library/films/stet), in the dark.
import { FPS } from "./core";

export type Mood = { base: string; c: [string, string, string, string]; a: number };
export const MOODS: Record<string, Mood> = {
  dark: { base: "#07080C", c: ["#0B0D14", "#0A0C12", "#0C0E16", "#090A10"], a: 0.6 },
  rain: { base: "#090D16", c: ["#1F3F68", "#17324F", "#2A4770", "#122238"], a: 0.8 },
  thunder: { base: "#0C0A18", c: ["#43358A", "#6557C0", "#2E2660", "#8C80E6"], a: 0.8 },
  steps: { base: "#110C08", c: ["#6B4312", "#8A5516", "#4A2F10", "#A86C1E"], a: 0.7 },
  echo: { base: "#07100F", c: ["#0F5454", "#146C6A", "#0C3F40", "#1E8A86"], a: 0.75 },
  heart: { base: "#120709", c: ["#6A141C", "#8C1A24", "#4A0F14", "#B4222E"], a: 0.75 },
  warm: { base: "#0C0B10", c: ["#252A52", "#5A4220", "#1B1F3C", "#3A2C5E"], a: 0.75 },
};
const rgb = (h: string) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mix = (ws: [Mood, number][], pick: (m: Mood) => string) => {
  const o = [0, 0, 0]; let t = 0;
  for (const [m, w] of ws) { const c = rgb(pick(m)); o[0] += c[0] * w; o[1] += c[1] * w; o[2] += c[2] * w; t += w; }
  return o.map((v) => Math.round(v / (t || 1)));
};
const BLOBS: [number, number, number, number, number, number, number, number, number, number, number][] = [
  [0.22, 0.30, 0.10, 0.08, 1700, 1100, 0.21, 0.17, 0.0, 18, 0],
  [0.80, 0.24, 0.08, 0.10, 1500, 1000, 0.17, 0.23, 1.3, -12, 1],
  [0.70, 0.84, 0.12, 0.07, 1700, 1050, 0.19, 0.15, 2.1, 10, 2],
  [0.20, 0.86, 0.09, 0.09, 1400, 1000, 0.23, 0.20, 3.4, -20, 3],
  [0.50, 0.52, 0.18, 0.12, 1200, 820, 0.13, 0.11, 4.2, 0, 3],
];
/** the air at frame f. `ws`: how much of each mood is in the room; (dx, dy): how far it lags behind the camera */
export function field(f: number, ws: [Mood, number][], w: number, h: number, dx = 0, dy = 0) {
  const t = f / FPS, out: any[] = [];
  const base = mix(ws, (m) => m.base), tot = ws.reduce((a, [, k]) => a + k, 0) || 1, alpha = ws.reduce((a, [m, k]) => a + m.a * k, 0) / tot;
  out.push(<div key="fbase" style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: `rgb(${base.join(",")})` }} />);
  BLOBS.forEach(([x0, y0, ax, ay, bw, bh, wx, wy, ph, rot, ci], i) => {
    const c = mix(ws, (m) => m.c[ci]).join(","), a = alpha * (i === 4 ? 0.6 : 1);
    const cx = (x0 + ax * Math.sin(wx * t * 2 + ph)) * w + dx, cy = (y0 + ay * Math.cos(wy * t * 2 + ph * 1.7)) * h + dy;
    out.push(<div key={`fb${i}`} style={{ position: "absolute", left: cx - bw / 2, top: cy - bh / 2, width: bw, height: bh, transform: `rotate(${(rot + 8 * Math.sin(0.11 * t * 2 + ph)).toFixed(2)}deg)`,
      background: `radial-gradient(closest-side, rgba(${c},${a.toFixed(3)}) 0%, rgba(${c},${(a * 0.86).toFixed(3)}) 22%, rgba(${c},${(a * 0.5).toFixed(3)}) 50%, rgba(${c},${(a * 0.15).toFixed(3)}) 78%, rgba(${c},0) 100%)` }} />);
  });
  return out;
}
/** grain over everything, new every frame */
export function grain(f: number, w: number, h: number, opacity = 0.22) {
  return (
    <svg key="grain" style={{ position: "absolute", left: 0, top: 0, mixBlendMode: "overlay", opacity }} width={w} height={h}>
      <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={String((f % 97) + 1)} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width={w} height={h} filter="url(#grainF)" />
    </svg>
  );
}
