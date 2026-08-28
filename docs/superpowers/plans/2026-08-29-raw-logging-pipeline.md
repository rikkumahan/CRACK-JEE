# Raw Logging Pipeline Implementation Plan

> **Execution owner: Claude Code.** Per AGENTS.md's task-routing table, backend logic/schema work is Claude Code's lane (Antigravity is frontend/UI/browser-testing/parallel-exploration; this task is none of those).

**Goal:** Implement ex1.md's Build Order §12 step 2 — the raw logging pipeline. Add the `concepts`/`attempts`/`error_types`/`attempt_errors` SQLite tables and a `log_performance_input` MCP tool that writes to them, with the concept de-duplication logic already confirmed in `docs/plan.md`'s Architecture section. This is the first step that makes the system actually store real student data — everything before it (step 1) just proved the wire connection works.

**Architecture:** A new `src/db.js` module owns the SQLite connection (via `better-sqlite3`) and schema creation (`CREATE TABLE IF NOT EXISTS`, idempotent). A new `src/tools/logPerformanceInput.js` exports the tool registration, importing `db.js`. `src/server.js` gains one new import and one new `registerTool` call; the existing `echo` tool stays as-is (cheap connectivity sanity check, no reason to remove). A new `src/tools/listConcepts.js` exposes a small read tool so the calling LLM (Qwen) can see existing concepts for a subject *before* deciding whether to reuse one or mint a new one — this is layer 1 of the two-layer de-dup design already agreed in `docs/plan.md`.

**Why the tool takes structured fields, not raw text:** ex1.md §11 states the MCP server "never calls an LLM API itself" — extraction is done by Qwen (the calling LLM) as part of its own reasoning, before it calls the tool. So `log_performance_input`'s actual parameters are the *already-extracted* structured fields, not a raw `content` blob for the server to parse itself.

**Tech Stack:** `better-sqlite3` (verified on npm: v13.0.3, requires Node >=22 — we have v24.13.1, fine; already decided in ex1.md §11, no local-inference/network dependency, synchronous API so no extra async-wrapper library needed). Test-installed it in isolation and confirmed it ships a prebuilt `win32-x64.node` binary (and `win32-arm64`) — `npm install` does not compile from source or need a C++ toolchain, which matters directly for ex1.md §2's "minimal setup friction for her" constraint (this same install has to happen on her machine eventually, not just here). Confirmed working with a real insert/select round-trip, not just that it installs. No ORM — hand-written SQL via `better-sqlite3`'s prepared statements is already the minimal, standard way to use it; an ORM would be new unrequested abstraction for 4 small tables.

**Spec:** `ex1.md` §6 (schema), §10 (tool group/signatures), §11 (stack); `docs/plan.md` Architecture section (concept de-dup, already-agreed two-layer design) and Open Questions (retention decay — NOT needed here, that's step 4/BKT, out of scope).

## Global Constraints

- Retention-decay formula, BKT, `student_concept_state`, `interventions`, `intervention_outcomes` tables are OUT OF SCOPE — those are steps 3/4/6. This step only touches `concepts`, `attempts`, `error_types`, `attempt_errors`.
- Concept de-duplication is REQUIRED, not optional — both layers (LLM-context via `listConcepts`, and the normalize-and-exact-match backstop on write) must be implemented, per `docs/plan.md`'s Architecture section.
- `error_types` is a fixed lookup table — seed exactly these 6 rows at schema init: `concept_gap`, `calculation`, `misread`, `time_pressure`, `unattempted`, `unknown` (ex1.md §6).
- No trained ML, no LLM calls from the server itself (ex1.md §3, §11 — hard constraints, unchanged from step 1).
- Branch: `claude/raw-logging-pipeline`, created inside its own worktree via `scripts/new-worktree.sh claude raw-logging-pipeline` (AGENTS.md isolation rule — this bit was gotten wrong once already in the step-1 plan and caught in review; don't repeat it).
- Commit format: `<type>(claude): summary`, type ∈ {feat, fix, chore, docs, refactor, test} (AGENTS.md, verified regex from `.githooks-src/commit-msg`: `^(feat|fix|chore|docs|refactor|test)\([a-z0-9-]+\): .+`).
- DB file: `data/jee.db`, gitignored (like `node_modules` was for step 1) — it's local state, not source.
- Keep `src/tools/` as one file per tool (matches the split ex1.md's own step-1 plan flagged as "revisit when step 2 adds a second tool" — now is that point).

---

### Task 1: Worktree + `better-sqlite3` dependency

**Files:**
- Modify: `package.json` (add dependency)

**Interfaces:**
- Produces: `better-sqlite3` importable as `import Database from "better-sqlite3"`.

- [ ] **Step 0: Create the isolated worktree**

```bash
bash scripts/new-worktree.sh claude raw-logging-pipeline --no-open
```
Expected: creates `../JEE_MCP-claude-raw-logging-pipeline` on branch `claude/raw-logging-pipeline`, hooks installed. All remaining steps run from inside that worktree.

- [ ] **Step 1: Add dependency and `.gitignore` entry**

```bash
npm install better-sqlite3@^13.0.3
```
Add to `.gitignore`: `data/`

- [ ] **Step 2: Commit**

```bash
git add package.json package-lock.json .gitignore
git commit -m "chore(claude): add better-sqlite3 dependency"
```

---

### Task 2: Schema module (`src/db.js`)

**Files:**
- Create: `src/db.js`

**Interfaces:**
- Produces: `export const db` (a `better-sqlite3` `Database` instance, schema already applied), `export function findOrCreateConcept(name, subject)` returning a concept `id` (number). Task 3 and 4 both import from here.

- [ ] **Step 1: Write `src/db.js`**

```js
import Database from "better-sqlite3";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dataDir = fileURLToPath(new URL("../data", import.meta.url));
mkdirSync(dataDir, { recursive: true });
export const db = new Database(fileURLToPath(new URL("../data/jee.db", import.meta.url)));

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    result TEXT NOT NULL CHECK (result IN ('correct', 'wrong', 'unattempted')),
    time_seconds INTEGER,
    created_at INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS error_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
  );

  CREATE TABLE IF NOT EXISTS attempt_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
    error_type_id INTEGER NOT NULL REFERENCES error_types(id),
    notes TEXT
  );
`);

const seedErrorType = db.prepare(
  `INSERT OR IGNORE INTO error_types (name) VALUES (?)`
);
for (const name of [
  "concept_gap",
  "calculation",
  "misread",
  "time_pressure",
  "unattempted",
  "unknown",
]) {
  seedErrorType.run(name);
}

function normalize(name) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function findOrCreateConcept(name, subject) {
  const target = normalize(name);
  const existing = db
    .prepare(`SELECT id, name FROM concepts WHERE subject = ?`)
    .all(subject)
    .find((c) => normalize(c.name) === target);

  if (existing) return existing.id;

  return db
    .prepare(
      `INSERT INTO concepts (name, subject, created_at) VALUES (?, ?, ?)`
    )
    .run(name, subject, Date.now()).lastInsertRowid;
}

export function listConcepts(subject) {
  return db
    .prepare(`SELECT id, name FROM concepts WHERE subject = ? ORDER BY name`)
    .all(subject);
}
```

This is the whole schema layer — no separate migration tool, no ORM. `CREATE TABLE IF NOT EXISTS` + `INSERT OR IGNORE` make it safely re-runnable, which is all that's needed at this scale.

- [ ] **Step 2: Sanity-check syntax**

Run: `node --check src/db.js`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add src/db.js
git commit -m "feat(claude): add SQLite schema and concept de-dup helpers"
```

---

### Task 3: `list_concepts` tool (de-dup layer 1)

**Files:**
- Create: `src/tools/listConcepts.js`
- Modify: `src/server.js`

**Interfaces:**
- Consumes: `listConcepts` from `src/db.js`.
- Produces: MCP tool `list_concepts(subject: string) -> { content: [{ type: "text", text: JSON string of [{id, name}, ...] }] }`. Lets the calling LLM check existing concepts before extraction decides on a name — this is what makes de-dup layer 1 (semantic matching by the LLM) possible; without it the LLM has no visibility into what already exists.

- [ ] **Step 1: Write `src/tools/listConcepts.js`**

```js
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
```

- [ ] **Step 2: Wire it into `src/server.js`**

Add near the top:
```js
import { registerListConcepts } from "./tools/listConcepts.js";
```
Add after the `echo` tool registration, before `const transport = ...`:
```js
registerListConcepts(server);
```

- [ ] **Step 3: Sanity-check syntax**

Run: `node --check src/server.js && node --check src/tools/listConcepts.js`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add src/tools/listConcepts.js src/server.js
git commit -m "feat(claude): add list_concepts tool"
```

---

### Task 4: `log_performance_input` tool (de-dup layer 2 + writes)

**Files:**
- Create: `src/tools/logPerformanceInput.js`
- Modify: `src/server.js`

**Interfaces:**
- Consumes: `db`, `findOrCreateConcept` from `src/db.js`.
- Produces: MCP tool `log_performance_input({ subject, concept, result, error_type?, time_seconds?, notes?, context? }) -> { content: [{ type: "text", text: confirmation string }] }`.

- [ ] **Step 1: Write `src/tools/logPerformanceInput.js`**

```js
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
```

`error_type` and `time_seconds` are `.optional()` in the Zod schema — matches ex1.md §5/§10's explicit design ("Partial extraction is expected and fine — fields are nullable... never blocks or rejects a partial input"). `context` is accepted per ex1.md §10's signature but not yet used (no `tests`/sessions table exists yet in this schema) — accepting and ignoring it now is correct: rejecting it would break the documented tool signature, and there is nowhere to store it until a future step adds session/test grouping.

- [ ] **Step 2: Wire it into `src/server.js`**

Add near the top:
```js
import { registerLogPerformanceInput } from "./tools/logPerformanceInput.js";
```
Add after `registerListConcepts(server);`:
```js
registerLogPerformanceInput(server);
```

- [ ] **Step 3: Sanity-check syntax**

Run: `node --check src/server.js && node --check src/tools/logPerformanceInput.js`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add src/tools/logPerformanceInput.js src/server.js
git commit -m "feat(claude): add log_performance_input tool with concept dedup"
```

---

### Task 5: End-to-end tests

**Files:**
- Create: `test/logging.test.js`

**Interfaces:**
- Consumes: same `Client`/`StdioClientTransport` pattern as `test/smoke.test.js` (step 1) — spawns the real server as a child process, calls tools through the real MCP protocol, not unit-testing internals directly.

- [ ] **Step 1: Write the test**

```js
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
```

This directly tests the de-dup backstop (layer 2) end-to-end through the real MCP tool call path, which is the part that's actually verifiable by a script — layer 1 (the LLM choosing to reuse a name after calling `list_concepts`) can't be tested without a live LLM and is verified manually via Qwen Desktop instead, same as the `echo` tool was in step 1.

- [ ] **Step 2: Run tests**

Run: `npm test`
Expected: `# pass 2`, `# fail 0` (both `smoke.test.js` from step 1 and the new `logging.test.js`), exit code 0.

- [ ] **Step 3: Commit**

```bash
git add test/logging.test.js
git commit -m "test(claude): add end-to-end test for log_performance_input dedup"
```

---

### Task 6: Wrap up

- [ ] **Step 1: Update `docs/plan.md`** — mark step 2 done in Current phase, update Backlog.
- [ ] **Step 2: Append to `docs/decisions.md`**:
```
[<timestamp>] [claude] [claude/raw-logging-pipeline] [done] — raw logging pipeline built (concepts/attempts/error_types/attempt_errors schema, log_performance_input + list_concepts tools, concept dedup verified end-to-end); Build Order §12 step 2 done
```
- [ ] **Step 3: Commit**
```bash
git add docs/plan.md docs/decisions.md
git commit -m "docs(claude): log raw logging pipeline completion"
```
- [ ] **Step 4: Merge readiness.** Do not merge to `main`/`master` yourself — human review step (AGENTS.md). Report back for merge approval, same as step 1.

---

## Self-Review Notes

- **Spec coverage:** ex1.md §6 schema (concepts/attempts/error_types/attempt_errors) → Task 2. §10 `log_performance_input` signature and nullable-fields behavior → Task 4. Concept de-dup (docs/plan.md Architecture) → Task 2 (backstop) + Task 3 (LLM-context layer). §11 stack (better-sqlite3, no server-side LLM calls) → Task 1, Task 4's design note. Out-of-scope items (BKT, retention decay, interventions) correctly excluded — those are steps 3/4/6.
- **Placeholder scan:** no TBD/TODO. `context` param accepted-but-unused is explained, not hand-waved — there's genuinely no table to store it in yet.
- **Type consistency:** `findOrCreateConcept(name, subject) -> id` and `listConcepts(subject) -> [{id, name}]` from Task 2 used identically in Task 3 and Task 4. Tool names `list_concepts` and `log_performance_input` match between registration (Tasks 3/4) and the test (Task 5).
- **Verified against real sources:** `better-sqlite3@13.0.3` confirmed current on npm, `engines.node >= 22` confirmed satisfied by installed Node v24.13.1. Fetched the actual `database.js` source and confirmed the `Database` constructor requires a plain string path and throws `TypeError` on anything else (including a `URL` object) — caught and fixed a real bug: Task 2's original code passed `new URL(...)` directly, now wrapped in `fileURLToPath()`. Fetched the real API docs and confirmed `statement.run().lastInsertRowid`, `db.pragma()`, and `db.exec()` usage all match the plan's code exactly. Test-installed `better-sqlite3` in an isolated scratch directory (not this repo) and confirmed it ships a prebuilt `win32-x64.node` binary — no compiler toolchain required — and ran a real insert/select through it to confirm it actually works, not just installs.
