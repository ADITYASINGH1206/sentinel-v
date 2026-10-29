import React from 'react';
import { m } from 'framer-motion';
import { cn } from '../design/ui';

export type StageState = 'pending' | 'active' | 'done' | 'error';
export interface Stage {
  id: string;
  label: string;
  state: StageState;
  detail?: string;
}

const Check: React.FC = () => (
  <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
    <m.path
      d="M3.5 8.5l3 3 6-7"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ duration: 0.3, ease: [0.3, 0, 0, 1] }}
    />
  </svg>
);

/** Horizontal pipeline stepper driven only by real progress events. */
export const StageProgress: React.FC<{ stages: Stage[] }> = ({ stages }) => (
  <ol className="grid gap-3 sm:grid-cols-[repeat(auto-fit,minmax(0,1fr))]" aria-label="Analysis progress">
    {stages.map((s, i) => (
      <li key={s.id} className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-2">
        <div className="flex w-full items-center gap-2">
          <span
            className={cn(
              'grid h-6 w-6 shrink-0 place-items-center rounded-full border text-[11px] font-semibold transition-colors duration-200',
              s.state === 'done' && 'border-accent bg-accent text-accent-contrast',
              s.state === 'active' && 'border-accent text-accent',
              s.state === 'pending' && 'border-border text-muted',
              s.state === 'error' && 'border-band-manipulated bg-band-manipulated text-white'
            )}
            aria-hidden
          >
            {s.state === 'done' ? <Check /> : s.state === 'error' ? '!' : i + 1}
          </span>
          <div className="relative hidden h-0.5 flex-1 overflow-hidden rounded-full bg-border sm:block">
            <m.div
              className="absolute inset-y-0 left-0 bg-accent"
              initial={false}
              animate={{ width: s.state === 'done' ? '100%' : s.state === 'active' ? '45%' : '0%' }}
              transition={{ duration: 0.32, ease: [0.2, 0, 0, 1] }}
            />
          </div>
        </div>
        <div>
          <p className={cn('text-xs font-medium', s.state === 'pending' ? 'text-muted' : 'text-text')}>
            {s.label}
            <span className="sr-only"> — {s.state}</span>
          </p>
          {s.detail && <p className="font-mono text-[11px] text-muted">{s.detail}</p>}
        </div>
      </li>
    ))}
  </ol>
);
