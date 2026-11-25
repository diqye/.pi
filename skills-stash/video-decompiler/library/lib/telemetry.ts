// Bidirectional physics-to-DSP telemetry: closed-form motion derivatives from physics.ts and scene.tsx
// exported as a frame-accurate physical trace for sound.py / tools/foley.py. Imports nothing from raea.
import { BounceOpts, SpringOpts, bounce, spring, springSpeed } from "./physics";
import { Cam, project } from "./scene";

export type CameraSample = {
  frame: number;
  t: number;
  vx: number;        // screen-space horizontal velocity (px/s)
  vy: number;        // screen-space vertical velocity (px/s)
  zoomRate: number;  // instantaneous log-zoom velocity d(ln scale)/dt (1/s)
  omega: number;     // combined angular + zoom speed (deg/s equivalent) driving aerodynamic whoosh
  pan: number;       // stereo pan -1 (left) to +1 (right)
};

export type ImpactEvent = {
  name: string;
  t: number;         // exact impact timestamp in seconds
  frame: number;     // fractional frame number
  mass: number;      // screen-space area share (w * h) / (W * H), 0..1
  velocity: number;  // normalized impact speed
  pan: number;       // stereo pan -1..1 from screen X center
  kind: "slam" | "bounce" | "slide" | "lock";
};

export type TelemetryTrace = {
  fps: number;
  frames: number;
  width: number;
  height: number;
  camera: CameraSample[];
  impacts: ImpactEvent[];
};

const clampPan = (x: number, W: number) => Math.max(-1, Math.min(1, (x - W / 2) / (W / 2)));

// Sample a 2D [cx, cy, zoom] or 3D Cam function at every frame to drive continuous aerodynamic foley.
export function sampleCamera(
  cameraAt: (f: number) => [number, number, number] | Cam,
  fps: number,
  frames: number,
  W = 1920,
  H = 1080,
): CameraSample[] {
  const out: CameraSample[] = [];
  const dt = 1 / fps;
  for (let f = 0; f < frames; f++) {
    const c0 = cameraAt(Math.max(0, f - 0.5));
    const c1 = cameraAt(Math.min(frames - 1, f + 0.5));
    if (Array.isArray(c0) && Array.isArray(c1)) {
      const vx = (c1[0] - c0[0]) * fps;
      const vy = (c1[1] - c0[1]) * fps;
      const z0 = Math.max(1e-4, c0[2]), z1 = Math.max(1e-4, c1[2]);
      const zoomRate = Math.log(z1 / z0) * fps;
      const omega = Math.hypot(vx / (W * 0.04), vy / (H * 0.04), zoomRate * 45);
      out.push({ frame: f, t: +(f * dt).toFixed(5), vx: +vx.toFixed(2), vy: +vy.toFixed(2), zoomRate: +zoomRate.toFixed(4), omega: +omega.toFixed(3), pan: +clampPan(c1[0], W).toFixed(3) });
    } else {
      const a = c0 as Cam, b = c1 as Cam;
      const p0 = project(a, a.tx, a.ty, a.tz), p1 = project(b, b.tx, b.ty, b.tz);
      const vx = (p1.x - p0.x) * fps, vy = (p1.y - p0.y) * fps;
      const zoomRate = Math.log(Math.max(1e-4, p1.s) / Math.max(1e-4, p0.s)) * fps;
      const dyaw = (b.yaw - a.yaw) * fps, dpitch = (b.pitch - a.pitch) * fps, droll = (b.roll - a.roll) * fps;
      const omega = Math.hypot(dyaw, dpitch, droll, zoomRate * 45, vx / (W * 0.05));
      out.push({ frame: f, t: +(f * dt).toFixed(5), vx: +vx.toFixed(2), vy: +vy.toFixed(2), zoomRate: +zoomRate.toFixed(4), omega: +omega.toFixed(3), pan: +clampPan(p1.x, W).toFixed(3) });
    }
  }
  return out;
}

// Analytical peak-velocity and first-overshoot impact of a damped spring from physics.ts.
export function springImpact(
  name: string,
  startSec: number,
  fps: number,
  opts: SpringOpts = {},
  box: { x: number; y: number; w: number; h: number } = { x: 760, y: 440, w: 400, h: 200 },
  W = 1920,
  H = 1080,
): ImpactEvent {
  const freq = opts.freq ?? 2.2, damp = opts.damp ?? 0.45;
  // First crossing of target `to = 1` occurs near pi / (2 * wd); peak speed is early in the stroke
  let bestS = 0, bestSpeed = 0;
  for (let i = 1; i <= 120; i++) {
    const s = (i / 120) * (1.2 / Math.max(0.5, freq));
    const v = Math.abs(springSpeed(s, opts));
    if (v > bestSpeed) { bestSpeed = v; bestS = s; }
    if (spring(s, { ...opts, from: 0, to: 1 }) >= 0.98) { bestS = s; break; }
  }
  const t = startSec + bestS;
  const mass = Math.max(0.005, Math.min(1, (box.w * box.h) / (W * H)));
  return {
    name,
    t: +t.toFixed(5),
    frame: +(t * fps).toFixed(2),
    mass: +mass.toFixed(4),
    velocity: +Math.min(4, bestSpeed / Math.max(1, freq * 2)).toFixed(3),
    pan: +clampPan(box.x + box.w / 2, W).toFixed(3),
    kind: damp < 0.65 ? "slam" : "slide",
  };
}

// Every floor contact of a bounce() trajectory from physics.ts.
export function bounceImpacts(
  name: string,
  startSec: number,
  fps: number,
  opts: BounceOpts = {},
  box: { x: number; y: number; w: number; h: number } = { x: 860, y: 440, w: 200, h: 200 },
  W = 1920,
  H = 1080,
): ImpactEvent[] {
  const fall = opts.fall ?? 0.42, restitution = opts.restitution ?? 0.5, minHop = opts.minHop ?? 0.015;
  const mass = Math.max(0.005, Math.min(1, (box.w * box.h) / (W * H)));
  const pan = +clampPan(box.x + box.w / 2, W).toFixed(3);
  const events: ImpactEvent[] = [];
  let s = fall, r = 1, hop = 1;
  while (r * r >= minHop && hop <= 8) {
    const b = bounce(s + 1e-4, opts);
    events.push({
      name: `${name}#${hop}`,
      t: +(startSec + s).toFixed(5),
      frame: +((startSec + s) * fps).toFixed(2),
      mass: +mass.toFixed(4),
      velocity: +Math.max(0.05, r * (1 + 0.2 * b.contact)).toFixed(3),
      pan,
      kind: "bounce",
    });
    const d = 2 * fall * (r * restitution);
    s += d;
    r *= restitution;
    hop++;
  }
  return events;
}

// Sub-millisecond kerning lock clicks as characters or words arrive into place.
export function typeLockEvents(
  name: string,
  text: string,
  startSec: number,
  stepSec: number,
  fps: number,
  box: { x: number; y: number; w: number; h: number } = { x: 480, y: 480, w: 960, h: 80 },
  W = 1920,
  H = 1080,
): ImpactEvent[] {
  const out: ImpactEvent[] = [];
  const n = Math.max(1, text.length);
  const charMass = Math.max(0.001, Math.min(0.05, ((box.w / n) * box.h) / (W * H)));
  for (let i = 0; i < text.length; i++) {
    if (text[i] === " ") continue;
    const t = startSec + i * stepSec;
    const cx = box.x + ((i + 0.5) / n) * box.w;
    out.push({
      name: `${name}[${i}]`,
      t: +t.toFixed(5),
      frame: +(t * fps).toFixed(2),
      mass: +charMass.toFixed(5),
      velocity: 0.65,
      pan: +clampPan(cx, W).toFixed(3),
      kind: "lock",
    });
  }
  return out;
}
