// What every layout receives, and how a layout looks up the motion the outline named for one of its slots.
import { BeatSpec, Motion, MotionFn, Pose, defaults, named } from "./core";
import { MOTIONS } from "../motions/index";

export type LayoutProps = {
  c: any;            // this beat's content (plus product)
  style: any;        // the whole style file
  tone: any;         // style.tones[spec.tone]
  spec: BeatSpec;
  t: number;         // frames since the beat started
  body: number;      // frames before the beat starts leaving
  W: number; H: number;
};

export type Bound = { at: MotionFn; params: Record<string, any>; frames: number; name: string };

const still: Motion = { meta: { name: "still", kind: "hold", summary: "no motion", params: {}, seenIn: "" }, frames: () => 0, at: () => ({}) };

// The motion the outline names for `slot`, with its params merged over the motion's defaults.
export function motionFor(spec: BeatSpec, slot: string, extra: Record<string, any> = {}): Bound {
  const ref = spec.motions?.[slot];
  const m = !ref || ref.name === "still" ? still : named(MOTIONS, ref.name, "motion");
  const params = { ...defaults(m.meta), ...(ref?.params ?? {}), ...extra };
  return { at: m.at, params, frames: m.frames(params), name: ref?.name ?? "still" };
}

export const poseAt = (b: Bound, t: number, box = { w: 1920, h: 1080 }): Pose => b.at(t, box, b.params);
export const param = (spec: BeatSpec, key: string, fallback: any) => (spec.layout.params ?? {})[key] ?? fallback;
