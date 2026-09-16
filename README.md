# JEE Performance Engine

A personal, local MCP server that acts as a performance coach for a JEE aspirant — not a tutor, not a chatbot. It ingests whatever test data she has, mines recurring mistake patterns **across tests** (the gap Aakash's per-test reports leave), prescribes a concrete next-day plan, and verifies whether that plan actually worked on her next test.

Built as a gift. Zero cost, zero hosting bill, zero ongoing maintenance.

---

## What it does

Aakash gives per-test reports. This fills two gaps those reports never close:

1. **Cross-test pattern mining** — same error type hitting the same concept across multiple tests? This finds it. Aakash can't, because each report is siloed.
2. **Closed-loop verification** — after a plan is prescribed and she acts on it, the next test's data is compared against the baseline. The loop closes. Aakash never does this.

### The 6-stage pipeline

```
STUDENT INPUT  →  LLM EXTRACTION  →  RAW EVENT DB  →  ANALYTICS ENGINE  →  DECISION ENGINE  →  INTERVENTION OUTCOME
     ↑                                                                                                      │
     └──────────────────────────────────── feedback loop ──────────────────────────────────────────────────┘
```

1. **Student input** — any format: exam paper + key + her notes, a full Aakash report, or just a sentence. Nothing is rejected for being the wrong format.
2. **LLM extraction** — the LLM (Qwen, running in the chat UI) converts messy input into structured evidence. Missing fields are nullable and never block a log.
3. **Raw event database** — immutable SQLite log. Source of truth. Nothing is hand-edited here.
4. **Analytics engine** — pure deterministic code: SQL aggregations, BKT Bayesian update (closed-form, no ML library), retention decay nudge.
5. **Decision engine** — ranks weaknesses by recoverable-marks potential; LLM produces a concrete time-blocked plan (not "revise Physics for 2 hours").
6. **Intervention outcome** — measures accuracy/time/mastery before vs. after. Writes to `intervention_outcomes`. This is the loop.

---

## Architecture

```
Qwen Desktop (local install)
  Chat UI  ←→  Qwen Cloud API  (inference only, free tier)
       │
       │  stdio MCP (launched automatically from config)
       ▼
  JEE Performance Engine  (local Python/FastMCP server)
       │
       │  reads/writes
       ▼
  jee_performance.db  (local SQLite file)
       │
       │  periodic backup
       ▼
  Google Drive  (backup only)
```

**Core principle:** The LLM is used only for extraction and daily-plan reasoning. Every statistic, ranking, and mastery estimate is deterministic code — plain SQL, arithmetic, or a closed-form Bayesian update. Nothing is a trained model.

---

## MCP Tools

| Tool | Group | Description |
|---|---|---|
| `echo` | utility | Health-check / smoke test |
| `list_concepts` | logging | List all tracked concepts, optionally filtered by subject |
| `log_performance_input` | logging | Ingest raw test data in any format; LLM extracts structured fields |
| `get_weak_topics` | analytics | Accuracy & error-rate aggregation per concept |
| `get_recurring_mistakes` | analytics | Same `error_type × concept` pairs appearing across 2+ tests |
| `get_concept_state` | analytics | Current BKT mastery probability per concept (with retention decay) |
| `generate_daily_plan` | planning | LLM-generated, time-blocked intervention; writes to `interventions` |
| `get_progress` | planning | Before/after accuracy & mastery compared at concept level |

---

## Database Schema

```
concepts                    attempts                    error_types
├── id                      ├── id                      ├── id
├── name                    ├── concept_id (FK)         ├── name
├── subject                 ├── result                  └── description
└── created_at              ├── time_seconds
                            └── created_at

attempt_errors              student_concept_state       interventions
├── id                      ├── id                      ├── id
├── attempt_id (FK)         ├── concept_id (FK)         ├── concept_id (FK)
├── error_type_id (FK)      ├── mastery_probability     ├── recommendation
└── notes                   ├── attempts                ├── created_at
                            └── last_updated_at         └── status

intervention_outcomes
├── id
├── intervention_id (FK)
├── accuracy_before / accuracy_after
├── time_before / time_after
├── mastery_before / mastery_after
└── created_at
```

**Error types:** `concept_gap`, `calculation`, `misread`, `time_pressure`, `unattempted`, `unknown`.

---

## Knowledge Tracing

BKT with **fixed, literature-default parameters** — not fitted. Parameters:

| Parameter | Value | Meaning |
|---|---|---|
| P(L0) | 0.20 | Prior probability of knowing the concept |
| P(T) | 0.10 | Probability of learning it on any attempt |
| P(S) | 0.10 | Slip: knows it but answers wrong |
| P(G) | 0.25 | Guess: doesn't know it but answers right |

Why not a trained model (DKT, AKT, SAINT, reKT)? Every model in pyKT requires gradient descent + training data across thousands of students. A single student's few hundred attempts is a fundamentally different data regime, not a smaller version of the same problem. See [`ex1.md §7`](ex1.md) for the full reasoning.

**Retention decay:** mastery estimates decay slightly after 14 days of no attempts on a concept (×0.97/week, floor 0.30). Applied read-time only — the raw event log is never modified.

---

## Setup

### Prerequisites
- [Python ≥ 3.10](https://www.python.org/) with [`uv`](https://github.com/astral-sh/uv) installed
- [Node.js](https://nodejs.org/) (for the legacy Node server — still passing, not yet decommissioned)

### Install

```bash
# Python server (current — use this one)
uv sync

# Node server (legacy, only needed if you're touching the JS side)
npm install
```

### Run

```bash
# Development: run the Python server directly on stdio
uv run python src/server.py

# Production: run via uvx (how a real MCP client launches it)
uvx --from . jee-performance-engine
```

### Test

```bash
# Python test suite (35 tests)
uv run pytest tests/ -v

# Node test suite (2 tests — legacy logging pipeline)
npm test

# Research track (isolated venv, run from its own directory)
cd research/synthetic_jee_kt
uv sync
uv run pytest tests/ -v
```

---

## Connecting to Qwen Desktop

Two ways to wire the server in Qwen Desktop:

**Option A — Development (recommended):**
In Qwen Desktop → Settings → MCP → My MCP → Add using JSON:
```json
{
  "mcpServers": {
    "jee-performance-engine": {
      "command": "node",
      "args": ["C:\\dev\\JEE_MCP\\src\\server.js"]
    }
  }
}
```

> **Note:** Qwen Desktop intercepts any `npx` command and replaces it with its bundled `bun.exe x -y`, which queries the remote npm registry and fails for local/unpublished packages. During development, use `node <path>/src/server.js` directly. See [`docs/decisions.md`](docs/decisions.md) (2026-08-29 entry) for the full root-cause analysis.

**Option B — Production (future):** Once published to npm, `npx -y jee-performance-engine` will work zero-install.

---

## Project Structure

```
JEE_MCP/
├── src/
│   ├── server.py              # FastMCP server entrypoint (Python, current)
│   ├── db.py                  # SQLite schema, queries, concept dedup
│   ├── bkt.py                 # BKT closed-form Bayesian update
│   ├── prism_client.py        # PRISM tracing client (Block Convey integration)
│   ├── tools/                 # One file per MCP tool (Python)
│   │   ├── log_performance_input.py
│   │   ├── get_weak_topics.py
│   │   ├── get_recurring_mistakes.py
│   │   ├── get_concept_state.py
│   │   ├── generate_daily_plan.py
│   │   └── get_progress.py
│   ├── server.js              # Node MCP server (legacy, still passing)
│   └── db.js                  # Node SQLite layer (legacy)
├── tests/                     # Python test suite (35 tests)
├── test/                      # Node test suite (2 tests, legacy)
├── research/
│   └── synthetic_jee_kt/      # Parallel research track — KT benchmark
│       ├── simulator/         # IRT-based synthetic student simulator
│       ├── models/            # BKT (default + EM-fit), PFA, LKT
│       ├── evaluation/        # Cross-world stress tests & ablations
│       └── tests/             # 27 unit tests
├── docs/
│   ├── plan.md                # Current spec and build status
│   ├── decisions.md           # Append-only decision log
│   └── setup.md               # Build/test/lint commands (read by pre-commit hook)
├── ex1.md                     # Full implementation context and rationale
├── pyproject.toml             # Python package config
└── package.json               # Node package config (legacy)
```

---

## Research Track: Synthetic JEE KT Benchmark

A parallel, independent research workstream — not part of the production MCP server. Generates a reproducible synthetic JEE student dataset (140 students, 35,000 interactions across 7 learner-world archetypes built from 2,307 real eQOURSE items) and benchmarks four knowledge-tracing model families.

**Results summary (5 seeds, 140 students, 35,000 interactions):**

| Model | AUC | Log Loss | Notes |
|---|---|---|---|
| Baseline | 0.557 | 2.622 | Majority-class predictor |
| BKT (default params) | 0.577 | 0.690 | Fixed P(L0/T/S/G) |
| BKT (EM-fitted) | 0.652 | 0.658 | +0.068 AUC vs default |
| PFA | 0.662 | 0.652 | Compensatory summation |
| **LKT** | **0.671** | **0.648** | Recency + difficulty features; best overall |

LKT's recency and difficulty features provide the most robustness under real-world learner distribution shifts (cross-world generalization gap: ΔAUCcross = −0.032).

These results inform but do not change the production decision (ex1.md §7.2): the product server uses fixed-param BKT because a single student's data is a different regime than the multi-student training data these models require.

See [`research/synthetic_jee_kt/BENCHMARK_REPORT.md`](research/synthetic_jee_kt/BENCHMARK_REPORT.md) and [`docs/real-student-validation-report.md`](docs/real-student-validation-report.md) for full details.

---

## Design Decisions (summarized)

| Decision | Choice | Why |
|---|---|---|
| LLM usage | Extraction + daily plan only | Everything else is deterministic — no trained models in the loop |
| KT model | Fixed-param BKT | Single-student data regime; fitting is unreliable at this volume |
| Trained KT models (DKT, AKT, etc.) | Rejected | Require population-scale data + torch/wandb infra; wrong regime |
| Local LLM inference | Rejected | Hard constraint from day one — no GPU/RAM load, no heavy download |
| MCP server language | Python/FastMCP (migrated from Node.js) | Better MCP ecosystem; Node server kept until explicit decommission |
| Database | SQLite (`better-sqlite3` / stdlib `sqlite3`) | Zero-config, local file, negligible at this data scale |
| Concept dedup | LLM context match + normalized exact-match backstop | Prevents "Rotational Motion" and "Rotational Dynamics" splitting mastery history |
| Retention decay | Simple time-decay nudge (not Ebbinghaus fitting) | Data-insufficiency; fitting decay params has the same problem as fitting BKT |

Full rationale, including rejected approaches, is in [`ex1.md`](ex1.md).

---

## Status

Build Order (from [`ex1.md §12`](ex1.md)):

- [x] Step 1 — Skeleton MCP server (`echo` tool, Qwen Desktop connection verified)
- [x] Step 2 — Raw logging pipeline (`concepts`, `attempts`, `error_types`, `attempt_errors`, `log_performance_input`, `list_concepts`, concept dedup)
- [x] Step 3 — Descriptive analytics (`get_weak_topics`, `get_recurring_mistakes`)
- [x] Step 4 — BKT with default parameters (`student_concept_state`, `get_concept_state`, retention decay)
- [ ] Step 5 — Concept graph (incremental, chapter-by-chapter — explicitly deferred by design)
- [x] Step 6 — Interventions + outcome tracking (`generate_daily_plan`, `get_progress`)
- [ ] Step 7 — Backup (periodic SQLite copy to Google Drive)

All 7 MCP tools are implemented and tested (35 Python + 2 Node tests passing).

