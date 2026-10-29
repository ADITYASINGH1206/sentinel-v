import React from 'react';
import { BRAND } from '../brand';
import { cn } from './ui';

/** Original VeriFrame monogram: a framed check mark crossed by a scan line. */
export const LogoMark: React.FC<{ className?: string; title?: string }> = ({ className, title }) => (
  <svg viewBox="0 0 64 64" className={cn('h-8 w-8', className)} role={title ? 'img' : undefined} aria-hidden={title ? undefined : true}>
    {title && <title>{title}</title>}
    <defs>
      <linearGradient id="vf-logo-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="rgb(242 153 79)" />
        <stop offset="1" stopColor="rgb(79 86 190)" />
      </linearGradient>
    </defs>
    <rect x="4" y="4" width="56" height="56" rx="14" fill="rgb(7 11 18)" />
    <path
      d="M16 22v-6h6M42 16h6v6M48 42v6h-6M22 48h-6v-6"
      fill="none"
      stroke="url(#vf-logo-g)"
      strokeWidth="4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M21 26l11 14 11-14" fill="none" stroke="rgb(231 237 245)" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" />
    <rect x="14" y="31" width="36" height="2.5" rx="1.25" fill="url(#vf-logo-g)" opacity="0.9" />
  </svg>
);

export const Logo: React.FC<{ className?: string; compact?: boolean; suffix?: string }> = ({ className, compact, suffix }) => (
  <span className={cn('inline-flex items-center gap-2.5', className)}>
    <LogoMark />
    {!compact && (
      <span className="flex items-baseline gap-2">
        <span className="text-[15px] font-semibold tracking-tight text-text">{BRAND.name}</span>
        {suffix && <span className="text-xs font-medium text-muted">{suffix}</span>}
      </span>
    )}
  </span>
);
