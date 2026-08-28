import { test } from "node:test";
import assert from "node:assert/strict";
import { unlinkSync, existsSync } from "node:fs";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const DB_PATH = new URL("../data/jee.db", import.meta.url);

test("log_performance_input records an attempt and dedups concepts", async () => {
  if (existsSync(DB_PATH)) unlinkSync(DB_PATH);

  const transport = new StdioClientTransport({
    command: "node",
    args: ["src/server.js"],
  });
  const client = new Client({ name: "logging-test-client", version: "0.1.0" });
  await client.connect(transport);

  await client.callTool({
    name: "log_performance_input",
    arguments: {
      subject: "Physics",
      concept: "Rotational Motion",
      result: "wrong",
      error_type: "concept_gap",
    },
  });

  // Same concept, different phrasing/casing — must NOT create a duplicate row.
  await client.callTool({
    name: "log_performance_input",
    arguments: {
      subject: "Physics",
      concept: "rotational motion",
      result: "correct",
    },
  });

  const listResult = await client.callTool({
    name: "list_concepts",
    arguments: { subject: "Physics" },
  });
  const concepts = JSON.parse(listResult.content[0].text);
  assert.equal(concepts.length, 1, "expected exactly one deduped concept");
  assert.equal(concepts[0].name, "Rotational Motion");

  await client.close();
});
