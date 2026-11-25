// D: a fast spin with real motion blur, landing sharp. Twelve date tiles on a drum; the CAMERA orbits the drum's axis
// (so the drum seems to spin): Bevy's motion blur smears whole-frame camera moves, while a part moving over a still
// background keeps a sharp silhouette. Fast in the middle, lands on 31 and holds.
import { AbsoluteFill, Composition, Easing, interpolate, registerRoot, staticFile, useCurrentFrame } from "raea";
import { Bloom, MotionBlur, ToneMapping } from "raea/3d";
import { StandardMaterial } from "raea/pbr";
import { Cylinder, Mesh3d, Plane3d } from "raea/mesh";
import { Quat, Transform } from "raea/transform";
import { Camera3d } from "raea/camera";

const N = 12, R = 1.3, STEP = (2 * Math.PI) / N;
const DATES = Array.from({ length: N }, (_, i) => 20 + i); // tile i shows date 20 + i, at angle i * STEP

function Shot({ blur }: { blur: boolean }) {
  const f = useCurrentFrame();
  // the camera's angle round the drum: from tile 0 (date 20) one and a bit turns to tile 11 (date 31), out-expo landing
  const turn = interpolate(f, [4, 40], [0, 2 * Math.PI + 11 * STEP], { easing: Easing.bezier(0.6, 0, 0.1, 1), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dist = interpolate(f, [4, 40], [3.6, 2.75], { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const eye: [number, number, number] = [Math.sin(turn) * dist, 0.12, Math.cos(turn) * dist];
  return (
    <AbsoluteFill style={{ background: "#0a0b0c" }}>
      <Camera3d transform={Transform.fromXyz(...eye).lookingAt([Math.sin(turn) * R, 0, Math.cos(turn) * R])} projection={{ Perspective: { fov: (34 * Math.PI) / 180 } }} />
      {blur ? <MotionBlur shutterAngle={1} samples={32} /> : null}
      <ToneMapping mode="none" />
      <Bloom intensity={0.25} threshold={0.9} />
      <Mesh3d name="core"><Cylinder radius={R - 0.04} half_height={0.45} /><StandardMaterial base_color="#141618" unlit /></Mesh3d>
      {DATES.map((d, i) => (
        <Mesh3d key={d} name={`d${d}`} transform={Transform.fromXyz(Math.sin(i * STEP) * R, 0, Math.cos(i * STEP) * R).withRotation(Quat.fromRotationY(i * STEP))}>
          <Plane3d normal={[0, 0, 1]} half_size={[0.32, 0.32]} />
          <StandardMaterial base_color_texture={staticFile(`date${d}.png`)} unlit alpha_mode={{ Mask: 0.5 }} />
        </Mesh3d>
      ))}
    </AbsoluteFill>
  );
}

registerRoot(() => (
  <>
    <Composition id="D" component={() => <Shot blur />} width={1920} height={1080} fps={30} durationInFrames={60} />
    <Composition id="Dsharp" component={() => <Shot blur={false} />} width={1920} height={1080} fps={30} durationInFrames={60} />
  </>
));
