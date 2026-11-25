// The lean starter's kit. Every default here already meets the studio numbers the skill measured, so a film that keeps
// them starts above the floor instead of below it:
//  - words sized by their job, as a share of the frame's height (JOB): an opening word 8 %, a statement 5 %, a proof
//    5.5 %, a running line 3.6 % (measured against studio films);
//  - words always on their own dark band or shadow, so their contrast does not depend on what passes behind them, and
//    always wrapped inside a 6 % margin, so no line runs off the frame (raea check's two text faults);
//  - every held shot drifts (library/motions/hold-drift: about 5 % over 3 s), so no frame is frozen;
//  - true colours: everything here is drawn on the page, unlit, with no tone mapping;
//  - a finish: grain as a page overlay, new every frame (capability-fx K), and a halo on bright words.
// Everything is a function of the time `t` in seconds. Change the palette and the shots; keep the mechanisms.
import { AbsoluteFill } from "raea";
import { FACES } from "./lib/faces";
import { clamp, ease, lerp } from "./lib/core";

export const C = {
  ground: "#0f1424", ground2: "#1b2340", far: "#2c3a66", mid: "#40518a", near: "#141a30",
  ink: "#0b0f1c", paper: "#f6efe0", accent: "#f5aa3b", accent2: "#f2653a", cool: "#7fb2f5",
};
// the faces the library ships (library/media/fonts), embedded in lib/faces.ts so they draw on any machine: a face named by
// the system's name falls back without a word (TRAPS.md: fonts), and Bahnschrift, Segoe UI and Consolas are Windows's
export const FACE = "Inter";            // the display face: Inter 700, which a weight of 600 to 900 draws
export const SANS = "Inter";
export const MONO = "'JetBrains Mono'";
/** the embedded faces' @font-face rules: once in each film, before any words */
export const Faces = () => <style>{FACES}</style>;

/** words sized by their job, as a share of the frame's height */
export const JOB = { open: 0.08, statement: 0.05, proof: 0.055, running: 0.036 } as const;
export type Job = keyof typeof JOB;
export const MARGIN = 0.06;                                   // share of the frame's width kept clear at each side

/** 0 -> 1 between a and b seconds, eased, clamped */
export const k01 = (t: number, a: number, b: number, e: keyof typeof ease = "outCubic") => (ease as any)[e](clamp((t - a) / Math.max(1e-6, b - a)));
/** a beat's own clock: in, hold, out, as 0..1 envelopes */
export const env = (t: number, from: number, to: number, fade = 0.18) => k01(t, from - 0.02, from + fade) * (1 - k01(t, to - fade * 0.6, to + 0.04, "inCubic"));

/** hold-drift: a held shot keeps creeping in, so no frame is frozen. depth > 1 drifts more (near), < 1 less (far) */
export const DRIFT_PER_S = 0.018;   // library/motions/hold-drift: 0.0003 a frame at 60 fps
export function Drift({ t, from, depth = 1, dx = 0, dy = 0, children }: { t: number; from: number; depth?: number; dx?: number; dy?: number; children: any }) {
  const s = Math.max(0, t - from);
  const scale = 1 + s * DRIFT_PER_S * depth;
  return (
    <AbsoluteFill style={{ transform: `translate(${s * dx * depth}px, ${s * dy * depth}px) scale(${scale})`, transformOrigin: "50% 55%" }}>{children}</AbsoluteFill>
  );
}

/** a line of words set for its job: on a band (running, proof) or with a halo and shadow (open, statement). It wraps
 * inside the margins, never past the frame's edge. `accent` words take the accent colour. */
export function Words({ t, from, to, text, job, w, h, accent = [], at = "low", band }: { t: number; from: number; to: number; text: string; job: Job; w: number; h: number; accent?: string[]; at?: "low" | "middle" | "high"; band?: boolean }) {
  const o = env(t, from, to);
  if (o <= 0) return null;
  const size = Math.round(JOB[job] * h);
  const banded = band ?? (job === "running" || job === "proof");
  const rise = (1 - k01(t, from, from + 0.45)) * size * 0.25;
  const top = at === "high" ? 0.12 * h : at === "middle" ? 0.5 * h - size * 0.7 : undefined;
  const bottom = at === "low" ? 0.1 * h : undefined;
  const words = text.split(" ");
  const line = (
    <div style={{ fontFamily: FACE, fontWeight: 900, fontSize: size, lineHeight: 1.16, color: C.paper, maxWidth: (1 - 2 * MARGIN) * w - (banded ? size * 1.1 : 0),
      textShadow: banded ? undefined : `0 0 ${Math.round(size * 0.35)}px rgba(255, 214, 150, 0.35), 0 ${Math.round(size * 0.08)}px ${Math.round(size * 0.3)}px rgba(4, 6, 14, 0.9)` }}>
      {words.map((word, i) => (
        <span key={i} style={{ color: accent.includes(word.replace(/[.,!?]/g, "")) ? C.accent : C.paper, marginRight: i < words.length - 1 ? "0.28em" : 0 }}>{word}</span>
      ))}
    </div>
  );
  return (
    <div style={{ position: "absolute", left: MARGIN * w, top: top === undefined ? undefined : top + rise, bottom: bottom === undefined ? undefined : bottom - rise, opacity: o }}>
      {banded ? (
        <div style={{ display: "inline-block", padding: `${size * 0.3}px ${size * 0.55}px ${size * 0.34}px`, borderRadius: size * 0.25, background: "rgba(8, 10, 22, 0.94)", boxShadow: "0 10px 30px rgba(3, 4, 12, 0.5)" }}>{line}</div>
      ) : line}
    </div>
  );
}

/** grain over everything, new every frame (one SVG turbulence; capability-fx K) */
export function Grain({ f, w, h, opacity = 0.28 }: { f: number; w: number; h: number; opacity?: number }) {
  return (
    <svg style={{ position: "absolute", left: 0, top: 0, mixBlendMode: "overlay", opacity }} width={w} height={h}>
      <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={String((f % 97) + 1)} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width={w} height={h} filter="url(#grainF)" />
    </svg>
  );
}

/** a light in the world: a soft radial glow where the light is, not a vignette round the middle */
export function Halo({ x, y, r, color = C.accent, opacity = 0.35 }: { x: number; y: number; r: number; color?: string; opacity?: number }) {
  return <div style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: r, opacity, background: `radial-gradient(closest-side, ${color}, ${color}00)` }} />;
}

/** the measure plate: the frame's margins and one line at each job's size, to hold a frame against (composition "plate") */
export function Plate({ w, h }: { w: number; h: number }) {
  const jobs = Object.keys(JOB) as Job[];
  return (
    <AbsoluteFill style={{ background: C.ground }}>
      <div style={{ position: "absolute", left: MARGIN * w, top: 0.06 * h, width: (1 - 2 * MARGIN) * w, height: 0.88 * h, outline: `2px dashed ${C.cool}` }} />
      {jobs.map((j, i) => (
        <div key={j} style={{ position: "absolute", left: MARGIN * w + 24, top: 0.1 * h + i * 0.2 * h, fontFamily: FACE, fontWeight: 900, fontSize: Math.round(JOB[j] * h), color: C.paper }}>
          {j} {Math.round(JOB[j] * h)}px
        </div>
      ))}
      {[C.ground, C.far, C.mid, C.accent, C.accent2, C.cool, C.paper].map((c, i) => (
        <div key={c} style={{ position: "absolute", right: MARGIN * w, top: 0.1 * h + i * 0.1 * h, width: 0.06 * h, height: 0.06 * h, background: c }} />
      ))}
    </AbsoluteFill>
  );
}

export { lerp };
