/**
 * /trim [n] — 手动裁剪上下文，只保留最近 n 轮用户提问（默认 10 轮）。
 *
 * 实现方式：拦截 session_before_compact，跳过 LLM 摘要，
 * 直接落一条 compaction 检查点，firstKeptEntryId 指向裁剪点。
 * 之后每次请求只携带该检查点说明 + 保留的尾部消息。
 * 会话文件仍保留全部历史（可用 /tree 回看），仅 LLM context 被裁剪。
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const DEFAULT_KEEP_ROUNDS = 10;

interface PendingTrim {
	firstKeptEntryId: string;
	keptRounds: number;
	totalRounds: number;
}

export default function (pi: ExtensionAPI) {
	let pendingTrim: PendingTrim | null = null;

	pi.registerCommand("trim", {
		description: `裁剪上下文，只保留最近 N 轮提问（默认 ${DEFAULT_KEEP_ROUNDS}）`,
		handler: async (args, ctx) => {
			// 解析 n
			const arg = args.trim();
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
							(tokens !== undefined ? `（剩余约 ${tokens.toLocaleString()} tokens）` : ""),
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
		},
	});

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
}
