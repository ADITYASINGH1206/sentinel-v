import React from 'react';
import { ShieldCheck, Eye, ShieldAlert, HelpCircle } from 'lucide-react';

export type DecisionBand = 'likely_authentic' | 'needs_review' | 'likely_manipulated' | 'inconclusive';

interface BandChipProps {
  band: DecisionBand;
  size?: 'sm' | 'md' | 'lg';
}

export const BandChip: React.FC<BandChipProps> = ({ band, size = 'md' }) => {
  const configs = {
    likely_authentic: {
      label: 'Likely authentic',
      icon: ShieldCheck,
      colorClass: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700',
    },
    needs_review: {
      label: 'Needs review',
      icon: Eye,
      colorClass: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300 border-amber-300 dark:border-amber-700',
    },
    likely_manipulated: {
      label: 'Likely manipulated',
      icon: ShieldAlert,
      colorClass: 'bg-rose-50 text-rose-800 dark:bg-rose-950/50 dark:text-rose-300 border-rose-300 dark:border-rose-700',
    },
    inconclusive: {
      label: 'Inconclusive',
      icon: HelpCircle,
      colorClass: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-600',
    },
  };

  const config = configs[band] || configs.inconclusive;
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2',
  };

  return (
    <span
      className={`inline-flex items-center font-medium border rounded-full ${config.colorClass} ${sizeClasses[size]}`}
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span>{config.label}</span>
    </span>
  );
};
