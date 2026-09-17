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
    if (jobs.size === 0) return "No scheduled jobs (in-memory only, lost when the process exits)";
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
      "Manage scheduled prompt-injection jobs (cron, in-memory only, not persisted). " +
      "add requires cron (5 fields: minute hour day month weekday; 6/7-field forms supported) and prompt; " +
      "remove requires id; list/clear take no extra parameters.",
    promptSnippet: "Schedule cron-based prompt injections (in-memory only)",
    promptGuidelines: [
      "Use schedule_prompt when the user asks to run a prompt periodically on a cron schedule; tasks vanish when the process exits.",
    ],
    parameters: Type.Object({
      action: StringEnum(["add", "list", "remove", "clear"]),
      cron: Type.Optional(
        Type.String({ description: "Cron expression (e.g. '*/30 * * * *' = every 30 minutes), required for add" }),
      ),
      prompt: Type.Optional(Type.String({ description: "Prompt content to inject on schedule, required for add" })),
      id: Type.Optional(Type.String({ description: "Job id, required for remove" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      if (params.action === "add") {
        if (!params.cron || !params.prompt) {
          return {
            content: [{ type: "text", text: "ERROR: add requires both cron and prompt" }],
            details: {},
            isError: true,
          };
        }
        if (!validate(params.cron)) {
          return {
            content: [{ type: "text", text: `ERROR: invalid cron expression: ${params.cron}` }],
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
              text: `Added ${id}: ${params.cron}\nnext: ${next ? next.toLocaleString() : "-"}\nactive jobs: ${jobs.size}`,
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
            content: [{ type: "text", text: `ERROR: job not found: ${params.id ?? "(no id provided)"}` }],
            details: { jobs: jobsSummary() },
            isError: true,
          };
        }
        void jobs.get(params.id)!.task.destroy();
        jobs.delete(params.id);
        refreshStatus();
        return {
          content: [{ type: "text", text: `Removed ${params.id}, jobs left: ${jobs.size}` }],
          details: { jobs: jobsSummary() },
        };
      }
      if (params.action === "clear") {
        destroyAll();
        refreshStatus();
        return {
          content: [{ type: "text", text: "Cleared all scheduled jobs" }],
          details: { jobs: [] },
        };
      }
      return {
        content: [{ type: "text", text: `ERROR: unknown action: ${params.action}` }],
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
    refreshStatus();
  });

  pi.on("session_shutdown", () => {
    destroyAll();
    uiCtx = undefined;
  });
}
