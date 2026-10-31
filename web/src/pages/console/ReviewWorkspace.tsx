import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence, m } from 'framer-motion';
import { toast } from 'sonner';
import { ArrowLeft, Clock, HelpCircle, Keyboard, RotateCcw, Send, ShieldAlert, ShieldCheck, SkipForward, X } from 'lucide-react';
import { EvidencePlayer } from '../../components/EvidencePlayer';
import { ClipTimeline } from '../../components/ClipTimeline';
import { BandChip } from '../../components/BandChip';
import { ScoreReadout } from '../../components/ScoreReadout';
import { Button, Card, DemoBadge, Disclaimer, EmptyState, Kbd, Skeleton, cn } from '../../design/ui';
import { errorMessage, useCase, usePresets, useReviewQueue, useSubmitReview } from '../../data/hooks';
import type { ReviewDecision } from '../../data/types';

export const REASON_CODES = [
  { id: 'blending_seam', label: 'Blending seam or boundary artifact' },
  { id: 'mouth_teeth', label: 'Mouth, teeth or lip anomaly' },
  { id: 'temporal_flicker', label: 'Temporal flicker or jitter' },
  { id: 'lighting', label: 'Lighting or reflection mismatch' },
  { id: 'identity', label: 'Identity mismatch or warping' },
  { id: 'context_osint', label: 'Context / open-source evidence' },
  { id: 'low_quality', label: "Low quality — can't judge" },
  { id: 'other', label: 'Other visual cue' },
];

const DECISIONS: Array<{ value: ReviewDecision; label: string; key: string; icon: typeof ShieldCheck; tone: string }> = [
  { value: 'authentic', label: 'Authentic', key: '1', icon: ShieldCheck, tone: 'band-authentic' },
  { value: 'manipulated', label: 'Manipulated', key: '2', icon: ShieldAlert, tone: 'band-manipulated' },
  { value: 'cannot_tell', label: "Can't tell", key: '3', icon: HelpCircle, tone: 'band-inconclusive' },
];

const TONE: Record<string, string> = {
  'band-authentic': 'border-band-authentic bg-band-authentic/10 text-band-authentic ring-band-authentic/40',
  'band-manipulated': 'border-band-manipulated bg-band-manipulated/10 text-band-manipulated ring-band-manipulated/40',
  'band-inconclusive': 'border-band-inconclusive bg-band-inconclusive/10 text-text ring-band-inconclusive/40',
};

export const ReviewWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const q = useCase(id);
  const queue = useReviewQueue();
  const presets = usePresets();
  const submit = useSubmitReview();

  const [track, setTrack] = useState(0);
  const [time, setTime] = useState(0);
  const [seek, setSeek] = useState<number | undefined>();
  const [decision, setDecision] = useState<ReviewDecision | null>(null);
  const [reasons, setReasons] = useState<string[]>([]);
  const [confidence, setConfidence] = useState(3);
  const [notes, setNotes] = useState('');
  const [overlayToggles, setOverlayToggles] = useState(0);
  const [showKeys, setShowKeys] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const started = useRef(Date.now());

  useEffect(() => {
    started.current = Date.now();
    setDecision(null);
    setReasons([]);
    setNotes('');
    setConfidence(3);
    setOverlayToggles(0);
    setTrack(0);
    const t = window.setInterval(() => setElapsed(Math.floor((Date.now() - started.current) / 1000)), 1000);
    return () => window.clearInterval(t);
  }, [id]);

  const nextId = useMemo(() => {
    const items = queue.data?.data ?? [];
    const idx = items.findIndex((c) => c.id === id);
    const rest = items.filter((c) => c.id !== id);
    return rest[idx >= 0 ? Math.min(idx, rest.length - 1) : 0]?.id ?? null;
  }, [queue.data, id]);

  const goNext = useCallback(() => navigate(nextId ? `/app/review/${nextId}` : '/app/review'), [navigate, nextId]);

  const reset = useCallback(() => {
    setDecision(null);
    setReasons([]);
    setNotes('');
    setConfidence(3);
  }, []);

  const c = q.data;

  const onSubmit = useCallback(() => {
    if (!decision || !c || submit.isPending) return;
    submit.mutate(
      {
        analysisId: c.id,
        isDemo: c.isDemo,
        payload: {
          decision,
          reasons,
          notes: notes.trim() || null,
          confidence,
          telemetry: {
            time_to_decision_ms: Date.now() - started.current,
            overlay_toggles: overlayToggles,
            evidence_shown: true,
            score_shown: true,
          },
        },
      },
      {
        onSuccess: (res) => {
          toast.success(res.demo ? 'Demo: decision recorded locally (not sent to the API).' : `Review recorded · receipt ${res.receipt_id}`);
          goNext();
        },
        onError: (err) => {
          toast.error(`Review was not recorded: ${errorMessage(err)}`);
        },
      }
    );
  }, [decision, c, submit, reasons, notes, confidence, overlayToggles, goNext]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'textarea' || tag === 'input' || tag === 'select') return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const digit = /^Digit([1-5])$/.exec(e.code)?.[1];
      if (digit && e.shiftKey) {
        e.preventDefault();
        setConfidence(Number(digit));
        return;
      }
      if (digit && Number(digit) <= 3) {
        e.preventDefault();
        setDecision(DECISIONS[Number(digit) - 1].value);
      } else if (e.key === 'Enter') {
        if (tag === 'button' || tag === 'a') return; // let focused controls activate normally
        e.preventDefault();
        onSubmit();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        reset();
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        goNext();
      } else if (e.key === '?') {
        e.preventDefault();
        setShowKeys((v) => !v);
      } else if (e.key === 'Escape') {
        setShowKeys(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onSubmit, reset, goNext]);

  if (q.isLoading) {
    return (
      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]" aria-busy="true">
        <Skeleton className="aspect-video" />
        <Skeleton className="h-[480px]" />
      </div>
    );
  }
  if (q.isError || !c) {
    return (
      <Card>
        <EmptyState title="Could not open this case" body={errorMessage(q.error)} action={<Link to="/app/review" className="text-sm text-accent hover:underline">Back to queue</Link>} />
      </Card>
    );
  }

  const preset = presets.data?.data[c.policyId];
  const tauHigh = c.thresholds.tauManipulated ?? preset?.thresholds.tau_manipulated ?? null;
  const tauLow = c.thresholds.tauAuthentic ?? preset?.thresholds.tau_authentic ?? null;

  return (
    <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <Link to="/app/review" className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text" aria-label="Back to queue">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <h1 className="truncate font-mono text-lg font-semibold text-text">{c.id}</h1>
          {c.band && <BandChip band={c.band} size="sm" />}
          {c.isDemo && <DemoBadge />}
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          <span className="inline-flex items-center gap-1 font-mono">
            <Clock className="h-3.5 w-3.5" /> {elapsed}s
          </span>
          <span>
            Policy <code className="text-text">{c.policyId}</code>
          </span>
          <button type="button" onClick={() => setShowKeys(true)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-surface-2 hover:text-text">
            <Keyboard className="h-3.5 w-3.5" /> Shortcuts <Kbd>?</Kbd>
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <section className="flex min-w-0 flex-col gap-4" aria-label="Evidence">
          <EvidencePlayer
            videoUrl={c.videoUrl}
            videoSources={c.videoSources}
            initialDuration={c.media?.durationS}
            isImage={Boolean(c.isImage || (c.media?.container && ['jpg', 'jpeg', 'png', 'webp', 'bmp'].includes(c.media.container.toLowerCase())))}
            tracks={c.tracks}
            selectedTrackIdx={track}
            onSelectTrack={setTrack}
            onTimeUpdate={setTime}
            seekTime={seek}
            onOverlayToggled={() => setOverlayToggles((n) => n + 1)}
            fps={c.media?.fps ?? 30}
            demo={c.isDemo}
          />
          {!c.isImage && !['jpg', 'jpeg', 'png', 'webp', 'bmp'].includes(c.media?.container?.toLowerCase() ?? '') && (
            <ClipTimeline
              tracks={c.tracks}
              selectedTrackIdx={track}
              currentTime={time}
              duration={c.media?.durationS ?? 0}
              tau={tauHigh}
              tauLow={tauLow}
              fps={c.media?.fps ?? 30}
              onSeek={(t) => setSeek((prev) => (prev === t ? t + 1e-6 : t))}
            />
          )}
          <Card className="p-4">
            {c.pBal != null ? <ScoreReadout p_bal={c.pBal} p_prior={c.pPrior ?? undefined} prior_prevalence={c.priorPrevalence} size="md" /> : <p className="text-sm text-muted">No score.</p>}
          </Card>
        </section>

        <section aria-label="Decision" className="flex flex-col gap-4">
          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-text">Reviewer decision</h2>
              <span className="font-mono text-xs text-muted">1 · 2 · 3</span>
            </div>
            <div className="grid gap-2" role="radiogroup" aria-label="Decision">
              {DECISIONS.map((d) => {
                const active = decision === d.value;
                return (
                  <button
                    key={d.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setDecision(d.value)}
                    className={cn(
                      'relative flex items-center justify-between rounded-md border px-3.5 py-3 text-sm font-medium transition-all duration-150',
                      active ? `${TONE[d.tone]} ring-2` : 'border-border text-text hover:border-accent/40 hover:bg-surface-2'
                    )}
                  >
                    <span className="flex items-center gap-2.5">
                      <d.icon className="h-4 w-4" aria-hidden />
                      {d.label}
                    </span>
                    <Kbd>{d.key}</Kbd>
                  </button>
                );
              })}
            </div>

            <fieldset className="mt-5">
              <legend className="mb-2 text-xs font-medium text-muted">Confidence (Shift + 1–5)</legend>
              <div className="flex gap-1.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setConfidence(n)}
                    aria-pressed={confidence === n}
                    aria-label={`Confidence ${n} of 5`}
                    className={cn(
                      'h-8 flex-1 rounded-md border font-mono text-xs transition-colors',
                      confidence === n ? 'border-accent bg-accent text-accent-contrast' : 'border-border text-muted hover:bg-surface-2'
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset className="mt-5">
              <legend className="mb-2 text-xs font-medium text-muted">Reasons</legend>
              <div className="flex flex-wrap gap-1.5">
                {REASON_CODES.map((r) => {
                  const on = reasons.includes(r.id);
                  return (
                    <button
                      key={r.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setReasons((prev) => (on ? prev.filter((x) => x !== r.id) : [...prev, r.id]))}
                      className={cn(
                        'rounded-full border px-2.5 py-1 text-xs transition-colors',
                        on ? 'border-accent bg-accent/10 text-accent' : 'border-border text-muted hover:border-accent/40 hover:text-text'
                      )}
                    >
                      {r.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <label className="mt-5 block">
              <span className="mb-1.5 block text-xs font-medium text-muted">Notes (optional)</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="e.g. mouth texture flickers between 7 s and 11 s"
                className="w-full resize-none rounded-md border border-border bg-bg p-2.5 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </label>

            <Button className="mt-5 w-full" size="lg" disabled={!decision || submit.isPending} onClick={onSubmit}>
              <Send className="h-4 w-4" /> {submit.isPending ? 'Submitting…' : 'Submit & next'} <Kbd className="ml-1 border-white/30 bg-white/15 text-current">⏎</Kbd>
            </Button>
            <div className="mt-3 flex items-center justify-between text-xs text-muted">
              <button type="button" onClick={reset} className="inline-flex items-center gap-1 hover:text-text">
                <RotateCcw className="h-3 w-3" /> Reset <Kbd>R</Kbd>
              </button>
              <button type="button" onClick={goNext} className="inline-flex items-center gap-1 hover:text-text">
                <SkipForward className="h-3 w-3" /> Skip <Kbd>S</Kbd>
              </button>
            </div>
            <Disclaimer className="mt-4 border-t border-border pt-4 text-center" />
          </Card>
        </section>
      </div>

      <AnimatePresence>
        {showKeys && (
          <m.div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowKeys(false)}>
            <m.div
              role="dialog"
              aria-modal="true"
              aria-label="Keyboard shortcuts"
              initial={{ opacity: 0, scale: 0.98, y: 6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.16 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-2"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-text">Keyboard shortcuts</h2>
                <button className="grid h-8 w-8 place-items-center rounded-md hover:bg-surface-2" onClick={() => setShowKeys(false)} aria-label="Close">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
                {[
                  ['1 / 2 / 3', 'Authentic / Manipulated / Can’t tell'],
                  ['Shift + 1–5', 'Confidence'],
                  ['Enter', 'Submit and open next'],
                  ['S', 'Skip'],
                  ['R', 'Reset form'],
                  ['Space', 'Play / pause'],
                  ['← / →', 'Step one frame'],
                  ['P', 'Jump to peak clip'],
                  ['H', 'Toggle overlay'],
                  ['?', 'Show this sheet'],
                ].map(([k, v]) => (
                  <React.Fragment key={k}>
                    <dt>
                      <Kbd>{k}</Kbd>
                    </dt>
                    <dd className="text-muted">{v}</dd>
                  </React.Fragment>
                ))}
              </dl>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ReviewWorkspace;
