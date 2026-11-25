// Stand-ins for a product that turns recordings into release notes, drawn from data in the style's tokens.
// changelog: dated lines, each with a tag and a link back to its second in the recording; one line can be hovered.
// recording: a seeded waveform with a playhead and an optional quote. post-card: a post in a named app.
// wave-ball: a waveform wrapped into a ball or ring. Nothing here knows a product's name or copy.
import { clamp, hash } from "../lib/core";

const f = (style: any, role = "ui") => style.type[role]?.family ?? style.type.ui.family;
// every colour from the film's look, so these stand-ins restyle with whichever master a mix chooses
const pal = (S: any, dark?: boolean) => {
  const T: any = Object.values(S.tones)[0], c = S.color, line = c.line ?? c.cardEdge ?? T.muted ?? T.ink;
  const accent = c.found ?? T.accent ?? T.ink;
  const shared = { accent, onAccent: c.onAccent ?? T.ground, tags: { fixed: accent, new: c.judge ?? T.muted ?? T.ink, changed: c.commandPrompt ?? T.muted ?? T.ink } as Record<string, string>, neutralTag: T.muted ?? T.ink };
  return dark
    ? { ...shared, bg: c.surface ?? T.ink, fg: c.surfaceInk ?? T.ground, edge: c.surfaceEdge ?? T.muted ?? T.ground, rest: c.surfaceMuted ?? T.muted ?? T.ground, pill: c.surfaceEdge ?? T.muted ?? T.ground, hover: c.surfaceEdge ?? T.muted ?? T.ground }
    : { ...shared, bg: c.card ?? T.ground, fg: c.ink ?? T.ink, edge: line, rest: c.barTrack ?? line, pill: c.barTrack ?? line, hover: c.foundSoft ?? c.barTrack ?? line };
};

export function Changelog({ data, w, h, style }: { data: any; w: number; h: number; style: any }) {
  const u = w / 460, t = data.t ?? 0, P = pal(style, data.dark);
  const lines: any[] = data.lines ?? [];
  const hoverOn = data.hoverAt != null && t >= data.hoverAt;
  const rowH = (h - 52 * u) / Math.max(1, data.rows ?? lines.length);
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: P.bg, color: P.fg, fontFamily: f(style), borderRadius: 10 * u, border: `${1 * u}px solid ${P.edge}`, boxSizing: "border-box" }}>
      <div style={{ position: "absolute", left: 18 * u, top: 12 * u, fontSize: 15 * u, fontWeight: 600, opacity: 0.65 }}>{data.date}</div>
      {lines.map((l, i) => {
        const over = hoverOn && i === data.hoverIdx;
        const y = 44 * u + i * rowH;
        return (
          <div key={i} style={{ position: "absolute", left: 10 * u, top: y, width: w - 20 * u, height: rowH - 6 * u, borderRadius: 8 * u, background: over ? P.hover : "transparent" }}>
            <div style={{ position: "absolute", left: 8 * u, top: (rowH - 6 * u) / 2 - 10 * u, width: 64 * u, height: 20 * u, borderRadius: 5 * u, background: P.tags[(l.kind ?? "").toLowerCase()] ?? P.neutralTag, color: P.onAccent, fontSize: 12 * u, fontWeight: 700, textAlign: "center", lineHeight: `${20 * u}px` }}>{l.kind}</div>
            <div style={{ position: "absolute", left: 82 * u, top: (rowH - 6 * u) / 2 - 11 * u, width: w - 190 * u, fontSize: (data.size ?? 15) * u, fontWeight: 600, lineHeight: 1.15, whiteSpace: "normal" }}>{l.text}</div>
            {l.at ? <div style={{ position: "absolute", right: 8 * u, top: (rowH - 6 * u) / 2 - 11 * u, height: 22 * u, padding: `0 ${8 * u}px`, borderRadius: 11 * u, background: over ? P.accent : P.pill, color: over ? P.onAccent : P.fg, fontSize: 13 * u, fontWeight: 700, lineHeight: `${22 * u}px`, whiteSpace: "pre" }}>{`▶ ${l.at}`}</div> : null}
          </div>
        );
      })}
    </div>
  );
}

export function Recording({ data, w, h, style }: { data: any; w: number; h: number; style: any }) {
  const u = w / 460, t = data.t ?? 0, bars = data.bars ?? 72, P = pal(style, data.dark);
  const pStart = data.playFrom ?? 0.1, pEnd = data.playTo ?? 0.62;
  const p = data.playAt != null ? pStart + (pEnd - pStart) * clamp((t - data.playAt) / (data.playFrames ?? 110)) : (data.head ?? 0.3);
  const quoteOn = data.quote && (data.quoteAt == null || t >= data.quoteAt);
  const waveTop = 34 * u, waveH = h * (data.quote ? 0.42 : 0.62);
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: P.bg, color: P.fg, fontFamily: f(style), borderRadius: 10 * u, border: `${1 * u}px solid ${P.edge}`, boxSizing: "border-box" }}>
      <div style={{ position: "absolute", left: 14 * u, top: 9 * u, fontSize: 14 * u, fontWeight: 700, whiteSpace: "pre" }}>{data.title}</div>
      <div style={{ position: "absolute", right: 14 * u, top: 9 * u, fontSize: 13 * u, fontWeight: 600, opacity: 0.6, whiteSpace: "pre" }}>{data.clock}</div>
      {Array.from({ length: bars }, (_, i) => {
        const a = 0.25 + 0.75 * Math.abs(Math.sin(i * 0.37 + (data.seed ?? 1)) * hash(i, data.seed ?? 1));
        const x = 14 * u + (i / bars) * (w - 28 * u), bh = a * waveH;
        return <div key={i} style={{ position: "absolute", left: x, top: waveTop + (waveH - bh) / 2, width: Math.max(1.4, (w - 28 * u) / bars - 1.6 * u), height: bh, borderRadius: 1.5 * u, background: i / bars < p ? (data.accent ?? P.accent) : P.rest }} />;
      })}
      <div style={{ position: "absolute", left: 14 * u + p * (w - 28 * u) - u, top: waveTop - 4 * u, width: 2.4 * u, height: waveH + 8 * u, background: P.fg }} />
      {quoteOn ? <div style={{ position: "absolute", left: 14 * u, right: 14 * u, top: waveTop + waveH + 8 * u, fontSize: (data.quoteSize ?? 16) * u, fontWeight: 600, lineHeight: 1.2, whiteSpace: "normal" }}>{`“${data.quote}”`}</div> : null}
    </div>
  );
}

export function PostCard({ data, w, h, style }: { data: any; w: number; h: number; style: any }) {
  const u = w / 300, P = pal(style);
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, background: data.ground ?? P.bg, color: data.ink ?? P.fg, fontFamily: f(style), borderRadius: 10 * u, border: `${1 * u}px solid ${P.edge}`, boxSizing: "border-box" }}>
      <div style={{ position: "absolute", left: 12 * u, top: 12 * u, width: 22 * u, height: 22 * u, borderRadius: 6 * u, background: data.color ?? P.accent }} />
      <div style={{ position: "absolute", left: 42 * u, top: 12 * u, fontSize: 15 * u, fontWeight: 700, lineHeight: `${22 * u}px`, whiteSpace: "pre" }}>{data.app}</div>
      <div style={{ position: "absolute", left: 12 * u, top: 44 * u, width: w - 24 * u, fontSize: 13 * u, fontWeight: 600, lineHeight: 1.25, whiteSpace: "normal" }}>{data.title}</div>
      {(data.lines ?? []).map((l: string, i: number) => <div key={i} style={{ position: "absolute", left: 12 * u, top: (data.linesTop ?? 96) * u + i * 22 * u, width: w - 24 * u, fontSize: 12 * u, opacity: 0.75, whiteSpace: "nowrap", overflow: "hidden" }}>{l}</div>)}
    </div>
  );
}

export function WaveBall({ data, w, h, style }: { data: any; w: number; h: number; style: any }) {
  const n = data.bars ?? 42, cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.32, col = data.color ?? pal(style).fg, seed = data.seed ?? 1;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h }}>
      {data.fill ? <div style={{ position: "absolute", left: cx - R * 0.72, top: cy - R * 0.72, width: R * 1.44, height: R * 1.44, borderRadius: "50%", background: data.fill }} /> : null}
      {Array.from({ length: n }, (_, i) => {
        const a = (i / n) * 360, L = R * (0.25 + 0.55 * hash(i, seed));
        return <div key={i} style={{ position: "absolute", left: cx - 1.5, top: cy - R - L * 0.5, width: Math.max(2, Math.min(w, h) * (data.weight ?? 0.018)), height: L, background: col, borderRadius: 2, transformOrigin: `50% ${R + L * 0.5}px`, transform: `rotate(${a}deg)` }} />;
      })}
    </div>
  );
}
