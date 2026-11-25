// The guests: twenty-four friends, where each stands round the card once they are invited, who answers and when.
// Fifteen have a painted portrait as their picture (media/art/faces, sources in media/art/SOURCES.md; the sixteenth
// portrait is the host's, MIRA_FACE); the rest have an initial on a colour, as people without a picture do.
import { TIMES } from "./kit/times.gen";
import { C, FB, pic, rnd } from "./kit/core";

const NAMES = ["Ana", "Jo", "Ravi", "Ines", "Sam", "Lou", "Kemi", "Max", "Noor", "Dani", "Yuki", "Omar", "Bea", "Leo", "Zoe", "Tariq", "Mei", "Finn", "Ada", "Nico", "Isa", "Paz", "Gus", "Uma"];
const HUES = ["#E8795A", "#5B8DEF", "#E3B23C", "#58B09C", "#B07CC6", "#E56B8A", "#6FA8DC", "#8FB35A"];
/** which guests have a portrait: the file is faces/NN.jpg, NN counting from 01. FACES[i] is guest i's file number, or 0 for an initial */
export const FACES: number[] = [1, 12, 3, 4, 0, 5, 6, 7, 8, 0, 9, 10, 0, 11, 2, 0, 13, 0, 14, 0, 15, 0, 0, 0];
export const MIRA_FACE = 16;               // the host's own picture

export type Guest = { name: string; face: number; hue: string; x: number; y: number; r: number; soft: number; reply: number };
const ROWS = [128, 246, 362, 752, 868, 984];
/** the order they answer in (indices into GUESTS); five never do */
const ORDER = [14, 13, 6, 19, 2, 15, 8, 21, 4, 17, 10, 23, 1, 12, 7, 18, 3, 0, 9];
export const FIRST = ORDER[0];              // the guest whose own phone the film looks at, before the count runs
export const GUESTS: Guest[] = NAMES.map((name, i) => {
  const side = i % 2, k = Math.floor(i / 2), row = k % 6, col = Math.floor(k / 6);          // side 0 is left of the card, 1 right
  const xl = (row % 2 ? [286, 514] : [158, 402])[col] + (rnd(i * 3 + 1) - 0.5) * 34;
  const near = rnd(i * 7 + 2);                                                                  // how near the camera it stands
  return { name, face: FACES[i], hue: HUES[i % HUES.length], x: side ? 1920 - xl : xl, y: ROWS[row] + (rnd(i * 5 + 3) - 0.5) * 22, r: 44 + 14 * near, soft: (1 - near) * 2.0, reply: ORDER.indexOf(i) };
});
/** the frame guest i's invitation reaches them */
export const sentFrame = (i: number) => Math.round((TIMES.PRESS + 0.5) * FB + i * 0.045 * FB) + 4;

/** a round picture of someone: a portrait if they have one, an initial if not */
export function face(key: string, who: { name: string; face: number; hue: string }, cx: number, cy: number, r: number, st: Record<string, any> = {}) {
  return (
    <div key={key} style={{ position: "absolute", left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: "50%", overflow: "hidden", background: who.hue, boxShadow: "0 0 0 3px rgba(255, 255, 255, 0.92), 0 8px 20px rgba(0, 0, 0, 0.22)", ...st }}>
      {who.face > 0
        ? pic("p", `art/faces/${String(who.face).padStart(2, "0")}.jpg`, 0, 0, 2 * r, 2 * r)
        : <div style={{ position: "absolute", left: 0, top: 0, width: 2 * r, height: 2 * r, textAlign: "center", fontFamily: "Geist", fontWeight: 600, fontSize: r * 0.95, lineHeight: `${2 * r}px`, color: C.white }}>{who.name[0]}</div>}
    </div>
  );
}
export const MIRA = { name: "Mira", face: MIRA_FACE, hue: "#E8795A" };
export const THEO = { name: "Theo", face: 0, hue: "#3A6BE0" };
