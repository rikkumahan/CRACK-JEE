"""Student-level holdout splitting and sequential ordering without temporal leakage."""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


def student_level_split(
    df: pd.DataFrame,
    train_frac: float = 0.60,
    val_frac: float = 0.20,
    test_frac: float = 0.20,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits dataset wholesale by student_id to prevent student-level leakage.

    Preserves strict chronological order within each student's trajectory.
    """
    assert abs((train_frac + val_frac + test_frac) - 1.0) < 1e-5, "Fractions must sum to 1.0"

    rng = np.random.default_rng(seed)

    # If world_id is present, balance student sampling across worlds
    if "world_id" in df.columns:
        train_students: List[str] = []
        val_students: List[str] = []
        test_students: List[str] = []

        for world_id, w_group in df.groupby("world_id"):
            students = sorted(w_group["student_id"].unique())
            perm = rng.permutation(students)
            n_tot = len(perm)
            n_tr = int(round(train_frac * n_tot))
            n_va = int(round(val_frac * n_tot))

            train_students.extend(perm[:n_tr])
            val_students.extend(perm[n_tr : n_tr + n_va])
            test_students.extend(perm[n_tr + n_va :])
    else:
        students = sorted(df["student_id"].unique())
        perm = rng.permutation(students)
        n_tot = len(perm)
        n_tr = int(round(train_frac * n_tot))
        n_va = int(round(val_frac * n_tot))

        train_students = list(perm[:n_tr])
        val_students = list(perm[n_tr : n_tr + n_va])
        test_students = list(perm[n_tr + n_va :])

    train_set = set(train_students)
    val_set = set(val_students)
    test_set = set(test_students)

    train_df = df[df["student_id"].isin(train_set)].sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    val_df = df[df["student_id"].isin(val_set)].sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    test_df = df[df["student_id"].isin(test_set)].sort_values(["student_id", "timestamp"]).reset_index(drop=True)

    return train_df, val_df, test_df

