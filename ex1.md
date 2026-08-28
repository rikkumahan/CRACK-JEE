# JEE Performance Engine — Full Implementation Context

This document consolidates every decision made while designing this system, so
implementation can start without re-deriving anything. Where a decision was
contested and later confirmed, that's noted — it matters for not re-opening
settled questions mid-build.

---

## 1. One-Line Product Definition

A personal JEE performance coach for one student (not a tutor, not a chatbot)
that ingests whatever performance data she has, finds recurring mistake
patterns across tests over time, prescribes a concrete next-day action, and
verifies whether that action actually improved her results.

## 2. Who It's For, and the Core Constraint

- Single user (a JEE aspirant), gift project, built by her sibling.
- She's already enrolled in Aakash (coaching + AIATS test series), which
  provides per-test reports — this system does **not** replace that. It fills
  two specific gaps Aakash doesn't cover:
  1. **Cross-test pattern mining** — Aakash reports are per-test/siloed; this
     tracks recurring patterns across many tests.
  2. **Closed-loop verification** — Aakash never checks whether a suggested
     fix actually worked on the next test; this does.
- Hard constraint set at the very start of the project: **no local LLM
  inference** (no Ollama, no GPU/RAM load, no heavy download). Inference
  always stays cloud-hosted via whatever chat app she uses.
- Zero cost, zero ongoing maintenance burden, minimal setup friction for her.

## 3. Core Principle (do not violate this while building)

> **The LLM is used only for extraction and reasoning where judgment is
> genuinely needed (turning messy input into structured evidence, generating
> the daily plan). Every statistic, ranking, and mastery estimate is
> deterministic code — plain queries, arithmetic, or a closed-form Bayesian
> update. Nothing is a trained model.**

This was tested hard mid-conversation (see §9, "Rejected Approaches") and
held up. Do not reintroduce trained ML models into this system without
re-deriving why the constraint no longer applies.

---

## 4. Hosting Architecture

```text
                        ┌─────────────────────────┐
                        │      Qwen Desktop        │
                        │   (free, local install)  │
                        │   Chat UI ← → LLM calls   │──────► Qwen Cloud API
                        └────────────┬──────────────┘        (inference only,
                                     │ local MCP                free tier)
                                     │ (stdio, launched
                                     │  automatically by
                                     │  the app via config)
                                     ▼
                        ┌─────────────────────────┐
                        │   JEE Performance MCP     │
                        │      Server (local)       │
                        └────────────┬──────────────┘
                                     │ reads/writes
                                     ▼
                        ┌─────────────────────────┐
                        │   Local SQLite file        │
                        └────────────┬──────────────┘
                                     │ periodic backup
                                     ▼
                        ┌─────────────────────────┐
                        │  Google Drive (backup only)│
                        └─────────────────────────┘
```

**Confirmed working** (screenshot verified mid-conversation): Qwen Desktop's
Settings → MCP → "My MCP" tab has a working "Add MCP" flow with two paths —
"Quick Add" and **"Add using JSON"** (the one we'll use). Existing servers
(Fetch, Filesystem, Sequential-Thinking) are shown as real, toggleable,
functioning entries — proves the local MCP mechanism is real and working on
her actual machine, not just documented in theory.

### Why this hosting choice, not the alternatives considered:
- **Claude.ai / ChatGPT hosted connectors** — rejected. ChatGPT gates custom
  MCP connectors behind Developer Mode + a paid plan (Plus/Pro/Business/
  Enterprise/Education); she's on the free tier. Claude.ai supports connectors
  on its free tier but usage/rate limits were the specific objection raised.
- **A standalone web app + your own LLM API key** — a valid fallback discussed
  in depth, still on the table if the MCP route hits friction, but not the
  current path.
- **Kimi consumer app** — checked, does not expose MCP connectors to end
  users (Kimi's MCP support is in Kimi Code, a dev CLI tool, not the consumer
  chat app). Ruled out.
- **Qwen Desktop, local MCP** — chosen. Free, no plan gating, runs the MCP
  server as a local process (stdio), so **no public hosting, no server
  bill, no uptime to manage.**

### Resource footprint (validated, not just assumed):
- Qwen Desktop app: normal desktop-chat-app footprint, trivial for any
  laptop from the last ~8 years.
- MCP server: a small Node/Python script, negligible CPU/RAM.
- SQLite: a local file, negligible at her data scale (thousands of rows,
  not millions).
- Only real prerequisite: Node.js (or Python) runtime installed once.
- **What is explicitly NOT local:** the LLM itself. This was a deliberate,
  repeatedly-confirmed decision — local inference was ruled out on day one
  and every later idea that would have reintroduced it (BKT parameter
  fitting, neural knowledge-tracing models) was rejected partly for this
  reason too.

---

## 5. Full Data Pipeline (6 stages)

```text
1. STUDENT INPUT
   Submitted in ANY format: exam paper + answer key + her solutions,
   OR one complete report, OR just text describing what happened.
   No fixed format is required or enforced.
        ↓
2. LLM EXTRACTION
   The LLM (Qwen, via the chat conversation) converts whatever she sent into
   structured evidence: result (correct/wrong), concept, error type,
   time taken, confidence (if given), notes/reasoning.
   Partial extraction is expected and fine — fields are nullable.
        ↓
3. RAW EVENT DATABASE
   Immutable log of every attempt and every piece of extracted evidence.
   This is the source of truth; everything downstream is derived/recomputed
   from this, never hand-edited directly.
        ↓
4. ANALYTICS ENGINE
   Deterministic and statistical processing only:
     - descriptive stats (accuracy by topic, trend over time)
     - BKT / knowledge tracing (fixed-parameter Bayesian update — see §7)
     - concept graph (built on-the-fly, not pre-curated — see §8)
     - error pattern analytics (recurring error type × topic combos)
     - retention/forgetting — a SIMPLE time-decay nudge only, not
       curve-fitting (see §7.3 — this was a scope correction made after
       reviewing a proposed diagram that had over-included this)
        ↓
5. DECISION ENGINE
   Ranks weaknesses by recoverable-marks potential, outputs:
     - weak topics list, with WHY it's weak (not just a label)
     - recommended interventions
     - a concrete, time-blocked daily plan
        ↓
6. INTERVENTION OUTCOME
   After the plan is acted on and she takes her next test, this stage
   measures accuracy before/after and time before/after per concept, and
   feeds the result back into the raw event database (closes the loop).
```

The feedback loop (stage 6 → stage 3) is the single most differentiated part
of this whole system relative to what Aakash or any competitor product does
— confirmed multiple times across the conversation, never contested.

---

## 6. Database Schema (V1 scope, confirmed)

```text
concepts
├── id (PK)
├── name
├── subject
└── created_at

attempts
├── id (PK)
├── concept_id (FK → concepts)
├── result            -- correct / wrong / unattempted
├── time_seconds       -- nullable, not always available
└── created_at

error_types
├── id (PK)
├── name                -- concept_gap | calculation | misread |
│                          time_pressure | unattempted | unknown
└── description

attempt_errors
├── id (PK)
├── attempt_id (FK → attempts)
├── error_type_id (FK → error_types)
└── notes               -- free text, optional

student_concept_state          -- BKT-derived, recomputable from attempts
├── id (PK)
├── concept_id (FK → concepts)
├── mastery_probability
├── attempts
└── last_updated_at

interventions
├── id (PK)
├── concept_id (FK → concepts)
├── recommendation
├── created_at
└── status              -- pending / done

intervention_outcomes
├── id (PK)
├── intervention_id (FK → interventions)
├── accuracy_before
├── accuracy_after
├── time_before
├── time_after
├── mastery_before
├── mastery_after
└── created_at
```

This schema was independently validated against real knowledge-tracing
research conventions (pyKT toolkit's dataset documentation): question/skill
ID, correctness, time spent, and timestamp are exactly the fields academic
KT datasets consider essential. That's confirmation the raw `attempts` table
is capturing the right primitives, not a new requirement.

### Deliberately NOT in this schema (cut from an earlier, over-scoped version):
- A pre-curated concept **prerequisite graph** table (concept → concept
  edges). Build this incrementally, only for chapters she's actually being
  tested on, as they come up — never as an upfront full-syllabus curation
  project.
- `question_concepts` weighted multi-tagging (one question mapped to
  several concepts with weights). Single-concept-per-attempt for V1;
  extend later without breaking anything already built.
- Any trained-model table (embeddings, learned weights, checkpoints) — see
  §9 for why.

---

## 7. Knowledge Tracing Approach: BKT, Not a Trained Model

### 7.1 The decision, and why it survived multiple challenges
Bayesian Knowledge Tracing, run with **fixed, literature-default
parameters** (not fitted/trained on her data). This was proposed, then
specifically re-examined twice more (once when the user pushed back citing
her 3-exams/week volume, once when the user brought pyKT's full model list,
once more narrowing specifically to reKT) — and held up every time.

### 7.2 Why not a real knowledge-tracing model (DKT, AKT, SAINT, reKT, etc.)
Checked directly against pyKT's own documentation and package metadata:
- Every model in pyKT (30+, including the newer "lightweight" reKT) is a
  **trained** model requiring gradient descent, an embedding layer, and a
  train/val/test split.
- pyKT's own smallest benchmark dataset (Statics2011) has ~195,000
  interactions across 333 *pooled* students. Their flagship (ASSISTments2009)
  has ~347,000 interactions across 4,217 students. A single student
  generating a few hundred attempts a month is a fundamentally different
  data regime, not a smaller version of the same problem.
- Verified via the actual `pykt-toolkit` package metadata (pip-inspected
  directly): required dependencies include `torch` and `wandb` — confirming
  real training/hyperparameter-sweep infrastructure is unavoidable even to
  use the library, not just optional tooling.
- **reKT specifically** was checked in depth because its own paper claims to
  be "lightweight" (its FRU core is literally two linear regression units,
  ~38% the compute cost of LSTM/Transformer models). That claim is true and
  verified — but it's a claim about *compute cost*, not *data efficiency*.
  reKT is still trained via gradient descent on pooled multi-student data;
  nothing about it works from one student's small history. Compute-lightness
  and data-efficiency are separate axes, and only the first was solved.
- No pretrained JEE-specific weights exist anywhere, and pretrained weights
  from the public benchmark datasets (all US school platforms — ASSISTments,
  Algebra2005, Eedi) wouldn't transfer to JEE content anyway — different
  curriculum, different question style entirely.

### 7.3 What "BKT" means concretely for this build
- Standard four-parameter model per concept: P(L0) prior knowledge,
  P(T) transition/learn rate, P(G) guess rate, P(S) slip rate.
- Use reasonable literature-default values to start (do not spend time
  trying to fit these — that reintroduces the exact problem just ruled out).
- Per attempt: closed-form Bayesian update of `mastery_probability` in
  `student_concept_state`. No ML library needed — this is arithmetic.
- **Retention/forgetting**: a simple time-decay nudge only (e.g., mastery
  estimate decays slightly if a concept hasn't been attempted in N weeks).
  NOT a fitted forgetting-curve model (Ebbinghaus-style parameter fitting)
  — that was flagged as scope creep when it appeared in a later diagram and
  was explicitly cut back down to the simple version.

---

## 8. Concept Graph

Build incrementally, chapter by chapter, only as she's actually tested on
them. No upfront full-JEE-syllabus prerequisite curation project — that
alone would be weeks of manual work disconnected from the core system, and
was explicitly identified as a scope risk to avoid.

---

## 9. Rejected Approaches (with reasons, so they aren't re-litigated)

| Approach | Why rejected |
|---|---|
| Local LLM inference (Ollama etc.) | Violates the original hard constraint: no heavy download, no GPU/RAM load, no complex setup for her. |
| Hosted MCP via ChatGPT (free tier) | Custom connectors require Developer Mode, gated to paid plans only. |
| Hosted MCP via Claude.ai | Works even on free tier, but usage/rate limits were the user's specific objection. |
| Kimi consumer app MCP | Doesn't exist for the consumer chat surface — Kimi's MCP support is dev-tool-only (Kimi Code). |
| Full pre-curated concept prerequisite graph (upfront) | Real, multi-week manual curation project, disconnected from the core value; do incrementally instead. |
| BKT with data-fitted (not default) parameters | Not enough data per concept early on to fit reliably; may revisit after months of real usage. |
| Any pyKT deep-learning KT model (DKT, AKT, SAINT, DTransformer, reKT, etc.) | All require training on population-scale, multi-student pooled data (thousands of students); a single student's data is a different regime entirely, not a smaller version of the same problem. Also require `torch`/`wandb`/GPU infra, violating the no-heavy-compute constraint. |
| Fitted forgetting-curve model (Ebbinghaus-style decay parameters) | Same data-insufficiency problem as fitted BKT; use a simple time-decay nudge instead for V1. |
| Full ITS-style IRT / prerequisite-graph curation | Research-scale project, months of work, not appropriate for a single-user gift app. |

---

## 10. MCP Server — Tool Groups and Signatures

Three tool groups, called in sequence by Qwen during a conversation:

### Logging
- **`log_performance_input(content, context?)`**
  - `content`: text and/or image(s) — whatever she has (full report, raw
    question + her answer + solution, or just a sentence describing what
    happened). No fixed format required.
  - `context` (optional): which test/date this relates to, if she specifies.
  - Behavior: LLM extracts whatever structured fields it can find; writes
    to `attempts` / `attempt_errors` / `concepts` (creating concepts
    on-the-fly if new). Missing fields are simply left null — never blocks
    or rejects a partial input.

### Analytics (read-only, deterministic)
- **`get_weak_topics()`** — accuracy/error-rate aggregation by concept
  across recent attempts.
- **`get_recurring_mistakes()`** — cross-test pattern query: same
  `error_type` + `concept` combination appearing 2+ times. This is the
  core differentiator relative to Aakash's per-test-only reports.
- **`get_concept_state()`** — current BKT mastery probability per concept,
  including the retention decay nudge.

### Planning
- **`generate_daily_plan()`** — the one tool where the LLM does real
  reasoning: takes ranked weaknesses from the analytics tools and produces
  a concrete, time-blocked plan (not generic "revise Physics for 2 hours").
  Writes to `interventions`.
- **`get_progress()`** — compares accuracy/time/mastery before vs. after an
  intervention was issued, once a later test provides "after" data. Writes
  to `intervention_outcomes`. This is stage 6 of the pipeline, the
  closed-loop verification step.

---

## 11. Stack (decided, not yet built)

- **MCP server language**: Node.js (better MCP SDK support, easier Qwen
  Desktop config than Python for this use case).
- **Database**: SQLite via `better-sqlite3` — zero-config, local file.
- **Dependencies to install**: `@modelcontextprotocol/sdk`,
  `better-sqlite3`.
- **LLM**: none bundled — Qwen Desktop's own model handles all reasoning;
  the MCP server never calls an LLM API itself.
- **Config**: Qwen Desktop → Settings → MCP → My MCP → Add MCP → "Add using
  JSON" (confirmed working via screenshot).

---

## 12. Build Order (confirmed, in sequence)

1. **Skeleton MCP server** — one dummy tool, prove the Qwen Desktop
   connection works before any real logic. **✅ Done — confirmed via
   screenshot, Qwen Desktop's MCP settings and JSON-add flow verified
   working on her actual machine.**
2. **Raw logging pipeline** — `attempts`, `concepts`, `error_types`,
   `attempt_errors` tables + `log_performance_input` tool. **← next step,
   not yet built.**
3. **Descriptive analytics** — `get_weak_topics`, `get_recurring_mistakes`,
   plain SQL/aggregation, no ML.
4. **BKT with default parameters** — `student_concept_state` table,
   `get_concept_state` tool, closed-form Bayesian update per attempt.
5. **Concept graph, incremental** — added chapter-by-chapter alongside
   real test coverage, never blocking steps 2–4.
6. **Interventions + outcome tracking** — `generate_daily_plan`,
   `get_progress`, closing the loop.
7. **Backup** — periodic copy of the SQLite file to Google Drive (a
   five-line addition, not a new architecture).

Explicitly deferred beyond this build order: a dashboard (optional, later),
packaging for her friends to self-install (only after core value is proven
for her specifically), mobile access (Qwen Desktop's MCP support is
desktop-only).

---

## 13. Open Item Before Writing Step-2 Code

None blocking — the flexible-input design (§10, `log_performance_input`)
was specifically adopted so that the system doesn't depend on knowing her
exact Aakash report format in advance. Implementation can begin immediately.