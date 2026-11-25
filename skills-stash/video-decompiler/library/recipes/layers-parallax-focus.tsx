// B: four flat layers at different depths; the camera trucks and pushes (parallax) while focus is pulled from the
// nearest layer to the farthest. Each layer is a transparent PNG on an unlit Plane3d sized to fill the view at its depth.
import { AbsoluteFill, Composition, Easing, interpolate, registerRoot, staticFile, useCurrentFrame } from "raea";
import { DepthOfField, ToneMapping } from "raea/3d";
import { StandardMaterial } from "raea/pbr";
import { Mesh3d, Plane3d } from "raea/mesh";
import { Transform } from "raea/transform";
import { Camera3d } from "raea/camera";

const ease = (f: number, a: number, b: number, from: number, to: number) =>
  interpolate(f, [a, b], [from, to], { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const FOV = 40;
const LAYERS = [ // nearest first: z of the layer, its picture
  { z: -1.2, src: "layer1.png" }, { z: -2.4, src: "layer2.png" }, { z: -3.8, src: "layer3.png" }, { z: -5.6, src: "layer4.png" },
];
const half = (d: number) => Math.tan((FOV * Math.PI) / 360) * d * 1.15; // half height that fills the view, plus room to move

function Shot() {
  const f = useCurrentFrame();
  const cx = ease(f, 0, 59, -0.32, 0.32), cz = ease(f, 0, 59, 0.0, -0.35);
  const eye: [number, number, number] = [cx, 0, cz];
  const focus = ease(f, 8, 52, 1.2 - cz, 5.6 + cz) ; // distance from the camera to the nearest, then the farthest layer
  return (
    <AbsoluteFill style={{ background: "#eef2f1" }}>
      <Camera3d transform={Transform.fromXyz(...eye).lookingAt([cx * 0.4, 0, -6])} projection={{ Perspective: { fov: (FOV * Math.PI) / 180 } }}>
        <DepthOfField focal_distance={focus} aperture_f_stops={0.6} />
      </Camera3d>
      <ToneMapping mode="none" />
      {LAYERS.map((l, i) => (
        <Mesh3d key={l.src} name={`layer${i}`} transform={Transform.fromXyz(0, 0, l.z)}>
          <Plane3d normal={[0, 0, 1]} half_size={[half(-l.z) * 16 / 9, half(-l.z)]} />
          <StandardMaterial base_color_texture={staticFile(l.src)} unlit alpha_mode={{ Mask: 0.5 }} />
        </Mesh3d>
      ))}
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="B" component={Shot} width={1920} height={1080} fps={30} durationInFrames={60} />);
