import math

import numpy as np


def sigmoid(x: float) -> float:
    """Stable sigmoid."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def logit(p: float, eps: float = 1e-7) -> float:
    """Stable logit function."""
    p_clamped = min(max(p, eps), 1.0 - eps)
    return math.log(p_clamped / (1.0 - p_clamped))


def apply_platt(u: float, a: float, b: float) -> float:
    """Class-balanced Platt scaling: p_bal = sigmoid(a * u + b)."""
    return sigmoid(a * u + b)


calibrate_platt = apply_platt


def fit_platt(u_scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Fit class-balanced Platt scaling parameters (a, b) using logistic regression.

    Equivalent to smsdt.eval_cross.fit_platt.
    """
    from scipy.optimize import minimize

    # Class-balanced negative log likelihood
    n_pos = np.sum(labels == 1)
    n_neg = np.sum(labels == 0)
    w_pos = 0.5 / max(n_pos, 1)
    w_neg = 0.5 / max(n_neg, 1)
    weights = np.where(labels == 1, w_pos, w_neg)

    def loss(params: np.ndarray) -> float:
        a, b = params
        preds = 1.0 / (1.0 + np.exp(-(a * u_scores + b)))
        preds = np.clip(preds, 1e-7, 1.0 - 1e-7)
        nll = -np.sum(weights * (labels * np.log(preds) + (1.0 - labels) * np.log(1.0 - preds)))
        return float(nll)

    res = minimize(loss, x0=np.array([1.0, 0.0]), method="L-BFGS-B")
    return float(res.x[0]), float(res.x[1])
