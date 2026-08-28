# Skeleton MCP Server Implementation Plan

> **Execution owner: Antigravity.** This plan is written to be self-contained — every command, file, and piece of logic needed is spelled out inline, since Antigravity (per `AGENTS.md`'s "Note on file references") does not reliably expand `@file` references the way Claude Code does. Do not assume access to Claude Code's `superpowers` skills or subagent tooling — follow the numbered steps directly. Steps use checkbox (`- [ ]`) syntax for tracking; check each one off as completed.
>
> **After Antigravity finishes:** Claude Code will independently verify the work (see "Verification Handoff" at the end) before anything gets merged. Do not merge to `main` yourself — per `AGENTS.md`, that is a human review step, and here it additionally waits on Claude's verification pass.
>
> **On parallelism:** Tasks 1–5 below are strictly sequential, not independent work — Task 2 requires `package.json` from Task 1 to exist, Task 3 requires `src/server.js` from Task 2, Task 5 requires everything before it. Do not fan these out in parallel even if you have the capability to run multiple agents at once; doing so risks writing `src/server.js` before `npm install` finishes, or racing edits within Task 4. This particular task has no independent subtasks to parallelize — that opportunity shows up starting step 2 (several read-only analytics tools with no dependencies on each other) and in browser-based testing against Qwen Desktop, not here.

**Goal:** Stand up a from-scratch Node.js MCP server that Qwen Desktop can discover over stdio and call one real tool on — proving the connection end-to-end from inside this repo (not just verified manually elsewhere), per ex1.md Build Order §12 step 1.

**Architecture:** A single-file `McpServer` (from `@modelcontextprotocol/sdk`) registers one tool, `echo`, and connects over `StdioServerTransport`. Verification uses the SDK's own `Client` + `StdioClientTransport` to spawn the server as a child process and call the tool — the same launch mechanism Qwen Desktop will use — so the test is a faithful stand-in for the real integration, no manual app interaction required.

**Tech Stack:** Node.js (v24, already installed), `@modelcontextprotocol/sdk` (verified on npm: v1.30.0, requires Node >=18), `zod` (required peer, SDK's peer range is `^3.25 || ^4.0` — pin `^4.5.1`, the current release), Node's built-in `node:test` runner (no test framework dependency), `node --check` for lint (no ESLint yet). Evaluated and skipped `fastmcp` (real, actively maintained, wraps the official SDK) — its ~11 extra dependencies (hono, execa, yargs, mcp-proxy, etc.) buy conveniences a one-tool skeleton doesn't need; reconsider only once the tool count grows enough to justify the weight.

**Spec:** `ex1.md` (repo root) §4, §10, §11, §12 step 1; working state in `docs/plan.md` / `docs/decisions.md`.

## Global Constraints

- No database, no business-logic tools yet — that's step 2 (`log_performance_input`), explicitly out of scope here (ex1.md §11: "no ML library needed," §12 sequencing).
- No local LLM inference, ever (ex1.md §2, hard constraint).
- Branch: `antigravity/skeleton-mcp-server` (AGENTS.md), created inside its own worktree via `scripts/new-worktree.sh antigravity skeleton-mcp-server` (AGENTS.md isolation rule: "do not cd into... the main checkout"). That script also runs `install-hooks.sh` in the new worktree automatically. All file paths below are relative to that worktree's root, not the main checkout at `c:\Users\rikku\OneDrive\Desktop\JEE_MCP`.
- Commit format: `<type>(antigravity): summary`, type ∈ {feat, fix, chore, docs, refactor, test} — verified against `.githooks-src/commit-msg`'s actual regex: `^(feat|fix|chore|docs|refactor|test)\([a-z0-9-]+\): .+` (AGENTS.md).
- Never use `git commit --no-verify` — the pre-commit hook (`.githooks-src/pre-commit`) reads `# LINT_CMD:` / `# TEST_CMD:` marker lines from `docs/setup.md` verbatim (exact regex: `^# LINT_CMD: ` / `^# TEST_CMD: `) and runs them; a blank/`e.g.`-prefixed value is skipped, not failed.
- Append a `[done]` or `[blocked]` entry to `docs/decisions.md` when finished (AGENTS.md decision-log format).
- Keep `src/tools/` split, ESLint, and a CI workflow file out of scope — none earn their keep for one tool and ~25 lines. Revisit when step 2 adds a second tool.

---

### Task 1: Worktree + project scaffold (`package.json`)

**Files:**
- Create: `package.json` (inside the new worktree, not the main checkout)

**Interfaces:**
- Produces: `npm start` (runs `node src/server.js`), `npm test` (runs `node --test`) — later tasks and `docs/setup.md` depend on these exact script names.

- [ ] **Step 0: Create the isolated worktree**

Run (from the main checkout, `c:\Users\rikku\OneDrive\Desktop\JEE_MCP`):
```bash
bash scripts/new-worktree.sh antigravity skeleton-mcp-server --no-open
```
Expected: creates `../JEE_MCP-antigravity-skeleton-mcp-server` on branch `antigravity/skeleton-mcp-server`, runs `install-hooks.sh` inside it, prints `worktree ready: ...`. All remaining steps in this plan run from inside that new worktree directory, not the main checkout.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "jee-performance-engine",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "test": "node --test"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.30.0",
    "zod": "^4.5.1"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run: `npm install`
Expected: `node_modules/@modelcontextprotocol/sdk` and `node_modules/zod` exist, `package-lock.json` created, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore(antigravity): scaffold package.json"
```

---

### Task 2: Skeleton MCP server with `echo` tool

**Files:**
- Create: `src/server.js`

**Interfaces:**
- Consumes: `@modelcontextprotocol/sdk/server/mcp.js` (`McpServer`), `@modelcontextprotocol/sdk/server/stdio.js` (`StdioServerTransport`), `zod` (`z`).
- Produces: a running MCP server named `jee-performance-engine` v`0.1.0` exposing tool `echo(message: string) -> { content: [{ type: "text", text: message }] }`. Task 3's test and the Qwen Desktop config in Task 5 both depend on this exact tool name and shape.

- [ ] **Step 1: Write `src/server.js`**

```js
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "jee-performance-engine",
  version: "0.1.0",
});

server.registerTool(
  "echo",
  {
    title: "Echo",
    description:
      "Echoes back the message it is given. Used only to verify the MCP connection is alive.",
    inputSchema: { message: z.string() },
  },
  async ({ message }) => ({
    content: [{ type: "text", text: message }],
  })
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

- [ ] **Step 2: Sanity-check syntax**

Run: `node --check src/server.js`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add src/server.js
git commit -m "feat(antigravity): add skeleton MCP server with echo tool"
```

---

### Task 3: End-to-end smoke test

**Files:**
- Create: `test/smoke.test.js`

**Interfaces:**
- Consumes: `src/server.js` (spawned as a child process via `StdioClientTransport({ command: "node", args: ["src/server.js"] })`), `@modelcontextprotocol/sdk/client/index.js` (`Client`), `@modelcontextprotocol/sdk/client/stdio.js` (`StdioClientTransport`).

- [ ] **Step 1: Write the test**

```js
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
```

- [ ] **Step 2: Run it to verify it fails first (TDD sanity check)**

Since `src/server.js` already exists from Task 2, this test should actually PASS on first run — there's no red-then-green cycle for a one-tool skeleton like there would be for real business logic. Run: `node --test` and confirm PASS. If it fails, the server or test has a bug — fix before proceeding, do not adjust the test to match broken behavior.

Run: `npm test`
Expected: `# pass 1`, `# fail 0`, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add test/smoke.test.js
git commit -m "test(antigravity): add stdio smoke test for echo tool"
```

---

### Task 4: Fill in `docs/setup.md`

**Files:**
- Modify: `docs/setup.md` (currently placeholder `# e.g. npm install` etc. — see docs/setup.md:1-24)

**Interfaces:**
- Produces: the exact `# LINT_CMD:` / `# TEST_CMD:` lines the pre-commit hook (`.githooks-src/pre-commit`) parses via `sed -n "s/^# ${marker}: //p"`.

- [ ] **Step 1: Replace the placeholder content**

```markdown
# Setup & Commands

## Install
```
npm install
```

## Lint  (read by pre-commit hook)
```
# LINT_CMD: node --check src/server.js
```

## Test  (read by pre-commit hook)
```
# TEST_CMD: npm test
```

## Run locally
```
npm start
```
```

- [ ] **Step 2: Verify the hook picks up the commands**

Run: `bash .githooks-src/pre-commit` (from repo root; requires `git add` of a change first since the hook is meant to run pre-commit, but it can be run standalone to check output)
Expected: `· pre-commit: running lint -> node --check src/server.js`, then `· pre-commit: running test -> npm test`, then `· pre-commit: passed`.

- [ ] **Step 3: Commit**

```bash
git add docs/setup.md
git commit -m "docs(antigravity): fill in setup commands for pre-commit hook"
```

---

### Task 5: Wire up Qwen Desktop (manual, non-repo step)

**Files:** none (no repo changes — this step confirms the repo's server works with the real client)

- [ ] **Step 1: Confirm `npm install` has been run** (done in Task 1) so `node_modules/@modelcontextprotocol/sdk` and `node_modules/zod` exist — Qwen Desktop does not run `npm install` itself.

- [ ] **Step 2: Add the server in Qwen Desktop**

Settings → MCP → My MCP → Add MCP → "Add using JSON". The server code lives in the worktree created in Task 1 (`scripts/new-worktree.sh` puts it at `../JEE_MCP-antigravity-skeleton-mcp-server` relative to the main checkout, i.e. `C:\Users\rikku\OneDrive\Desktop\JEE_MCP-antigravity-skeleton-mcp-server`), not the main checkout — point Qwen Desktop there for now:

```json
{
  "mcpServers": {
    "jee-performance-engine": {
      "command": "node",
      "args": [
        "C:\\Users\\rikku\\OneDrive\\Desktop\\JEE_MCP-antigravity-skeleton-mcp-server\\src\\server.js"
      ]
    }
  }
}
```

Once this branch is reviewed and merged to `main` (a human review step — AGENTS.md), update the path back to the main checkout, `C:\Users\rikku\OneDrive\Desktop\JEE_MCP\src\server.js`, and remove the worktree (`git worktree remove`).

- [ ] **Step 3: Restart Qwen Desktop, confirm `echo` is listed and callable** — ask it to call the tool with a test message and confirm the response echoes back.

- [ ] **Step 4: Update the decision log**

Append to `docs/decisions.md`:
```
[<current timestamp>] [antigravity] [antigravity/skeleton-mcp-server] [done] — skeleton MCP server with echo tool built and verified end-to-end (smoke test + live Qwen Desktop call); Build Order §12 step 1 now actually true in-repo, not just verified elsewhere
```

- [ ] **Step 5: Commit and merge readiness**

```bash
git add docs/decisions.md
git commit -m "docs(antigravity): log skeleton MCP server completion"
```
Do not merge to main — that's a human review step (AGENTS.md).

---

## Self-Review Notes

- **Spec coverage:** ex1.md §4 (hosting via Qwen Desktop stdio MCP) → Task 5. §11 (stack: Node.js, SDK, no bundled LLM) → Task 1/2. §12 step 1 (skeleton server, prove connection before real logic) → whole plan. §10's tool-response shape (`content: [{ type: "text", ... }]`) → Task 2, reused pattern for future tools. Database/BKT/analytics (§5-§9) correctly out of scope — that's step 2 onward.
- **Placeholder scan:** no TBD/TODO, no "add appropriate error handling" — none needed, `echo` has no failure modes worth handling at this scope (a required string arg that Zod already validates).
- **Type consistency:** tool name `echo`, arg shape `{ message: string }`, response `{ content: [{ type: "text", text }] }` used identically in Task 2 (server), Task 3 (test), Task 5 (manual check).
- **Re-verification pass (second pass, against real sources, not assumptions):** confirmed `@modelcontextprotocol/sdk@1.30.0` and `zod@4.5.1` are real current npm versions; confirmed via actual `.d.ts` files (fetched from unpkg) that `registerTool`'s `inputSchema` takes a raw Zod-shape object (not `z.object(...)`), that `Client.listTools()` returns `{ tools: [...] }`, `Client.callTool()` returns `{ content: [...] }`, and both `StdioServerTransport`/`StdioClientTransport` constructors match the plan's usage. Confirmed `.githooks-src/pre-commit` and `commit-msg` are already installed in `.git/hooks/` in this repo (not just tracked source), and that commit-msg's actual regex accepts all planned commit messages. Caught and fixed one real bug: Task 1 originally branched directly in the main checkout (`git checkout -b`), violating AGENTS.md's worktree-isolation rule — now Task 1 Step 0 runs `scripts/new-worktree.sh` first, and Task 5's Qwen Desktop config path was corrected to point at the worktree, not the main checkout.

---

## Verification Handoff (Claude Code, after Antigravity finishes)

Do not just re-read the diff and eyeball it — run these checks and report pass/fail on each, in this order:

1. **Location and isolation:** confirm the worktree exists at
   `C:\Users\rikku\OneDrive\Desktop\JEE_MCP-antigravity-skeleton-mcp-server`,
   is on branch `antigravity/skeleton-mcp-server`, and that the main checkout
   (`C:\Users\rikku\OneDrive\Desktop\JEE_MCP`) has no stray uncommitted
   changes from this work (`git status` in the main checkout should be
   clean of anything related to this task).
2. **Commit hygiene:** `git log` on the branch — every commit message must
   match `^(feat|fix|chore|docs|refactor|test)\(antigravity\): .+`
   (the real regex from `.githooks-src/commit-msg`), and there should be no
   `--no-verify` bypass (check reflog / hook output isn't suspiciously
   absent for any commit).
3. **File-for-file diff against this plan:** `package.json` matches Task 1
   exactly (name, `type: module`, scripts, the two pinned dependency
   versions — flag it if Antigravity substituted different versions or
   added dependencies not in this plan, e.g. `fastmcp` or an unrelated test
   framework). `src/server.js` matches Task 2's code (tool name `echo`,
   `inputSchema: { message: z.string() }` — not `z.object(...)`, response
   shape `{ content: [{ type: "text", text }] }`). `test/smoke.test.js`
   matches Task 3 (uses `node:test` + the SDK's own `Client`/
   `StdioClientTransport`, not a different test runner).
4. **Actually run it, don't trust a status report:** in the worktree, run
   `npm install` (if not already done), then `npm test` — expect
   `# pass 1`, `# fail 0`. Then run `node --check src/server.js` — expect
   silent success. Then run `bash .githooks-src/pre-commit` — expect it to
   report running both lint and test commands (confirms `docs/setup.md`
   was actually filled in, not left as placeholder).
5. **`docs/setup.md` and `docs/decisions.md`:** confirm `docs/setup.md`'s
   `# LINT_CMD:` / `# TEST_CMD:` lines exactly match Task 4, and
   `docs/decisions.md` has a new `[antigravity]` entry in the correct
   format (AGENTS.md: `[YYYY-MM-DD HH:MM] [tool] [branch] [status] — what / why`).
6. **Live Qwen Desktop check:** this one can't be automated — ask the user
   to confirm they completed Task 5 Step 3 (restarted Qwen Desktop, saw
   `echo` listed, called it, got the message back). Do not mark this plan
   complete without that confirmation, since it's the actual point of the
   task (ex1.md Build Order §12 step 1: prove Qwen Desktop can discover and
   call a tool on this server).

If any check fails, report exactly which one and why — do not silently fix
Antigravity's work without saying so; the point of this handoff is an
independent check, not a rubber stamp.
