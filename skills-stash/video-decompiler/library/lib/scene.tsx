// A scene: a world, a light and an observer. In a flat film the picture is drawn directly. Here it is what one observer
// sees of a world: things with a place, a size and a height, lit by one light, through one lens with one focus. Depth,
// things sliding against each other, shadows, softness and scale then all follow from one cause and can't disagree.
//
// The world's axes: x right, y along the ground (away from the observer is -y), z up off the ground, in px. Head on at
// `head(W, H)` the ground is drawn 1:1, so a flat layout laid on the ground is the flat film exactly, and any beat can be
// reframed without touching its timing. A ground can be a table seen from above, a wall seen from the front, a floor
// running to a horizon: it is the plane z = 0, and the observer decides which it is by where it stands.
//
// The maths is lifted from an earlier film's stage, where it was made and watched; what is new is that a camera
// carries its frame size, things can lie, stand or face the observer, light and shadow are part of the scene, shots are
// worked out from what they are for, moves must say what they are for, and the renderer's limit on planes is checked.
// Imports nothing from raea, so bun can run it.
import { lerp } from "./core";
import { PAPER } from "../finish.gen";

// ---- the observer ---------------------------------------------------------------------------------------------------------
export type Cam = {
  tx: number; ty: number; tz: number;        // the point it looks at
  dist: number;                              // how far it is from that point
  yaw: number; pitch: number; roll: number;  // degrees: yaw swings it to the right; pitch brings it down the ground (0 = straight above, 90 = level with the ground)
  focal: number;                             // the lens, in px: with dist == focal the looked-at plane is drawn 1:1
  W: number; H: number;                      // the frame it draws into
  ox?: number; oy?: number;                  // where the looked-at point lands on screen (the middle when absent)
  focus?: number;                            // the depth that is sharp (dist when absent)
  aperture?: number;                         // how fast things go soft away from it (0 = everything sharp)
  world?: number;                            // the frame width the world was written for (W when absent). See "A world drawn at any size".
  shows?: string;                            // what its angle shows, when it is off square (see `shot`)
};
// A world drawn at any size. A world is written in px for one frame width, and the frame is only how big the observer's
// picture is: the same world gives the same picture at 640 x 360, 1920 x 1080 and 3840 x 2160, and costs the renderer the
// same share of its room. So a camera says the width its world was written for (`world`). The lens is in the frame's px
// (`focal` = 1.25 W in a shot), which makes the picture the right size, and each plane's own picture is drawn at W / world,
// so a plane's box (its cost) shrinks with the frame. Lens softness and the float are in px at the world's width and
// shrink the same way. A frame of another shape is scaled by its width alone: a shot frames its subject by `fill`, a share of
// the frame's width, so a tall frame shows more above and below the same subject, and nothing in the world changes.
export const sizeOf = (c: Cam) => c.W / (c.world ?? c.W);
// Straight above the middle of the world's frame, at the lens's own distance: the ground drawn 1:1 (at W / world). 1.25 x the
// width is the lens an earlier film was made with (2400 px at 1920 wide, about 44 degrees across).
export const head = (W: number, H: number, world = W): Cam => ({ tx: world / 2, ty: (H * world) / W / 2, tz: 0, dist: 1.25 * world, focal: 1.25 * W, yaw: 0, pitch: 0, roll: 0, W, H, world });

export type M4 = number[];                   // 4 x 4, row-major: a plane's own x, y into the world
const RAD = Math.PI / 180;
export const mat = {
  id: (): M4 => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
  mul: (a: M4, b: M4): M4 => { const o = new Array(16).fill(0); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) for (let k = 0; k < 4; k++) o[i * 4 + j] += a[i * 4 + k] * b[k * 4 + j]; return o; },
  move: (x: number, y: number, z: number): M4 => [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1],
  scale: (s: number, sy = s): M4 => [s, 0, 0, 0, 0, sy, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
  rotX: (deg: number): M4 => { const c = Math.cos(deg * RAD), s = Math.sin(deg * RAD); return [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1]; },
  rotY: (deg: number): M4 => { const c = Math.cos(deg * RAD), s = Math.sin(deg * RAD); return [c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1]; },
  rotZ: (deg: number): M4 => { const c = Math.cos(deg * RAD), s = Math.sin(deg * RAD); return [c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; },
  chain: (...ms: M4[]): M4 => ms.reduce((a, b) => mat.mul(a, b)),
};
export const atZ = (z: number): M4 => mat.move(0, 0, z);
// a plane turned about a point of its own: for a card that flips or stands up
export const about = (x: number, y: number, z: number, turn: M4): M4 => mat.chain(mat.move(x, y, z), turn, mat.move(-x, -y, 0));
// a point of a plane's own surface, in the world
export const apply = (m: M4, x: number, y: number) => ({ x: m[0] * x + m[1] * y + m[3], y: m[4] * x + m[5] * y + m[7], z: m[8] * x + m[9] * y + m[11] });

// ---- where a thing is: it lies on the ground, stands on it, or faces the observer ----------------------------------------
// `anchor` is the point of the thing's own surface (its own px) that lands on (x, y, z). `turn` turns it about the vertical.
export type Anchor = [number, number];
export const lie = (x: number, y: number, z = 0, anchor: Anchor = [0, 0], turn = 0): M4 => mat.chain(mat.move(x, y, z), mat.rotZ(turn), mat.move(-anchor[0], -anchor[1], 0));
// Stood up on the ground: its own y runs down to the ground, and its face looks towards +y, where an observer stands to
// see it. Give the anchor at its bottom edge and (x, y, z) is the spot it stands on. `lean` tips it back, in degrees.
export const stand = (x: number, y: number, z = 0, anchor: Anchor = [0, 0], turn = 0, lean = 0): M4 =>
  mat.chain(mat.move(x, y, z), mat.rotZ(turn), mat.rotX(-90 + lean), mat.move(-anchor[0], -anchor[1], 0));
// Square to the observer wherever it is, at its own place and depth: it gets nearer and further like everything else, but
// never turns away. For a label or a line of type that has to stay readable while the camera moves round it.
export function face(c: Cam, x: number, y: number, z = 0, anchor: Anchor = [0, 0], s = 1): M4 {
  const { r, d, b } = axes(c);
  const P = [x - (r[0] * anchor[0] + d[0] * anchor[1]) * s, y - (r[1] * anchor[0] + d[1] * anchor[1]) * s, z - (r[2] * anchor[0] + d[2] * anchor[1]) * s];
  return [r[0] * s, d[0] * s, b[0], P[0], r[1] * s, d[1] * s, b[1], P[1], r[2] * s, d[2] * s, b[2], P[2], 0, 0, 0, 1];
}

function axes(c: Cam) {
  const th = c.yaw * RAD, ph = c.pitch * RAD, ro = c.roll * RAD;
  const b = [Math.sin(th) * Math.cos(ph), Math.sin(ph), Math.cos(th) * Math.cos(ph)];          // from the looked-at point to the camera
  const r0 = [Math.cos(th), 0, -Math.sin(th)], d0 = [-Math.sin(th) * Math.sin(ph), Math.cos(ph), -Math.cos(th) * Math.sin(ph)];
  const cr = Math.cos(ro), sr = Math.sin(ro);
  return { b, r: r0.map((v, i) => v * cr + d0[i] * sr), d: r0.map((v, i) => -v * sr + d0[i] * cr) };
}
type Rows = { X: number[]; Y: number[]; Z: number[] };
function rows(c: Cam): Rows {
  const { b, r, d } = axes(c);
  const T = [c.tx, c.ty, c.tz], dot = (a: number[]) => a[0] * T[0] + a[1] * T[1] + a[2] * T[2];
  return { X: [...r, -dot(r)], Y: [...d, -dot(d)], Z: [-b[0], -b[1], -b[2], c.dist + dot(b)] };
}
const through = (row: number[], m: M4) => [0, 1, 2, 3].map((j) => row[0] * m[j] + row[1] * m[4 + j] + row[2] * m[8 + j] + row[3] * m[12 + j]);

// where the observer is, on the world's own axes
export function eye(c: Cam) {
  const th = c.yaw * RAD, ph = c.pitch * RAD;
  return { x: c.tx + c.dist * Math.sin(th) * Math.cos(ph), y: c.ty + c.dist * Math.sin(ph), z: c.tz + c.dist * Math.cos(th) * Math.cos(ph) };
}
// a point of the world on screen: x, y in px, its depth from the observer, and the scale things are drawn at there
export function project(c: Cam, x: number, y: number, z = 0) {
  const R = rows(c), p = [x, y, z, 1], f = (row: number[]) => row[0] * p[0] + row[1] * p[1] + row[2] * p[2] + row[3];
  const depth = f(R.Z);
  return { x: (c.ox ?? c.W / 2) + (c.focal * f(R.X)) / depth, y: (c.oy ?? c.H / 2) + (c.focal * f(R.Y)) / depth, depth, s: c.focal / depth };
}
// the sixteen numbers of the matrix3d for a plane whose own x, y map into the world through m, in CSS's order
export function planeNumbers(c: Cam, m: M4): number[] {
  const R = rows(c), X = through(R.X, m), Y = through(R.Y, m), Z = through(R.Z, m), ox = c.ox ?? c.W / 2, oy = c.oy ?? c.H / 2, n = c.dist;
  const a = X.map((v, j) => (c.focal * v + ox * Z[j]) / n), b = Y.map((v, j) => (c.focal * v + oy * Z[j]) / n), w = Z.map((v) => v / n);
  return [a[0], b[0], 0, w[0], a[1], b[1], 0, w[1], a[2], b[2], 1, w[2], a[3], b[3], 0, w[3]];
}
// the css for that plane
export function planeCss(c: Cam, m: M4) {
  const t = (v: number) => (Math.abs(v) < 1e-9 ? "0" : v === 1 ? "1" : v.toFixed(9));
  return `matrix3d(${planeNumbers(c, m).map(t).join(",")})`;
}
// how soft a thing at this depth is, in screen px
// (in px at the world's width: `planes` draws it at the frame's)
export const softness = (c: Cam, depth: number) => (c.aperture ?? 0) * Math.abs(depth - (c.focus ?? c.dist)) / depth;

// one camera part-way to another: distances and lenses in ratio, the rest straight
export function mixCam(a: Cam, b: Cam, p: number): Cam {
  const g = (x: number, y: number) => Math.exp(lerp(Math.log(x), Math.log(y), p));
  return {
    tx: lerp(a.tx, b.tx, p), ty: lerp(a.ty, b.ty, p), tz: lerp(a.tz, b.tz, p), dist: g(a.dist, b.dist), focal: g(a.focal, b.focal),
    yaw: lerp(a.yaw, b.yaw, p), pitch: lerp(a.pitch, b.pitch, p), roll: lerp(a.roll, b.roll, p), W: b.W, H: b.H, world: b.world, shows: b.shows,
    ox: lerp(a.ox ?? a.W / 2, b.ox ?? b.W / 2, p), oy: lerp(a.oy ?? a.H / 2, b.oy ?? b.H / 2, p),
    focus: g(a.focus ?? a.dist, b.focus ?? b.dist), aperture: lerp(a.aperture ?? 0, b.aperture ?? 0, p),
  };
}
// how a camera travels: it eases away and eases in, and never snaps through the middle
export const glide = (p: number) => 0.5 - 0.5 * Math.cos(Math.PI * Math.min(1, Math.max(0, p)));
// The camera is never quite still: a slow float, scaled to how far off it is, so near and far keep sliding a little
// against each other in a held shot. Its terms have one name, so a shot that must be flat can take it back out exactly.
export const floatOf = (f: number) => ({ yaw: 0.2 * Math.sin(f / 37 + 0.4), pitch: 0.14 * Math.sin(f / 47 + 1.9), sx: Math.sin(f / 61), cy: Math.cos(f / 53) });
export function floatCam(c: Cam, f: number, amount = 1): Cam {
  const k = (c.dist / (1.25 * (c.world ?? c.W))) * amount, w = floatOf(f);   // in px at the world's width, like everything in it
  return { ...c, yaw: c.yaw + w.yaw * amount, pitch: c.pitch + w.pitch * amount, tx: c.tx + 2.5 * k * w.sx, ty: c.ty + 1.5 * k * w.cy };
}

// ---- named shots: a camera worked out from what the shot is for -----------------------------------------------------------
// The plan gives every beat one of these words.
export type Scale = "macro" | "close" | "medium" | "wide" | "all-type";
// What a shot is of: a box in the world. Lying (the default) it is x..x+w by y..y+h on the plane at height z. Standing
// (`stands`) it is x..x+w across, at y, from height z up to z+h, its face towards +y.
export type Subject = { x: number; y: number; w: number; h: number; z?: number; stands?: boolean };
export type ShotOpts = {
  shows?: string;     // what the angle shows that a square-on view can't: "the stamp's height over the page", "the rows behind it".
                      // Without it the shot is square on. An angle with no reason is a skewed page.
  fill?: number;      // how much of the frame's width the subject's width takes (through its middle); for macro, how far it overfills the frame
  side?: number;      // -1 from the left, 1 from the right, 0 square on. A track keeps to one side unless a move says it crosses
  turn?: number;      // degrees round to that side (the scale's own when absent)
  tilt?: number;      // degrees off square: how far the observer looks along the subject rather than straight at it
  sharp?: number;     // the depth either side of the subject that stays within 1.5 px of sharp, in px. 0 = everything sharp
  lens?: number;      // focal length as a share of the frame's width (1.25 when absent)
  world?: number;     // the frame width the world was written for (W when absent): see "A world drawn at any size"
  ox?: number; oy?: number;   // where the subject's middle lands on screen
};
// An angle needs something to show, as a move needs a job. One flat thing seen from an angle is a skewed page, and readers
// say the tilt has no job; the person an earlier film was made for said the same of its third cut ("needless changes in
// perspectives at points that don't actually do anything"). An angle earns its place by showing a relation in depth that a
// square-on view can't: what is above what (a height, a stack's thickness), how many there are (rows running away), what is
// near and what is far. So a shot is square on unless it says what its angle shows (`shows`), and then it takes its scale's
// angle below, or the `turn` and `tilt` given. Square on is a real shot: it is how type is read and the inside of a thing seen.
//
// Each scale's defaults, and why. Checked against the cameras of an earlier film, which a person watched and kept, as one case that
// is known to work (act1 CORNER turn 21 tilt 25 with a shallow lens; act1 OBJECT 17 and 12; act3
// grid 9 and 15; act4 WIDE 6 and 34, act1 WIDE 8 and 56); the numbers here are reasons, not copies.
export const SHOT: Record<Scale, { fill: number; turn: number; tilt: number; sharp: number; lens: number; why: string }> = {
  // inside the thing: square on, and it overfills the frame a little so no edge of it shows. Nothing near or far to part.
  macro: { fill: 1.08, turn: 0, tilt: 0, sharp: 0, lens: 1.25, why: "inside the thing, full screen" },
  // a detail: steep enough that the near edge is drawn visibly bigger than the far one (about 8% at this fill), and shallow
  // focus, sharp only across the subject's own size, so the eye goes where the lens does.
  close: { fill: 0.8, turn: 14, tilt: 24, sharp: 1, lens: 1.25, why: "close on a detail, shallow focus" },
  // one object from an angle: at 28 degrees its far edge is about 10% shorter than its near edge, so it reads as a thing in
  // space, and type on it is foreshortened by cos 28 = 0.88, which stays readable. Mild focus: three of its sizes either side.
  medium: { fill: 0.55, turn: 16, tilt: 28, sharp: 3, lens: 1.25, why: "one object, seen from an angle" },
  // many things at once: higher over the ground, so rows run away into the distance and read as many; a small turn keeps the
  // rows near parallel to the frame; a wider lens shows more of the run; everything sharp, the distance does the fading.
  wide: { fill: 0.42, turn: 8, tilt: 40, sharp: 0, lens: 1.0, why: "many things at once" },
  // type as the picture: type reads best square on, which is what it is with no reason given; asked to show something, a few
  // degrees keep it in the world, so its shadow and ground still show.
  "all-type": { fill: 0.72, turn: 0, tilt: 6, sharp: 0, lens: 1.25, why: "type as the picture" },
};

// the subject's middle, and the two ends of the line through it that `fill` measures
function subjectLine(t: Subject) {
  const z = t.z ?? 0;
  if (t.stands) return { mid: [t.x + t.w / 2, t.y, z + t.h / 2], a: [t.x, t.y, z + t.h / 2], b: [t.x + t.w, t.y, z + t.h / 2], up: [t.x + t.w / 2, t.y, z + t.h], dn: [t.x + t.w / 2, t.y, z] };
  return { mid: [t.x + t.w / 2, t.y + t.h / 2, z], a: [t.x, t.y + t.h / 2, z], b: [t.x + t.w, t.y + t.h / 2, z], up: [t.x + t.w / 2, t.y, z], dn: [t.x + t.w / 2, t.y + t.h, z] };
}
// how wide and tall the subject is drawn through its middle, in px, by this camera
export function drawnSize(c: Cam, t: Subject) {
  const L = subjectLine(t), P = (p: number[]) => project(c, p[0], p[1], p[2]);
  const a = P(L.a), b = P(L.b), u = P(L.up), d = P(L.dn);
  return { w: Math.hypot(b.x - a.x, b.y - a.y), h: Math.hypot(d.x - u.x, d.y - u.y) };
}

export function shot(scale: Scale, subject: Subject, W: number, H: number, o: ShotOpts = {}): Cam {
  const S = SHOT[scale];
  if (!S) throw new Error(`shot: "${scale}" isn't a scale. Use one of ${Object.keys(SHOT).join(", ")}.`);
  // a subject with no width or height gave a camera of NaNs, and drew nothing with no message
  if (![subject.x, subject.y, subject.w, subject.h, subject.z ?? 0].every(Number.isFinite) || !(subject.w > 0) || !(subject.h > 0))
    throw new Error(`shot: the subject of a ${scale} shot has no size (x ${subject.x}, y ${subject.y}, w ${subject.w}, h ${subject.h}). Give it a box with a width and a height.`);
  const angled = typeof o.shows === "string" && o.shows.trim().split(/\s+/).length >= 2;
  if (!angled && (o.tilt || o.turn)) throw new Error(`shot: a ${scale} shot turned ${o.turn ?? 0} and tilted ${o.tilt ?? 0} degrees doesn't say what its angle shows. Give it "shows": a few words for the relation in depth the angle shows (the stamp's height over the page, the rows behind it), or leave it square on.`);
  const side = o.side ?? -1, fill = o.fill ?? S.fill, tilt = angled ? o.tilt ?? S.tilt : 0, turn = (angled ? o.turn ?? S.turn : 0) * Math.sign(side);
  const L = subjectLine(subject), focal = (o.lens ?? S.lens) * W;
  // a lying subject is looked at from above, tipped by `tilt`; a standing one from in front, raised by `tilt`
  const pitch = subject.stands ? 90 - tilt : tilt;
  const c: Cam = { tx: L.mid[0], ty: L.mid[1], tz: L.mid[2], dist: focal, focal, yaw: turn, pitch: Math.min(pitch, 89), roll: 0, W, H, ox: o.ox, oy: o.oy, world: o.world, shows: angled ? o.shows : undefined };
  // distance by measurement: the subject drawn at `fill` of the frame's width, or for macro covering the whole frame
  for (let i = 0; i < 6; i++) {
    const got = drawnSize(c, subject);
    const k = scale === "macro" ? Math.min(got.w / (fill * W), got.h / (fill * H)) : got.w / (fill * W);
    c.dist *= k;
  }
  c.focus = c.dist;
  const sharpBy = o.sharp ?? S.sharp;
  // the depth that stays within 1.5 px of sharp is `sharp` times the subject's size: aperture * depth / dist = 1.5
  c.aperture = sharpBy > 0 ? (1.5 * c.dist) / (sharpBy * Math.max(subject.w, subject.h)) : 0;
  // The distance was worked out from the subject's width alone. A long thing seen from an angle (a strip 100 wide and
  // 10,000 long) then put the camera over its middle with its near end behind the lens, and the picture was drawn through
  // zero depth. Every corner of the subject has to be in front of the observer, with room to spare.
  const zs = subject.z ?? 0, ends = subject.stands
    ? [[subject.x, subject.y, zs + subject.h], [subject.x + subject.w, subject.y, zs + subject.h], [subject.x + subject.w, subject.y, zs], [subject.x, subject.y, zs]]
    : [[subject.x, subject.y, zs], [subject.x + subject.w, subject.y, zs], [subject.x + subject.w, subject.y + subject.h, zs], [subject.x, subject.y + subject.h, zs]];
  const nearest = Math.min(...ends.map((e) => project(c, e[0], e[1], e[2]).depth));
  if (!Number.isFinite(c.dist) || !(c.dist > 0) || !(nearest > 0.05 * c.dist))
    throw new Error(`shot: a ${scale} shot from this angle can't hold a subject ${subject.w} wide and ${subject.h} ${subject.stands ? "tall" : "long"}: part of it would be at or behind the observer. `
      + "Frame a part of it (a box), look at it square on, or use a wider scale.");
  return c;
}

// ---- the track: shots held, and moves that say what they are for ------------------------------------------------------------
// A move with no reason is the fault the fourth cut of an earlier film took back out: its third cut moved on every beat, and the
// person it was made for asked for less. So a move can't be written without its job, and between moves the shot holds.
export type Move = { at: number; to: Cam; job: string; frames?: number; cross?: boolean; cut?: boolean };
const sayJob = "Say in a few words what it is for (follows the stamp down, arrives at the detail, shows these are many). If it has no job, hold the shot.";
export function move(at: number, to: Cam, job: string, frames?: number, o: { cross?: boolean } = {}): Move {
  if (typeof job !== "string" || job.trim().split(/\s+/).length < 2) throw new Error(`a camera move at frame ${at} has no job. ${sayJob}`);
  return { at, to, job, frames, cross: o.cross };
}
// A cut: the camera is somewhere else at once. It needs a reason too, and reads best hidden under a flash or a hard change.
export function cut(at: number, to: Cam, why: string): Move {
  if (typeof why !== "string" || why.trim().split(/\s+/).length < 2) throw new Error(`a cut at frame ${at} has no reason. ${sayJob}`);
  return { at, to, job: why, frames: 0, cut: true };
}
const sideOf = (c: Cam) => (Math.abs(c.yaw) < 2 ? 0 : Math.sign(c.yaw));
// The camera at every frame: it starts on `start`, and each move travels on `glide` over its frames (a second when not
// given, never under half a second, which reads as a jolt). `float` adds the slow float; 0 takes it out.
export function track(fps: number, start: Cam, moves: Move[], o: { float?: number } = {}) {
  let last = -Infinity, from = start;
  const legs = moves.map((m) => {
    const frames = m.cut ? 0 : m.frames ?? Math.round(fps);
    if (!m.cut && frames < fps / 2) throw new Error(`the move at frame ${m.at} (${m.job}) takes ${frames} frames, under half a second: that reads as a jolt. Give it about a second.`);
    if (m.at < last) throw new Error(`the move at frame ${m.at} (${m.job}) starts before the one before it has arrived (frame ${last}). One move at a time.`);
    const a = sideOf(from), b = sideOf(m.to);
    // a cut can go to the other side: it is a cut, it has its reason, and `cut()` takes no `cross`. Only a move has to say so
    if (!m.cut && a && b && a !== b && !m.cross) throw new Error(`the move at frame ${m.at} (${m.job}) changes sides of its subject. A shot stays on one side; changing sides is a move of its own: pass { cross: true } if it is meant.`);
    const leg = { ...m, frames, from };
    last = m.at + frames; from = m.to;
    return leg;
  });
  const float = o.float ?? 1;
  return (f: number): Cam => {
    let c = start;
    for (const l of legs) {
      if (f < l.at) break;
      c = l.frames === 0 || f >= l.at + l.frames ? l.to : mixCam(l.from, l.to, glide((f - l.at) / l.frames));
    }
    return float ? floatCam(c, f, float) : c;
  };
}
// The moves of a track as a list a reader can check: when, what each is for, and what the angle it arrives at shows (or that it
// is square on). Pass the first shot too, and it heads the list.
export const jobs = (moves: Move[], start?: Cam) => [
  ...(start ? [`start: ${start.shows ? `angled, shows ${start.shows}` : "square on"}`] : []),
  ...moves.map((m) => `${m.at}${m.cut ? " cut" : ""}: ${m.job}; ${m.to.shows ? `angled, shows ${m.to.shows}` : "square on"}`),
];

// What a shot's frame cuts through. A thing whose edge the frame crosses, when it is not what the shot is of, reads as a crop
// nobody chose ("wide frame crop of card looks unchosen", a director of the first film made with this). Returns the keys of
// things partly in and partly out of the frame, leaving out the ground and other backdrops (`backdrop`), and whatever holds
// the subject's middle: the subject itself (a macro shot overfills it on purpose) and what it lies on (the page under a detail).
export function cutBy(c: Cam, things: Thing[], subject?: Subject): string[] {
  const mid = subject ? project(c, ...(subjectLine(subject).mid as [number, number, number])) : null;
  const out: string[] = [];
  for (const t of things) {
    if (t.backdrop || !t.box) continue;
    const m = t.m ?? atZ(t.z ?? 0), b = t.box;
    const P = [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]].map(([x, y]) => { const w = apply(m, x, y); return project(c, w.x, w.y, w.z); });
    if (P.some((p) => p.depth <= 60)) continue;
    const inside = P.filter((p) => p.x >= 0 && p.x <= c.W && p.y >= 0 && p.y <= c.H).length;
    const xs = P.map((p) => p.x), ys = P.map((p) => p.y);
    const seen = Math.max(...xs) > 0 && Math.min(...xs) < c.W && Math.max(...ys) > 0 && Math.min(...ys) < c.H;
    if (!seen || inside === 4) continue;
    // a thing that holds the subject's middle (what the detail lies on) is meant to run out of a close frame
    if (mid && inQuad(P, mid.x, mid.y)) continue;
    out.push(t.key);
  }
  return out;
}
function inQuad(P: { x: number; y: number }[], x: number, y: number) {
  let s = 0;
  for (let i = 0; i < 4; i++) { const a = P[i], b = P[(i + 1) % 4]; const cr = (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x); if (cr !== 0) { if (s && Math.sign(cr) !== s) return false; s = Math.sign(cr); } }
  return true;
}

// ---- light ---------------------------------------------------------------------------------------------------------------
// One light for the whole scene, and it is somewhere: over the point (x, y) of the ground, z px up. Everything it lights is
// brighter near it and dimmer far from it, and every shadow is thrown from that place, so a shadow falls away from where
// the light is and can't disagree with the light on the things. A reader of the first film staged in a scene called it "flat
// evenly lit": its light had a direction and no place, and only the stage's own ground had a falloff, painted on.
// How much light reaches a point goes with its straight-line distance D from the light, as a bare bulb's does: what reaches
// the ground right under it is all of it, and `reach` is how far across the ground from there half of it is gone
// (f = reach^2 / (reach^2 + D^2 - z^2)). `dark` is how much of the picture's brightness the light gives: far from it a
// thing keeps 1 - dark of its own brightness. The same law lights the ground, every thing, and a wall standing up.
// Colours are names a style gives (the defaults are plain css words, so no source's colour is held here).
// `tint` is the light's colour on everything it lights (laid over the picture by multiplying, at `tintA`); `lift` is how bright it is
// (laid over by screening, at `liftA`). Both are the light, not a layer pasted on the lens: they change only when the light does.
export type Light = {
  x?: number; y?: number; z?: number;   // where it is (world px): over (x, y) of the ground, z up. Absent: see `placeLight`
  reach?: number;                       // how far across the ground half its light is gone (z when absent)
  dark?: number;                        // 0..1: how much of the brightness far things lose
  soft: number; shade: string; glow: string; strength: number; tint?: string; tintA?: number; lift?: string; liftA?: number;
};
export const LIGHT: Light = { soft: 0.09, shade: "black", glow: "white", strength: 0.55 };
export type PlacedLight = Light & { x: number; y: number; z: number; reach: number; dark: number };
// Where the light is when nobody says, and why.
// - Height: the world's frame width (1920 px for a world written at 1920). From there a thing lifted a few px throws a short
//   shadow, as the shots expect, and things a frame apart throw shadows that visibly spread away from the light.
// - Place: over a point up and to the left of what the film opens on (`over`: the first shot's subject), by 0.22 and 0.30 of
//   its height. The opening subject is then in nearly all of the light (88% of it) and its shadow falls to the near right,
//   22 px across and 30 down for every 100 px of height, as every shadow in this library fell before the light had a place
//   (from the upper left and a little from the observer's side, as in an earlier film). Rows running away up the ground and
//   anything far to the right get plainly dimmer.
// - Reach: its height, which is how a bare bulb lights a table. A frame's width from under it a thing is lit by half the light,
//   two frames off by a fifth.
// - Dark: 0.55. Far off a white card keeps 45% of its brightness: on a dark ground it is still read at a glance, and it is
//   plainly dimmer than the same card under the light. Much darker and a wide shot's far half goes black; much lighter and a
//   reader calls the world evenly lit again.
export function placeLight(L: Light, over: { x: number; y: number }, world = 1920): PlacedLight {
  const z = L.z ?? world;
  return { ...L, z, reach: L.reach ?? z, dark: L.dark ?? 0.55, x: L.x ?? over.x - 0.22 * z, y: L.y ?? over.y - 0.3 * z };
}
const placed = (L: Light, c?: Cam): PlacedLight => (L.x != null && L.y != null && L.z != null && L.reach != null && L.dark != null ? (L as PlacedLight)
  : placeLight(L, { x: (c?.world ?? c?.W ?? 1920) / 2, y: ((c?.H ?? 1080) * (c?.world ?? c?.W ?? 1920)) / (c?.W ?? 1920) / 2 }, c?.world ?? c?.W ?? 1920));
// How much of the light reaches a point at squared distance d2 from it: 1 on the ground right under it, half at `reach`.
export function reaching(L: PlacedLight, d2: number) {
  const R2 = L.reach * L.reach, den = R2 + d2 - L.z * L.z;
  return den <= R2 ? 1 : R2 / den;
}
// How bright the light leaves a point of the world: 1 under the light, 1 - dark far away
export const brightness = (L: Light, x: number, y: number, z = 0) => { const P = placed(L); return 1 - P.dark * (1 - reaching(P, (x - P.x) ** 2 + (y - P.y) ** 2 + (z - P.z) ** 2)); };
// Where the light throws a point that is h px above a surface at height u: along the line from the light through the point,
// so away from where the light is, and longer the nearer the point is to the light's own height.
export function shadowAt(x: number, y: number, h: number, L: Light = LIGHT, u = 0) {
  const P = placed(L), k = h / Math.max(1, P.z - u - h);
  return { x: x + (x - P.x) * k, y: y + (y - P.y) * k };
}

// A light that changes over the film. "The light changed and it was day" is a moment viewers retell, and it is one change in one
// light: the shadows swing and soften or harden, the world takes the light's colour and brightness, all together, because they
// all come from it. Each key is where the light starts to change (`at`, a frame), what it becomes, and how long it takes
// (`frames`, a second when not given); it travels on `glide`. Colours given as #rrggbb mix; any other colour changes halfway.
export type LightKey = { at: number; light: Partial<Light>; frames?: number };
const hex = (v: string) => /^#[0-9a-f]{6}$/i.test(v);
const mixHex = (a: string, b: string, p: number) => "#" + [1, 3, 5].map((i) => Math.round(lerp(parseInt(a.slice(i, i + 2), 16), parseInt(b.slice(i, i + 2), 16), p)).toString(16).padStart(2, "0")).join("");
export function mixLight(a: Light, b: Light, p: number): Light {
  const o: any = { ...a };
  for (const k of Object.keys(b) as (keyof Light)[]) {
    const x: any = (a as any)[k], y: any = (b as any)[k];
    if (typeof y === "number") o[k] = lerp(typeof x === "number" ? x : k === "tintA" || k === "liftA" ? 0 : y, y, p);
    else if (typeof y === "string") o[k] = typeof x === "string" && hex(x) && hex(y) ? mixHex(x, y, p) : p < 0.5 && x != null ? x : y;
  }
  return o;
}
export function lightAt(base: Light, keys: LightKey[], f: number, fps = 60): Light {
  let L = base;
  for (const k of [...keys].sort((a, b) => a.at - b.at)) {
    if (f < k.at) break;
    const to = { ...L, ...k.light } as Light;
    L = mixLight(L, to, glide((f - k.at) / (k.frames ?? fps)));
  }
  return L;
}

// ---- things and planes ---------------------------------------------------------------------------------------------------
export type Thing = {
  key: string;
  node: any;                  // what it draws, in its own px (or, with `crops`, a function: see below)
  m?: M4;                     // where it is (lie, stand, face, or a matrix of your own)
  z?: number;                 // or lying flat at this height
  box?: [number, number, number, number];   // x, y, w, h of its own surface: all it draws on. Its picture is then only that big.
                              // Without it the plane is the size of the frame, and raea has room for about nine of those.
                              // What a boxed plane holds is placed in px from its own corner: inside a box its container has
                              // no size, so a width in per cent, or a place given by right, bottom or inset, comes out wrong.
  ref?: [number, number];     // the point of it that decides its depth (the middle of its box when absent)
  opacity?: number;
  sharp?: boolean;            // never softened by the lens
  blur?: number;              // extra softness, in screen px
  order?: number;             // breaks ties between things drawn at one height: the higher number is drawn later
  sortZ?: number;             // draw it as if it were at this height
  stands?: boolean;           // drawn with the height it stands on, farthest first, after what lies lower (set by `standing`)
  shadow?: number;            // 0..1: it throws a soft shadow on the surface under it, apart from it by its height
  under?: number;             // the height of that surface (when absent, the highest thing lying flat under it, or the ground)
  glow?: number;              // 0..1: it lights the surface under it
  backdrop?: boolean;         // the ground, rows running away: meant to run out of the frame (see `cutBy`)
  material?: Material;        // what it is made of (see MATERIALS). With one, its picture fills its box, rounded by `radius`
  radius?: number;            // the corners of what it is made of, in its own px
  lit?: number;               // how much the light's falloff darkens it, 0..1 (1 when absent; what its material says)
  crops?: boolean;            // its `node` is a function of the part of its box a plane shows ([x, y, w, h], own px) that lays out only
                              // that part, from its corner: it then costs only that, and can be cut into bands and enlarged freely
};

// ---- what a thing is made of ------------------------------------------------------------------------------------------------
// A card is not a fill with a knife edge. Paper lying on a table has an edge that catches the light and one that doesn't, a tight
// dark line where it meets the table, a surface that isn't one value, and it takes the light of the place it lies in. A reader of
// the first film staged in a scene: "flat evenly lit tilted plane with hard-edged card". So a thing says what it is made of in one
// word, and everything below comes from the light's place, the thing's height and the observer's: nobody draws a highlight.
//   grain   the kit's paper tooth (the tile in finish.gen.ts), multiplied at this strength
//   rim     its edge: [width in px, how much the edge facing the light brightens, how much the edge away from it darkens]
//   sheen   the light seen in it, where the light would mirror into the observer's eye: [strength, spread], the spread as a share
//           of the light's and the eye's distances, so a matte thing's sheen is broad and faint and a glass one's tight
//   shadow  the shadow it throws when the thing doesn't say (it rests on the surface under it: see `contact` in lightPlanes)
//   lit     how much the light's falloff darkens it: a screen gives off its own light, glass shows what is behind it
// A thing with a material fills its box (rounded by `radius`), so all of this is drawn inside its own shape, on its own plane, at
// no extra cost of plane area. Each costs a few layers of drawing on that plane: the grain a tiled picture, the sheen a gradient,
// the rim a border.
export type Material = "card" | "paper" | "print" | "screen" | "glass" | "none";
export const MATERIALS: Record<Material, { grain: number; rim: [number, number, number]; sheen: [number, number]; shadow: number; lit: number; glow?: number; why: string }> = {
  // card stock: a visible tooth, an edge thick enough to catch the light, a faint broad sheen. The default for a block.
  card: { grain: 0.55, rim: [2.5, 0.55, 0.35], sheen: [0.06, 0.9], shadow: 0.8, lit: 1, why: "a card lying there" },
  // thin paper: more tooth, a hairline edge, almost no sheen
  paper: { grain: 0.9, rim: [1.2, 0.35, 0.3], sheen: [0.03, 1.2], shadow: 0.7, lit: 1, why: "a sheet of paper" },
  // a photographic print: little tooth, a semi-gloss sheen that slides as the observer moves. The default for an image.
  print: { grain: 0.15, rim: [1.5, 0.5, 0.35], sheen: [0.12, 0.35], shadow: 0.8, lit: 1, why: "a print of a photograph" },
  // a screen gives off its own light: the room's light doesn't dim it, its glass shows a tight sheen, and it lights what is under it
  screen: { grain: 0, rim: [3, 0.25, 0.6], sheen: [0.14, 0.15], shadow: 0.8, lit: 0, glow: 0.35, why: "a screen giving off its own light" },
  // glass shows what is behind it, so the light's falloff is left to what is behind; a bright edge and a tight sheen say it is there
  glass: { grain: 0, rim: [1.5, 0.7, 0.2], sheen: [0.22, 0.12], shadow: 0.25, lit: 0, why: "a pane of glass" },
  // nothing said: drawn as it is, and still lit by the light like everything else
  none: { grain: 0, rim: [0, 0, 0], sheen: [0, 1], shadow: 0, lit: 1, why: "drawn as it is" },
};
const materialOf = (t: Thing) => {
  if (!t.material) return null;
  const M = MATERIALS[t.material];
  if (!M) throw new Error(`scene: "${t.key}" is made of "${t.material}", which is none of ${Object.keys(MATERIALS).join(", ")}`);
  return M;
};
// a thing stood up: its matrix from `stand`, and drawn in the right order
export const standing = (t: Thing): Thing => ({ ...t, stands: true });

// Every plane drawn this frame is a picture raea keeps a place for, the size of its box, on a sheet with room for 28 frame-sized
// pictures that keeps each about three frames. Past about nine frame-sized planes the nearest go missing, with no message
// (measured on rc4). So the scene adds up the planes' areas, each box as a share of the frame, and refuses past this.
export const AREA_LIMIT = 9;
export function planeArea(things: Thing[], W: number, H: number) {
  const each = things.map((t) => ({ key: t.key, area: t.box ? (t.box[2] * t.box[3]) / (W * H) : 1 })).sort((a, b) => b.area - a.area);
  return { total: each.reduce((s, e) => s + e.area, 0), each };
}
export function checkArea(things: Thing[], W: number, H: number, limit = AREA_LIMIT) {
  const { total, each } = planeArea(things, W, H);
  if (total > limit) throw new Error(`scene: this frame's planes add up to ${total.toFixed(1)} frames of picture, over the limit of ${limit}. ` +
    `raea draws each plane with perspective to a picture the size of its box and has room for about ${limit} the size of the frame; past that the nearest ` +
    `planes go missing from frames with no message. Give each plane a box the size of what it draws, or put things at one height on one plane. ` +
    `Biggest: ${each.slice(0, 5).map((e) => `${e.key} ${e.area.toFixed(2)}`).join(", ")}.`);
  return total;
}

// The surface a thing's shadow falls on: the highest thing lying flat under its middle and lower than it, or the ground.
// (Given by hand, a card over a page threw its shadow onto the ground under the page, where nobody could see it.)
const cornersOf = (t: Thing, W: number, H: number) => { const m = t.m ?? atZ(t.z ?? 0), b = t.box ?? [0, 0, W, H]; return [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]].map(([x, y]) => apply(m, x, y)); };
export function surfaceUnder(t: Thing, things: Thing[], W: number, H: number): number {
  const P = cornersOf(t, W, H), x = P.reduce((s, p) => s + p.x, 0) / 4, y = P.reduce((s, p) => s + p.y, 0) / 4, low = Math.min(...P.map((p) => p.z));
  let u = 0;
  for (const s of things) {
    if (s === t || s.stands || s.backdrop) continue;
    const Q = cornersOf(s, W, H), z = Q[0].z;
    if (Q.some((q) => Math.abs(q.z - z) > 0.5) || z >= low - 0.5 || z <= u) continue;     // only flat things, below it, higher than found
    if (inQuad(Q, x, y)) u = z;
  }
  return u;
}

// A box's outline with its corners rounded by r, as points (six to a corner)
function rounded(b: [number, number, number, number], r: number): [number, number][] {
  const k = Math.max(0, Math.min(r, b[2] / 2, b[3] / 2));
  if (k < 1) return [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]];
  const out: [number, number][] = [], cs: [number, number, number][] = [[b[0] + b[2] - k, b[1] + k, -90], [b[0] + b[2] - k, b[1] + b[3] - k, 0], [b[0] + k, b[1] + b[3] - k, 90], [b[0] + k, b[1] + k, 180]];
  for (const [cx, cy, a0] of cs) for (let i = 0; i <= 5; i++) { const a = ((a0 + 18 * i) * Math.PI) / 180; out.push([cx + k * Math.cos(a), cy + k * Math.sin(a)]); }
  return out;
}
// The shadows and pools of light that things ask for, on the surface under them: one plane per surface, boxed to what it draws.
// A thing made of something (a material) throws a shadow without asking, as a thing lying on a table does.
const shadowOf = (t: Thing) => t.shadow ?? (t.backdrop ? 0 : materialOf(t)?.shadow ?? 0);
const glowOf = (t: Thing) => t.glow ?? materialOf(t)?.glow ?? 0;
function lightPlanes(c: Cam, things: Thing[], L: PlacedLight): Thing[] {
  const by = new Map<number, { shapes: any[]; x0: number; y0: number; x1: number; y1: number }>();
  for (const t of things) {
    const shadow = shadowOf(t), glow = glowOf(t);
    if (!(shadow || glow)) continue;
    const m = t.m ?? atZ(t.z ?? 0), b = t.box ?? [0, 0, c.W, c.H], u = t.under ?? surfaceUnder(t, things, c.W, c.H);
    const corners = [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]].map(([x, y]) => apply(m, x, y));
    // its outline, round its corners when it has a radius (a pill's shadow was a rectangle), in the world
    const outline = rounded(b, t.radius ?? 0).map(([x, y]) => apply(m, x, y));
    const hMid = corners.reduce((s, p) => s + p.z, 0) / 4 - u;
    const g = by.get(u) ?? { shapes: [], x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
    const grow = (x: number, y: number, pad: number) => { g.x0 = Math.min(g.x0, x - pad); g.y0 = Math.min(g.y0, y - pad); g.x1 = Math.max(g.x1, x + pad); g.y1 = Math.max(g.y1, y + pad); };
    const cx = corners.reduce((s, p) => s + p.x, 0) / 4, cy = corners.reduce((s, p) => s + p.y, 0) / 4;
    if (glow) {
      const rx = 0.9 * Math.max(...corners.map((p) => Math.abs(p.x - cx))) + 0.5 * hMid, ry = 0.9 * Math.max(...corners.map((p) => Math.abs(p.y - cy))) + 0.5 * hMid;
      g.shapes.push({ kind: "pool", cx, cy, rx: Math.max(rx, 40), ry: Math.max(ry, 40), a: 0.22 * glow * (t.opacity ?? 1) });
      grow(cx, cy, Math.max(rx, ry, 40));
    }
    // A shadow is the light that doesn't arrive, so it is as strong as the light is there: under the light it is all of
    // `strength`, far from it, where little of the light reaches, it is fainter.
    const here = L.dark * reaching(L, (cx - L.x) ** 2 + (cy - L.y) ** 2 + (u - L.z) ** 2) + (1 - L.dark) * 0.35;
    // A shadow softens and fades as its thing rises, and is gone by the time it is a third of the way up to the light: a thing
    // lifted far off the ground throws none. (Without that, things carried up out of the picture threw shadows so far and so
    // soft that their plane grew past what raea can hold, and the render stopped.)
    const top = 0.36 * (L.z - u), fade = 1 - Math.min(1, hMid / top);
    if (shadow && hMid > 0.5 && fade > 0.02) {
      const pts = outline.map((p) => shadowAt(p.x, p.y, Math.min(top, Math.max(0, p.z - u)), L, u));
      const blur = 3 + L.soft * Math.min(hMid, top), op = L.strength * shadow * (t.opacity ?? 1) * fade * here;
      g.shapes.push({ kind: "shadow", pts, blur, op });
      pts.forEach((p) => grow(p.x, p.y, 3 * blur + 4));
    }
    // Where a thing rests on the surface (within a few px of it), the light can't get in under its edge: a tight dark line round
    // it, a little wider on the side away from the light, and a faint darkening just round it. It goes as the thing lifts.
    const near = Math.exp(-Math.max(0, hMid) / 10);
    if (shadow && near > 0.05) {
      const foot = outline.map((p) => shadowAt(p.x, p.y, Math.max(0, p.z - u) + 1.5, L, u));
      g.shapes.push({ kind: "shadow", pts: foot, blur: 1.6 + 0.15 * Math.max(0, hMid), op: 0.5 * shadow * (t.opacity ?? 1) * near * (0.5 + 0.5 * here) });
      const span = Math.min(...[0, 1].map((i) => Math.hypot(corners[i + 1].x - corners[i].x, corners[i + 1].y - corners[i].y)));
      const wide = 2 + 0.04 * span;
      g.shapes.push({ kind: "shadow", pts: foot, blur: wide, op: 0.18 * shadow * (t.opacity ?? 1) * near });
      foot.forEach((p) => grow(p.x, p.y, 3 * wide + 4));
    }
    by.set(u, g);
  }
  const out: Thing[] = [];
  for (const [u, g] of by) {
    if (!g.shapes.length) continue;
    const bx: [number, number, number, number] = [Math.floor(g.x0), Math.floor(g.y0), Math.ceil(g.x1 - g.x0), Math.ceil(g.y1 - g.y0)];
    out.push({
      // drawn right after the surface it falls on (a shadow sorted before its surface was hidden under it). It lies on that
      // surface, so the lens softens it with the surface; the light doesn't dim it again (it is the light's own absence).
      // laid out from its own corner (raea rc4 dropped a plane whose content sat over about 4000 px from its corner)
      // A shadow is soft, so it is drawn no finer than the frame's own scale, as a backdrop is (enlarged, a close shot's shadow
      // planes cost 2.3 frames each in the proof film).
      key: `light@${u}`, m: mat.move(bx[0], bx[1], u + 0.5), sortZ: u + 0.0005, lit: 0, backdrop: true, box: [0, 0, bx[2], bx[3]], node: (
        <div style={{ position: "absolute", left: 0, top: 0, width: bx[2], height: bx[3] }}>
          {g.shapes.map((s, i) => s.kind === "pool" ? (
            <div key={i} style={{ position: "absolute", left: s.cx - s.rx - bx[0], top: s.cy - s.ry - bx[1], width: 2 * s.rx, height: 2 * s.ry, borderRadius: "50%", background: L.glow, opacity: s.a, filter: `blur(${(0.35 * Math.min(s.rx, s.ry)).toFixed(1)}px)` }} />
          ) : (
            // each shadow blurred in a layer the size of its own shape (a layer the plane's size for each of 108 shadows of small
            // things ran the graphics card out of memory on rc4)
            (() => { const xs = s.pts.map((p: any) => p.x), ys = s.pts.map((p: any) => p.y), m = 3 * s.blur + 2;
              const x0 = Math.floor(Math.min(...xs) - m), y0 = Math.floor(Math.min(...ys) - m), w = Math.ceil(Math.max(...xs) + m) - x0, h = Math.ceil(Math.max(...ys) + m) - y0;
              return <div key={i} style={{ position: "absolute", left: x0 - bx[0], top: y0 - bx[1], width: w, height: h, opacity: s.op, filter: `blur(${s.blur.toFixed(1)}px)` }}>
                <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ position: "absolute", left: 0, top: 0 }}>
                  <polygon points={s.pts.map((p: any) => `${(p.x - x0).toFixed(1)},${(p.y - y0).toFixed(1)}`).join(" ")} fill={L.shade} />
                </svg>
              </div>; })()
          ))}
        </div>
      ),
    });
  }
  return out;
}

// ---- what the observer sees ---------------------------------------------------------------------------------------------------
// Every plane is drawn at the size the shot needs, and the big ones are cut to what is seen and drawn in bands by depth.
// - At the size the shot needs. A plane's picture was drawn at the world's own size and the camera enlarged it, so a detail that
//   filled the frame was an enlargement and went soft. Now each picture is drawn at the most the camera enlarges any part of it
//   that is seen, in steps of a quarter octave (so a move doesn't redraw type at a new size every frame), between 1/2.8 and 4
//   times the frame's own scale (a backdrop at most at the frame's scale: a close shot is never of it), and never past 2.5
//   frames of picture for one thing.
// - What it costs. raea costs a plane by everything laid out in it, and leaves out, with no message, a plane whose content sits
//   more than about 4000 px from its corner (both measured on rc4). So a thing is drawn whole and costed
//   whole, and refused past 4000 px, unless it `crops`: then its node lays out only the part a plane shows, from that part's
//   corner, it costs only that, and a plane wholly out of the frame isn't drawn. The stage's ground crops, and so can any
//   surface bigger than the frame.
// - The big ones in bands by depth. A plane bigger than the frame was never softened by the lens (raea rc3 left such a plane out
//   of the picture, with no message, when it was blurred), so the ground, the one surface that runs from near to far, was sharp
//   from near to far. Now a backdrop or any big thing that crops is cut into bands along whichever of its own axes is nearer to
//   the way depth grows across it, each band its own plane with its own softness and resolution, each costing less than the
//   frame. A band reaches past its edges by three times its softness and nearer bands are drawn over farther ones, so no seam
//   shows. A band ends where the lens's softness has changed by 1.5 px or the depth by a third, at most ten bands, and one that
//   would cost more than the frame is cut in two. A big thing that doesn't crop stays one plane, drawn sharp if it is blurred.
type Poly = [number, number][];
const BAND_RATIO = 1.35, BAND_SOFT = 1.5, MAX_BANDS = 10, MAX_PLANE = 2.5, LAYOUT = 4000;
function clipPoly(P: Poly, f: (u: number, v: number) => number): Poly {
  const out: Poly = [];
  for (let i = 0; i < P.length; i++) {
    const a = P[i], b = P[(i + 1) % P.length], fa = f(a[0], a[1]), fb = f(b[0], b[1]);
    if (fa >= 0) out.push(a);
    if ((fa >= 0) !== (fb >= 0)) { const s = fa / (fa - fb); out.push([a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s]); }
  }
  return out;
}
// The part of a plane's box (in its own px) that lands inside the frame grown by `pad` px each side, and is in front of the camera.
// Each edge of the view is a linear function of the plane's own x, y, so the box is clipped as a polygon in its own px.
export function seenPart(c: Cam, m: M4, b: [number, number, number, number], pad: number): Poly {
  const R = rows(c), X = through(R.X, m), Y = through(R.Y, m), Z = through(R.Z, m), ox = c.ox ?? c.W / 2, oy = c.oy ?? c.H / 2;
  const lin = (a: number[]) => (u: number, v: number) => a[0] * u + a[1] * v + a[3];
  const edges = [
    lin(Z.map((z, j) => z - (j === 3 ? 60 : 0))),
    lin(X.map((x, j) => c.focal * x + (ox + pad) * Z[j])), lin(X.map((x, j) => (c.W + pad - ox) * Z[j] - c.focal * x)),
    lin(Y.map((y, j) => c.focal * y + (oy + pad) * Z[j])), lin(Y.map((y, j) => (c.H + pad - oy) * Z[j] - c.focal * y)),
  ];
  let P: Poly = [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]];
  for (const e of edges) { P = clipPoly(P, e); if (P.length < 3) return []; }
  return P;
}
const bboxOf = (P: Poly) => { const xs = P.map((p) => p[0]), ys = P.map((p) => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
// a picture's scale (its px per own px) in quarter octaves of the frame's own scale
const stepScale = (need: number, base: number, most = 8) => base * 2 ** (Math.max(-6, Math.min(most, Math.round(4 * Math.log2(Math.max(1e-6, need / base))))) / 4);

// How the light falls on one thing, in its own px. Its own x, y and the distance off its surface are worked out from its matrix
// (whose two columns are square to each other in everything lie, stand and face make), so a lying card, a print on a wall and a
// label facing the observer are all lit by one law.
type Lit = { b: number; lo: number; hi: number; foot: [number, number]; sc: number; Lw: number; L: PlacedLight; lit: number;
  rim: [number, number, number, number]; sheen: { x: number; y: number; r: number; a: number } | null; far: number };
function litOf(c: Cam, t: Thing, m: M4, b: [number, number, number, number], L: PlacedLight): Lit {
  const c0 = [m[0], m[4], m[8]], c1 = [m[1], m[5], m[9]], o = [m[3], m[7], m[11]], sc = Math.hypot(c0[0], c0[1], c0[2]) || 1;
  const n0 = [c0[1] * c1[2] - c0[2] * c1[1], c0[2] * c1[0] - c0[0] * c1[2], c0[0] * c1[1] - c0[1] * c1[0]], nl = Math.hypot(n0[0], n0[1], n0[2]) || 1, n = n0.map((v) => v / nl);
  const dot = (a: number[], q: number[]) => a[0] * q[0] + a[1] * q[1] + a[2] * q[2];
  const local = (P: number[]) => { const d = [P[0] - o[0], P[1] - o[1], P[2] - o[2]]; return [dot(c0, d) / (sc * sc), dot(c1, d) / (sc * sc), dot(n, d)]; };
  const Ll = local([L.x, L.y, L.z]), E = eye(c), El = local([E.x, E.y, E.z]);
  const M = materialOf(t), lit = t.lit ?? M?.lit ?? 1;
  const at = (u: number, v: number) => 1 - L.dark * (1 - reaching(L, ((u - Ll[0]) ** 2 + (v - Ll[1]) ** 2) * sc * sc + Ll[2] * Ll[2]));
  const corners = [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]];
  const nearest = [Math.max(b[0], Math.min(b[0] + b[2], Ll[0])), Math.max(b[1], Math.min(b[1] + b[3], Ll[1]))];
  const ref = t.ref ?? [b[0] + b[2] / 2, b[1] + b[3] / 2];
  const far = Math.max(...corners.map(([u, v]) => Math.hypot(u - Ll[0], v - Ll[1])));
  // the edge facing the light brightens and the one away from it darkens, by how squarely each faces it; a light right overhead
  // lights no edge more than another
  const mid = [b[0] + b[2] / 2, b[1] + b[3] / 2], hx = (Ll[0] - mid[0]) * sc, hy = (Ll[1] - mid[1]) * sc, hn = Math.hypot(hx, hy) || 1;
  const side = Math.min(1, (3 * hn) / Math.hypot(hn, Ll[2]));
  const rim: [number, number, number, number] = [(-hy / hn) * side, (hx / hn) * side, (hy / hn) * side, (-hx / hn) * side];   // top, right, bottom, left
  // the sheen: where the light mirrors into the observer's eye, if both are in front of the surface
  let sheen: Lit["sheen"] = null;
  if (M && M.sheen[0] > 0 && Ll[2] > 1 && El[2] > 1) {
    const w = Ll[2] + El[2], x = (Ll[0] * El[2] + El[0] * Ll[2]) / w, y = (Ll[1] * El[2] + El[1] * Ll[2]) / w;
    const r = (M.sheen[1] * 2 * Ll[2] * El[2]) / w / sc;
    sheen = { x, y, r, a: M.sheen[0] * reaching(L, ((x - Ll[0]) ** 2 + (y - Ll[1]) ** 2) * sc * sc + Ll[2] * Ll[2]) };
  }
  return { b: at(ref[0], ref[1]), lo: Math.min(...corners.map(([u, v]) => at(u, v))), hi: at(nearest[0], nearest[1]), foot: [Ll[0], Ll[1]], sc, Lw: Ll[2], L, lit, rim, sheen, far };
}
// The light's falloff as a radial gradient of darkness round the point of the surface nearest the light, `far` own px across.
// A gradient is straight between its stops, so a stop is placed wherever the brightness has changed by a step, or a sixteenth
// of the way has gone by, and the step is the whole change in 48 parts (at least 0.6%). raea rc4 drew a gradient of 122 stops
// and left a whole plane out, with no message, for one of 141.
// `mask`: false for a darkening to lay over a thing that fills its box; "lit" for a mask that is whole where the light is
// brightest across the thing and clear where it is darkest; "rest" for what that mask leaves, so the two add up to one
// everywhere.
function falloffCss(q: Lit, k = 1, ox = 0, oy = 0, mask: false | "lit" | "rest" = false) {
  const R = Math.max(1, q.far), stops: string[] = [];
  const total = Math.abs(reaching(q.L, q.Lw * q.Lw) - reaching(q.L, R * R * q.sc * q.sc + q.Lw * q.Lw)) * q.L.dark, step = Math.max(0.006, total / 48);
  const bAt = (rho: number) => 1 - q.L.dark * (1 - reaching(q.L, rho * rho * q.sc * q.sc + q.Lw * q.Lw));
  const toward = (b: number) => +Math.max(0, Math.min(1, q.hi - q.lo > 1e-6 ? (b - q.lo) / (q.hi - q.lo) : 1)).toFixed(4);
  const alpha = (b: number) => (mask === "lit" ? toward(b) : mask === "rest" ? 1 - toward(b) : q.lit * (1 - b));
  let rho = 0;
  for (let n = 0; n < 200; n++) {
    const b = bAt(rho);
    stops.push(`${unlit(Math.max(0, Math.min(1, alpha(b))).toFixed(4))} ${((100 * rho) / R).toFixed(3)}%`);
    if (rho >= R) break;
    let next = Math.min(R, rho + R / 16);
    for (let i = 0; i < 30 && Math.abs(bAt(next) - b) > step; i++) next = rho + (next - rho) / 2;
    rho = Math.max(next, rho + R / 4000);
  }
  return `radial-gradient(circle ${(R * k).toFixed(2)}px at ${(q.foot[0] * k - ox).toFixed(2)}px ${(q.foot[1] * k - oy).toFixed(2)}px, ${stops.join(", ")})`;
}

// What a thing is made of, drawn over it inside its own shape: the light's falloff across it, its grain, the light seen in it,
// and its edge. In its own px; no plane of its own.
// Light and dark themselves, as colours with an alpha: neutral, so no source's colour is held here. (A mask uses only alpha.)
const LIGHT_RGB = [255, 255, 255].join(","), DARK_RGB = [0, 0, 0].join(",");
const lit = (a: number | string) => `rgba(${LIGHT_RGB},${a})`, unlit = (a: number | string) => `rgba(${DARK_RGB},${a})`;
const OPAQUE = "linear-gradient(black, black)";

// The part of a thing's box a plane shows (`seen`, own px), as one rectangle, with the box's own corners rounded where they fall
// inside it. A thing that crops lays out only this, from its corner: raea rc4 left out, with no message, a plane whose content
// sat more than about 4000 px from its corner, and it costs a plane by all it lays out (a ground 9000 px across, cut to a
// frame's worth, vanished beside other planes). (Laid out in pieces instead, their meeting lines showed across a ground.)
export function part(b: [number, number, number, number], rad = 0, seen?: [number, number, number, number]) {
  const s = seen ?? b, x0 = Math.max(b[0], s[0]), y0 = Math.max(b[1], s[1]), x1 = Math.min(b[0] + b[2], s[0] + s[2]), y1 = Math.min(b[1] + b[3], s[1] + s[3]);
  if (x1 <= x0 || y1 <= y0) return [];
  const L = x0 <= b[0] + 0.5, T = y0 <= b[1] + 0.5, R = x1 >= b[0] + b[2] - 0.5, B = y1 >= b[1] + b[3] - 0.5, c = (a: boolean) => (a ? `${rad}px` : "0px");
  return [{ x: x0, y: y0, w: x1 - x0, h: y1 - y0, r: `${c(L && T)} ${c(R && T)} ${c(R && B)} ${c(L && B)}`, sides: [L, T, R, B] }];   // sides: which of the box's own sides this piece has
}

function Surface({ t, q, b, seen, from }: { t: Thing; q: Lit; b: [number, number, number, number]; seen: [number, number, number, number]; from: [number, number] }) {
  // Each layer is rounded by its own corners. (A rounded parent with overflow: hidden clipped in the wrong place inside a
  // plane with perspective on rc4.)
  const M = materialOf(t)!, rad = t.radius ?? 0, P = part(b, rad, seen);
  const at = (p: (typeof P)[number]): any => ({ position: "absolute", left: p.x - from[0], top: p.y - from[1], width: p.w, height: p.h, borderRadius: p.r });
  // the edge: a bright border faded in toward the light and a dark one faded in away from it. (One border of four colours drew
  // its corners in steps on rc4 when a rounded thing was seen close.) It is laid out piece by piece, like everything else
  // here: the sides of the box a piece has, and no more. As first built each border was a layer the size of the whole box
  // whatever the piece, so a sheet 9000 px across cut to a frame's worth laid out two layers 9000 px across that the area
  // check never counted, which is what loses planes. The fade is the one the whole box would have (clear until three tenths
  // of the way across it toward the light's side, whole from 85 hundredths), worked out for each piece's own box so the
  // pieces of one thing agree where they meet.
  const rimW = M.rim[0] / q.sc, ang = (Math.atan2(q.rim[1], q.rim[0]) * 180) / Math.PI, side = Math.hypot(q.rim[0], q.rim[1]);
  const rimDiv = (p: (typeof P)[number], colour: string, deg: number, key: string) => {
    const th = (deg * Math.PI) / 180, sn = Math.sin(th), cs = Math.cos(th);
    const across = (w: number, h: number) => Math.abs(w * sn) + Math.abs(h * cs), along = (x: number, y: number) => x * sn - y * cs;
    // how far across the whole box (0 to 1, along the fade) a place in this piece is, and so how whole the fade is there
    const inBox = (tp: number) => 0.5 + (along(p.x + p.w / 2, p.y + p.h / 2) + (tp - 0.5) * across(p.w, p.h) - along(b[0] + b[2] / 2, b[1] + b[3] / 2)) / Math.max(1e-6, across(b[2], b[3]));
    const inPiece = (t0: number) => 0.5 + (along(b[0] + b[2] / 2, b[1] + b[3] / 2) + (t0 - 0.5) * across(b[2], b[3]) - along(p.x + p.w / 2, p.y + p.h / 2)) / Math.max(1e-6, across(p.w, p.h));
    const fade = (t0: number) => Math.max(0, Math.min(1, (t0 - 0.3) / 0.55));
    const stops = [[0, fade(inBox(0))], ...[0.3, 0.85].map((t0) => [inPiece(t0), fade(t0)]).filter(([tp]) => tp > 0 && tp < 1), [1, fade(inBox(1))]];
    const line = (on: boolean) => (on ? `${rimW.toFixed(2)}px solid ${colour}` : `0px solid ${colour}`);
    return <div key={key} style={{ ...at(p), boxSizing: "border-box", borderLeft: line(p.sides[0]), borderTop: line(p.sides[1]), borderRight: line(p.sides[2]), borderBottom: line(p.sides[3]),
      maskImage: `linear-gradient(${deg.toFixed(1)}deg, ${stops.map(([tp, a]) => `${unlit(a.toFixed(4))} ${(100 * tp).toFixed(2)}%`).join(", ")})` }} />;
  };
  const edged = rimW > 0.05 && !t.backdrop && side > 0.02 ? P.filter((p) => p.sides.some(Boolean)) : [];
  const tile = 512 / q.sc;
  return (
    <>
      {M.grain > 0 && PAPER ? P.map((p, i) => <div key={`g${i}`} style={{ ...at(p), backgroundImage: `url(${PAPER})`, backgroundSize: `${tile.toFixed(1)}px ${tile.toFixed(1)}px`, backgroundRepeat: "repeat", backgroundPosition: `${(b[0] - p.x).toFixed(1)}px ${(b[1] - p.y).toFixed(1)}px`, opacity: M.grain, mixBlendMode: "multiply" }} />) : null}
      {q.lit > 0 && (q.hi - q.lo > 0.002 || q.b < 0.998) ? P.map((p, i) => <div key={`f${i}`} style={{ ...at(p), background: falloffCss(q, 1, p.x, p.y), mixBlendMode: "multiply" }} />) : null}
      {q.sheen && q.sheen.a > 0.004 ? P.map((p, i) => <div key={`s${i}`} style={{ ...at(p), background: `radial-gradient(circle ${q.sheen!.r.toFixed(1)}px at ${(q.sheen!.x - p.x).toFixed(1)}px ${(q.sheen!.y - p.y).toFixed(1)}px, ${lit(q.sheen!.a.toFixed(3))} 0%, ${lit((q.sheen!.a * 0.4).toFixed(3))} 35%, ${lit(0)} 100%)`, mixBlendMode: "screen" }} />) : null}
      {edged.map((p, i) => rimDiv(p, lit((M.rim[1] * side).toFixed(3)), ang, `l${i}`))}
      {edged.map((p, i) => rimDiv(p, unlit((M.rim[2] * side).toFixed(3)), ang + 180, `d${i}`))}
    </>
  );
}

// `box` is the plane's picture, in its px: the part of the thing's box it draws, at `k`
// picture px to each of the thing's own px. `soft` is the lens's softness in px of that picture.
export type Plane = { t: Thing; key: string; m: M4; depth: number; s: number; sort: number; css: string; soft: number; k: number; box: [number, number, number, number]; clip: boolean; q: Lit; own: [number, number, number, number]; cost: [number, number] };
// What the observer sees: the things and the light they ask for, as planes in the order they are drawn, far to near.
// Things are drawn lowest first (seen from above, what is higher is in front); a standing thing is drawn with the height it
// stands on, farthest first. Where that order is wrong for a scene, give `order` or `sortZ`.
export function planes(c: Cam, things: (Thing | null | false | undefined)[], light: Light = LIGHT, limit = AREA_LIMIT): Plane[] {
  const L = placed(light, c);
  const list = things.filter(Boolean) as Thing[];
  const all = [...lightPlanes(c, list, L), ...list];
  const k = sizeOf(c), world = c.world ?? c.W, R = rows(c), pad0 = 0.022 * c.W;
  const out: Plane[] = [];
  for (const t of all) {
    const m = t.m ?? atZ(t.z ?? 0), b = t.box ?? [0, 0, world, (c.H * world) / c.W], ref = t.ref ?? [b[0] + b[2] / 2, b[1] + b[3] / 2];
    const w = apply(m, ref[0], ref[1]), pr = project(c, w.x, w.y, w.z);
    const base = t.stands ? Math.min(...[[b[0], b[1] + b[3]], [b[0] + b[2], b[1] + b[3]]].map(([x, y]) => apply(m, x, y).z)) + 0.5 - pr.depth * 1e-7 : w.z;
    const sort = (t.sortZ ?? base) + (t.order ?? 0) * 1e-3;
    const sc = Math.hypot(m[0], m[4], m[8]) || 1, Z = through(R.Z, m), depthAt = (u: number, v: number) => Z[0] * u + Z[1] * v + Z[3];
    // the lens's softness in frame px at a depth, and the frame px one of the thing's own px covers there
    const blurAt = (d: number) => ((t.sharp ? 0 : softness(c, d)) + (t.blur ?? 0)) * k, pxAt = (d: number) => (c.focal / Math.max(60, d)) * sc;
    const q = litOf(c, t, m, b, L);
    const big = b[2] * b[3] * (k * sc) ** 2 > c.W * c.H;
    // a picture of the part `poly` of this thing, softened by `soft` frame px, as close as `near`
    const make = (mm: M4, poly: Poly, soft: number, near: number, mid: number): Plane => {
      // the picture: the seen part's box, grown by three times its softness, at the scale its nearest seen point needs. A
      // backdrop is drawn at most at the frame's own scale: it is the far thing, and a close shot is never of it.
      // Anything that isn't laid out by the part it shows is drawn whole: it costs its whole box anyway, and cut, its content would
      // sit far from the picture's corner, which raea rc4 doesn't draw.
      const grow = (3 * soft + pad0 * 0.1) / pxAt(near), bb = t.crops ? bboxOf(poly) : [b[0], b[1], b[0] + b[2], b[1] + b[3]];
      const x0 = Math.floor(bb[0] - (t.crops ? grow : 0)), y0 = Math.floor(bb[1] - (t.crops ? grow : 0)), x1 = Math.ceil(bb[2] + (t.crops ? grow : 0)), y1 = Math.ceil(bb[3] + (t.crops ? grow : 0));
      // What raea costs a plane by is all it lays out, not its box (a ground 9000 px across, cut to a frame's worth, was left
      // out of frames beside other planes on rc4; laid out only where seen, it wasn't). A thing that lays out only what it is
      // shown (`crops`) costs its cut; anything else costs its whole box at the picture's scale, and is enlarged no further
      // than that allows.
      let r = stepScale(pxAt(near), k * sc, t.backdrop ? 0 : 8);
      const laid = t.crops ? (x1 - x0) * (y1 - y0) : b[2] * b[3];
      if (laid * r * r > MAX_PLANE * c.W * c.H) r = Math.sqrt((MAX_PLANE * c.W * c.H) / laid);
      const box: [number, number, number, number] = [x0 * r, y0 * r, (x1 - x0) * r, (y1 - y0) * r];
      const full = x0 <= b[0] && y0 <= b[1] && x1 >= b[0] + b[2] && y1 >= b[1] + b[3];
      const cost: [number, number] = t.crops ? [box[2], box[3]] : [b[2] * r, b[3] * r];
      if (!t.crops && (Math.max(Math.abs(b[0]), Math.abs(b[1])) * r > LAYOUT || Math.max(b[2], b[3]) > 2 * LAYOUT))
        throw new Error(`scene: "${t.key}" is laid out ${Math.round(Math.max(b[2], b[3]))} px across from ${Math.round(b[0])}, ${Math.round(b[1])}, drawn at ${r.toFixed(2)} times. raea rc4 leaves out, with no message, a plane whose content sits more than about ${LAYOUT} px from its corner. Lay a thing that big out only where it is seen: give it "crops" and a node that is a function of the part it is shown, as the stage's ground does.`);
      return { t, key: t.key, m: mat.mul(mm, mat.scale(1 / r)), depth: pr.depth, s: pr.s, sort, css: "", soft: (soft / pxAt(mid)) * r, k: r, box, clip: !full, q, own: b, cost };
    };
    const frame = 0.95 * c.W * c.H, sizeOfP = (p: Plane) => p.cost[0] * p.cost[1];
    if (!t.crops || (!big && !t.backdrop)) {
      const soft = blurAt(pr.depth), poly = seenPart(c, m, b, pad0 + 3 * soft);
      if (!poly.length) continue;
      const one = make(m, poly, soft, Math.min(...poly.map(([u, v]) => depthAt(u, v))), pr.depth);
      // A blurred picture costing more than the frame: raea rc3 left such a plane out of the picture, with no message. One that
      // lays out only what is seen goes in bands; anything else is drawn sharp, as a plane that big always was (each band of
      // it would cost all of it again).
      if (one.cost[0] * one.cost[1] <= frame || one.soft <= 0.35) { out.push(one); continue; }
      if (!t.crops) { out.push({ ...one, soft: 0 }); continue; }
    }
    // a big plane, in bands across the lines of equal depth
    const ap = (c.aperture ?? 0) * k, padB = pad0 + 3 * Math.min(40, 2 * ap + (t.blur ?? 0) * k);
    const poly = seenPart(c, m, b, padB);
    if (!poly.length) continue;
    // Bands run along whichever of the thing's own axes is nearer to the way depth grows across it, so its picture is never
    // turned: content turned inside a plane was drawn to a picture of its own the size of its turned bounds, and a ground 9000 px
    // across, turned, lost the whole plane on rc4 with no message. The bands then lie a little across the lines of equal depth
    // (at most 45 degrees), and each is softened by its depth at the middle of what is seen of it.
    const ax = Math.abs(Z[0]) >= Math.abs(Z[1]) ? 0 : 1, dir = Z[ax] >= 0 ? 1 : -1, gl = Math.abs(Z[ax]);
    const mid = poly.reduce((a, p) => a + p[1 - ax], 0) / poly.length, c0 = Z[1 - ax] * mid + Z[3];
    const P = poly.map((p) => [dir * p[ax], p[1 - ax]] as [number, number]);   // (along, across): along grows with depth
    const s0 = Math.min(...P.map((p) => p[0])), s1 = Math.max(...P.map((p) => p[0]));
    const depthS = (s: number) => gl * s + c0, sAt = (d: number) => (gl > 1e-9 ? (d - c0) / gl : s1);
    const back = (q: Poly): Poly => q.map(([a, b]) => (ax === 0 ? [dir * a, b] : [b, dir * a]));
    const F = c.focus ?? c.dist, A = t.sharp ? 0 : (c.aperture ?? 0) * k, signed = (d: number) => (A * (d - F)) / d;
    const cuts = [s0];
    while (cuts[cuts.length - 1] < s1 - 1e-6 && cuts.length <= MAX_BANDS) {
      const s = cuts[cuts.length - 1], d = depthS(s);
      let next = sAt(d * BAND_RATIO);
      if (A > 0) { const target = signed(d) + BAND_SOFT; if (target < A) next = Math.min(next, sAt((A * F) / (A - target))); }
      cuts.push(cuts.length === MAX_BANDS ? s1 : Math.min(s1, Math.max(next, s + 1)));
    }
    const made: Plane[] = [];
    for (let i = 0; i < cuts.length - 1;) {
      const last = i === cuts.length - 2, sa = cuts[i], sb = cuts[i + 1], dm = depthS((sa + sb) / 2), soft = blurAt(dm), g = (3 * soft + pad0 * 0.1) / pxAt(depthS(sa));
      const part = clipPoly(clipPoly(P, (s) => s - (sa - (i ? g : 0))), (s) => (sb + (!last ? g : 0)) - s);
      if (part.length < 3) { i++; continue; }
      const band = make(m, back(part), soft, Math.max(60, depthS(Math.max(s0, sa - g))), dm);
      // a band bigger than the frame is cut in two (raea has dropped blurred pictures that big)
      if (sizeOfP(band) > frame && sb - sa > 8 && cuts.length < 4 * MAX_BANDS) { cuts.splice(i + 1, 0, (sa + sb) / 2); continue; }
      made.push(band); i++;
    }
    // far bands first, so a nearer band's soft edge lies over the farther one and nothing behind shows through
    made.forEach((p, i) => out.push({ ...p, key: `${t.key}#${made.length - 1 - i}`, sort: p.sort + (made.length - 1 - i) * 1e-7 }));
  }
  checkArea(out.map((p) => ({ ...p.t, key: p.key, box: [0, 0, p.cost[0], p.cost[1]] as [number, number, number, number] })), c.W, c.H, limit);
  return out.sort((a, b) => a.sort - b.sort).map((p) => ({ ...p, css: planeCss(c, mat.mul(p.m, mat.move(p.box[0], p.box[1], 0))) }));
}

// What a plane says about itself so its type can be judged at the size the camera draws it. raea lists a film's type at the
// size it is set, and knows nothing of this matrix: a film staged in a scene had every size reported as set, and type the
// frame never showed counted as read. So each plane holds two lines nobody sees, one where what it holds is laid out from
// and one after it. The first says the thing's name, the scale the plane's picture is drawn at (`p.k`), and the matrix that
// takes a place in that picture, measured from where the layout starts (`at`), to a place on screen. raea gives a text's
// box as that scale has drawn it and its size as it was set (measured on rc4: a line set at 76 px on a plane drawn at 1.414
// had a box 118 px high), which is why the scale is said apart. The look report (`vd look`) reads them. A thing drawn as several
// planes (bands of a ground, a thing lit in two passes) says the same name and the same place on screen each time.
export const TYPE_END = "[[/plane]]";
export function typeMark(c: Cam, p: Plane, at: [number, number] = [0, 0]): string {
  const n = planeNumbers(c, mat.mul(p.m, mat.move(p.box[0], p.box[1], 0))), [x, y] = at;
  const to = [...n.slice(0, 12), n[12] + x * n[0] + y * n[4], n[13] + x * n[1] + y * n[5], 0, n[15] + x * n[3] + y * n[7]];
  return `[[plane ${p.t.key.replace(/[^\w.-]+/g, "-") || "thing"} ${[p.k, ...to].map((v) => String(+v.toFixed(9))).join(" ")}]]`;
}
const UNSEEN = { position: "absolute", left: 0, top: 0, fontSize: 1, lineHeight: "1px", color: "transparent", whiteSpace: "nowrap" } as const;

// Draws what `planes` lists. Each plane is one matrix3d, the size of its picture, clipped there when it is a cut of its thing.
// Inside, what it holds is moved back to the thing's own corner in a wrapper of no size (so it adds nothing to the plane's own
// size), turned for a band, and drawn at the picture's scale. A thing made of something takes the light inside its own shape
// (`Surface`). Anything else (type, a part, an author's own drawing) may not fill its box, and a darkening laid over it would
// darken the empty part too (measured on rc4), so it is drawn in two passes that add up: at the brightest the light leaves
// it, under a mask that is the light's falloff, and at the darkest, under what that mask leaves. The second is added to the
// first, not laid over it (`plus-lighter`), so what is half clear stays half clear. Laid one over the other, as this was
// first built, a half-clear drawing came out three quarters solid where it was lit, and type was heavier at its lit end.
// Where the light hardly changes across a thing, it is drawn once, with one brightness. On rc4 the blend is ignored on a
// layer that itself has a mask, so it is given to a wrapper. Outside a picture of its own the blend adds to whatever is
// behind as well; a plane is drawn to a picture of its own, so here it adds only to the first pass. (A group round the two
// passes to make sure of that was one layer too many: rc4 refused a plane a little bigger than the frame.)
export function Scene({ cam, things, light = LIGHT, limit }: { cam: Cam; things: (Thing | null | false | undefined)[]; light?: Light; limit?: number }) {
  const L = placed(light, cam);
  return (
    <>
      {planes(cam, things, L, limit).map((p) => {
        const { t, css, soft, k: r, box: B, clip, q } = p, seen: [number, number, number, number] = [B[0] / r, B[1] / r, B[2] / r, B[3] / r];
        const fills = !!t.material && t.material !== "none", dim = (v: number) => 1 - q.lit * (1 - v);
        const twice = !fills && q.lit > 0 && q.hi - q.lo > 0.03, once = !fills && !twice && q.lit > 0 && dim(q.b) < 0.995;
        // A thing that crops lays out only the part it is shown, from that part's corner; anything else is laid out from its own.
        const said = <div style={UNSEEN}>{typeMark(cam, p, t.crops ? [0, 0] : [-B[0], -B[1]])}</div>, over = <div style={UNSEEN}>{TYPE_END}</div>;
        const body = t.crops ? (
          <div style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, transformOrigin: "0 0", transform: `scale(${r.toFixed(6)})` }}>
            {said}
            {t.node(seen)}
            {fills ? <Surface t={t} q={q} b={p.own} seen={seen} from={[seen[0], seen[1]]} /> : null}
            {over}
          </div>
        ) : (
          <div style={{ position: "absolute", left: -B[0], top: -B[1], width: 0, height: 0, transformOrigin: "0 0", transform: `scale(${r.toFixed(6)})` }}>
            {said}
            {typeof t.node === "function" ? t.node(seen) : t.node}
            {fills ? <Surface t={t} q={q} b={p.own} seen={seen} from={[0, 0]} /> : null}
            {over}
          </div>
        );
        // A cut of a thing is clipped by a mask the size of its picture: overflow: hidden on a plane with perspective clipped in
        // the wrong place on rc4 (a band of the ground ended 700 px short), and a mask clips where it is drawn.
        const layer = (key: string, filter?: string, mask?: string) => <div key={key} style={{ position: "absolute", left: 0, top: 0, width: B[2], height: B[3], filter, maskImage: mask ?? (clip ? OPAQUE : undefined) }}>{body}</div>;
        let inner: any = clip ? layer("cut") : body;
        const lens = soft > 0.35 ? `blur(${soft.toFixed(2)}px)` : "";
        if (twice) {
          // Each pass is softened by the lens itself, so no filter has more than one layer the plane's size under it
          // (rc4 refuses a filter with too many: "past Vello's bump buffers"). The masks change slowly beside a lens's
          // softness, so softening before the mask or after it is the same picture.
          const whole: any = { position: "absolute", left: 0, top: 0, width: B[2], height: B[3] };
          const pass = (v: number) => [v < 0.999 ? `brightness(${v.toFixed(4)})` : "", lens].filter(Boolean).join(" ") || undefined;
          inner = (
            <>
              {layer("lo", pass(dim(q.lo)), falloffCss(q, r, B[0], B[1], "rest"))}
              <div style={{ ...whole, mixBlendMode: "plus-lighter" }}>{layer("hi", pass(dim(q.hi)), falloffCss(q, r, B[0], B[1], "lit"))}</div>
            </>
          );
        }
        const filter = [twice ? "" : lens, once ? `brightness(${dim(q.b).toFixed(4)})` : ""].filter(Boolean).join(" ") || undefined;
        return (
          <div key={p.key} style={{ position: "absolute", left: 0, top: 0, width: B[2], height: B[3], transformOrigin: "0 0", transform: css, opacity: t.opacity ?? 1, filter }}>
            {inner}
          </div>
        );
      })}
      {light.tint && (light.tintA ?? 0) > 0.001 ? <div style={{ position: "absolute", left: 0, top: 0, width: cam.W, height: cam.H, background: light.tint, opacity: light.tintA, mixBlendMode: "multiply" }} /> : null}
      {light.lift && (light.liftA ?? 0) > 0.001 ? <div style={{ position: "absolute", left: 0, top: 0, width: cam.W, height: cam.H, background: light.lift, opacity: light.liftA, mixBlendMode: "screen" }} /> : null}
    </>
  );
}
