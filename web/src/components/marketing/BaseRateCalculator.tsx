import React, { useMemo, useState } from 'react';
import { m } from 'framer-motion';
import paperA from '../../content/sourced/paper_a_operating_points.json';
import { baseRate } from '../../utils/calibration';
import { Card, CountUp, Reveal, SectionHeading, cn } from '../../design/ui';

type ModelKey = keyof typeof paperA.models;
const MODELS = Object.keys(paperA.models) as ModelKey[];

// Log-scale slider: 0 → 0.1 %, 1000 → 20 %.
const MIN = Math.log(0.001);
const MAX = Math.log(0.2);
const toPrev = (s: number) => Math.exp(MIN + (s / 1000) * (MAX - MIN));
const toSlider = (p: number) => Math.round(((Math.log(p) - MIN) / (MAX - MIN)) * 1000);

const Segmented = <T extends string | number>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: Array<{ value: T; label: string; hint?: string }>;
  onChange: (v: T) => void;
  label: string;
}) => (
  <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-border bg-surface-2 p-1">
    {options.map((o) => (
      <button
        key={String(o.value)}
        type="button"
        role="radio"
        aria-checked={value === o.value}
        title={o.hint}
        onClick={() => onChange(o.value)}
        className={cn('relative rounded-[7px] px-3 py-1.5 text-xs font-medium transition-colors', value === o.value ? 'text-text' : 'text-muted hover:text-text')}
      >
        {value === o.value && <m.span layoutId={`seg-${label}`} className="absolute inset-0 rounded-[7px] bg-surface shadow-1" transition={{ duration: 0.2 }} />}
        <span className="relative">{o.label}</span>
      </button>
    ))}
  </div>
);

export const BaseRateCalculator: React.FC = () => {
  const [model, setModel] = useState<ModelKey>('Full');
  const [fpr, setFpr] = useState<0.01 | 0.05>(0.01);
  const [slider, setSlider] = useState(toSlider(0.01));
  const prevalence = toPrev(slider);
  const tpr = fpr === 0.01 ? paperA.models[model].fpr_1 : paperA.models[model].fpr_5;
  const r = useMemo(() => baseRate(tpr, fpr, prevalence), [tpr, fpr, prevalence]);
  const prevLabel = prevalence < 0.01 ? (prevalence * 100).toFixed(2) : (prevalence * 100).toFixed(1);

  return (
    <section id="base-rates" aria-labelledby="base-rates-title" className="scroll-mt-20 py-24">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 sm:px-6 lg:grid-cols-[1fr_1.15fr] lg:items-center">
        <SectionHeading
          id="base-rates-title"
          eyebrow="Why base rates matter"
          title="A good detector can still flag mostly authentic videos"
          body="Most videos people upload are genuine. Move the slider to see how the share of manipulated videos in your traffic changes what a flag actually means — using the S-MSDT paper's measured operating points."
        />
        <Reveal>
          <Card className="p-6">
            <div className="flex flex-wrap items-center gap-3">
              <Segmented
                label="Model"
                value={model}
                onChange={setModel}
                options={MODELS.map((k) => ({ value: k, label: paperA.models[k].label, hint: paperA.models[k].description }))}
              />
              <Segmented
                label="False-positive rate"
                value={fpr}
                onChange={setFpr}
                options={[
                  { value: 0.01 as const, label: '1% FPR' },
                  { value: 0.05 as const, label: '5% FPR' },
                ]}
              />
            </div>

            <div className="mt-6">
              <div className="mb-2 flex items-baseline justify-between">
                <label htmlFor="prevalence" className="text-sm font-medium text-text">
                  Share of manipulated videos in your traffic
                </label>
                <span className="font-mono text-sm font-semibold text-accent">{prevLabel}%</span>
              </div>
              <input
                id="prevalence"
                type="range"
                min={0}
                max={1000}
                value={slider}
                onChange={(e) => setSlider(Number(e.target.value))}
                className="range"
                aria-valuetext={`${prevLabel} percent`}
              />
              <div className="mt-1 flex justify-between font-mono text-[10px] text-muted">
                <span>0.1%</span>
                <span>1%</span>
                <span>20%</span>
              </div>
            </div>

            <dl className="mt-6 grid grid-cols-2 gap-3">
              <div className="col-span-2 rounded-md border border-accent/25 bg-accent/5 p-4">
                <dt className="text-xs text-muted">Of the videos flagged, manipulated</dt>
                <dd className="text-4xl font-semibold tabular-nums tracking-tight text-text">
                  <CountUp value={r.precision * 100} decimals={1} suffix="%" duration={0.35} />
                </dd>
              </div>
              <div className="rounded-md border border-border bg-surface-2 p-3">
                <dt className="text-xs text-muted">Flags per 10,000 videos</dt>
                <dd className="font-mono text-xl font-semibold text-text">
                  <CountUp value={r.flagsPer10k} duration={0.35} />
                </dd>
              </div>
              <div className="rounded-md border border-border bg-surface-2 p-3">
                <dt className="text-xs text-muted">Manipulated caught / missed</dt>
                <dd className="font-mono text-xl font-semibold text-text">
                  <CountUp value={r.caughtPer10k} duration={0.35} /> <span className="text-muted">/</span> <CountUp value={r.missedPer10k} duration={0.35} />
                </dd>
              </div>
            </dl>
            <p className="mt-4 text-[11px] leading-relaxed text-muted">
              Source: {paperA.source}. Operating point: TPR {(tpr * 100).toFixed(1)}% at {(fpr * 100).toFixed(0)}% FPR. Test-split numbers assume the
              false-positive rate holds on your traffic; your deployment's numbers come from the active model bundle.
            </p>
          </Card>
        </Reveal>
      </div>
    </section>
  );
};
