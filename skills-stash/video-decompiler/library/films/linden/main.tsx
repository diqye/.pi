// The entry raea renders. `film` is the film; `film-look` is the same film under the name `vd look` draws.
import { Composition, registerRoot } from "raea";
import { FILM_ID } from "./ids";
import { FPS, FRAMES, Film, H, W } from "./film";

registerRoot(() => (
  <>
    <Composition id={FILM_ID} component={Film} width={W} height={H} fps={FPS} durationInFrames={FRAMES} />
    <Composition id={`${FILM_ID}-look`} component={Film} width={W} height={H} fps={FPS} durationInFrames={FRAMES} />
    <Composition id={`${FILM_ID}-sub`} component={() => <Film sub={4} />} width={W} height={H} fps={FPS * 4} durationInFrames={FRAMES * 4} />
  </>
));
