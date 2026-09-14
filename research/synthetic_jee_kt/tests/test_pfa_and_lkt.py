import pytest
import numpy as np
import pandas as pd
from models.pfa import PFAModel
from models.lkt import LKTModel
from evaluation.splits import student_level_split


@pytest.fixture
def sample_trajectories():
    # 6 students, 2 concepts, 20 interactions each
    rows = []
    rng = np.random.default_rng(42)
    for s_idx in range(6):
        sid = f"STU_{s_idx}"
        cur_time = 1000.0
        for i_idx in range(20):
            cid = "Concept_A" if i_idx % 2 == 0 else "Concept_B"
            cur_time += float(rng.uniform(60, 3600))
            corr = int(rng.random() < (0.4 + 0.02 * i_idx))
            rows.append({
                "student_id": sid,
                "question_id": f"Q_{i_idx}",
                "concept_id": cid,
                "difficulty": 0.50,
                "timestamp": cur_time,
                "correct": corr,
                "world_id": "A",
                "ground_truth_mastery": 0.3 + 0.02 * i_idx,
            })
    return pd.DataFrame(rows)


def test_pfa_model_feature_extraction_and_fit(sample_trajectories):
    train_df = sample_trajectories[sample_trajectories["student_id"].isin(["STU_0", "STU_1", "STU_2", "STU_3"])]
    test_df = sample_trajectories[sample_trajectories["student_id"].isin(["STU_4", "STU_5"])]

    pfa = PFAModel()
    pfa.fit(train_df)

    # Evaluate sequentially on test_df
    preds = pfa.evaluate_sequential(test_df)
    assert len(preds) == len(test_df)
    assert all(0.0 <= p <= 1.0 for p in preds)


def test_lkt_model_feature_extraction_and_fit(sample_trajectories):
    train_df = sample_trajectories[sample_trajectories["student_id"].isin(["STU_0", "STU_1", "STU_2", "STU_3"])]
    test_df = sample_trajectories[sample_trajectories["student_id"].isin(["STU_4", "STU_5"])]

    lkt = LKTModel()
    lkt.fit(train_df)

    # Evaluate sequentially on test_df
    preds = lkt.evaluate_sequential(test_df)
    assert len(preds) == len(test_df)
    assert all(0.0 <= p <= 1.0 for p in preds)


def test_no_leakage_in_sequential_feature_computation():
    # Verify that the first question for any student ALWAYS has 0 prior successes/failures
    df = pd.DataFrame([
        {"student_id": "S1", "concept_id": "C1", "difficulty": 0.5, "timestamp": 10.0, "correct": 1},
        {"student_id": "S1", "concept_id": "C1", "difficulty": 0.5, "timestamp": 20.0, "correct": 0},
    ])
    pfa = PFAModel()
    pfa.fit(df)

    tracker = pfa.create_tracker("S1")
    f0 = tracker.get_features("C1")
    assert f0["successes"] == 0
    assert f0["failures"] == 0

    tracker.update("C1", outcome=1)
    f1 = tracker.get_features("C1")
    assert f1["successes"] == 1
    assert f1["failures"] == 0


def test_benchmark_pipeline_smoke(sample_trajectories, tmp_path):
    from evaluation.run_benchmark import run_single_seed_benchmark

    results = run_single_seed_benchmark(
        sample_trajectories,
        models_to_run=["baseline", "bkt_default", "pfa", "lkt"],
        seed=42,
    )

    for m in ["baseline", "bkt_default", "pfa", "lkt"]:
        assert m in results
        assert "auc" in results[m]
        assert "rmse" in results[m]
        assert "log_loss" in results[m]
        assert "brier" in results[m]
    # Check BKT state recovery exists
    assert "state_recovery_mae" in results["bkt_default"]
    assert "state_recovery_r" in results["bkt_default"]
