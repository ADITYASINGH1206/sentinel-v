import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { m } from 'framer-motion';
import { ArrowRight, ClipboardCheck, Inbox } from 'lucide-react';
import { BandChip } from '../../components/BandChip';
import { PageHeader, bandStripe, relativeTime } from '../../components/console/common';
import { Button, Card, DemoBadge, EmptyState, Kbd, Skeleton, cn } from '../../design/ui';
import { errorMessage, useReviewQueue } from '../../data/hooks';

const SLA_WARN_H = 4;
const SLA_BREACH_H = 24;

function slaTone(iso: string): string {
  const hours = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  if (hours >= SLA_BREACH_H) return 'text-band-manipulated';
  if (hours >= SLA_WARN_H) return 'text-band-review';
  return 'text-muted';
}

const ReviewQueue: React.FC = () => {
  const navigate = useNavigate();
  const q = useReviewQueue();
  const items = q.data?.data ?? [];

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if ((e.key === 'n' || e.key === 'N') && items[0]) navigate(`/app/review/${items[0].id}`);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [items, navigate]);

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Cases the policy routed to a person, oldest first."
        meta={q.data?.isDemo ? <DemoBadge /> : undefined}
        actions={
          <Button disabled={items.length === 0} onClick={() => items[0] && navigate(`/app/review/${items[0].id}`)}>
            <ClipboardCheck className="h-4 w-4" /> Claim next <Kbd className="ml-1 border-white/30 bg-white/15 text-current">N</Kbd>
          </Button>
        }
      />
      <Card className="overflow-hidden">
        {q.isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-12" />)}
          </div>
        ) : q.isError ? (
          <EmptyState title="Could not load the queue" body={errorMessage(q.error)} />
        ) : items.length === 0 ? (
          <EmptyState icon={<Inbox className="h-5 w-5" />} title="Queue is clear" body="Nothing is waiting for review right now." />
        ) : (
          <m.ul className="divide-y divide-border" initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.03 } } }}>
            {items.map((c, i) => (
              <m.li key={c.id} variants={i < 12 ? { hidden: { opacity: 0, y: 4 }, show: { opacity: 1, y: 0 } } : undefined}>
                <Link to={`/app/review/${c.id}`} className="group flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface-2">
                  <span className={cn('h-10 w-1 rounded-full', bandStripe[c.band ?? 'none'])} aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-sm text-text">{c.id}</p>
                    <p className="text-xs text-muted">
                      {c.tracks.length} {c.tracks.length === 1 ? 'face' : 'faces'} · {c.media ? `${c.media.durationS.toFixed(0)} s` : '—'} · {c.source}
                    </p>
                  </div>
                  <span className="hidden font-mono text-sm text-text sm:inline">{c.pBal != null ? c.pBal.toFixed(2) : '—'}</span>
                  {c.band && <BandChip band={c.band} size="sm" />}
                  <span className={cn('w-20 text-right text-xs', slaTone(c.createdAt))}>{relativeTime(c.createdAt)}</span>
                  <ArrowRight className="h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
              </m.li>
            ))}
          </m.ul>
        )}
      </Card>
      <p className="mt-3 text-xs text-muted">
        Ages turn amber after {SLA_WARN_H} h and red after {SLA_BREACH_H} h.
      </p>
    </>
  );
};

export default ReviewQueue;
