// E: type that glows, and a streak of light that flares. The word is solid Text3D with an emissive face; Bloom spreads
// the glow past the letters (it is a pass over the whole frame, so nothing clips it to a box). The streak is a sphere
// squashed into a long thin needle, its emissive ramped hot for a flare and then settling.
import { AbsoluteFill, Composition, Easing, interpolate, registerRoot, useCurrentFrame } from "raea";
import { Bloom, Sphere, Text3D, ToneMapping } from "raea/3d";
import { LinearRgba, Srgba } from "raea/color";
import { StandardMaterial } from "raea/pbr";
import { Mesh3d } from "raea/mesh";
import { AmbientLight, DirectionalLight } from "raea/light";
import { Quat, Transform } from "raea/transform";
import { Camera3d } from "raea/camera";

const clampI = (f: number, a: number, b: number, from: number, to: number, e = Easing.inOut(Easing.cubic)) =>
  interpolate(f, [a, b], [from, to], { easing: e, extrapolateLeft: "clamp", extrapolateRight: "clamp" });

function Shot() {
  const f = useCurrentFrame();
  const glow = clampI(f, 0, 18, 0, 1, Easing.out(Easing.cubic));
  // the streak: grows along its length (frames 14-26), flares (26-32) and settles
  const len = clampI(f, 14, 28, 0.02, 1.8, Easing.bezier(0.16, 1, 0.3, 1));
  const flare = f < 26 ? 4 : f < 32 ? clampI(f, 26, 30, 4, 160, Easing.out(Easing.cubic)) : clampI(f, 32, 50, 160, 14);
  const fat = f < 26 ? 0.012 : clampI(f, 26, 31, 0.012, 0.05, Easing.out(Easing.cubic)) - clampI(f, 31, 50, 0, 0.025);
  const WHITE = LinearRgba.from(Srgba.hex("#fff3e8"));
  const HOT = LinearRgba.from(Srgba.hex("#ff9a6a"));
  return (
    <AbsoluteFill style={{ background: "#050506" }}>
      <Camera3d transform={Transform.fromXyz(0, 0, 6).lookingAt([0, 0, 0])} projection={{ Perspective: { fov: (34 * Math.PI) / 180 } }} />
      <ToneMapping mode="agx" />
      <Bloom intensity={1.8} threshold={0.5} />
      <AmbientLight brightness={60} />
      <DirectionalLight transform={Transform.fromXyz(-3, 4, 5).lookingAt([0, 0, 0])} illuminance={4000} />
      <Mesh3d name="word" transform={Transform.fromXyz(0, 0.45, 0)}>
        <Text3D size={0.62} depth={0.12}>TIDEWATER</Text3D>
        <StandardMaterial base_color="#d8dde2" perceptual_roughness={0.4} emissive={WHITE.mul(0.05 + 5 * glow)} />
      </Mesh3d>
      <Mesh3d name="streak" transform={Transform.fromXyz(0, -0.55, 0.3).withRotation(Quat.fromRotationZ(0.12)).withScale([len, fat, fat])}>
        <Sphere radius={1} />
        <StandardMaterial base_color="#000000" unlit={false} emissive={HOT.mul(flare)} />
      </Mesh3d>
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="E" component={Shot} width={1920} height={1080} fps={30} durationInFrames={60} />);
