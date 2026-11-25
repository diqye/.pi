// Draws the wall from any set of panels. Each panel is a whole frame at full size, moved and scaled by one camera, so the
// push lands exactly on a live scene with nothing to swap.
import { clamp, easeBy, hash, lerp, prog } from "../lib/core";
import { JoinProps, layer } from "../lib/join";
import { tokenOf } from "../lib/parts";

type Panel = { id: string; node: any; x: number; y: number };

const logLerp = (a: number, b: number, e: number) => Math.exp(lerp(Math.log(a), Math.log(b), e));

function arrange(panels: { id: string; node: any }[], W: number, H: number, P: any): Panel[] {
  const n = panels.length;
  const cols = Math.max(2, Math.ceil(Math.sqrt(n)));
  const G = W * P.gap;
  return panels.map((p, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const nudgeX = (hash(i, 31) - 0.5) * 2 * P.loose * G, nudgeY = (hash(i, 37) - 0.5) * 2 * P.loose * G;
    const shift = r % 2 ? (W + G) * 0.32 : 0;
    return { ...p, x: c * (W + G) + shift + nudgeX, y: r * (H + G) + nudgeY };
  });
}

// One camera: scale s, looking at world point (cx, cy).
type Cam = { s: number; cx: number; cy: number };

function between(a: Cam, b: Cam, e: number): Cam {
  const s = logLerp(a.s, b.s, e);
  const k = Math.abs(1 / b.s - 1 / a.s) > 1e-6 ? (1 / s - 1 / a.s) / (1 / b.s - 1 / a.s) : e;
  return { s, cx: lerp(a.cx, b.cx, k), cy: lerp(a.cy, b.cy, k) };
}

function elbow(a: Panel, b: Panel, W: number, H: number) {
  const sameRow = Math.abs(a.y - b.y) < H * 0.6;
  if (sameRow) {
    const x0 = a.x + W, y0 = a.y + H / 2, x1 = b.x, y1 = b.y + H / 2, mx = (x0 + x1) / 2;
    return [[x0, y0], [mx, y0], [mx, y1], [x1, y1]];
  }
  const x0 = a.x + W / 2, y0 = a.y + H, x1 = b.x + W / 2, y1 = b.y, my = (y0 + y1) / 2;
  return [[x0, y0], [x0, my], [x1, my], [x1, y1]];
}

function partial(pts: number[][], k: number) {
  const seg = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  const total = seg.reduce((a, b) => a + b, 0) * clamp(k);
  const out = [pts[0]];
  let left = total;
  for (let i = 0; i < seg.length; i++) {
    if (left >= seg[i]) { out.push(pts[i + 1]); left -= seg[i]; continue; }
    const u = seg[i] ? left / seg[i] : 0;
    out.push([lerp(pts[i][0], pts[i + 1][0], u), lerp(pts[i][1], pts[i + 1][1], u)]);
    break;
  }
  return out;
}

export function RecapWall({ panels, startIndex, intoIndex, p, P, W, H, tone, style, lineInk, ground, fps, frames }: { panels: { id: string; node: any }[]; startIndex: number; intoIndex: number; p: number; P: any; W: number; H: number; tone: any; style: any; lineInk: string; ground: string; fps: number; frames: number }) {
  const m = Math.min(W, H);
  const placed = arrange(panels, W, H, P);
  const xs = placed.flatMap((q) => [q.x, q.x + W]), ys = placed.flatMap((q) => [q.y, q.y + H]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const fit = Math.min(W / (x1 - x0), H / (y1 - y0)) * P.fit;
  const camOf = (q: Panel): Cam => ({ s: 1, cx: q.x + W / 2, cy: q.y + H / 2 });
  const start = camOf(placed[startIndex]), into = camOf(placed[intoIndex]);
  const wall: Cam = { s: fit, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
  const e = easeBy(P.ease);
  const holdU = clamp((p - P.pull) / (P.push - P.pull));
  const crept = wall.s * (1 + P.drift * holdU);
  const held: Cam = { s: crept, cx: wall.cx, cy: wall.cy };
  const cam = p < P.pull ? between(start, wall, e(p / P.pull)) : p < P.push ? held : between(held, into, e((p - P.push) / (1 - P.push)));
  const screen = (wx: number, wy: number) => [(wx - cam.cx) * cam.s + W / 2, (wy - cam.cy) * cam.s + H / 2];
  const onWall = clamp((1 - cam.s) / (1 - fit));

  const cells: any[] = [];
  placed.forEach((q, i) => {
    const [sx, sy] = screen(q.x, q.y);
    if (sx > W || sy > H || sx + W * cam.s < 0 || sy + H * cam.s < 0) return;
    const r = P.corner * onWall;
    const line = 1 / cam.s;
    cells.push(
      <div key={q.id} style={{ ...layer, width: W, height: H, transformOrigin: "0px 0px", transform: `translate(${sx.toFixed(2)}px, ${sy.toFixed(2)}px) scale(${cam.s.toFixed(5)})`, boxShadow: onWall > 0.02 ? style.shadow?.window : undefined, borderRadius: r }}>
        <div style={{ ...layer, width: W, height: H, borderRadius: r, overflow: "hidden" }}>{q.node}</div>
        {onWall > 0.02 ? <div style={{ ...layer, width: W, height: H, borderRadius: r, border: `${line * 2}px solid ${hexOr(lineInk, 0.5 * onWall)}`, boxSizing: "border-box" }} /> : null}
        {P.labels?.[q.id] && onWall > 0.4 ? <div style={{ position: "absolute", left: 0, top: H + 18, fontFamily: style.type.ui?.family, fontWeight: style.type.ui?.weight, fontSize: Math.min(H * 0.07, 22 / cam.s), color: lineInk, opacity: clamp((onWall - 0.4) * 2.2) }}>{P.labels[q.id]}</div> : null}
      </div>,
    );
  });

  const drawSec = P.drawDur * (fps > 0 ? 1 : 1);
  const lineStart = P.pull * 0.72;
  const span = frames / fps;
  const links: any[] = [];
  const list: [number, number][] = [];
  for (let i = 0; i + 1 < placed.length; i++) list.push([i, i + 1]);
  list.forEach(([a, b], i) => {
    const draw = prog(p, lineStart + (i * 0.1) / Math.max(1, list.length), drawSec / span);
    if (draw <= 0) return;
    const pts = partial(elbow(placed[a], placed[b], W, H), draw).map(([x, y]) => screen(x, y));
    const d = pts.map(([x, y], k) => `${k ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
    const [ex, ey] = pts[pts.length - 1];
    links.push(<path key={`l${i}`} d={d} fill="none" stroke={lineInk} strokeWidth={P.line * m} strokeLinecap="round" strokeLinejoin="round" />);
    links.push(<circle key={`c${i}`} cx={ex} cy={ey} r={P.line * m * 2.2} fill={lineInk} />);
  });

  const grid = 56 * cam.s;
  const ox = (-cam.cx * cam.s + W / 2) % grid, oy = (-cam.cy * cam.s + H / 2) % grid;
  return (
    <div style={{ ...layer, width: W, height: H, overflow: "hidden", background: ground }}>
      <div style={{ ...layer, width: W, height: H, backgroundImage: `radial-gradient(circle, ${hexOr(lineInk, 0.16)} ${Math.max(1, 1.5 * cam.s)}px, transparent ${Math.max(1.5, 2 * cam.s)}px)`, backgroundSize: `${grid}px ${grid}px`, backgroundPosition: `${ox}px ${oy}px`, opacity: onWall }} />
      {cells}
      {links.length && onWall > 0.05 ? <svg width={W} height={H} style={{ ...layer, opacity: clamp(onWall * 2.2) }}>{links}</svg> : null}
    </div>
  );
}

function hexOr(c: string, a: number) {
  if (!c || c[0] !== "#" || c.length < 7) return c;
  const n = parseInt(c.slice(1, 7), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

export function Join({ from, to, p, frames, fps, params, style, W, H, toneTo, earlier }: JoinProps) {
  const past = (earlier ?? []).slice(0, -1).map((e) => ({ id: e.id, node: e.node }));
  const panels = [...past, { id: "__from", node: from }, { id: "__to", node: to }];
  const startIndex = past.length;
  const asked = params.into === "next" ? -1 : panels.findIndex((q) => q.id === params.into);
  if (params.into !== "next" && asked < 0) throw new Error(`recap-wall: no earlier beat called ${params.into}`);
  const intoIndex = asked < 0 ? panels.length - 1 : asked;
  const lineInk = tokenOf(style, toneTo, params.ink) ?? params.ink;
  const ground = params.ground ? (tokenOf(style, toneTo, params.ground) ?? params.ground) : toneTo.ground;
  return <RecapWall panels={panels} startIndex={startIndex} intoIndex={intoIndex} p={p} P={params} W={W} H={H} tone={toneTo} style={style} lineInk={lineInk} ground={ground} fps={fps} frames={frames} />;
}
