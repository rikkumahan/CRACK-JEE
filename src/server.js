import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "jee-performance-engine",
  version: "0.1.0",
});

server.registerTool(
  "echo",
  {
    title: "Echo",
    description:
      "Echoes back the message it is given. Used only to verify the MCP connection is alive.",
    inputSchema: { message: z.string() },
  },
  async ({ message }) => ({
    content: [{ type: "text", text: message }],
  })
);

const transport = new StdioServerTransport();
await server.connect(transport);
