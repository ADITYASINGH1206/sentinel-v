import React from 'react';
import { m } from 'framer-motion';
import type { DecisionBand } from '../BandChip';
import { cn } from '../../design/ui';

export const PageHeader: React.FC<{ title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode; meta?: React.ReactNode }> = ({
  title,
  description,
  actions,
  meta,
}) => (
  <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div className="min-w-0">
      {meta && <div className="mb-2 flex flex-wrap items-center gap-2">{meta}</div>}
      <h1 className="text-2xl font-semibold tracking-tight text-text">{title}</h1>
      {description && <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>}
    </div>
    {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
  </div>
);

export const bandStripe: Record<DecisionBand | 'none', string> = {
  likely_authentic: 'bg-band-authentic',
  needs_review: 'bg-band-review',
  likely_manipulated: 'bg-band-manipulated',
  inconclusive: 'bg-band-inconclusive',
  none: 'bg-border',
};

export function relativeTime(iso: string, now = Date.now()): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const s = Math.round((now - t) / 1000);
  const abs = Math.abs(s);
  if (abs < 60) return 'just now';
  const mins = Math.round(abs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs} h ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

export const formatDateTime = (iso: string) => {
  const d = new Date(iso);
  return Number.isFinite(d.getTime()) ? d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—';
};

/** Animated list container: staggers only the first 12 children on first render. */
export const StaggerList: React.FC<{ children: React.ReactNode; className?: string; as?: 'ul' | 'tbody' | 'div' }> = ({ children, className, as = 'div' }) => {
  const Comp = m[as] as typeof m.div;
  return (
    <Comp className={className} initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.03 } } }}>
      {children}
    </Comp>
  );
};

export const staggerItem = (index: number) =>
  index < 12
    ? { variants: { hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: [0.2, 0, 0, 1] } } } }
    : {};

export const StatusPill: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    pending_review: 'border-band-review/30 bg-band-review/10 text-band-review',
    reviewed: 'border-band-authentic/30 bg-band-authentic/10 text-band-authentic',
    adjudication: 'border-band-manipulated/30 bg-band-manipulated/10 text-band-manipulated',
    not_required: 'border-border bg-surface-2 text-muted',
    failed: 'border-band-manipulated/30 bg-band-manipulated/10 text-band-manipulated',
    processing: 'border-accent/30 bg-accent/10 text-accent',
    queued: 'border-border bg-surface-2 text-muted',
  };
  const label: Record<string, string> = {
    pending_review: 'Pending review',
    reviewed: 'Reviewed',
    adjudication: 'Adjudication',
    not_required: 'No review needed',
    failed: 'Failed',
    processing: 'Processing',
    queued: 'Queued',
  };
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium', map[status] ?? map.not_required)}>
      {label[status] ?? status}
    </span>
  );
};
