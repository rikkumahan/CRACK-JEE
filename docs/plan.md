# Project Plan

_Last updated: 2026-08-29_

## Goal
JEE Performance Engine: a local MCP server (Node.js + better-sqlite3) that
Qwen Desktop talks to via stdio. Ingests a single JEE aspirant's test
performance in any format, mines recurring mistake patterns across tests
(not per-test, which is all her Aakash reports give her), prescribes a
concrete next-day action, and verifies whether it worked on the next test.
Full spec: `ex1.md` at repo root (validated 2026-08-27/29, sound).

## Current phase
Step 1 (skeleton MCP server, built by Antigravity) and step 2 (raw logging
pipeline, built by Claude Code) are both DONE and merged to `master`
(currently at commit `cb84335`). Server exposes three tools: `echo`,
`list_concepts`, and `log_performance_input`, backed by a SQLite schema
(`concepts`/`attempts`/`error_types`/`attempt_errors`) with concept
de-duplication implemented and tested end-to-end (`test/logging.test.js`,
2/2 passing).

**Repo location changed:** moved from `C:\Users\rikku\OneDrive\Desktop\
JEE_MCP` to `C:\dev\JEE_MCP` on 2026-08-29. Reason: OneDrive's real-time
sync was locking files mid-operation, causing repeated `git worktree
remove` failures ("device or resource busy") and file-cleanup warnings
during `npm`/`npx` operations. The old OneDrive folder may still exist
(locked, pending OneDrive releasing it) — it is stale, do not use it.
**Any tool picking up this project should confirm it is working from
`C:\dev\JEE_MCP`, not the old OneDrive path.**

**Step 2b (MCP connection root cause & strategy) — Resolved (2026-08-29):**
Root cause identified by decompiling Qwen Desktop internals: client command runner translates `npx` to bundled `bun.exe x -y` and queries remote npm registry (failing on unpublished local packages), while also overriding Windows `PATH` with colon-separated paths. Standard MCP clients use `node <path>/src/server.js` during development; zero-install public `npx -y` distribution will be published to npm upon release. Unblocked for Step 3.


Retention-decay formula (open question below) still not pinned down —
not blocking, since it's needed for step 4 (BKT), not step 3.

## Architecture / key decisions
- LLM (Qwen's cloud model) used only for extraction + the daily-plan
  reasoning step. Everything else (stats, BKT mastery updates, rankings) is
  deterministic code — no trained ML models. See ex1.md §3, §7.
- BKT with fixed literature-default parameters, not fitted — data volume
  per concept is far too low to fit reliably (see ex1.md §7.2 for the
  pyKT-based reasoning on why every trained KT model was rejected).
- No local LLM inference, ever — hard constraint from project start.
- Concept de-duplication for `log_performance_input` (confirmed 2026-08-29,
  not in original ex1.md draft): without it the LLM will mint "Rotational
  Motion" and "Rotational Dynamics" as two different `concepts` rows across
  two tests, silently splitting mastery history and defeating the
  cross-test pattern mining that's the system's core value. Two-layer fix:
  1. Pass the existing concept list for that subject to the LLM before
     extraction, instruct it to reuse a match or flag "new concept" —
     leans on the LLM's domain knowledge, which string similarity can't
     replicate.
  2. Deterministic backstop on write: normalize (lowercase, strip
     non-alphanumeric) and exact-match against existing concepts before
     inserting — catches casing/spacing/punctuation slips. No embeddings,
     no fuzzy-matching library — add only if real usage shows this missing
     cases.

## Open questions
- Retention/forgetting decay (ex1.md §7.3) is named — "simple time-decay
  nudge" — but has no concrete formula yet (decay rate, trigger window,
  when applied). Needs pinning down when the expanded spec is written.

## Backlog
Build order (ex1.md §12), in sequence:
1. ~~Skeleton MCP server~~ — done (merged)
2. ~~Raw logging pipeline~~ — done (merged, `concepts`/`attempts`/
   `error_types`/`attempt_errors` + `log_performance_input`/`list_concepts`,
   concept dedup implemented and tested)
2b. Qwen Desktop MCP wiring — BLOCKED, handed to Antigravity (see Current
   phase above). Server code is correct and tested; this is purely a
   client-integration/config problem, not a code problem.
3. Descriptive analytics: `get_weak_topics`, `get_recurring_mistakes` —
   next, but blocked behind 2b since it needs live tool calls to verify
4. BKT w/ default params: `student_concept_state`, `get_concept_state`
5. Concept graph, incremental, chapter-by-chapter
6. Interventions + outcome tracking: `generate_daily_plan`, `get_progress`
7. Backup: periodic SQLite copy to Google Drive