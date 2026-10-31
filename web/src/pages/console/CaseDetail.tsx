import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { AlertTriangle, ArrowLeft, ClipboardCheck, FileDown, FileSearch, RefreshCw, Sparkles } from 'lucide-react';
import { EvidencePlayer } from '../../components/EvidencePlayer';
import { ClipTimeline } from '../../components/ClipTimeline';
import { KeyframeTimeline } from '../../components/KeyframeTimeline';
import { StageProgress } from '../../components/StageProgress';
import { MediaPanel, ModelPanel, ReceiptPanel, SignalsPanel, TracksPanel, VerdictCard } from '../../components/console/CaseParts';
import { PageHeader, formatDateTime } from '../../components/console/common';
import { Card, EmptyState, Skeleton, buttonVariants, cn } from '../../design/ui';
import { errorMessage, useCase, usePresets } from '../../data/hooks';
import { api, ApiError } from '../../data/api';

const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const q = useCase(id);
  const presets = usePresets();
  const [track, setTrack] = useState(0);
  const [time, setTime] = useState(0);
  const [seek, setSeek] = useState<number | undefined>();

  if (q.isLoading) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-40" />
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <Skeleton className="aspect-video" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (q.isError || !q.data) {
    const notFound = q.error instanceof ApiError && q.error.status === 404;
    return (
      <Card>
        <EmptyState
          icon={<FileSearch className="h-5 w-5" />}
          title={notFound ? 'Analysis not found' : 'Could not load this analysis'}
          body={notFound ? `No analysis with id ${id} exists on this server.` : errorMessage(q.error)}
          action={
            <Link to="/app/cases" className={buttonVariants({ variant: 'secondary' })}>
              Back to cases
            </Link>
          }
        />
      </Card>
    );
  }

  const c = q.data;
  const preset = presets.data?.data[c.policyId];
  const tauHigh = c.thresholds.tauManipulated ?? preset?.thresholds.tau_manipulated ?? null;
  const tauLow = c.thresholds.tauAuthentic ?? preset?.thresholds.tau_authentic ?? null;
  const processing = c.status === 'queued' || c.status === 'processing';

  const gen = (c.signals.generative_image ?? null) as {
    enabled?: boolean;
    model?: string;
    threshold?: number;
    max?: number;
    mean?: number;
    flagged?: boolean;
    keyframes?: Array<{ timestamp_s: number; p_artificial: number; p_real: number }>;
  } | null;

  const isGenElevated =
    c.labels.includes('generative_signal_flagged') ||
    (gen?.flagged ?? false) ||
    (gen?.max != null && gen.max >= (gen.threshold ?? 0.65));

  const downloadReceipt = async () => {
    if (!c.receiptId) return;
    try {
      const receipt = await api.getReceipt(c.receiptId);
      const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${c.receiptId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(`Receipt download failed: ${errorMessage(err)}`);
    }
  };

  const isImage = Boolean(
    c.media?.container && ['jpg', 'jpeg', 'png', 'webp', 'bmp'].includes(c.media.container.toLowerCase())
  );

  return (
    <>
      <PageHeader
        title={<span className="font-mono text-xl">{c.id}</span>}
        description={`Received ${formatDateTime(c.createdAt)} · source ${c.source}`}
        meta={
          <Link to="/app/cases" className="inline-flex items-center gap-1 text-xs text-muted hover:text-text">
            <ArrowLeft className="h-3.5 w-3.5" /> Cases
          </Link>
        }
        actions={
          <>
            {!c.isDemo && (
              <a href={`/v1/analyses/${encodeURIComponent(c.id)}/report.pdf`} className={buttonVariants({ variant: 'secondary' })}>
                <FileDown className="h-4 w-4" /> PDF report
              </a>
            )}
            {c.band && c.band !== 'inconclusive' && (
              <button type="button" onClick={() => navigate(`/app/review/${c.id}`)} className={buttonVariants()}>
                <ClipboardCheck className="h-4 w-4" /> Open in review
              </button>
            )}
          </>
        }
      />

      {processing && (
        <Card className="mb-6 p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-text">
            <RefreshCw className="h-4 w-4 animate-spin text-accent" /> Analysis in progress — this page refreshes automatically.
          </div>
          <StageProgress
            stages={[
              { id: 'ingest', label: 'Ingest', state: 'done' },
              { id: 'preprocess', label: 'Faces', state: c.status === 'processing' ? 'active' : 'pending' },
              { id: 'gpu', label: 'Cascade', state: 'pending' },
              { id: 'finalize', label: 'Receipt', state: 'pending' },
            ]}
          />
        </Card>
      )}

      {/* Full-Frame AI Detector Escalation Banner */}
      {isGenElevated && !processing && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-band-review/40 bg-band-review/10 p-4 text-sm text-text">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-band-review" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-band-review">Decision Elevated by Full-Frame AI Detector</span>
              <span className="inline-flex items-center gap-1 rounded bg-band-review/20 px-2 py-0.5 text-xs font-mono font-bold text-band-review">
                <Sparkles className="h-3 w-3" />
                Peak {gen?.max != null ? (gen.max * 100).toFixed(1) + '%' : '—'}
              </span>
            </div>
            <p className="text-xs text-muted">
              SwinV2 full-frame keyframe analysis detected high-probability synthetic generative artifacts (threshold &ge; {(gen?.threshold ?? 0.65).toFixed(2)}).
              Case was elevated to <strong className="text-band-review font-semibold">NEEDS REVIEW</strong> per screening policy.
            </p>
          </div>
        </div>
      )}

      {c.status === 'failed' ? (
        <Card className="border-band-manipulated/30 p-6">
          <p className="text-sm font-semibold text-band-manipulated">This analysis failed.</p>
          <p className="mt-1 text-sm text-muted">The media could not be processed. Submit it again from Analyze, or check the worker logs.</p>
        </Card>
      ) : (
        !processing && <VerdictCard c={c} preset={preset} />
      )}

      {/* Main Video & Timeline Section */}
      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(300px,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <EvidencePlayer
            videoUrl={c.videoUrl}
            videoSources={c.videoSources}
            initialDuration={c.media?.durationS}
            isImage={isImage}
            tracks={c.tracks}
            selectedTrackIdx={track}
            onSelectTrack={setTrack}
            onTimeUpdate={setTime}
            seekTime={seek}
            fps={c.media?.fps ?? 30}
            demo={c.isDemo}
          />

          {!isImage && c.tracks.length > 0 && (
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

          {/* SwinV2 Keyframe Timeline Strip */}
          {gen?.keyframes && gen.keyframes.length > 0 && (
            <KeyframeTimeline
              keyframes={gen.keyframes}
              threshold={gen.threshold ?? 0.65}
              currentTime={time}
              onSeek={(t) => setSeek((prev) => (prev === t ? t + 1e-6 : t))}
            />
          )}
        </div>

        <div className="flex flex-col gap-4">
          {c.tracks.length > 0 && (
            <TracksPanel c={c} selected={track} onSelect={setTrack} />
          )}
          <SignalsPanel c={c} />
          <ReceiptPanel c={c} onDownload={downloadReceipt} onVerify={() => navigate(c.isDemo ? '/verify' : `/verify?receipt=${encodeURIComponent(c.receiptId ?? '')}`)} />
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <MediaPanel c={c} />
        <ModelPanel c={c} />
      </div>
    </>
  );
};

export default CaseDetail;
