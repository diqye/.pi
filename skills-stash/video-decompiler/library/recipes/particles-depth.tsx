// I: small particles drifting at different depths (near ones bigger and softer), and one burst from a point at frame 24: 48 sparks thrown out on seeded directions, slowing,
// shrinking and fading. Every particle is its own Mesh3d (Instances are fixed for the shot, so they can't drift).
// Particles are camera-facing sprites (a soft or a hard dot picture, tinted): perspective makes near ones bigger, and
// the sprite's softness follows its distance from the focus plane. Tried first: tiny emissive spheres + DepthOfField;
// Bevy's default DOF mode is hexagonal bokeh (polygons), and "gaussian" smears tiny dots into squares.
import { AbsoluteFill, Composition, registerRoot, staticFile, useCurrentFrame } from "raea";
import { Bloom, Sphere, ToneMapping } from "raea/3d";
import { LinearRgba, Srgba } from "raea/color";
import { StandardMaterial } from "raea/pbr";
import { Mesh3d, Plane3d } from "raea/mesh";
import { Transform } from "raea/transform";
import { Camera3d } from "raea/camera";

function rng(seed: number) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const COLS = ["#ff4f8b", "#36d6c3", "#5b8cff", "#ffb04f", "#ffffff"];
const R = rng(5);
const DUST = Array.from({ length: 140 }, () => ({ x: (R() - 0.5) * 9, y: (R() - 0.5) * 5, z: -R() * 9 + 2.2, vx: (R() - 0.5) * 0.25, vy: 0.05 + R() * 0.15, ph: R() * 6.28, c: Math.floor(R() * 5) }));
const B = rng(9);
const SPARKS = Array.from({ length: 48 }, () => { const a = B() * 2 * Math.PI, e = (B() - 0.5) * 1.2; return { d: [Math.cos(a) * Math.cos(e), Math.sin(e), Math.sin(a) * Math.cos(e)], v: 1.2 + B() * 1.8, c: B() < 0.6 ? 0 : 3 }; });
const BURST_AT = 24, ORIGIN = [0.6, 0.1, 0];

function Shot() {
  const f = useCurrentFrame(), t = f / 30;
  const tb = Math.max(0, (f - BURST_AT) / 30);
  return (
    <AbsoluteFill style={{ background: "#020203" }}>
      <Camera3d transform={Transform.fromXyz(0, 0, 4).lookingAt([0, 0, 0])} projection={{ Perspective: { fov: (40 * Math.PI) / 180 } }} />
      <ToneMapping mode="agx" />
      <Bloom intensity={0.6} threshold={0.7} />
      {DUST.map((p, i) => {
        // thin lens: circle of confusion on screen = K |1/focus - 1/d| px (focus 4 m), turned back into metres at d
        const d = 4 - p.z, coc = 70 * Math.abs(1 / 4 - 1 / d), extra = (coc * d) / 1484;
        const size = 0.02 + extra, soft = coc > 3;
        const keep = Math.min(1, (0.02 / size) ** 2 * 1.6); // a spread dot keeps its light, so it dims
        return (
          <Mesh3d key={i} name={`p${i}`} transform={Transform.fromXyz(p.x + p.vx * t + 0.04 * Math.sin(t * 1.3 + p.ph), p.y + p.vy * t, p.z)}>
            <Plane3d normal={[0, 0, 1]} half_size={[size, size]} />
            <StandardMaterial base_color={Srgba.hex(COLS[p.c]).with_alpha(Math.max(0.18, keep))} base_color_texture={staticFile(soft ? "dot_soft.png" : "dot_hard.png")} unlit alpha_mode="Blend" />
          </Mesh3d>
        );
      })}
      {SPARKS.map((s, i) => {
        // distance travelled with drag: v (1 - e^-k t) / k; size and glow fall with time
        const k = 3.2, dist = (s.v * (1 - Math.exp(-k * tb))) / k, life = Math.max(0, 1 - tb / 0.9);
        const show = f >= BURST_AT && life > 0;
        return (
          <Mesh3d key={`s${i}`} name={`s${i}`} transform={Transform.fromXyz(ORIGIN[0] + s.d[0] * dist, ORIGIN[1] + s.d[1] * dist, ORIGIN[2] + s.d[2] * dist).withScale(show ? Math.max(0.05, life) : 0.0001)}>
            <Sphere radius={0.02} /><StandardMaterial base_color="#000000" emissive={LinearRgba.from(Srgba.hex(COLS[s.c])).mul(show ? 1 + 8 * life : 0)} />
          </Mesh3d>
        );
      })}
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="I" component={Shot} width={1920} height={1080} fps={30} durationInFrames={60} />);
