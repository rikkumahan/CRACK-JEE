# Experimental Protocol — Synthetic JEE KT Benchmark

_Written 2026-09-14. Specifies train/val/test splitting, metrics, baselines,
ablations, and seeds. Grounded in
[`research-validation-report.md`](research-validation-report.md) Q9, Q12,
Q13. Antigravity implements against this; do not redesign the split or
metric choices without updating the validation report first._

## 1. Data splitting

**Two controls, applied together (validation report Q9):**

1. **Student-level holdout** (field convention, verified against pyKT's own
   methodology): synthetic students are partitioned wholesale —
   60% train / 20% validation / 20% test — no student's interactions
   appear in more than one split. This also directly enables the cross-
   world tests in §4 (e.g. train-split students drawn from Worlds A+B+C,
   test-split students drawn from Worlds D+E).
2. **Sequential-in-time prediction** — inherent to how BKT/PFA/LKT update:
   a prediction for interaction *t* uses only that student's history before
   *t*. No additional chronological cutoff is needed within a student's
   sequence; this falls out of the online-update structure automatically
   as long as the implementation processes each student's interactions in
   timestamp order and never looks ahead.
3. **All-in-one multi-KC prediction** — if a question is tagged to
   multiple concepts (weighted `question_concepts`, brief §3), predict all
   of its concept-outcomes simultaneously rather than one at a time
   (pyKT's fix for the sibling-KC leak, validation report Q9). Only
   relevant once World G (multi-concept interference) or any multi-concept
   question is in a given experiment.

Audit checklist before any result is reported (per brief §17):
- [ ] No synthetic student appears in more than one of train/val/test.
- [ ] No prediction uses an interaction timestamped after the one being
      predicted, for that student.
- [ ] Concept-level statistics used as model *input* (e.g. a running
      success/failure count for PFA) are computed only from that student's
      own past, never from the full population or future.
- [ ] If multi-concept questions are used, all-in-one prediction is applied.

## 2. Metrics

Per validation report Q12/Q13 — **do not apply a uniform metric across
model families**; PFA/LKT do not expose a state comparable to BKT's.

### Next-response prediction (all models)
- **AUC** — primary metric, used by every KT paper read in the validation
  pass (DKT, GKT, LKT, PFA-via-A').
- **Log loss** — secondary, matches PFA/DKT's own training objective.
- **RMSE** — secondary, reported by LKT in every one of its result tables.
- **Brier score** — included as a standard calibration metric, but flagged
  per Q13: not found in any primary KT source read this session, so cite it
  as general ML practice, not KT-literature precedent.
- Accuracy — tertiary/sanity-check only, not a primary comparison metric
  (accuracy is misleading under class imbalance, which the Pagonis finding
  on BKT/majority-class bias makes directly relevant here).

### Latent-state recovery — **BKT only**
Compare BKT's recovered `mastery_probability` against the simulator's true
`mastery` (ground truth, from `student_ground_truth.csv`) at matched
timestamps: Pearson correlation + MAE. **Do not compute this for PFA/LKT**
as a "state recovery" claim — per Q12, their output is a predicted-
correctness score, not a mastery estimate. For PFA/LKT/DKT/GKT, instead
report the correlation between their predicted-correctness trajectory and
the true simulated ability curve, explicitly labeled "predicted-probability
vs. true-ability correlation" in any report, never "state recovery."

### Data efficiency
Re-run the next-response-prediction metrics at truncated history lengths
(10/25/50/100/250/500/1000+ interactions per student, per brief §10C) to
produce a learning curve per model — this is the metric that matters most
for the eventual single-real-student use case, where history will always
be short.

## 3. Baselines and models (build order)

```
1. Recent-accuracy baseline   — rolling accuracy over last N attempts per concept, no state
2. BKT                        — literature-default AND, separately, EM-fit on the synthetic population (both reported)
3. PFA                        — logistic regression, scikit-learn, CPU-only
4. LKT                        — logistic regression over the feature set in synthetic-learner-spec.md §1 core variables
```

Do not implement ReKT/GKT/DKT in this phase — brief §11 and the validation
report's own tooling findings (neither pyKT nor EduStudio ships BKT/PFA/LKT
at all; both are deep-model-only) confirm those are a separate, heavier
workstream with no runnable-code shortcut available, and brief §11
explicitly says not to assume newer/deeper is better without first
establishing whether the added complexity earns its cost against these
baselines.

## 4. Cross-world evaluation (brief §8)

Minimum required experiment set:
```
Train: Worlds A + B + C   →  Test: Worlds D + E
Train: Worlds A + D       →  Test: Worlds B + G
Train: all worlds except H →  Test: held-out students from each world individually (per-world breakdown)
```
World H is excluded from the first benchmark entirely (deferred, §synthetic-learner-spec.md §5).

Report both **within-world** (train and test students from the same
world(s)) and **cross-world** (disjoint world sets) numbers for every
model — the gap between them is itself the headline result answering
brief §8's actual question (does the model generalize beyond the
simulator's own generative assumptions, or does it only look good on data
shaped like what it was tuned against).

## 5. Ablations

- Core-variable-only vs. core+extended-variable generation (tests whether
  the "unverified, plausible" extended traits in `synthetic-learner-spec.md`
  §1 actually change which model wins — if they don't, that's useful
  evidence they can stay deferred).
- Single-concept-only vs. multi-concept-question-inclusive (tests whether
  PFA's compensatory-sum advantage over BKT, found in the validation
  report's Q5 literature check, actually shows up in this synthetic setup).
- Fixed-default BKT vs. EM-fit-on-synthetic-population BKT (directly tests
  whether fitting helps at population scale — informs, but does not by
  itself justify, ever fitting BKT for the real single-student product;
  see validation report's reconciliation section).

## 6. Random seeds and reproducibility

- One global seed per full experiment run, propagated to every stochastic
  draw (student parameter sampling, Bernoulli outcome sampling, response-
  time lognormal draws) via a single seeded RNG instance passed through the
  generator — no unseeded `random`/`np.random` global-state calls anywhere
  in the simulator.
- Report results averaged over **5 seeds minimum**, with the spread
  (std dev or min/max) shown alongside every headline number — a single-
  seed result is not reportable as a finding.
- `student_ground_truth.csv` and `synthetic_interactions.csv` (brief §9)
  are regenerable byte-for-byte from `(seed, world, archetype config)` —
  store the generation config alongside the output files, not just the
  files themselves.
