import pytest
import numpy as np
import pandas as pd
from evaluation.cross_world import (
    cross_world_split,
    run_cross_world_experiment,
    run_per_world_breakdown,
)


@pytest.fixture
def multi_world_dataset():
    # 5 worlds (A, B, D, E, G), 4 students each, 15 interactions each
    rows = []
    rng = np.random.default_rng(42)
    for wid in ["A", "B", "D", "E", "G"]:
        for s_idx in range(4):
            sid = f"STU_{wid}_{s_idx}"
            cur_time = 1000.0
            for i_idx in range(15):
                cur_time += float(rng.uniform(60, 3600))
                rows.append({
                    "student_id": sid,
                    "world_id": wid,
                    "question_id": f"Q_{i_idx}",
                    "concept_id": f"Concept_{i_idx % 3}",
                    "difficulty": 0.50,
                    "timestamp": cur_time,
                    "correct": int(rng.random() < 0.6),
                    "ground_truth_mastery": 0.5,
                })
    return pd.DataFrame(rows)


def test_cross_world_split_disjoint(multi_world_dataset):
    train_df, test_df = cross_world_split(
        multi_world_dataset,
        train_worlds=["A", "B"],
        test_worlds=["D", "E"],
    )

    train_students = set(train_df["student_id"])
    test_students = set(test_df["student_id"])

    # Disjoint worlds and students
    assert len(train_students & test_students) == 0
    assert set(train_df["world_id"].unique()) == {"A", "B"}
    assert set(test_df["world_id"].unique()) == {"D", "E"}


def test_cross_world_experiment_execution(multi_world_dataset):
    results = run_cross_world_experiment(
        multi_world_dataset,
        train_worlds=["A", "B"],
        test_worlds=["D", "E"],
        models=["baseline", "bkt_default", "pfa", "lkt"],
    )

    assert "train_worlds" in results
    assert "test_worlds" in results
    assert "models" in results
    for m in ["baseline", "bkt_default", "pfa", "lkt"]:
        assert m in results["models"]
        assert "auc" in results["models"][m]
        assert "generalization_gap" in results["models"][m]


def test_per_world_breakdown(multi_world_dataset):
    breakdown = run_per_world_breakdown(
        multi_world_dataset,
        worlds=["A", "B", "D", "E"],
        models=["bkt_default", "lkt"],
    )

    for w in ["A", "B", "D", "E"]:
        assert w in breakdown
        assert "lkt" in breakdown[w]
        assert "auc" in breakdown[w]["lkt"]


def test_ablation_suite(multi_world_dataset):
    from evaluation.cross_world import (
        run_core_vs_extended_ablation,
        run_single_vs_multiconcept_ablation,
        run_bkt_fixed_vs_fit_ablation,
    )

    # 1. Core vs Extended
    res_ce = run_core_vs_extended_ablation(
        multi_world_dataset,
        models=["bkt_default", "lkt"],
    )
    assert "core_worlds" in res_ce
    assert "extended_worlds" in res_ce
    assert "bkt_default" in res_ce["core_worlds"]
    assert "lkt" in res_ce["extended_worlds"]

    # 2. Single vs Multi-concept
    # Inject multi-concept row into fixture
    multi_world_dataset["has_multi_concept"] = multi_world_dataset["world_id"] == "G"
    res_sm = run_single_vs_multiconcept_ablation(
        multi_world_dataset,
        models=["bkt_default", "pfa", "lkt"],
    )
    assert "single_concept" in res_sm
    assert "multi_concept" in res_sm
    assert "pfa" in res_sm["single_concept"]

    # 3. Fixed vs Fitted BKT
    res_bkt = run_bkt_fixed_vs_fit_ablation(multi_world_dataset)
    assert "bkt_default" in res_bkt
    assert "bkt_fit" in res_bkt
    assert "auc" in res_bkt["bkt_default"]
    assert "auc" in res_bkt["bkt_fit"]

