/**
 * Zhipu API Tools（REST 直调，无 MCP / SDK 依赖）
 *
 * 替代原 zhipu-web-search-sse（web_search）与 zai-mcp-server（analyze_image）两个 MCP：
 * - web_search：智谱 Web Search API（search_pro），补实时信息
 * - analyze_image：智谱 GLM 视觉模型，补识图 / OCR / 图表读取
 *
 * - 凭证热生效：每次调用现读 ~/.pi/agent/auth.json（zhipu 条目，缺省回退
 *   zai-coding-cn——同一开放平台、同格式 key），改完无需重启
 * - 默认 OFF：session_start 移出活跃集，由 /tools 手动开启
 * - 所有失败（缺凭证 / 网络 / 超时 / 文件不存在 / 超大）返回结构化错误文本
 *   而非抛异常，LLM 理解原因后自行决定：换参数重试 / 转告用户 / 放弃
 */

import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { extname, isAbsolute, join, resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { z } from "zod";

const API_BASE = "https://open.bigmodel.cn/api/paas/v4";
const REQUEST_TIMEOUT_MS = 30_000;
const VISION_MODEL = "glm-5.3-flash";
const VISION_SYSTEM_PROMPT =
	"You are a careful vision assistant. Describe only what is actually visible in the image; " +
	"never invent details beyond it. Extract text verbatim. Render tables as markdown.";

const WEB_SEARCH = "web_search";
const ANALYZE_IMAGE = "analyze_image";

// ---------- 凭证（热生效） ----------

// auth.json 中可用的条目名：zhipu 优先；zai-coding-cn 是同一平台的历史条目名
const AUTH_KEYS = ["zhipu", "zai-coding-cn"] as const;

function zhipuApiKey(): string | undefined {
	try {
		const raw = readFileSync(join(homedir(), ".pi", "agent", "auth.json"), "utf8");
		const auth = JSON.parse(raw) as Record<string, { type?: string; key?: string }>;
		for (const name of AUTH_KEYS) {
			const key = auth[name]?.key;
			if (key) return key;
		}
	} catch {
		// 缺文件 / 坏 JSON 统一走“未配置”分支
	}
	return undefined;
}

const NO_KEY_HINT =
	'ERROR: Zhipu API key not configured. Add {"zhipu":{"type":"api_key","key":"..."}} to ~/.pi/agent/auth.json, then retry.';

// ---------- HTTP ----------

// 只取需要的字段，其余丢弃；字段全部可选（实测 link/media/icon 常为空串）
const SearchResponseSchema = z.object({
	search_result: z
		.array(
			z.object({
				title: z.string().default(""),
				link: z.string().default(""),
				media: z.string().default(""),
				publish_date: z.string().default(""),
				content: z.string().default(""),
			}),
		)
		.default([]),
});

const ChatResponseSchema = z.object({
	choices: z.array(z.object({ message: z.object({ content: z.string().default("") }) })).min(1),
});

type Result<TDetails extends Record<string, unknown>> =
	| { content: Array<{ type: "text"; text: string }>; details: TDetails; isError: true }
	| { content: Array<{ type: "text"; text: string }>; details: TDetails };

function ok(text: string): Result<Record<string, never>> {
	return { content: [{ type: "text", text }], details: {} };
}

function fail(text: string): Result<Record<string, never>> {
	return { content: [{ type: "text", text }], details: {}, isError: true };
}

async function zhipuPost<T>(
	path: string,
	key: string,
	body: unknown,
	schema: z.ZodType<T>,
): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
	try {
		const res = await fetch(`${API_BASE}${path}`, {
			method: "POST",
			headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
			body: JSON.stringify(body),
			signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
		});
		const text = await res.text();
		if (!res.ok) return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 300)}` };
		const parsed = schema.safeParse(JSON.parse(text));
		if (!parsed.success) return { ok: false, error: `unexpected response shape: ${text.slice(0, 300)}` };
		return { ok: true, data: parsed.data };
	} catch (error) {
		return { ok: false, error: error instanceof Error ? error.message : String(error) };
	}
}

// ---------- 图片源 ----------

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MIME_BY_EXT: Record<string, string> = {
	".png": "image/png",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".webp": "image/webp",
	".gif": "image/gif",
	".bmp": "image/bmp",
};

/** URL 原样透传；本地路径（相对会话 cwd）读文件转 base64 data URL */
function toImageUrl(
	source: string,
	cwd: string,
): { ok: true; url: string } | { ok: false; error: string } {
	if (/^https?:\/\//i.test(source)) return { ok: true, url: source };
	const path = isAbsolute(source) ? source : resolve(cwd, source);
	const mime = MIME_BY_EXT[extname(path).toLowerCase()];
	if (!mime)
		return { ok: false, error: `unsupported image type (expected png/jpg/jpeg/webp/gif/bmp): ${source}` };
	try {
		const size = statSync(path).size;
		if (size > MAX_IMAGE_BYTES)
			return {
				ok: false,
				error: `image too large (${(size / 1024 / 1024).toFixed(1)}MB, max 5MB): ${path}`,
			};
		return { ok: true, url: `data:${mime};base64,${readFileSync(path).toString("base64")}` };
	} catch {
		return { ok: false, error: `image file not found or unreadable: ${path}` };
	}
}

// ---------- 工具 ----------

export default function zhipuToolsExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: WEB_SEARCH,
		label: "Web Search",
		description:
			"Search the web via the Zhipu Web Search API (search_pro) for up-to-date information beyond " +
			"training data (news, prices, release versions, docs). Keep query short (<70 chars); " +
			"count is 1-50 and defaults to 10. Returns structured results (title/link/media/date/content). " +
			"Empty results or errors come back as text — refine the query and retry, or report to the user.",
		promptSnippet: "Search the web for up-to-date information beyond training data",
		promptGuidelines: [
			"Use web_search when the user asks about current events, prices, release versions, or anything likely beyond training data.",
		],
		parameters: Type.Object({
			query: Type.String({ description: "Search query, keep it short (<70 chars)" }),
			count: Type.Optional(
				Type.Integer({ minimum: 1, maximum: 50, description: "Number of results (1-50, default 10)" }),
			),
		}),
		async execute(_toolCallId, params) {
			const key = zhipuApiKey();
			if (!key) return fail(NO_KEY_HINT);

			const r = await zhipuPost(
				"/web_search",
				key,
				{ search_engine: "search_pro", search_query: params.query, count: params.count ?? 10 },
				SearchResponseSchema,
			);
			if (!r.ok) return fail(`ERROR: web search failed (${r.error}). Check the query and retry.`);

			const items = r.data.search_result;
			if (items.length === 0)
				return ok(`No results for "${params.query}". Try a shorter, more specific query.`);
			return ok(
				items
					.map((it, i) =>
						[
							`${i + 1}. ${it.title || "(untitled)"}`,
							[it.link, it.media, it.publish_date].filter(Boolean).join(" · "),
							it.content,
						]
							.filter(Boolean)
							.join("\n"),
					)
					.join("\n\n"),
			);
		},
	});

	pi.registerTool({
		name: ANALYZE_IMAGE,
		label: "Analyze Image",
		description:
			`Analyze an image via the Zhipu GLM vision model (${VISION_MODEL}): describe content, read text (OCR), ` +
			"extract chart/table data. image_source accepts an http(s) URL (passed through) or a local path " +
			"(resolved against the session cwd, read as base64, max 5MB); prompt says what to look for. " +
			"Reports only what is visible; tables come back as markdown.",
		promptSnippet: "Analyze images: description, OCR, chart/table reading",
		promptGuidelines: [
			"Use analyze_image when the user shares an image path or URL and asks what is in it, to OCR it, or to read chart data.",
		],
		parameters: Type.Object({
			image_source: Type.String({
				description: "http(s) URL or local path of the image",
			}),
			prompt: Type.String({ description: "What to analyze in the image" }),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const key = zhipuApiKey();
			if (!key) return fail(NO_KEY_HINT);

			const img = toImageUrl(params.image_source, ctx.cwd);
			if (!img.ok) return fail(`ERROR: ${img.error}`);

			const r = await zhipuPost(
				"/chat/completions",
				key,
				{
					model: VISION_MODEL,
					messages: [
						{ role: "system", content: VISION_SYSTEM_PROMPT },
						{
							role: "user",
							content: [
								// 图片块在前、文本 prompt 在后
								{ type: "image_url", image_url: { url: img.url } },
								{ type: "text", text: params.prompt },
							],
						},
					],
				},
				ChatResponseSchema,
			);
			if (!r.ok) return fail(`ERROR: image analysis failed (${r.error}).`);

			const content = r.data.choices[0]?.message.content ?? "";
			if (!content.trim()) return fail("ERROR: vision model returned empty content, try a more specific prompt.");
			return ok(content);
		},
	});
}
