// G: a word and a simple logo given thickness, lit from one side, casting a shadow on a ground. Text3D (solid letters)
// and a logo mark extruded from an outline (a wave in a ring), a low raking key light from the left with soft
// shadows, a plain ground that catches them, a slow push and turn.
import { AbsoluteFill, Composition, Easing, interpolate, registerRoot, useCurrentFrame } from "raea";
import { AmbientOcclusion, Shadows, Text3D, ToneMapping, crossSection } from "raea/3d";
import { StandardMaterial } from "raea/pbr";
import { Cuboid, Mesh3d } from "raea/mesh";
import { AmbientLight, DirectionalLight } from "raea/light";
import { Quat, Transform } from "raea/transform";
import { Camera3d } from "raea/camera";

// the logo: a ring with a wave cut through it, extruded 0.18 m and stood up
const LOGO = (() => {
  const circ = (r: number, n = 96) => Array.from({ length: n }, (_, i) => [r * Math.cos((i / n) * 2 * Math.PI), r * Math.sin((i / n) * 2 * Math.PI)] as [number, number]);
  const ring = crossSection.polygon(circ(0.5)).minus(crossSection.polygon(circ(0.38)));
  const wave: [number, number][] = [];
  // counter-clockwise (lower edge left->right, then upper edge back): the clockwise version came out empty, silently
  for (let i = 0; i <= 40; i++) { const x = -0.42 + (0.84 * i) / 40; wave.push([x, 0.07 * Math.sin((i / 40) * 2 * Math.PI) - 0.07]); }
  for (let i = 40; i >= 0; i--) { const x = -0.42 + (0.84 * i) / 40; wave.push([x, 0.07 * Math.sin((i / 40) * 2 * Math.PI) + 0.04]); }
  return ring.union(crossSection.polygon(wave).intersect(crossSection.polygon(circ(0.4)))).extrude(0.18).move(0, 0, -0.09);
})();

const ease = (f: number, a: number, b: number, from: number, to: number) =>
  interpolate(f, [a, b], [from, to], { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });

function Shot() {
  const f = useCurrentFrame();
  const z = ease(f, 0, 59, 6.2, 5.4), yaw = ease(f, 0, 59, 0.22, -0.1);
  return (
    <AbsoluteFill style={{ background: "#c9c2b6" }}>
      <Camera3d transform={Transform.fromXyz(0.4, 2.3, z).lookingAt([0.1, 0.25, 0])} projection={{ Perspective: { fov: (32 * Math.PI) / 180 } }} />
      <ToneMapping mode="agx" />
      <Shadows distance={14} firstCascade={6} mapSize={4096} />
      <AmbientLight brightness={260} color="#e8eefc" />
      <AmbientOcclusion quality="high" />
      <DirectionalLight transform={Transform.fromXyz(-6, 2.6, 1.5).lookingAt([0, 0, 0])} illuminance={14000} color="#ffe7cc" shadow_maps_enabled soft_shadow_size={0.6} />
      <Mesh3d name="ground" transform={Transform.fromXyz(0, -0.05, 0)}><Cuboid half_size={[30, 0.05, 30]} /><StandardMaterial base_color="#c9c2b6" perceptual_roughness={0.9} /></Mesh3d>
      <Mesh3d name="logo" shape={LOGO} transform={Transform.fromXyz(-1.95, 0.5, 0).withRotation(Quat.fromRotationY(yaw))}>
        <StandardMaterial base_color="#1f7a8c" perceptual_roughness={0.35} />
      </Mesh3d>
      <Mesh3d name="word" transform={Transform.fromXyz(0.95, 0.3, 0).withRotation(Quat.fromRotationY(yaw))}>
        <Text3D size={0.62} depth={0.22}>Tidewater</Text3D>
        <StandardMaterial base_color="#f4f1ea" perceptual_roughness={0.45} />
      </Mesh3d>
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="G" component={Shot} width={1920} height={1080} fps={30} durationInFrames={60} />);
