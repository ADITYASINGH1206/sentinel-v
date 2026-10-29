import React from 'react';
import { Info } from 'lucide-react';

interface ScoreReadoutProps {
  p_bal: number;
  p_prior?: number;
  prior_prevalence?: number;
  size?: 'md' | 'lg';
}

/**
 * SPEC §14.4: shows p_bal as "Score 0.62" (never more than 2 decimals) and p_prior as
 * "≈ 1.6% at 1% prevalence", with the validation caveat.
 */
export const ScoreReadout: React.FC<ScoreReadoutProps> = ({ p_bal, p_prior, prior_prevalence = 0.01, size = 'lg' }) => {
  const formattedScore = p_bal.toFixed(2);
  const formattedPrior = p_prior !== undefined ? (p_prior * 100).toFixed(1) : null;
  const prevalencePercent = (prior_prevalence * 100).toFixed(prior_prevalence < 0.01 ? 1 : 0);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className={`font-mono font-semibold tracking-tight text-text ${size === 'lg' ? 'text-3xl' : 'text-xl'}`}>
          Score {formattedScore}
        </span>
        {formattedPrior && (
          <span className="group relative inline-flex items-center gap-1 text-sm font-medium text-muted">
            ≈ {formattedPrior}% at {prevalencePercent}% prevalence
            <Info className="h-3.5 w-3.5" aria-hidden />
            <span
              role="tooltip"
              className="pointer-events-none absolute left-0 top-full z-20 mt-2 w-72 rounded-md border border-border bg-surface p-3 text-xs font-normal leading-relaxed text-muted opacity-0 shadow-2 transition-opacity group-hover:opacity-100"
            >
              The score is calibrated for a 50/50 mix of authentic and manipulated videos. The second number re-weights it for the
              prevalence configured in your policy: logit(p<sub>π</sub>) = logit(p<sub>bal</sub>) + log(π / (1 − π)).
            </span>
          </span>
        )}
      </div>
      <p className="text-xs text-muted">Based on validation data; may differ on your traffic.</p>
    </div>
  );
};
