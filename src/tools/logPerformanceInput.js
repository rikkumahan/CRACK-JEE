import { z } from "zod";
import { db, findOrCreateConcept } from "../db.js";

const ERROR_TYPES = [
  "concept_gap",
  "calculation",
  "misread",
  "time_pressure",
  "unattempted",
  "unknown",
];

export function registerLogPerformanceInput(server) {
  server.registerTool(
    "log_performance_input",
    {
      title: "Log Performance Input",
      description:
        "Records one attempt (a question the student answered, right or wrong) against a concept. Call list_concepts first to check for an existing concept name before inventing a new one.",
      inputSchema: {
        subject: z.string(),
        concept: z.string(),
        result: z.enum(["correct", "wrong", "unattempted"]),
        error_type: z.enum(ERROR_TYPES).optional(),
        time_seconds: z.number().optional(),
        notes: z.string().optional(),
        context: z.string().optional(),
      },
    },
    async ({ subject, concept, result, error_type, time_seconds, notes }) => {
      const conceptId = findOrCreateConcept(concept, subject);

      const attemptId = db
        .prepare(
          `INSERT INTO attempts (concept_id, result, time_seconds, created_at)
           VALUES (?, ?, ?, ?)`
        )
        .run(conceptId, result, time_seconds ?? null, Date.now())
        .lastInsertRowid;

      if (error_type) {
        const errorTypeId = db
          .prepare(`SELECT id FROM error_types WHERE name = ?`)
          .get(error_type).id;

        db.prepare(
          `INSERT INTO attempt_errors (attempt_id, error_type_id, notes)
           VALUES (?, ?, ?)`
        ).run(attemptId, errorTypeId, notes ?? null);
      }

      return {
        content: [
          {
            type: "text",
            text: `Logged attempt ${attemptId} for concept "${concept}" (${subject}): ${result}.`,
          },
        ],
      };
    }
  );
}
