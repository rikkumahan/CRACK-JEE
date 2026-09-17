<p align="center">
  <img src="assets/banner.png" alt="CRACK-JEE — Plan smarter, Prepare better" width="100%">
</p>

<p align="center">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-red">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-red">
  <img alt="Protocol: MCP" src="https://img.shields.io/badge/protocol-MCP-black">
  <img alt="Local-first" src="https://img.shields.io/badge/data-local--only-black">
</p>

<p align="center">
  A personal AI coach for JEE aspirants, built as an MCP server. Not a tutor,
  not a chatbot with a syllabus bolted on — it turns raw test results into a
  closed feedback loop: log what happened, find the patterns a single test
  report can never show, get a concrete next study plan, and verify whether
  it actually worked on the next test.
</p>

<p align="center">
  Free. Local. No subscription, no hosting bill, no data leaving your machine
  except to whatever LLM chat client you connect it to.
</p>

---

## Why

Coaching institute reports are siloed — each test is graded in isolation. Two
things never happen on their own:

1. **Cross-test pattern mining.** The same mistake, on the same concept,
   across five different tests over two months, looks like five unrelated
   bad days unless something is tracking it. CRACK-JEE finds it.
2. **Closed-loop verification.** A coach tells you to fix something. Nobody
   goes back after the next test and checks whether it worked. CRACK-JEE
   does, automatically, every time.

Everything in between — mastery estimation, what's about to be forgotten,
where you're burning time versus actually stuck, skip-vs-wrong strategy
under negative marking — is plain deterministic code, not a trained model.
An LLM only extracts messy input into structured data and writes the study
plan in your coach's voice; every number it reasons over comes from
arithmetic and SQL, not inference.

---

## How it works

<p align="center">
  <img src="assets/how-it-works.png" alt="How CRACK-JEE works: describe a test, LLM extracts structured data, deterministic analytics engine, LLM reasons over it and writes a plan, next test closes the loop" width="100%">
</p>

Connect it to any MCP-capable chat client (Claude Desktop, Qwen Desktop,
etc.) and just talk to it like a coach — describe results in whatever format
you have, ask what to study, mention an upcoming exam and its syllabus.

---

## What it tracks

| Capability | What it answers |
|---|---|
| Weak topics | Which concepts have the worst accuracy — and separates "skipped wisely" from "guessed and got it wrong," since JEE's negative marking makes those different problems |
| Recurring mistakes | Which error types repeat on the same concept across multiple tests — the thing a single per-test report can't show |
| Concept mastery (BKT) | A real probability of knowing each concept, updated after every attempt, with retention decay applied over time |
| Revision due | What's about to be forgotten and should be revised before that happens |
| Time patterns | Whether you're genuinely stuck on a concept (spending much longer on wrong answers) versus just making quick errors |
| Student profile | Overall pace, time-management tendencies, and subject strengths across everything logged so far |
| Exam planning | A full study plan for an upcoming exam's syllabus, accounting for topics you haven't touched yet |
| Progress verification | Before/after accuracy on a concept or exam once a plan has been acted on — the closed loop |

17 MCP tools total, covering logging, analytics, daily planning, exam
planning, and progress verification. See [`docs/plan.md`](docs/plan.md) for
the full build history and [`docs/chat-client-system-prompt.md`](docs/chat-client-system-prompt.md)
for exactly how a connected client is expected to use them.

---

## Quick Start (no coding experience needed)

You don't need to know how to code to use this — five steps, about two
minutes.

**1. Install an MCP-capable chat app** if you don't already have one —
this is what you'll actually talk to. Two good options:
- [Claude Desktop](https://claude.ai/download) (free)
- [Qwen Desktop](https://qwen.ai/) — steps 3-4 differ slightly, see the
  note at the end

**2. Install `uv`.** It's a small tool that lets Claude Desktop download
and run CRACK-JEE automatically — you only do this once, ever. Open:
- **Windows:** PowerShell (search "PowerShell" in the Start menu)
- **Mac:** Terminal (search "Terminal" in Spotlight)

and paste in the matching command, then press Enter:

```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**3. Open Claude Desktop's settings** → **Developer** tab → **Edit Config**.
This opens a text file called `claude_desktop_config.json`.

**4. Paste this in** (replace the whole file if it's empty, or add the
`"crack-jee"` block if you already have other servers configured):

```json
{
  "mcpServers": {
    "crack-jee": {
      "command": "uvx",
      "args": ["crack-jee"]
    }
  }
}
```

Save the file.

**5. Restart Claude Desktop completely** (quit it, not just close the
window, then reopen). That's it — try typing something like:

> "I just did a Physics mock test — got Rotational Motion questions wrong,
> skipped 2 Organic Chem ones I wasn't sure about."

If it responds by logging the results and asking follow-up questions
instead of just chatting normally, it's connected and working.

**Using Qwen Desktop instead?** Skip steps 3-4 above and instead go to
Settings → MCP → My MCP → Add MCP → **Add using JSON**, and paste the
same JSON block from step 4. Qwen Desktop's form only accepts `uvx` or
`npx` as the command — since `crack-jee` runs via `uvx`, it fits
natively, no workaround needed.

*Using some other MCP-capable client? Same JSON block works — just find
that app's own config file instead.*

---

## Setup (technical reference)

Requires [Python ≥ 3.10](https://www.python.org/) and
[`uv`](https://github.com/astral-sh/uv). Published on PyPI as
[`crack-jee`](https://pypi.org/project/crack-jee/) — zero local install needed.
For the plain-language version, see [Quick Start](#quick-start-no-coding-experience-needed)
above.

Connect it from any MCP client by pointing it at `uvx crack-jee`, e.g.:

```json
{
  "mcpServers": {
    "crack-jee": {
      "command": "uvx",
      "args": ["crack-jee"]
    }
  }
}
```

### For development

Running from source instead of the published package:

```bash
uv sync
uv run python src/server.py   # runs the server on stdio
```

```json
{
  "mcpServers": {
    "crack-jee": {
      "command": "uv",
      "args": ["run", "--directory", "C:/path/to/CRACK-JEE", "python", "src/server.py"]
    }
  }
}
```

See [`docs/setup.md`](docs/setup.md) for exact commands.

### Test

```bash
uv run pytest tests/ -v
```

---

## Design principles

- **Deterministic core, LLM at the edges.** The LLM extracts and writes
  plans in natural language; every mastery estimate, ranking, and trend is
  plain code — reproducible, debuggable, and free to run.
- **Fixed-parameter BKT, not a trained model.** A single student's few
  hundred attempts is a different data regime than the population-scale
  data DKT/AKT/SAINT-style models need. See [`ex1.md §7`](ex1.md) for the
  full reasoning, and [`research/synthetic_jee_kt/`](research/synthetic_jee_kt/)
  for the benchmark that backs the decision.
- **Never invents an answer.** If a tool call fails on bad input or
  something's ambiguous, the client is instructed to ask rather than guess
  and log something wrong into your history.
- **Exam-agnostic.** Nothing hardcodes JEE's subjects or syllabus — concept
  and subject are free-text fields set by whoever logs the data. Works the
  same for any exam; JEE is just what it was built for.

Full rationale for every non-obvious decision, including rejected
approaches, is in [`docs/decisions.md`](docs/decisions.md) (append-only
log) and [`ex1.md`](ex1.md).

---

## Project structure

```
CRACK-JEE/
├── src/
│   ├── server.py       # FastMCP server entrypoint
│   ├── db.py            # SQLite schema, queries, concept dedup
│   ├── bkt.py            # BKT closed-form Bayesian update + retention decay
│   └── tools/            # One file per MCP tool, registered in server.py
├── tests/                # Test suite (pytest)
├── research/synthetic_jee_kt/   # Independent KT-model benchmark, not part of the server
├── docs/                 # Design docs, decision log, setup instructions
├── presentation/         # Hackathon deck source + related notes, not part of the server
└── pyproject.toml
```

---

## License

MIT — see [`LICENSE`](LICENSE).
