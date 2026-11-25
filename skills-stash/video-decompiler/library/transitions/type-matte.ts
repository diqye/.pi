// Enormous letters are a window onto the next scene, then the camera goes through one of them.
// letter-portal flies through a letter's counter into a flat ground; this one shows the live next scene through the letters' ink.
import { joinFrames } from "../lib/join";

export const meta = {
  name: "type-matte", kind: "transition",
  summary: "enormous letterforms stand up as a window onto the live next scene, then the camera flies through one letter's ink until the next scene fills the frame",
  function: "metaphor and continuity: the word is the way in, so the line and the next scene read as one idea",
  params: {
    dur: { default: 1.5, min: 0.5, max: 5, note: "seconds, the whole join" },
    word: { default: "", note: "the letters; empty takes the longest word of the outgoing headline" },
    role: { default: "display", note: "type role; its face must have outlines (\"glyphs\": true in style.json)" },
    measure: { default: 0.9, min: 0.3, max: 1.2, note: "the word's width, of the frame width" },
    maxSize: { default: 0.86, min: 0.2, max: 1.4, note: "largest letter size, of the frame height" },
    letter: { default: -1, min: -1, max: 40, note: "which letter the camera goes through; -1 picks the one with the widest ink" },
    per: { default: 0.05, min: 0, max: 0.2, note: "seconds between letters arriving" },
    rise: { default: 0.34, min: 0.1, max: 1, note: "seconds a letter takes to stand up" },
    hold: { default: 0.5, min: 0.1, max: 0.9, note: "share of the join before the camera starts through" },
    drift: { default: 0.05, min: 0, max: 0.2, note: "how much the letters grow while they hold, so they never sit still" },
    parallax: { default: 1.3, min: 1, max: 2, note: "how large the next scene starts behind the letters; it settles to rest as the camera goes through" },
    dim: { default: 0.5, min: 0, max: 1, note: "how far the outgoing scene darkens or lightens so the letters read" },
    rim: { default: 0.0016, min: 0, max: 0.01, note: "a thin rule round the letters, of the shorter frame side" },
    ease: { default: [0.72, 0, 0.3, 1], note: "the camera's curve" },
  },
  seenIn: "letter-portal's source for the idea; extended so the letters' ink shows the live next scene",
};

export default {
  meta: meta as any,
  frames: (p: any) => { const n = joinFrames(p); return { exit: n, enter: 0, gap: -n }; },
};
