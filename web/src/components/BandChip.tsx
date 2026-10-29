import React from 'react';
import { m } from 'framer-motion';
import { ShieldCheck, Eye, ShieldAlert, HelpCircle } from 'lucide-react';

export type DecisionBand = 'likely_authentic' | 'needs_review' | 'likely_manipulated' | 'inconclusive';

interface BandChipProps {
  band: DecisionBand;
  size?: 'sm' | 'md' | 'lg';
  /** Play a one-time pulse (used on the verdict card). */
  pulse?: boolean;
}

const CONFIG = {
  likely_authentic: {
    label: 'Likely authentic',
    icon: ShieldCheck,
    className: 'border-band-authentic/35 bg-band-authentic/10 text-band-authentic',
    ring: 'rgb(var(--band-authentic) / 0.35)',
  },
  needs_review: {
    label: 'Needs review',
    icon: Eye,
    className: 'border-band-review/35 bg-band-review/10 text-band-review',
    ring: 'rgb(var(--band-review) / 0.35)',
  },
  likely_manipulated: {
    label: 'Likely manipulated',
    icon: ShieldAlert,
    className: 'border-band-manipulated/35 bg-band-manipulated/10 text-band-manipulated',
    ring: 'rgb(var(--band-manipulated) / 0.35)',
  },
  inconclusive: {
    label: 'Inconclusive',
    icon: HelpCircle,
    className: 'border-band-inconclusive/35 bg-band-inconclusive/10 text-band-inconclusive',
    ring: 'rgb(var(--band-inconclusive) / 0.35)',
  },
} as const;

const SIZE = {
  sm: 'px-2 py-0.5 text-xs gap-1',
  md: 'px-2.5 py-1 text-sm gap-1.5',
  lg: 'px-3.5 py-1.5 text-base gap-2',
};

const ICON = { sm: 'h-3.5 w-3.5', md: 'h-4 w-4', lg: 'h-5 w-5' };

export const BandChip: React.FC<BandChipProps> = ({ band, size = 'md', pulse = false }) => {
  const config = CONFIG[band] || CONFIG.inconclusive;
  const Icon = config.icon;
  return (
    <m.span
      initial={pulse ? { scale: 0.96, boxShadow: `0 0 0 0px ${config.ring}` } : false}
      animate={pulse ? { scale: [0.96, 1.03, 1], boxShadow: [`0 0 0 0px ${config.ring}`, `0 0 0 8px rgb(0 0 0 / 0)`, `0 0 0 0px rgb(0 0 0 / 0)`] } : undefined}
      transition={{ duration: 0.42, ease: [0.3, 0, 0, 1] }}
      className={`inline-flex items-center whitespace-nowrap rounded-full border font-medium ${config.className} ${SIZE[size]}`}
    >
      <Icon className={`${ICON[size]} shrink-0`} aria-hidden />
      <span>{config.label}</span>
    </m.span>
  );
};
