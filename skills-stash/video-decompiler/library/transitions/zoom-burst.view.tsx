// Draws the rush from any two nodes. The copies are averaged by giving the k-th copy an opacity of 1 / (k + 1), so all of
// them weigh the same however many there are: that's what reads as a blur and not as a stack of ghosts.
import { clamp, ease, lerp } from "../lib/core";
import { JoinProps, layer } from "../lib/join";

function Stack({ node, P, scale, spread, amount, W, H, m }: any) {
  const n = Math.max(1, Math.round(1 + (P.copies - 1) * clamp(amount)));
  const out: any[] = [];
  const origin = `${P.cx * W}px ${P.cy * H}px`;
  for (let k = 0; k < n; k++) {
    const s = scale * (1 + spread * k);
    out.push(<div key={k} style={{ ...layer, width: W, height: H, transformOrigin: origin, transform: `scale(${s.toFixed(4)})`, opacity: 1 / (k + 1) }}>{node}</div>);
  }
  const blur = P.soft * m * clamp((amount - 0.35) / 0.65);
  return <div style={{ ...layer, width: W, height: H, filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined }}>{out}</div>;
}

export function ZoomBurst({ from, to, p, P, W, H }: { from: any; to: any; p: number; P: any; W: number; H: number }) {
  const m = Math.min(W, H);
  let content;
  if (p < P.cut) {
    const u = p / P.cut;
    const scale = lerp(1, P.reach, ease.inCubic(u));
    const speed = u * u;
    content = <Stack node={from} P={P} scale={scale} spread={P.spread * speed} amount={speed * 1.15} W={W} H={H} m={m} />;
  } else {
    const v = (p - P.cut) / (1 - P.cut);
    const e = ease.outCubic(v);
    const speed = (1 - e) * (1 - e);
    content = <Stack node={to} P={P} scale={lerp(P.land, 1, e)} spread={P.spread * speed * 0.8} amount={speed * 1.1} W={W} H={H} m={m} />;
  }
  return <div style={{ ...layer, width: W, height: H, overflow: "hidden" }}>{content}</div>;
}

export function Join({ from, to, p, params, W, H }: JoinProps) {
  return <ZoomBurst from={from} to={to} p={p} P={params} W={W} H={H} />;
}
