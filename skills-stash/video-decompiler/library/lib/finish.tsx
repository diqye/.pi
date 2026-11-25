// The finish: what makes clean vector frames feel like a real object. It wraps a whole film and reads one definition,
// style.finish, so a film's grade, grain, halation, vignette, weave, dust and overlays are set in one place.
// Every effect is optional, sizes follow the frame, rates are per second, and every value comes from the frame number.
import { Freeze, useCurrentFrame, useVideoConfig } from "raea";
import { GRAIN, OVERLAYS } from "../finish.gen";
import { rand } from "./optics";

const full: any = { position: "absolute", left: 0, top: 0, width: "100%", height: "100%" };

// The step a stepped effect is on: `rate` new values a second, whatever the film's frame rate.
const stepOf = (f: number, fps: number, rate: number) => Math.floor((f / fps) * rate + 1e-6);

function gradeFilter(g: any): string | undefined {
  if (!g) return undefined;
  const parts: string[] = [];
  for (const k of ["brightness", "contrast", "saturate"]) if (g[k] != null && g[k] !== 1) parts.push(`${k}(${g[k]})`);
  return parts.length ? parts.join(" ") : undefined;
}

// A gel over the lens: warm cuts blue and a little green, cool cuts red and a little green.
function warmthGel(w: number): string {
  const a = Math.abs(w), k = (x: number) => Math.round(255 * (1 - x));
  return w >= 0 ? `rgb(255, ${k(0.4 * a)}, ${k(a)})` : `rgb(${k(a)}, ${k(0.4 * a)}, 255)`;
}

// Filter steps that map luma at or under T to black and white to white.
function above(T: number, c = 8) {
  const b = (0.5 - 0.5 / c) / T, white = Math.min(1, (b - 0.5) * c + 0.5);
  return `saturate(0) brightness(${b.toFixed(4)}) contrast(${c}) brightness(${(1 / white).toFixed(4)})`;
}

// Halation is the frame's highlights blurred, tinted and screened back over the frame. Reading the frame through
// backdropFilter (no second copy of the film) keeps its cost flat however heavy the film is. raea ignores a blend on
// the backdrop element itself, so each read sits inside a plain wrapper that carries the blend.
// The small blur before the threshold stops thin bright strokes emitting a glow. The guard stops the glow landing on
// dark strokes that sit on a bright ground: it multiplies the glow by "this pixel is bright, or its surroundings are
// dark", so black type on a white card stays black while the dark edge beside a big highlight still takes the glow.
export function Halation({ amount = 0.25, radius = 14, color = "#ff6a2a", threshold = 0.9, protect, u = 1 }: any) {
  if (!(amount > 0)) return null;
  const pre = (protect ?? 0.32 * radius) * u, r = radius * u;
  return (
    <div style={{ ...full, mixBlendMode: "screen", opacity: amount }}>
      <div style={{ ...full, backdropFilter: `blur(${pre.toFixed(2)}px) ${above(threshold)} blur(${r.toFixed(2)}px)` }} />
      <div style={{ ...full, background: color, mixBlendMode: "multiply" }} />
      <div style={{ ...full, mixBlendMode: "multiply" }}>
        <div style={{ ...full, backdropFilter: `blur(${(0.6 * u).toFixed(2)}px) ${above(0.42)}` }} />
        <div style={{ ...full, mixBlendMode: "screen" }}>
          <div style={{ ...full, backdropFilter: `blur(${(40 * u).toFixed(1)}px) ${above(0.62)} invert(1)` }} />
        </div>
      </div>
    </div>
  );
}

function Grain({ g, f, fps, u }: any) {
  if (!(g.amount > 0)) return null;
  if (!GRAIN.length) throw new Error("finish: grain has no tiles. finish.gen.ts is empty or missing: copy it again from the skill's library.");
  const size = g.size ?? 1.4, step = stepOf(f, fps, g.fps ?? 24), seed = g.seed ?? 1;
  const tile = GRAIN[Math.floor(rand(seed, step, 1) * GRAIN.length)];
  const s = 512 * size * u;
  return <div style={{ ...full, backgroundImage: `url(${tile})`, backgroundSize: `${s.toFixed(1)}px ${s.toFixed(1)}px`, backgroundRepeat: "repeat", backgroundPosition: `${(rand(seed, step, 2) * s).toFixed(1)}px ${(rand(seed, step, 3) * s).toFixed(1)}px`, mixBlendMode: g.blend ?? "overlay", opacity: g.amount }} />;
}

// A ring of radius-noisy points: a speck of dirt, not a dot.
function speckPath(cx: number, cy: number, r: number, seed: number, k: number) {
  const n = 7;
  let d = "";
  for (let i = 0; i < n; i++) {
    const a = (i / n) * 2 * Math.PI, q = r * (0.6 + 0.8 * rand(seed, k, i + 40));
    d += `${i ? "L" : "M"}${(cx + Math.cos(a) * q).toFixed(1)} ${(cy + Math.sin(a) * q).toFixed(1)}`;
  }
  return d + "Z";
}

function Dust({ d, f, fps, W, H, u }: any) {
  if (!(d.amount > 0)) return null;
  const seed = d.seed ?? 3, step = stepOf(f, fps, d.fps ?? 12);
  const specks = Math.round(d.amount * 26), hairs = Math.round(d.amount * 3);
  const out: any[] = [];
  for (let i = 0; i < specks; i++) {
    const k = step * 1000 + i, dark = rand(seed, k, 3) < 0.35;
    out.push(<path key={`s${i}`} d={speckPath(rand(seed, k, 1) * W, rand(seed, k, 2) * H, (0.7 + 2.6 * rand(seed, k, 4) ** 3) * u, seed, k)} fill={dark ? "#000" : "#fff"} opacity={(dark ? 0.55 : 0.75) * (0.4 + 0.6 * rand(seed, k, 5))} />);
  }
  for (let i = 0; i < hairs; i++) {
    const k = step * 1000 + 500 + i;
    if (rand(seed, k, 9) > 0.45) continue;
    const x = rand(seed, k, 1) * W, y = rand(seed, k, 2) * H, a = rand(seed, k, 3) * 2 * Math.PI, l = (24 + 90 * rand(seed, k, 4)) * u;
    const bx = x + Math.cos(a + 0.9) * l * 0.6, by = y + Math.sin(a + 0.9) * l * 0.6, ex = x + Math.cos(a) * l, ey = y + Math.sin(a) * l;
    out.push(<path key={`h${i}`} d={`M${x.toFixed(1)} ${y.toFixed(1)}Q${bx.toFixed(1)} ${by.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`} fill="none" stroke={rand(seed, k, 5) < 0.5 ? "#000" : "#fff"} strokeWidth={(0.7 + rand(seed, k, 6)) * u} opacity={0.5} />);
  }
  // scratches outlive dust and hold a line while they run, drifting a little
  const span = 0.45, win = Math.floor(f / fps / span);
  for (let i = -1; i <= 1; i++) {
    const w = win + i;
    if (rand(seed, w, 21) > d.amount * 0.55) continue;
    const t0 = (w + rand(seed, w, 22) * 0.5) * span, life = (0.25 + rand(seed, w, 23)) * span, age = f / fps - t0;
    if (age < 0 || age > life) continue;
    const x0 = rand(seed, w, 24) * W, x = x0 + (rand(seed, w, 25) - 0.5) * 18 * u * (age / life);
    const fade = Math.sin((age / life) * Math.PI);
    out.push(<path key={`c${w}`} d={`M${x.toFixed(1)} 0L${(x + (rand(seed, w, 26) - 0.5) * 8 * u).toFixed(1)} ${H}`} stroke="#fff" strokeWidth={(0.8 + 0.8 * rand(seed, w, 27)) * u} opacity={(0.12 + 0.28 * rand(seed, w, 28)) * fade} fill="none" />);
  }
  return <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", left: 0, top: 0, width: W, height: H }}>{out}</svg>;
}

function Overlay({ o, f, fps, u, i }: any) {
  const tex = OVERLAYS[o.src];
  if (!tex) throw new Error(`finish: overlay "${o.src}" is not embedded: finish.gen.ts does not hold it.`);
  const drift = o.drift ?? [0, 0], t = f / fps;
  const flick = o.flicker ? 1 - o.flicker * rand(i + 77, stepOf(f, fps, 12), 1) : 1;
  const a = (o.opacity ?? 1) * flick;
  if (!(a > 0)) return null;
  let bg: any;
  if (o.fit === "tile") {
    const w = (o.scale ?? 1) * tex.w * u, h = (o.scale ?? 1) * tex.h * u;
    bg = { backgroundSize: `${w.toFixed(1)}px ${h.toFixed(1)}px`, backgroundRepeat: "repeat" };
  } else {
    bg = { backgroundSize: "cover", backgroundRepeat: drift[0] || drift[1] ? "repeat" : "no-repeat" };
  }
  return <div style={{ ...full, backgroundImage: `url(${tex.data})`, backgroundPosition: `${(drift[0] * t * u).toFixed(2)}px ${(drift[1] * t * u).toFixed(2)}px`, ...bg, mixBlendMode: o.blend ?? "normal", opacity: a }} />;
}

// Radial falloff on a smooth curve: a single straight ramp shows its start as a visible ring.
function vignetteCss(amount: number, softness: number) {
  const inner = Math.max(0, 1 - softness) * 100, stops = [`rgba(0,0,0,0) ${inner.toFixed(1)}%`];
  for (let i = 1; i <= 6; i++) {
    const p = i / 6, e = p * p * (3 - 2 * p);
    stops.push(`rgba(0,0,0,${(amount * e).toFixed(4)}) ${(inner + (100 - inner) * p).toFixed(1)}%`);
  }
  return `radial-gradient(ellipse farthest-corner at 50% 50%, ${stops.join(", ")})`;
}

export function Finish({ finish, children }: { finish: any; children: any }) {
  const f = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const u = Math.min(W, H) / 1080;
  const hold = finish.onTwos === true ? 2 : typeof finish.onTwos === "number" ? Math.max(1, Math.round(finish.onTwos)) : 1;
  let picture = hold > 1 ? <Freeze frame={f - (f % hold)}>{children}</Freeze> : children;
  const w = finish.weave;
  if (w?.px) {
    const step = stepOf(f, fps, w.fps ?? 12), seed = w.seed ?? 7, px = w.px * u;
    const dx = (rand(seed, step, 1) * 2 - 1) * px, dy = (rand(seed, step, 2) * 2 - 1) * px;
    // scaled just enough that the moved edge never shows; the film is still vector here, so nothing resamples
    const k = 1 + (2 * (px + 1)) / Math.min(W, H);
    picture = <div style={{ ...full, transform: `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px) scale(${k.toFixed(5)})`, transformOrigin: "50% 50%" }}>{picture}</div>;
  }
  const grade = gradeFilter(finish.grade);
  const warm = finish.grade?.warmth ?? 0;
  const h = finish.halation, v = finish.vignette;
  return (
    <div style={{ ...full, width: W, height: H, overflow: "hidden" }}>
      <div style={{ ...full, filter: grade }}>{picture}</div>
      {warm ? <div style={{ ...full, background: warmthGel(warm), mixBlendMode: "multiply" }} /> : null}
      {h ? <Halation {...h} u={u} /> : null}
      {(finish.overlays ?? []).map((o: any, i: number) => <Overlay key={i} o={o} f={f} fps={fps} u={u} i={i} />)}
      {v?.amount > 0 ? <div style={{ ...full, background: vignetteCss(v.amount, v.softness ?? 0.6) }} /> : null}
      {finish.grain ? <Grain g={finish.grain} f={f} fps={fps} u={u} /> : null}
      {finish.dust ? <Dust d={finish.dust} f={f} fps={fps} W={W} H={H} u={u} /> : null}
    </div>
  );
}
