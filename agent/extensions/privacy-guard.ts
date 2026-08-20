import { homedir } from "node:os";
import { resolve } from "node:path";
import type { ExtensionAPI, ExtensionUIContext } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

const HOME = homedir();

const PROTECTED_PATHS = [
//  "~/.pi",
  "~/.zshrc",
  "~/.bashrc",
  "~/.ssh",
  "~/.gnupg",
  "~/.aws",
  "~/.config",
].map(expandHome);

function expandHome(path: string): string {
  if (path === "~") return HOME;
  if (path.startsWith("~/")) return resolve(HOME, path.slice(2));
  return resolve(path);
}

function normalizePath(path: string): string {
  return expandHome(path);
}

function isProtectedPath(path: string): boolean {
  const normalized = normalizePath(path);
  return PROTECTED_PATHS.some((protectedPath) => {
    return normalized === protectedPath || normalized.startsWith(`${protectedPath}/`);
  });
}

function extractProtectedPathsFromCommand(command: string): string[] {
  const hits = new Set<string>();

  const candidates = [
    ...PROTECTED_PATHS,
    ...PROTECTED_PATHS.map((p) => p.replace(HOME, "~")),
  ];

  for (const candidate of candidates) {
    if (command.includes(candidate)) {
      hits.add(candidate);
    }
  }

  return [...hits];
}

// 单输入框授权：直接回车 = yes；yes [备注] / no [备注] 带附加信息；其他输入循环重提示
// 返回 undefined 表示 Esc 取消整个授权（按拒绝处理）
async function askWithNote(
  ui: ExtensionUIContext,
  title: string,
  message: string,
): Promise<{ ok: boolean; note: string } | undefined> {
  const header = `${title}\n${message}\n\n直接回车 = yes　|　yes [备注]　|　no [备注]`;
  const placeholder = "yes [备注] / no [备注]";
  while (true) {
    const raw = await ui.input(header, placeholder);
    if (raw === undefined) return undefined; // Esc → 取消整个授权
    const trimmed = raw.trim();
    const lower = trimmed.toLowerCase();
    if (trimmed === "") return { ok: true, note: "" }; // 直接回车 = yes
    if (lower === "yes" || lower === "y") return { ok: true, note: "" };
    if (lower === "no" || lower === "n") return { ok: false, note: "" };
    if (lower.startsWith("yes ")) return { ok: true, note: trimmed.slice(4).trim() };
    if (lower.startsWith("no ")) return { ok: false, note: trimmed.slice(3).trim() };
    if (lower.startsWith("y ")) return { ok: true, note: trimmed.slice(2).trim() };
    if (lower.startsWith("n ")) return { ok: false, note: trimmed.slice(2).trim() };
    ui.notify("输入格式不对。请输入：yes [备注]、no [备注]、或直接回车（= yes）", "warning");
  }
}

// 只读模式：仅会话期间有效，不持久化（reload / 切换会话后自动重置）
let readOnlyMode = false;

export default function privacyGuard(pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    // 只读模式：所有写操作需用户确认（不持久化，仅会话期间）
    if (readOnlyMode) {
      if (isToolCallEventType("edit", event) || isToolCallEventType("write", event)) {
        const r = await askWithNote(
          ctx.ui,
          "只读模式 · 确认写入？",
          `当前处于只读模式，工具 ${event.toolName} 想修改：\n${event.input.path}`,
        );
        if (!r || !r.ok) {
          const reason = r?.note
            ? `只读模式下用户拒绝 ${event.toolName}：${event.input.path} · 备注：${r.note}`
            : `只读模式下用户拒绝 ${event.toolName}：${event.input.path}`;
          return { block: true, reason };
        }
        if (r.note) ctx.ui.notify(`只读模式 · 已允许写入 ${event.input.path} · 备注：${r.note}`, "info");
        return;
      }
      if (isToolCallEventType("bash", event)) {
        const r = await askWithNote(
          ctx.ui,
          "只读模式 · 确认执行 bash？",
          `当前处于只读模式，是否允许执行：\n${event.input.command}`,
        );
        if (!r || !r.ok) {
          const reason = r?.note
            ? `只读模式下用户拒绝该 bash 命令 · 备注：${r.note}`
            : "只读模式下用户拒绝该 bash 命令";
          return { block: true, reason };
        }
        if (r.note) ctx.ui.notify(`只读模式 · 已允许执行 bash · 备注：${r.note}`, "info");
        return;
      }
    }

    if (isToolCallEventType("read", event)) {
      if (!isProtectedPath(event.input.path)) return;

      const r = await askWithNote(
        ctx.ui,
        "允许读取私密文件？",
        `工具 read 想读取：\n${event.input.path}`,
      );
      if (!r || !r.ok) {
        const reason = r?.note
          ? `User denied read access to ${event.input.path} · 备注：${r.note}`
          : `User denied read access to ${event.input.path}`;
        return { block: true, reason };
      }
      if (r.note) ctx.ui.notify(`已允许读取 ${event.input.path} · 备注：${r.note}`, "info");
      return;
    }

    if (isToolCallEventType("edit", event) || isToolCallEventType("write", event)) {
      const targetPath = event.input.path;
      if (!isProtectedPath(targetPath)) return;

      const r = await askWithNote(
        ctx.ui,
        "允许修改私密文件？",
        `工具 ${event.toolName} 想修改：\n${targetPath}`,
      );
      if (!r || !r.ok) {
        const reason = r?.note
          ? `User denied ${event.toolName} access to ${targetPath} · 备注：${r.note}`
          : `User denied ${event.toolName} access to ${targetPath}`;
        return { block: true, reason };
      }
      if (r.note) ctx.ui.notify(`已允许 ${event.toolName} 修改 ${targetPath} · 备注：${r.note}`, "info");
      return;
    }

    if (isToolCallEventType("bash", event)) {
      const hits = extractProtectedPathsFromCommand(event.input.command);
      if (hits.length === 0) return;

      const r = await askWithNote(
        ctx.ui,
        "允许 bash 访问私密路径？",
        `bash 命令可能会访问这些私密路径：\n${hits.map((p) => `- ${p}`).join("\n")}\n\n命令：\n${event.input.command}`,
      );
      if (!r || !r.ok) {
        const reason = r?.note
          ? `User denied bash access to protected paths · 备注：${r.note}`
          : "User denied bash access to protected paths";
        return { block: true, reason };
      }
      if (r.note) ctx.ui.notify(`已允许 bash 访问私密路径 · 备注：${r.note}`, "info");
    }
  });

  pi.registerCommand("privacy-guard", {
    description: "Show protected paths guarded by confirmation prompts",
    handler: async (_args, ctx) => {
      ctx.ui.notify(`Privacy guard enabled for:\n${PROTECTED_PATHS.map((p) => `- ${p}`).join("\n")}`, "info");
    },
  });

  pi.registerCommand("privacy-guard-readonly", {
    description: "切换只读模式（会话期间所有写操作需确认，不持久化）用法：on | off | 留空切换",
    handler: async (args, ctx) => {
      const arg = args.trim().toLowerCase();
      if (arg === "on") readOnlyMode = true;
      else if (arg === "off") readOnlyMode = false;
      else if (arg === "") readOnlyMode = !readOnlyMode;
      else {
        ctx.ui.notify(`用法：/privacy-guard-readonly [on|off]　当前：${readOnlyMode ? "开启" : "关闭"}`, "info");
        return;
      }
      ctx.ui.setStatus("privacy-readonly", readOnlyMode ? "🔒 只读" : undefined);
      ctx.ui.notify(
        readOnlyMode ? "🔒 只读模式已开启：写操作将需确认" : "只读模式已关闭",
        readOnlyMode ? "warning" : "info",
      );
    },
  });
}
