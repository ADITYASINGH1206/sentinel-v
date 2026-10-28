import math
from typing import Optional
from sv_engine.calibration import sigmoid, logit


def adjust_prevalence(p_bal: float, prior_pi: float = 0.01) -> float:
    """Adjust class-balanced probability (50/50 prior) to deployment prevalence pi.
    
    logit(p_pi) = logit(p_bal) + log(pi / (1 - pi))
    """
    if prior_pi <= 0.0:
        return 0.0
    if prior_pi >= 1.0:
        return 1.0
    
    # When pi = 0.5, log(0.5 / 0.5) = 0, exact identity
    l_bal = logit(p_bal)
    shift = math.log(prior_pi / (1.0 - prior_pi))
    return sigmoid(l_bal + shift)


def estimate_ppv(tpr: float, fpr: float, prior_pi: float) -> Optional[float]:
    """Calculate Positive Predictive Value (Precision) at prevalence pi.
    
    PPV(pi) = (TPR * pi) / (TPR * pi + FPR * (1 - pi))
    """
    numerator = tpr * prior_pi
    denominator = numerator + fpr * (1.0 - prior_pi)
    if denominator <= 0.0:
        return None
    return numerator / denominator
