import React, { useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { m } from 'framer-motion';
import { Download, FileSearch, Search, UploadCloud } from 'lucide-react';
import { BandChip, type DecisionBand } from '../../components/BandChip';
import { PageHeader, StatusPill, bandStripe, formatDateTime, relativeTime } from '../../components/console/common';
import { Card, DemoBadge, EmptyState, Skeleton, buttonVariants, cn } from '../../design/ui';
import { useCases } from '../../data/hooks';
import { errorMessage } from '../../data/hooks';
import type { CaseSummary } from '../../data/types';

const BAND_FILTERS: Array<{ value: 'all' | DecisionBand; label: string }> = [
  { value: 'all', label: 'All bands' },
  { value: 'needs_review', label: 'Needs review' },
  { value: 'likely_manipulated', label: 'Likely manipulated' },
  { value: 'likely_authentic', label: 'Likely authentic' },
  { value: 'inconclusive', label: 'Inconclusive' },
];

const SOURCE_LABEL: Record<string, string> = { upload: 'Upload', api: 'API', sentinel: 'SENTINEL' };

function toCsv(rows: CaseSummary[]): string {
  const header = ['id', 'created_at', 'band', 'score', 'faces', 'duration_s', 'source', 'review_status', 'policy', 'demo'];
  const lines = rows.map((r) => [r.id, r.createdAt, r.band ?? '', r.pBal?.toFixed(2) ?? '', r.faces, r.durationS ?? '', r.source, r.reviewStatus, r.policyId, r.isDemo].join(','));
  return [header.join(','), ...lines].join('\n');
}

const Cases: React.FC = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const band = (params.get('band') ?? 'all') as 'all' | DecisionBand;
  const q = params.get('q') ?? '';
  const source = params.get('source') ?? 'all';
  const cases = useCases();

  const rows = useMemo(() => {
    const all = cases.data?.data ?? [];
    return all.filter((c) => (band === 'all' || c.band === band) && (source === 'all' || c.source === source) && (!q || c.id.toLowerCase().includes(q.toLowerCase())));
  }, [cases.data, band, q, source]);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (!value || value === 'all') next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  const exportCsv = () => {
    const blob = new Blob([toCsv(rows)], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'veriframe-cases.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageHeader
        title="Cases"
        description="Every analysis with its decision band, calibrated score and review status."
        meta={cases.data?.isDemo ? <DemoBadge /> : undefined}
        actions={
          <>
            <button type="button" onClick={exportCsv} className={buttonVariants({ variant: 'secondary' })} disabled={rows.length === 0}>
              <Download className="h-4 w-4" /> Export CSV
            </button>
            <Link to="/app/analyze" className={buttonVariants()}>
              <UploadCloud className="h-4 w-4" /> Analyze
            </Link>
          </>
        }
      />

      <Card className="mb-4 flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" aria-hidden />
          <input
            type="search"
            value={q}
            onChange={(e) => setParam('q', e.target.value)}
            placeholder="Search by analysis id…"
            aria-label="Search by analysis id"
            className="h-9 w-full rounded-md border border-border bg-bg pl-9 pr-3 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>
        <select
          value={band}
          onChange={(e) => setParam('band', e.target.value)}
          aria-label="Filter by decision band"
          className="h-9 rounded-md border border-border bg-bg px-3 text-sm text-text focus:border-accent focus:outline-none"
        >
          {BAND_FILTERS.map((b) => (
            <option key={b.value} value={b.value}>
              {b.label}
            </option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => setParam('source', e.target.value)}
          aria-label="Filter by source"
          className="h-9 rounded-md border border-border bg-bg px-3 text-sm text-text focus:border-accent focus:outline-none"
        >
          <option value="all">All sources</option>
          <option value="upload">Upload</option>
          <option value="api">API</option>
          <option value="sentinel">SENTINEL</option>
        </select>
      </Card>

      <Card className="overflow-hidden">
        {cases.isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-10" />)}
          </div>
        ) : cases.isError ? (
          <EmptyState icon={<FileSearch className="h-5 w-5" />} title="Could not load cases" body={errorMessage(cases.error)} />
        ) : rows.length === 0 ? (
          <EmptyState icon={<FileSearch className="h-5 w-5" />} title="No cases match these filters" body="Clear the search or choose another band." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="w-1 p-0" aria-label="Band" />
                  <th className="px-4 py-2.5 font-medium">Analysis</th>
                  <th className="px-4 py-2.5 font-medium">Received</th>
                  <th className="px-4 py-2.5 font-medium">Band</th>
                  <th className="px-4 py-2.5 font-medium">Score</th>
                  <th className="px-4 py-2.5 font-medium">Faces</th>
                  <th className="px-4 py-2.5 font-medium">Duration</th>
                  <th className="px-4 py-2.5 font-medium">Source</th>
                  <th className="px-4 py-2.5 font-medium">Review</th>
                </tr>
              </thead>
              <m.tbody className="divide-y divide-border" initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.025 } } }}>
                {rows.map((c, i) => (
                  <m.tr
                    key={c.id}
                    variants={i < 12 ? { hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } } : undefined}
                    tabIndex={0}
                    onClick={() => navigate(`/app/cases/${c.id}`)}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/app/cases/${c.id}`)}
                    className="cursor-pointer transition-colors hover:bg-surface-2 focus:bg-surface-2 focus:outline-none"
                  >
                    <td className="p-0">
                      <span className={cn('block h-10 w-1', bandStripe[c.band ?? 'none'])} aria-hidden />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-text">{c.id}</td>
                    <td className="px-4 py-2.5 text-muted" title={formatDateTime(c.createdAt)}>
                      {relativeTime(c.createdAt)}
                    </td>
                    <td className="px-4 py-2.5">{c.band ? <BandChip band={c.band} size="sm" /> : <StatusPill status={c.status} />}</td>
                    <td className="px-4 py-2.5 font-mono text-text">{c.pBal != null ? c.pBal.toFixed(2) : '—'}</td>
                    <td className="px-4 py-2.5 font-mono text-muted">{c.faces}</td>
                    <td className="px-4 py-2.5 font-mono text-muted">{c.isImage ? <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] font-sans font-medium text-accent">Image</span> : (c.durationS != null ? `${c.durationS.toFixed(0)} s` : '—')}</td>
                    <td className="px-4 py-2.5 text-muted">{SOURCE_LABEL[c.source] ?? c.source}</td>
                    <td className="px-4 py-2.5">
                      <StatusPill status={c.reviewStatus} />
                    </td>
                  </m.tr>
                ))}
              </m.tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="mt-3 text-xs text-muted">
        {rows.length} {rows.length === 1 ? 'case' : 'cases'} · filters are saved in the URL so views can be shared.
      </p>
    </>
  );
};

export default Cases;
