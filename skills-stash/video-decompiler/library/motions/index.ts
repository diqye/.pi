// Every motion by name. The outline chooses motions by these names; nothing else imports a motion file.
import m_hold_drift from "./hold-drift";
import m_skew_snap from "./skew-snap";
import m_ghost_zoom from "./ghost-zoom";
import m_zoom_settle from "./zoom-settle";
import m_grow_from_point from "./grow-from-point";
import m_shrink_to_point from "./shrink-to-point";
import m_whip_out from "./whip-out";
import m_whip_in from "./whip-in";
import m_outline_to_fill from "./outline-to-fill";
import m_fade_step from "./fade-step";
import m_pop from "./pop";
import m_defocus_in from "./defocus-in";
import m_fade_in from "./fade-in";
import m_card_drop from "./card-drop";
import m_caret_blink from "./caret-blink";
import { Motion } from "../lib/core";
export const MOTIONS: Record<string, Motion> = {
  "hold-drift": m_hold_drift,
  "skew-snap": m_skew_snap,
  "ghost-zoom": m_ghost_zoom,
  "zoom-settle": m_zoom_settle,
  "grow-from-point": m_grow_from_point,
  "shrink-to-point": m_shrink_to_point,
  "whip-out": m_whip_out,
  "whip-in": m_whip_in,
  "outline-to-fill": m_outline_to_fill,
  "fade-step": m_fade_step,
  "pop": m_pop,
  "defocus-in": m_defocus_in,
  "fade-in": m_fade_in,
  "card-drop": m_card_drop,
  "caret-blink": m_caret_blink,
};
