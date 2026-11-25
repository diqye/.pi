// Draws the smear from any two nodes. A column is the whole picture clipped to one strip and stretched from its top edge.
import { clamp, ease, hash, lerp } from "../lib/core";
import { JoinProps, layer } from "../lib/join";

// Smooth noise in 0..1, so neighbouring columns melt together and the front reads as a wave, not a comb.
function wave(x: number, seed: number) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(hash(i, seed), hash(i + 1, seed), u);
}

export function Smear({ from, to, p, P, W, H }: { from: any; to: any; p: number; P: any; W: number; H: number }) {
  const cols = Math.max(2, Math.round(P.cols));
  const cw = W / cols, feather = H * P.feather;
  const reveal = ease.outCubic(clamp(p * 1.1));
  const strips: any[] = [];
  for (let i = 0; i < cols; i++) {
    const c = i / cols;
    const front = 0.86 * wave(c * P.wander, P.seed) + 0.11 * wave(c * P.wander * 3.7, P.seed + 7) + 0.03 * hash(i, P.seed + 13);
    const u = clamp((p - front * P.stagger) / (1 - P.stagger));
    if (u >= 1) continue;
    const pull = ease.inQuart(u);
    const sy = 1 + (P.stretch - 1) * ease.inCubic(clamp(u * 1.15));
    const top = pull * H * P.drop;
    if (top >= H) continue;
    const L = i * cw;
    strips.push(
      <div key={i} style={{ ...layer, width: W, height: H, clipPath: `inset(0px ${(W - L - cw - 0.6).toFixed(2)}px 0px ${L.toFixed(2)}px)`, maskImage: top > 0.5 ? `linear-gradient(to bottom, transparent ${top.toFixed(1)}px, black ${(top + feather).toFixed(1)}px)` : undefined }}>
        <div style={{ ...layer, width: W, height: H, transformOrigin: "0px 0px", transform: `translate(0px, ${top.toFixed(2)}px) scale(1, ${sy.toFixed(4)})` }}>{from}</div>
      </div>,
    );
  }
  return (
    <div style={{ ...layer, width: W, height: H, overflow: "hidden" }}>
      <div style={{ ...layer, width: W, height: H, transform: `translate(0px, ${(H * P.pull * (1 - reveal)).toFixed(2)}px)` }}>{to}</div>
      {strips}
    </div>
  );
}

export function Join({ from, to, p, params, W, H }: JoinProps) {
  return <Smear from={from} to={to} p={p} P={params} W={W} H={H} />;
}
