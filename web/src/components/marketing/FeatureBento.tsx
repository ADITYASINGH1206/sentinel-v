import React from 'react';
import { m } from 'framer-motion';
import { Gauge, Grid3x3, GitBranch, FileSignature, Keyboard, Plug } from 'lucide-react';
import { Card, Kbd, Reveal, SectionHeading, cn } from '../../design/ui';
import { demoHeat, magmaCss, HEAT_ALPHA_FLOOR } from '../../utils/heat';
import { platt, priorCorrect } from '../../utils/calibration';
import hero from '../../content/sourced/hero_illustration.json';

const HERO_P = platt(hero.u);
const HERO_PRIOR = priorCorrect(HERO_P, hero.prior_prevalence);

const MiniGrid: React.FC = () => (
  <div className="grid w-full max-w-[168px] grid-cols-8 gap-0.5 rounded-sm bg-[#070B12] p-2" aria-hidden>
    {Array.from({ length: 64 }, (_, i) => {
      const gx = (i % 8) * 2;
      const gy = Math.floor(i / 8) * 2;
      const v = demoHeat(gx, gy, 5);
      return (
        <span
          key={i}
          className="aspect-square rounded-[2px] transition-[transform,opacity] duration-300 group-hover:scale-105"
          style={{ background: v >= HEAT_ALPHA_FLOOR ? magmaCss(v) : '#111a29', transitionDelay: `${(gy / 2) * 30}ms` }}
        />
      );
    })}
  </div>
);

const CascadeDiagram: React.FC = () => (
  <svg viewBox="0 0 220 70" className="h-16 w-full" aria-hidden>
    <rect x="4" y="18" width="60" height="34" rx="6" fill="rgb(var(--surface-2))" stroke="rgb(var(--border))" />
    <text x="34" y="39" textAnchor="middle" fontSize="11" fill="rgb(var(--text))" fontFamily="JetBrains Mono, monospace">S</text>
    <rect x="152" y="18" width="62" height="34" rx="6" fill="rgb(var(--accent) / 0.12)" stroke="rgb(var(--accent) / 0.5)" />
    <text x="183" y="39" textAnchor="middle" fontSize="11" fill="rgb(var(--accent))" fontFamily="JetBrains Mono, monospace">ST</text>
    <path d="M64 35H152" stroke="rgb(var(--border))" strokeWidth="2" />
    <path d="M64 35c30 0 30 26 60 26" stroke="rgb(var(--band-authentic) / 0.6)" strokeWidth="2" fill="none" strokeDasharray="3 3" />
    <text x="128" y="66" fontSize="9" fill="rgb(var(--band-authentic))" fontFamily="Inter, sans-serif">exit early</text>
    <circle r="3.5" fill="rgb(var(--accent))" className="smil-dot opacity-0 transition-opacity duration-200 group-hover:opacity-100">
      <animateMotion dur="1.4s" repeatCount="indefinite" path="M64 35H152" />
    </circle>
  </svg>
);

const TypingHash: React.FC = () => (
  <div className="space-y-1 font-mono text-[11px] text-muted" aria-hidden>
    {['content  a3f9…c21e', 'weights  4c1e…9b07', 'policy   strict-low-fpr v1'].map((l, i) => (
      <m.p
        key={l}
        initial={{ opacity: 0, x: -6 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.15 * i, duration: 0.3 }}
        className="truncate"
      >
        {l}
      </m.p>
    ))}
  </div>
);

const Keys: React.FC = () => (
  <div className="flex items-center gap-1.5" aria-hidden>
    {['1', '2', '3', '⏎'].map((k, i) => (
      <span key={k} className="inline-block transition-transform duration-150 group-hover:translate-y-0.5" style={{ transitionDelay: `${i * 80}ms` }}>
        <Kbd className="h-7 min-w-[1.75rem] text-xs">{k}</Kbd>
      </span>
    ))}
  </div>
);

const FEATURES = [
  {
    icon: Gauge,
    title: 'Calibrated scores',
    body: 'Scores are calibrated on held-out validation data, then re-weighted for the share of manipulated videos you actually expect.',
    visual: (
      <div className="rounded-sm border border-border bg-surface-2 p-3">
        <p className="font-mono text-lg font-semibold text-text">Score {HERO_P.toFixed(2)}</p>
        <p className="text-xs text-muted">≈ {(HERO_PRIOR * 100).toFixed(1)}% at {(hero.prior_prevalence * 100).toFixed(0)}% prevalence</p>
        <p className="mt-2 font-mono text-[11px] text-accent">logit(p_π) = logit(p_bal) + log(π/(1−π))</p>
        <div className="mt-3 flex h-2 overflow-hidden rounded-full" aria-hidden>
          <span className="w-[30%] bg-band-authentic/70 transition-[width] duration-500 group-hover:w-[26%]" />
          <span className="flex-1 bg-band-review/70" />
          <span className="w-[25%] bg-band-manipulated/70 transition-[width] duration-500 group-hover:w-[29%]" />
        </div>
        <p className="mt-1.5 text-[11px] text-muted">Band boundaries come from your policy, snapped to validation operating points.</p>
      </div>
    ),
    className: 'lg:col-span-2',
  },
  { icon: Grid3x3, title: 'Evidence maps', body: 'Patch-level evidence is mapped back onto the original frames, so reviewers see where the model looked.', visual: <MiniGrid /> },
  { icon: GitBranch, title: 'Two-stage cascade', body: 'A cheap single-frame screen handles clear cases; only uncertain faces reach the temporal model.', visual: <CascadeDiagram /> },
  { icon: FileSignature, title: 'Verifiable receipts', body: 'Every decision is a signed, canonical record. Verification runs in the browser, without trusting the operator.', visual: <TypingHash /> },
  { icon: Keyboard, title: 'Reviewer workspace', body: 'Keyboard-first triage with evidence, timelines and reason codes. Decisions issue superseding receipts.', visual: <Keys /> },
  {
    icon: Plug,
    title: 'Works with SENTINEL',
    body: 'An additive adapter adds video screening to the SENTINEL verification hub without touching its locked code.',
    visual: (
      <div className="flex items-center gap-2 text-xs" aria-hidden>
        <span className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono">SENTINEL</span>
        <span className="h-px flex-1 bg-gradient-to-r from-border via-accent to-border" />
        <span className="rounded-md border border-accent/40 bg-accent/10 px-2 py-1 font-mono text-accent">/compat</span>
      </div>
    ),
    className: 'lg:col-span-2',
  },
];

export const FeatureBento: React.FC = () => (
  <section id="features" aria-labelledby="features-title" className="scroll-mt-20 border-y border-border bg-surface/50 py-24">
    <div className="mx-auto max-w-6xl px-4 sm:px-6">
      <SectionHeading id="features-title" eyebrow="Features" title="Built for accountable decisions, not just high scores" />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f, i) => (
          <Reveal key={f.title} delay={i * 0.05} className={cn('h-full', f.className)}>
            <Card interactive className="group flex h-full flex-col gap-4 p-5">
              <div className="flex items-center gap-2.5">
                <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/10 text-accent">
                  <f.icon className="h-4 w-4" aria-hidden />
                </span>
                <h3 className="text-sm font-semibold text-text">{f.title}</h3>
              </div>
              <p className="text-sm leading-relaxed text-muted">{f.body}</p>
              <div className="mt-auto">{f.visual}</div>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  </section>
);
