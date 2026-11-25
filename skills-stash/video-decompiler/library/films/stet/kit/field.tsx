// The air behind the page: soft colour that moves like light through cloth, and takes the build's mood.
// Calm while things pass, flushed when one fails, held once the flake is held, clear from the release. (The person asked for a ground
// with more character after an early cut on plain white.)
// Only gradients: no filters, so nothing frame-sized goes through a blur (TRAPS: filtered layers).
import { CLOCK } from "./times.gen";

export type Mood = { base: string; c: [string, string, string, string]; a: number };
export const MOODS: Record<string, Mood> = {
  // one family of colour a mood, and white: sky while it passes, a flush when it fails, sky with a memory of the flush
  // once it is held, and morning (sky and one corner of sun) from the release on
  calm: { base: "#EEF2F6", c: ["#A9CDF5", "#DDEBFA", "#BCD8F6", "#E4E1F8"], a: 0.92 },
  alarm: { base: "#F9E4D8", c: ["#FF8E60", "#FFC09B", "#FFAAAE", "#FFD08E"], a: 0.95 },
  held: { base: "#EEF1F5", c: ["#A7CBF3", "#D6E6F8", "#BBD7F5", "#F7D8CA"], a: 0.92 },
  clear: { base: "#F1F4F6", c: ["#9CCAF8", "#FFE7A8", "#BEDFFA", "#FFFFFF"], a: 0.95 },
};
const rgb = (h: string) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mixRgb = (ws: [Mood, number][], pick: (m: Mood) => string) => {
  const out = [0, 0, 0];
  let tot = 0;
  for (const [m, w] of ws) { const c = rgb(pick(m)); out[0] += c[0] * w; out[1] += c[1] * w; out[2] += c[2] * w; tot += w; }
  return out.map((v) => Math.round(v / (tot || 1)));
};
// each soft shape: where it sits (share of the frame), how far it wanders, its size in px, its speeds, its tilt, its colour
const BLOBS: [number, number, number, number, number, number, number, number, number, number, number][] = [
  [0.20, 0.28, 0.10, 0.08, 1700, 1100, 0.21, 0.17, 0.0, 18, 0],
  [0.80, 0.20, 0.08, 0.10, 1500, 1000, 0.17, 0.23, 1.3, -12, 1],
  [0.72, 0.82, 0.12, 0.07, 1700, 1050, 0.19, 0.15, 2.1, 10, 2],
  [0.18, 0.86, 0.09, 0.09, 1400, 1000, 0.23, 0.20, 3.4, -20, 3],
  [0.50, 0.50, 0.18, 0.12, 1150, 800, 0.13, 0.11, 4.2, 0, 0],
];
const RIBBONS: [number, number, number, number, number, number, number][] = [
  [0.42, 0.34, 2600, 320, -18, 0.12, 0.5],
  [0.62, 0.74, 2400, 260, -24, 0.09, 0.42],
];

/** the field at frame f. `ws` is how much of each mood is in the air; (dx, dy) lets it lag behind the camera. */
export function field(f: number, ws: [Mood, number][], w: number, h: number, dx = 0, dy = 0) {
  const t = f / CLOCK.FPS, out: any[] = [];
  const base = mixRgb(ws, (m) => m.base), alpha = ws.reduce((a, [m, k]) => a + m.a * k, 0) / (ws.reduce((a, [, k]) => a + k, 0) || 1);
  out.push(<div key="fbase" style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: `rgb(${base.join(",")})` }} />);
  BLOBS.forEach(([x0, y0, ax, ay, bw, bh, wx, wy, ph, rot, ci], i) => {
    const c = mixRgb(ws, (m) => m.c[ci]).join(",");
    const cx = (x0 + ax * Math.sin(wx * t * 2 + ph)) * w + dx, cy = (y0 + ay * Math.cos(wy * t * 2 + ph * 1.7)) * h + dy;
    const a = alpha * (i === 4 ? 0.55 : 1);
    out.push(<div key={`fb${i}`} style={{ position: "absolute", left: cx - bw / 2, top: cy - bh / 2, width: bw, height: bh, transform: `rotate(${(rot + 8 * Math.sin(0.11 * t * 2 + ph)).toFixed(2)}deg)`,
      background: `radial-gradient(closest-side, rgba(${c},${a.toFixed(3)}) 0%, rgba(${c},${(a * 0.86).toFixed(3)}) 22%, rgba(${c},${(a * 0.5).toFixed(3)}) 50%, rgba(${c},${(a * 0.15).toFixed(3)}) 78%, rgba(${c},0) 100%)` }} />);
  });
  RIBBONS.forEach(([x0, y0, rw, rh, rot, sp, a], i) => {
    const cx = x0 * w + 0.10 * w * Math.sin(sp * t * 2 + i * 2.2) + dx * 1.4, cy = (y0 + 0.13 * Math.sin(sp * 1.3 * t * 2 + i)) * h + dy * 1.4;
    out.push(<div key={`fr${i}`} style={{ position: "absolute", left: cx - rw / 2, top: cy - rh / 2, width: rw, height: rh, transform: `rotate(${(rot + 6 * Math.sin(0.07 * t * 2 + i * 1.9)).toFixed(2)}deg)`,
      background: `radial-gradient(closest-side, rgba(255,255,255,${a}) 0%, rgba(255,255,255,${(a * 0.86).toFixed(3)}) 22%, rgba(255,255,255,${(a * 0.5).toFixed(3)}) 50%, rgba(255,255,255,${(a * 0.15).toFixed(3)}) 78%, rgba(255,255,255,0) 100%)` }} />);
  });
  return out;
}

/** grain over everything, new every frame: it keeps the soft colour from banding and gives the picture a surface */
export function grain(f: number, w: number, h: number, opacity = 0.24) {
  return (
    <svg key="grain" style={{ position: "absolute", left: 0, top: 0, mixBlendMode: "overlay", opacity }} width={w} height={h}>
      <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={String((f % 97) + 1)} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width={w} height={h} filter="url(#grainF)" />
    </svg>
  );
}
