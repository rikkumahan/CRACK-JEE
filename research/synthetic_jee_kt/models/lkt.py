"""Logistic Knowledge Tracing (LKT) model with recency, difficulty, and opportunity features."""

import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.linear_model import LogisticRegression


class LKTTracker:
    """Maintains student opportunity counts, success/failure counts, and recency timestamps."""

    def __init__(self, student_id: str):
        self.student_id = student_id
        # concept_id -> {"successes": int, "failures": int, "last_timestamp": float}
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.last_global_timestamp: Optional[float] = None
        self.total_opportunities: int = 0
        self.total_successes: int = 0

    def get_features(self, concept_id: str, current_timestamp: float, difficulty: float) -> Dict[str, float]:
        if concept_id in self.concepts:
            c = self.concepts[concept_id]
            s = c["successes"]
            f = c["failures"]
            n = s + f
            rate = s / max(1, n)
            # Days since last practice on this concept
            dt_concept_days = max(0.0, (current_timestamp - c["last_timestamp"]) / 86400.0)
        else:
            s, f, n, rate = 0, 0, 0, 0.5
            dt_concept_days = 30.0  # default unpracticed lapse

        # Global student study history
        if self.last_global_timestamp is not None:
            dt_global_hours = max(0.0, (current_timestamp - self.last_global_timestamp) / 3600.0)
        else:
            dt_global_hours = 24.0

        global_rate = self.total_successes / max(1, self.total_opportunities)

        return {
            "successes": s,
            "failures": f,
            "attempts": n,
            "success_rate": rate,
            "log_dt_concept": math.log1p(dt_concept_days),
            "log_dt_global": math.log1p(dt_global_hours),
            "difficulty": difficulty,
            "total_attempts": self.total_opportunities,
            "global_success_rate": global_rate,
        }

    def update(self, concept_id: str, outcome: int, timestamp: float) -> None:
        if concept_id not in self.concepts:
            self.concepts[concept_id] = {"successes": 0, "failures": 0, "last_timestamp": timestamp}

        if outcome == 1:
            self.concepts[concept_id]["successes"] += 1
            self.total_successes += 1
        else:
            self.concepts[concept_id]["failures"] += 1

        self.concepts[concept_id]["last_timestamp"] = timestamp
        self.last_global_timestamp = timestamp
        self.total_opportunities += 1


class LKTModel:
    """Logistic Knowledge Tracing model (Pavlik et al. 2021)."""

    def __init__(self, max_concepts: int = 100, C: float = 1.0):
        self.max_concepts = max_concepts
        self.C = C
        self.concept_to_idx: Dict[str, int] = {}
        self.model: Optional[LogisticRegression] = None
        self.default_prior: float = 0.50

    def _build_feature_row(
        self, tracker: LKTTracker, concept_id: str, timestamp: float, difficulty: float
    ) -> np.ndarray:
        # Base features per concept: [KC intercept, success count, failure count]
        # Global features: [difficulty, log_dt_concept, log_dt_global, success_rate, global_rate, total_attempts]
        K = len(self.concept_to_idx)
        n_global = 6
        dim = 3 * K + n_global
        vec = np.zeros(dim, dtype=np.float32)

        feat = tracker.get_features(concept_id, timestamp, difficulty)

        # Global features
        vec[3 * K] = feat["difficulty"]
        vec[3 * K + 1] = feat["log_dt_concept"]
        vec[3 * K + 2] = feat["log_dt_global"]
        vec[3 * K + 3] = feat["success_rate"]
        vec[3 * K + 4] = feat["global_success_rate"]
        vec[3 * K + 5] = math.log1p(feat["total_attempts"])

        # Concept-specific features
        if concept_id in self.concept_to_idx:
            idx = self.concept_to_idx[concept_id]
            vec[idx] = 1.0
            vec[K + idx] = math.log1p(feat["successes"])
            vec[2 * K + idx] = math.log1p(feat["failures"])

        return vec

    def fit(self, train_df: pd.DataFrame) -> "LKTModel":
        """Fits LKT logistic regression model on training sequences."""
        if len(train_df) == 0:
            return self

        self.default_prior = float(train_df["correct"].mean())

        top_concepts = (
            train_df["concept_id"].value_counts().head(self.max_concepts).index.tolist()
        )
        self.concept_to_idx = {cid: i for i, cid in enumerate(top_concepts)}
        K = len(self.concept_to_idx)
        dim = 3 * K + 6

        df_sorted = train_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
        X = lil_matrix((len(df_sorted), dim), dtype=np.float32)
        y = df_sorted["correct"].values.astype(np.int32)

        trackers: Dict[str, LKTTracker] = {}

        for row_idx, row in df_sorted.iterrows():
            sid = row["student_id"]
            cid = row["concept_id"]
            ts = float(row.get("timestamp", 0.0))
            diff = float(row.get("difficulty", 0.50))
            outcome = int(row["correct"])

            if sid not in trackers:
                trackers[sid] = LKTTracker(sid)

            # Features BEFORE current attempt
            row_feat = self._build_feature_row(trackers[sid], cid, ts, diff)
            for c_idx, val in enumerate(row_feat):
                if val != 0.0:
                    X[row_idx, c_idx] = val

            # Update tracker
            trackers[sid].update(cid, outcome, ts)

        self.model = LogisticRegression(C=self.C, max_iter=200, solver="lbfgs")
        self.model.fit(X.tocsr(), y)
        return self

    def evaluate_sequential(self, test_df: pd.DataFrame) -> np.ndarray:
        """Evaluates model strictly sequentially on test students."""
        if len(test_df) == 0:
            return np.array([])
        if self.model is None:
            return np.full(len(test_df), self.default_prior)

        df_sorted = test_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
        predictions = np.zeros(len(df_sorted), dtype=np.float64)

        trackers: Dict[str, LKTTracker] = {}

        for row_idx, row in df_sorted.iterrows():
            sid = row["student_id"]
            cid = row["concept_id"]
            ts = float(row.get("timestamp", 0.0))
            diff = float(row.get("difficulty", 0.50))
            outcome = int(row["correct"])

            if sid not in trackers:
                trackers[sid] = LKTTracker(sid)

            row_feat = self._build_feature_row(trackers[sid], cid, ts, diff).reshape(1, -1)
            p_correct = float(self.model.predict_proba(row_feat)[0, 1])
            predictions[row_idx] = p_correct

            trackers[sid].update(cid, outcome, ts)

        return predictions
