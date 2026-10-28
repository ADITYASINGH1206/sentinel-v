import pytest
from sv_engine.priors import adjust_prevalence, estimate_ppv


def test_prior_identity_at_half():
    # With pi = 0.5, prior correction must be exact identity
    for p in [0.1, 0.35, 0.5, 0.62, 0.89]:
        assert pytest.approx(adjust_prevalence(p, prior_pi=0.5), abs=1e-5) == p


def test_prior_suppression_low_prevalence():
    # At pi = 0.01 (1% base rate), a balanced score of 0.62 drops to ~0.016
    p_adj = adjust_prevalence(0.62, prior_pi=0.01)
    assert pytest.approx(p_adj, abs=0.005) == 0.016


def test_estimate_ppv_paper_table():
    # ST @ 1% FPR (TPR 47.1%), pi = 1%
    # Numerator = 0.471 * 0.01 = 0.00471
    # Denom = 0.00471 + 0.01 * 0.99 = 0.00471 + 0.0099 = 0.01461
    # PPV = 0.00471 / 0.01461 = 0.322 (32.2%)
    ppv = estimate_ppv(tpr=0.471, fpr=0.01, prior_pi=0.01)
    assert pytest.approx(ppv, abs=0.005) == 0.322

