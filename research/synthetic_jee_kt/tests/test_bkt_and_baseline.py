import pytest
import numpy as np
import pandas as pd
from models.baseline import RecentAccuracyBaseline
from models.bkt import BKTModel, BKTParameters
from evaluation.splits import student_level_split
from evaluation.metrics import compute_prediction_metrics, compute_state_recovery_metrics


def test_recent_accuracy_baseline():
    baseline = RecentAccuracyBaseline(window_size=3, default_prob=0.5)

    # Cold start
    p0 = baseline.predict("S1", "C1")
    assert p0 == 0.5

    # Update with 1, 1, 1
    baseline.update("S1", "C1", 1)
    assert baseline.predict("S1", "C1") == 1.0
    baseline.update("S1", "C1", 1)
    baseline.update("S1", "C1", 1)
    assert baseline.predict("S1", "C1") == 1.0

    # Next outcome is 0 -> window of 3 is [1, 1, 0] -> 2/3
    baseline.update("S1", "C1", 0)
    assert pytest.approx(baseline.predict("S1", "C1")) == 2.0 / 3.0


def test_bkt_bayesian_updates():
    params = BKTParameters(p_l0=0.20, p_t=0.10, p_s=0.10, p_g=0.25)
    bkt = BKTModel(default_params=params)

    # Initial state
    p_c1 = bkt.predict("S1", "C1")
    expected_initial = 0.20 * (1 - 0.10) + 0.80 * 0.25
    assert pytest.approx(p_c1) == expected_initial

    # Correct response should increase mastery
    m0 = bkt.get_mastery("S1", "C1")
    bkt.update("S1", "C1", 1)
    m1 = bkt.get_mastery("S1", "C1")
    assert m1 > m0

    # Three more correct responses
    for _ in range(3):
        bkt.update("S1", "C1", 1)
    m4 = bkt.get_mastery("S1", "C1")
    assert m4 > m1
    assert m4 < 1.0

    # Wrong response should decrease mastery relative to preceding state
    bkt.update("S1", "C1", 0)
    m5 = bkt.get_mastery("S1", "C1")
    assert m5 < m4


def test_bkt_em_fitting():
    # Synthetic sequences on concept C1: 10 students who learn quickly
    data = []
    for sid in range(10):
        # Starts wrong, then mostly correct
        seq = [0, 0, 1, 1, 1, 1, 1]
        for t, corr in enumerate(seq):
            data.append({
                "student_id": f"S{sid}",
                "concept_id": "C1",
                "timestamp": t,
                "correct": corr,
            })
    df = pd.DataFrame(data)

    model = BKTModel()
    model.fit(df)

    fitted_params = model.get_params("C1")
    assert fitted_params.p_t > 0.0
    assert fitted_params.p_s < 0.45
    assert fitted_params.p_g < 0.45


def test_student_level_split():
    df = pd.DataFrame({
        "student_id": [f"S{i}" for i in range(100) for _ in range(5)],
        "timestamp": [t for _ in range(100) for t in range(5)],
        "correct": [1] * 500,
    })

    train_df, val_df, test_df = student_level_split(df, train_frac=0.6, val_frac=0.2, test_frac=0.2, seed=42)

    train_students = set(train_df["student_id"])
    val_students = set(val_df["student_id"])
    test_students = set(test_df["student_id"])

    # Disjoint splits (no leakage)
    assert len(train_students & test_students) == 0
    assert len(train_students & val_students) == 0
    assert len(val_students & test_students) == 0
    assert len(train_students) == 60
    assert len(val_students) == 20
    assert len(test_students) == 20


def test_evaluation_metrics():
    y_true = np.array([0, 1, 1, 0, 1, 0, 1, 1])
    y_pred = np.array([0.1, 0.9, 0.8, 0.2, 0.7, 0.3, 0.85, 0.95])

    metrics = compute_prediction_metrics(y_true, y_pred)
    assert metrics["auc"] > 0.90
    assert metrics["log_loss"] < 0.50
    assert metrics["rmse"] < 0.40
    assert metrics["brier"] < 0.20

    # State recovery metrics
    true_state = np.array([0.2, 0.3, 0.5, 0.7, 0.85])
    est_state = np.array([0.25, 0.35, 0.48, 0.65, 0.80])
    rec = compute_state_recovery_metrics(true_state, est_state)
    assert rec["pearson_r"] > 0.95
    assert rec["mae"] < 0.10
