/**
 * Schedule Prompt Extension
 *
 * 定时注入 prompt（cron 表达式，node-cron v4 调度）。
 *
 * - 工具 schedule_prompt 默认 OFF，需在 /tools 中手动开启
 *   （tools.ts 的 session_start 恢复在本扩展之后执行，兼容已持久化的启用状态）
 * - 任务纯内存：不 appendEntry，session_shutdown 销毁，进程退出即消失
 * - 注入用 pi.sendMessage（custom message），AI 可感知这是定时触发而非用户输入
 * - /schedule 查看当前任务列表
 */

import { schedule, validate, type ScheduledTask } from "node-cron";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

const TOOL = "schedule_prompt";
const CUSTOM_TYPE = "schedule-prompt";

interface ScheduledJob {
  id: string;
  cron: string;
  prompt: string;
  task: ScheduledTask;
}

function truncate(s: string, max: number): string {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

export default function schedulePromptExtension(pi: ExtensionAPI) {
  const jobs = new Map<string, ScheduledJob>();
  let seq = 0;
  // 最新 session 的 ctx，供 cron 回调里 notify / setStatus（session 切换时更新）
  let uiCtx: ExtensionContext | undefined;

  function refreshStatus() {
    uiCtx?.ui.setStatus("schedule", jobs.size > 0 ? `⏰ schedule:${jobs.size}` : undefined);
  }

  function fire(job: ScheduledJob) {
    pi.sendMessage(
      {
        customType: CUSTOM_TYPE,
        content: `[scheduled ${job.cron}] ${job.prompt}`,
        display: true,
      },
      // followUp + triggerTurn：busy 时排队等 agent 结束，idle 时立即触发 turn，无需判断状态
      { triggerTurn: true, deliverAs: "followUp" },
    );
    uiCtx?.ui.notify(`⏰ fired: ${job.cron} → ${truncate(job.prompt, 50)}`, "info");
  }

  function listText(): string {
    if (jobs.size === 0) return "没有定时任务（纯内存，进程退出即消失）";
    return [...jobs.values()]
      .map((j) => {
        const next = j.task.getNextRun();
        return `${j.id}  ${j.cron}\n  next: ${next ? next.toLocaleString() : "-"}\n  prompt: ${truncate(j.prompt, 60)}`;
      })
      .join("\n");
  }

  function jobsSummary() {
    return [...jobs.values()].map((j) => ({ id: j.id, cron: j.cron, prompt: j.prompt }));
  }

  function destroyAll() {
    for (const j of jobs.values()) void j.task.destroy();
    jobs.clear();
  }

  pi.registerTool({
    name: TOOL,
    label: "Schedule Prompt",
    description:
      "管理定时 prompt 注入任务（cron 表达式，进程内存态，不持久化）。" +
      "add 需要 cron（5 字段：分 时 日 月 周，支持 6/7 字段扩展）和 prompt；" +
      "remove 需要 id；list/clear 无额外参数。",
    promptSnippet: "Schedule prompts to be injected periodically on cron expressions (in-memory only)",
    promptGuidelines: [
      "Use schedule_prompt when the user asks to run a prompt periodically on a cron schedule; tasks vanish when the process exits.",
    ],
    parameters: Type.Object({
      action: StringEnum(["add", "list", "remove", "clear"]),
      cron: Type.Optional(
        Type.String({ description: "cron 表达式（如 '*/30 * * * *' 每 30 分钟），add 时必填" }),
      ),
      prompt: Type.Optional(Type.String({ description: "到点注入的 prompt 内容，add 时必填" })),
      id: Type.Optional(Type.String({ description: "任务 id，remove 时必填" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      if (params.action === "add") {
        if (!params.cron || !params.prompt) {
          return {
            content: [{ type: "text", text: "ERROR: add 需要 cron 和 prompt 两个参数" }],
            details: {},
            isError: true,
          };
        }
        if (!validate(params.cron)) {
          return {
            content: [{ type: "text", text: `ERROR: 非法 cron 表达式: ${params.cron}` }],
            details: {},
            isError: true,
          };
        }
        const id = `sp-${(++seq).toString(36)}`;
        const job: ScheduledJob = { id, cron: params.cron, prompt: params.prompt, task: undefined! };
        job.task = schedule(params.cron, () => fire(job), { unref: true });
        jobs.set(id, job);
        uiCtx = ctx;
        refreshStatus();
        const next = job.task.getNextRun();
        return {
          content: [
            {
              type: "text",
              text: `已添加 ${id}: ${params.cron}\nnext: ${next ? next.toLocaleString() : "-"}\n当前任务数: ${jobs.size}`,
            },
          ],
          details: { jobs: jobsSummary() },
        };
      }
      if (params.action === "list") {
        return {
          content: [{ type: "text", text: listText() }],
          details: { jobs: jobsSummary() },
        };
      }
      if (params.action === "remove") {
        if (!params.id || !jobs.has(params.id)) {
          return {
            content: [{ type: "text", text: `ERROR: 任务不存在: ${params.id ?? "(未提供 id)"}` }],
            details: { jobs: jobsSummary() },
            isError: true,
          };
        }
        void jobs.get(params.id)!.task.destroy();
        jobs.delete(params.id);
        refreshStatus();
        return {
          content: [{ type: "text", text: `已移除 ${params.id}，剩余任务数: ${jobs.size}` }],
          details: { jobs: jobsSummary() },
        };
      }
      if (params.action === "clear") {
        destroyAll();
        refreshStatus();
        return {
          content: [{ type: "text", text: "已清空全部定时任务" }],
          details: { jobs: [] },
        };
      }
      return {
        content: [{ type: "text", text: `ERROR: 未知 action: ${params.action}` }],
        details: {},
        isError: true,
      };
    },
  });

  pi.registerCommand("schedule", {
    description: "List scheduled prompts",
    handler: async (_args, ctx) => {
      ctx.ui.notify(listText(), jobs.size > 0 ? "info" : "warning");
    },
  });

  pi.on("session_start", (_event, ctx) => {
    uiCtx = ctx;
    // 默认 OFF：从活跃工具中移除自己，由 /tools 手动开启
    pi.setActiveTools(pi.getActiveTools().filter((n) => n !== TOOL));
    refreshStatus();
  });

  pi.on("session_shutdown", () => {
    destroyAll();
    uiCtx = undefined;
  });
}
