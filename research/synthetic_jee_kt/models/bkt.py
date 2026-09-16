"""Bayesian Knowledge Tracing (BKT) with closed-form updates and EM/likelihood fitting."""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class BKTParameters:
    p_l0: float = 0.20  # Initial mastery prior
    p_t: float = 0.10   # Probability of learning (transition)
    p_s: float = 0.10   # Slip probability
    p_g: float = 0.25   # Guess probability


class BKTModel:
    """Standard Bayesian Knowledge Tracing model."""

    def __init__(self, default_params: Optional[BKTParameters] = None):
        self.default_params = default_params or BKTParameters()
        self.concept_params: Dict[str, BKTParameters] = {}
        self._states: Dict[Tuple[str, str], float] = {}  # (student_id, concept_id) -> P(L_t)

    def get_params(self, concept_id: str) -> BKTParameters:
        return self.concept_params.get(concept_id, self.default_params)

    def get_mastery(self, student_id: str, concept_id: str) -> float:
        """Returns current latent mastery belief P(L_t)."""
        key = (student_id, concept_id)
        if key not in self._states:
            params = self.get_params(concept_id)
            self._states[key] = params.p_l0
        return self._states[key]

    def predict(self, student_id: str, concept_id: str) -> float:
        """Predicts probability of correct response on next attempt."""
        params = self.get_params(concept_id)
        p_l = self.get_mastery(student_id, concept_id)
        p_c = p_l * (1.0 - params.p_s) + (1.0 - p_l) * params.p_g
        return float(np.clip(p_c, 0.001, 0.999))

    def update(self, student_id: str, concept_id: str, outcome: int) -> float:
        """Applies closed-form Bayesian posterior update and transition."""
        params = self.get_params(concept_id)
        p_l = self.get_mastery(student_id, concept_id)

        # Posterior calculation P(L_t | O_t)
        if outcome == 1:
            numerator = p_l * (1.0 - params.p_s)
            denominator = numerator + (1.0 - p_l) * params.p_g
        else:
            numerator = p_l * params.p_s
            denominator = numerator + (1.0 - p_l) * (1.0 - params.p_g)

        if denominator <= 1e-9:
            p_post = p_l
        else:
            p_post = numerator / denominator

        # Transition to t+1: P(L_{t+1}) = P(L_t | O_t) + (1 - P(L_t | O_t)) * P(T)
        p_next = p_post + (1.0 - p_post) * params.p_t
        p_next = float(np.clip(p_next, 0.0001, 0.9999))

        key = (student_id, concept_id)
        self._states[key] = p_next
        return p_next

    def fit(self, train_df: pd.DataFrame, max_concepts: int = 50) -> "BKTModel":
        """Fits BKT parameters per concept on training population via log-likelihood maximization."""
        grouped = train_df.groupby("concept_id")
        # Sort concepts by number of observations descending
        top_concepts = grouped.size().sort_values(ascending=False).head(max_concepts).index

        for cid in top_concepts:
            c_df = grouped.get_group(cid).sort_values(["student_id", "timestamp"])
            # Extract observation sequences per student
            sequences = [
                group["correct"].tolist()
                for _, group in c_df.groupby("student_id")
                if len(group) >= 3
            ]

            if len(sequences) >= 3:
                params = fit_bkt_for_sequences(sequences, self.default_params)
                self.concept_params[cid] = params

        return self


def compute_sequence_log_likelihood(
    params: BKTParameters, sequences: List[List[int]]
) -> float:
    """Computes total log-likelihood of observation sequences under BKT parameters."""
    total_ll = 0.0
    p_l0, p_t, p_s, p_g = params.p_l0, params.p_t, params.p_s, params.p_g

    for seq in sequences:
        p_l = p_l0
        for obs in seq:
            # P(O | L)
            p_correct = p_l * (1.0 - p_s) + (1.0 - p_l) * p_g
            p_obs = p_correct if obs == 1 else (1.0 - p_correct)
            total_ll += math.log(max(p_obs, 1e-9))

            # Posterior update
            if obs == 1:
                denom = p_l * (1.0 - p_s) + (1.0 - p_l) * p_g
                p_post = (p_l * (1.0 - p_s)) / max(denom, 1e-9)
            else:
                denom = p_l * p_s + (1.0 - p_l) * (1.0 - p_g)
                p_post = (p_l * p_s) / max(denom, 1e-9)

            p_l = p_post + (1.0 - p_post) * p_t

    return total_ll


def fit_bkt_for_sequences(
    sequences: List[List[int]], initial_params: BKTParameters
) -> BKTParameters:
    """Fits BKT parameters on sequences using bounded L-BFGS-B optimization."""

    def loss(x):
        p_l0, p_t, p_s, p_g = x
        p = BKTParameters(p_l0=p_l0, p_t=p_t, p_s=p_s, p_g=p_g)
        return -compute_sequence_log_likelihood(p, sequences)

    x0 = [
        initial_params.p_l0,
        initial_params.p_t,
        initial_params.p_s,
        initial_params.p_g,
    ]
    # Parameter bounds enforcing non-degenerate parameters
    bounds = [
        (0.01, 0.90),  # p_l0
        (0.01, 0.40),  # p_t
        (0.01, 0.40),  # p_s
        (0.01, 0.40),  # p_g
    ]

    res = minimize(loss, x0, bounds=bounds, method="L-BFGS-B")
    if res.success:
        return BKTParameters(
            p_l0=float(res.x[0]),
            p_t=float(res.x[1]),
            p_s=float(res.x[2]),
            p_g=float(res.x[3]),
        )
    return initial_params

