"""Evaluation metrics for next-response prediction and latent-state recovery."""

from typing import Any, Dict, Union
import numpy as np
from scipy.stats import pearsonr
from sklearn.metrics import log_loss, roc_auc_score


def compute_prediction_metrics(
    y_true: Union[np.ndarray, list], y_pred: Union[np.ndarray, list]
) -> Dict[str, float]:
    """Computes AUC, Log Loss, RMSE, Brier score, and accuracy for next-response prediction."""
    y_t = np.asarray(y_true, dtype=np.int32)
    y_p = np.asarray(y_pred, dtype=np.float64)
    y_p_clipped = np.clip(y_p, 1e-6, 1.0 - 1e-6)

    # Check for single-class degenerate case
    if len(np.unique(y_t)) < 2:
        auc = 0.50
    else:
        try:
            auc = float(roc_auc_score(y_t, y_p_clipped))
        except Exception:
            auc = 0.50

    try:
        ll = float(log_loss(y_t, y_p_clipped))
    except Exception:
        ll = float(-np.mean(y_t * np.log(y_p_clipped) + (1 - y_t) * np.log(1 - y_p_clipped)))

    brier = float(np.mean((y_p - y_t) ** 2))
    rmse = float(np.sqrt(brier))
    acc = float(np.mean((y_p >= 0.5) == y_t))

    return {
        "auc": round(auc, 4),
        "log_loss": round(ll, 4),
        "rmse": round(rmse, 4),
        "brier": round(brier, 4),
        "accuracy": round(acc, 4),
    }


def compute_state_recovery_metrics(
    ground_truth_mastery: Union[np.ndarray, list],
    estimated_mastery: Union[np.ndarray, list],
) -> Dict[str, float]:
    """Computes latent-state recovery metrics (Pearson r and MAE). Valid for BKT only."""
    gt = np.asarray(ground_truth_mastery, dtype=np.float64)
    est = np.asarray(estimated_mastery, dtype=np.float64)

    mae = float(np.mean(np.abs(gt - est)))

    if len(gt) < 2 or np.std(gt) < 1e-8 or np.std(est) < 1e-8:
        r = 0.0
    else:
        r_val, _ = pearsonr(gt, est)
        r = float(r_val) if not np.isnan(r_val) else 0.0

    return {
        "pearson_r": round(r, 4),
        "mae": round(mae, 4),
    }


def compute_ability_correlation(
    true_ability: Union[np.ndarray, list], predicted_prob: Union[np.ndarray, list]
) -> Dict[str, float]:
    """Computes predicted-probability vs true-ability correlation.

    Used for PFA/LKT/DKT as clarified by validation report Q12/Q13.
    """
    ta = np.asarray(true_ability, dtype=np.float64)
    pp = np.asarray(predicted_prob, dtype=np.float64)

    if len(ta) < 2 or np.std(ta) < 1e-8 or np.std(pp) < 1e-8:
        r = 0.0
    else:
        r_val, _ = pearsonr(ta, pp)
        r = float(r_val) if not np.isnan(r_val) else 0.0

    return {
        "ability_correlation_r": round(r, 4),
    }
