import numpy as np
import pytest
from sv_monitor.recalibration import (
    InsufficientDataError,
    compute_confusion_matrix,
    promote_recalibration,
    propose_recalibration,
)


def test_recalibration_sample_size_guards():
    """Verify recalibration guards enforce minimum sample sizes and balanced classes."""
    u_small = np.random.normal(0, 1, size=150)
    y_small = np.random.randint(0, 2, size=150)

    # N < 200 should fail
    with pytest.raises(InsufficientDataError, match="at least 200"):
        propose_recalibration(u_small, y_small)

    # N = 250 but only 20 positives should fail
    u_imbal = np.random.normal(0, 1, size=250)
    y_imbal = np.zeros(250, dtype=int)
    y_imbal[:20] = 1

    with pytest.raises(InsufficientDataError, match="at least 50 manipulated"):
        propose_recalibration(u_imbal, y_imbal)

    # N = 250 but only 30 negatives should fail
    u_imbal2 = np.random.normal(0, 1, size=250)
    y_imbal2 = np.ones(250, dtype=int)
    y_imbal2[:30] = 0

    with pytest.raises(InsufficientDataError, match="at least 50 authentic"):
        propose_recalibration(u_imbal2, y_imbal2)


def test_propose_recalibration_success():
    """Verify propose_recalibration produces side-by-side reliability and confusion matrices."""
    rng = np.random.default_rng(606)
    # True authentic logits centered around -2.0, manipulated around +2.0
    u_auth = rng.normal(loc=-2.0, scale=0.8, size=150)
    u_manip = rng.normal(loc=2.0, scale=0.8, size=150)
    u = np.concatenate([u_auth, u_manip])
    y = np.concatenate([np.zeros(150, dtype=int), np.ones(150, dtype=int)])

    proposal = propose_recalibration(
        u_scores=u,
        labels=y,
        current_parameters=(1.0, 0.0),
        model_id="smsdt-st-b",
    )

    assert proposal.status == "proposed"
    assert proposal.n_expert_reviews == 300
    assert proposal.n_authentic == 150
    assert proposal.n_manipulated == 150

    # Parameters should be non-trivial
    a_new, b_new = proposal.candidate_parameters
    assert a_new > 0.0

    # Side-by-side comparisons present
    assert "current" in proposal.confusion_matrices
    assert "candidate" in proposal.confusion_matrices
    assert "current" in proposal.reliability_comparison
    assert "candidate" in proposal.reliability_comparison
    assert "ece" in proposal.current_metrics
    assert "ece" in proposal.candidate_metrics


def test_promote_recalibration_governance():
    """Verify promotion requires admin justification and creates immutable bundle version."""
    rng = np.random.default_rng(707)
    u = np.concatenate([rng.normal(-2, 1, 120), rng.normal(2, 1, 120)])
    y = np.concatenate([np.zeros(120, dtype=int), np.ones(120, dtype=int)])

    proposal = propose_recalibration(u, y, model_id="smsdt-st-b")

    # Short justification must be rejected
    with pytest.raises(ValueError, match="at least 20 characters"):
        promote_recalibration(proposal, admin_user="admin@sentinel.org", justification="too short")

    # Valid justification succeeds
    promoted = promote_recalibration(
        proposal,
        admin_user="admin@sentinel.org",
        justification="Recalibrated on 240 expert reviews after mobile camera compression drift observed.",
        target_bundle_version="bundle-2026-recal-02",
    )

    assert promoted.proposal_id == proposal.proposal_id
    assert promoted.model_id == "smsdt-st-b"
    assert promoted.promoted_by == "admin@sentinel.org"
    assert len(promoted.bundle_hash) == 64
    assert promoted.bundle_version == "bundle-2026-recal-02"
    assert promoted.parameters == proposal.candidate_parameters


def test_confusion_matrix_thresholds():
    """Verify compute_confusion_matrix adheres to decision thresholds."""
    probs = np.array([0.10, 0.20, 0.50, 0.60, 0.85, 0.95])
    labels = np.array([0, 0, 0, 1, 1, 1])

    cm = compute_confusion_matrix(probs, labels, tau_authentic=0.30, tau_manipulated=0.75)
    # p < 0.30: probs[0], probs[1] -> both label 0 -> TN=2, FN=0
    assert cm["tn"] == 2
    assert cm["fn"] == 0
    # p > 0.75: probs[4], probs[5] -> both label 1 -> TP=2, FP=0
    assert cm["tp"] == 2
    assert cm["fp"] == 0
    # 0.30 <= p <= 0.75: probs[2] (y=0), probs[3] (y=1) -> 2 in needs review
    assert cm["needs_review_total"] == 2
    assert cm["needs_review_real"] == 1
    assert cm["needs_review_fake"] == 1
