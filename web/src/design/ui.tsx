import React, { useEffect, useRef, useState } from 'react';
import { animate, m, useInView } from 'framer-motion';
import { Check, Copy, FlaskConical, Info } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { usePreferences } from './preferences';
import { fadeUp } from './motion';
import { REQUIRED_DISCLAIMER } from '../copy/forbidden';

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs));
}

/* ------------------------------------------------------------------ Button */

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-out active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-contrast shadow-1 hover:bg-accent/90 hover:shadow-2',
        secondary: 'border border-border bg-surface text-text shadow-1 hover:border-accent/40 hover:bg-surface-2',
        ghost: 'text-muted hover:bg-surface-2 hover:text-text',
        danger: 'bg-band-manipulated text-white hover:bg-band-manipulated/90',
      },
      size: {
        sm: 'h-8 rounded-sm px-3 text-xs',
        md: 'h-9 rounded-md px-4 text-sm',
        lg: 'h-11 rounded-md px-5 text-sm',
        icon: 'h-9 w-9 rounded-md',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = 'button', ...props }, ref) => (
    <button ref={ref} type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
);
Button.displayName = 'Button';

export { buttonVariants };

/* -------------------------------------------------------------------- Card */

export const Card: React.FC<React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }> = ({
  className,
  interactive,
  ...props
}) => (
  <div
    className={cn(
      'rounded-md border border-border bg-surface shadow-1',
      interactive && 'transition-[transform,box-shadow,border-color] duration-150 hover:-translate-y-px hover:border-accent/30 hover:shadow-2',
      className
    )}
    {...props}
  />
);

export const CardHeader: React.FC<{ title: React.ReactNode; icon?: React.ReactNode; actions?: React.ReactNode; className?: string }> = ({
  title,
  icon,
  actions,
  className,
}) => (
  <div className={cn('flex items-center justify-between gap-3 border-b border-border px-4 py-3', className)}>
    <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-text">
      {icon && <span className="text-accent">{icon}</span>}
      <span className="truncate">{title}</span>
    </div>
    {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
);

/* ------------------------------------------------------------------- Badge */

const badgeVariants = cva('inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium', {
  variants: {
    tone: {
      neutral: 'border-border bg-surface-2 text-muted',
      accent: 'border-accent/30 bg-accent/10 text-accent',
      warning: 'border-band-review/30 bg-band-review/10 text-band-review',
      danger: 'border-band-manipulated/30 bg-band-manipulated/10 text-band-manipulated',
      success: 'border-band-authentic/30 bg-band-authentic/10 text-band-authentic',
    },
  },
  defaultVariants: { tone: 'neutral' },
});

export const Badge: React.FC<React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>> = ({
  className,
  tone,
  ...props
}) => <span className={cn(badgeVariants({ tone }), className)} {...props} />;

export const DemoBadge: React.FC<{ label?: string; className?: string }> = ({ label = 'DEMO DATA', className }) => (
  <Badge tone="warning" className={cn('font-mono tracking-wide', className)} title="Generated demo data — not an actual analysis">
    <FlaskConical className="h-3 w-3" aria-hidden />
    {label}
  </Badge>
);

/* --------------------------------------------------------------------- Kbd */

export const Kbd: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <kbd
    className={cn(
      'inline-flex min-w-[1.5rem] items-center justify-center rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted shadow-[inset_0_-1px_0_rgb(var(--border))]',
      className
    )}
  >
    {children}
  </kbd>
);

/* ---------------------------------------------------------------- HashText */

export const HashText: React.FC<{ value: string; head?: number; tail?: number; className?: string }> = ({
  value,
  head = 8,
  tail = 6,
  className,
}) => {
  const [copied, setCopied] = useState(false);
  const short = value.length > head + tail + 1 ? `${value.slice(0, head)}…${value.slice(-tail)}` : value;
  return (
    <button
      type="button"
      title={value}
      onClick={() => {
        navigator.clipboard?.writeText(value).catch(() => undefined);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      }}
      className={cn(
        'group inline-flex items-center gap-1 rounded px-1 font-mono text-xs text-text hover:bg-surface-2',
        className
      )}
      aria-label={`Copy ${value}`}
    >
      <span>{short}</span>
      {copied ? (
        <Check className="h-3 w-3 text-band-authentic" aria-hidden />
      ) : (
        <Copy className="h-3 w-3 text-muted opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
      )}
    </button>
  );
};

/* -------------------------------------------------------------- CountUp/Stat */

export const CountUp: React.FC<{ value: number; decimals?: number; suffix?: string; prefix?: string; duration?: number }> = ({
  value,
  decimals = 0,
  suffix = '',
  prefix = '',
  duration = 0.6,
}) => {
  const { reduceMotion } = usePreferences();
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef(0);
  const format = (v: number) =>
    `${prefix}${v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduceMotion) {
      node.textContent = format(value);
      prev.current = value;
      return;
    }
    const controls = animate(prev.current, value, {
      duration,
      ease: [0.3, 0, 0, 1],
      onUpdate: (v) => {
        node.textContent = format(v);
      },
    });
    prev.current = value;
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduceMotion]);

  return <span ref={ref}>{format(reduceMotion ? value : prev.current)}</span>;
};

export const Stat: React.FC<{
  label: string;
  value: number | null | undefined;
  decimals?: number;
  suffix?: string;
  icon?: React.ReactNode;
  hint?: string;
  tone?: 'neutral' | 'review' | 'manipulated' | 'authentic' | 'accent';
}> = ({ label, value, decimals = 0, suffix, icon, hint, tone = 'neutral' }) => {
  const toneClass = {
    neutral: 'bg-surface-2 text-muted',
    accent: 'bg-accent/10 text-accent',
    review: 'bg-band-review/10 text-band-review',
    manipulated: 'bg-band-manipulated/10 text-band-manipulated',
    authentic: 'bg-band-authentic/10 text-band-authentic',
  }[tone];
  return (
    <Card className="flex items-center gap-3 p-4">
      {icon && <div className={cn('grid h-10 w-10 shrink-0 place-items-center rounded-md', toneClass)}>{icon}</div>}
      <div className="min-w-0">
        <p className="truncate text-xs text-muted">{label}</p>
        <p className="font-mono text-xl font-semibold text-text" title={value == null ? hint ?? 'No data yet' : undefined}>
          {value == null ? '—' : <CountUp value={value} decimals={decimals} suffix={suffix} />}
        </p>
      </div>
    </Card>
  );
};

/* ---------------------------------------------------------- States/feedback */

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('skeleton h-4 w-full', className)} aria-hidden />
);

export const EmptyState: React.FC<{ icon?: React.ReactNode; title: string; body?: React.ReactNode; action?: React.ReactNode }> = ({
  icon,
  title,
  body,
  action,
}) => (
  <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
    {icon && <div className="grid h-12 w-12 place-items-center rounded-full bg-surface-2 text-muted">{icon}</div>}
    <p className="text-sm font-semibold text-text">{title}</p>
    {body && <div className="max-w-sm text-sm text-muted">{body}</div>}
    {action}
  </div>
);

export const Notice: React.FC<{ tone?: 'info' | 'warning'; children: React.ReactNode; className?: string }> = ({
  tone = 'info',
  children,
  className,
}) => (
  <div
    className={cn(
      'flex items-start gap-2 rounded-md border px-3 py-2 text-xs',
      tone === 'info' ? 'border-accent/25 bg-accent/5 text-text' : 'border-band-review/30 bg-band-review/10 text-text',
      className
    )}
  >
    <Info className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', tone === 'info' ? 'text-accent' : 'text-band-review')} aria-hidden />
    <div>{children}</div>
  </div>
);

export const Disclaimer: React.FC<{ className?: string }> = ({ className }) => (
  <p className={cn('text-xs italic text-muted', className)}>{REQUIRED_DISCLAIMER}</p>
);

/* ------------------------------------------------------------------ Reveal */

/** Fades content up once when it scrolls into view. Static under reduced motion. */
export const Reveal: React.FC<{ children: React.ReactNode; className?: string; delay?: number; as?: 'div' | 'section' | 'li' }> = ({
  children,
  className,
  delay = 0,
  as = 'div',
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '0px 0px -10% 0px' });
  const Comp = m[as] as typeof m.div;
  return (
    <Comp
      ref={ref}
      className={className}
      variants={{
        hidden: fadeUp.hidden,
        show: { ...fadeUp.show, transition: { ...fadeUp.show.transition, delay } },
      }}
      initial="hidden"
      animate={inView ? 'show' : 'hidden'}
    >
      {children}
    </Comp>
  );
};

export const SectionHeading: React.FC<{ eyebrow?: string; title: React.ReactNode; body?: React.ReactNode; id?: string; center?: boolean }> = ({
  eyebrow,
  title,
  body,
  id,
  center,
}) => (
  <Reveal className={cn('max-w-2xl', center && 'mx-auto text-center')}>
    {eyebrow && <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-accent">{eyebrow}</p>}
    <h2 id={id} className="text-3xl font-semibold tracking-tight text-text sm:text-4xl">
      {title}
    </h2>
    {body && <p className="mt-4 text-base leading-relaxed text-muted">{body}</p>}
  </Reveal>
);
