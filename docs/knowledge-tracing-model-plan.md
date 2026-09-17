# Knowledge tracing model plan: is BKT enough, or do we need more models?

Written 2026-09-18, in response to the direct question: "we only have
general BKT, is it needed to add any other models?"

Short answer up front: **no, not for the production server** — and this
isn't a fresh opinion, it's backed by an actual real-student experiment
already run in this repo that specifically tested the alternative. The
rest of this doc explains why, what was actually tried, and the two
things that *are* worth doing instead of swapping models.

---

## What's live today

`src/bkt.py` — fixed-parameter Bayesian Knowledge Tracing:
- `P(L0)=0.20` (prior knowledge), `P(T)=0.10` (learning rate),
  `P(S)=0.10` (slip — knows it, answers wrong), `P(G)=0.25` (guess —
  doesn't know it, answers right).
- Closed-form posterior update per attempt (`update_mastery`) — pure
  arithmetic, no ML library, no training step.
- A simple time-decay nudge on top (`apply_decay`) — not a fitted
  forgetting curve, just a fixed ×0.97/week after a 14-day grace period,
  floored at 0.3.
- Parameters are **fixed literature defaults, never fitted** to her data.

## The actual question: does something smarter beat this on real data?

This exact question — "should we use a real trained knowledge-tracing
model instead" — was raised and tested **twice**, not just reasoned
about in the abstract:

**1. Against the full pyKT model catalog (DKT, AKT, SAINT, reKT, etc.)**
— checked directly against `pykt-toolkit`'s own package metadata. Every
one of these requires gradient descent training, an embedding layer, and
`torch`/`wandb` as hard dependencies. Their own smallest benchmark
dataset has ~195,000 interactions pooled across 333 students; the
flagship has ~347,000 across 4,217 students. A single student generating
a few hundred attempts a month is not a smaller version of that problem
— it's a different regime a trained embedding model has no way to work
in. Full reasoning: [`ex1.md §7.2`](../ex1.md).

**2. Against a model actually built and pre-trained for this exact use
case (LKT, from this repo's own `research/synthetic_jee_kt` track)** —
trained on 35,000 synthetic JEE interactions, then tested against a real
student's 74 real attempts across 3 real mock tests. Results, from
[`docs/real-student-validation-report.md`](real-student-validation-report.md):

| Model | AUC (primary metric) | Natural-threshold accuracy |
|---|---|---|
| **BKT (fixed default)** | **0.5139** | 41.9% |
| Pre-trained LKT | 0.4593 (*below* random-chance 0.50) | 50.0% |
| Recent-5 rolling baseline | 0.5088 | 70.3% |

LKT's AUC being *below chance* on real data isn't a close call — the
trained model actively performs worse than a coin flip at ranking which
questions she'd get right vs. wrong. Root cause, also verified directly:
**zero of the real student's 49 concepts overlapped with the 1,029
synthetic training concepts.** The model's learned concept-specific
weights were never active; it was guessing on unfamiliar vocabulary the
whole time. A previously-reported 71.6% accuracy figure for LKT turned
out to be threshold-tuned using the test labels themselves (data leakage)
— not a real generalization number, and this was caught and corrected in
the same report.

**Verdict** (recorded in the report itself, not just this doc): *"74
attempts from a single student on concept-mismatched data does not
support replacing or augmenting BKT in production."*

## What about PFA, or the EM-fitted BKT variant from the research track?

Worth naming explicitly since both exist in `research/synthetic_jee_kt/`
and both *do* beat default BKT — but only on the synthetic, pooled,
multi-student benchmark (PFA: AUC 0.662, EM-fitted BKT: AUC 0.652, vs.
default BKT's 0.577, all on the 35,000-interaction synthetic set).

Neither has been tested against real single-student data, and neither
should be expected to fare better than LKT did if they were: both are
**fit via logistic regression / likelihood maximization pooled across
many students' sequences** (checked directly in
`research/synthetic_jee_kt/models/pfa.py` and `bkt.py`'s `fit()` method
— `groupby("student_id")`, pooled across students per concept). That's
the exact same population-data dependency that caused LKT's concept
vocabulary mismatch. There's no reason to expect a different outcome,
and actually testing it would cost real effort for a predictable result.

## So what's the actual conclusion?

**Model family: keep fixed-parameter BKT.** Every population-trained
alternative shares the same fundamental blocker (needs pooled
multi-student data this product doesn't have and, by design, shouldn't
collect — see `docs/cloud-sync-design.md`'s deferred status), and the one
alternative actually tested on real data performed *below chance*.

This isn't "we haven't gotten around to it" — it's "we tried the
obvious next thing and it made results worse, with a root cause that
would recur for any population-trained model, not just this one."

---

## What's actually worth doing instead (two real options, not urgent)

Not "add another model" — refinements to the one that's already working:

### Option A: Fit BKT parameters to *her own* long-run history (not pooled)
Different from the rejected "EM-fitted BKT" above — that pooled across
*many students*. This would fit `P(L0)/P(T)/P(S)/P(G)` per-concept using
only *her* accumulated attempts over months, still closed-form
(`scipy.optimize` on her own sequences, same technique already proven in
`research/synthetic_jee_kt/models/bkt.py`'s `fit_bkt_for_sequences`, just
pointed at one student instead of pooled data). This was explicitly
flagged in `ex1.md §9`'s rejected-approaches table as **not** rejected
outright — deferred specifically until "enough data per concept," which
didn't exist at launch and might exist now after real usage. Worth
revisiting once a concept has, say, 15-20+ real attempts — below that,
fitting just overfits noise.

### Option B: Concept graph / prerequisite propagation (`ex1.md §8`)
Currently: each concept's mastery is tracked in isolation. A real
learning structure has prerequisites — weakness in "Limits" predicts
risk in "Continuity" and "Differentiability" before she's even attempted
those. This was explicitly scoped as incremental, chapter-by-chapter, no
upfront full-syllabus curation project (`ex1.md §8`) — still true, still
the right shape, still not built. This is a bigger lever on plan quality
than a different point-estimate model would be, and doesn't need any
training data at all, just structure.

Neither of these is urgent — both assume enough real usage has
accumulated to be worth the effort. Flagging them here so they're the
next things considered, not "which trained model," when there's an
appetite to go deeper on the knowledge-tracing side.

---

## Not doing (explicitly, so it isn't re-litigated again)

- **Any pyKT model (DKT/AKT/SAINT/reKT/etc.)** — wrong data regime,
  checked directly against their own docs/dependencies. `ex1.md §7.2`.
- **Pre-trained or freshly-trained LKT/PFA in production** — tested (LKT)
  or would predictably fail the same way (PFA) on real single-student
  data. This doc + `docs/real-student-validation-report.md`.
- **A fitted (Ebbinghaus-style) forgetting curve** — same
  data-insufficiency problem as fitted BKT; the simple time-decay nudge
  stays. `ex1.md §7.3`.
- **Local LLM inference to run any of the above locally** — separate,
  already-rejected constraint (`ex1.md §9`): no GPU/RAM load, no heavy
  download.

This list exists so a future session (or a future "should we add X"
question) can check here first instead of re-running an investigation
that already has a real, data-backed answer.
