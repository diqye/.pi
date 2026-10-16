/**
 * Image Gen Extension（gpt-image-2 CLI 封装）
 *
 * 替代 prompt 模板 gpt-image-2.md：模板的长规则收进工具 description，
 * 模型经 tool_search 按需加载（deferred），平时零上下文成本。
 *
 * - generate_image：生成 / 编辑图片（prompt + ref/ref-url/mask）
 * - image_mask：本地生成蒙版（纯本地、不耗 API），配合 generate_image 局部重绘
 * - 两个工具均为 deferred exposure：不声明给模型，tool_search 命中后直接调用
 */

import { spawn } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const ASPECTS = ["1:1", "3:2", "2:3", "3:4", "4:3", "16:9", "9:16", "21:9", "9:21"] as const;

// ---------- CLI 执行 ----------

function runCli(args: string[]): Promise<{ ok: true; stdout: string } | { ok: false; error: string }> {
	return new Promise((resolve) => {
		const child = spawn("gpt-image-2", args, { stdio: ["ignore", "pipe", "pipe"] });
		let stdout = "";
		let stderr = "";
		child.stdout.on("data", (d: Buffer) => (stdout += d));
		child.stderr.on("data", (d: Buffer) => (stderr += d));
		child.on("error", (err) => resolve({ ok: false, error: `failed to start gpt-image-2: ${err.message}` }));
		child.on("close", (code) => {
			if (code === 0) resolve({ ok: true, stdout: stdout + stderr });
			else resolve({ ok: false, error: `gpt-image-2 exited with ${code}: ${(stderr || stdout).slice(-500)}` });
		});
	});
}

type Result<TDetails extends Record<string, unknown>> =
	| { content: Array<{ type: "text"; text: string }>; details: TDetails; isError: true }
	| { content: Array<{ type: "text"; text: string }>; details: TDetails };

function ok(text: string, details: Record<string, unknown> = {}): Result<Record<string, unknown>> {
	return { content: [{ type: "text", text }], details };
}

function fail(text: string): Result<Record<string, never>> {
	return { content: [{ type: "text", text }], details: {}, isError: true };
}

const GEN_GUIDELINES = [
	"First understand the user's request and WRITE a clear, specific Chinese image prompt yourself (subject, composition, style, color, text requirements) — never pass the user's raw words as the prompt.",
	"Aspect defaults by image type: illustration/general → 16:9, avatar/icon → 1:1, poster/portrait → 9:16. Use the user's choice when given.",
	"Never raise resolution on your own: always 1K; use 2K/4K only when the user explicitly asks (higher tiers cost much more).",
	"With ref images the prompt becomes an edit/fusion instruction (e.g. '换背景为森林'), not a full re-description; prompt may be omitted when refs are given.",
	"Default output path: ./out-<short-desc>.png in the session cwd. After generation, tell the user the saved path.",
	"gpt-image-2 renders long Chinese text reliably: for text-bearing images put the FULL text verbatim into the prompt (never abbreviate), plus font style and layout instructions. Do not OCR-verify or re-check the result afterwards (wastes tokens; the user checks it themselves).",
];

export default function imageGenExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "generate_image",
		label: "Generate Image",
		exposure: "deferred",
		namespace: { name: "image-gen", description: "Image generation and editing via the gpt-image-2 CLI" },
		description:
			"Generate or edit images via the global `gpt-image-2` CLI (GPT Image 2). Takes an optimized Chinese prompt " +
			"(write it yourself from the user's need, do not forward raw user words), optional local/remote reference " +
			"images for image-to-image editing, and an optional mask for partial repaint. Refs: jpeg/jpg/png/webp, ≤7MB total. " +
		"Generation takes 1-3 minutes. Returns the CLI output including the saved file path. " +
		"gpt-image-2 renders long Chinese text accurately: when the image must contain text (poster, letter, card, 文字图), " +
		"embed the full text verbatim in the prompt — do not fear long text, do not composite text yourself, do not shorten or split. " +
		"Specify font style (e.g. 手写体) and layout (spacing, alignment) in the prompt.",
		promptSnippet: "Generate and edit images via gpt-image-2",
		promptGuidelines: GEN_GUIDELINES,
		parameters: Type.Object({
			prompt: Type.Optional(
				Type.String({ description: "Optimized image prompt (Chinese). Required unless ref images are given" }),
			),
			out: Type.Optional(Type.String({ description: "Output file path, default ./out-<short-desc>.png" })),
			aspect: Type.Optional(Type.String({ description: `Aspect ratio: ${ASPECTS.join(" ")}` })),
			resolution: Type.Optional(
				Type.String({ description: "1K / 2K / 4K. Always omit (1K) unless the user explicitly asks for higher — higher tiers cost much more" }),
			),
			format: Type.Optional(Type.String({ description: "png / jpeg, default png" })),
			count: Type.Optional(Type.Integer({ minimum: 1, maximum: 8, description: "Number of images (1-8)" })),
			ref: Type.Optional(Type.Array(Type.String(), { description: "Local reference image paths" })),
			ref_url: Type.Optional(Type.Array(Type.String(), { description: "Remote reference image URLs" })),
			mask: Type.Optional(Type.String({ description: "Mask path for partial repaint, requires ref" })),
			negative: Type.Optional(Type.String({ description: "Negative prompt" })),
		}),
		async execute(_toolCallId, params) {
			if (!params.prompt && !params.ref?.length && !params.ref_url?.length)
				return fail("ERROR: either prompt or at least one ref/ref_url is required.");

			const out = params.out ?? `./out-${Date.now().toString(36)}.png`;
			const args: string[] = [];
			if (params.prompt) args.push(params.prompt);
			args.push("--out", out);
			if (params.aspect) args.push("--aspect", params.aspect);
			if (params.resolution) args.push("--resolution", params.resolution);
			if (params.format) args.push("--format", params.format);
			if (params.count) args.push("--count", String(params.count));
			if (params.negative) args.push("--negative", params.negative);
			for (const r of params.ref ?? []) args.push("--ref", r);
			for (const u of params.ref_url ?? []) args.push("--ref-url", u);
			if (params.mask) args.push("--mask", params.mask);

			const r = await runCli(args);
			if (!r.ok) return fail(`ERROR: ${r.error}`);
			// CLI 成功输出里含“已保存: <path>”；整体回传，模型自行提取路径
			return ok(r.stdout.replace(/\r[^\n]*\r/g, "\r").trim(), { out });
		},
	});

	pi.registerTool({
		name: "image_mask",
		label: "Image Mask",
		exposure: "deferred",
		namespace: { name: "image-gen", description: "Image generation and editing via the gpt-image-2 CLI" },
		description:
			"Create a local mask for partial repaint with the `gpt-image-2 mask` sub-command (pure local, no API cost). " +
			"Painted shapes = area allowed to repaint, black = keep original. Rectangles: --rect x,y,w,h (repeatable); " +
			"circles: --circle cx,cy,r (repeatable). Reads the source image size via --ref (PNG), or use --size WxH. " +
			"Blurred edge (feather 15-25px) recommended; approximate shapes suffice. Then call generate_image with " +
			"the mask and ref. Read the source image first to estimate coordinates.",
		promptSnippet: "Create local masks for partial image repaint",
		promptGuidelines: [
			"Use image_mask before generate_image when the user wants to change only part of an image.",
			"First read the source image to estimate the target area's coordinates, then build the mask; rectangle approximation with feathering is enough.",
		],
		parameters: Type.Object({
			ref: Type.Optional(Type.String({ description: "Source PNG path, reads its size" })),
			size: Type.Optional(Type.String({ description: "Explicit size WxH, e.g. 1536x1024" })),
			rect: Type.Optional(Type.Array(Type.String(), { description: "Rectangles x,y,w,h (repeatable)" })),
			circle: Type.Optional(Type.Array(Type.String(), { description: "Circles cx,cy,r (repeatable)" })),
			blur: Type.Optional(Type.Integer({ description: "Edge feather in pixels, 15-25 recommended" })),
			out: Type.Optional(Type.String({ description: "Mask output path, default ./mask-<timestamp>.png" })),
		}),
		async execute(_toolCallId, params) {
			if (!params.ref && !params.size) return fail("ERROR: ref or size is required.");
			if (!params.rect?.length && !params.circle?.length)
				return fail("ERROR: at least one rect or circle is required.");

			const args = ["mask"];
			if (params.ref) args.push("--ref", params.ref);
			if (params.size) args.push("--size", params.size);
			for (const rc of params.rect ?? []) args.push("--rect", rc);
			for (const c of params.circle ?? []) args.push("--circle", c);
			if (params.blur) args.push("--blur", String(params.blur));
			const out = params.out ?? `./mask-${Date.now().toString(36)}.png`;
			args.push("--out", out);

			const r = await runCli(args);
			if (!r.ok) return fail(`ERROR: ${r.error}`);
			return ok(`mask saved: ${out}\n${r.stdout.trim()}`, { out });
		},
	});
}
