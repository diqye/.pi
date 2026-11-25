// One piece of flat artwork, written once as a tree, drawn two ways: as inline SVG elements on the page (svgJsx) and
// as an SVG data URL a 3D texture can take (svgUrl). Everything that changes with time is a function of the frame:
// the clock's minute hand turns 6 degrees a frame, the eye opens and closes on a 30-frame cycle. Its type is Inter and
// JetBrains Mono, embedded (../lib/faces.ts, the page library's) so it draws on any machine; drawn as a texture
// (svgUrl), an SVG picture can't load the page's faces, so keep words on the inline route.
import { FACES } from "../lib/faces";

type Node = [string, Record<string, string | number>, ...(Node | string)[]];
const h = (tag: string, attrs: Record<string, string | number>, ...kids: (Node | string)[]): Node => [tag, attrs, ...kids];

export const W = 1200, H = 800;

export function tree(f: number): Node {
  const minute = (f * 6) % 360;
  const hour = 300 + f * 0.5;
  const open = 0.5 + 0.5 * Math.cos((2 * Math.PI * f) / 30); // 1 = open, 0 = shut
  const eyeRy = 1 + 13 * open;
  const ticks: Node[] = [];
  for (let i = 0; i < 12; i++) {
    const a = (i * Math.PI) / 6;
    ticks.push(h("line", { x1: 200 + Math.sin(a) * 62, y1: 560 - Math.cos(a) * 62, x2: 200 + Math.sin(a) * 74, y2: 560 - Math.cos(a) * 74, stroke: "#222222", strokeWidth: i % 3 ? 3 : 7, strokeLinecap: "round" }));
  }
  const houses: Node[] = [];
  for (let i = 0; i < 7; i++) {
    const x = 380 + i * 70, hgt = 70 + ((i * 37) % 60), base = 470;
    houses.push(h("path", { d: `M${x} ${base} L${x} ${base - hgt} L${x + 30} ${base - hgt - 30} L${x + 60} ${base - hgt} L${x + 60} ${base} Z`, fill: i % 2 ? "#3d405b" : "#5b5f97" }));
    houses.push(h("rect", { x: x + 20, y: base - hgt + 18, width: 18, height: 22, fill: "#ffd166" }));
  }
  return h("svg", { xmlns: "http://www.w3.org/2000/svg", width: W, height: H, viewBox: `0 0 ${W} ${H}` },
    h("defs", {},
      h("linearGradient", { id: "sky", x1: 0, y1: 0, x2: 0, y2: 1 }, h("stop", { offset: 0, stopColor: "#1d3557" }), h("stop", { offset: 1, stopColor: "#f4a261" })),
      h("radialGradient", { id: "sun", cx: 0.5, cy: 0.5, r: 0.5 }, h("stop", { offset: 0, stopColor: "#fff3b0" }), h("stop", { offset: 0.6, stopColor: "#ffd166" }), h("stop", { offset: 1, stopColor: "#ffd166", stopOpacity: 0 })),
      h("clipPath", { id: "round" }, h("circle", { cx: 590, cy: 400, r: 170 })),
      h("linearGradient", { id: "fadeg", x1: 0, y1: 0, x2: 1, y2: 0 }, h("stop", { offset: 0, stopColor: "#ffffff" }), h("stop", { offset: 1, stopColor: "#000000" })),
      h("mask", { id: "fade" }, h("rect", { x: 0, y: 470, width: W, height: 330, fill: "url(#fadeg)" })),
      h("filter", { id: "soft", x: -0.5, y: -0.5, width: 2, height: 2 }, h("feGaussianBlur", { stdDeviation: 10 })),
      h("filter", { id: "drop", x: -0.5, y: -0.5, width: 2, height: 2 }, h("feDropShadow", { dx: 8, dy: 12, stdDeviation: 6, floodColor: "#000000", floodOpacity: 0.6 })),
    ),
    // sky (linear gradient) and sun (radial gradient)
    h("rect", { x: 0, y: 0, width: W, height: H, fill: "url(#sky)" }),
    h("circle", { cx: 860, cy: 250, r: 150, fill: "url(#sun)" }),
    // clouds: blurred ellipses (feGaussianBlur)
    h("g", { filter: "url(#soft)" }, h("ellipse", { cx: 300, cy: 150, rx: 140, ry: 40, fill: "#ffffff" }), h("ellipse", { cx: 420, cy: 120, rx: 90, ry: 35, fill: "#ffffff" })),
    // a small town seen through a round window (clipPath)
    h("g", { clipPath: "url(#round)" }, h("rect", { x: 380, y: 230, width: 420, height: 340, fill: "#a8dadc" }), ...houses),
    h("circle", { cx: 590, cy: 400, r: 170, fill: "none", stroke: "#1d1d1b", strokeWidth: 8 }),
    // a hill under a left-to-right fade (mask)
    h("path", { d: "M0 800 L0 560 Q300 470 600 560 T1200 540 L1200 800 Z", fill: "#2a9d8f", mask: "url(#fade)" }),
    // the clock: a dial with a drop shadow (feDropShadow), ticks, two hands that turn with the frame
    h("circle", { cx: 200, cy: 560, r: 90, fill: "#fdfcf7", filter: "url(#drop)" }),
    ...ticks,
    h("line", { x1: 200, y1: 560, x2: 200 + Math.sin((hour * Math.PI) / 180) * 42, y2: 560 - Math.cos((hour * Math.PI) / 180) * 42, stroke: "#1d1d1b", strokeWidth: 9, strokeLinecap: "round" }),
    h("line", { x1: 200, y1: 560, x2: 200 + Math.sin((minute * Math.PI) / 180) * 66, y2: 560 - Math.cos((minute * Math.PI) / 180) * 66, stroke: "#c1121f", strokeWidth: 5, strokeLinecap: "round" }),
    h("circle", { cx: 200, cy: 560, r: 7, fill: "#1d1d1b" }),
    // a character with a face: head, two eyes that blink with the frame, a mouth (quadratic curve), a body
    h("path", { d: "M940 800 Q940 640 1010 630 Q1080 640 1080 800 Z", fill: "#e76f51" }),
    h("circle", { cx: 1010, cy: 560, r: 70, fill: "#f2c9a0", stroke: "#1d1d1b", strokeWidth: 4 }),
    h("ellipse", { cx: 985, cy: 548, rx: 10, ry: eyeRy, fill: "#1d1d1b" }),
    h("ellipse", { cx: 1035, cy: 548, rx: 10, ry: eyeRy, fill: "#1d1d1b" }),
    h("path", { d: "M985 590 Q1010 612 1035 590", fill: "none", stroke: "#1d1d1b", strokeWidth: 5, strokeLinecap: "round" }),
    // type in three Windows faces
    h("text", { x: 60, y: 120, fontFamily: "Georgia", fontSize: 110, fontWeight: 700, fill: "#fdfcf7" }, "Tidewater"),
    h("text", { x: 64, y: 190, fontFamily: "Inter", fontWeight: 600, fontSize: 48, fill: "#fdfcf7" }, "OPEN 06:00 INTER"),
    h("text", { x: 64, y: 250, fontFamily: "JetBrains Mono", fontSize: 40, fill: "#fdfcf7" }, "x = 4.20 m  mono"),
    // colour swatches to read back: orange, black, white (flat fills, nothing over them)
    h("rect", { x: 1040, y: 30, width: 130, height: 130, fill: "#ff7a1a" }),
    h("rect", { x: 1040, y: 170, width: 60, height: 60, fill: "#000000" }),
    h("rect", { x: 1110, y: 170, width: 60, height: 60, fill: "#ffffff" }),
  );
}

// SVG's own camelCase attribute names; every other camelCase prop is written kebab-case in the markup
const KEEP = new Set(["viewBox", "stdDeviation", "gradientUnits", "maskUnits", "clipPathUnits", "preserveAspectRatio"]);
const attr = (k: string) => (KEEP.has(k) ? k : k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()));
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

function markup(n: Node | string): string {
  if (typeof n === "string") return esc(n);
  const [tag, attrs, ...kids] = n;
  const a = Object.entries(attrs).map(([k, v]) => ` ${attr(k)}="${esc(String(v))}"`).join("");
  return `<${tag}${a}>${kids.map(markup).join("")}</${tag}>`;
}

let k = 0;
function jsx(n: Node | string): any {
  if (typeof n === "string") return n;
  const [tag, attrs, ...kids] = n;
  const { xmlns, ...props } = attrs;
  const Tag = tag as any;
  return <Tag key={k++} {...props}>{kids.map(jsx)}</Tag>;
}

export const svgString = (f: number) => markup(tree(f));
export const svgUrl = (f: number) => "data:image/svg+xml;utf8," + encodeURIComponent(svgString(f));
export const SvgArt = ({ f }: { f: number }) => <><style>{FACES}</style>{jsx(tree(f))}</>;
