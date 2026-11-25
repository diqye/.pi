// Shared maths for every part: easing, poses, and the beat timeline built from outline + content.
// Nothing here knows any film's words, colours or faces.

export type Pose = {
  x?: number; y?: number; scale?: number; sx?: number; sy?: number;
  rotate?: number; skewX?: number; opacity?: number; blur?: number;
  rotateX?: number; rotateY?: number; perspective?: number;
};
export type Box = { w: number; h: number };
// A box big enough to be the frame is the frame; an element's own box (a word's, say) reads as a 1920 x 1080 frame.
export const frameOf = (b: Box): Box => (b.w >= 400 && b.h >= 400 ? b : { w: 1920, h: 1080 });
export type ParamSpec = { default: number | string | boolean; min?: number; max?: number; options?: string[]; note?: string };
export type Meta = {
  name: string;
  function?: string; evidence?: string;
  kind: "enter" | "exit" | "emphasis" | "hold" | "camera" | "transition" | "method" | "layout";
  summary: string;
  params: Record<string, ParamSpec>;
  seenIn: string;
};
export type MotionFn = (t: number, box: Box, p: Record<string, any>) => Pose;
export type Motion = { meta: Meta; at: MotionFn; frames: (p: Record<string, any>) => number };

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const prog = (t: number, a: number, d: number) => (d <= 0 ? (t >= a ? 1 : 0) : clamp((t - a) / d));

export const ease = {
  linear: (x: number) => x,
  inCubic: (x: number) => x * x * x,
  outQuad: (x: number) => 1 - (1 - x) * (1 - x),
  outCubic: (x: number) => 1 - Math.pow(1 - x, 3),
  inOutCubic: (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  outQuart: (x: number) => 1 - Math.pow(1 - x, 4),
  inQuart: (x: number) => x * x * x * x,
  outExpo: (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  inExpo: (x: number) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10)),
  inOutExpo: (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2),
  inOutSine: (x: number) => -(Math.cos(Math.PI * x) - 1) / 2,
  // a damped spring stretched to land at x = 1: overshoot sets the first peak past 1
  spring: (x: number, overshoot = 0.08) => {
    if (x >= 1) return 1;
    const z = Math.log(1 / Math.max(overshoot, 1e-4)) / Math.PI;
    const damp = z / Math.sqrt(1 + z * z);
    const w = 2 * Math.PI * 1.25;
    return 1 - Math.exp(-damp * w * x * 1.6) * Math.cos(w * Math.sqrt(1 - damp * damp) * x) * (1 - x);
  },
};
export type EaseName = keyof typeof ease;
// A cubic-bezier easing as design tools write it (x1, y1, x2, y2), so a curve measured from the source
// (tools/measure.py's moves[].ease) is used as measured. y may pass 0 or 1 for an overshoot.
export function bezier(x1: number, y1: number, x2: number, y2: number): (x: number) => number {
  const bx = (s: number) => 3 * (1 - s) * (1 - s) * s * x1 + 3 * (1 - s) * s * s * x2 + s * s * s;
  const by = (s: number) => 3 * (1 - s) * (1 - s) * s * y1 + 3 * (1 - s) * s * s * y2 + s * s * s;
  const dx = (s: number) => 3 * (1 - s) * (1 - s) * x1 + 6 * (1 - s) * s * (x2 - x1) + 3 * s * s * (1 - x2);
  return (x: number) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let s = x;
    for (let i = 0; i < 6; i++) {
      const d = dx(s);
      if (Math.abs(d) < 1e-6) break;
      s = clamp(s - (bx(s) - x) / d);
    }
    let lo = 0, hi = 1;
    for (let i = 0; i < 20 && Math.abs(bx(s) - x) > 1e-5; i++) {
      if (bx(s) < x) lo = s; else hi = s;
      s = (lo + hi) / 2;
    }
    return by(s);
  };
}

// An easing by name or as a measured [x1, y1, x2, y2]. An unknown name fails loudly: a silent fallback hands every
// typo the same default curve, and the film quietly loses the source's motion.
// A job's motion is one definition in style.motion, referenced by name, so two moves doing one job can't drift apart
export const motionOf = (style: any, m: string | number[] | undefined): { ease: string | number[]; frames?: number } | undefined => {
  if (typeof m !== "string") return m === undefined ? undefined : { ease: m };
  return style?.motion?.[m] ?? { ease: m };
};

// A part the outline names has to exist, for the same reason an easing does. A misspelt hold used to mean no motion, and the film froze with nothing to say why.
export function named<T>(table: Record<string, T>, name: string, what: string): T {
  const found = table[name];
  if (!found) throw new Error(`unknown ${what} "${name}": use one of ${Object.keys(table).sort().join(", ")}`);
  return found;
}

export const easeBy = (e: string | number[]): ((x: number) => number) => {
  if (Array.isArray(e)) return bezier(e[0], e[1], e[2], e[3]);
  const f = (ease as any)[e];
  if (!f) throw new Error(`unknown easing "${e}": use a name from lib/core.ts ease or a measured [x1, y1, x2, y2]`);
  return f;
};


// Deterministic per-index noise in [0, 1)
export const hash = (i: number, salt = 0) => {
  const s = Math.sin(i * 127.1 + salt * 311.7) * 43758.5453;
  return s - Math.floor(s);
};

export function poseCss(p: Pose): string {
  const parts: string[] = [];
  if (p.perspective) parts.push(`perspective(${p.perspective}px)`);
  if (p.x || p.y) parts.push(`translate(${p.x ?? 0}px, ${p.y ?? 0}px)`);
  if (p.rotateX) parts.push(`rotateX(${p.rotateX}deg)`);
  if (p.rotateY) parts.push(`rotateY(${p.rotateY}deg)`);
  if (p.rotate) parts.push(`rotate(${p.rotate}deg)`);
  if (p.skewX) parts.push(`skewX(${p.skewX}deg)`);
  const s = p.scale ?? 1;
  const sx = s * (p.sx ?? 1), sy = s * (p.sy ?? 1);
  if (sx !== 1 || sy !== 1) parts.push(`scale(${sx}, ${sy})`);
  return parts.join(" ") || "none";
}

export function mergePose(a: Pose, b: Pose): Pose {
  return {
    x: (a.x ?? 0) + (b.x ?? 0), y: (a.y ?? 0) + (b.y ?? 0),
    scale: (a.scale ?? 1) * (b.scale ?? 1), sx: (a.sx ?? 1) * (b.sx ?? 1), sy: (a.sy ?? 1) * (b.sy ?? 1),
    rotate: (a.rotate ?? 0) + (b.rotate ?? 0), skewX: (a.skewX ?? 0) + (b.skewX ?? 0),
    opacity: (a.opacity ?? 1) * (b.opacity ?? 1), blur: Math.max(a.blur ?? 0, b.blur ?? 0),
    rotateX: (a.rotateX ?? 0) + (b.rotateX ?? 0), rotateY: (a.rotateY ?? 0) + (b.rotateY ?? 0),
    perspective: a.perspective || b.perspective,
  };
}

// ---------- the timeline ----------

export type Per = { of: string; each: number };
// A beat's body in frames: a base, plus time for its words (at the outline's word rate unless `each` is given),
// characters typed, and items shown. Each term points at a content path.
export type DurationRule = {
  base?: number; words?: { of: string[]; each?: number }; chars?: Per[]; items?: Per[];
  min?: number; max?: number; why?: string;
};
export type BeatSpec = {
  id: string; role: string; intent: string; optional?: boolean; tone: string;
  slots: Record<string, any>; layout: { name: string; params?: Record<string, any> };
  motions?: Record<string, { name: string; params?: Record<string, any>; function?: string }>;
  methods?: Record<string, { name: string; params?: Record<string, any>; function?: string }>;
  message?: string; move?: string;
  transitionIn: { name: string; params?: Record<string, any>; function?: string };
  duration: DurationRule;
};
export type Outline = { name: string; fps: number; width: number; height: number; readingRate: number; beats: BeatSpec[] };

const get = (o: any, path: string) => path.split(".").reduce((x, k) => (x == null ? x : x[k]), o);
const words = (s: any) => (typeof s === "string" ? s.trim().split(/\s+/).filter(Boolean).length : 0);
const chars = (s: any) => (typeof s === "string" ? s.length : 0);

export function beatBody(spec: BeatSpec, content: any, readingRate: number): number {
  const r = spec.duration;
  let d = r.base ?? 0;
  if (r.words) for (const k of r.words.of) d += (r.words.each ?? readingRate) * words(get(content, k));
  for (const c of r.chars ?? []) d += c.each * chars(get(content, c.of));
  for (const it of r.items ?? []) d += it.each * Math.max(0, (get(content, it.of) ?? []).length);
  if (r.min != null) d = Math.max(r.min, d);
  if (r.max != null) d = Math.min(r.max, d);
  return Math.round(d);
}

export type TransitionLike = { meta: Meta; frames: (p: Record<string, any>) => { exit: number; enter: number; gap: number } };
export type Placed = {
  spec: BeatSpec; content: any; index: number;
  start: number; body: number; exit: number; enter: number; len: number;
  next?: Placed; prev?: Placed;
};

// Beats in order. A beat's own body comes from its duration rule; the next beat's transitionIn decides how many
// frames this beat spends leaving (exit) and how many the next spends arriving (enter, inside its body).
export function placeBeats(outline: Outline, content: any, transitions: Record<string, TransitionLike>): Placed[] {
  // A content file may refill a beat's layout values (beats.ID.layoutParams), set its own length (beats.ID.durationBase)
  // and reorder beats (order: ids, which take the places those beats hold in the outline, in the order given).
  let present = outline.beats.filter((b) => content.beats?.[b.id] != null || !b.optional).map((b) => {
    const cb = content.beats?.[b.id];
    if (!cb?.layoutParams && cb?.durationBase == null) return b;
    return { ...b, layout: { ...b.layout, params: { ...(b.layout.params ?? {}), ...(cb.layoutParams ?? {}) } }, duration: cb.durationBase != null ? { ...b.duration, base: cb.durationBase } : b.duration };
  });
  const order: string[] | undefined = content.order;
  if (order?.length) {
    if (new Set(order).size !== order.length) throw new Error(`content.order names a beat twice: ${order.join(", ")}`);
    const slots = present.map((b, i) => (order.includes(b.id) ? i : -1)).filter((i) => i >= 0);
    const moved = order.map((id) => present.find((b) => b.id === id)).filter(Boolean) as BeatSpec[];
    const next = present.slice();
    slots.forEach((slot, k) => { if (moved[k]) next[slot] = moved[k]; });
    present = next;
  }
  const out: Placed[] = [];
  let t = 0;
  present.forEach((spec, i) => {
    const c = { ...(content.beats?.[spec.id] ?? {}), product: content.product };
    // a beat holding a whole film lasts as long as that film
    const film = (spec as any).film;
    const body = film ? totalFrames(placeBeats(film, c.film, transitions)) : beatBody(spec, c, outline.readingRate);
    const nx = present[i + 1];
    const tr = nx ? named(transitions, nx.transitionIn.name, "transition") : undefined;
    const tf = tr ? tr.frames({ ...defaults(tr.meta), ...(nx!.transitionIn.params ?? {}), fps: outline.fps }) : { exit: 0, enter: 0, gap: 0 };
    const own = named(transitions, spec.transitionIn.name, "transition");
    const of = own ? own.frames({ ...defaults(own.meta), ...(spec.transitionIn.params ?? {}), fps: outline.fps }) : { exit: 0, enter: 0, gap: 0 };
    const p: Placed = { spec, content: c, index: i, start: t, body, exit: tf.exit, enter: of.enter, len: body + tf.exit };
    out.push(p);
    t += body + tf.exit + tf.gap;
  });
  out.forEach((p, i) => { p.next = out[i + 1]; p.prev = out[i - 1]; });
  return out;
}

export const totalFrames = (beats: Placed[]) => {
  const last = beats[beats.length - 1];
  return last ? last.start + last.len : 1;
};

export function defaults(meta: Meta): Record<string, any> {
  const o: Record<string, any> = {};
  for (const [k, v] of Object.entries(meta.params)) o[k] = v.default;
  return o;
}
