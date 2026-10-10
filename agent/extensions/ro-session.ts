/**
 * /ro [file] — 只读加载会话文件作为基础 session。
 *
 * 用法：
 *   pi --no-session     启动（必须：内存会话才能保证后续对话不落盘）
 *   /ro [file]          加载（默认 ro.jsonl，相对 cwd，支持 ~）
 *
 * 原理：当前会话为内存态时 ctx.newSession() 建的新会话同样不落盘
 * （agent-session-runtime 的既定行为），setup 回调把文件条目按原顺序重放进
 * 新 SessionManager，runtime 随后 refreshContext。源文件全程只读，退出即丢。
 *
 * 重放会生成新 entry id，compaction.firstKeptEntryId 需经 old→new 映射改写，
 * 否则分界指向不存在的条目、被 buildContextEntries 静默丢弃。
 * branch_summary / context_edit / label 涉及分支与改写语义，无法线性重放，遇到报错。
 * 同理，message 条目里的 compactionSummary / branchSummary 角色（正常只应由
 * appendCompaction 等生成，手改文件才可能出现）也拒绝重放。
 */

import {
	migrateSessionEntries,
	parseSessionEntries,
	type ExtensionAPI,
	type FileEntry,
	type SessionManager,
} from "@earendil-works/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const DEFAULT_FILE = "ro.jsonl";

/** 可线性重放的条目类型（session 为文件头，重放时跳过） */
const REPLAYABLE = new Set([
	"session",
	"message",
	"model_change",
	"thinking_level_change",
	"session_info",
	"usage",
	"custom",
	"custom_message",
	"compaction",
]);

function replay(sm: SessionManager, entries: FileEntry[]): void {
	const remap = new Map<string, string>();
	for (const entry of entries) {
		switch (entry.type) {
			case "session":
				break;
			case "message": {
				// 入口已拦截这两种角色；此处再拦一次为了让 TS 收窄到 appendMessage 可接受的集合
				const m = entry.message;
				if (m.role === "compactionSummary" || m.role === "branchSummary") break;
				remap.set(entry.id, sm.appendMessage(m));
				break;
			}
			case "model_change":
				remap.set(entry.id, sm.appendModelChange(entry.provider, entry.modelId));
				break;
			case "thinking_level_change":
				remap.set(entry.id, sm.appendThinkingLevelChange(entry.thinkingLevel));
				break;
			case "session_info":
				if (entry.name) remap.set(entry.id, sm.appendSessionInfo(entry.name));
				break;
			case "usage":
				remap.set(entry.id, sm.appendUsage(entry.kind, entry.provider, entry.model, entry.usage, entry.note).id);
				break;
			case "custom":
				remap.set(entry.id, sm.appendCustomEntry(entry.customType, entry.data));
				break;
			case "custom_message":
				remap.set(
					entry.id,
					sm.appendCustomMessageEntry(entry.customType, entry.content, entry.display, entry.details),
				);
				break;
			case "compaction": {
				// 分界改写为新 id；找不到则退化为 null（= 压缩点之前全部丢弃）
				const kept = entry.firstKeptEntryId ? remap.get(entry.firstKeptEntryId) : undefined;
				remap.set(
					entry.id,
					sm.appendCompaction(
						entry.summary,
						kept ?? null,
						entry.tokensBefore,
						entry.details,
						entry.fromHook,
						entry.usage,
					),
				);
				break;
			}
		}
	}
}

export default function (pi: ExtensionAPI) {
	pi.registerCommand("ro", {
		description: "只读加载会话文件为内存基础会话（需 pi --no-session 启动）",
		handler: async (args, ctx) => {
			// 守卫：持久会话里 newSession 会新建文件并把重放内容写盘，违背"只读"。
			// ctx.sessionManager 是 Readonly 视图（不含 isPersisted），运行时对象上方法存在。
			if ((ctx.sessionManager as SessionManager).isPersisted()) {
				ctx.ui.notify("当前是持久会话，/ro 会把重放写进新文件。请用 pi --no-session 启动后再 /ro", "error");
				return;
			}

			const arg = args.trim() || DEFAULT_FILE;
			const path = arg.startsWith("~") ? join(homedir(), arg.slice(1)) : resolve(ctx.cwd, arg);
			if (!existsSync(path)) {
				ctx.ui.notify(`文件不存在：${path}`, "error");
				return;
			}

			let entries: FileEntry[];
			try {
				entries = parseSessionEntries(readFileSync(path, "utf8"));
				migrateSessionEntries(entries);
			} catch (err) {
				ctx.ui.notify(`解析失败：${err instanceof Error ? err.message : String(err)}`, "error");
				return;
			}

			const badTypes = [...new Set(entries.map((e) => e.type).filter((t) => !REPLAYABLE.has(t)))];
			const badRoles = [
				...new Set(
					entries
						.filter(
							(e): e is Extract<FileEntry, { type: "message" }> =>
								e.type === "message" &&
								(e.message.role === "compactionSummary" || e.message.role === "branchSummary"),
						)
						.map((e) => e.message.role),
				),
			];
			if (badTypes.length > 0 || badRoles.length > 0) {
				const why = [
					badTypes.length > 0 ? `不支持的条目类型：${badTypes.join(", ")}` : "",
					badRoles.length > 0 ? `不支持的消息角色：${badRoles.join(", ")}` : "",
				].filter(Boolean);
				ctx.ui.notify(`${why.join("；")}（分支/改写语义无法线性重放）`, "error");
				return;
			}

			if (!ctx.isIdle()) await ctx.waitForIdle();

			const messages = entries.filter((e) => e.type === "message").length;
			const result = await ctx.newSession({
				setup: async (sm) => {
					replay(sm, entries); // 之后 runtime 自动 refreshContext
				},
				// 会话已替换，旧 ctx 失效，反馈一律走 withSession 的新 ctx
				withSession: async (rctx) => {
					rctx.ui.notify(`已只读加载 ${path}（${messages} 条消息）。继续对话仅存内存，退出即丢`, "info");
				},
			});
			if (result.cancelled) {
				// cancelled 时未发生会话替换，旧 ctx 仍有效
				ctx.ui.notify("已取消", "info");
			}
		},
	});
}
