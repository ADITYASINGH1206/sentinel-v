import React, { useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { ChevronDown, Cpu, FileCheck2, Film, Fingerprint, Layers, ShieldQuestion, TriangleAlert } from 'lucide-react';
import { BandChip } from '../BandChip';
import { ScoreReadout } from '../ScoreReadout';
import { Badge, Card, CardHeader, DemoBadge, Disclaimer, HashText, cn } from '../../design/ui';
import type { CaseView } from '../../data/types';
import type { PolicyPreset } from '../../data/types';

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
    <span className="text-muted">{label}</span>
    <span className="min-w-0 truncate text-right text-text">{children}</span>
  </div>
);

export const VerdictCard: React.FC<{ c: CaseView; preset?: PolicyPreset }> = ({ c, preset }) => {
  const decisive = c.tracks.find((t) => t.decisive);
  const stage = c.cascade ? (c.cascade.exitedEarly ? `${c.cascade.stage1Model} (stage 1, exited early)` : `${c.cascade.stage2Model ?? c.cascade.stage1Model} (stage 2)`) : '—';
  const tauLow = c.thresholds.tauAuthentic ?? preset?.thresholds.tau_authentic ?? null;
  const tauHigh = c.thresholds.tauManipulated ?? preset?.thresholds.tau_manipulated ?? null;
  return (
    <m.div layoutId={`verdict-${c.id}`}>
      <Card className="relative overflow-hidden p-6">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-accent via-violet to-accent opacity-70" aria-hidden />
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              {c.band ? <BandChip band={c.band} size="lg" pulse /> : <Badge>Status: {c.status}</Badge>}
              {c.isDemo && <DemoBadge />}
              {c.mockEngine && !c.isDemo && <Badge tone="warning">MOCK ENGINE</Badge>}
              {c.cacheHit && <Badge tone="accent">Reused result (same file, model and policy)</Badge>}
            </div>
            {c.pBal != null ? (
              <ScoreReadout p_bal={c.pBal} p_prior={c.pPrior ?? undefined} prior_prevalence={c.priorPrevalence} />
            ) : c.band === 'inconclusive' ? (
              <p className="text-sm text-text">
                No score: <span className="font-mono">{c.inconclusiveReason ?? 'INCONCLUSIVE'}</span>.{' '}
                {c.inconclusiveReason === 'NO_FACE' && 'No usable face was found in the sampled frames.'}
                {c.inconclusiveReason === 'TOO_FEW_FRAMES' && 'Fewer than 8 consecutive trackable frames were found.'}
              </p>
            ) : (
              <p className="text-sm text-muted">No score available.</p>
            )}
            <p className="text-xs text-muted">
              Decided by <span className="font-mono text-text">{stage}</span> · policy{' '}
              <span className="font-mono text-text">
                {c.policyId}
                {c.policyVersion != null && ` v${c.policyVersion}`}
              </span>
              {decisive && c.tracks.length > 0 && (
                <>
                  {' '}
                  · track {decisive.track_idx} of {c.tracks.length}
                </>
              )}
            </p>
          </div>
          <div className="grid min-w-[220px] gap-1 rounded-md border border-border bg-surface-2 p-3 text-xs">
            <p className="font-medium text-text">Band boundaries (score)</p>
            {tauLow != null && tauHigh != null ? (
              <div className="mt-1 flex items-center gap-1 font-mono">
                <span className="flex-1 rounded-l bg-band-authentic/15 px-2 py-1 text-band-authentic">&lt; {tauLow.toFixed(2)}</span>
                <span className="flex-1 bg-band-review/15 px-2 py-1 text-center text-band-review">review</span>
                <span className="flex-1 rounded-r bg-band-manipulated/15 px-2 py-1 text-right text-band-manipulated">≥ {tauHigh.toFixed(2)}</span>
              </div>
            ) : (
              <p className="text-muted">Not reported by the API for this policy.</p>
            )}
          </div>
        </div>
        <Disclaimer className="mt-5 border-t border-border pt-4" />
      </Card>
    </m.div>
  );
};

export const SignalsPanel: React.FC<{ c: CaseView }> = ({ c }) => {
  const c2pa = (c.signals.c2pa ?? null) as { present?: boolean; ai_disclosed?: boolean } | null;
  const gen = (c.signals.generative_image ?? null) as { enabled?: boolean; max?: number } | null;
  const meta = (c.signals.metadata ?? null) as { encoder?: string } | null;
  return (
    <Card>
      <CardHeader title="Signals" icon={<Layers className="h-4 w-4" />} />
      <div className="divide-y divide-border px-4">
        <Row label="Face manipulation">
          <span className="font-mono">{c.pBal != null ? c.pBal.toFixed(2) : '—'}</span>
        </Row>
        {c.cascade && (
          <Row label="Stage 1 score">
            <span className="font-mono">
              {c.cascade.stage1PBal != null ? c.cascade.stage1PBal.toFixed(2) : '—'} {c.cascade.exitedEarly ? '· exited early' : '→ escalated'}
            </span>
          </Row>
        )}
        <Row label="C2PA credentials">{c2pa ? (c2pa.present ? (c2pa.ai_disclosed ? 'Present · AI disclosed' : 'Present') : 'None found') : 'Not checked'}</Row>
        <Row label="Generative image">
          {gen?.enabled ? (
            <span className="font-mono">
              {gen.max?.toFixed(2) ?? '—'} <Badge tone="warning">experimental</Badge>
            </span>
          ) : (
            'Disabled'
          )}
        </Row>
        <Row label="Encoder">{meta?.encoder ?? '—'}</Row>
      </div>
    </Card>
  );
};

export const MediaPanel: React.FC<{ c: CaseView }> = ({ c }) => (
  <Card>
    <CardHeader title="Media" icon={<Film className="h-4 w-4" />} />
    <div className="divide-y divide-border px-4">
      <Row label="Resolution">{c.media ? `${c.media.width} × ${c.media.height}` : '—'}</Row>
      <Row label="Duration / fps">{c.media ? `${c.media.durationS.toFixed(1)} s · ${c.media.fps.toFixed(0)} fps` : '—'}</Row>
      <Row label="Codec">{c.media ? `${c.media.codec} / ${c.media.container}` : '—'}</Row>
      <Row label="SHA-256">{c.media?.sha256 ? <HashText value={c.media.sha256} /> : '—'}</Row>
    </div>
  </Card>
);

export const ReceiptPanel: React.FC<{ c: CaseView; onDownload: () => void; onVerify: () => void }> = ({ c, onDownload, onVerify }) => (
  <Card>
    <CardHeader title="Detection receipt" icon={<FileCheck2 className="h-4 w-4" />} />
    <div className="space-y-3 p-4 text-sm">
      {c.receiptId ? (
        <>
          <Row label="Receipt">
            <HashText value={c.receiptId} head={12} tail={4} />
          </Row>
          <Row label="Format">RFC 8785 JCS · Ed25519</Row>
          {c.isDemo && <p className="text-xs text-muted">Demo cases have no signed receipt. Use “Load sample receipt” on the verify page to try verification.</p>}
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onDownload} disabled={c.isDemo} className="inline-flex h-8 items-center rounded-md border border-border px-3 text-xs font-medium text-text transition-colors hover:bg-surface-2 disabled:opacity-50">
              Download JSON
            </button>
            <button type="button" onClick={onVerify} className="inline-flex h-8 items-center rounded-md bg-accent/10 px-3 text-xs font-medium text-accent transition-colors hover:bg-accent/15">
              Open in Verify
            </button>
          </div>
        </>
      ) : (
        <p className="text-muted">No receipt was issued for this analysis.</p>
      )}
    </div>
  </Card>
);

export const ModelPanel: React.FC<{ c: CaseView }> = ({ c }) => {
  const [open, setOpen] = useState(true);
  return (
    <Card>
      <CardHeader title="Model card" icon={<Cpu className="h-4 w-4" />} />
      <div className="divide-y divide-border px-4">
        {c.models.length === 0 ? (
          <Row label="Models">—</Row>
        ) : (
          c.models.map((mdl, i) => (
            <Row key={i} label={mdl.role ?? 'model'}>
              <span className="font-mono">{mdl.model_id}</span>
            </Row>
          ))
        )}
      </div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between border-t border-border px-4 py-3 text-sm font-medium text-text hover:bg-surface-2"
      >
        <span className="inline-flex items-center gap-2">
          <TriangleAlert className="h-4 w-4 text-band-review" aria-hidden /> Known limitations
        </span>
        <ChevronDown className={cn('h-4 w-4 text-muted transition-transform', open && 'rotate-180')} aria-hidden />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <m.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-1.5 overflow-hidden px-4 pb-4 text-xs text-muted"
          >
            <li>Not trained on fully generated (text-to-video) content.</li>
            <li>Calibration fitted on FF++ + DFD validation; it may not transfer to other sources.</li>
            <li>No audio. Lightly compressed (c23) training data only.</li>
          </m.ul>
        )}
      </AnimatePresence>
    </Card>
  );
};

export const TracksPanel: React.FC<{ c: CaseView; selected: number; onSelect: (i: number) => void }> = ({ c, selected, onSelect }) => (
  <Card>
    <CardHeader title="Face tracks" icon={<Fingerprint className="h-4 w-4" />} />
    {c.tracks.length === 0 ? (
      <div className="flex items-center gap-2 p-4 text-sm text-muted">
        <ShieldQuestion className="h-4 w-4" /> No face tracks.
      </div>
    ) : (
      <ul className="divide-y divide-border">
        {c.tracks.map((t) => (
          <li key={t.track_idx}>
            <button
              type="button"
              onClick={() => onSelect(t.track_idx)}
              aria-pressed={selected === t.track_idx}
              className={cn('flex w-full items-center justify-between px-4 py-2.5 text-sm transition-colors hover:bg-surface-2', selected === t.track_idx && 'bg-accent/5')}
            >
              <span className="font-mono text-text">
                #{t.track_idx} {t.decisive && <span className="text-band-review">★ decisive</span>}
              </span>
              <span className="font-mono text-muted">
                {t.p_bal.toFixed(2)} · {t.n_frames} frames
              </span>
            </button>
          </li>
        ))}
      </ul>
    )}
  </Card>
);
