import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

interface ModelsConfig {
  providers?: Record<string, { models?: Array<{ id?: string; name?: string }> }>;
}

function loadModelNames(): Record<string, string> {
  try {
    const filePath = join(homedir(), ".pi", "agent", "models.json");
    const raw = readFileSync(filePath, "utf8");
    const config = JSON.parse(raw) as ModelsConfig;
    const names: Record<string, string> = {};

    for (const provider of Object.values(config.providers ?? {})) {
      for (const model of provider.models ?? []) {
        if (model.id && model.name) {
          names[model.id] = model.name;
        }
      }
    }

    return names;
  } catch {
    return {};
  }
}

export default function (pi: ExtensionAPI) {
  let modelNames = loadModelNames();

  function updateStatus(modelId: string, ctx: ExtensionContext) {
    const realName = modelNames[modelId];
    if (realName) {
      ctx.ui.setStatus("model-alias", ctx.ui.theme.fg("muted", `(${realName})`));
    } else {
      ctx.ui.setStatus("model-alias", undefined);
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    modelNames = loadModelNames();
    const model = ctx.model;
    if (model?.id) {
      updateStatus(model.id, ctx);
    }
  });

  pi.on("model_select", async (event, ctx) => {
    modelNames = loadModelNames();
    updateStatus(event.model.id, ctx);
  });
}
