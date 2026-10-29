import numpy as np
from sv_monitor.drift import (
    compute_categorical_psi,
    compute_ece_ipw,
    compute_psi,
    compute_quantile_bins,
    evaluate_input_drift,
)


def test_compute_quantile_bins():
    """Verify quantile bins are monotonically increasing and cover the real line."""
    ref = np.random.default_rng(42).normal(loc=0.0, scale=1.0, size=1000)
    edges = compute_quantile_bins(ref, num_bins=10)

    assert len(edges) == 11
    assert edges[0] == -np.inf
    assert edges[-1] == np.inf
    for i in range(len(edges) - 1):
        assert edges[i] < edges[i + 1]


def test_psi_identical_distribution_ok():
    """Identical distributions should have PSI close to zero and status 'ok'."""
    rng = np.random.default_rng(101)
    expected = rng.normal(loc=-1.0, scale=1.0, size=2000)
    actual = rng.normal(loc=-1.0, scale=1.0, size=2000)

    report = compute_psi(expected, actual, feature_name="score", num_bins=10)
    assert report.psi < 0.05
    assert report.status == "ok"
    assert report.num_bins == 10
    assert len(report.bins) == 10


def test_psi_moderate_drift_watch():
    """Moderate distribution shift should trigger 'watch' (0.10 <= PSI <= 0.25)."""
    rng = np.random.default_rng(202)
    expected = rng.normal(loc=0.0, scale=1.0, size=3000)
    actual = rng.normal(loc=0.35, scale=1.0, size=3000)

    report = compute_psi(expected, actual, feature_name="score", num_bins=10)
    assert 0.08 <= report.psi <= 0.28
    assert report.status in ["watch", "alert"]


def test_psi_significant_drift_alert():
    """Large distribution shift should trigger 'alert' (PSI > 0.25)."""
    rng = np.random.default_rng(303)
    expected = rng.normal(loc=-2.0, scale=0.8, size=3000)
    actual = rng.normal(loc=1.5, scale=1.2, size=3000)

    report = compute_psi(expected, actual, feature_name="score", num_bins=10)
    assert report.psi > 0.25
    assert report.status == "alert"


def test_simulated_30_day_drift_curve():
    """Simulate 30-day domain shift showing progression from OK to Watch to Alert."""
    rng = np.random.default_rng(404)
    baseline = rng.normal(loc=-1.5, scale=1.0, size=5000)

    psi_history = []
    statuses = []

    # Shift mean logits gradually over 30 days from -1.5 to +1.0
    for day in range(31):
        shift = (day / 30.0) * 2.5
        daily_actual = rng.normal(loc=-1.5 + shift, scale=1.0, size=1000)
        rep = compute_psi(baseline, daily_actual, num_bins=10)
        psi_history.append(rep.psi)
        statuses.append(rep.status)

    # Day 0 must be OK
    assert statuses[0] == "ok"
    assert psi_history[0] < 0.05

    # Day 30 must be ALERT
    assert statuses[-1] == "alert"
    assert psi_history[-1] > 0.25

    # Must contain watch state in the transition period
    assert "watch" in statuses
    # Monotonic drift growth
    assert psi_history[-1] > psi_history[0]


def test_categorical_psi_codecs():
    """Test PSI on categorical features (video codecs)."""
    expected = ["h264"] * 800 + ["hevc"] * 150 + ["vp9"] * 50
    # Production traffic suddenly flooded with AV1 and VP9
    actual = ["h264"] * 300 + ["hevc"] * 100 + ["vp9"] * 400 + ["av1"] * 200

    report = compute_categorical_psi(expected, actual, feature_name="codec")
    assert report.psi > 0.25
    assert report.status == "alert"
    assert report.num_bins == 4


def test_evaluate_input_drift_multifeature():
    """Test composite input drift evaluation."""
    rng = np.random.default_rng(808)
    ref_records = [
        {
            "score": float(rng.normal(-1.5, 0.8)),
            "face_size": float(rng.normal(25000.0, 1000)),
            "detector_conf": 0.95,
            "fps": 30.0,
            "resolution": 921600,
            "codec": "h264",
        }
        for _ in range(500)
    ]

    # Production records with stable scores but heavy face size shift (small faces)
    prod_records = [
        {
            "score": float(rng.normal(-1.5, 0.8)),
            "face_size": float(rng.normal(5000.0, 500)),
            "detector_conf": 0.95,
            "fps": 30.0,
            "resolution": 921600,
            "codec": "h264",
        }
        for _ in range(500)
    ]

    summary = evaluate_input_drift(ref_records, prod_records)
    assert summary.score_drift.status == "ok"
    assert "face_size" in summary.input_drifts
    assert summary.input_drifts["face_size"].status == "alert"
    assert summary.overall_status == "alert"


def test_ipw_vs_unweighted_ece():
    """Verify that Inverse-Probability Weighting (IPW) corrects for audit sampling bias."""
    rng = np.random.default_rng(505)

    # Synthetic population: 90% easy authentic (p ~ 0.05), 10% ambiguous/fake (p ~ 0.8)
    probs_pop = np.concatenate(
        [
            rng.uniform(0.01, 0.10, size=9000),
            rng.uniform(0.70, 0.95, size=1000),
        ]
    )
    labels_pop = np.concatenate(
        [
            np.zeros(9000, dtype=int),
            np.ones(1000, dtype=int),
        ]
    )

    # Review sample with selection bias:
    # 1. Ambiguous/high-score items (p >= 0.70): 100% reviewed -> sampling rate = 1.0, weight = 1.0
    # 2. Low-score items (p < 0.70): only 2% random audit -> sampling rate = 0.02, weight = 50.0
    high_mask = probs_pop >= 0.70
    low_mask = probs_pop < 0.70

    p_high = probs_pop[high_mask]
    y_high = labels_pop[high_mask]
    w_high = np.ones(len(p_high))

    n_low_audit = int(np.sum(low_mask) * 0.02)  # ~180 samples
    idx_low = rng.choice(np.where(low_mask)[0], size=n_low_audit, replace=False)
    p_low = probs_pop[idx_low]
    y_low = labels_pop[idx_low]
    w_low = np.full(len(p_low), 1.0 / 0.02)  # weight = 50.0

    sample_probs = np.concatenate([p_high, p_low])
    sample_labels = np.concatenate([y_high, y_low])
    sample_weights = np.concatenate([w_high, w_low])

    # Unweighted ECE on reviewed sample (severely biased because 85% of reviews are high-score)
    unweighted_rep = compute_ece_ipw(sample_probs, sample_labels, weights=None, num_bins=15)

    # IPW ECE on reviewed sample (restores true population proportions)
    ipw_rep = compute_ece_ipw(sample_probs, sample_labels, weights=sample_weights, num_bins=15)

    assert ipw_rep.ece >= 0.0
    assert unweighted_rep.ece >= 0.0
    assert len(ipw_rep.reliability_curve) == 15
    # The weights successfully alter the calibration error estimate
    assert ipw_rep.ece != unweighted_rep.ece
