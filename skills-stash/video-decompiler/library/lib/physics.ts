// Weight in closed form. Every helper is a pure function of seconds, so any frame can be asked for in any order at any
// frame rate, and nothing is integrated or carried from frame to frame. Times are seconds, frequencies are Hz.
import { hash } from "./core";

const TAU = Math.PI * 2;

export type SpringOpts = { from?: number; to?: number; freq?: number; damp?: number; v0?: number };

// A damped spring released at s = 0. freq sets how fast it moves and damp how much it rings: 0.2 is loose, 0.5 settles
// with one small overshoot, 1 and above arrive without crossing the target. Before release it holds at `from`.
export function spring(s: number, { from = 0, to = 1, freq = 2.2, damp = 0.45, v0 = 0 }: SpringOpts = {}) {
  if (s <= 0) return from;
  const w = TAU * freq, x0 = from - to;
  if (damp < 1) {
    const wd = w * Math.sqrt(1 - damp * damp);
    return to + Math.exp(-damp * w * s) * (x0 * Math.cos(wd * s) + ((v0 + damp * w * x0) / wd) * Math.sin(wd * s));
  }
  if (damp === 1) return to + Math.exp(-w * s) * (x0 + (v0 + w * x0) * s);
  const r = Math.sqrt(damp * damp - 1), a = -w * (damp - r), b = -w * (damp + r);
  const c2 = (v0 - a * x0) / (b - a), c1 = x0 - c2;
  return to + c1 * Math.exp(a * s) + c2 * Math.exp(b * s);
}

export function springSpeed(s: number, opts: SpringOpts = {}) {
  const h = 1e-3;
  return (spring(s + h, opts) - spring(s - h, opts)) / (2 * h);
}

export type Key = { at: number; v: number };

// A value that springs from key to key: each key adds one spring step, so a new key takes over while the last still moves.
export function keyed(s: number, keys: Key[], opts: Omit<SpringOpts, "from" | "to"> = {}) {
  if (!keys.length) return 0;
  let v = keys[0].v;
  for (let i = 1; i < keys.length; i++) v += (keys[i].v - keys[i - 1].v) * spring(s - keys[i].at, { ...opts, from: 0, to: 1 });
  return v;
}

// A hit at dt = 0 that rings and dies: 0 at the hit, one quick swing, then less and less. For sympathy between things.
export function ring(dt: number, { freq = 4, damp = 0.28, amp = 1 } = {}) {
  if (dt <= 0) return 0;
  const w = TAU * freq;
  return amp * Math.exp(-damp * w * dt) * Math.sin(w * Math.sqrt(1 - damp * damp) * dt);
}

// A child that lags its parent and swings past it: the parent seen through a spring's response. parent is a pure function
// of seconds. The window is fixed, so the cost is the same on every frame.
export function follow(parent: (s: number) => number, s: number, { lag = 0, freq = 3, damp = 0.4, samples = 18 } = {}) {
  const w = TAU * freq, wd = w * Math.sqrt(Math.max(1e-4, 1 - damp * damp));
  const span = 5 / (damp * w), dt = span / samples;
  let sum = 0, norm = 0;
  for (let i = 0; i < samples; i++) {
    const tau = (i + 0.5) * dt, h = Math.exp(-damp * w * tau) * Math.sin(wd * tau);
    sum += h * parent(s - lag - tau);
    norm += h;
  }
  return sum / norm;
}

// A swing about rest, in the same units as angle, dying away. Before release it holds at angle.
export function pendulum(s: number, { angle = 18, period = 1.1, decay = 1.8 } = {}) {
  if (s <= 0) return angle;
  return angle * Math.exp(-decay * s) * Math.cos((TAU * s) / period);
}

export type Bounce = { y: number; vy: number; sx: number; sy: number; contact: number; hits: number; settled: boolean };
export type BounceOpts = { height?: number; fall?: number; restitution?: number; squash?: number; stretch?: number; contact?: number; minHop?: number };

// Something dropped at s = 0 from `height` above a floor at y = 0. fall is the seconds to the first hit, restitution how much
// speed each bounce keeps. sx and sy squash it against the floor and stretch it in flight, keeping its area, so draw it
// from its bottom edge. contact is how hard it is pressing into the floor right now (0 to 1).
export function bounce(s: number, { height = 1, fall = 0.42, restitution = 0.5, squash = 0.28, stretch = 0.14, contact = 0.11, minHop = 0.015 }: BounceOpts = {}): Bounce {
  if (s <= 0) return { y: height, vy: 0, sx: 1, sy: 1, contact: 0, hits: 0, settled: false };
  const vMax = (2 * height) / fall;
  let y = 0, vy = 0, hits = 0, t = fall, last = -1, lastV = 0, settled = false;
  if (s < fall) {
    const u = s / fall;
    y = height * (1 - u * u);
    vy = -vMax * u;
  } else {
    let r = restitution, d = 2 * fall * r;
    last = fall; lastV = 1; hits = 1;
    while (true) {
      if (r * r < minHop || s < t) { settled = r * r < minHop; break; }
      if (s < t + d) {
        const u = (s - t) / d;
        y = height * r * r * 4 * u * (1 - u);
        vy = vMax * r * (1 - 2 * u);
        break;
      }
      t += d; last = t; lastV = r; hits++;
      r *= restitution; d *= restitution;
    }
    if (settled) { y = 0; vy = 0; }
  }
  const dt = s - last;
  const press = last < 0 ? 0 : lastV * Math.exp(-dt / (contact * 2.2)) * (dt < contact ? Math.sin((Math.PI * dt) / contact) : -0.3 * Math.sin((TAU * (dt - contact)) / (contact * 2.6)));
  const flight = Math.min(1, Math.abs(vy) / vMax);
  const sy = Math.max(0.2, (1 - squash * press) * (1 + stretch * flight));
  return { y, vy, sx: 1 / sy, sy, contact: Math.max(0, press), hits, settled };
}

export type Wander = { x: number; y: number; vx: number; vy: number };

// A seeded smooth path about 0, staying within about -1 to 1. speed is the main drift in cycles a second.
export function wander(s: number, seed: number, { speed = 0.15, octaves = 3 } = {}): Wander {
  let x = 0, y = 0, vx = 0, vy = 0, a = 0.6, f = speed;
  for (let o = 0; o < octaves; o++) {
    const fx = f * (1 + 0.3 * hash(seed, 11 + o * 7)), fy = f * (1 + 0.3 * hash(seed, 13 + o * 7));
    const px = hash(seed, 17 + o * 7) * TAU, py = hash(seed, 19 + o * 7) * TAU;
    x += a * Math.sin(TAU * fx * s + px); vx += a * TAU * fx * Math.cos(TAU * fx * s + px);
    y += a * Math.sin(TAU * fy * s + py); vy += a * TAU * fy * Math.cos(TAU * fy * s + py);
    a *= 0.45; f *= 1.93;
  }
  return { x, y, vx, vy };
}
