from datetime import UTC, datetime
from typing import Any, Literal

import numpy as np

from sv_monitor.schemas import (
    CalibrationReport,
    FeatureDriftSummary,
    PSIBinResult,
    PSIReport,
    ReliabilityBinPoint,
)

__all__ = [
    "compute_quantile_bins",
    "compute_psi",
    "compute_categorical_psi",
    "evaluate_input_drift",
    "compute_ece_ipw",
]


def compute_quantile_bins(reference_values: np.ndarray, num_bins: int = 10) -> np.ndarray:
    """Compute quantile bin edges from reference distribution baseline."""
    ref = np.asarray(reference_values, dtype=np.float64)
    if ref.size == 0:
        raise ValueError("Reference values array cannot be empty")

    percentiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(ref, percentiles)

    # If reference distribution has duplicate quantiles, perturb slightly to preserve monotonicity
    for i in range(1, len(bin_edges)):
        if bin_edges[i] <= bin_edges[i - 1]:
            bin_edges[i] = bin_edges[i - 1] + 1e-6

    # Extend boundary bins to infinity so out-of-range actuals are captured
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf
    return bin_edges


def compute_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    feature_name: str = "score",
    num_bins: int = 10,
    eps: float = 1e-4,
) -> PSIReport:
    """Calculate Population Stability Index (PSI) between baseline and production distributions.

    PSI Formula: sum((P_i - Q_i) * ln(P_i / Q_i))
    Status:
        PSI < 0.10: 'ok' (stable distribution)
        0.10 <= PSI <= 0.25: 'watch' (moderate drift)
        PSI > 0.25: 'alert' (significant drift)
    """
    exp = np.asarray(expected, dtype=np.float64)
    act = np.asarray(actual, dtype=np.float64)

    if exp.size == 0 or act.size == 0:
        raise ValueError("Expected and actual arrays must contain at least one element")

    bin_edges = compute_quantile_bins(exp, num_bins=num_bins)

    exp_counts, _ = np.histogram(exp, bins=bin_edges)
    act_counts, _ = np.histogram(act, bins=bin_edges)

    exp_pct = exp_counts.astype(np.float64) / len(exp)
    act_pct = act_counts.astype(np.float64) / len(act)

    # Laplace smoothing to prevent division by zero or log(0)
    smooth_exp = (exp_pct + eps) / np.sum(exp_pct + eps)
    smooth_act = (act_pct + eps) / np.sum(act_pct + eps)

    contributions = (smooth_act - smooth_exp) * np.log(smooth_act / smooth_exp)
    total_psi = float(np.sum(contributions))

    status: Literal["ok", "watch", "alert"]
    if total_psi < 0.10:
        status = "ok"
    elif total_psi <= 0.25:
        status = "watch"
    else:
        status = "alert"

    # Finite display edges
    finite_edges = np.percentile(exp, np.linspace(0, 100, num_bins + 1))
    bins_data: list[PSIBinResult] = []
    for b in range(num_bins):
        bins_data.append(
            PSIBinResult(
                bin_index=b,
                lower_bound=float(finite_edges[b]),
                upper_bound=float(finite_edges[b + 1]),
                expected_pct=round(float(exp_pct[b]), 5),
                actual_pct=round(float(act_pct[b]), 5),
                psi_contribution=round(float(contributions[b]), 5),
            )
        )

    return PSIReport(
        feature_name=feature_name,
        psi=round(total_psi, 5),
        status=status,
        num_bins=num_bins,
        n_expected=len(exp),
        n_actual=len(act),
        bins=bins_data,
    )


def compute_categorical_psi(
    expected_categories: list[str] | np.ndarray,
    actual_categories: list[str] | np.ndarray,
    feature_name: str = "codec",
    eps: float = 1e-4,
) -> PSIReport:
    """Calculate PSI over categorical distributions (e.g. video codec, container)."""
    exp_list = [str(x) for x in expected_categories]
    act_list = [str(x) for x in actual_categories]

    if not exp_list or not act_list:
        raise ValueError("Expected and actual category lists must not be empty")

    all_cats = sorted(set(exp_list).union(set(act_list)))
    n_exp = len(exp_list)
    n_act = len(act_list)

    exp_counts = np.array([exp_list.count(c) for c in all_cats], dtype=np.float64)
    act_counts = np.array([act_list.count(c) for c in all_cats], dtype=np.float64)

    exp_pct = exp_counts / n_exp
    act_pct = act_counts / n_act

    smooth_exp = (exp_pct + eps) / np.sum(exp_pct + eps)
    smooth_act = (act_pct + eps) / np.sum(act_pct + eps)

    contributions = (smooth_act - smooth_exp) * np.log(smooth_act / smooth_exp)
    total_psi = float(np.sum(contributions))

    status: Literal["ok", "watch", "alert"]
    if total_psi < 0.10:
        status = "ok"
    elif total_psi <= 0.25:
        status = "watch"
    else:
        status = "alert"

    bins_data: list[PSIBinResult] = []
    for idx, cat in enumerate(all_cats):
        bins_data.append(
            PSIBinResult(
                bin_index=idx,
                lower_bound=float(idx),
                upper_bound=float(idx + 1),
                expected_pct=round(float(exp_pct[idx]), 5),
                actual_pct=round(float(act_pct[idx]), 5),
                psi_contribution=round(float(contributions[idx]), 5),
            )
        )

    return PSIReport(
        feature_name=feature_name,
        psi=round(total_psi, 5),
        status=status,
        num_bins=len(all_cats),
        n_expected=n_exp,
        n_actual=n_act,
        bins=bins_data,
    )


def evaluate_input_drift(
    reference_records: list[dict[str, Any]],
    production_records: list[dict[str, Any]],
) -> FeatureDriftSummary:
    """Evaluate multi-feature drift across continuous and categorical inputs."""
    now_str = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Score drift
    ref_scores = [r["score"] for r in reference_records if "score" in r]
    prod_scores = [r["score"] for r in production_records if "score" in r]
    score_report = compute_psi(
        expected=np.array(ref_scores, dtype=np.float64),
        actual=np.array(prod_scores, dtype=np.float64),
        feature_name="score",
    )

    input_drifts: dict[str, PSIReport] = {}
    continuous_features = ["face_size", "detector_conf", "fps", "resolution"]
    for feat in continuous_features:
        ref_f = [r[feat] for r in reference_records if feat in r and r[feat] is not None]
        prod_f = [r[feat] for r in production_records if feat in r and r[feat] is not None]
        if ref_f and prod_f:
            input_drifts[feat] = compute_psi(
                expected=np.array(ref_f, dtype=np.float64),
                actual=np.array(prod_f, dtype=np.float64),
                feature_name=feat,
            )

    categorical_features = ["codec", "container"]
    for feat in categorical_features:
        ref_c = [r[feat] for r in reference_records if feat in r and r[feat] is not None]
        prod_c = [r[feat] for r in production_records if feat in r and r[feat] is not None]
        if ref_c and prod_c:
            input_drifts[feat] = compute_categorical_psi(
                expected_categories=ref_c,
                actual_categories=prod_c,
                feature_name=feat,
            )

    # Determine overall status
    statuses = [score_report.status] + [r.status for r in input_drifts.values()]
    overall_status: Literal["ok", "watch", "alert"]
    if "alert" in statuses:
        overall_status = "alert"
    elif "watch" in statuses:
        overall_status = "watch"
    else:
        overall_status = "ok"

    return FeatureDriftSummary(
        timestamp=now_str,
        overall_status=overall_status,
        score_drift=score_report,
        input_drifts=input_drifts,
    )


def compute_ece_ipw(
    probs: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray | None = None,
    num_bins: int = 15,
    model_id: str = "smsdt-st-b",
) -> CalibrationReport:
    """Compute rolling Expected Calibration Error (ECE) with Inverse-Probability Weighting (IPW).

    Accounts for audit sample selection bias:
        Flagged samples (needs_review): w = 1.0 (100% audited)
        Audit samples (likely_authentic / likely_manipulated): w = 1.0 / audit_sample_rate
    """
    p = np.asarray(probs, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    n = len(p)

    if n == 0 or len(y) != n:
        raise ValueError("probs and labels must be non-empty arrays of identical length")

    if weights is None:
        w = np.ones(n, dtype=np.float64)
    else:
        w = np.asarray(weights, dtype=np.float64)

    total_weight = float(np.sum(w))
    if total_weight <= 0:
        raise ValueError("Total weights sum must be strictly positive")

    bin_edges = np.linspace(0.0, 1.0, num_bins + 1)
    curve_points: list[ReliabilityBinPoint] = []
    weighted_abs_error_sum = 0.0

    for b in range(num_bins):
        low = bin_edges[b]
        high = bin_edges[b + 1]

        if b == num_bins - 1:
            mask = (p >= low) & (p <= high)
        else:
            mask = (p >= low) & (p < high)

        count = int(np.sum(mask))
        bin_weight = float(np.sum(w[mask]))
        center = float(0.5 * (low + high))

        if bin_weight > 0:
            mean_conf = float(np.sum(w[mask] * p[mask]) / bin_weight)
            mean_acc = float(np.sum(w[mask] * y[mask]) / bin_weight)
            cal_err = abs(mean_acc - mean_conf)
        else:
            mean_conf = center
            mean_acc = 0.0
            cal_err = 0.0

        weighted_abs_error_sum += (bin_weight / total_weight) * cal_err

        curve_points.append(
            ReliabilityBinPoint(
                bin_index=b,
                bin_lower=round(low, 4),
                bin_upper=round(high, 4),
                bin_center=round(center, 4),
                sample_count=count,
                weight_sum=round(bin_weight, 2),
                mean_confidence=round(mean_conf, 4),
                mean_accuracy=round(mean_acc, 4),
                calibration_error=round(cal_err, 4),
            )
        )

    # Weighted Brier score: sum(w * (p - y)^2) / total_weight
    brier_score = float(np.sum(w * (p - y) ** 2) / total_weight)

    # Weighted Log-Loss
    eps = 1e-7
    p_clamped = np.clip(p, eps, 1.0 - eps)
    log_loss = -float(
        np.sum(w * (y * np.log(p_clamped) + (1.0 - y) * np.log(1.0 - p_clamped))) / total_weight
    )

    return CalibrationReport(
        model_id=model_id,
        n_samples=n,
        num_bins=num_bins,
        ece=round(weighted_abs_error_sum, 4),
        brier_score=round(brier_score, 4),
        log_loss=round(log_loss, 4),
        reliability_curve=curve_points,
    )
