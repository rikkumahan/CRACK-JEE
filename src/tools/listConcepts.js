import { z } from "zod";
import { listConcepts } from "../db.js";

export function registerListConcepts(server) {
  server.registerTool(
    "list_concepts",
    {
      title: "List Concepts",
      description:
        "Lists existing concepts for a subject. Call this before log_performance_input to check whether a concept already exists under a different phrasing (e.g. 'Rotational Motion' vs 'Rotational Dynamics') — reuse the existing name rather than creating a near-duplicate.",
      inputSchema: { subject: z.string() },
    },
    async ({ subject }) => ({
      content: [
        { type: "text", text: JSON.stringify(listConcepts(subject)) },
      ],
    })
  );
}
