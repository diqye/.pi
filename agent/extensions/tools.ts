/**
 * Tools Extension
 *
 * /tools 命令：所有工具（built-in + extension + MCP）的统一开关。
 * 使用 SettingsList 组件，原地 toggle，无需每次重建列表。
 *
 * 默认策略集中在此：session_start 时保留 pi 默认激活的 builtin 工具，
 * 其余（builtin 中默认未激活的、扩展/MCP 工具）全关，
 * 需要时由用户在 /tools 手动开启，不做持久化（reload/resume 后回到默认）。
 * 各扩展无需再自行 inactive 自己的工具。
 * 例外：PI_TOOLS_ON 环境变量（冒号分隔）指定的工具名默认激活。
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getSettingsListTheme } from "@earendil-works/pi-coding-agent";
import { Container, type SettingItem, SettingsList } from "@earendil-works/pi-tui";
import { toolsOnFromEnv } from "../util/tools-env.js";

export default function toolsExtension(pi: ExtensionAPI) {
  pi.registerCommand("tools", {
    description: "Enable/disable tools",
    handler: async (_args, ctx) => {
      if (ctx.mode !== "tui") {
        ctx.ui.notify("/tools requires TUI mode", "error");
        return;
      }

      const allTools = pi.getAllTools();
      const activeSet = new Set(pi.getActiveTools());

      if (allTools.length === 0) {
        ctx.ui.notify("没有可用的工具", "warning");
        return;
      }

      // ON 排前、OFF 排后
      const sorted = [
        ...allTools.filter((t) => activeSet.has(t.name)),
        ...allTools.filter((t) => !activeSet.has(t.name)),
      ];

      const items: SettingItem[] = sorted.map((tool) => ({
        id: tool.name,
        label: tool.name,
        currentValue: activeSet.has(tool.name) ? "enabled" : "disabled",
        values: ["enabled", "disabled"],
      }));

      await ctx.ui.custom((_tui, theme, _kb, done) => {
        const container = new Container();
        container.addChild(
          new (class {
            render(_width: number) {
              return [theme.fg("accent", theme.bold("Tool Configuration")), ""];
            }
            invalidate() {}
          })(),
        );

        const settingsList = new SettingsList(
          items,
          Math.min(items.length + 2, 15),
          getSettingsListTheme(),
          (id, newValue) => {
            const activeNow = pi.getActiveTools();
            if (newValue === "enabled") {
              if (!activeNow.includes(id)) {
                pi.setActiveTools([...activeNow, id]);
                ctx.ui.notify(`已启用 ${id}`, "info");
              }
            } else {
              if (activeNow.includes(id)) {
                pi.setActiveTools(activeNow.filter((n) => n !== id));
                ctx.ui.notify(`已禁用 ${id}`, "info");
              }
            }
          },
          () => done(undefined),
        );

        container.addChild(settingsList);

        return {
          render: (w: number) => container.render(w),
          invalidate: () => container.invalidate(),
          handleInput: (data: string) => {
            settingsList.handleInput?.(data);
          },
        };
      });
    },
  });

  // 默认策略：保留 pi 默认激活的 builtin 工具（read/bash/edit/write，
  // 尊重 settings defaultTools / CLI --tools 配置），其余全关，用户经 /tools 手动开启；
  // PI_TOOLS_ON 白名单（如 web_search:session_msg）放行
  pi.on("session_start", () => {
    const builtin = new Set(
      pi
        .getAllTools()
        .filter((t) => t.sourceInfo.source === "builtin")
        .map((t) => t.name),
    );
    const keep = toolsOnFromEnv();
    pi.setActiveTools(pi.getActiveTools().filter((name) => builtin.has(name) || keep.has(name)));
  });
}
