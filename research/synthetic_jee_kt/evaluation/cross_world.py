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


def run_core_vs_extended_ablation(
    df: pd.DataFrame,
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ablation A: Core-variable-only vs. core+extended-variable generation (Protocol §5).

    Tests whether the unverified, plausible extended traits (careless slips,
    time pressure panic, confidence calibration) alter model rankings or performance.
    """
    if models is None:
        models = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]

    core_worlds = [w for w in ["A", "B", "C"] if w in df["world_id"].unique()]
    extended_worlds = [w for w in ["D", "E", "F"] if w in df["world_id"].unique()]

    # Fallbacks for partial/test datasets
    if not extended_worlds:
        extended_worlds = [w for w in df["world_id"].unique() if w not in core_worlds]
    if not core_worlds:
        core_worlds = [w for w in df["world_id"].unique() if w not in extended_worlds]

    core_results = {}
    if core_worlds:
        core_df = df[df["world_id"].isin(core_worlds)].reset_index(drop=True)
        tr_c, _, te_c = student_level_split(core_df, train_frac=0.70, val_frac=0.0, test_frac=0.30, seed=42)
        for m in models:
            res, _ = _train_and_eval_model(m, tr_c, te_c)
            core_results[m] = res

    ext_results = {}
    if extended_worlds:
        ext_df = df[df["world_id"].isin(extended_worlds)].reset_index(drop=True)
        tr_e, _, te_e = student_level_split(ext_df, train_frac=0.70, val_frac=0.0, test_frac=0.30, seed=42)
        for m in models:
            res, _ = _train_and_eval_model(m, tr_e, te_e)
            ext_results[m] = res

    return {
        "core_worlds": core_results,
        "extended_worlds": ext_results,
        "core_world_ids": core_worlds,
        "extended_world_ids": extended_worlds,
    }


def run_single_vs_multiconcept_ablation(
    df: pd.DataFrame,
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ablation B: Single-concept vs. multi-concept questions (Protocol §5).

    Tests whether PFA's compensatory-sum advantage over BKT manifests on multi-KC items.
    """
    if models is None:
        models = ["baseline", "bkt_default", "bkt_fit", "pfa", "lkt"]

    train_df, _, test_df = student_level_split(df, train_frac=0.70, val_frac=0.0, test_frac=0.30, seed=42)

    if "has_multi_concept" in test_df.columns:
        is_multi_test = test_df["has_multi_concept"].astype(bool).values
    else:
        is_multi_test = (test_df["world_id"] == "G").values

    single_results = {}
    multi_results = {}

    y_test = test_df["correct"].values.astype(np.int32)
    has_gt = "ground_truth_mastery" in test_df.columns
    gt_mastery = test_df["ground_truth_mastery"].values if has_gt else np.zeros(len(y_test))

    for m in models:
        _, preds = _train_and_eval_model(m, train_df, test_df)

        # Single concept subset
        mask_single = ~is_multi_test
        if np.sum(mask_single) > 0 and len(np.unique(y_test[mask_single])) > 1:
            res_s = compute_prediction_metrics(y_test[mask_single], preds[mask_single])
            if has_gt:
                res_s["ability_r"] = compute_ability_correlation(gt_mastery[mask_single], preds[mask_single])["ability_correlation_r"]
            single_results[m] = res_s
        else:
            single_results[m] = {"auc": 0.50, "log_loss": 0.6931, "rmse": 0.50}

        # Multi concept subset
        mask_multi = is_multi_test
        if np.sum(mask_multi) > 0 and len(np.unique(y_test[mask_multi])) > 1:
            res_m = compute_prediction_metrics(y_test[mask_multi], preds[mask_multi])
            if has_gt:
                res_m["ability_r"] = compute_ability_correlation(gt_mastery[mask_multi], preds[mask_multi])["ability_correlation_r"]
            multi_results[m] = res_m
        else:
            multi_results[m] = {"auc": 0.50, "log_loss": 0.6931, "rmse": 0.50}

    return {
        "single_concept": single_results,
        "multi_concept": multi_results,
    }


def run_bkt_fixed_vs_fit_ablation(
    df: pd.DataFrame,
) -> Dict[str, Any]:
    """Ablation C: Fixed-default BKT vs. EM-fitted BKT (Protocol §5).

    Directly tests whether fitting BKT parameters at population scale improves performance.
    """
    train_df, _, test_df = student_level_split(df, train_frac=0.70, val_frac=0.0, test_frac=0.30, seed=42)

    res_default, _ = _train_and_eval_model("bkt_default", train_df, test_df)
    res_fit, _ = _train_and_eval_model("bkt_fit", train_df, test_df)

    auc_default = res_default.get("auc", 0.50)
    auc_fit = res_fit.get("auc", 0.50)
    delta_auc = round(auc_fit - auc_default, 4)

    return {
        "bkt_default": res_default,
        "bkt_fit": res_fit,
        "delta_auc": delta_auc,
    }


def run_full_phase6_suite(df: pd.DataFrame) -> Dict[str, Any]:
    """Executes the entire Phase 6 Cross-World and Ablation test suite."""
    print("=" * 80)
    print("RUNNING PHASE 6: CROSS-WORLD STRESS TESTS & ABLATION SUITE")
    print("=" * 80)

    # Experiment 1: Train A+B+C -> Test D+E
    print("\n[1/6] Running Experiment 1: Train Worlds A+B+C -> Test Worlds D+E...")
    exp1 = run_cross_world_experiment(
        df,
        train_worlds=["A", "B", "C"],
        test_worlds=["D", "E"],
    )

    # Experiment 2: Train A+D -> Test B+G
    print("[2/6] Running Experiment 2: Train Worlds A+D -> Test Worlds B+G...")
    exp2 = run_cross_world_experiment(
        df,
        train_worlds=["A", "D"],
        test_worlds=["B", "G"],
    )

    # Experiment 3: Per-World Breakdown
    active_worlds = [w for w in ["A", "B", "C", "D", "E", "F", "G"] if w in df["world_id"].unique()]
    print(f"[3/6] Running Experiment 3: Per-World Breakdown across {active_worlds}...")
    breakdown = run_per_world_breakdown(df, worlds=active_worlds)

    # Ablation 1: Core vs Extended
    print("\n[4/6] Running Ablation 1: Core-Variable-Only vs. Core+Extended-Variable Generation...")
    ablation_core_ext = run_core_vs_extended_ablation(df)

    # Ablation 2: Single vs Multi-concept
    print("[5/6] Running Ablation 2: Single-Concept vs. Multi-Concept Items...")
    ablation_single_multi = run_single_vs_multiconcept_ablation(df)

    # Ablation 3: Fixed vs Fitted BKT
    print("[6/6] Running Ablation 3: Fixed-Default BKT vs. EM-Fitted BKT...")
    ablation_bkt = run_bkt_fixed_vs_fit_ablation(df)

    results = {
        "experiment_1_abc_to_de": exp1,
        "experiment_2_ad_to_bg": exp2,
        "per_world_breakdown": breakdown,
        "ablation_core_vs_extended": ablation_core_ext,
        "ablation_single_vs_multiconcept": ablation_single_multi,
        "ablation_bkt_fixed_vs_fit": ablation_bkt,
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

    # Section 4: Ablations
    lines.extend([
        "",
        "## 4. Ablation Suite (Protocol §5)",
        "",
        "### 4.1 Ablation A: Core-Variable-Only vs. Core+Extended-Variable Generation",
        "",
        "Tests whether unverified extended traits (careless slips, time panic, confidence bias) alter model rankings.",
        "",
        "| Model | Core Worlds AUC | Extended Worlds AUC | Delta AUC |",
        "|---|---|---|---|",
    ])
    core_res = results.get("ablation_core_vs_extended", {}).get("core_worlds", {})
    ext_res = results.get("ablation_core_vs_extended", {}).get("extended_worlds", {})
    all_models = list(core_res.keys()) if core_res else list(ext_res.keys())
    for m in all_models:
        c_auc = core_res.get(m, {}).get("auc", 0.5)
        e_auc = ext_res.get(m, {}).get("auc", 0.5)
        d_auc = e_auc - c_auc
        lines.append(f"| **{m}** | {c_auc:.4f} | {e_auc:.4f} | {d_auc:+.4f} |")

    lines.extend([
        "",
        "### 4.2 Ablation B: Single-Concept vs. Multi-Concept Items",
        "",
        "Tests whether PFA's compensatory-sum advantage over BKT appears on multi-concept questions.",
        "",
        "| Model | Single-Concept AUC | Multi-Concept AUC | Delta AUC |",
        "|---|---|---|---|",
    ])
    single_res = results.get("ablation_single_vs_multiconcept", {}).get("single_concept", {})
    multi_res = results.get("ablation_single_vs_multiconcept", {}).get("multi_concept", {})
    sm_models = list(single_res.keys()) if single_res else list(multi_res.keys())
    for m in sm_models:
        s_auc = single_res.get(m, {}).get("auc", 0.5)
        m_auc = multi_res.get(m, {}).get("auc", 0.5)
        d_auc = m_auc - s_auc
        lines.append(f"| **{m}** | {s_auc:.4f} | {m_auc:.4f} | {d_auc:+.4f} |")

    lines.extend([
        "",
        "### 4.3 Ablation C: Fixed-Default BKT vs. EM-Fitted BKT",
        "",
        "Tests whether population-level EM parameter fitting improves BKT.",
        "",
        "| Configuration | AUC | Log Loss | RMSE | State Recovery MAE | State Recovery r |",
        "|---|---|---|---|---|---|",
    ])
    bkt_ab = results.get("ablation_bkt_fixed_vs_fit", {})
    d_m = bkt_ab.get("bkt_default", {})
    f_m = bkt_ab.get("bkt_fit", {})
    lines.append(f"| **BKT Default (Fixed)** | {d_m.get('auc', 0.5):.4f} | {d_m.get('log_loss', 0.0):.4f} | {d_m.get('rmse', 0.0):.4f} | {d_m.get('state_recovery_mae', 0.0):.4f} | {d_m.get('state_recovery_r', 0.0):.4f} |")
    lines.append(f"| **BKT Fit (EM)** | {f_m.get('auc', 0.5):.4f} | {f_m.get('log_loss', 0.0):.4f} | {f_m.get('rmse', 0.0):.4f} | {f_m.get('state_recovery_mae', 0.0):.4f} | {f_m.get('state_recovery_r', 0.0):.4f} |")

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
