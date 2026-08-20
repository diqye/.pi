/**
 * Tools Extension
 *
 * /tools 命令：所有工具（built-in + extension + MCP）的统一开关。
 * 使用 SettingsList 组件，原地 toggle，无需每次重建列表。
 * 持久化到 session 分支，session_start / session_tree 时恢复。
 *
 * 与 mcp-bridge 解耦：MCP 工具注册后默认 OFF，由 /tools 统一启用。
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { getSettingsListTheme } from "@earendil-works/pi-coding-agent";
import { Container, type SettingItem, SettingsList } from "@earendil-works/pi-tui";

// 持久化到 session 的状态：当前启用的工具名集合
interface ToolsState {
  enabledTools: string[];
}

export default function toolsExtension(pi: ExtensionAPI) {
  // 从 session 分支恢复最新的 tools-config，并应用到活跃工具
  function restoreFromBranch(ctx: ExtensionContext) {
    const allToolNames = pi.getAllTools().map((t) => t.name);
    const branchEntries = ctx.sessionManager.getBranch();
    let savedTools: string[] | undefined;

    for (const entry of branchEntries) {
      if (entry.type === "custom" && entry.customType === "tools-config") {
        const data = entry.data as ToolsState | undefined;
        if (data?.enabledTools) {
          savedTools = data.enabledTools;
        }
      }
    }

    if (savedTools) {
      // 仅恢复当前仍存在的工具；未注册的（如尚未连接的 MCP 工具）忽略
      const valid = savedTools.filter((t) => allToolNames.includes(t));
      pi.setActiveTools(valid);
    }
    // 无持久化记录时不覆盖默认活跃工具（基础工具）
  }

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
            // 持久化当前完整活跃集，供 reload / 分支导航恢复
            pi.appendEntry<ToolsState>("tools-config", {
              enabledTools: pi.getActiveTools(),
            });
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

  // 恢复持久化的工具选择
  pi.on("session_start", async (_event, ctx) => {
    restoreFromBranch(ctx);
  });

  // 分支导航时恢复对应分支的工具选择
  pi.on("session_tree", async (_event, ctx) => {
    restoreFromBranch(ctx);
  });
}
