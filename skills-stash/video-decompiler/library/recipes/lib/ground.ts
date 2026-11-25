// Shared by the proofs that need a real ground: the height-field recipe, proved in an earlier study.
import { staticFile } from "raea";
import { Affine2 } from "raea/math";

const hash = (x: number, z: number) => { const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453; return s - Math.floor(s); };
const smooth = (t: number) => t * t * (3 - 2 * t);
export function noise(x: number, z: number) {
  const xi = Math.floor(x), zi = Math.floor(z), xf = smooth(x - xi), zf = smooth(z - zi);
  const a = hash(xi, zi), b = hash(xi + 1, zi), c = hash(xi, zi + 1), d = hash(xi + 1, zi + 1);
  return a + (b - a) * xf + (c - a) * zf + (a - b - c + d) * xf * zf;
}
/** a seeded stream for scatters that hold still */
export function seeded(seed: number) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

/** gentle forest floor: small hummocks underfoot, hills beyond `calm` metres from (cx, cz) */
export function makeHeight(o: { amp?: number; calm?: number; cx?: number; cz?: number; small?: number } = {}) {
  const amp = o.amp ?? 10, calm = o.calm ?? 20, cx = o.cx ?? 0, cz = o.cz ?? 0, small = o.small ?? 0.25;
  const hills = (x: number, z: number) => {
    let h = 0, a = amp, f = 1 / 70;
    for (let k = 0; k < 5; k++) { h += a * (noise(x * f, z * f) - 0.5); a *= 0.45; f *= 2.1; }
    return h;
  };
  const h0 = hills(cx, cz);
  return (x: number, z: number) => {
    const t = Math.min(1, Math.hypot(x - cx, z - cz) / calm), w = t * t * (3 - 2 * t); // smooth: no kink
    const hum = small * (noise(x * 0.9 + 7, z * 0.9) - 0.5) + small * 0.5 * (noise(x * 2.3, z * 2.3 + 3) - 0.5);
    return h0 + (hills(x, z) - h0) * w + hum;
  };
}

export function buildGround(height: (x: number, z: number) => number, o: { N?: number; S?: number; cx?: number; cz?: number; exp?: number } = {}) {
  const N = o.N ?? 200, S = o.S ?? 400, cx = o.cx ?? 0, cz = o.cz ?? 0, exp = o.exp ?? 2.2;
  const positions: number[] = [], normals: number[] = [], uvs: number[] = [], indices: number[] = [], colors: number[] = [];
  const warp = (t: number) => Math.sign(t) * Math.pow(Math.abs(t), exp) * S;
  for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) {
    const x = cx + warp(i / N * 2 - 1), z = cz + warp(j / N * 2 - 1), y = height(x, z), e = 0.1;
    const nx = height(x - e, z) - height(x + e, z), nz = height(x, z - e) - height(x, z + e), ny = 2 * e;
    const l = Math.hypot(nx, ny, nz);
    positions.push(x, y, z); normals.push(nx / l, ny / l, nz / l);
    uvs.push((x - cx + S) / (2 * S), (z - cz + S) / (2 * S)); // 0..1: a BufferMesh's UVs clamp outside it
    const m = noise(x / 23 + 50, z / 23), g = noise(x / 9 - 20, z / 9);
    colors.push(0.55 + 0.45 * m, 0.55 + 0.42 * m + 0.08 * g, 0.5 + 0.38 * m, 1);
  }
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const a = j * (N + 1) + i, b = a + 1, c = a + N + 1, d = c + 1;
    indices.push(a, c, b, b, c, d);
  }
  return { mesh: { positions, normals, uvs, indices, colors }, tiles: (2 * S) / 3.15 };
}

/** Poly Haven forest_ground_04 (3.15 m a repeat), with its tiling for a ground of half-size S */
export function forestFloor(tiles: number, tint = "#ffffff") {
  return {
    base_color: tint,
    base_color_texture: staticFile("forest_ground_04/forest_ground_04_diff_2k.jpg"),
    normal_map_texture: staticFile("forest_ground_04/forest_ground_04_nor_gl_2k.jpg"),
    metallic_roughness_texture: staticFile("forest_ground_04/forest_ground_04_arm_2k.jpg"),
    occlusion_texture: staticFile("forest_ground_04/forest_ground_04_arm_2k.jpg"),
    perceptual_roughness: 1,
    metallic: 1,
    uv_transform: Affine2.fromScale([tiles, tiles]),
  };
}

/** a texture set from Poly Haven's naming (diff / nor_gl / arm), tiled */
export function phSet(id: string, res: "1k" | "2k", tile: [number, number] = [1, 1], extra: object = {}) {
  return {
    base_color_texture: staticFile(`${id}/${id}_diff_${res}.jpg`),
    normal_map_texture: staticFile(`${id}/${id}_nor_gl_${res}.jpg`),
    metallic_roughness_texture: staticFile(`${id}/${id}_arm_${res}.jpg`),
    occlusion_texture: staticFile(`${id}/${id}_arm_${res}.jpg`),
    perceptual_roughness: 1,
    metallic: 1,
    uv_transform: Affine2.fromScale(tile),
    ...extra,
  };
}
