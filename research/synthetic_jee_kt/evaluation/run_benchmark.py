"""Benchmark execution harness comparing Baseline, BKT, PFA, and LKT on synthetic JEE data."""

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
from evaluation.metrics import (
    compute_ability_correlation,
    compute_prediction_metrics,
    compute_state_recovery_metrics,
)
from evaluation.splits import student_level_split
from models.baseline import RecentAccuracyBaseline
from models.bkt import BKTModel, BKTParameters
from models.lkt import LKTModel
from models.pfa import PFAModel


def evaluate_bkt_sequential(model: BKTModel, test_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    df_sorted = test_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    preds = np.zeros(len(df_sorted), dtype=np.float64)
    recovered_states = np.zeros(len(df_sorted), dtype=np.float64)

    # Local state tracker for test evaluation
    for row_idx, row in df_sorted.iterrows():
        sid = row["student_id"]
        cid = row["concept_id"]
        outcome = int(row["correct"])

        # Predict
        p = model.predict(sid, cid)
        m = model.get_mastery(sid, cid)
        preds[row_idx] = p
        recovered_states[row_idx] = m

        # Update
        model.update(sid, cid, outcome)

    return preds, recovered_states


def evaluate_baseline_sequential(model: RecentAccuracyBaseline, test_df: pd.DataFrame) -> np.ndarray:
    df_sorted = test_df.sort_values(["student_id", "timestamp"]).reset_index(drop=True)
    preds = np.zeros(len(df_sorted), dtype=np.float64)

    for row_idx, row in df_sorted.iterrows():
        sid = row["student_id"]
        cid = row["concept_id"]
        outcome = int(row["correct"])

        preds[row_idx] = model.predict(sid, cid)
        model.update(sid, cid, outcome)

    return preds


def run_single_seed_benchmark(
    df: pd.DataFrame,
    models_to_run: Optional[List[str]] = None,
    seed: int = 42,
    eval_efficiency: bool = False,
) -> Dict[str, Any]:
    """Runs train/test evaluation for specified models on a single train/val/test split."""
    if models_to_run is None:
        models_to_run = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]

    train_df, val_df, test_df = student_level_split(df, train_frac=0.60, val_frac=0.20, test_frac=0.20, seed=seed)
    y_test = test_df["correct"].values.astype(np.int32)
    has_gt = "ground_truth_mastery" in test_df.columns
    gt_mastery = test_df["ground_truth_mastery"].values if has_gt else np.zeros(len(y_test))

    results: Dict[str, Any] = {}

    # 1. Baseline
    if "baseline" in models_to_run:
        baseline = RecentAccuracyBaseline(window_size=5).fit(train_df)
        preds = evaluate_baseline_sequential(baseline, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        results["baseline"] = res

    # 2. BKT Literature Default
    if "bkt_default" in models_to_run:
        bkt_def = BKTModel(default_params=BKTParameters(p_l0=0.20, p_t=0.10, p_s=0.10, p_g=0.25))
        preds, states = evaluate_bkt_sequential(bkt_def, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            rec = compute_state_recovery_metrics(gt_mastery, states)
            res["state_recovery_mae"] = rec["mae"]
            res["state_recovery_r"] = rec["pearson_r"]
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        results["bkt_default"] = res

    # 3. BKT EM-fit on synthetic population
    if "bkt_fit" in models_to_run:
        bkt_fit = BKTModel().fit(train_df)
        preds, states = evaluate_bkt_sequential(bkt_fit, test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            rec = compute_state_recovery_metrics(gt_mastery, states)
            res["state_recovery_mae"] = rec["mae"]
            res["state_recovery_r"] = rec["pearson_r"]
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        results["bkt_fit"] = res

    # 4. PFA
    if "pfa" in models_to_run:
        pfa = PFAModel().fit(train_df)
        preds = pfa.evaluate_sequential(test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        results["pfa"] = res

    # 5. LKT
    if "lkt" in models_to_run:
        lkt = LKTModel().fit(train_df)
        preds = lkt.evaluate_sequential(test_df)
        res = compute_prediction_metrics(y_test, preds)
        if has_gt:
            res["ability_r"] = compute_ability_correlation(gt_mastery, preds)["ability_correlation_r"]
        results["lkt"] = res

    # Data efficiency evaluation at truncated student interaction lengths
    if eval_efficiency:
        eff_lengths = [10, 25, 50, 100, 200]
        results["efficiency"] = {}
        for l in eff_lengths:
            # Truncate each student in test_df to first l interactions
            sub_test = test_df.groupby("student_id").head(l).reset_index(drop=True)
            if len(sub_test) > 0:
                y_sub = sub_test["correct"].values.astype(np.int32)
                sub_res = {}
                if "baseline" in models_to_run:
                    base = RecentAccuracyBaseline().fit(train_df)
                    sub_res["baseline"] = compute_prediction_metrics(y_sub, evaluate_baseline_sequential(base, sub_test))["auc"]
                if "bkt_default" in models_to_run:
                    bkt = BKTModel()
                    p, _ = evaluate_bkt_sequential(bkt, sub_test)
                    sub_res["bkt_default"] = compute_prediction_metrics(y_sub, p)["auc"]
                if "pfa" in models_to_run:
                    pfa = PFAModel().fit(train_df)
                    sub_res["pfa"] = compute_prediction_metrics(y_sub, pfa.evaluate_sequential(sub_test))["auc"]
                if "lkt" in models_to_run:
                    lkt = LKTModel().fit(train_df)
                    sub_res["lkt"] = compute_prediction_metrics(y_sub, lkt.evaluate_sequential(sub_test))["auc"]
                results["efficiency"][str(l)] = sub_res

    return results


def run_multi_seed_benchmark(
    df: pd.DataFrame,
    seeds: List[int],
    models_to_run: Optional[List[str]] = None,
    eval_efficiency: bool = True,
) -> Dict[str, Any]:
    """Runs benchmark across multiple random seeds and computes mean +- std."""
    if models_to_run is None:
        models_to_run = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]

    all_seed_results: List[Dict[str, Any]] = []

    for seed in seeds:
        print(f"  Running benchmark for seed={seed}...")
        seed_res = run_single_seed_benchmark(
            df, models_to_run=models_to_run, seed=seed, eval_efficiency=(eval_efficiency and seed == seeds[0])
        )
        all_seed_results.append(seed_res)

    # Aggregate across seeds
    aggregated: Dict[str, Dict[str, Any]] = {}
    for model_name in models_to_run:
        aggregated[model_name] = {}
        metric_keys = all_seed_results[0][model_name].keys()
        for k in metric_keys:
            vals = [res[model_name][k] for res in all_seed_results if k in res[model_name]]
            aggregated[model_name][k] = {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
                "min": round(float(np.min(vals)), 4),
                "max": round(float(np.max(vals)), 4),
            }

    summary = {
        "seeds": seeds,
        "models": models_to_run,
        "total_interactions": len(df),
        "total_students": int(df["student_id"].nunique()),
        "results": aggregated,
        "efficiency": all_seed_results[0].get("efficiency", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return summary


def format_benchmark_table(summary: Dict[str, Any]) -> str:
    """Formats benchmark summary into clean markdown table."""
    lines = [
        "| Model | AUC | Log Loss | RMSE | Brier Score | BKT State Recovery MAE | BKT State Recovery r |",
        "|---|---|---|---|---|---|---|",
    ]
    res = summary["results"]
    for m in summary["models"]:
        m_data = res.get(m, {})
        auc_str = f"{m_data.get('auc', {}).get('mean', 0):.4f} ± {m_data.get('auc', {}).get('std', 0):.4f}"
        ll_str = f"{m_data.get('log_loss', {}).get('mean', 0):.4f} ± {m_data.get('log_loss', {}).get('std', 0):.4f}"
        rmse_str = f"{m_data.get('rmse', {}).get('mean', 0):.4f} ± {m_data.get('rmse', {}).get('std', 0):.4f}"
        brier_str = f"{m_data.get('brier', {}).get('mean', 0):.4f} ± {m_data.get('brier', {}).get('std', 0):.4f}"

        if "state_recovery_mae" in m_data:
            mae_str = f"{m_data['state_recovery_mae']['mean']:.4f} ± {m_data['state_recovery_mae']['std']:.4f}"
            r_str = f"{m_data['state_recovery_r']['mean']:.4f} ± {m_data['state_recovery_r']['std']:.4f}"
        else:
            mae_str = "n/a (predictive only)"
            r_str = "n/a"

        lines.append(f"| **{m}** | {auc_str} | {ll_str} | {rmse_str} | {brier_str} | {mae_str} | {r_str} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run Knowledge Tracing benchmark on synthetic JEE data.")
    parser.add_argument("--data-path", type=str, default=None, help="Path to synthetic_interactions.csv.")
    parser.add_argument("--seeds", type=str, default="1,2,3,4,5", help="Comma-separated random seeds.")
    parser.add_argument("--models", type=str, default="baseline,bkt_default,bkt_fit,pfa,lkt", help="Models to benchmark.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for benchmark report.")
    args = parser.parse_args()

    default_data = Path(__file__).resolve().parent.parent / "data" / "generated" / "synthetic_interactions.csv"
    data_path = Path(args.data_path) if args.data_path else default_data
    if not data_path.exists():
        print(f"Data file not found at {data_path}. Please run generate_dataset.py first.")
        sys.exit(1)

    print(f"Loading synthetic interactions from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} interactions from {df['student_id'].nunique()} students across {df['world_id'].nunique()} worlds.")

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    models_list = [m.strip() for m in args.models.split(",") if m.strip()]

    print(f"Running benchmark across {len(seeds)} seeds: {seeds}...")
    summary = run_multi_seed_benchmark(df, seeds=seeds, models_to_run=models_list, eval_efficiency=True)

    table_md = format_benchmark_table(summary)
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS (Mean ± Std across 5 Seeds):")
    print("=" * 80)
    print(table_md)
    print("=" * 80)

    out_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "data" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "benchmark_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    report_path = out_dir / "benchmark_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Synthetic JEE Knowledge Tracing Benchmark Results\n\n")
        f.write(f"Generated at: {summary['timestamp']}\n")
        f.write(f"Total students: {summary['total_students']}, Total interactions: {summary['total_interactions']}\n")
        f.write(f"Seeds evaluated: {summary['seeds']}\n\n")
        f.write("## Performance Metrics\n\n")
        f.write(table_md)
        f.write("\n\n## Data Efficiency Curves (AUC vs History Length)\n\n")
        f.write("```json\n" + json.dumps(summary.get("efficiency", {}), indent=2) + "\n```\n")

    print(f"\nSaved benchmark results to {summary_path} and {report_path}")


if __name__ == "__main__":
    main()
