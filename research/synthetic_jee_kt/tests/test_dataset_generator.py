import json
import pytest
import pandas as pd
from pathlib import Path
from simulator.generate_dataset import generate_dataset, GenerationConfig


@pytest.fixture
def temp_output_dir(tmp_path):
    out_dir = tmp_path / "dataset"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def test_generate_dataset_structure_and_schema(temp_output_dir):
    config = GenerationConfig(
        seed=123,
        worlds=["A", "B"],
        students_per_world=3,
        interactions_per_student=15,
        output_dir=temp_output_dir,
    )
    generate_dataset(config)

    interactions_file = temp_output_dir / "synthetic_interactions.csv"
    ground_truth_file = temp_output_dir / "student_ground_truth.csv"
    manifest_file = temp_output_dir / "generation_manifest.json"

    assert interactions_file.exists()
    assert ground_truth_file.exists()
    assert manifest_file.exists()

    df_int = pd.read_csv(interactions_file)
    assert len(df_int) == 2 * 3 * 15  # 90 interactions
    expected_cols = [
        "student_id", "question_id", "exam", "year", "shift",
        "subject", "chapter", "concept_id", "timestamp", "correct",
        "time_seconds", "confidence", "error_type", "answer_changed",
        "source", "world_id", "archetype", "ground_truth_mastery"
    ]
    for col in expected_cols:
        assert col in df_int.columns

    # Verify per-student monotonic timestamps
    for sid, group in df_int.groupby("student_id"):
        ts = group["timestamp"].tolist()
        assert ts == sorted(ts)
        assert len(ts) == 15

    # Verify values
    assert set(df_int["correct"].unique()).issubset({0, 1})
    assert (df_int["time_seconds"] > 0).all()
    assert ((df_int["confidence"] >= 0) & (df_int["confidence"] <= 1)).all()

    # Verify ground truth
    df_gt = pd.read_csv(ground_truth_file)
    assert len(df_gt) > 0
    gt_cols = [
        "student_id", "archetype", "world_id", "concept_id",
        "initial_mastery", "final_mastery", "learning_rate",
        "forgetting_rate", "slip_rate", "guess_rate"
    ]
    for col in gt_cols:
        assert col in df_gt.columns


def test_dataset_exact_reproducibility(tmp_path):
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    dir3 = tmp_path / "run3"

    cfg1 = GenerationConfig(seed=42, worlds=["A", "D"], students_per_world=2, interactions_per_student=10, output_dir=dir1)
    cfg2 = GenerationConfig(seed=42, worlds=["A", "D"], students_per_world=2, interactions_per_student=10, output_dir=dir2)
    cfg3 = GenerationConfig(seed=43, worlds=["A", "D"], students_per_world=2, interactions_per_student=10, output_dir=dir3)

    generate_dataset(cfg1)
    generate_dataset(cfg2)
    generate_dataset(cfg3)

    csv1 = (dir1 / "synthetic_interactions.csv").read_text(encoding="utf-8")
    csv2 = (dir2 / "synthetic_interactions.csv").read_text(encoding="utf-8")
    csv3 = (dir3 / "synthetic_interactions.csv").read_text(encoding="utf-8")

    # Exact bit-for-bit equality for same seed
    assert csv1 == csv2
    # Distinct for different seed
    assert csv1 != csv3
