"""Bayesian Knowledge Tracing: pure functions, no DB dependency.

Fixed literature-default parameters, per ex1.md §7.2 — not fitted on her
data (not enough volume to fit reliably). Same defaults used by the
synthetic-KT research track's BKTParameters for consistency across the repo.
"""
from typing import Literal

P_L0 = 0.20  # initial mastery prior
P_T = 0.10  # learning/transition rate
P_S = 0.10  # slip rate
P_G = 0.25  # guess rate

Result = Literal["correct", "wrong", "unattempted"]


def update_mastery(prior: float, result: Result) -> float:
    """Closed-form Bayesian update + transition. `unattempted` carries no
    evidence about knowledge (she didn't try), so mastery passes through
    unchanged — only correct/wrong update the posterior."""
    if result == "unattempted":
        return prior

    if result == "correct":
        numerator = prior * (1.0 - P_S)
        denominator = numerator + (1.0 - prior) * P_G
    else:
        numerator = prior * P_S
        denominator = numerator + (1.0 - prior) * (1.0 - P_G)

    posterior = numerator / denominator if denominator > 0 else prior
    return posterior + (1.0 - posterior) * P_T


def apply_decay(mastery: float, days_since_last_attempt: float) -> float:
    """Simple time-decay nudge (ex1.md §7.3) — not a fitted forgetting
    curve. 14-day grace period, then ×0.97 per additional full week idle,
    floored at 0.3 so it never implies "never learned." Read-time only,
    never written back."""
    grace_days = 14
    floor = 0.3
    if days_since_last_attempt <= grace_days:
        return mastery
    idle_weeks = (days_since_last_attempt - grace_days) / 7.0
    return floor + (mastery - floor) * (0.97**idle_weeks)
