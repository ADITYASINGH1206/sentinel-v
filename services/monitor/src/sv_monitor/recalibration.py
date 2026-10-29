import hashlib
import json
import secrets
from datetime import UTC, datetime

import numpy as np
from sv_engine.calibration import apply_platt, fit_platt

from sv_monitor.drift import compute_ece_ipw
from sv_monitor.schemas import PromotedCalibration, RecalibrationProposal

__all__ = [
    "InsufficientDataError",
    "propose_recalibration",
    "promote_recalibration",
    "compute_confusion_matrix",
]


class InsufficientDataError(ValueError):
    """Raised when ground-truth review dataset fails minimum recalibration thresholds."""

    pass


def compute_confusion_matrix(
    probs: np.ndarray,
    labels: np.ndarray,
    tau_authentic: float = 0.35,
    tau_manipulated: float = 0.75,
) -> dict[str, int]:
    """Calculate confusion matrix and screening band distribution."""
    p = np.asarray(probs, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int32)

    authentic_pred = p < tau_authentic
    manipulated_pred = p > tau_manipulated
    review_pred = (p >= tau_authentic) & (p <= tau_manipulated)

    tp = int(np.sum((manipulated_pred) & (y == 1)))
    fp = int(np.sum((manipulated_pred) & (y == 0)))
    tn = int(np.sum((authentic_pred) & (y == 0)))
    fn = int(np.sum((authentic_pred) & (y == 1)))

    needs_review_real = int(np.sum((review_pred) & (y == 0)))
    needs_review_fake = int(np.sum((review_pred) & (y == 1)))

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "needs_review_total": int(np.sum(review_pred)),
        "needs_review_real": needs_review_real,
        "needs_review_fake": needs_review_fake,
        "total": len(p),
    }


def propose_recalibration(
    u_scores: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray | None = None,
    current_parameters: tuple[float, float] = (0.6470, -0.5865),
    model_id: str = "smsdt-st-b",
    min_samples: int = 200,
    min_per_class: int = 50,
) -> RecalibrationProposal:
    """Fit candidate Platt recalibration on expert review data with side-by-side diagnostics."""
    u = np.asarray(u_scores, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int32)
    n = len(u)

    if n < min_samples:
        raise InsufficientDataError(
            f"Recalibration requires at least {min_samples} expert review samples, but received {n}."
        )

    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))

    if n_pos < min_per_class:
        raise InsufficientDataError(
            f"Recalibration requires at least {min_per_class} manipulated (positive) samples, but received {n_pos}."
        )
    if n_neg < min_per_class:
        raise InsufficientDataError(
            f"Recalibration requires at least {min_per_class} authentic (negative) samples, but received {n_neg}."
        )

    # 1. Fit new class-balanced Platt parameters
    a_new, b_new = fit_platt(u, y)
    candidate_params = (round(a_new, 4), round(b_new, 4))

    # 2. Compute probabilities under current and candidate calibrations
    a_curr, b_curr = current_parameters
    p_curr = np.array([apply_platt(score, a_curr, b_curr) for score in u], dtype=np.float64)
    p_cand = np.array([apply_platt(score, a_new, b_new) for score in u], dtype=np.float64)

    # 3. Compute side-by-side IPW calibration metrics and reliability curves
    curr_calib_report = compute_ece_ipw(p_curr, y, weights=weights, model_id=model_id)
    cand_calib_report = compute_ece_ipw(p_cand, y, weights=weights, model_id=model_id)

    curr_metrics = {
        "ece": curr_calib_report.ece,
        "brier_score": curr_calib_report.brier_score,
        "log_loss": curr_calib_report.log_loss,
    }
    cand_metrics = {
        "ece": cand_calib_report.ece,
        "brier_score": cand_calib_report.brier_score,
        "log_loss": cand_calib_report.log_loss,
    }
    delta_ece = round(cand_calib_report.ece - curr_calib_report.ece, 4)

    # 4. Confusion matrices before and after
    cm_curr = compute_confusion_matrix(p_curr, y)
    cm_cand = compute_confusion_matrix(p_cand, y)

    now_str = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    proposal_id = f"prop_{secrets.token_hex(12)}"

    return RecalibrationProposal(
        proposal_id=proposal_id,
        model_id=model_id,
        created_at=now_str,
        n_expert_reviews=n,
        n_authentic=n_neg,
        n_manipulated=n_pos,
        current_parameters=current_parameters,
        candidate_parameters=candidate_params,
        current_metrics=curr_metrics,
        candidate_metrics=cand_metrics,
        delta_ece=delta_ece,
        confusion_matrices={"current": cm_curr, "candidate": cm_cand},
        reliability_comparison={
            "current": curr_calib_report.model_dump(),
            "candidate": cand_calib_report.model_dump(),
        },
        status="proposed",
    )


def promote_recalibration(
    proposal: RecalibrationProposal,
    admin_user: str,
    justification: str,
    target_bundle_version: str = "bundle-2026-recal-01",
) -> PromotedCalibration:
    """Promote candidate calibration to official status with written admin justification.

    SPEC §13 rule: Never overwrite historic calibrations. Promotion generates a new bundle version.
    """
    if not justification or len(justification.strip()) < 20:
        raise ValueError(
            "Admin promotion requires written justification of at least 20 characters explaining domain drift or calibration improvement."
        )

    now_str = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    cal_id = f"cal_{secrets.token_hex(12)}"

    # Generate deterministic SHA-256 bundle hash over the calibration specification
    cal_payload = {
        "calibration_id": cal_id,
        "model_id": proposal.model_id,
        "parameters": list(proposal.candidate_parameters),
        "promoted_at": now_str,
        "justification": justification.strip(),
    }
    payload_bytes = json.dumps(cal_payload, sort_keys=True).encode("utf-8")
    bundle_hash = hashlib.sha256(payload_bytes).hexdigest()

    return PromotedCalibration(
        calibration_id=cal_id,
        proposal_id=proposal.proposal_id,
        model_id=proposal.model_id,
        promoted_at=now_str,
        promoted_by=admin_user,
        justification=justification.strip(),
        bundle_version=target_bundle_version,
        bundle_hash=bundle_hash,
        parameters=proposal.candidate_parameters,
    )
