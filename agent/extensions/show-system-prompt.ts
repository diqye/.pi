import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const OUT_PATH = join(tmpdir(), "pi-system-prompt.md");

export default function (pi: ExtensionAPI) {
  pi.registerCommand("system-prompt", {
    description: "Write the current effective system prompt to a file",
    handler: async (_args, ctx) => {
      const prompt = ctx.getSystemPrompt();
      writeFileSync(OUT_PATH, prompt, "utf8");
      const kb = (Buffer.byteLength(prompt, "utf8") / 1024).toFixed(1);
      ctx.ui.notify(`System prompt (${kb} KB) written to ${OUT_PATH}`, "info");
    },
  });
}
