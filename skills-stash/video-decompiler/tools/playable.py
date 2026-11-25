#!/usr/bin/env python3
"""`vd playable` (not proven on a film): a browser page that builds the film's code against a small stand-in for raea,
for scrubbing. It is not the film: raea does not draw it, and nothing compares its frames with the export.

  python playable.py [ENTRY.tsx] [--film DIR] [-o OUT_DIR]

What it does: bundles the film's code with esbuild or bun against a small stand-in for "raea" (AbsoluteFill,
Composition, registerRoot, useCurrentFrame, staticFile), so the page can be played with its sound or scrubbed with the
wheel, with a panel of the film's clock, cues and reader notes. It is not the film: raea does not draw it, parts of the
kit (Freeze in kit/lib/finish.tsx, 3D) do not build, and nothing compares its frames with the export.
"""
import argparse
from html import escape as escape_html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


RAEA_SHIM_TS = """// ~2 KB zero-dependency JSX + raea browser runtime shim for `vd export --playable`
let _currentFrame = 0;
let _fps = 60;
let _width = 1920;
let _height = 1080;
let _durationInFrames = 1800;
let _rootFactory: any = null;
const _compositions: Record<string, any> = {};

export function __setFrame(f: number) { _currentFrame = f; }
export function __getCompositions() { return _compositions; }
export function __getRoot() { return _rootFactory; }

export function useCurrentFrame(): number { return _currentFrame; }
export function useVideoConfig() {
  return { fps: _fps, width: _width, height: _height, durationInFrames: _durationInFrames };
}
export function staticFile(path: string): string {
  const clean = String(path).replace(/^\\/+/, "");
  return clean.startsWith("media/") ? clean : "media/" + clean;
}
export function registerRoot(fn: any) { _rootFactory = fn; }

export function AbsoluteFill(props: any) {
  const style = Object.assign({ position: "absolute", left: 0, top: 0, right: 0, bottom: 0, width: "100%", height: "100%", overflow: "hidden" }, props?.style || {});
  return { __vnode: true, tag: "div", props: Object.assign({}, props, { style, "data-vd-layer": "AbsoluteFill" }) };
}

export function Composition(props: any) {
  if (props && props.id) {
    _compositions[props.id] = props;
    if (!_compositions.__default) {
      _compositions.__default = props;
      _fps = props.fps || 60;
      _width = props.width || 1920;
      _height = props.height || 1080;
      _durationInFrames = props.durationInFrames || 1800;
    }
  }
  return { __vnode: true, tag: "div", props: {} };
}

export function Sequence(props: any) {
  const from = Number(props?.from || 0);
  const dur = props?.durationInFrames != null ? Number(props.durationInFrames) : Infinity;
  if (_currentFrame < from || _currentFrame >= from + dur) return null;
  const saved = _currentFrame;
  _currentFrame = saved - from;
  try {
    const ch = typeof props.children === "function" ? props.children() : props.children;
    return { __vnode: true, tag: "div", props: { style: { position: "absolute", inset: 0 }, children: ch } };
  } finally {
    _currentFrame = saved;
  }
}

export function Audio(_props: any) { return null; }
export function Mix(_props: any) { return null; }
function solveCubicBezier(x1: number, y1: number, x2: number, y2: number, x: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  let u = x;
  for (let i = 0; i < 8; i++) {
    const inv = 1 - u;
    const bx = 3 * inv * inv * u * x1 + 3 * inv * u * u * x2 + u * u * u - x;
    if (Math.abs(bx) < 1e-6) break;
    const dbx = 3 * inv * inv * x1 + 6 * inv * u * (x2 - x1) + 3 * u * u * (1 - x2);
    if (Math.abs(dbx) < 1e-6) break;
    u = Math.max(0, Math.min(1, u - bx / dbx));
  }
  const inv = 1 - u;
  return 3 * inv * inv * u * y1 + 3 * inv * u * u * y2 + u * u * u;
}
export const Easing = {
  linear: (t: number) => t,
  quad: (t: number) => t * t,
  cubic: (t: number) => t * t * t,
  exp: (t: number) => (t <= 0 ? 0 : Math.pow(2, 10 * (t - 1))),
  bezier: (x1: number, y1: number, x2: number, y2: number) => (t: number) => solveCubicBezier(x1, y1, x2, y2, t),
};
"""

JSX_RUNTIME_TS = """// Minimal zero-dependency JSX + React shim returning plain VNodes rendered into the stage DOM
export const Fragment = "__fragment";
export function jsx(tag: any, props: any, key?: any) {
  return { __vnode: true, tag, props: props || {}, key };
}
export const jsxs = jsx;
export const jsxDEV = jsx;
export function createElement(tag: any, props: any, ...children: any[]) {
  const merged = Object.assign({}, props || {});
  if (children.length === 1) merged.children = children[0];
  else if (children.length > 1) merged.children = children;
  return { __vnode: true, tag, props: merged, key: merged.key };
}
export const useMemo = (fn: () => any) => fn();
export const useCallback = (fn: any) => fn;
export const useRef = (init: any) => ({ current: init });
export const useState = (init: any) => [typeof init === "function" ? init() : init, () => {}];
export const useEffect = () => {};
export default { Fragment, createElement, useMemo, useCallback, useRef, useState, useEffect };
"""

BOOT_PLAYER_TS = """// The page's player: play or scrub with the wheel, and a panel of the film's clock, cues and reader notes
import { __setFrame, __getCompositions, __getRoot } from "raea";
import * as EntryMod from "./__vd_entry";

declare const __VD_META__: any;

const SVG_TAGS = new Set(["svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan", "defs", "linearGradient", "radialGradient", "stop", "clipPath", "mask", "filter", "feGaussianBlur", "feColorMatrix", "feOffset", "feBlend", "use"]);
const UNITLESS = new Set(["opacity", "zIndex", "fontWeight", "lineHeight", "flex", "flexGrow", "flexShrink", "order", "zoom", "scale", "strokeOpacity", "fillOpacity", "strokeWidth", "stopOpacity"]);

function applyStyle(el: HTMLElement | SVGElement, style: Record<string, any>) {
  const s = (el as HTMLElement).style;
  for (const k of Object.keys(style)) {
    const v = style[k];
    if (v == null || v === false) continue;
    const cssKey = k.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
    const val = typeof v === "number" && !UNITLESS.has(k) ? v + "px" : String(v);
    s.setProperty(cssKey, val);
  }
}

function renderVNode(node: any, inSvg = false): Node | null {
  if (node == null || node === false || node === true) return null;
  if (Array.isArray(node)) {
    const frag = document.createDocumentFragment();
    for (const item of node) {
      const child = renderVNode(item, inSvg);
      if (child) frag.appendChild(child);
    }
    return frag;
  }
  if (typeof node === "string" || typeof node === "number") {
    return document.createTextNode(String(node));
  }
  if (node.__vnode) {
    if (node.tag === "__fragment") return renderVNode(node.props?.children, inSvg);
    if (typeof node.tag === "function") {
      return renderVNode(node.tag(node.props || {}), inSvg);
    }
    const tag = String(node.tag);
    const isSvg = inSvg || tag === "svg" || SVG_TAGS.has(tag);
    const SVG_CAMEL = new Set(["viewBox", "gradientUnits", "gradientTransform", "clipPathUnits", "preserveAspectRatio",
      "baseFrequency", "numOctaves", "stdDeviation", "stitchTiles", "filterUnits", "primitiveUnits", "patternUnits",
      "patternContentUnits", "patternTransform", "tableValues", "xChannelSelector", "yChannelSelector", "maskUnits",
      "maskContentUnits", "markerWidth", "markerHeight", "markerUnits", "refX", "refY", "pathLength", "spreadMethod",
      "startOffset", "textLength", "lengthAdjust", "kernelMatrix", "kernelUnitLength", "surfaceScale", "specularConstant",
      "specularExponent", "diffuseConstant", "edgeMode", "targetX", "targetY", "preserveAlpha", "limitingConeAngle",
      "pointsAtX", "pointsAtY", "pointsAtZ", "keyTimes", "keySplines", "repeatCount", "attributeName"]);
    const el = isSvg ? document.createElementNS("http://www.w3.org/2000/svg", tag) : document.createElement(tag);
    const props = node.props || {};
    for (const k of Object.keys(props)) {
      if (k === "children" || k === "key" || k === "ref") continue;
      const v = props[k];
      if (v == null || v === false) continue;
      if (k === "style" && typeof v === "object") {
        applyStyle(el, v);
      } else if (k === "className") {
        el.setAttribute("class", String(v));
      } else if (!isSvg && k in el && typeof v !== "string" && typeof v !== "number") {
        (el as any)[k] = v;
      } else {
        // SVG names its own attributes in camelCase; only the presentation ones (strokeWidth) are hyphenated. Made
        // stroke-like, baseFrequency and stdDeviation were dropped, and the starters' grain filter drew nothing
        const attr = SVG_CAMEL.has(k) ? k : k.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
        el.setAttribute(attr, String(v));
      }
    }
    if (props.children != null) {
      const ch = renderVNode(props.children, isSvg);
      if (ch) el.appendChild(ch);
    }
    return el;
  }
  return null;
}

function boot() {
  const meta = __VD_META__;
  const rootFn = __getRoot();
  if (rootFn) {
    try { renderVNode(rootFn()); } catch (_e) {}
  }
  const comps = __getCompositions();
  const comp = comps.film || comps.__default || Object.values(comps)[0];
  const FilmComp = (EntryMod as any).Film || comp?.component;
  const W = Number((EntryMod as any).W || comp?.width || meta.width || 1920);
  const H = Number((EntryMod as any).H || comp?.height || meta.height || 1080);
  const FPS = Number((EntryMod as any).FPS || comp?.fps || meta.fps || 60);
  const FRAMES = Number((EntryMod as any).FRAMES || comp?.durationInFrames || Math.round((meta.duration || 30) * FPS));
  const FB = Number(meta.clock?.FB || 32);

  const stage = document.getElementById("vd-stage")!;
  const scrub = document.getElementById("vd-scrub") as HTMLInputElement;
  const timeLabel = document.getElementById("vd-time")!;
  const playBtn = document.getElementById("vd-play")!;
  const scoreBtn = document.getElementById("vd-score-btn")!;
  const themeBtn = document.getElementById("vd-theme-btn")!;
  const hud = document.getElementById("vd-hud")!;
  const inspector = document.getElementById("vd-inspector")!;
  const audio = document.getElementById("vd-audio") as HTMLAudioElement | null;

  scrub.max = String(FRAMES - 1);
  let frame = 0;
  let playing = false;
  let showScore = true;
  let invertTheme = false;
  let lastWall = performance.now();

  function drawFrame(f: number) {
    frame = Math.max(0, Math.min(FRAMES - 1, f));
    __setFrame(frame);
    stage.innerHTML = "";
    if (FilmComp) {
      const tree = FilmComp({ offset: 0, sub: 1, finish: true });
      const dom = renderVNode(tree);
      if (dom) stage.appendChild(dom);
    }
    stage.style.filter = invertTheme ? "invert(1) hue-rotate(180deg)" : "none";
    scrub.value = String(Math.round(frame));
    const sec = frame / FPS;
    const beat = frame / FB;
    timeLabel.textContent = `${sec.toFixed(2)}s · f${Math.round(frame)}/${FRAMES} · beat ${beat.toFixed(1)}`;
    if (showScore) {
      const esc = (x: any) => String(x).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" } as any)[ch]);
      const activeCues = (meta.cues || []).filter((c: any) => Math.abs(c[1] - sec) < 0.28).map((c: any) => `${esc(c[0])} (${c[1].toFixed(2)}s)`);
      const activeNotes = (meta.notes || []).filter((n: any) => Math.abs(n.t - sec) < 0.6).map((n: any) => esc(n.text));
      hud.innerHTML =
        `<div><b>CLOCK:</b> ${FPS} fps · ${meta.clock?.BPM || 112.5} BPM (${FB} f/beat) · beat <b>${beat.toFixed(2)}</b></div>` +
        `<div><b>ACTIVE CUES:</b> ${activeCues.length ? activeCues.join(" · ") : "—"}</div>` +
        `<div><b>DECOMPILED CHECKS:</b> ${activeNotes.length ? activeNotes.join(" | ") : "clean frame"}</div>`;
    }
  }

  function resizeStage() {
    const wrap = document.getElementById("vd-viewport")!;
    const s = Math.min((wrap.clientWidth - 24) / W, (wrap.clientHeight - 24) / H);
    stage.style.width = W + "px";
    stage.style.height = H + "px";
    stage.style.transform = `scale(${Math.max(0.001, s).toFixed(4)})`;   // a 10% floor cropped the frame in a pane under 216 px (a review's finding)
  }
  window.addEventListener("resize", resizeStage);
  resizeStage();

  playBtn.addEventListener("click", () => {
    playing = !playing;
    playBtn.textContent = playing ? "Pause" : "Play";
    lastWall = performance.now();
    if (audio) {
      if (playing) { audio.currentTime = frame / FPS; audio.play().catch(() => {}); }
      else { audio.pause(); }
    }
  });

  scoreBtn.addEventListener("click", () => {
    showScore = !showScore;
    hud.style.display = showScore ? "block" : "none";
    scoreBtn.classList.toggle("active", showScore);
    drawFrame(frame);
  });

  themeBtn.addEventListener("click", () => {
    invertTheme = !invertTheme;
    themeBtn.classList.toggle("active", invertTheme);
    drawFrame(frame);
  });

  scrub.addEventListener("input", () => {
    playing = false;
    playBtn.textContent = "Play";
    if (audio) audio.pause();
    drawFrame(Number(scrub.value));
  });

  // Scroll wheel scrubs time at sub-frame precision
  window.addEventListener("wheel", (e) => {
    e.preventDefault();
    playing = false;
    playBtn.textContent = "Play";
    if (audio) audio.pause();
    const step = (e.deltaY / 100) * (e.shiftKey ? 0.25 : 2.0);
    drawFrame((frame + step + FRAMES) % FRAMES);
  }, { passive: false });

  // Hover inspector for cards & typography in mid-flight
  stage.addEventListener("mousemove", (e) => {
    const t = e.target as HTMLElement;
    if (!t || t === stage) { inspector.textContent = "Hover any element in mid-flight to inspect live pose & type"; return; }
    const cs = window.getComputedStyle(t);
    const rect = t.getBoundingClientRect();
    const sRect = stage.getBoundingClientRect();
    const scale = sRect.width / W;
    const x = Math.round((rect.left - sRect.left) / scale);
    const y = Math.round((rect.top - sRect.top) / scale);
    const w = Math.round(rect.width / scale);
    const h = Math.round(rect.height / scale);
    const txt = (t.textContent || "").trim().slice(0, 36);
    inspector.textContent = `<${t.tagName.toLowerCase()}> box ${x},${y} ${w}x${h}px · font ${cs.fontFamily.split(",")[0]} ${cs.fontSize} · transform ${cs.transform !== "none" ? cs.transform.slice(0, 48) + "..." : "none"}${txt ? ` · "${txt}"` : ""}`;
  });

  function tick(now: number) {
    if (playing) {
      if (audio && !audio.paused && audio.readyState >= 2) {
        frame = (audio.currentTime * FPS) % FRAMES;
      } else {
        const dt = (now - lastWall) / 1000;
        frame = (frame + dt * FPS) % FRAMES;
      }
      lastWall = now;
      drawFrame(frame);
    }
    requestAnimationFrame(tick);
  }
  drawFrame(0);
  requestAnimationFrame(tick);
}

window.addEventListener("DOMContentLoaded", boot);
"""


def find_esbuild():
    exe = "esbuild.cmd" if os.name == "nt" else "esbuild"
    for candidate in (
        shutil.which("esbuild"),
        str(Path.cwd() / "node_modules" / ".bin" / exe),
        str(Path.home() / ".raea" / "bin" / ("esbuild.exe" if os.name == "nt" else "esbuild")),
    ):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def find_bun():
    for candidate in (shutil.which("bun"), str(Path.home() / ".bun" / "bin" / ("bun.exe" if os.name == "nt" else "bun"))):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def collect_film_meta(film_dir: Path):
    import lean
    s = lean.score_of(film_dir) if (film_dir / "score.json").is_file() else {"fps": 60, "width": 1920, "height": 1080, "duration": 30.0}
    gen = lean.gen_data(film_dir)
    clock = gen.get("CLOCK") or {"FPS": s.get("fps", 60), "FB": 32, "BEATS": 60, "DURATION": s.get("duration", 30.0), "BPM": s.get("bpm", 112.5)}
    cues = gen.get("CUES") or [[e.get("name") or e.get("make") or "cue", float(e.get("at", 0.0))] for e in (s.get("sounds") or [])]
    notes = []
    out_dir = lean.outdir(film_dir)
    for report_file in (out_dir / "scan.txt", out_dir / "look-report.txt", film_dir / "READINGS.md"):
        if report_file.is_file():
            for line in report_file.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.search(r"(\d+\.\d+)\s*s", line)
                if m:
                    notes.append({"t": float(m.group(1)), "text": line.strip()[:90]})
    return {
        "name": film_dir.name,
        "fps": clock.get("FPS") or s.get("fps") or 60,
        "width": s.get("width") or 1920,
        "height": s.get("height") or 1080,
        "duration": clock.get("DURATION") or s.get("duration") or 30.0,
        "clock": clock,
        "times": gen.get("TIMES") or {},
        "cues": cues,
        "notes": notes[:40],
        "has_audio": (film_dir / "media" / "sound.wav").is_file() or (out_dir / "sound.wav").is_file(),
    }


def build_playable(film_dir: Path, entry: Path = None, out_dir: Path = None):
    """Compile `film_dir` into an interactive WebGL/DOM twin in `out_dir` (default: ~/.vd/out/NAME/playable)."""
    import lean
    film_dir = Path(film_dir).resolve()
    entry = Path(entry).resolve() if entry else lean.entry_of(film_dir)
    out_dir = Path(out_dir).resolve() if out_dir else (lean.outdir(film_dir) / "playable")
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = collect_film_meta(film_dir)

    esbuild = find_esbuild()
    bun = find_bun()
    if not esbuild and not bun:
        raise SystemExit("vd playable needs esbuild or bun to bundle TSX for the browser (install esbuild via npm or bun from https://bun.sh)")
    bundle_js = out_dir / "bundle.js"
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "work"
        shutil.copytree(film_dir, w, ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".git", "out", "candidates"))
        # Install local zero-dependency raea + react + vd-jsx shims inside node_modules
        raea_mod = w / "node_modules" / "raea"
        jsx_mod = w / "node_modules" / "vd-jsx"
        react_mod = w / "node_modules" / "react"
        raea_mod.mkdir(parents=True, exist_ok=True)
        (jsx_mod / "jsx-runtime").mkdir(parents=True, exist_ok=True)
        (jsx_mod / "jsx-dev-runtime").mkdir(parents=True, exist_ok=True)
        (react_mod / "jsx-runtime").mkdir(parents=True, exist_ok=True)
        (react_mod / "jsx-dev-runtime").mkdir(parents=True, exist_ok=True)
        (raea_mod / "index.ts").write_text(RAEA_SHIM_TS, encoding="utf-8")
        (raea_mod / "package.json").write_text('{"name":"raea","main":"index.ts"}', encoding="utf-8")
        (jsx_mod / "jsx-runtime" / "index.ts").write_text(JSX_RUNTIME_TS, encoding="utf-8")
        (jsx_mod / "jsx-dev-runtime" / "index.ts").write_text(JSX_RUNTIME_TS, encoding="utf-8")
        (jsx_mod / "package.json").write_text('{"name":"vd-jsx","exports":{"./jsx-runtime":"./jsx-runtime/index.ts","./jsx-dev-runtime":"./jsx-dev-runtime/index.ts"}}', encoding="utf-8")
        (react_mod / "index.ts").write_text(JSX_RUNTIME_TS, encoding="utf-8")
        (react_mod / "jsx-runtime" / "index.ts").write_text(JSX_RUNTIME_TS, encoding="utf-8")
        (react_mod / "jsx-dev-runtime" / "index.ts").write_text(JSX_RUNTIME_TS, encoding="utf-8")
        (react_mod / "package.json").write_text('{"name":"react","main":"index.ts","exports":{".":"./index.ts","./jsx-runtime":"./jsx-runtime/index.ts","./jsx-dev-runtime":"./jsx-dev-runtime/index.ts"}}', encoding="utf-8")
        (w / "tsconfig.json").write_text('{"compilerOptions":{"jsx":"react-jsx","jsxImportSource":"vd-jsx"}}', encoding="utf-8")
        rel_entry = "./" + entry.relative_to(film_dir).with_suffix("").as_posix()
        boot_code = f'const __VD_META__ = {json.dumps(meta)};\n' + BOOT_PLAYER_TS.replace("./__vd_entry", rel_entry)
        (w / "__vd_boot.ts").write_text(boot_code, encoding="utf-8")
        if esbuild:
            cmd = [
                esbuild, "__vd_boot.ts", "--bundle", f"--outfile={bundle_js}",
                "--format=iife", "--platform=browser", "--jsx=automatic", "--jsx-import-source=vd-jsx", "--minify",
            ]
        else:
            cmd = [bun, "build", "__vd_boot.ts", "--outfile", str(bundle_js), "--target=browser", "--format=iife", "--minify"]
        p = subprocess.run(
            cmd, cwd=str(w), capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW
        )
        if p.returncode != 0:
            raise SystemExit(f"playable bundle failed:\n{p.stdout}\n{p.stderr}")

    # Copy media assets (art, sound.wav) so staticFile() and WebAudio resolve locally
    if (film_dir / "media").is_dir():
        shutil.copytree(film_dir / "media", out_dir / "media", dirs_exist_ok=True)
    # the page plays the sound the export lays under the picture (lean.film_sound), copied on every build: the film's own
    # media/sound.wav had won, so a film with a voice or a mapped track played its own mix alone (foley with no music),
    # and an earlier rule kept a rebuilt mix from ever reaching a page built before it
    s = lean.score_of(film_dir) if (film_dir / "score.json").is_file() else None
    built_wav = lean.film_sound(film_dir, s)[0] if s else lean.outdir(film_dir) / "sound.wav"
    if built_wav.is_file():
        (out_dir / "media").mkdir(parents=True, exist_ok=True)
        if built_wav.resolve() != (out_dir / "media" / "sound.wav").resolve():
            shutil.copy2(built_wav, out_dir / "media" / "sound.wav")

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape_html(str(meta["name"]))} — a browser imitation of the film, not the film</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #0d0e11; color: #e6edf3; font-family: system-ui, -apple-system, sans-serif; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
  #vd-bar {{ display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #16181d; border-bottom: 1px solid #282c34; font-size: 13px; }}
  button {{ background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; cursor: pointer; font-weight: 600; font-size: 12px; }}
  button.active {{ background: #1f6feb; border-color: #388bfd; }}
  #vd-scrub {{ flex: 1; accent-color: #1f6feb; cursor: pointer; }}
  #vd-viewport {{ flex: 1; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
  #vd-stage {{ flex: none; position: relative; transform-origin: center center; box-shadow: 0 24px 80px rgba(0,0,0,0.65); overflow: hidden; }}
  #vd-hud {{ position: absolute; left: 16px; top: 16px; background: rgba(13, 14, 17, 0.86); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; font-family: ui-monospace, monospace; font-size: 12px; line-height: 1.6; pointer-events: none; backdrop-filter: blur(8px); }}
  #vd-inspector {{ padding: 6px 16px; background: #121418; border-top: 1px solid #282c34; font-family: ui-monospace, monospace; font-size: 12px; color: #8b949e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
</style>
</head>
<body>
  <div id="vd-bar">
    <button id="vd-play">Play</button>
    <input id="vd-scrub" type="range" min="0" max="1800" value="0" />
    <span id="vd-time">0.00s · f0</span>
    <button id="vd-score-btn" class="active">View Decompiled Score</button>
    <button id="vd-theme-btn">Toggle Dark/Light</button>
  </div>
  <div id="vd-viewport">
    <div id="vd-stage"></div>
    <div id="vd-hud"></div>
  </div>
  <div id="vd-inspector">Scroll wheel scrubs time · Hover any card or word in mid-flight to inspect live pose & type</div>
  {"<audio id='vd-audio' src='media/sound.wav' preload='auto' loop></audio>" if (out_dir / "media" / "sound.wav").is_file() else ""}
  <script src="bundle.js"></script>
</body>
</html>
"""
    index_html = out_dir / "index.html"
    index_html.write_text(html, encoding="utf-8")
    return index_html, bundle_js


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("entry", nargs="?", help="optional ENTRY.tsx (default: film folder's film.tsx)")
    ap.add_argument("--film", help="film folder")
    ap.add_argument("-o", dest="out", help="output directory for playable twin (default: ~/.vd/out/NAME/playable)")
    a = ap.parse_args(argv)
    import lean
    d = Path(a.entry).resolve().parent if a.entry else lean.film_dir(a.film, required=True)
    index_html, bundle_js = build_playable(d, Path(a.entry) if a.entry else None, Path(a.out) if a.out else None)
    size_kb = bundle_js.stat().st_size / 1024.0
    print(f"playable twin {index_html} (bundle {bundle_js.name}: {size_kb:.1f} KB, scroll-wheel scrub + View Decompiled Score HUD)")
    print(index_html)


if __name__ == "__main__":
    import utf8  # noqa: F401
    main()
