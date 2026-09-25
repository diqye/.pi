export default {
  mcpServers: {
    "chrome-devtools": {
      type: "stdio",
      command: "bunx",
      args: ["chrome-devtools-mcp@latest", "--autoConnect"],
      lazy: true, // 默认不连接，用 /mcp on chrome-devtools 手动开启
    },
  },
};
