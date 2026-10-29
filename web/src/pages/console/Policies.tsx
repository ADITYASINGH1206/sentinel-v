import React, { useState } from 'react';
import { m } from 'framer-motion';
import { Calculator, SlidersHorizontal } from 'lucide-react';
import { PageHeader } from '../../components/console/common';
import { Badge, Card, CardHeader, CountUp, DemoBadge, EmptyState, Skeleton, cn } from '../../design/ui';
import { errorMessage, usePresets, useSimulation, type ModelKey } from '../../data/hooks';
import paperA from '../../content/sourced/paper_a_operating_points.json';

const MIN = Math.log(0.001);
const MAX = Math.log(0.2);
const toPrev = (s: number) => Math.exp(MIN + (s / 1000) * (MAX - MIN));
const toSlider = (p: number) => Math.round(((Math.log(p) - MIN) / (MAX - MIN)) * 1000);

const BandBar: React.FC<{ low: number; high: number }> = ({ low, high }) => (
  <div className="relative mt-2 h-3 overflow-hidden rounded-full bg-surface-2" aria-label={`Bands: authentic below ${low}, manipulated at or above ${high}`}>
    <m.div className="absolute inset-y-0 left-0 bg-band-authentic/70" initial={{ width: 0 }} animate={{ width: `${low * 100}%` }} transition={{ duration: 0.4 }} />
    <m.div className="absolute inset-y-0 bg-band-review/70" style={{ left: `${low * 100}%` }} initial={{ width: 0 }} animate={{ width: `${(high - low) * 100}%` }} transition={{ duration: 0.4, delay: 0.05 }} />
    <m.div className="absolute inset-y-0 right-0 bg-band-manipulated/70" initial={{ width: 0 }} animate={{ width: `${(1 - high) * 100}%` }} transition={{ duration: 0.4, delay: 0.1 }} />
  </div>
);

const Policies: React.FC = () => {
  const presets = usePresets();
  const [selected, setSelected] = useState('strict-low-fpr');
  const [model, setModel] = useState<ModelKey>('ST');
  const [fpr, setFpr] = useState<0.01 | 0.05>(0.01);
  const [slider, setSlider] = useState(toSlider(0.01));
  const [volume, setVolume] = useState(10_000);
  const prevalence = toPrev(slider);
  const sim = useSimulation(model, fpr, prevalence, volume);
  const list = Object.values(presets.data?.data ?? {});
  const active = presets.data?.data[selected];

  return (
    <>
      <PageHeader
        title="Policies"
        description="Decision bands, cascade settings and a simulator for what a threshold means at your traffic's base rate."
        meta={presets.data?.isDemo ? <DemoBadge /> : undefined}
      />

      <div className="grid gap-4 md:grid-cols-3">
        {presets.isLoading
          ? Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-40" />)
          : presets.isError
            ? <Card className="md:col-span-3"><EmptyState title="Could not load policies" body={errorMessage(presets.error)} /></Card>
            : list.map((p) => (
                <button key={p.policy_id} type="button" onClick={() => setSelected(p.policy_id)} className="text-left" aria-pressed={selected === p.policy_id}>
                  <Card interactive className={cn('h-full p-5', selected === p.policy_id && 'border-accent/60 shadow-glow')}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-mono text-xs text-muted">{p.policy_id}</p>
                      <Badge tone={selected === p.policy_id ? 'accent' : 'neutral'}>v{p.version}</Badge>
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-text">{p.name}</h3>
                    <p className="mt-1 line-clamp-2 text-xs text-muted">{p.description}</p>
                    <BandBar low={p.thresholds.tau_authentic} high={p.thresholds.tau_manipulated} />
                    <div className="mt-1.5 flex justify-between font-mono text-[10px] text-muted">
                      <span>{p.thresholds.tau_authentic.toFixed(2)}</span>
                      <span>{p.thresholds.tau_manipulated.toFixed(2)}</span>
                    </div>
                  </Card>
                </button>
              ))}
      </div>

      {active && (
        <Card className="mt-6">
          <CardHeader title={`${active.name} · details`} icon={<SlidersHorizontal className="h-4 w-4" />} />
          <dl className="grid gap-x-8 gap-y-3 p-5 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {[
              ['Stage 1 model', active.stage1_variant],
              ['Stage 2 model', active.stage2_variant],
              ['Cascade', active.cascade_enabled ? `on · exit below ${active.exit_below_p_bal.toFixed(2)}` : 'off'],
              ['Configured prevalence', `${(active.target_prevalence * 100).toFixed(0)}%`],
              ['Audit sample rate', `${(active.audit_sample_rate * 100).toFixed(0)}% of “likely authentic”`],
              ['Band boundaries', `${active.thresholds.tau_authentic.toFixed(2)} / ${active.thresholds.tau_manipulated.toFixed(2)}`],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-4 border-b border-border pb-2">
                <dt className="text-muted">{k}</dt>
                <dd className="font-mono text-text">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="px-5 pb-5 text-xs text-muted">Policy editing and activation need the admin API; presets are read-only here.</p>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader
          title="Policy simulator"
          icon={<Calculator className="h-4 w-4" />}
          actions={sim.data && <Badge tone={sim.data.computedBy === 'api' ? 'success' : 'warning'}>{sim.data.computedBy === 'api' ? 'computed by API' : 'computed in browser'}</Badge>}
        />
        <div className="grid gap-6 p-5 lg:grid-cols-[1fr_1.2fr]">
          <div className="space-y-5 text-sm">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Model</span>
              <select value={model} onChange={(e) => setModel(e.target.value as ModelKey)} className="h-9 w-full rounded-md border border-border bg-bg px-3 text-text focus:border-accent focus:outline-none">
                {(Object.keys(paperA.models) as ModelKey[]).map((k) => (
                  <option key={k} value={k}>
                    {paperA.models[k].label} — {paperA.models[k].description}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <span className="mb-1.5 block text-xs font-medium text-muted">Operating point</span>
              <div className="grid grid-cols-2 gap-2">
                {([0.01, 0.05] as const).map((v) => (
                  <button key={v} type="button" onClick={() => setFpr(v)} aria-pressed={fpr === v} className={cn('h-9 rounded-md border text-xs font-medium transition-colors', fpr === v ? 'border-accent bg-accent/10 text-accent' : 'border-border text-muted hover:bg-surface-2')}>
                    {(v * 100).toFixed(0)}% false-positive rate
                  </button>
                ))}
              </div>
            </div>
            <label className="block">
              <span className="mb-1.5 flex justify-between text-xs font-medium text-muted">
                Prevalence <span className="font-mono text-accent">{(prevalence * 100).toFixed(prevalence < 0.01 ? 2 : 1)}%</span>
              </span>
              <input type="range" min={0} max={1000} value={slider} onChange={(e) => setSlider(Number(e.target.value))} className="range" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Videos per day</span>
              <input type="number" min={1} step={1000} value={volume} onChange={(e) => setVolume(Math.max(1, Number(e.target.value) || 1))} className="h-9 w-full rounded-md border border-border bg-bg px-3 font-mono text-text focus:border-accent focus:outline-none" />
            </label>
          </div>
          <div>
            {sim.isError ? (
              <EmptyState title="Simulation failed" body={errorMessage(sim.error)} />
            ) : !sim.data ? (
              <Skeleton className="h-48" />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-accent/25 bg-accent/5 p-4 sm:col-span-2">
                  <p className="text-xs text-muted">Precision of flags</p>
                  <p className="text-3xl font-semibold tabular-nums tracking-tight text-text">
                    <CountUp value={sim.data.precision * 100} decimals={1} suffix="%" duration={0.3} />
                  </p>
                </div>
                {[
                  ['Flags per day', sim.data.daily.flags],
                  ['Manipulated caught per day', sim.data.daily.caught],
                  ['False alarms per day', sim.data.daily.falseAlarms],
                  ['Missed per day', sim.data.daily.missed],
                ].map(([k, v]) => (
                  <div key={k as string} className="rounded-md border border-border bg-surface-2 p-3">
                    <p className="text-xs text-muted">{k}</p>
                    <p className="font-mono text-xl font-semibold text-text">
                      <CountUp value={Number(v)} duration={0.3} />
                    </p>
                  </div>
                ))}
                {sim.data.daily.reviewHours != null && (
                  <p className="text-xs text-muted sm:col-span-2">Estimated review time: {sim.data.daily.reviewHours.toFixed(1)} h per day.</p>
                )}
              </div>
            )}
            <p className="mt-3 text-[11px] text-muted">Operating points: {paperA.source}. They assume the false-positive rate holds on your traffic.</p>
          </div>
        </div>
      </Card>
    </>
  );
};

export default Policies;
