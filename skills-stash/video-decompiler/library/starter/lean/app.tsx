// The app kind: a light interface in a window, the words in their own column beside it, so nothing crosses them.
// A pointer presses a card, carries it into the list and lets go; the rows make room; then the view zooms in on it,
// inside the window. Cut down from an earlier film, Clearing, to its skeleton.
// Every value is a function of the time, and the times are score.json's beats (open, press, drag, zoom, close), so a
// moved line changes the score, not this file. Rename the rows, the card and the words; keep the score as the clock.
// `offset` (frames) lets `vd render --from A --to B` draw only a stretch of it.
import { AbsoluteFill, useCurrentFrame } from "raea";
import score from "./score.json" with { type: "json" };
import { Faces, Grain, SANS } from "./kit/base";

type Beat = { id: string; from: number; to: number; words?: string; job?: "open" | "statement" | "proof" | "running" };
const S = score as unknown as { fps: number; width: number; height: number; duration: number; beats: Beat[] };
export const FPS = S.fps, W = S.width, H = S.height, FRAMES = Math.round(S.duration * S.fps);
/** a beat by its id; a beat the score leaves out never comes (it starts at the end) */
const beat = (id: string): Beat => S.beats.find((b) => b.id === id) ?? { id, from: S.duration, to: S.duration };

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const smooth = (v: number) => { const u = clamp01(v); return u * u * (3 - 2 * u); };
const out = (v: number) => 1 - Math.pow(1 - clamp01(v), 3);
const span = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));
const mix = (a: number, b: number, u: number) => a + (b - a) * u;
/** a landing that carries a little past and settles */
const land = (v: number) => { const u = clamp01(v); return 1 - Math.pow(1 - u, 3) * Math.cos(u * 4.2); };

// drawn at 1920 x 1080; another size in score.json scales the whole stage
const DW = 1920, DH = 1080;
const C = { ground: "#f1ece3", ground2: "#e6dfd2", ink: "#1f1c18", soft: "#6f675c", line: "#e9e3d8", paper: "#fffdf9", accent: "#ee5a3c", accent2: "#f47b5a" };
const UI = SANS, SERIF = "Georgia, 'Times New Roman', serif";   // UI: Inter, embedded by kit/lib/faces.ts
const JOB = { open: 0.08 * DH, statement: 0.046 * DH, proof: 0.055 * DH, running: 0.034 * DH };
const COL = { x: 72, w: 440 };                                   // the words column
const WIN = { x: 560, y: 110, w: 1280, h: 860, bar: 60, r: 22 }; // the window
const VW = WIN.w, VH = WIN.h - WIN.bar;                          // its content, under the title bar
const ROW = { x: 28, top: 30, w: VW - 56, h: 84 };               // the rows, in the content's own coordinates
const ROWS = [
  { name: "Plan the week", note: "Mon 9 am" }, { name: "Hiring call", note: "Mon 11 am" }, { name: "Budget review", note: "Tue 1 pm" },
  { name: "Payroll", note: "Wed 10 am" }, { name: "Client notes", note: "Thu 9 am" }, { name: "Roadmap", note: "Thu 2 pm" }, { name: "Team review", note: "Fri 10 am" },
];
const CARD = { name: "Proposal due", note: "Friday 5 pm", detail: "Fits on Thursday, a day before it is due" };
const DROP = 3;                                                  // the card goes in above this row
const rowY = (i: number) => ROW.top + i * ROW.h;

function Row({ y, name, note, hot = 0, detail = "", show = 0 }: { y: number; name: string; note: string; hot?: number; detail?: string; show?: number }) {
  return (
    <div style={{ position: "absolute", left: ROW.x, top: y + 6, width: ROW.w, height: ROW.h - 12, borderRadius: 14, boxSizing: "border-box",
      background: hot ? `linear-gradient(170deg, ${C.accent2}, ${C.accent})` : C.paper, border: hot ? "none" : `1px solid ${C.line}` }}>
      <div style={{ position: "absolute", left: 22, top: 10, fontFamily: UI, fontWeight: 700, fontSize: 24, color: hot ? "#fff" : C.ink, whiteSpace: "nowrap" }}>{name}</div>
      <div style={{ position: "absolute", left: 22, top: 42, fontFamily: UI, fontSize: 17, color: hot ? "rgba(255,255,255,0.9)" : C.soft, whiteSpace: "nowrap" }}>{note}</div>
      {detail && show > 0 ? <div style={{ position: "absolute", left: 250, top: 25, fontFamily: UI, fontWeight: 600, fontSize: 18, color: "#fff", opacity: show, whiteSpace: "nowrap" }}>{detail}</div> : null}
    </div>
  );
}

function Cursor({ x, y, press }: { x: number; y: number; press: number }) {
  return (
    <svg style={{ position: "absolute", left: x - 6, top: y - 4, transform: `scale(${1 - press * 0.12})`, transformOrigin: "6px 4px", filter: "drop-shadow(0 4px 5px rgba(40,30,20,0.35))" }} width="34" height="44" viewBox="0 0 34 44">
      <path d="M4 3 L4 33 L12 26 L18 40 L24 37 L18 24 L29 24 Z" fill={C.ink} stroke={C.paper} strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}

/** a line in the words column: it rises into place and leaves the same way */
function Line({ t, b, last, y = 150 }: { t: number; b: Beat; last: boolean; y?: number }) {
  if (!b.words) return null;
  const size = JOB[b.job ?? "statement"], to = last ? S.duration + 1 : b.to;
  const o = out(span(t, b.from + 0.05, b.from + 0.35)) * (1 - smooth(span(t, to - 0.22, to)));
  if (o <= 0) return null;
  return <div style={{ position: "absolute", left: COL.x, top: y + (1 - out(span(t, b.from, b.from + 0.4))) * size * 0.3, width: COL.w, fontFamily: SERIF, fontWeight: 700, fontSize: size, lineHeight: 1.1, color: C.ink, opacity: o }}>{b.words}</div>;
}

function Stage({ t, f, finish }: { t: number; f: number; finish: boolean }) {
  const open = beat("open"), press = beat("press"), drag = beat("drag"), zoom = beat("zoom");
  const pressAt = press.to - 0.3, dropAt = drag.to;
  // the card: it waits under the words, is pressed, carried along an arc into the list, and let go
  const home = { x: COL.x + 220, y: 640 };
  const slot = { x: WIN.x + ROW.x + ROW.w / 2, y: WIN.y + WIN.bar + rowY(DROP) + ROW.h / 2 };
  const carry = smooth(span(t, drag.from, dropAt));
  const cx = mix(home.x, slot.x, carry), cy = mix(home.y, slot.y, carry) - Math.sin(carry * Math.PI) * 80;
  const lift = smooth(span(t, pressAt, pressAt + 0.15)) * (1 - smooth(span(t, dropAt - 0.1, dropAt)));
  const cw = mix(440, ROW.w, carry), ch = ROW.h - 12;
  const inList = smooth(span(t, dropAt - 0.02, dropAt + 0.08));  // the card hands over to the row drawn in the window
  const cardIn = out(span(t, open.from + 0.5, open.from + 0.9));
  // the rows below make room while it travels; the new row lands with a small settle
  const room = smooth(span(t, mix(drag.from, dropAt, 0.4), dropAt));
  const settle = land(span(t, dropAt, dropAt + 0.45));
  // the view zooms in on the new row, inside the window: the frame stays, the content grows about the row's left end,
  // so its name and what it says stay in view
  const z = mix(1, 1.7, smooth(span(t, zoom.from, zoom.from + 0.9)));
  const ox = ROW.x + 40, oy = rowY(DROP) + ROW.h / 2;
  // the pointer: in from below, to the card, presses, carries it, lets go, and leaves
  const p0 = { x: 330, y: 1130 }, grab = { x: home.x + 80, y: home.y + 12 };
  const toGrab = out(span(t, press.from, pressAt - 0.04)), away = smooth(span(t, dropAt + 0.1, dropAt + 0.8));
  let px = mix(p0.x, grab.x, toGrab), py = mix(p0.y, grab.y, toGrab);
  if (t >= pressAt) { px = cx + 80; py = cy + 12; }
  if (t >= dropAt) { px = mix(slot.x + 80, slot.x + 300, away); py = mix(slot.y + 12, slot.y + 200, away); }
  const pressed = smooth(span(t, pressAt - 0.05, pressAt + 0.08)) * (1 - smooth(span(t, dropAt - 0.02, dropAt + 0.1)));
  const pointer = smooth(span(t, press.from, press.from + 0.2)) * (1 - smooth(span(t, dropAt + 0.6, dropAt + 0.95)));
  return (
    <AbsoluteFill style={{ background: C.ground }}>
      <AbsoluteFill style={{ background: `radial-gradient(1200px 900px at 22% 18%, #fbf7f0 0%, ${C.ground} 55%, ${C.ground2} 100%)` }} />
      {/* the window */}
      <div style={{ position: "absolute", left: WIN.x, top: WIN.y + (1 - out(span(t, open.from, open.from + 0.5))) * 40, width: WIN.w, height: WIN.h, borderRadius: WIN.r, background: C.paper,
        boxShadow: "0 50px 90px rgba(70, 50, 26, 0.22), 0 6px 14px rgba(70, 50, 26, 0.1)", overflow: "hidden", opacity: out(span(t, open.from, open.from + 0.3)) }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: WIN.w, height: WIN.bar, borderBottom: `1px solid ${C.line}` }}>
          <div style={{ position: "absolute", left: 22, top: 17, width: 26, height: 26, borderRadius: 8, background: C.accent }} />
          <div style={{ position: "absolute", left: 60, top: 13, fontFamily: SERIF, fontWeight: 700, fontSize: 25, color: C.ink }}>Your app</div>
          <div style={{ position: "absolute", left: 200, top: 20, fontFamily: UI, fontSize: 16, color: C.soft }}>This week</div>
        </div>
        <div style={{ position: "absolute", left: 0, top: WIN.bar, width: VW, height: VH, overflow: "hidden", background: "#faf7f1" }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: VW, height: VH, transform: `scale(${z})`, transformOrigin: `${ox}px ${oy}px` }}>
            {ROWS.map((r, i) => {
              const pop = land(span(t, open.from + 0.2 + i * 0.05, open.from + 0.45 + i * 0.05));
              return <div key={r.name} style={{ opacity: clamp01(pop) }}><Row y={rowY(i) + (i >= DROP ? room * ROW.h : 0) + (1 - pop) * 16} name={r.name} note={r.note} /></div>;
            })}
            {inList > 0 ? <div style={{ opacity: inList, transform: `scale(${1 + (1 - settle) * 0.03})`, transformOrigin: `${ox}px ${oy}px` }}>
              <Row y={rowY(DROP)} name={CARD.name} note={CARD.note} hot={1} detail={CARD.detail} show={smooth(span(t, zoom.from + 0.6, zoom.from + 1.0))} />
            </div> : null}
          </div>
        </div>
      </div>
      {/* the words, in their own column */}
      {S.beats.map((b, i) => <Line key={b.id} t={t} b={b} last={i === S.beats.length - 1} />)}
      {/* the card, as a thing the pointer can carry */}
      {inList < 1 && cardIn > 0 ? (
        <div style={{ position: "absolute", left: cx - cw / 2, top: cy - ch / 2, width: cw, height: ch, borderRadius: 14, background: `linear-gradient(170deg, ${C.accent2}, ${C.accent})`,
          opacity: cardIn * (1 - inList), transform: `scale(${1 + lift * 0.06}) rotate(${Math.sin(carry * Math.PI) * -2}deg)`,
          boxShadow: `0 ${10 + lift * 22}px ${24 + lift * 36}px rgba(238, 90, 60, ${0.3 + lift * 0.1})` }}>
          <div style={{ position: "absolute", left: 22, top: 10, fontFamily: UI, fontWeight: 700, fontSize: 24, color: "#fff", whiteSpace: "nowrap" }}>{CARD.name}</div>
          <div style={{ position: "absolute", left: 22, top: 42, fontFamily: UI, fontSize: 17, color: "rgba(255,255,255,0.9)", whiteSpace: "nowrap" }}>{CARD.note}</div>
        </div>
      ) : null}
      {pointer > 0 ? <div style={{ opacity: pointer }}><Cursor x={px} y={py} press={pressed} /></div> : null}
      {finish ? <Grain f={f} w={DW} h={DH} opacity={0.1} /> : null}
    </AbsoluteFill>
  );
}

/** `finish` false leaves out the grain: `vd look` draws composition film-look so its masks can see under it */
export function Film({ offset = 0, finish = true }: { offset?: number; finish?: boolean }) {
  const f = useCurrentFrame() + offset, t = f / FPS;
  if (W === DW && H === DH) return <Stage t={t} f={f} finish={finish} />;
  return (
    <AbsoluteFill style={{ background: C.ground, overflow: "hidden" }}>
      <Faces />
      <div style={{ position: "absolute", left: 0, top: 0, width: DW, height: DH, transform: `scale(${W / DW}, ${H / DH})`, transformOrigin: "0 0" }}><Stage t={t} f={f} finish={finish} /></div>
    </AbsoluteFill>
  );
}
