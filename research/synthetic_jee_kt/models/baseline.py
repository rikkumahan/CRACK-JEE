"""Recent-accuracy baseline model."""

from collections import deque
from typing import Dict, Optional, Tuple
import pandas as pd


class RecentAccuracyBaseline:
    """Predicts next response probability based on recent accuracy on the KC."""

    def __init__(self, window_size: int = 5, default_prob: float = 0.50):
        self.window_size = window_size
        self.default_prob = default_prob
        self._history: Dict[Tuple[str, str], deque] = {}
        self._concept_prior: Dict[str, float] = {}
        self._global_prior: float = default_prob

    def fit(self, train_df: pd.DataFrame) -> "RecentAccuracyBaseline":
        """Computes concept priors from training dataset."""
        if len(train_df) == 0:
            return self

        self._global_prior = float(train_df["correct"].mean())
        grouped = train_df.groupby("concept_id")["correct"].mean()
        self._concept_prior = grouped.to_dict()
        return self

    def predict(self, student_id: str, concept_id: str) -> float:
        """Returns predicted probability of correct answer."""
        key = (student_id, concept_id)
        if key in self._history and len(self._history[key]) > 0:
            return float(sum(self._history[key]) / len(self._history[key]))

        # Cold start fallback
        return self._concept_prior.get(concept_id, self._global_prior)

    def update(self, student_id: str, concept_id: str, outcome: int) -> None:
        """Updates rolling history with observed outcome."""
        key = (student_id, concept_id)
        if key not in self._history:
            self._history[key] = deque(maxlen=self.window_size)
        self._history[key].append(outcome)

    def reset_student(self, student_id: str) -> None:
        keys_to_del = [k for k in self._history if k[0] == student_id]
        for k in keys_to_del:
            del self._history[k]

