// The entry raea renders. `film` is the film; `film-look` is the film without its grain, which `vd look` draws so the
// report can see under it (the layer masks keep only the frontmost layer, and the grain covers the whole frame);
// `plate` is the measure plate (margins, each job's type size, the palette).
import { Composition, registerRoot } from "raea";
import { FILM_ID } from "./ids";
import { FPS, FRAMES, Film, H, W } from "./film";
import { Plate } from "./kit/base";

registerRoot(() => (
  <>
    <Composition id={FILM_ID} component={Film} width={W} height={H} fps={FPS} durationInFrames={FRAMES} />
    <Composition id={`${FILM_ID}-look`} component={() => <Film finish={false} />} width={W} height={H} fps={FPS} durationInFrames={FRAMES} />
    <Composition id="plate" component={() => <Plate w={W} h={H} />} width={W} height={H} fps={FPS} durationInFrames={1} />
  </>
));
