import React, { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { m } from 'framer-motion';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, ArrowRight, Clock, Eye, HelpCircle, ShieldAlert, UploadCloud } from 'lucide-react';
import { BandChip } from '../../components/BandChip';
import { PageHeader, bandStripe, relativeTime } from '../../components/console/common';
import { Button, Card, CardHeader, DemoBadge, Disclaimer, EmptyState, Skeleton, Stat, buttonVariants, cn } from '../../design/ui';
import { useThemeColors } from '../../design/useThemeColors';
import { usePreferences } from '../../design/preferences';
import { useCases, usePresets, useReviewQueue } from '../../data/hooks';

const DAYS = 7;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const cases = useCases();
  const queue = useReviewQueue();
  const presets = usePresets();
  const colors = useThemeColors();
  const { reduceMotion } = usePreferences();
  const list = cases.data?.data ?? [];
  const isDemo = Boolean(cases.data?.isDemo);

  const counts = useMemo(() => {
    const c = { total: list.length, review: 0, manipulated: 0, inconclusive: 0 };
    for (const x of list) {
      if (x.band === 'needs_review') c.review += 1;
      if (x.band === 'likely_manipulated') c.manipulated += 1;
      if (x.band === 'inconclusive') c.inconclusive += 1;
    }
    return c;
  }, [list]);

  const series = useMemo(() => {
    if (list.length === 0) return [];
    const latest = Math.max(...list.map((c) => new Date(c.createdAt).getTime()));
    const days = Array.from({ length: DAYS }, (_, i) => {
      const d = new Date(latest - (DAYS - 1 - i) * 86_400_000);
      return { key: d.toISOString().slice(0, 10), label: d.toLocaleDateString(undefined, { weekday: 'short' }), authentic: 0, review: 0, manipulated: 0, inconclusive: 0 };
    });
    for (const c of list) {
      const key = new Date(c.createdAt).toISOString().slice(0, 10);
      const day = days.find((d) => d.key === key);
      if (!day) continue;
      if (c.band === 'likely_authentic') day.authentic += 1;
      else if (c.band === 'needs_review') day.review += 1;
      else if (c.band === 'likely_manipulated') day.manipulated += 1;
      else if (c.band === 'inconclusive') day.inconclusive += 1;
    }
    return days;
  }, [list]);

  const backlog = (queue.data?.data ?? []).slice(0, 5);
  const preset = presets.data?.data['strict-low-fpr'];

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Screening activity, review backlog and the active policy."
        meta={isDemo ? <DemoBadge /> : undefined}
        actions={
          <>
            <Link to="/app/analyze" className={buttonVariants({ variant: 'secondary' })}>
              <UploadCloud className="h-4 w-4" /> Analyze a video
            </Link>
            <Button onClick={() => navigate(backlog[0] ? `/app/review/${backlog[0].id}` : '/app/review')}>
              Start reviewing <ArrowRight className="h-4 w-4" />
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cases.isLoading ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[74px]" />)
        ) : (
          <>
            <Stat label={isDemo ? 'Analyses (demo set)' : 'Analyses'} value={counts.total} icon={<Activity className="h-5 w-5" />} tone="accent" />
            <Stat label="Needs review" value={counts.review} icon={<Eye className="h-5 w-5" />} tone="review" />
            <Stat label="Likely manipulated" value={counts.manipulated} icon={<ShieldAlert className="h-5 w-5" />} tone="manipulated" />
            <Stat label="Inconclusive" value={counts.inconclusive} icon={<HelpCircle className="h-5 w-5" />} />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader title="Decisions by band" actions={<span className="text-xs text-muted">last {DAYS} days of data</span>} />
          <div className="h-64 p-4">
            {series.length === 0 ? (
              <EmptyState title="No analyses yet" body="Decisions appear here once videos are screened." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke={colors['--border']} strokeDasharray="2 4" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: colors['--muted'] }} tickLine={false} axisLine={{ stroke: colors['--border'] }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: colors['--muted'] }} tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ fill: colors['--border'], opacity: 0.3 }}
                    contentStyle={{ background: colors['--surface'], border: `1px solid ${colors['--border']}`, borderRadius: 8, fontSize: 12, color: colors['--text'] }}
                  />
                  <Bar dataKey="authentic" name="Likely authentic" stackId="a" fill={colors['--band-authentic']} isAnimationActive={!reduceMotion} />
                  <Bar dataKey="review" name="Needs review" stackId="a" fill={colors['--band-review']} isAnimationActive={!reduceMotion} />
                  <Bar dataKey="manipulated" name="Likely manipulated" stackId="a" fill={colors['--band-manipulated']} isAnimationActive={!reduceMotion} />
                  <Bar dataKey="inconclusive" name="Inconclusive" stackId="a" fill={colors['--band-inconclusive']} radius={[4, 4, 0, 0]} isAnimationActive={!reduceMotion} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Review backlog"
            icon={<Clock className="h-4 w-4" />}
            actions={
              <Link to="/app/review" className="text-xs font-medium text-accent hover:underline">
                Open queue
              </Link>
            }
          />
          {queue.isLoading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : backlog.length === 0 ? (
            <EmptyState title="Queue is clear" body="Nothing is waiting for review." />
          ) : (
            <ul className="divide-y divide-border">
              {backlog.map((c, i) => (
                <m.li key={c.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}>
                  <Link to={`/app/review/${c.id}`} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-2">
                    <span className={cn('h-8 w-1 rounded-full', bandStripe[c.band ?? 'none'])} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-xs text-text">{c.id}</p>
                      <p className="text-xs text-muted">{relativeTime(c.createdAt)}</p>
                    </div>
                    {c.band && <BandChip band={c.band} size="sm" />}
                  </Link>
                </m.li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Active policy" />
          <div className="space-y-3 p-4 text-sm">
            {preset ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Policy</span>
                  <span className="font-mono text-text">
                    {preset.policy_id} v{preset.version}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Cascade</span>
                  <span className="font-mono text-text">
                    {preset.stage1_variant} → {preset.stage2_variant}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Band boundaries (score)</span>
                  <span className="font-mono text-text">
                    {preset.thresholds.tau_authentic.toFixed(2)} / {preset.thresholds.tau_manipulated.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Configured prevalence</span>
                  <span className="font-mono text-text">{(preset.target_prevalence * 100).toFixed(0)}%</span>
                </div>
                <Link to="/app/policies" className="inline-flex items-center gap-1 pt-1 text-xs font-medium text-accent hover:underline">
                  Policies and simulator <ArrowRight className="h-3 w-3" />
                </Link>
              </>
            ) : (
              <Skeleton className="h-24" />
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Monitoring" />
          <div className="space-y-3 p-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted">Score drift (PSI)</span>
              <span className="text-muted">Needs live traffic</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Calibration on reviewed items</span>
              <span className="text-muted">Needs ≥ 200 expert reviews</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted">Most recent analysis</span>
              {list[0] ? (
                <Link to={`/app/cases/${list[0].id}`} className="font-mono text-xs text-accent hover:underline">
                  {list[0].id} · {relativeTime(list[0].createdAt)}
                </Link>
              ) : (
                <span className="text-muted">—</span>
              )}
            </div>
            <p className="pt-1 text-xs text-muted">Drift and calibration monitors only report numbers computed from your own traffic.</p>
          </div>
        </Card>
      </div>

      <Disclaimer className="mt-8 text-center" />
    </>
  );
};

export default Dashboard;
