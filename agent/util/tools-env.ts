/**
 * PI_TOOLS_ON 环境变量解析（多个扩展共享）
 *
 * 语义：冒号分隔的工具名列表，session_start 时这些工具默认激活（绕过
 * tools 扩展的「非 builtin 默认关」策略）。session-chat 等扩展也用它
 * 判断自身是否随启动上线。
 *
 * 例：PI_TOOLS_ON=web_search:session_msg pi --no-session
 */

const RAW = process.env.PI_TOOLS_ON ?? "";

/** 解析结果缓存（模块级单例，env 在进程内不会变） */
const TOOLS_ON = new Set(
	RAW
		.split(":")
		.map((s) => s.trim())
		.filter(Boolean),
);

/** PI_TOOLS_ON 中指定的工具名集合 */
export function toolsOnFromEnv(): Set<string> {
	return TOOLS_ON;
}
