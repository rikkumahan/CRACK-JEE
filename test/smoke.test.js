import { test } from "node:test";
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

test("echo tool round-trips a message over stdio", async () => {
  const transport = new StdioClientTransport({
    command: "node",
    args: ["src/server.js"],
  });
  const client = new Client({ name: "smoke-test-client", version: "0.1.0" });
  await client.connect(transport);

  const tools = await client.listTools();
  assert.ok(tools.tools.some((t) => t.name === "echo"));

  const result = await client.callTool({
    name: "echo",
    arguments: { message: "ping" },
  });
  assert.equal(result.content[0].text, "ping");

  await client.close();
});
