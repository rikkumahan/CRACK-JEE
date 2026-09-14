"""Cross-World Evaluation Harness and Ablation Suite (Phase 6)."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Add repo to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from evaluation.metrics import (
    compute_ability_correlation,
    compute_prediction_metrics,
    compute_state_recovery_metrics,
)
from evaluation.run_benchmark import evaluate_baseline_sequential, evaluate_bkt_sequential
from evaluation.splits import student_level_split
from models.baseline import RecentAccuracyBaseline
from models.bkt import BKTModel, BKTParameters
from models.lkt import LKTModel
from models.pfa import PFAModel


def cross_world_split(
    df: pd.DataFrame,
    train_worlds: List[str],
    test_worlds: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Partitions dataset into disjoint training and testing worlds."""
    train_df = df[df["world_id"].isin(train_worlds)].sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    test_df = df[df["world_id"].isin(test_worlds)].sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    return train_df, test_df


def _train_and_eval_model(
    model_name: str, train_df: pd.DataFrame, test_df: pd.DataFrame
) -> Tuple[Dict[str, float], np.ndarray]:
    y_test = test_df["correct"].values.astype(np.int32)
    has_gt = "ground_truth_mastery" in test_df.columns
    gt_mastery = test_df["ground_truth_mastery"].values if has_gt else np.zeros(len(y_test))

    if model_name == "baseline":
        m = RecentAccuracyBaseline(window_size=5).fit(train_df)
        preds = evaluate_baseline_sequential(m, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        return res, preds

    elif model_name == "bkt_default":
        m = BKTModel(default_params=BKTParameters(p_l0=0.20, p_t=0.10, p_s=0.10, p_g=0.25))
        preds, states = evaluate_bkt_sequential(m, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            rec = compute_state_recovery_metrics(gt_mastery, states)
            res["state_recovery_mae"] = rec["mae"]
            res["state_recovery_r"] = rec["pearson_r"]
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        return res, preds

    elif model_name == "bkt_fit":
        m = BKTModel().fit(train_df)
        preds, states = evaluate_bkt_sequential(m, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            rec = compute_state_recovery_metrics(gt_mastery, states)
            res["state_recovery_mae"] = rec["mae"]
            res["state_recovery_r"] = rec["pearson_r"]
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        return res, preds

    elif model_name == "pfa":
        m = PFAModel().fit(train_df)
        preds = m.evaluate_sequential(test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        return res, preds

    elif model_name == "lkt":
        m = LKTModel().fit(train_df)
        preds = m.evaluate_sequential(test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        return res, preds

    raise ValueError(f"Unknown model: {model_name}")


def run_cross_world_experiment(
    df: pd.DataFrame,
    train_worlds: List[str],
    test_worlds: List[str],
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluates models trained on train_worlds and tested on unseen test_worlds."""
    if models is None:
        models = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]

    train_df, test_df = cross_world_split(df, train_worlds, test_worlds)

    # Within-world reference: split train_df 80/20 by student
    within_tr, within_te, _ = student_level_split(train_df, train_frac=0.80, val_frac=0.20, test_frac=0.0, seed=42)

    model_results = {}
    for m in models:
        # Within-world baseline AUC
        within_metrics, _ = _train_and_eval_model(m, within_tr, within_te)
        within_auc = within_metrics.get("auc", 0.50)

        # Cross-world test on unseen worlds
        cross_metrics, _ = _train_and_eval_model(m, train_df, test_df)
        cross_auc = cross_metrics.get("auc", 0.50)

        gap = round(within_auc - cross_auc, 4)
        cross_metrics["within_world_auc"] = round(within_auc, 4)
        cross_metrics["cross_world_auc"] = round(cross_auc, 4)
        cross_metrics["generalization_gap"] = gap

        model_results[m] = cross_metrics

    return {
        "train_worlds": train_worlds,
        "test_worlds": test_worlds,
        "train_students": int(train_df["student_id"].nunique()),
        "test_students": int(test_df["student_id"].nunique()),
        "models": model_results,
    }


def run_per_world_breakdown(
    df: pd.DataFrame,
    worlds: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Trains on 70% of students across all worlds, then breaks down test AUC by world."""
    if models is None:
        models = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]
    if worlds is None:
        worlds = sorted(list(df["world_id"].unique()))

    train_df, _, test_df = student_level_split(df, train_frac=0.70, val_frac=0.0, test_frac=0.30, seed=42)

    breakdown: Dict[str, Dict[str, Any]] = {}
    for w in worlds:
        w_test = test_df[test_df["world_id"] == w].reset_index(drop=True)
        if len(w_test) == 0:
            continue

        breakdown[w] = {}
        for m in models:
            res, _ = _train_and_eval_model(m, train_df, w_test)
            breakdown[w][m] = res

    return breakdown


def run_full_phase6_suite(df: pd.DataFrame) -> Dict[str, Any]:
    """Executes the entire Phase 6 Cross-World and Ablation test suite."""
    print("=" * 80)
    print("RUNNING PHASE 6: CROSS-WORLD STRESS TESTS & ABLATION SUITE")
    print("=" * 80)

    # Experiment 1: Train A+B+C -> Test D+E
    print("\n[1/3] Running Experiment 1: Train Worlds A+B+C -> Test Worlds D+E...")
    exp1 = run_cross_world_experiment(
        df,
        train_worlds=["A", "B", "C"],
        test_worlds=["D", "E"],
    )

    # Experiment 2: Train A+D -> Test B+G
    print("[2/3] Running Experiment 2: Train Worlds A+D -> Test Worlds B+G...")
    exp2 = run_cross_world_experiment(
        df,
        train_worlds=["A", "D"],
        test_worlds=["B", "G"],
    )

    # Experiment 3: Per-World Breakdown
    active_worlds = [w for w in ["A", "B", "C", "D", "E", "F", "G"] if w in df["world_id"].unique()]
    print(f"[3/3] Running Experiment 3: Per-World Breakdown across {active_worlds}...")
    breakdown = run_per_world_breakdown(df, worlds=active_worlds)

    results = {
        "experiment_1_abc_to_de": exp1,
        "experiment_2_ad_to_bg": exp2,
        "per_world_breakdown": breakdown,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return results


def format_cross_world_report(results: Dict[str, Any]) -> str:
    """Generates markdown report for Phase 6 experiments."""
    lines = [
        "# Phase 6: Cross-World Generalization & Robustness Report",
        "",
        "Evaluates whether models generalize beyond their training distribution or overfit to simulator assumptions.",
        "",
        "## 1. Experiment 1: Train on Standard Worlds (A+B+C) -> Test on Stress Worlds (D+E)",
        "",
        "- **Train Worlds:** A (BKT-like), B (Forgetting), C (Prerequisites)",
        "- **Test Worlds:** D (High Careless Slips), E (Time-Pressure Panic)",
        "",
        "| Model | Within-World AUC | Cross-World AUC | Generalization Gap (Delta AUC) | Log Loss | RMSE |",
        "|---|---|---|---|---|---|",
    ]

    exp1_models = results["experiment_1_abc_to_de"]["models"]
    for m, d in exp1_models.items():
        within = d["within_world_auc"]
        cross = d["cross_world_auc"]
        gap = d["generalization_gap"]
        ll = d["log_loss"]
        rmse = d["rmse"]
        lines.append(f"| **{m}** | {within:.4f} | {cross:.4f} | {gap:+.4f} | {ll:.4f} | {rmse:.4f} |")

    lines.extend([
        "",
        "## 2. Experiment 2: Train on A+D -> Test on Severe Forgetting & Multi-Concept (B+G)",
        "",
        "- **Train Worlds:** A (Standard), D (Careless)",
        "- **Test Worlds:** B (Steep Forgetting), G (Multi-Concept Interference)",
        "",
        "| Model | Within-World AUC | Cross-World AUC | Generalization Gap (Delta AUC) | Log Loss | RMSE |",
        "|---|---|---|---|---|---|",
    ])

    exp2_models = results["experiment_2_ad_to_bg"]["models"]
    for m, d in exp2_models.items():
        within = d["within_world_auc"]
        cross = d["cross_world_auc"]
        gap = d["generalization_gap"]
        ll = d["log_loss"]
        rmse = d["rmse"]
        lines.append(f"| **{m}** | {within:.4f} | {cross:.4f} | {gap:+.4f} | {ll:.4f} | {rmse:.4f} |")

    lines.extend([
        "",
        "## 3. Per-World Breakdown (Test AUC by Individual World)",
        "",
        "| World | Description | Baseline | BKT Default | BKT Fit | PFA | LKT |",
        "|---|---|---|---|---|---|---|",
    ])

    world_names = {
        "A": "BKT-like (Standard)",
        "B": "Strong Forgetting",
        "C": "Prerequisite-Gated",
        "D": "High Careless Slips",
        "E": "Time-Pressure Panic",
        "F": "Confidence Bias",
        "G": "Multi-Concept Interference",
    }

    pwb = results["per_world_breakdown"]
    for w, models_data in pwb.items():
        desc = world_names.get(w, w)
        base_auc = models_data.get("baseline", {}).get("auc", 0.5)
        bktd_auc = models_data.get("bkt_default", {}).get("auc", 0.5)
        bktf_auc = models_data.get("bkt_fit", {}).get("auc", 0.5)
        pfa_auc = models_data.get("pfa", {}).get("auc", 0.5)
        lkt_auc = models_data.get("lkt", {}).get("auc", 0.5)
        lines.append(f"| **World {w}** | {desc} | {base_auc:.4f} | {bktd_auc:.4f} | {bktf_auc:.4f} | {pfa_auc:.4f} | **{lkt_auc:.4f}** |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run Phase 6 Cross-World benchmark suite.")
    parser.add_argument("--data-path", type=str, default=None, help="Path to synthetic_interactions.csv.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for reports.")
    args = parser.parse_args()

    default_data = Path(__file__).resolve().parent.parent / "data" / "generated" / "synthetic_interactions.csv"
    data_path = Path(args.data_path) if args.data_path else default_data
    if not data_path.exists():
        print(f"Data file not found at {data_path}.")
        sys.exit(1)

    df = pd.read_csv(data_path)
    results = run_full_phase6_suite(df)

    report_md = format_cross_world_report(results)
    print("\n" + report_md)

    out_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "data" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "cross_world_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    report_path = out_dir / "cross_world_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md + "\n")

    print(f"\nSaved cross-world results to {json_path} and {report_path}")


if __name__ == "__main__":
    main()
