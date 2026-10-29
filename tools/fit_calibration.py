import argparse
import csv
import json
import os
from typing import Any

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve
from sv_engine.calibration import apply_platt, fit_platt


def compute_ece(p: np.ndarray, y: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error across n_bins equal-width confidence bins."""
    p = np.asarray(p, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        bin_mask = (p >= bin_boundaries[i]) & (p < bin_boundaries[i + 1])
        if bin_mask.sum() > 0:
            bin_acc = float(y[bin_mask].mean())
            bin_conf = float(p[bin_mask].mean())
            ece += (bin_mask.sum() / len(y)) * abs(bin_acc - bin_conf)
    return float(ece)


def compute_tpr_at_fpr(p: np.ndarray, y: np.ndarray, target_fpr: float) -> float:
    """Calculate True Positive Rate at a target False Positive Rate (e.g. 0.01 or 0.05)."""
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.interp(target_fpr, fpr, tpr))


def compute_youden_tau(p: np.ndarray, y: np.ndarray) -> float:
    """Find operating cutoff tau maximizing Youden's J statistic = TPR - FPR."""
    fpr, tpr, thr = roc_curve(y, p)
    idx = int(np.argmax(tpr - fpr))
    return float(thr[idx])


def load_validation_scores(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load logits/scores and binary labels from CSV (expects columns 'u' or 'score' and 'label' or 'y')."""
    scores = []
    labels = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            score_val = row.get("u") or row.get("score") or row.get("logit") or row.get("p_raw")
            label_val = row.get("label") or row.get("y") or row.get("target")
            if score_val is not None and label_val is not None:
                scores.append(float(score_val))
                labels.append(int(float(label_val)))
    if not scores:
        raise ValueError(f"No valid score/label rows found in {csv_path}")
    return np.array(scores, dtype=np.float64), np.array(labels, dtype=np.int32)


def fit_calibration_and_metrics(
    u_scores: np.ndarray, labels: np.ndarray, variant_id: str = "smsdt-st-b"
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fit class-balanced Platt scaling and calculate standardized operating points."""
    # 1. Fit Platt parameters (a, b)
    a, b = fit_platt(u_scores, labels)

    # 2. Calibrate raw logits
    p_cal = np.array([apply_platt(u, a, b) for u in u_scores], dtype=np.float64)

    # 3. Calculate metrics
    auc = float(roc_auc_score(labels, p_cal))
    tau_star = compute_youden_tau(p_cal, labels)
    tpr_1pct = compute_tpr_at_fpr(p_cal, labels, 0.01)
    tpr_5pct = compute_tpr_at_fpr(p_cal, labels, 0.05)
    ece = compute_ece(p_cal, labels, n_bins=15)

    calibration_dict = {
        "model_id": variant_id,
        "method": "platt",
        "parameters": {"a": round(float(a), 4), "b": round(float(b), 4)},
        "youden_tau_star": round(float(tau_star), 4),
        "calibration_sample_size": int(len(labels)),
    }

    operating_points_dict = {
        "model_id": variant_id,
        "validation_auc": round(float(auc), 4),
        "youden_optimal": {
            "threshold": round(float(tau_star), 4),
            "tpr": round(compute_tpr_at_fpr(p_cal, labels, compute_youden_tau(p_cal, labels)), 4),
        },
        "fixed_fpr_points": [
            {"target_fpr": 0.01, "tpr": round(float(tpr_1pct), 4)},
            {"target_fpr": 0.05, "tpr": round(float(tpr_5pct), 4)},
        ],
        "expected_calibration_error": round(float(ece), 4),
        "n_bins": 15,
    }

    return calibration_dict, operating_points_dict


def main():
    parser = argparse.ArgumentParser(
        description="Fit Platt calibration and compute operating points"
    )
    parser.add_argument(
        "--scores", type=str, required=True, help="Path to validation scores CSV (u, label)"
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=".",
        help="Directory to save calibration.json and operating_points.json",
    )
    parser.add_argument("--variant", type=str, default="smsdt-st-b", help="Model variant ID")
    args = parser.parse_args()

    u_scores, labels = load_validation_scores(args.scores)
    calib, op_points = fit_calibration_and_metrics(u_scores, labels, variant_id=args.variant)

    os.makedirs(args.out_dir, exist_ok=True)
    calib_path = os.path.join(args.out_dir, "calibration.json")
    op_path = os.path.join(args.out_dir, "operating_points.json")

    with open(calib_path, "w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2)
    with open(op_path, "w", encoding="utf-8") as f:
        json.dump(op_points, f, indent=2)

    print(f"Calibration saved to {calib_path}")
    print(f"Operating points saved to {op_path}")


if __name__ == "__main__":
    main()
