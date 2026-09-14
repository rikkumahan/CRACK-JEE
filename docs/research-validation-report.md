# Research Validation Report — Synthetic JEE Learner Data + Lightweight Knowledge Tracing

_Written 2026-09-14. Answers the 17 validation questions in
`Synthetic_JEE_KT_Agent_Brief.md`'s "VERY IMPORTANT: Validate Before
Implementing" section, before any simulator/KT code exists. Every claim
below was checked against a fetched primary source (paper full text, arXiv
page, GitHub repo, dataset card) this session — not recalled from training
data. Where a source could not be reached, that is stated explicitly rather
than filled in from memory._

**Companion documents:** [`jee-dataset-audit.md`](jee-dataset-audit.md) (Q6–Q8
in full detail), [`synthetic-learner-spec.md`](synthetic-learner-spec.md),
[`experimental-protocol.md`](experimental-protocol.md).

---

## Corrections to the brief, found during verification

- **pyKT's arXiv ID is wrong.** The brief cites `10.48550/arXiv.2206.12017` —
  that ID resolves to an unrelated hep-th physics paper. The correct pyKT
  paper is **arXiv:2206.11460** (NeurIPS 2022 Datasets & Benchmarks Track).
- **L-HAKT's AAAI URL is correct**, contrary to the brief's flag that it
  "needs verification" — it resolves to "Towards LLM-Empowered Knowledge
  Tracing via LLM-Student Hierarchical Behavior Alignment in Hyperbolic
  Space" (AAAI 2026, vol. 40(17), pp. 14747–14755), which matches the
  description in the brief.
- **StudentSim's arXiv ID (2609.01591) is real** and resolves to a genuine
  September 2026 submission — not a hallucinated ID, contrary to what its
  format might suggest.
- **Corbett & Anderson (1995) could not be read directly** — the DOI
  redirects to a login wall, and no free-standing copy was found. Its model
  description below is reconstructed from two primary sources that were
  read in full and cite it consistently (Pavlik/Cen/Koedinger 2009; Piech et
  al. 2015), not from the original text. Flagged per-question below wherever
  this matters.
- **Neither pyKT nor EduStudio implements BKT, PFA, or LKT.** Both are
  deep-learning-model libraries (39 and 28 KT models respectively, all
  neural). Their value to this project is as splitting-methodology and
  data-pipeline references, not as sources of runnable code for the models
  this project actually plans to benchmark.

---

## Q1 — Is synthetic student interaction data an accepted/useful methodology for KT research?

**Verdict: defensible as a documented approach, not an established best practice.**

Primary-source support exists but is thin: Pagonis et al. (2024) is a single
AI4Ed **workshop** paper (not a top-tier venue), and L-HAKT (AAAI 2026) uses
synthetic data only as an *augmentation-and-alignment* input, never as a
full substitute for real data. There is no mature, widely-replicated
consensus that synthetic KT data is a validated substitute for real data.
Treat the methodology as "supported by limited prior work, with important
caveats" in anything written for an outside audience — not as settled
science.

## Q2 — What has prior work actually demonstrated about synthetic-vs-real KT performance?

**Verdict: the commonly-cited claim is real but narrower than it sounds, and doesn't hold evenly across models.**

Pagonis et al. (2024) is the only source of the three synthetic-precedent
papers that directly measured this. Their headline finding — "training with
only synthetic data achieved similar performance to real data" — is real,
but:
- It held clearly for **DKT** with their best generator (Generator2:
  bootstrap-resample + Gaussian noise, which preserves some temporal
  structure). Their naive distribution-fitting generator (Generator1) was
  measurably worse (3–4 MAE points).
- For **BKT specifically**, results were flat and uninformative across every
  training condition — near-zero MCC, strong majority-class bias — meaning
  the "synthetic ≈ real" equivalence is **not demonstrated for BKT**, it's
  an artifact of BKT performing poorly everywhere in their setup.
- The authors' own caveat: synthetic-only data "may cause the KT models to
  be more biased towards positive grades, not being able to predict
  negative grades in a more balanced test set."

**Implication for this project:** don't cite "synthetic works as well as
real" as a blanket justification, especially not for the BKT leg of the
planned benchmark. State the claim with its actual scope: generator-design
matters, and the strongest evidence is for a deep sequence model, not BKT.

## Q3/Q4 — What assumptions generate synthetic learner behavior, and do they create evaluation bias / circularity?

**Verdict: real risk, project must self-manage it — no source in this review explicitly names or solves it.**

Two philosophies were found in the verified literature:
- **Pagonis (2024):** purely statistical, model-agnostic generators
  (distribution-fit sampling, bootstrap resampling, sequence replication +
  noise). None use BKT- or IRT-style generative assumptions — genuinely
  independent of the DKT/BKT models being tested. This is the clean,
  non-circular case.
- **L-HAKT (2026):** an LLM-driven cognitive-engagement + forgetting-curve
  generator whose synthetic interactions and the downstream hyperbolic
  GNN+GRU KT model **share the same knowledge-graph embeddings** from a
  common Teacher-Agent pipeline — a structural circularity risk the authors
  acknowledge only indirectly (via needing a distribution-"alignment" step)
  and never name as a bias/circularity concern.

Neither paper contains an explicit circularity warning. **This directly
confirms brief §19's "model-independence rule" is not optional decoration —
it's the one thing standing between a defensible experiment and a
self-fulfilling one.** Concretely: if this project's synthetic generator
uses BKT-shaped or IRT-shaped generative logic, and then BKT or an
IRT-family model is evaluated against data it generated, that specific pair
is circular and unsupported by any source reviewed here. The synthetic
learner spec (see companion doc) is written to keep the generator's
mechanism (multi-factor stochastic process with explicit error taxonomy)
structurally different from any single KT model's mathematical form.

## Q5 — What data fields are required by BKT, PFA, LKT, ReKT/GKT?

**Verdict: verified from primary sources (BKT partially — see correction above).**

| Method | Student ID | Item/skill tag | Correctness | Timestamps | Multi-KC support | Concept graph |
|---|---|---|---|---|---|---|
| BKT | required (per-skill sequence) | required (1 KC/opportunity) | required | not required | not natively | n/a |
| PFA | required | required (multi-KC OK, compensatory) | required (drives success/failure counts) | not required for base model | supported | n/a |
| LKT | required | required | required | required (recency/decay features) | supported | n/a |
| DKT | required (sequencing) | required | required | not structurally required | can be learned | none |
| GKT | required | required | required | not required for base model | not required | optional — else learned |
| ReKT | required | required (problem+skill) | required | required (forget-gate input) | operates question/concept/domain levels | not confirmed |

This directly informs `synthetic_interactions.csv`'s required columns (see
dataset schema, brief §9A) — `student_id`, `question_id`/`concept_id`,
`correct`, `timestamp` cover every model in the initial benchmark (BKT, PFA,
LKT); nothing in the schema needs to change to add DKT/GKT/ReKT later.

## Q6/Q7/Q8 — JEE dataset contents, real-interaction availability, licensing

**Verdict: full detail in [`jee-dataset-audit.md`](jee-dataset-audit.md). Summary: no public JEE/NEET student-interaction dataset exists anywhere.**

Every JEE/NEET-related public dataset found (JEEBench, eQOURSE,
NalandaJEENEETBench, plus `Reja1/jee-neet-benchmark`) is a question bank —
items plus canonical answers — with zero per-student attempt sequences,
timing, or correctness-over-time data. Indian ed-tech platforms (Embibe
explicitly markets "Deep Knowledge Tracing"-based features) hold this kind
of data internally but do not publish it, and no academic paper surfaced
using a released Indian-platform log for JEE/NEET KT research. This
confirms brief §1's premise directly: **there is genuinely no real student
interaction dataset available, and building one requires either the
synthetic path or a business-level data-sharing arrangement — not a
dataset-discovery shortcut.**

eQOURSE (CC-BY-4.0, ~2,307 questions, topic/subtopic/difficulty metadata) is
the best-structured environment to simulate over, since it's the only
source with the concept/difficulty metadata a synthetic learner needs to
condition its responses on.

## Q9 — Appropriate train/val/test splitting; leakage prevention

**Verdict: verified from primary source (pyKT paper, full text read) — student-level holdout is the field's convention, not time-based.**

pyKT's own methodology withholds entire students (20%) as a test set,
never split within a timeline; the remaining 80% is 5-fold cross-validated,
again split whole-student. pyKT also identifies (as its headline empirical
contribution) a **separate** leakage mode specific to multi-KC questions:
predicting a question's knowledge components one at a time lets a model
"peek" at ground truth from sibling KCs of the same question; the fix is
predicting all KCs of a question simultaneously ("all-in-one" protocol).

This project needs **both** controls, and they don't conflict:
1. **Student-level holdout** — synthetic students used for evaluation never
   appear in training, matching field convention and directly enabling the
   cross-world generalization tests in brief §8.
2. **Sequential-in-time prediction** — inherent to BKT/PFA/LKT's online
   update structure: a prediction at interaction *t* only ever uses history
   before *t*. This satisfies brief §17's temporal-leakage concern without
   needing a separate chronological train/test cutoff *within* a student.
3. **All-in-one KC prediction**, if any JEE question is tagged to multiple
   concepts (brief §3's weighted multi-skill mapping) — apply pyKT's fix to
   avoid the sibling-KC leak.

## Q10 — Is an independent rule-based/stochastic simulator scientifically defensible?

**Verdict: yes, conditionally — only if kept structurally independent of the KT model(s) under test.**

This follows directly from the Q3/Q4 finding: Pagonis's non-circular,
model-agnostic generators are the only clean precedent found. The synthetic
learner spec (companion doc) is designed around this constraint: the
generator is a multi-factor stochastic process (mastery × difficulty ×
recency × behavioral traits × explicit error mechanism sampling), not a
literal BKT or PFA implementation, so that evaluating BKT/PFA/LKT against
it is not tautological.

## Q11 — Are the proposed student-agent variables sufficient / over-simplified?

**Verdict: mixed confidence — split into core (verified-grounded) vs. extended (plausible but unverified in this pass).**

Only a subset of brief §2's variable list is directly grounded in the KT
papers verified this session:
- **Directly grounded:** mastery (BKT's P(Ln)), learning rate (BKT's T),
  guess/slip rates (BKT's G/S), recency and success/failure counts
  (PFA/LKT), response time as a covariate (LKT includes latency-adjacent
  features).
- **Plausible but not independently verified this session:** careless-error
  tendency as a trait distinct from BKT's slip parameter, calculation-error
  vs. reading-misinterpretation vs. sign/unit-error as separate mechanisms,
  confidence calibration, time-pressure sensitivity, and all four
  intervention-response sensitivities (worked-example/hint/practice/timed-
  practice). These come from the repo's own (pre-existing, not
  independently verified) landscape docs and general educational-error
  literature — no KT paper read this session models them explicitly.

**Recommendation:** implement the core set first (it's what BKT/PFA/LKT can
actually consume and what the state-recovery evaluation can meaningfully
test), and treat the extended behavioral traits as optional generator
parameters for the cross-world design (brief §8's Worlds D/E/F) rather than
required V1 scope — consistent with the brief's own instruction not to
assume the full wishlist is necessary.

## Q12 — Can BKT/PFA/LKT be evaluated against synthetic data with known hidden ground truth?

**Verdict: verified from primary sources — true for BKT only. PFA/LKT do not expose a comparable state.**

This is one of the most consequential findings, checked directly against
the three papers' own text:
- **BKT** has a formally defined hidden state, P(Ln), driven by an explicit
  generative HMM. Comparing it against a synthetic ground-truth mastery
  trajectory is a like-for-like evaluation.
- **PFA**'s own paper concludes the data are better explained by "a
  continuous distribution that represents strength of learning, rather than
  a discrete probability distribution" — there is no discrete state to
  recover.
- **LKT** goes further: its principal models are deliberately built
  *without* any student-level latent parameter, to generalize to unseen
  students. There is no claim anywhere in the paper that its output is a
  calibrated mastery probability.

**Implication:** the "latent-state recovery" evaluation (brief §10A) is
methodologically valid only for BKT. For PFA/LKT, the closest honest
analogue is correlating their predicted-correctness trajectory against the
true simulated ability curve — a materially weaker claim than "state
recovery," and the experimental protocol must present it as such rather
than force a uniform metric across model families.

## Q13 — Which evaluation metrics for next-response prediction and state recovery?

**Verdict: verified from primary sources.**

Every KT paper read this session (DKT, GKT, LKT, PFA) uses **AUC** as a
primary metric. Secondary: log-likelihood/cross-entropy (PFA, LKT — PFA
also trains via it, DKT trains via it), RMSE (LKT, every table), BIC (PFA,
for parsimony not accuracy), McFadden's pseudo-R² (LKT's primary
variance-explained statistic), Pearson r (PFA). **Brier score did not
appear in any primary source read this session** — if used, cite it as a
standard calibration metric from the broader ML/forecasting literature, not
as something these specific KT papers established.

For state recovery: none of PFA/LKT/DKT/GKT perform a direct quantitative
ground-truth-recovery evaluation in the sources read — DKT's synthetic
experiment compares predictive accuracy against an oracle with perfect
generative knowledge (a prediction benchmark, not a recovery metric); GKT's
interpretability claim is a qualitative heatmap visualization, not a
numeric score. **Recommendation, consistent with what the field actually
does:** AUC/RMSE/LL uniformly for next-response prediction across all
models; state-recovery analysis (correlation/MAE against true simulated
mastery) for BKT only, with the same computation applied to PFA/LKT/DKT/GKT
labeled explicitly as "predicted-probability vs. true-ability correlation,"
not "state recovery," per Q12's finding.

## Q14 — Are there simpler/better alternatives to a bespoke simulator?

**Verdict: verified — no existing tool does synthetic student-behavior generation. A bespoke simulator is genuinely necessary, but keep it minimal.**

Neither pyKT nor EduStudio (the two standard KT toolkits) ships a
student-behavior simulator; both process only real (or externally supplied)
interaction logs. EduStudio's "data generation" vocabulary means deriving
structural metadata (Q-matrices, KC sequences) from *existing* labeled
data, not simulating new behavior. Where these tools do offer reuse value:
EduStudio's atomic data-operation pipeline (partitioning, Q-matrix
construction) is worth adopting for post-generation processing, not
generation itself.

## Q15 — Which parts should be deterministic vs. LLM-driven?

**Verdict: brief §15's principle is correct and matches this project's own standing architecture decision (`ex1.md` §3) — no LLM in the simulator or KT layer at all.**

The synthetic student generator, the BKT/PFA/LKT models, and all evaluation
metrics should be plain deterministic/stochastic code (numpy/scipy random
sampling, closed-form or logistic-regression fits) — not LLM-generated.
Reasons: cost (thousands of synthetic interactions per student × hundreds
of students would be expensive and slow through an LLM), reproducibility
(a fixed random seed must give identical output), and — per Q3/Q4 — using
an LLM to role-play students risks an even less-controlled, less-auditable
generative mechanism than a rule-based one. The only place an LLM
legitimately belongs in this project (matching the existing product's
`log_performance_input` pattern) is far downstream: parsing a *real*
student's free-text description of what happened into structured evidence
— not touched by this synthetic-data/KT-benchmark work at all.

## Q16 — What can transfer from synthetic JEE interactions to real student data?

**Verdict: methodology and schema likely transfer; specific fitted parameters probably don't — must be measured empirically, not assumed.**

Per brief §19's own framing and Pagonis's actual (hedged) findings:
the data schema, the leakage-safe splitting protocol, the evaluation
metrics, and the benchmark harness itself are reusable once real data
exists. Fitted model parameters (PFA/LKT weights, BKT's if ever fitted)
learned purely on synthetic data are not guaranteed to transfer — Pagonis
found only *minor* additional benefit from combining synthetic with real
data, and that benefit was strongest for DKT, not BKT. **Do not claim
synthetic pretraining reduces real-data requirements for this project until
that is actually measured against real data** (brief §19, deferred until
real data exists).

## Q17 — Is this feasible on ordinary developer hardware?

**Verdict: yes for the planned model set (BKT/PFA/LKT) — CPU-only, laptop-feasible. Not directly evidenced by pyKT/EduStudio docs since neither implements these models, but well-supported by the models' own mathematical structure.**

BKT is a small HMM fit via closed-form Bayesian updates (no EM needed if
using literature-default parameters, per this project's own existing
`ex1.md` §7.3 approach) or, for the synthetic-population benchmark, EM/
Baum-Welch over a population-scale but still modest dataset. PFA/LKT are
logistic regressions — a standard scikit-learn-class workload. At the scale
implied by brief §9 (hundreds of synthetic students × thousands of
interactions each = low hundreds of thousands of rows), this is trivially
CPU-feasible on a laptop; no GPU, no `torch`, no `wandb` needed — consistent
with, and not in tension with, this project's existing no-heavy-compute
constraint (`ex1.md` §2, §9). Neither pyKT nor EduStudio's documentation
addresses this directly (they don't implement BKT/PFA/LKT), so this
conclusion rests on the models' own well-known compute class, not a
fetched primary-source benchmark — flagged accordingly.

---

## Reconciliation with the existing project decision (`ex1.md` §7.2)

`ex1.md` §7.2 commits the **shipped, single-real-student MCP tool** to
fixed literature-default BKT parameters, explicitly rejecting *any* fitted
or trained KT model — including fitted BKT — because one student's
per-concept data volume is too small to fit reliably, and because fitting
would reintroduce the `torch`/GPU/heavy-compute burden the project ruled
out on day one.

**This synthetic-data research track does not change that decision**, and
should not be read as reopening it. The two tracks operate in genuinely
different data regimes:

| | Production tool (`ex1.md`, unchanged) | Synthetic research track (this work) |
|---|---|---|
| Data volume | One real student, ~hundreds of attempts total | Hundreds of synthetic students, thousands of interactions each |
| BKT parameters | Fixed, literature-default | Fixed for the "true" generator (ground truth); the KT model under test may still use fixed defaults, or — separately — a **synthetic-population** BKT/PFA/LKT may be *fit* against the synthetic population, never against the real student |
| PFA/LKT | Not implemented in the shipped tool | Fit via ordinary scikit-learn logistic regression against the synthetic population — CPU-only, not the `torch`/GPU-class training `ex1.md` §9 rejected |
| Purpose | Ship a working coach for one real person | Research: does a richer model beat BKT's mastery-only view, and does any of it transfer to real data later |

Concretely: fitting PFA/LKT via logistic regression on a synthetic
population of hundreds of students is not the same class of thing as the
rejected pyKT deep-learning models (which require gradient descent,
embeddings, `torch`, and population-scale *real* data) — it's classical
statistics at a compute cost `ex1.md` never objected to. This report
recommends the project explicitly track this as **two parallel, non-
interfering workstreams**, not a replacement of the existing decision:
the shipped tool keeps using fixed-param BKT exactly as decided, while this
synthetic benchmark separately investigates whether PFA/LKT are worth
adopting *if and when* enough real data ever accumulates to fit them safely
— a question `ex1.md` explicitly left open ("may revisit after months of
real usage," §9's rejection table) rather than closed.
