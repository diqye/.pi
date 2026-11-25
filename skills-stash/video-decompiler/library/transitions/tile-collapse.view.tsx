// Draws the tile collapse from any two nodes. Tiles that haven't left stay in one clipped copy of the picture, so the cost
// grows only with the tiles in flight, and nothing is drawn after a tile has become its dot.
import { clamp, easeBy, ease, hash, lerp, prog } from "../lib/core";
import { readable } from "../lib/parts";
import { JoinProps, layer } from "../lib/join";

const FLY0 = 0.07, FLY1 = 0.68, OPEN0 = 0.74, TAU = Math.PI * 2;

type Tile = { x: number; y: number; w: number; h: number; hx: number; hy: number; a0: number; r0: number; start: number; slot: number; lifted: boolean; order: number; turn: number };

function tilesOf(W: number, H: number, P: any): { tiles: Tile[]; cols: number; rows: number; dur: number } {
  const cols = Math.max(2, Math.round(P.cols));
  const rows = P.rows > 0 ? Math.round(P.rows) : Math.max(2, Math.round(cols * (H / W)));
  const tw = W / cols, th = H / rows;
  const cx = P.cx * W, cy = P.cy * H;
  const raw: Tile[] = [];
  let maxR = 1;
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    const hx = i * tw + tw / 2, hy = j * th + th / 2;
    const r0 = Math.hypot(hx - cx, hy - cy);
    maxR = Math.max(maxR, r0);
    raw.push({ x: i * tw, y: j * th, w: tw, h: th, hx, hy, a0: Math.atan2(hy - cy, hx - cx), r0, start: 0, slot: 0, lifted: false, order: 0, turn: (hash(i * 17 + j * 3, 5) - 0.5) * 2 });
  }
  const span = FLY1 - FLY0, dur = span * (1 - P.stagger);
  const dots = Math.max(3, Math.round(P.dots));
  raw.forEach((t, n) => {
    const near = t.r0 / maxR, h = hash(n, 11);
    t.order = P.order === "far-first" ? 1 - near : P.order === "near-first" ? near : 0.62 * h + 0.38 * (1 - near);
    t.start = FLY0 + span * P.stagger * t.order;
    t.slot = n % dots;
  });
  const lifted = [...raw].sort((a, b) => hash(raw.indexOf(a), 23) - hash(raw.indexOf(b), 23)).slice(0, Math.max(0, Math.round(P.lift)));
  lifted.forEach((t, n) => { t.lifted = true; t.start = Math.max(FLY0 * 0.6, t.start * 0.55) + n * 0.002; });
  return { tiles: raw, cols, rows, dur };
}

// The ring as it stands at p (0..1): each dot's centre and radius. A part that takes over from the dots starts from this at p = 1.
export function ringState(W: number, H: number, P: any, p: number) {
  const m = Math.min(W, H), cx = P.cx * W, cy = P.cy * H;
  const dots = Math.max(3, Math.round(P.dots));
  const open = P.handoff === "open" ? prog(p, OPEN0, 1 - OPEN0) : 0;
  const diag = Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) * 1.04;
  const ring = P.ringR * m;
  const opened = easeBy([0.5, 0, 0.12, 1])(open);
  const radius = lerp(ring, diag, opened);
  const spin = P.spin * TAU * (0.35 * clamp((p - FLY0) / (1 - FLY0)) + 0.65 * Math.pow(clamp((p - FLY0) / (1 - FLY0)), 2));
  const dot = P.dotR * m;
  return { cx, cy, radius, ring, dot, open: opened, count: dots, dots: Array.from({ length: dots }, (_, k) => { const a = -Math.PI / 2 + (k * TAU) / dots + spin; return { x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius, a }; }) };
}

export function TileCollapse({ from, to, p, P, W, H, ground, ink, shadow }: { from: any; to: any; p: number; P: any; W: number; H: number; ground: string; ink: string; shadow?: string }) {
  const { tiles, dur } = tilesOf(W, H, P);
  const fly = easeBy(P.ease);
  const m = Math.min(W, H), cx = P.cx * W, cy = P.cy * H;
  const ring = ringState(W, H, P, p);
  const arrivals = new Array<number[]>(ring.count).fill(null as any).map(() => [] as number[]);
  const open = P.handoff === "open" ? prog(p, OPEN0, 1 - OPEN0) : 0;

  // Tiles still home draw as one clipped copy of the picture.
  const pts: string[] = [];
  const pct = (x: number, y: number) => `${((x / W) * 100).toFixed(3)}% ${((y / H) * 100).toFixed(3)}%`;
  const flying: any[] = [];
  tiles.forEach((t, n) => {
    const arrive = t.start + dur;
    arrivals[t.slot].push(arrive);
    const lift = t.lifted ? ease.outCubic(prog(p, 0, Math.max(0.0001, t.start - 0.01))) : 0;
    const u = clamp((p - t.start) / dur);
    if (p < t.start) {
      const x1 = t.x + t.w + 0.5, y1 = t.y + t.h + 0.5;
      pts.push(pct(t.x, t.y), pct(x1, t.y), pct(x1, y1), pct(t.x, y1), pct(t.x, t.y), "0% 0%");
      if (!t.lifted || lift <= 0) return;
    }
    if (u >= 1) return;
    const e = fly(u);
    const ringNow = ringState(W, H, P, arrive);
    const target = ringNow.dots[t.slot];
    const turns = Math.round((t.a0 + P.swirl - target.a) / TAU);
    const a1 = target.a + TAU * turns;
    const a = lerp(t.a0, a1, e), r = lerp(t.r0, ringNow.radius, e);
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    const dxLift = t.lifted ? Math.cos(t.a0) * m * 0.012 * lift * (1 - e) : 0, dyLift = t.lifted ? Math.sin(t.a0) * m * 0.012 * lift * (1 - e) : 0;
    const shrink = Math.pow(e, 2.4);
    const D = ring.dot * 2;
    const sx = lerp(1 + 0.06 * lift, D / t.w, shrink), sy = lerp(1 + 0.06 * lift, D / t.h, shrink);
    const round = 50 * clamp((e - 0.35) / 0.65) ** 1.2;
    const inkA = clamp((e - 0.62) / 0.3);
    flying.push(
      <div key={n} style={{ position: "absolute", left: t.x, top: t.y, width: t.w, height: t.h, transform: `translate(${(x + dxLift - t.hx).toFixed(2)}px, ${(y + dyLift - t.hy).toFixed(2)}px) rotate(${(t.turn * 42 * e).toFixed(2)}deg) scale(${sx.toFixed(4)}, ${sy.toFixed(4)})`, transformOrigin: "50% 50%", borderRadius: `${round.toFixed(1)}%`, overflow: "hidden", boxShadow: t.lifted && e < 0.15 ? shadow : undefined }}>
        <div style={{ position: "absolute", left: -t.x, top: -t.y, width: W, height: H }}>{from}</div>
        {t.lifted ? <div style={{ position: "absolute", left: 0, top: 0, width: t.w, height: t.h, background: ink, opacity: 0.16 * (1 - e) * lift }} /> : null}
        <div style={{ position: "absolute", left: 0, top: 0, width: t.w, height: t.h, background: ink, opacity: inkA }} />
      </div>,
    );
  });

  const showOpen = P.handoff === "open" && open > 0;
  const toScale = 1 + 0.07 * (1 - ease.outCubic(open));

  return (
    <div style={{ ...layer, width: W, height: H, overflow: "hidden", background: ground }}>
      {pts.length ? <div style={{ ...layer, width: W, height: H, clipPath: `polygon(0% 0%, ${pts.join(", ")})` }}>{from}</div> : null}
      {flying}
      {ring.dots.map((d, k) => {
        const arr = arrivals[k];
        const landed = arr.filter((a) => p >= a).length;
        if (!landed) return null;
        const share = landed / arr.length;
        const bump = arr.reduce((s, a) => (p >= a ? Math.max(s, Math.exp(-(p - a) * 26)) : s), 0);
        const fade = 1 - clamp((open - 0.45) / 0.5);
        const r = ring.dot * (0.5 + 0.5 * ease.outCubic(share)) * (1 + 0.55 * bump) * (1 + 0.5 * open);
        return <div key={k} style={{ position: "absolute", left: d.x - r, top: d.y - r, width: r * 2, height: r * 2, borderRadius: "50%", background: ink, opacity: fade }} />;
      })}
      {showOpen ? <div style={{ ...layer, width: W, height: H, clipPath: `circle(${ring.radius.toFixed(2)}px at ${cx.toFixed(1)}px ${cy.toFixed(1)}px)` }}>
        <div style={{ ...layer, width: W, height: H, transform: `scale(${toScale.toFixed(4)})`, transformOrigin: `${cx}px ${cy}px` }}>{to}</div>
      </div> : null}
    </div>
  );
}

export function Join({ from, to, p, params, style, toneTo, W, H }: JoinProps) {
  const ground = params.ground ? (toneTo[params.ground] ?? style.color[params.ground]) : toneTo.ground;
  const ink = params.ink ? (toneTo[params.ink] ?? style.color[params.ink]) : readable(ground, toneTo.ink, toneTo.ground);
  return <TileCollapse from={from} to={to} p={p} P={params} W={W} H={H} ground={ground} ink={ink} shadow={style.shadow?.window} />;
}
