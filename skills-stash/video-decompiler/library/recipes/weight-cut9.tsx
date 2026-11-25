// Weight: a wooden letter I that has carried an iron IT so long it took its shape. Real light, real shadow.
import { AbsoluteFill, Composition, registerRoot, staticFile, useCurrentFrame } from "raea";
import { AmbientOcclusion, DepthOfField, Environment, FogVolume, Grade, RichText, Shadows, Text3D, ToneMapping, VolumetricFog, manifold } from "raea/3d";
import { StandardMaterial } from "raea/pbr";
import { Cuboid, Mesh3d } from "raea/mesh";
import { AmbientLight, DirectionalLight, RectLight } from "raea/light";
import { Quat, Transform } from "raea/transform";
import { Camera3d } from "raea/camera";
import { phSet } from "./lib/ground";

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const smooth = (v: number) => { const u = clamp01(v); return u * u * (3 - 2 * u); };
const mix = (a: number, b: number, u: number) => a + (b - a) * u;

// ---- the I: a slab-serif column built like a spine: rigid oak blocks on a dark core. Wood does not stretch; the joints open.
const H = 1.8, STEM = 0.3, DEPTH = 0.3, SERIF_W = 0.82, SERIF_H = 0.13;
const LEVELS = 60, PHI_MAX = 0.52, N = 48, BLOCKS = 14;
type Curve = { cx: number[]; cy: number[]; phi: number[] };
/** Its posture. level: the stoop (0 upright .. 60 bowed), curling more the higher it goes. nod: the neck alone, radians.
 *  bow: bending from the waist (between 12% and 60% of its height), radians: how it lowers something to the floor. */
function curve(level: number, nod = 0, bow = 0): Curve {
  const P = (PHI_MAX * Math.max(0, Math.min(80, level))) / LEVELS, ds = H / N, cx = [0], cy = [0], phi = [0];
  const ang = (u: number) => P * Math.pow(u, 1.6) + nod * smooth((u - 0.72) / 0.28) + bow * smooth((u - 0.12) / 0.48);
  for (let i = 1; i <= N; i++) {
    const mid = ang(((i - 0.5) * ds) / H);
    cx.push(cx[i - 1] + Math.sin(mid) * ds); cy.push(cy[i - 1] + Math.cos(mid) * ds); phi.push(ang((i * ds) / H));
  }
  return { cx, cy, phi };
}
const at = (c: Curve, s: number) => {
  const u = Math.min(N - 1e-6, Math.max(0, s / (H / N))), i = Math.floor(u), fr = u - i;
  return { x: c.cx[i] + (c.cx[i + 1] - c.cx[i]) * fr, y: c.cy[i] + (c.cy[i + 1] - c.cy[i]) * fr, phi: c.phi[i] + (c.phi[i + 1] - c.phi[i]) * fr };
};
const topOf = (level: number, nod = 0, bow = 0) => { const c = curve(level, nod, bow); return { x: c.cx[N], y: c.cy[N], tip: c.phi[N] }; };
const IT_SIZE = 1.15, IT_HALF = 0.358 * IT_SIZE;    // the iron word, and half its height
const IT_W2 = 0.5;                                  // half its width: how high its middle is when it lies on its side

// ---- the room: plaster, and out of frame on the left a wall with one tall window that the sun comes through
const IX = -0.9;                                    // where the I stands
const SUN = [4, -0.8, -3.4] as const;               // the way the light travels: right, a little down, to the back
const WIN = { h: 3.4, w: 2.6, y: 1.75 };
const SHADE = manifold.box(0.2, 12, 40)
  .minus(manifold.box(1, WIN.h, WIN.w).move(0, WIN.y - 6, -0.72))
  .union(manifold.box(0.12, WIN.h, 0.07).move(0, WIN.y - 6, -0.72), manifold.box(0.12, 0.07, WIN.w).move(0, WIN.y - 6 + 0.45, -0.72));
const plaster = phSet("plastered_wall", "1k", [7, 3.2]);
const floor = phSet("plastered_wall", "1k", [6, 6], { base_color: "#a39c90" });

function Room({ children }: { children?: any }) {
  return (
    <>
      <ToneMapping mode="agx" exposure={0} />
      <Shadows distance={40} firstCascade={9} mapSize={4096} />
      <AmbientOcclusion quality="high" />
      <AmbientLight brightness={240} color="#cdd6e8" />
      <Environment src={staticFile("kloofendal_28d_misty_puresky/kloofendal_28d_misty_puresky_1k.hdr")} intensity={0.1} />
      <DirectionalLight volumetric transform={Transform.fromXyz(IX - 3 * SUN[0], 0.95 - 3 * SUN[1], -3 * SUN[2]).lookingAt([IX, 0.95, 0])} illuminance={52000} color="#ffd2a0" shadow_maps_enabled soft_shadow_size={0.6} />
      {/* the window's own soft light, the sky behind the sun: it gives the things in the room their form and leaves the far wall dark */}
      <RectLight name="sky" transform={Transform.fromXyz(-4.6, 1.9, 2.5).lookingAt([0.6, 0.7, 0.6])} intensity={45000} width={2.6} height={3.4} color="#dfe6f6" />
      {/* what the sunlit wall gives back to the room: a warm light from behind, on the backs and edges of things */}
      <RectLight name="bounce" transform={Transform.fromXyz(0.05, 1.5, -1.5).lookingAt([0.2, 1.0, 4])} intensity={BOUNCE} width={2.8} height={3.0} color="#ffd9b4" />
      <VolumetricFog />
      <FogVolume name="air" position={[0, 2.2, 1.5]} scale={[13, 4.6, 13]} density={0.022} color="#fff0d8" scattering={0.5} absorption={0.04} anisotropy={0.65} />
      <Mesh3d name="shade" transform={Transform.fromXyz(IX - SUN[0], 6, -SUN[2])} shape={SHADE}><StandardMaterial base_color="#bdb7ad" perceptual_roughness={1} /></Mesh3d>
      <Mesh3d name="wall" transform={Transform.fromXyz(0, 4, -1.7)}><Cuboid half_size={[9, 4, 0.1]} /><StandardMaterial {...plaster} /></Mesh3d>
      <Mesh3d name="floor" transform={Transform.fromXyz(0, -0.05, 3)}><Cuboid half_size={[9, 0.05, 9]} /><StandardMaterial {...floor} /></Mesh3d>
      {children}
    </>
  );
}
const BOUNCE = 60000;

const iron = phSet("plastered_wall", "1k", [1.6, 1.6], { base_color: "#34343a" });
const Iron = () => <StandardMaterial {...iron} metallic={0.7} />;

const oak = (i: number) => phSet("oak_wood_planks", "1k", [0.5, 0.5], { base_color: i % 2 ? "#e9d6b6" : "#dcc7a4" });
const CORE = 16;                                    // pieces of the dark core the blocks are threaded on: what shows in an open joint
function Letter({ level, nod = 0, bow = 0, y = 0, tip = 0 }: { level: number; nod?: number; bow?: number; y?: number; tip?: number }) {
  // tip > 0 tips the whole letter toward its stoop about the right-hand corner of its foot; tip < 0 the other way, about the left
  const c = curve(level, nod, bow), px = tip >= 0 ? SERIF_W / 2 : -SERIF_W / 2, a = -tip, ca = Math.cos(a), sa = Math.sin(a);
  const place = (lx: number, ly: number, rot: number) => Transform.fromXyz(IX + px + (lx - px) * ca - ly * sa, y + (lx - px) * sa + ly * ca, 0).withRotation(Quat.fromRotationZ(a + rot));
  const h = (H - 2 * SERIF_H) / BLOCKS, parts: any[] = [];
  const foot = at(c, SERIF_H / 2), head = at(c, H - SERIF_H / 2);
  parts.push(<Mesh3d key="foot" name="I-foot" transform={place(foot.x, foot.y, -foot.phi)}><Cuboid half_size={[SERIF_W / 2, SERIF_H / 2, DEPTH / 2 + 0.015]} /><StandardMaterial {...oak(0)} /></Mesh3d>);
  for (let i = 0; i < BLOCKS; i++) {
    const q = at(c, SERIF_H + (i + 0.5) * h);
    parts.push(<Mesh3d key={i} name={`I-${i}`} allowOverlap transform={place(q.x, q.y, -q.phi)}><Cuboid half_size={[STEM / 2, h * 0.48, DEPTH / 2]} /><StandardMaterial {...oak(i + 1)} /></Mesh3d>);
  }
  const k = (H - 2 * SERIF_H) / CORE;
  for (let i = 0; i < CORE; i++) {
    const q = at(c, SERIF_H + (i + 0.5) * k);
    parts.push(<Mesh3d key={`c${i}`} name={`I-core-${i}`} allowOverlap transform={place(q.x, q.y, -q.phi)}><Cuboid half_size={[STEM * 0.3, k * 0.62, DEPTH * 0.3]} /><StandardMaterial base_color="#3b2a1d" perceptual_roughness={0.9} /></Mesh3d>);
  }
  parts.push(<Mesh3d key="head" name="I-head" transform={place(head.x, head.y, -head.phi)}><Cuboid half_size={[SERIF_W / 2, SERIF_H / 2, DEPTH / 2 + 0.015]} /><StandardMaterial {...oak(1)} /></Mesh3d>);
  return <>{parts}</>;
}
const BAR = 0.04;                                   // half the thickness of the bar the two iron letters are cast on: it makes them one thing
function It({ x, y, tip = 0 }: { x: number; y: number; tip?: number }) {
  const d = IT_HALF + BAR, q = Quat.fromRotationZ(tip);
  return (
    <>
      <Mesh3d name="IT" transform={Transform.fromXyz(x, y, 0).withRotation(q)}>
        <Text3D size={IT_SIZE} depth={0.5}>IT</Text3D>
        <Iron />
      </Mesh3d>
      <Mesh3d name="IT-bar" allowOverlap transform={Transform.fromXyz(x + Math.sin(tip) * d, y - Math.cos(tip) * d, 0).withRotation(q)}>
        <Cuboid half_size={[IT_W2, BAR, 0.25]} />
        <Iron />
      </Mesh3d>
    </>
  );
}

// ---- the performance. Every value comes from the frame. Times in seconds.
const FPS = 30, DUR = 399;
const T = {
  act: 2.6, bend: 3.0, set: 4.5,                // it gathers; it bows from the waist, slowly; the iron is on the floor
  free: 4.9, shape: 6.0,                        // it takes its head away; it is back in the old shape, out of habit
  sway: 6.1, back: 7.9, flat: 8.95,             // it goes over, toward the iron, and hangs past the point it should come back from; it throws its head back and comes back; the foot slaps flat
  low: 10.0, rise: 10.15, up: 11.9,             // it stands, on purpose, in one shot
};
type K = [number, number, ("s" | "o" | "i")?];
function keys(t: number, ks: K[]): number {
  if (t <= ks[0][0]) return ks[0][1];
  for (let i = 1; i < ks.length; i++) if (t < ks[i][0]) {
    const u = (t - ks[i - 1][0]) / (ks[i][0] - ks[i - 1][0]), e = ks[i][2] ?? "s";
    const w = e === "o" ? 1 - Math.pow(1 - u, 2.6) : e === "i" ? u * u : u * u * (3 - 2 * u);
    return ks[i - 1][1] + (ks[i][1] - ks[i - 1][1]) * w;
  }
  return ks[ks.length - 1][1];
}
// Setting the iron down: with stoop 10, bow BOW and nod NOD its head is level with the floor's rise of half the iron's width and
// its face is upright, so the iron, still on its head, lies exactly on its side on the floor. (Solved outside; see READINGS.)
const BOW = 1.81, NOD = -0.33;
const LEVEL: K[] = [[0, 34], [1.4, 58, "o"], [2.3, 60], [T.act, 60], [T.bend, 64], [T.set, 10], [T.free, 10], [T.shape, 56],
  [T.back, 56], [T.back + 0.4, 44, "o"], [T.flat, 50], [T.flat + 0.35, 48], [T.flat + 0.75, 52], [T.rise, 52], [T.up, 0]];
const BOWK: K[] = [[T.bend, 0], [T.set, BOW], [T.free, BOW], [T.shape, 0]];
const NODK: K[] = [[T.bend, 0], [T.set, NOD], [T.free, NOD], [T.shape, 0]];
const levelAt = (t: number) => keys(t, LEVEL), bowAt = (t: number) => keys(t, BOWK), nodAt = (t: number) => keys(t, NODK);
function tipAt(t: number): number {
  const sw = t - T.sway;
  if (sw <= 0) return 0;
  if (sw < 1.1) return 0.46 * (1 - Math.pow(1 - sw / 1.1, 2));
  if (t < T.back) return 0.46 + 0.014 * Math.sin((sw - 1.1) * 21);
  if (t < T.flat) { const u = clamp01(((t - T.back) / (T.flat - T.back) - 0.2) / 0.8); return 0.46 * (1 - Math.pow(u, 1.8)); }   // the head goes back first, then the whole letter follows
  if (t < T.flat + 0.45) return -0.05 * Math.sin(((t - T.flat) / 0.45) * Math.PI);
  if (t < T.flat + 0.75) return 0.015 * Math.sin(((t - T.flat - 0.45) / 0.3) * Math.PI);
  return 0;
}

/** where the iron is while it rides on the head */
function restOn(level: number, nod: number, bow: number) {
  const top = topOf(level, nod, bow);
  const d = IT_HALF + 2 * BAR;                       // the letters' middle, above the bar that sits on the head
  return { x: IX + top.x + Math.sin(top.tip) * d, y: top.y + Math.cos(top.tip) * d, tip: -top.tip };
}
const DOWN = restOn(10, NOD, BOW);                  // where it is set down
function itAt(t: number) {
  if (t <= T.set) return restOn(levelAt(t), nodAt(t), bowAt(t));
  const h = t - T.set;                             // on the floor, on its side: one small rock as the weight comes off the head, then still
  return { x: DOWN.x, y: IT_W2, tip: -Math.PI / 2 + 0.02 * Math.exp(-h * 8) * Math.sin(h * 26) };
}

// Four shots. A cut is a change of what matters.
type V3 = [number, number, number];
function shotAt(t: number, shake: number): { p: V3; at: V3; focus: number; ap: number } {
  const span = (a: number, b: number) => clamp01((t - a) / (b - a));
  if (t < T.act) { const u = span(0, T.act); return { p: [-0.15, 1.42, 7.2 - 0.6 * u], at: [-0.05, 1.3, 0], focus: 7.0, ap: 2.2 }; }
  if (t < T.sway) { const u = span(T.act, T.sway); return { p: [0.95 - 0.1 * u, 1.0 + shake, 5.3 - 0.25 * u], at: [0.12, 1.05 + shake * 0.5, 0], focus: 5.3, ap: 2.4 }; }
  if (t < T.low) { const u = span(T.sway, T.low); return { p: [-0.75 + 0.15 * u, 0.45 + shake, 5.75 - 0.3 * u], at: [-0.15, 1.02, 0], focus: 5.8, ap: 2.5 }; }
  const u = span(T.low, T.low + 3.3);
  return { p: [1.8 - 0.15 * u, 0.6, 5.7 - 0.2 * u], at: [-0.6, 1.1, 0], focus: 6.0, ap: 2.2 };
}

// The words are on the wall of the room and they do what the letter does. They arrive a word at a time, each set down with a
// little weight. The opening lines sag while it carries. "down." comes down with the iron, as slowly, and lands with it.
// "I didn't fall." arrives while it hangs, tipped as far as the I is, and comes level with it. The last line starts as
// bowed as the I and straightens as it stands.
const WALL = -1.58;
const say = { font: "Georgia", color: "#fffaf0", emissive: "#fffaf0", emissiveIntensity: 4.5, roughness: 1 };
const sagOf = (g: { index: number; count: number }, level: number, amount: number) => {
  const u = Math.pow(g.index / Math.max(1, g.count - 1), 1.6) * (level / LEVELS);
  return { y: -amount * u, r: -0.55 * u };
};

function Film() {
  const f = useCurrentFrame(), t = f / FPS;
  const level = levelAt(t), nod = nodAt(t), bow = bowAt(t);
  // under the weight it shakes, and hardest while it lowers it
  const strain = t < T.set ? Math.sin(t * 57) * (0.005 + 0.003 * smooth(t / 2) + 0.006 * smooth((t - T.bend) / 0.5)) : 0;
  // standing up carries a little too far, and settles
  const back = t > T.up - 0.25 && t < T.up + 0.9 ? -0.03 * Math.sin(clamp01((t - (T.up - 0.25)) / 1.15) * Math.PI) : 0;
  const it = itAt(t);
  const hit = t - T.set, land2 = t - T.flat;
  const shake = (hit > 0 && hit < 0.4 ? 0.02 * Math.exp(-hit * 12) * Math.cos(hit * 70) : 0) + (land2 > 0 && land2 < 0.3 ? 0.006 * Math.exp(-land2 * 14) * Math.cos(land2 * 70) : 0);
  const s = shotAt(t, shake);
  const tip = tipAt(t);

  /** a line set down a word at a time from `a`, gone by `b`; `move` adds each glyph's own motion */
  const line = (key: string, a: number, b: number, x: number, y: number, text: string, size: number, move?: (g: any) => { x?: number; y?: number; r?: number; o?: number }, each = 0.11) =>
    t >= a && t <= b ? (
      <RichText key={key} {...say} size={size} name={key} position={[x, y, WALL]} align="left"
        glyph={(g: any) => {
          const w = clamp01((t - a - g.word * each) / 0.2), m = move ? move(g) : {};
          return { opacity: (m.o ?? 1) * clamp01(w * 1.8) * clamp01((b - t) / 0.25), position: [m.x ?? 0, (m.y ?? 0) + 0.07 * Math.pow(1 - w, 2), 0] as V3, rotation: [0, 0, m.r ?? 0] as V3 };
        }}>{text}</RichText>
    ) : null;
  const carried = (g: any) => sagOf(g, level, 0.2);
  const lower = 1 - smooth((t - T.bend) / (T.set - T.bend));   // 1 while the iron is up, 0 when it is down
  return (
    <AbsoluteFill style={{ background: "#0b0a09" }}>
      <Camera3d transform={Transform.fromXyz(s.p[0], s.p[1], s.p[2]).lookingAt(s.at)} projection={{ Perspective: { fov: (34 * Math.PI) / 180 } }}>
        <DepthOfField focal_distance={s.focus} aperture_f_stops={s.ap} />
      </Camera3d>
      <Grade vignette={0.24} />
      <Room>
        <Letter level={level} nod={nod} bow={bow} tip={tip + strain + back} />
        <It x={it.x} y={it.y} tip={it.tip} />
        {t < T.act ? <>
          {line("carried1", -1.0, T.act - 0.04, -4.45, 3.05, "I carried it", 0.34, carried)}
          {line("carried2", 0.35, T.act - 0.04, -4.45, 2.63, "so long", 0.34, carried)}
          {line("carried3", 0.8, T.act - 0.04, -4.45, 2.21, "I thought it was", 0.34, carried)}
          {line("carried4", 1.3, T.act - 0.04, -4.45, 1.79, "my shape.", 0.34, carried)}
        </> : null}
        {t >= T.act && t < T.sway ? <>
          {line("put", T.bend + 0.1, T.sway - 0.08, -3.05, 2.5, "I put it", 0.36)}
          {line("down", T.bend + 0.5, T.sway - 0.08, -3.05, 2.06, "down.", 0.36, () => ({ x: 1.42 * lower, y: 0.44 * lower + shake * 2 }))}
        </> : null}
        {t >= T.sway + 1.1 && t < T.low ? (
          <RichText {...say} size={0.32} name="fall" position={[-1.72, 2.1, WALL]} rotation={[0, 0, -tip * 0.62]} align="right"
            glyph={(g: any) => { const w = clamp01((t - T.sway - 1.1 - g.word * 0.14) / 0.2); return { opacity: clamp01(w * 1.8) }; }}>I didn't fall.</RichText>
        ) : null}
        {t >= T.low ? line("stood", T.rise + 0.1, 99, -4.75, 3.0, "I just stood up.", 0.34, (g: any) => sagOf(g, level, 0.26), 0.3) : null}
      </Room>
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <svg style={{ position: "absolute", left: 0, top: 0, mixBlendMode: "overlay", opacity: 0.32 }} width="1920" height="1080">
          <filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={String(f + 1)} /><feColorMatrix type="saturate" values="0" /></filter>
          <rect width="1920" height="1080" filter="url(#g)" />
        </svg>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "#000", opacity: clamp01((t - (DUR / FPS - 0.45)) / 0.45) }} />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="film" component={Film} width={1920} height={1080} fps={FPS} durationInFrames={DUR} />);
