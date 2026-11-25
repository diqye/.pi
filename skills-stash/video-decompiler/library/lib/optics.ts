// Shared by the finish and the light and depth parts: seeded noise and keys in seconds. Imports nothing from raea.
import { easeBy, lerp } from "./core";

// The same (seed, a, b) gives the same number in [0, 1) on every frame and every machine.
export function rand(seed: number, a: number, b = 0): number {
  let h = Math.imul(seed | 0, 0x9e3779b1) ^ Math.imul(a | 0, 0x85ebca6b) ^ Math.imul(b | 0, 0xc2b2ae35);
  h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d);
  h = Math.imul(h ^ (h >>> 12), 0x297a2d39);
  return ((h ^ (h >>> 15)) >>> 0) / 4294967296;
}

// One field of keys [{ at, x, ease? }] at t seconds. A key's ease shapes the segment that leaves it.
export function keyAt(keys: any[], t: number, field: string, fallback = 0): number {
  const k = (keys ?? []).filter((x) => x[field] != null);
  if (!k.length) return fallback;
  if (t <= k[0].at) return k[0][field];
  for (let i = 0; i < k.length - 1; i++) {
    if (t < k[i + 1].at) return lerp(k[i][field], k[i + 1][field], easeBy(k[i].ease ?? "linear")((t - k[i].at) / (k[i + 1].at - k[i].at)));
  }
  return k[k.length - 1][field];
}

// "#rrggbb" as 0..1 channels.
export function rgb01(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1, 7), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}
