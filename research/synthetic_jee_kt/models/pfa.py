"""Performance Factors Analysis (PFA) model via regularized logistic regression."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.linear_model import LogisticRegression


class PFATracker:
    """Maintains running success and failure counts per student per concept."""

    def __init__(self, student_id: str):
        self.student_id = student_id
        # concept_id -> {"successes": int, "failures": int}
        self.counts: Dict[str, Dict[str, int]] = {}

    def get_features(self, concept_id: str) -> Dict[str, int]:
        c = self.counts.get(concept_id, {"successes": 0, "failures": 0})
        return {"successes": c["successes"], "failures": c["failures"]}

    def update(self, concept_id: str, outcome: int) -> None:
        if concept_id not in self.counts:
            self.counts[concept_id] = {"successes": 0, "failures": 0}
        if outcome == 1:
            self.counts[concept_id]["successes"] += 1
        else:
            self.counts[concept_id]["failures"] += 1


class PFAModel:
    """Performance Factors Analysis model (Pavlik et al. 2009).

    logit(P(C)) = sum_k q_{j,k} * (beta_k + gamma_k * s_{i,k} + rho_k * f_{i,k})
    """

    def __init__(self, max_concepts: int = 100, C: float = 1.0):
        self.max_concepts = max_concepts
        self.C = C
        self.concept_to_idx: Dict[str, int] = {}
        self.model: Optional[LogisticRegression] = None
        self.default_prior: float = 0.50

    def _build_feature_row(self, tracker: PFATracker, concept_id: str) -> np.ndarray:
        # Features: [K concept intercepts, K success counts, K failure counts, 1 general success, 1 general failure]
        K = len(self.concept_to_idx)
        dim = 3 * K + 2
        vec = np.zeros(dim, dtype=np.float32)

        feat = tracker.get_features(concept_id)
        s, f = feat["successes"], feat["failures"]

        # General counts across all concepts
        tot_s = sum(c["successes"] for c in tracker.counts.values())
        tot_f = sum(c["failures"] for c in tracker.counts.values())
        vec[3 * K] = np.log1p(tot_s)
        vec[3 * K + 1] = np.log1p(tot_f)

        if concept_id in self.concept_to_idx:
            idx = self.concept_to_idx[concept_id]
            vec[idx] = 1.0               # beta_k (KC intercept)
            vec[K + idx] = np.log1p(s)   # gamma_k * s_{i,k}
            vec[2 * K + idx] = np.log1p(f) # rho_k * f_{i,k}

        return vec

    def create_tracker(self, student_id: str) -> PFATracker:
        return PFATracker(student_id)

    def fit(self, train_df: pd.DataFrame) -> "PFAModel":
        """Fits PFA logistic regression model on training sequences."""
        if len(train_df) == 0:
            return self

        self.default_prior = float(train_df["correct"].mean())

        # Select top K concepts
        top_concepts = (
            train_df["concept_id"].value_counts().head(self.max_concepts).index.tolist()
        )
        self.concept_to_idx = {cid: i for i, cid in enumerate(top_concepts)}
        K = len(self.concept_to_idx)
        dim = 3 * K + 2

        # Sort training data chronologically per student
        df_sorted = train_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)

        X = lil_matrix((len(df_sorted), dim), dtype=np.float32)
        y = df_sorted["correct"].values.astype(np.int32)

        trackers: Dict[str, PFATracker] = {}

        for row_idx, row in df_sorted.iterrows():
            sid = row["student_id"]
            cid = row["concept_id"]
            outcome = int(row["correct"])

            if sid not in trackers:
                trackers[sid] = PFATracker(sid)

            # Extract features BEFORE observing current outcome (leakage prevention)
            row_feat = self._build_feature_row(trackers[sid], cid)
            for c_idx, val in enumerate(row_feat):
                if val != 0.0:
                    X[row_idx, c_idx] = val

            # Update tracker with current outcome
            trackers[sid].update(cid, outcome)

        self.model = LogisticRegression(C=self.C, max_iter=200, solver="lbfgs")
        self.model.fit(X.tocsr(), y)
        return self

    def evaluate_sequential(self, test_df: pd.DataFrame) -> np.ndarray:
        """Evaluates model strictly sequentially on test students to prevent lookahead leakage."""
        if len(test_df) == 0:
            return np.array([])
        if self.model is None:
            return np.full(len(test_df), self.default_prior)

        K = len(self.concept_to_idx)
        dim = 3 * K + 2

        df_sorted = test_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
        predictions = np.zeros(len(df_sorted), dtype=np.float64)

        trackers: Dict[str, PFATracker] = {}

        for row_idx, row in df_sorted.iterrows():
            sid = row["student_id"]
            cid = row["concept_id"]
            outcome = int(row["correct"])

            if sid not in trackers:
                trackers[sid] = PFATracker(sid)

            # Predict using history strictly before step t
            row_feat = self._build_feature_row(trackers[sid], cid).reshape(1, -1)
            p_correct = float(self.model.predict_proba(row_feat)[0, 1])
            predictions[row_idx] = p_correct

            # Update tracker after prediction
            trackers[sid].update(cid, outcome)

        return predictions

