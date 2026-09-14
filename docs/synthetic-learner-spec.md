# Synthetic Learner Specification

_Written 2026-09-14. Defines the generative mechanism precisely enough to
implement without further design decisions. Grounded in
[`research-validation-report.md`](research-validation-report.md) — see Q10
(independence requirement), Q11 (core vs. extended variables), Q3/Q4
(circularity risk). Parameters, not code — Antigravity implements this._

## Design rule this spec exists to satisfy

Per the validation report's Q3/Q4/Q10 finding: the only defensible
precedent for synthetic-vs-real KT evaluation (Pagonis et al. 2024) used
generators that were **mathematically independent** of the models being
tested. This spec's core P(correct) equation is therefore a **Rasch/2PL-IRT-
style logit** (ability − difficulty → sigmoid), not BKT's discrete HMM
transition and not PFA/LKT's success/failure-count logistic form. It is a
third mathematical family, deliberately, so that evaluating BKT, PFA, and
LKT against data this generator produces is not tautological for any of
them. World A (below) intentionally uses BKT-*like* dynamics for the
*mastery update*, but even there the response-generation logit stays IRT-
shaped — only the learning/forgetting dynamics vary by world, never the
observation model, which keeps every world's data non-circular against
every tested KT model.

## 1. State variables

### Core (grounded in BKT/PFA/LKT per validation report Q11 — required for V1)

Per synthetic student, per concept:
- `mastery` (0–1, continuous) — analogous to BKT's P(Ln), but updated by
  this spec's own learning-curve rule (§3), not BKT's Bayesian update.
- `learning_rate` — per-student scalar (with small per-concept jitter),
  controls how fast `mastery` moves toward 1 with practice.
- `forgetting_rate` — per-student scalar, controls decay of `mastery`
  when the concept isn't practiced.

Per synthetic student, global:
- `guess_rate` — analogous to BKT's G, but sampled per-student (not a
  fixed literature default) so student populations vary.
- `slip_rate` — analogous to BKT's S, same treatment.
- `baseline_speed` — median seconds-per-question at matched difficulty.

### Extended (plausible, not independently literature-verified this session — optional, used only in specific Worlds per §5, never required for the core benchmark)

- `careless_error_tendency`, `calculation_error_tendency`,
  `reading_misinterpretation_tendency` — sub-split `slip_rate` into causes
  for the error-mechanism generator (§4), used in Worlds D/G.
- `time_pressure_sensitivity` — used in World E only.
- `confidence_calibration_bias` — used in World F only.
- `response_time_variability` — used everywhere response time is generated
  (§6), but as a fixed small default outside Worlds E/F.
- Intervention-response sensitivities (worked-example/hint/practice/timed-
  practice) — **not implemented in the first benchmark**, per brief §10E
  and the validation report's Q11 recommendation. Reserved for Phase 6+.

## 2. P(correct) equation

For a single-concept question of difficulty `d` (0–1, from eQOURSE's
Easy/Moderate/Tough mapped to a numeric scale, e.g. 0.25/0.5/0.75):

```
effective_mastery = forget(mastery, days_since_last_practice)     # §3.2
ability_logit     = k * (effective_mastery - d)                    # k: fixed scale constant, e.g. 4
p_know             = sigmoid(ability_logit)
p_correct          = p_know * (1 - slip_rate) + (1 - p_know) * guess_rate
outcome            = Bernoulli(p_correct)
```

For a multi-concept question (brief §3's weighted `question_concepts`,
e.g. `Q184 → Torque 0.7, Vector Decomposition 0.3`): compute
`effective_mastery` as the weighted average of each concept's effective
mastery before the logit step — a compensatory combination, echoing PFA's
own justification for compensatory multi-skill handling (validation report
Q5), but computed on mastery, not on success/failure counts, so the
independence property in §0 still holds.

World C (prerequisite-dependent, §5) additionally gates `effective_mastery`
by the prerequisite concept's own effective mastery — see §5.

## 3. Learning and forgetting dynamics

### 3.1 Learning (on every attempt, correct or not)

```
gain = learning_rate * (1 - mastery) * (0.6 + 0.4 * outcome)
mastery_new = mastery + gain
```

Exposure to a question moves `mastery` even on a wrong answer (productive
struggle), but a correct answer moves it further — a reasonable
simplification, not sourced from a specific verified paper this session
(flagged, matching the validation report's honesty standard). Diminishing
returns via `(1 - mastery)` avoids an unbounded/unrealistic runaway.

### 3.2 Forgetting (applied at read time, not on write — matches this project's own existing convention in `docs/tool-implementation-plan.md` Step 4, `ex1.md` §7.3: "a simple time-decay nudge, not curve-fitting")

```
grace_days = 14
if days_since_last_practice <= grace_days:
    effective_mastery = mastery
else:
    idle = days_since_last_practice - grace_days
    effective_mastery = floor + (mastery - floor) * exp(-forgetting_rate * idle)
    # floor = 0.15, so forgetting never implies "never learned"
```

## 4. Error mechanism generation

Per validation report Q11, the brief's 11-category taxonomy was not
independently checked against educational-error literature this session.
**Simplify to five mechanisms for V1**, chosen so each maps cleanly to an
already-defined state variable rather than inventing new unverified ones:

```
GUESS          — fires when p_know was low but outcome sampled correct via guess_rate path (tracked, not inferred)
CONCEPT_GAP    — outcome wrong, p_know was low (mastery genuinely insufficient)
SLIP           — outcome wrong, p_know was high (slip_rate path fired)
CALCULATION    — outcome wrong, p_know was moderate — covers arithmetic/sign/unit errors folded together
TIME_PRESSURE  — outcome wrong, only sampled with elevated probability when a World-E-style time constraint is active
```

`READING`, `SIGN`, `UNIT`, `CONCEPT_APPLICATION`, and `QUESTION_SELECTION`
from the brief's original taxonomy are folded into `CALCULATION` or
`CONCEPT_GAP` for V1. If Worlds D/G (extended-variable worlds) need finer
granularity, split `CALCULATION` using
`calculation_error_tendency`/`reading_misinterpretation_tendency` at that
point — don't build the finer taxonomy until a world actually needs it.

The error type is assigned deterministically from which branch of the
P(correct) computation produced the wrong outcome (which p_know band, which
stochastic path) — not a separate `P(error_type | ...)` model as the brief
proposed, because the outcome-generation process in §2 already determines
this without a second probability model to parameterize and justify.

## 5. Multiple synthetic "Worlds" (brief §8)

Every world shares the same P(correct) observation model (§2) and error
generator (§4) — only the **learning/forgetting/gating dynamics** differ.
This is what keeps cross-world evaluation meaningful (train on A+B+C, test
on D+E) without silently changing what "correct" means between worlds.

| World | What varies from the default (§3) |
|---|---|
| A — BKT-like | `learning_rate` high, mastery updates in larger discrete-feeling steps (small `(1-mastery)` exponent removed, i.e. near-linear gain) — closest to a two-state feel, but still continuous and still uses the shared IRT-shaped observation model (§0) |
| B — strong forgetting | `forgetting_rate` sampled from a higher-mean distribution; `grace_days` reduced to 7 |
| C — prerequisite-dependent | Concepts carry a `prerequisite_id`; `effective_mastery` is additionally capped at `prerequisite_effective_mastery + 0.3` — can't out-master a concept whose prerequisite is unlearned |
| D — high careless-error | `slip_rate` and `careless_error_tendency` sampled from elevated distributions |
| E — time-pressure | Response-time budget introduced per question; when `time_taken` would exceed budget, `TIME_PRESSURE` error probability rises and `p_correct` is discounted by `time_pressure_sensitivity` |
| F — poorly calibrated confidence | `confidence_calibration_bias` sampled with high variance/high magnitude (§7) |
| G — multi-concept interference | Multi-concept questions (§2's weighted case) are the majority of items, not the minority; weights skewed so no single concept dominates |
| H — intervention-responsive | **Deferred** — not built in the first benchmark (brief §10E), reserved for Phase 6+ once the core benchmark works |

## 6. Response-time generation

```
difficulty_factor = 1 + d          # harder questions take longer
time_taken = lognormal(
    mean = log(baseline_speed * difficulty_factor),
    sigma = 0.3 + response_time_variability
)
```

Not sourced from a specific verified paper this session — a standard
lognormal response-time model, flagged per the same honesty standard as
§3.1.

## 7. Confidence generation

Only populated in worlds/experiments that use it (not required for the
core BKT/PFA/LKT benchmark, since none of the three verified core models
consume a confidence field per validation report Q5):

```
raw_confidence = p_know
confidence = clip(raw_confidence + confidence_calibration_bias + noise(0, 0.1), 0, 1)
```

## 8. Heterogeneous population (brief §7)

The ten named archetypes (S01–S10) are **parameter presets**, not separate
code paths — each is a named point (or narrow distribution) in the state-
variable space defined in §1, applied when sampling a synthetic student
within a world. E.g. "S01 — strong but careless" = high `mastery`
init/`learning_rate`, high `slip_rate`/`careless_error_tendency`, normal
everything else. Document the exact preset values in the implementation
config (`configs/archetypes.yaml` or similar — Antigravity's call at
implementation time), not here — this spec fixes the mechanism, not the
tuning.

## 9. What this spec deliberately does not include

- Intervention response (brief §5's `intervention response (later)` field,
  §10E, §20's StudentSim-direction) — explicitly Phase 6+, not V1, per
  brief §10E itself.
- A separate `P(error_type | student_state, question_state, context)`
  model — folded into the outcome-generation branches in §4 instead, since
  a second free-standing probability model would need its own
  justification/validation this session didn't produce.
- Any per-student latent trait not listed in §1 as core or extended —
  adding one requires updating the validation report's Q11 answer first.
