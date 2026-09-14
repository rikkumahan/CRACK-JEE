from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from evaluation.eval_real_student import (
    prepare_real_student_data,
    evaluate_on_real_student,
    format_real_eval_report,
)


def test_prepare_real_student_data():
    real_path = Path(__file__).resolve().parent.parent / "data" / "real" / "student_gtm_attempts.csv"
    assert real_path.exists(), f"File {real_path} should exist"

    df = prepare_real_student_data(real_path)
    assert len(df) == 74
    assert set(df["status"].unique()) == {"Correct", "Wrong"}
    assert "timestamp" in df.columns
    assert "difficulty" in df.columns
    assert "concept_id" in df.columns
    assert (df["timestamp"].diff().dropna() >= 0).all(), "Timestamps must be monotonically increasing"


def test_evaluate_on_real_student_smoke():
    # Smoke test with tiny synthetic and real dataframes
    rng = np.random.default_rng(42)

    # 10 synthetic interactions
    synth_df = pd.DataFrame({
        "student_id": ["S1", "S1", "S2", "S2", "S3"],
        "concept_id": ["C1", "C2", "C1", "C2", "C1"],
        "timestamp": [100.0, 200.0, 150.0, 250.0, 300.0],
        "difficulty": [0.5, 0.5, 0.5, 0.5, 0.5],
        "correct": [1, 0, 1, 1, 0],
    })

    # 4 real attempts
    real_df = pd.DataFrame({
        "student_id": ["R1", "R1", "R1", "R1"],
        "concept_id": ["C1", "C2", "C1", "C2"],
        "timestamp": [1000.0, 2000.0, 3000.0, 4000.0],
        "difficulty": [0.25, 0.50, 0.50, 0.75],
        "correct": [1, 1, 0, 1],
    })

    res = evaluate_on_real_student(real_df, synth_df)
    assert res["total_attempts"] == 4
    assert "models" in res
    assert "pretrained_lkt" in res["models"]
    assert "bkt_default" in res["models"]
    assert "baseline" in res["models"]
    assert "lkt_difficulty_calibration" in res

    report = format_real_eval_report(res)
    assert "# Real-World Knowledge Tracing Validation Report" in report
