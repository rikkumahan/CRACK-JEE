# Production readiness notes (post-hackathon)

Written 2026-09-15, after the hackathon build order (all 7 MCP tools) closed.
Not a plan doc — a punch list to work through, priority order.

## 1. Kill the Node server
`src/server.js` + `src/db.js` are dead weight now that Python/FastMCP has full
parity. The pre-commit hook currently runs both suites (`uv run pytest && npm
test`) on every commit for no reason, and `docs/setup.md` documents two
install paths. Before deleting: confirm nothing external still launches
`node src/server.js` (check whatever MCP client config exists, per the
Qwen Desktop saga in `docs/decisions.md`). Then delete `src/*.js`, drop
`npm test`/`npm start` from `package.json`, drop `npm test` from the
`TEST_CMD` line, update `setup.md`.

## 2. Fix or ship the uvx launch path — DONE, published to PyPI
Published as `crack-jee` on PyPI (2026-09-17). `docs/setup.md` now leads
with `uvx crack-jee` (from the index) as the real launch path and
documents `uvx --from . crack-jee` separately as pre-publish/local-source
testing only. Verified live: a fresh `uvx crack-jee` pulls from PyPI and
completes a real JSON-RPC `initialize` handshake.

## 3. Commit or ignore the hackathon artifacts
`git status` is dirty: `README.md` staged but not committed;
`build_deck.py`, `presentation.html`, `jee_student_modeling_research_landscape.md`,
`student_modeling_research_map.md`, the pptx, and its `~$...pptx` lock file
are untracked. Decide per-file: commit the real ones (maybe under a
`presentation/` folder), gitignore the lock file and any other Office temp
files. Don't start production work with a dirty tree.

## 4. Check SQLite concurrency story — DONE, already safe
Checked 2026-09-16: `src/db.py`'s `init_db` sets both
`PRAGMA journal_mode = WAL` and `PRAGMA busy_timeout = 5000` on every
connection it creates (the only `sqlite3.connect()` call site in `src/`,
confirmed via grep). `get_connection()` always routes through `init_db()`,
so there's no bypass — this carries the same safeguard the Node layer
needed (2026-08-29 log entry), no code change required.

## 5. Concept graph (Build Order step 5) — leave it
Explicitly deferred/incremental by design, not a gap. Don't build ahead of
actual need.

---

## Will this work for other competitive exams, not just JEE?

**Yes, the shipped MCP server itself is exam-agnostic.** Checked the actual
code, not just the name:
- `concepts.subject` and `concept` are free-text strings passed in by whoever
  calls `log_performance_input` — nothing hardcodes "Physics/Chemistry/Maths"
  or a JEE syllabus. Works the same for NEET, boards, GRE vocab, whatever the
  caller logs.
- BKT parameters in `src/bkt.py` (P(L0)=0.20, P(T)=0.10, P(S)=0.10, P(G)=0.25)
  are literature-default constants, not fit to JEE data — they're generic
  knowledge-tracing defaults, exam-independent.
- The only place "JEE" appears in the shipped tool is cosmetic: the db
  filename (`jee.db`), the package name, and the system prompt's phrasing
  ("her coaching institute"). None of that is load-bearing logic.

**What's actually JEE-specific is the separate research track**
(`research/synthetic_jee_kt/`) — eQOURSE item bank, JEE-specific synthetic
student simulation, the LKT/BKT benchmark. That's a research workstream
evaluating *which model to use*, not the shipped product. It doesn't limit
what the MCP server itself can track.

**Caveat:** the workflow (system prompt in `docs/chat-client-system-prompt.md`)
assumes free-text concept/result extraction from natural language, which
works for any exam, but it was designed and tuned around one real JEE
student's usage pattern — swapping exams is a config/prompt change, not a
code change, but it hasn't actually been tried on non-JEE data yet.
