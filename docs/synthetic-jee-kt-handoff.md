# Handoff: Synthetic JEE Learner Data + Lightweight Knowledge Tracing

_Written 2026-09-14 by Claude Code, for Antigravity to implement. This is
the single doc to start from — it points at the supporting docs rather than
repeating them. Read in this order before writing any code:_

1. `Synthetic_JEE_KT_Agent_Brief.md` (repo root) — the original mission/spec.
2. [`docs/research-validation-report.md`](research-validation-report.md) —
   answers to all 17 pre-implementation validation questions, with primary-
   source citations. **Read this fully before writing the simulator** — it
   contains corrections to the brief (a wrong arXiv ID, a mischaracterized
   citation, and the important finding that BKT-vs-PFA/LKT need different
   evaluation treatment) that change what "correct" looks like.
3. [`docs/jee-dataset-audit.md`](jee-dataset-audit.md) — confirms no public
   JEE/NEET student-interaction dataset exists; eQOURSE (CC-BY-4.0,
   ~2,307 questions, has topic/subtopic/difficulty) is the item environment
   to build on.
4. [`docs/synthetic-learner-spec.md`](synthetic-learner-spec.md) — the
   exact generative mechanism (state variables, equations, worlds).
5. [`docs/experimental-protocol.md`](experimental-protocol.md) — splits,
   metrics, baselines, ablations, seeds.

Do not re-derive any of the above from the brief directly — the four docs
already resolved the brief's open questions against primary sources; follow
them.

## Relationship to the existing `JEE_MCP` product (read before touching anything)

This is a **separate, parallel research workstream**, not a modification of
the shipped MCP server. `ex1.md` and `docs/plan.md` describe a single-real-
student coaching tool that is explicitly committed to fixed-parameter BKT
with no fitting and no local ML/GPU — see the validation report's
"Reconciliation" section for the full reasoning. **Do not touch
`src/`, `ex1.md`, `docs/plan.md`, `docs/tool-implementation-plan.md`, or
the existing `attempts`/`concepts`/`student_concept_state` schema.** This
workstream lives in its own directory (see §1 below) with its own
dependencies, and produces research artifacts (docs, notebooks, CSVs,
scripts) — it does not currently need to touch the Node/MCP server at all.

## Feasibility assessment (brief §22E)

- **CPU:** sufficient. Per validation report Q17, BKT/PFA/LKT are all
  lightweight (HMM/EM or logistic regression), not deep learning — no GPU,
  no `torch`, no `wandb`. This matches, and does not strain, the existing
  project's no-heavy-compute constraint.
- **RAM:** low. At the scale implied by the experimental protocol (hundreds
  of synthetic students × thousands of interactions = low hundreds of
  thousands of rows), the full dataset fits comfortably in memory as a
  pandas DataFrame on any modern laptop (well under 1GB).
- **GPU:** not required, not used anywhere in this phase.
- **Storage:** `synthetic_interactions.csv` + `student_ground_truth.csv` at
  this scale: low tens of MB, not a concern.
- **Expected dataset size:** brief §9's schema, generated per the protocol
  in `experimental-protocol.md` — start with ~200–500 synthetic students
  across the 7 active worlds (A–G; H deferred), ~500–2,000 interactions
  each depending on world/archetype.
- **Expected training/eval time:** BKT (closed-form or small EM fit) and
  PFA/LKT (scikit-learn logistic regression) at this row count: seconds to
  low minutes per run, even across the 5-seed-minimum × multiple-cross-
  world-configuration matrix in the experimental protocol. No remote
  server/GPU needed for any part of this phase.

## Implementation plan (brief §22F)

### Repository structure
```
research/synthetic_jee_kt/          # new top-level dir, isolated from src/
├── data/
│   ├── raw/                        # eQOURSE export (item pool), not committed if large — document fetch script instead
│   └── generated/                  # synthetic_interactions.csv, student_ground_truth.csv (gitignored, regenerable from seed+config)
├── configs/
│   ├── worlds.yaml                 # World A–G parameter overrides, per synthetic-learner-spec.md §5
│   └── archetypes.yaml             # S01–S10 presets, per synthetic-learner-spec.md §8
├── simulator/
│   ├── student.py                  # state variables + P(correct)/learning/forgetting, per spec §1–§4
│   ├── worlds.py                   # world parameter loading
│   └── generate_dataset.py         # CLI: seed, world mix, student count → writes data/generated/*.csv
├── models/
│   ├── baseline.py                 # recent-accuracy
│   ├── bkt.py                      # closed-form update (default params) + EM-fit variant
│   ├── pfa.py                      # scikit-learn logistic regression
│   └── lkt.py                      # scikit-learn logistic regression, feature set per spec §1
├── evaluation/
│   ├── metrics.py                  # AUC/log-loss/RMSE/Brier, per experimental-protocol.md §2
│   ├── splits.py                   # student-level holdout + all-in-one multi-KC, per protocol §1
│   └── run_benchmark.py            # CLI: runs baselines+models across splits/worlds/seeds, per protocol §3–§6
└── notebooks/                      # exploratory only, not a source of truth
```

### Dependencies (Python — separate from the Node.js MCP server's stack)
- `numpy`, `pandas` — generation and data handling.
- `scikit-learn` — PFA/LKT logistic regression, EM-fit BKT variant if not
  hand-rolled.
- `pyyaml` — world/archetype configs.
- No `torch`, no `wandb` — not needed for this phase (validation report
  Q17); do not add them without first re-checking whether ReKT/GKT is
  actually justified per brief §11's own instruction not to assume it is.

### Config
- One YAML per world (`configs/worlds.yaml`), one per archetype
  (`configs/archetypes.yaml`) — see synthetic-learner-spec.md §5/§8 for the
  exact parameters each needs.
- Seed handling: a single `--seed` CLI flag threaded through a single RNG
  instance, per experimental-protocol.md §6 — no unseeded randomness
  anywhere in `simulator/`.

### Commands (to be wired up once the scripts exist)
```
python simulator/generate_dataset.py --seed 1 --worlds A,B,C,D,E,F,G --students-per-world 50
python evaluation/run_benchmark.py --seeds 1,2,3,4,5 --config experimental-protocol
```
Exact CLI surface is Antigravity's implementation call — the above is the
minimum needed to satisfy `experimental-protocol.md`'s reproducibility
requirement (§6).

### Build order
Follow brief §21 Phases 1–3 (question environment → simulator → dataset
generator) then Phase 4 (baseline + BKT) before Phase 5 (PFA/LKT), per the
brief's own baseline-first rule (§24 item 21) — do not build PFA/LKT before
a working BKT baseline exists to compare against. Phase 6 (cross-world/
ablations, per `experimental-protocol.md` §4–§5) closes out the first
benchmark. Phases 7–8 (real-data calibration, advanced models) are
explicitly out of scope until real data exists or the Phase 1–6 results
justify the added complexity — do not start them speculatively.

## Antigravity workflow (per `AGENTS.md`)

- Branch: `antigravity/synthetic-jee-kt` (single branch for the whole
  workstream, per the "one combined handoff" decision — split into
  per-phase branches only if the scope turns out to need it mid-work).
- Own worktree — do not work in the main checkout or a sibling worktree.
- Commit format: `<type>(antigravity): summary`, e.g.
  `feat(antigravity): add synthetic student generator core`.
- Read `docs/plan.md` and the last ~50 lines of `docs/decisions.md` before
  starting, per `AGENTS.md`'s standing "before doing anything" rule — this
  handoff doc is the task-specific context, `AGENTS.md`/`docs/setup.md` are
  the process rules that still apply.
- Append `[claimed]` when starting, then `[done]` or `[blocked]` entries to
  `docs/decisions.md` in the repo's standard format:
  `[YYYY-MM-DD HH:MM] [antigravity] [antigravity/synthetic-jee-kt] [status] — what / why`.
- Do not merge this branch to `main` — that's a human review step, per
  `AGENTS.md`.
- No new pre-commit/lint/test commands exist yet for `research/` — until
  `docs/setup.md` is updated with them, at minimum run the scripts
  end-to-end and confirm the reproducibility check in
  `experimental-protocol.md` §6 (same seed → byte-identical output) before
  marking any phase `[done]`.
