/**
 * /trim — 手动裁剪上下文。
 *
 * 子命令：
 *   /trim [n]        轮次裁剪：只保留最近 n 轮用户提问（默认 10 轮）。
 *                    拦截 session_before_compact，跳过 LLM 摘要，直接落一条
 *                    compaction 检查点（firstKeptEntryId 指向裁剪点），落盘持久。
 *                    会话文件仍保留全部历史（可用 /tree 回看），仅 LLM context 被裁剪。
 *   /trim show       统计：总轮数、总 tokens、tool result 条数/tokens/占比。
 *   /trim tool <n>   钉一条裁剪分界线（倒数第 n 条 tool result）：分界之前的在
 *                    context 中显示为 "[Content removed. Exit 0/1]" 标记（ok=0,
 *                    error=1，仅改发给 LLM 的 messages，非破坏性，会话文件不动），
 *                    分界及其后（含新增）原文保留。
 *                    状态持久化：向 session 插入一条 turn=false 的 CustomMessage
 *                    （customType "trim-tool"，content 对 LLM 可见，details 只存
 *                    分界 toolCallId）；session_start 取最后一条恢复。重复执行
 *                    以最后一次为准——加大 n 可放回部分/全部被裁内容。
 */

import {
	estimateTokens,
	type ExtensionAPI,
	type ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";

const DEFAULT_KEEP_ROUNDS = 10;

interface PendingTrim {
	firstKeptEntryId: string;
	keptRounds: number;
	totalRounds: number;
}

/** 人类友好 token 数：85300 → 85.3k */
function fmtTokens(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
	return String(n);
}

export default function (pi: ExtensionAPI) {
	let pendingTrim: PendingTrim | null = null;
	/** 裁剪分界：从该 toolCallId 起（含）保留原文，之前显示为标记；来源为 session 内最后一条 trim-tool 消息 */
	let keepFromToolCallId: string | null = null;

	// 从 session 条目恢复裁剪分界（startup / resume / new 均触发；多次裁剪以最后一条为准）
	pi.on("session_start", async (_event, ctx) => {
		let restored: string | null = null;
		for (const entry of ctx.sessionManager.buildContextEntries()) {
			if (entry.type === "custom_message" && entry.customType === "trim-tool") {
				const id = (entry.details as { keepFromToolCallId?: string } | undefined)?.keepFromToolCallId;
				if (typeof id === "string") restored = id;
			}
		}
		keepFromToolCallId = restored;
	});

	pi.registerCommand("trim", {
		description:
			"裁剪上下文：/trim [n] 轮次裁剪 | /trim show 统计 | /trim tool <show|n> 裁剪 tool result",
		handler: async (args, ctx) => {
			const arg = args.trim();

			if (arg === "show") {
				await showStats(ctx);
				return;
			}
			if (arg === "tool" || arg.startsWith("tool ")) {
				await handleToolSubcommand(arg.slice(4).trim(), ctx);
				return;
			}

			await trimRounds(arg, ctx);
		},
	});

	// ---------- /trim show / /trim tool ----------

	interface Stats {
		rounds: number;
		totalTokens: number;
		toolCount: number;
		toolTokens: number;
	}

	async function computeStats(ctx: ExtensionCommandContext): Promise<Stats> {
		await ctx.waitForIdle();
		const stats: Stats = { rounds: 0, totalTokens: 0, toolCount: 0, toolTokens: 0 };
		for (const entry of ctx.sessionManager.buildContextEntries()) {
			if (entry.type === "message") {
				const m = entry.message;
				if (m.role === "user") stats.rounds++;
				const tokens = estimateTokens(m);
				stats.totalTokens += tokens;
				if (m.role === "toolResult") {
					stats.toolCount++;
					stats.toolTokens += tokens;
				}
			} else if (entry.type === "compaction") {
				// 摘要文本按 pi 同款 chars/4 估算
				stats.totalTokens += Math.ceil(entry.summary.length / 4);
			}
		}
		return stats;
	}

	function pct(part: number, total: number): string {
		return total > 0 ? `${Math.round((part / total) * 100)}%` : "0%";
	}

	async function showStats(ctx: ExtensionCommandContext): Promise<void> {
		const s = await computeStats(ctx);
		ctx.ui.notify(
			`共 ${s.rounds} 轮提问，总计 ~${fmtTokens(s.totalTokens)} tokens\n` +
				`tool result ${s.toolCount} 条，~${fmtTokens(s.toolTokens)} tokens（占 ${pct(s.toolTokens, s.totalTokens)}）`,
			"info",
		);
	}

	interface ToolResultInfo {
		toolCallId: string;
		tokens: number;
	}

	async function collectToolResults(ctx: ExtensionCommandContext): Promise<ToolResultInfo[]> {
		await ctx.waitForIdle();
		const results: ToolResultInfo[] = [];
		for (const entry of ctx.sessionManager.buildContextEntries()) {
			if (entry.type === "message" && entry.message.role === "toolResult") {
				const m = entry.message;
				results.push({ toolCallId: m.toolCallId, tokens: estimateTokens(m) });
			}
		}
		return results;
	}

	async function handleToolSubcommand(sub: string, ctx: ExtensionCommandContext): Promise<void> {
		if (sub === "" || sub === "show") {
			const s = await computeStats(ctx);
			const results = await collectToolResults(ctx);
			const ids = results.map((r) => r.toolCallId);
			let setting: string;
			if (keepFromToolCallId === null) {
				setting = "当前未裁剪（tool result 全文保留）";
			} else {
				const idx = ids.indexOf(keepFromToolCallId);
				if (idx < 0) {
					setting = "裁剪分界不在当前 context（可能切换了分支），未生效";
				} else {
					const saved = results.slice(0, idx).reduce((sum, r) => sum + r.tokens, 0);
					setting = `已裁剪 ${idx} 条（节省 ~${fmtTokens(saved)} tokens），分界起 ${results.length - idx} 条及新增保留原文`;
				}
			}
			ctx.ui.notify(
				`tool result 共 ${s.toolCount} 条，~${fmtTokens(s.toolTokens)} tokens（占总 context ${pct(s.toolTokens, s.totalTokens)}）\n` +
					setting,
				"info",
			);
			return;
		}

		const n = Number.parseInt(sub, 10);
		if (!Number.isFinite(n) || n < 1) {
			ctx.ui.notify("用法: /trim tool <show|n>，n 为保留原文的条数（至少 1）", "error");
			return;
		}

		await ctx.waitForIdle();
		const results = await collectToolResults(ctx);
		const ids = results.map((r) => r.toolCallId);
		if (ids.length === 0) {
			ctx.ui.notify("当前没有 tool result，无需裁剪", "info");
			return;
		}

		const cutCount = Math.max(0, ids.length - n);
		if (cutCount === 0 && keepFromToolCallId === null) {
			ctx.ui.notify(`当前共 ${ids.length} 条 tool result，不超过 ${n} 条，无需裁剪`, "info");
			return;
		}

		// 分界 = 倒数第 n 条（n 超过总数时为第 1 条，即全保留，可用于后悔恢复）
		const keepFromId = ids[Math.max(0, ids.length - n)];

		// 状态节点：content 对 LLM 可见，details 落盘不进 LLM；triggerTurn=false 不触发回合
		pi.sendMessage(
			{
				customType: "trim-tool",
				content:
					`[trim-tool] 裁剪分界钉在${cutCount > 0 ? `倒数第 ${n} 条` : "第 1 条"} tool result：` +
					`分界之前的 ${cutCount} 条在 context 中显示为 "[Content removed. Exit 0]"（出错为 Exit 1），` +
					`原文仍在会话文件中但不再发送；分界及其后（含新增）保留原文。`,
				display: true,
				details: { keepFromToolCallId: keepFromId },
			},
			{ triggerTurn: false },
		);
		keepFromToolCallId = keepFromId;
		const savedTokens = results.slice(0, cutCount).reduce((sum, r) => sum + r.tokens, 0);
		ctx.ui.notify(
				cutCount > 0
					? `已裁剪 ${cutCount} 条 tool result（保留最后 ${n} 条原文，节省 ~${fmtTokens(savedTokens)} tokens），状态已写入 session，下次请求起生效`
					: `已恢复全保留（分界 = 第 1 条），状态已写入 session`,
			"info",
		);
	}

	// ---------- /trim [n] 轮次裁剪 ----------

	async function trimRounds(arg: string, ctx: ExtensionCommandContext): Promise<void> {
		let keep = DEFAULT_KEEP_ROUNDS;
		if (arg) {
			const parsed = Number.parseInt(arg, 10);
			if (!Number.isFinite(parsed) || parsed < 1) {
				ctx.ui.notify(`用法: /trim [n]，n 为保留的提问轮数（默认 ${DEFAULT_KEEP_ROUNDS}）`, "error");
				return;
			}
			keep = parsed;
		}

		await ctx.waitForIdle();

		// 当前参与 context 的条目（含 compaction 处理，root → leaf 顺序）
		const entries = ctx.sessionManager.buildContextEntries();

		// 一轮 = 从一条真实 user 消息开始，到下一条 user 消息之前的所有条目
		const roundStarts: number[] = [];
		for (let i = 0; i < entries.length; i++) {
			const entry = entries[i];
			if (entry.type === "message" && entry.message.role === "user") roundStarts.push(i);
		}

		if (roundStarts.length <= keep) {
			ctx.ui.notify(`当前共 ${roundStarts.length} 轮提问，不超过 ${keep} 轮，无需裁剪`, "info");
			return;
		}

		const cutIndex = roundStarts[roundStarts.length - keep];
		const totalRounds = roundStarts.length;
		pendingTrim = {
			firstKeptEntryId: entries[cutIndex].id,
			keptRounds: keep,
			totalRounds,
		};

		ctx.compact({
			onComplete: (result) => {
				const tokens = result.estimatedTokensAfter;
				ctx.ui.notify(
					`已裁剪：丢弃前 ${totalRounds - keep} 轮，保留最近 ${keep} 轮` +
						(tokens !== undefined ? `（剩余约 ${fmtTokens(tokens)} tokens）` : ""),
					"info",
				);
			},
			onError: (err) => {
				pendingTrim = null;
				const msg =
					err.message.includes("Nothing to compact") || err.message.includes("Already compacted")
						? `无法裁剪（${err.message}）：会话太小或刚压缩过，新增几轮对话后再试`
						: `裁剪失败：${err.message}`;
				ctx.ui.notify(msg, "error");
			},
		});
	}

	// 拦截 /trim 触发的压缩：跳过 LLM 摘要，把 firstKeptEntryId 钉在裁剪点
	pi.on("session_before_compact", async (event) => {
		if (!pendingTrim) return; // 正常 /compact 或自动压缩不受影响
		const t = pendingTrim;
		pendingTrim = null;
		const dropped = t.totalRounds - t.keptRounds;
		return {
			compaction: {
				summary:
					`[Manual trim] To relieve context pressure the user manually trimmed the session: ` +
					`dropped the first ${dropped} rounds, keeping only the most recent ${t.keptRounds}. ` +
					`The dropped content has no summary; do not assume it still exists in history.`,
				firstKeptEntryId: t.firstKeptEntryId,
				tokensBefore: event.preparation.tokensBefore,
				details: { reason: "manual-trim", keptRounds: t.keptRounds, droppedRounds: dropped },
			},
		};
	});

	// /trim tool：按分界 toolCallId 定位，之前的 tool result 替换为标记（messages 为深拷贝，非破坏性）
	pi.on("context", async (event) => {
		if (keepFromToolCallId === null) return;

		const keepFrom = event.messages.findIndex(
			(m) => m.role === "toolResult" && m.toolCallId === keepFromToolCallId,
		);
		if (keepFrom <= 0) return; // 分界不在当前 context（分支切换）或前面本就没有 tool result

		let changed = false;
		const messages = event.messages.map((m, i) => {
			if (i >= keepFrom || m.role !== "toolResult") return m;
			changed = true;
			// 告知内容被删 + 结果状态：ok=Exit 0, error=Exit 1（无真实 exit code 可取）
			const text = m.isError ? "[Content removed. Exit 1 (error)]" : "[Content removed. Exit 0]";
			return { ...m, content: [{ type: "text" as const, text }] };
		});
		return changed ? { messages } : undefined;
	});
}
