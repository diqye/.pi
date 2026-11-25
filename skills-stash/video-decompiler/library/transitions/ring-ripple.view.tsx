// Draws the ripple from any two nodes. Each ring is one copy of the next scene behind a radial-gradient mask, so the cost is
// the number of rings and the edges stay smooth at any radius.
import { clamp, ease, lerp, prog } from "../lib/core";
import { JoinProps, layer } from "../lib/join";

const px = (n: number) => `${n.toFixed(1)}px`;

export function RingRipple({ from, to, p, P, W, H, ink }: { from: any; to: any; p: number; P: any; W: number; H: number; ink: string }) {
  const m = Math.min(W, H), cx = P.cx * W, cy = P.cy * H;
  const R = Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) * 1.03;
  const n = Math.max(1, Math.round(P.rings));
  const delay = n > 1 ? P.stagger / (n - 1) : 0;
  const reach = 1 - P.stagger;
  const q = (k: number) => prog(p, k * delay, reach);
  const lead = (k: number) => R * ease.outQuad(q(k));
  const floodP = prog(p, P.flood, 1 - P.flood);
  const flood = R * ease.inOutCubic(floodP);
  const fill = ease.inCubic(floodP);
  const f = 1.2 * (m / 1080);
  const layers: any[] = [];
  const rules: any[] = [];
  for (let k = n - 1; k >= 0; k--) {
    const qk = q(k);
    if (qk <= 0) continue;
    const L = lead(k);
    const band = L * P.thick * lerp(0.15, 1, Math.pow(qk, 1.2));
    const inner = Math.max(0, L - band);
    if (flood >= L) continue;
    const mask = inner > f
      ? `radial-gradient(circle at ${px(cx)} ${px(cy)}, transparent ${px(inner - f)}, black ${px(inner)}, black ${px(L)}, transparent ${px(L + f)})`
      : `radial-gradient(circle at ${px(cx)} ${px(cy)}, black ${px(L)}, transparent ${px(L + f)})`;
    const lens = 1 + P.refract * (k + 1) * (1 - fill) * lerp(1, 0.4, qk);
    layers.push(
      <div key={k} style={{ ...layer, width: W, height: H, maskImage: mask }}>
        <div style={{ ...layer, width: W, height: H, transformOrigin: `${cx}px ${cy}px`, transform: `scale(${lens.toFixed(4)})` }}>{to}</div>
      </div>,
    );
    if (P.line > 0) {
      const a = (1 - clamp((qk - 0.55) / 0.45)) * (1 - fill);
      if (a > 0.01) rules.push(<circle key={k} cx={cx} cy={cy} r={L} fill="none" stroke={ink} strokeWidth={P.line * m} opacity={0.75 * a} />);
    }
  }
  const pushed = 1 + 0.05 * ease.inCubic(p);
  return (
    <div style={{ ...layer, width: W, height: H, overflow: "hidden" }}>
      <div style={{ ...layer, width: W, height: H, transformOrigin: `${cx}px ${cy}px`, transform: `scale(${pushed.toFixed(4)})` }}>{from}</div>
      {floodP < 1 ? layers : null}
      {flood > 1 ? <div style={{ ...layer, width: W, height: H, clipPath: `circle(${px(flood)} at ${px(cx)} ${px(cy)})` }}>
        <div style={{ ...layer, width: W, height: H, transformOrigin: `${cx}px ${cy}px`, transform: `scale(${(1 + P.refract * 0.5 * (1 - ease.outCubic(floodP))).toFixed(4)})` }}>{to}</div>
      </div> : null}
      {rules.length ? <svg width={W} height={H} style={{ ...layer }}>{rules}</svg> : null}
    </div>
  );
}

export function Join({ from, to, p, params, W, H, style, toneTo }: JoinProps) {
  const ink = params.ink ? (toneTo[params.ink] ?? style.color[params.ink]) : toneTo.ink;
  return <RingRipple from={from} to={to} p={p} P={params} W={W} H={H} ink={ink} />;
}
