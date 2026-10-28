import numpy as np
import pytest
from sv_engine.calibration import apply_platt, fit_platt, logit, sigmoid


def test_sigmoid_logit_roundtrip():
    for p in [0.01, 0.1, 0.5, 0.75, 0.99]:
        assert pytest.approx(sigmoid(logit(p)), abs=1e-5) == p


def test_known_stage_b_calibration():
    # S-MSDT-ST Stage B known parameters from SPEC §2.1: a=0.6470, b=-0.5865, tau*=0.7507
    a, b = 0.6470, -0.5865
    # If logit is 1.66:
    p = apply_platt(1.66, a, b)
    assert pytest.approx(p, abs=0.01) == 0.62


def test_fit_platt_optimization():
    np.random.seed(42)
    # Synthetic scores: reals centered around -1.5, fakes centered around +1.5
    u_reals = np.random.normal(-1.5, 0.8, size=100)
    u_fakes = np.random.normal(1.5, 0.8, size=100)
    scores = np.concatenate([u_reals, u_fakes])
    labels = np.concatenate([np.zeros(100), np.ones(100)])

    a, b = fit_platt(scores, labels)
    assert a > 0.5  # Positive scaling slope
