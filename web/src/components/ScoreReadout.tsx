import React from 'react';

interface ScoreReadoutProps {
  p_bal: number;
  p_prior?: number;
  prior_prevalence?: number;
}

export const ScoreReadout: React.FC<ScoreReadoutProps> = ({
  p_bal,
  p_prior,
  prior_prevalence = 0.01,
}) => {
  // SPEC rule: Never show more than 2 decimals of p_bal
  const formattedScore = p_bal.toFixed(2);
  const formattedPrior = p_prior !== undefined ? (p_prior * 100).toFixed(1) : null;
  const prevalencePercent = (prior_prevalence * 100).toFixed(0);

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-text">
          Score {formattedScore}
        </span>
        {formattedPrior && (
          <span className="text-sm text-muted font-medium">
            ≈ {formattedPrior}% at {prevalencePercent}% prevalence
          </span>
        )}
      </div>
      <p className="text-xs text-muted">
        Based on validation data; may differ on your traffic.
      </p>
    </div>
  );
};

