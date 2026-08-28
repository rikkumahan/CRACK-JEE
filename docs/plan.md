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
Step 1 (skeleton MCP server) plan written and saved to
`docs/superpowers/plans/2026-08-29-skeleton-mcp-server.md`. Execution owner
is Antigravity, on branch `antigravity/skeleton-mcp-server` in its own
worktree — Claude Code has not yet run this plan, only authored and
verified it. Once Antigravity finishes, Claude Code independently verifies
(see the plan's "Verification Handoff" section) before anything merges.
Expanded-spec write-up (concept dedup detail + retention-decay formula)
still not started — comes after step 1 lands.

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
1. Skeleton MCP server (not yet in this repo — needs scaffolding here)
2. Raw logging pipeline: `attempts`/`concepts`/`error_types`/
   `attempt_errors` tables + `log_performance_input` (incl. concept dedup
   above) — next real step after expanded spec is written
3. Descriptive analytics: `get_weak_topics`, `get_recurring_mistakes`
4. BKT w/ default params: `student_concept_state`, `get_concept_state`
5. Concept graph, incremental, chapter-by-chapter
6. Interventions + outcome tracking: `generate_daily_plan`, `get_progress`
7. Backup: periodic SQLite copy to Google Drive