// Flat artwork as layers in real 3D, the way After Effects layers work: inline SVG inside <Screen>. Measured on raea
// 0.1.1-rc4 (from an inventory of what raea draws): paths, gradients, clip, mask, blur and drop shadow, and type (then
// Windows's Georgia, Bahnschrift and Consolas; now the embedded Inter and JetBrains Mono) all draw; colours stay true (#ff7a1a read back #ff7a1a); depth of field blurs by depth and the
// near layer hides the far one; the art redraws every frame (the clock hand, the eye) with no work-round; motion blur
// works. 57-84 ms a frame for two 1200x800 layers with DOF and motion blur. screen-art.tsx is the artwork.
import { AbsoluteFill, Composition, Easing, interpolate, registerRoot, useCurrentFrame } from "raea";
import { DepthOfField, MotionBlur, Screen, ToneMapping } from "raea/3d";
import { Transform } from "raea/transform";
import { Camera3d } from "raea/camera";
import { H, SvgArt, W } from "./screen-art";

const FOV = (40 * Math.PI) / 180;

function Layer({ f, x, y, z, turn, name }: { f: number; x: number; y: number; z: number; turn: number; name: string }) {
  return (
    <Screen name={name} crt={false} resolution={[W, H]} size={[1.2]} position={[x, y, z]} rotation={[0, turn, 0]}>
      <div style={{ width: W, height: H }}><SvgArt f={f} /></div>
    </Screen>
  );
}

function Shot() {
  const f = useCurrentFrame();
  const truck = interpolate(f, [15, 29], [0, 0.7], { easing: Easing.in(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const a = (50 * Math.PI) / 180, dist = 1.35;
  return (
    <AbsoluteFill style={{ background: "#202020" }}>
      <Camera3d transform={Transform.fromXyz(Math.sin(a) * dist + truck, 0.05, Math.cos(a) * dist).lookingAt([truck * 0.6, 0, -0.3])} projection={{ Perspective: { fov: FOV } }}>
        <DepthOfField focal_distance={dist} aperture_f_stops={1.4} />
      </Camera3d>
      <MotionBlur shutterAngle={0.5} samples={8} />
      <ToneMapping mode="none" />
      <Layer f={f} x={-0.3} y={0.1} z={-2.3} turn={0.6} name="far" />
      <Layer f={f} x={0} y={0} z={0} turn={0} name="near" />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="screen-layer" component={Shot} width={1920} height={1080} fps={30} durationInFrames={30} />);
