# Migration: Node.js/MCP SDK → Python/FastMCP

_Written 2026-09-14. Full-replacement migration of the currently-built
portion of the MCP server (Steps 1–2 in `ex1.md` §12: skeleton + raw
logging pipeline) from Node.js to Python. TDD throughout: for every piece,
a failing test is written first, ported from the exact scenario the
existing JS test already covers, before any implementation code._

**Why, briefly (full reasoning already in this conversation, not repeated
here):** cheapest point in the build to switch (only 2 small steps exist);
`uvx` is a first-class command in MCP client config UIs generally, unlike
the raw-node-path workaround currently relied on; unifies with the
synthetic-KT research track (`research/synthetic_jee_kt/`, handed to
Antigravity separately), which is already Python — one BKT implementation
instead of two that can drift. **Not** about any specific chat client —
MCP is a standard protocol; this must work with any MCP-compatible client,
not just the one used during earlier debugging.

## Scope

Port exactly the current behavior, nothing more:
- `echo` tool (connection-liveness check)
- `list_concepts` tool
- `log_performance_input` tool, including concept dedup
  (normalize-and-compare — not a new feature, an exact port)
- The `concepts`/`attempts`/`error_types`/`attempt_errors` schema and seed
  data, unchanged

**Explicitly out of scope for this migration:** Steps 3a–6b (the 5 unbuilt
tools in `docs/tool-implementation-plan.md`) — those get built fresh in
Python once this migration lands, not ported (they don't exist in JS yet).
Do not start them as part of this task.

## Current implementation (source of truth for the port — read directly, not from memory)

- `src/server.js` — registers `echo` inline, then `list_concepts` and
  `log_performance_input` via their own modules; connects over stdio.
- `src/db.js` — `better-sqlite3`, WAL mode, `busy_timeout=5000`; schema
  exactly as in `ex1.md` §6 (concepts/attempts/error_types/attempt_errors);
  seeds `error_types` with `concept_gap | calculation | misread |
  time_pressure | unattempted | unknown`; `normalize(name)` = lowercase,
  strip everything but `[a-z0-9]`; `findOrCreateConcept` scans existing
  concepts *within the same subject*, compares normalized names, returns
  existing id or inserts a new row.
- `src/tools/listConcepts.js` — trivial passthrough to `listConcepts(subject)`.
- `src/tools/logPerformanceInput.js` — zod schema (`subject`, `concept`,
  `result` enum, optional `error_type` enum/`time_seconds`/`notes`/
  `context`), inserts one `attempts` row, and if `error_type` given, one
  `attempt_errors` row referencing it.
- `test/smoke.test.js` — spawns the real server subprocess over stdio,
  lists tools, calls `echo`, asserts round-trip.
- `test/logging.test.js` — resets the db file, logs "Rotational Motion"
  then "rotational motion" (different casing/phrasing), asserts
  `list_concepts` returns exactly one deduped row named "Rotational Motion".

**Every tool description string is copied verbatim in the port** — these
are the prompt-engineering surface (what an LLM client reads to decide
when/how to call the tool); don't "improve" the wording while porting
logic, that's a separate, deliberate task if ever done at all.

## Target stack

- **Server:** `fastmcp` (Python).
- **Database:** Python stdlib `sqlite3` — no third-party dependency
  needed, matches `better-sqlite3`'s synchronous, zero-config nature.
  Same `data/jee.db` path, same WAL + busy_timeout pragmas.
- **Tests:** `pytest`. Two tiers, both required (matches the existing
  JS tests' actual coverage, not a downgrade):
  1. **Fast, in-process** — FastMCP's own `Client` can connect directly to
     a server object in the same process, no subprocess. Use this for the
     TDD inner loop (dedup logic, tool argument handling).
  2. **Stdio subprocess, black-box** — at least one test per tool spawns
     the real server as a subprocess over stdio and drives it through a
     real MCP client, matching what `smoke.test.js`/`logging.test.js` do
     now. This is what previously caught a real integration bug (the
     SQLITE_BUSY race from parallel subprocess test execution, per
     `decisions.md` 2026-08-29 05:10) that an in-process test would have
     missed — don't drop this tier for convenience.
- **Packaging:** `pyproject.toml`, not `requirements.txt` — matches
  `fastmcp`/`uvx`'s own conventions and is what makes `uvx <package>`
  launchable at all.

## Project structure

```
src/
├── server.py            # registers echo + list_concepts + log_performance_input, stdio entrypoint
├── db.py                # schema, seed data, normalize(), find_or_create_concept(), list_concepts()
└── tools/
    ├── list_concepts.py
    └── log_performance_input.py
tests/
├── test_smoke.py         # stdio subprocess: echo round-trip
├── test_logging.py       # stdio subprocess: dedup scenario, byte-for-byte same assertions as logging.test.js
└── test_db.py            # in-process/unit: find_or_create_concept, normalize(), schema creation
pyproject.toml
```

(Old `src/*.js`, `test/*.js`, `package.json` stay in place until the
decommission step below — do not delete them mid-migration.)

## Build order (TDD at every step — test first, watch it fail, then implement)

1. **Project skeleton.** `pyproject.toml` with `fastmcp` + `pytest`
   dependencies. No server code yet.
2. **DB layer.** Write `tests/test_db.py` first: schema creates all 4
   tables + seeds the 6 error types; `find_or_create_concept("Rotational
   Motion", "Physics")` then `find_or_create_concept("rotational motion",
   "Physics")` returns the same id; a different subject with the same
   normalized name creates a separate concept (this is implied by the
   current `WHERE subject = ?` scoping — preserve it, don't "fix" it as
   part of this port). Then implement `src/db.py` until green.
3. **Echo tool + stdio wiring.** Port `test_smoke.py` from
   `smoke.test.js` (list tools, call `echo`, assert round-trip) — this is
   the step that actually proves `uvx`/stdio works end-to-end before
   anything else depends on it, same purpose Step 1 originally served.
   Implement `src/server.py` with just `echo` until green.
4. **`list_concepts` + `log_performance_input`.** Port
   `test_logging.py` from `logging.test.js` verbatim (same dedup
   scenario, same assertion: exactly one concept named "Rotational
   Motion"). Implement both tools until green.
5. **Verify `uvx` launch, client-agnostically.** A raw JSON-RPC
   stdio handshake test (same technique used to debug the original `npx`
   issue, per `decisions.md` 2026-08-29 — spawn the process, write an
   `initialize` request to stdin, confirm a `result` comes back on
   stdout) run against `uvx <package>` specifically, not just `python
   src/server.py` — this is the one substantive risk in this migration
   (does `uvx` have its own version of the `bun.exe`-interception
   surprise?) and must be checked directly, not assumed clean because the
   in-process/subprocess-via-python tests passed.
6. **Decommission the Node implementation — do not do this automatically.**
   Once steps 1–5 are green and step 5's `uvx` check is confirmed clean,
   stop and report back rather than deleting `src/*.js`/`test/*.js`/
   `package.json`/`node_modules` — that's a one-way door (removing a
   working, tested implementation) and gets a human go-ahead first, not
   an Antigravity judgment call.

## What this migration does not decide

- `docs/tool-implementation-plan.md`'s Steps 3a–6b are written in
  Node/zod/better-sqlite3 conventions. Once this migration lands, that
  doc needs a Python-conventions rewrite before those steps are built —
  flagged here as a known follow-up, not done as part of this task.
- No client-specific configuration (Qwen Desktop or otherwise) is part of
  this plan — verify the connection generically (step 5), not against any
  one app's UI.

## Antigravity workflow (per `AGENTS.md`)

- Branch: `antigravity/fastmcp-migration`, own worktree.
- Commits: `feat(antigravity): summary` / `test(antigravity): summary` per
  step above — small, TDD-shaped commits (test, then implementation) are
  preferred over one large commit at the end.
- `[claimed]` on start, `[done]`/`[blocked]` on finish, in `docs/decisions.md`,
  same format as existing entries.
- Stop and report after step 5, before step 6 (decommission) — that step
  needs explicit sign-off, per the one-way-door note above.
- Do not merge to `main`.
