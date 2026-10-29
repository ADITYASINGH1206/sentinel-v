import stCalibration from '../content/sourced/st_calibration.json';

export const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));
export const logit = (p: number) => Math.log(p / (1 - p));

/** Class-balanced Platt scaling: p_bal = σ(a·u + b). */
export function platt(u: number, a: number = stCalibration.a, b: number = stCalibration.b): number {
  return sigmoid(a * u + b);
}

/** Prior correction (SPEC §6.5): logit(p_π) = logit(p_bal) + log(π / (1 − π)). */
export function priorCorrect(pBal: number, prevalence: number): number {
  const clamped = Math.min(Math.max(pBal, 1e-9), 1 - 1e-9);
  return sigmoid(logit(clamped) + Math.log(prevalence / (1 - prevalence)));
}

export interface BaseRateResult {
  precision: number;
  flagsPer10k: number;
  caughtPer10k: number;
  missedPer10k: number;
}

/** Expected outcomes per 10,000 videos at prevalence π for an operating point (TPR, FPR). */
export function baseRate(tpr: number, fpr: number, prevalence: number): BaseRateResult {
  const tp = tpr * prevalence;
  const fp = fpr * (1 - prevalence);
  return {
    precision: tp + fp === 0 ? 0 : tp / (tp + fp),
    flagsPer10k: (tp + fp) * 10_000,
    caughtPer10k: tp * 10_000,
    missedPer10k: (1 - tpr) * prevalence * 10_000,
  };
}

export const ST_CALIBRATION = stCalibration;
