# MCP Tool Implementation Plan

_Written 2026-09-14. Covers the 5 tools in `ex1.md` §10 / `docs/plan.md`
backlog not yet built. Built tools (`echo`, `list_concepts`,
`log_performance_input`) are not covered here._

Conventions (already established in the codebase, follow exactly):
- One file per tool in `src/tools/`, exporting `register<ToolName>(server)`.
- Import and call each `register*` from `src/server.js`.
- zod schemas for tool input (plain object of zod fields, not `z.object({})`).
- Raw `db.prepare(sql).run/get/all(...)` — no ORM/query builder.
- Output: `JSON.stringify(...)` for structured data, plain string for
  write-confirmations.
- Tests: `node --test`, black-box, drive the real server subprocess via the
  MCP SDK's `Client`/`StdioClientTransport`, serial (`--test-concurrency=1`).

Build order: 3a → 3b → (confirm decay formula) → 4 → 5 (concept graph,
separate from tool work) → 6a → 6b. Matches `docs/plan.md`'s backlog.

---

## Step 3a — `get_weak_topics`

**Purpose:** accuracy/error-rate ranking by concept, across all attempts to
date.

**Input:** `{ subject: z.string(), limit?: z.number() }` (limit default 10)

**Query** (reuses `concepts`/`attempts`, no new tables):
```sql
SELECT c.id, c.name,
       COUNT(*) AS total_attempts,
       SUM(CASE WHEN a.result = 'correct' THEN 1 ELSE 0 END) AS correct,
       SUM(CASE WHEN a.result = 'wrong' THEN 1 ELSE 0 END) AS wrong,
       SUM(CASE WHEN a.result = 'unattempted' THEN 1 ELSE 0 END) AS unattempted
FROM attempts a JOIN concepts c ON c.id = a.concept_id
WHERE c.subject = ?
GROUP BY c.id
ORDER BY (CAST(wrong AS REAL) / total_attempts) DESC
LIMIT ?
```
Compute `accuracy = correct/total_attempts` in JS on the returned rows
before JSON-stringifying — simpler than float division in SQL.

**File:** `src/tools/getWeakTopics.js`
**Test:** `test/weakTopics.test.js` — log a few attempts via
`log_performance_input`, then assert ranking order.

Skipped: minimum-sample-size filtering (e.g. ignore concepts with <3
attempts). Add if early real usage shows noisy single-attempt concepts
dominating the ranking.

---

## Step 3b — `get_recurring_mistakes`

**Purpose:** the actual differentiator vs. Aakash reports — same
`(concept, error_type)` pair appearing 2+ times across different tests.

**Input:** `{ subject: z.string(), min_occurrences?: z.number() }` (default 2)

**Query** (joins in `attempt_errors`/`error_types`):
```sql
SELECT c.name AS concept, et.name AS error_type, COUNT(*) AS occurrences
FROM attempt_errors ae
JOIN attempts a ON a.id = ae.attempt_id
JOIN concepts c ON c.id = a.concept_id
JOIN error_types et ON et.id = ae.error_type_id
WHERE c.subject = ?
GROUP BY c.id, et.id
HAVING COUNT(*) >= ?
ORDER BY occurrences DESC
```
One query, no BKT/decay involvement.

**File:** `src/tools/getRecurringMistakes.js`
**Test:** `test/recurringMistakes.test.js`

---

## Step 4 — `get_concept_state` (BKT + retention decay)

**Open decision, confirm before building:** `docs/plan.md`'s decay formula
is unpinned. Proposed default (simplest thing satisfying `ex1.md` §7.3's
"simple time-decay nudge"):

> After a 14-day grace period since a concept's last attempt, decay
> `mastery_probability` by ×0.97 per additional full week idle, floored at
> ~0.3 so it never implies "never learned." Applied lazily at read time in
> `get_concept_state`, not via a cron job/scheduler — none exists, don't add
> one for this.

**Schema addition** (verify exact columns against `ex1.md` §6 before
writing — this report only confirms table name/purpose):
```sql
CREATE TABLE IF NOT EXISTS student_concept_state (
  concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
  mastery_probability REAL NOT NULL,
  last_attempt_at INTEGER
);
```

**Logic, two parts:**
1. **Update on write** — hook into `log_performance_input` (or a shared
   helper it calls): standard BKT closed-form update using fixed
   literature-default `P(L0), P(T), P(G), P(S)` — plain arithmetic, no
   library. Upsert into `student_concept_state`.
2. **Read with decay** — `get_concept_state({ subject, concept_id? })` reads
   `student_concept_state`, applies the decay formula above based on
   `now - last_attempt_at`, returns the decayed value. Decay is never
   written back — the stored value stays "true BKT state," decay is a
   read-time nudge, so the formula can be tuned later without a migration.

**Files:**
- `src/bkt.js` — pure functions `updateMastery(prior, result)` and
  `applyDecay(mastery, daysSinceLastAttempt)`, no DB dependency.
- `src/tools/getConceptState.js`
- Modify `src/tools/logPerformanceInput.js` to call the BKT update after
  inserting the attempt.

**Test:** a pure unit test for `src/bkt.js` (first non-black-box test in
the repo — fine, these are pure functions, no subprocess needed), plus one
black-box test logging attempts and checking mastery moves the right
direction.

---

## Step 6a — `generate_daily_plan`

**Purpose:** the one tool where Qwen does real reasoning. It calls
`get_weak_topics`/`get_recurring_mistakes`/`get_concept_state` itself as
separate tool calls in the same conversation, composes a plan, then calls
this tool once to persist it. The server never calls an LLM itself
(no ML/no LLM-in-server constraint, `ex1.md` §7.2/§9) — same
extraction-happens-in-chat pattern as `log_performance_input`.

**Schema addition** (verify exact columns against `ex1.md` §6):
```sql
CREATE TABLE IF NOT EXISTS interventions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  concept_id INTEGER NOT NULL REFERENCES concepts(id),
  plan_text TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
```

**Input:** `{ concept_id: z.number(), plan_text: z.string() }`

**File:** `src/tools/generateDailyPlan.js` — smallest tool in the set, one
insert, no query logic.

---

## Step 6b — `get_progress`

**Purpose:** closed-loop verification — did the intervention work?
Compares accuracy/mastery before vs. after `interventions.created_at`.

**Schema addition:**
```sql
CREATE TABLE IF NOT EXISTS intervention_outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  intervention_id INTEGER NOT NULL REFERENCES interventions(id),
  accuracy_before REAL,
  accuracy_after REAL,
  measured_at INTEGER NOT NULL
);
```

**Logic:** query `attempts` for the concept, split at
`interventions.created_at` (before vs. after), compute accuracy on each
side, insert into `intervention_outcomes`, return the comparison. Reuses
the same accuracy shape as `get_weak_topics` — worth factoring
`computeAccuracy(attempts)` into a shared `src/analytics.js` helper once
this tool exists, rather than duplicating the SQL a third time.

**File:** `src/tools/getProgress.js`
