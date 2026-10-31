import React, { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, m } from 'framer-motion';
import { toast } from 'sonner';
import { FileVideo, Link2, Loader2, UploadCloud, X } from 'lucide-react';
import { PageHeader } from '../../components/console/common';
import { StageProgress, type Stage } from '../../components/StageProgress';
import { Button, Card, CardHeader, Disclaimer, Notice, cn } from '../../design/ui';
import { errorMessage, usePresets } from '../../data/hooks';
import { ApiError, request, uploadAnalysis } from '../../data/api';
import { demoCases } from '../../data/demo';

/** Mirrors SV_MAX_UPLOAD_MB / SV_MAX_DURATION_S defaults in sv_core/settings.py. */
const MAX_MB = 500;
const MAX_DURATION_S = 600;
const PREVALENCES = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2];

function readDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement('video');
    v.preload = 'metadata';
    v.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(v.duration) ? v.duration : null);
    };
    v.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    v.src = url;
  });
}

const Analyze: React.FC = () => {
  const navigate = useNavigate();
  const presets = usePresets();
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const [mode, setMode] = useState<'file' | 'url'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [url, setUrl] = useState('');
  const [dragging, setDragging] = useState(false);
  const [policy, setPolicy] = useState('strict-low-fpr');
  const [prevalence, setPrevalence] = useState(0.01);
  const [forceFull, setForceFull] = useState(false);
  const [gradcam, setGradcam] = useState(true);
  const [skipCache, setSkipCache] = useState(false);
  const [externalRef, setExternalRef] = useState('');
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const acceptFile = useCallback(async (f: File | undefined) => {
    setError(null);
    if (!f) return;
    const isVid = f.type.startsWith('video/') || /\.(mp4|mov|webm|mkv|avi)$/i.test(f.name);
    const isImg = f.type.startsWith('image/') || /\.(jpg|jpeg|png|webp|bmp)$/i.test(f.name);
    if (!isVid && !isImg) {
      setError('UNSUPPORTED_MEDIA: choose a video (MP4, MOV, WebM, MKV) or image (JPG, PNG, WebP).');
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`MEDIA_TOO_LARGE: the limit is ${MAX_MB} MB.`);
      return;
    }
    let d: number | null = null;
    if (isVid) {
      d = await readDuration(f);
      if (d != null && d > MAX_DURATION_S) {
        setError(`MEDIA_TOO_LONG: the limit is ${MAX_DURATION_S / 60} minutes.`);
        return;
      }
    }
    setFile(f);
    setDuration(d);
  }, []);

  const stages: Stage[] = [
    { id: 'upload', label: mode === 'file' ? 'Upload' : 'Submit', state: progress == null ? 'pending' : progress < 1 ? 'active' : 'done', detail: progress != null && progress < 1 ? `${Math.round(progress * 100)}%` : undefined },
    { id: 'queued', label: 'Queued', state: progress != null && progress >= 1 ? 'active' : 'pending' },
    { id: 'faces', label: 'Faces', state: 'pending' },
    { id: 'cascade', label: 'Cascade', state: 'pending' },
    { id: 'receipt', label: 'Receipt', state: 'pending' },
  ];

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      let res: { analysis_id: string };
      if (mode === 'file') {
        if (!file) return;
        const form = new FormData();
        form.append('file', file);
        form.append('policy_id', policy);
        form.append('explain_gradcam', gradcam ? 'true' : 'false');
        form.append('skip_cache', skipCache ? 'true' : 'false');
        form.append('external_ref', externalRef || 'upload');
        setProgress(0);
        const job = uploadAnalysis(form, setProgress);
        abortRef.current = job.abort;
        res = await job.promise;
      } else {
        if (!/^https?:\/\//i.test(url)) {
          setError('Enter an http(s) URL.');
          return;
        }
        setProgress(0.5);
        res = await request<{ analysis_id: string }>('/v1/analyses', {
          method: 'POST',
          body: JSON.stringify({
            source_url: url,
            policy_id: policy,
            prior_prevalence: prevalence,
            mode: forceFull ? 'full' : 'auto',
            explain_gradcam: gradcam,
            skip_cache: skipCache,
            external_ref: externalRef || null,
          }),
        });
      }
      setProgress(1);
      toast.success(`Analysis ${res.analysis_id} queued`);
      navigate(`/app/cases/${res.analysis_id}`);
    } catch (err) {
      setProgress(null);
      if (err instanceof ApiError && err.code === 'ABORTED') return;
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const unreachable = error?.includes('NETWORK_ERROR') || error?.includes('not reachable');
  const demoId = demoCases().find((c) => c.band === 'needs_review')?.id;
  const ready = mode === 'file' ? Boolean(file) : url.length > 8;
  const presetList = Object.values(presets.data?.data ?? {});

  return (
    <>
      <PageHeader title="Analyze a video" description="Upload a file or paste a link. You can follow progress on the case page." />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="overflow-hidden">
          <div className="flex border-b border-border" role="tablist" aria-label="Source">
            {(['file', 'url'] as const).map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={mode === t}
                onClick={() => setMode(t)}
                className={cn('relative flex-1 px-4 py-3 text-sm font-medium transition-colors', mode === t ? 'text-text' : 'text-muted hover:text-text')}
              >
                <span className="inline-flex items-center gap-2">
                  {t === 'file' ? <UploadCloud className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
                  {t === 'file' ? 'Upload a file' : 'From a URL'}
                </span>
                {mode === t && <m.span layoutId="analyze-tab" className="absolute inset-x-0 bottom-0 h-0.5 bg-accent" />}
              </button>
            ))}
          </div>

          <div className="p-5">
            <AnimatePresence mode="wait" initial={false}>
              {mode === 'file' ? (
                <m.div key="file" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.16 }}>
                  {file ? (
                    <div className="flex items-center gap-3 rounded-md border border-border bg-surface-2 p-4">
                      <span className="grid h-10 w-10 place-items-center rounded-md bg-accent/10 text-accent">
                        <FileVideo className="h-5 w-5" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-text">{file.name}</p>
                        <p className="font-mono text-xs text-muted">
                          {(file.size / 1024 / 1024).toFixed(1)} MB{duration != null && ` · ${duration.toFixed(1)} s`}
                        </p>
                      </div>
                      <button type="button" className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-surface hover:text-text" onClick={() => setFile(null)} aria-label="Remove file">
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <label
                      onDragOver={(e) => {
                        e.preventDefault();
                        setDragging(true);
                      }}
                      onDragLeave={() => setDragging(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setDragging(false);
                        acceptFile(e.dataTransfer.files?.[0]);
                      }}
                      className={cn(
                        'group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-md px-6 py-14 text-center transition-colors',
                        dragging ? 'bg-accent/5' : 'bg-surface-2/60 hover:bg-surface-2'
                      )}
                    >
                      <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
                        <rect
                          x="1"
                          y="1"
                          style={{ width: 'calc(100% - 2px)', height: 'calc(100% - 2px)' }}
                          rx="10"
                          fill="none"
                          stroke={dragging ? 'rgb(var(--accent))' : 'rgb(var(--border))'}
                          strokeWidth="2"
                          strokeDasharray="8 6"
                          className={cn(dragging && 'animate-[dash_0.6s_linear_infinite]')}
                        />
                      </svg>
                      <m.span animate={{ y: dragging ? -4 : 0 }} className="grid h-12 w-12 place-items-center rounded-full bg-accent/10 text-accent">
                        <UploadCloud className="h-6 w-6" />
                      </m.span>
                      <span className="text-sm font-medium text-text">
                        Drop a video or image here, or <span className="text-accent underline-offset-2 group-hover:underline">browse</span>
                      </span>
                      <span className="text-xs text-muted">
                        MP4, MOV, WebM, MKV, JPG, PNG, WebP · up to {MAX_MB} MB
                      </span>
                      <input ref={inputRef} type="file" accept="video/*,image/*,.mp4,.mov,.webm,.mkv,.avi,.jpg,.jpeg,.png,.webp,.bmp" className="sr-only" onChange={(e) => acceptFile(e.target.files?.[0])} />
                    </label>
                  )}
                </m.div>
              ) : (
                <m.div key="url" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.16 }} className="space-y-2">
                  <label htmlFor="src-url" className="text-sm font-medium text-text">
                    Video URL
                  </label>
                  <input
                    id="src-url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.org/clip.mp4"
                    className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
                  />
                  <p className="text-xs text-muted">The server downloads it with SSRF protection; private and internal addresses are refused.</p>
                </m.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {error && (
                <m.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mt-4 overflow-hidden">
                  <Notice tone="warning">
                    <p className="font-medium">{error}</p>
                    {unreachable && demoId && (
                      <button type="button" className="mt-1 text-accent hover:underline" onClick={() => navigate(`/app/cases/${demoId}`)}>
                        Open a demo case instead
                      </button>
                    )}
                  </Notice>
                </m.div>
              )}
            </AnimatePresence>

            <div className="mt-6 border-t border-border pt-5">
              <StageProgress stages={stages} />
            </div>

            <div className="mt-6 flex items-center justify-end gap-2">
              {busy && abortRef.current && (
                <Button variant="ghost" onClick={() => abortRef.current?.()}>
                  Cancel
                </Button>
              )}
              <Button size="lg" disabled={!ready || busy} onClick={submit}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                {busy ? 'Submitting…' : 'Analyze'}
              </Button>
            </div>
          </div>
        </Card>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Options" />
            <div className="space-y-4 p-5 text-sm">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-muted">Policy</span>
                <select value={policy} onChange={(e) => setPolicy(e.target.value)} className="h-9 w-full rounded-md border border-border bg-bg px-3 text-text focus:border-accent focus:outline-none">
                  {presetList.length === 0 && <option value="strict-low-fpr">strict-low-fpr</option>}
                  {presetList.map((p) => (
                    <option key={p.policy_id} value={p.policy_id}>
                      {p.name} ({p.policy_id})
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-muted">Expected share of manipulated videos (prior)</span>
                <select value={prevalence} onChange={(e) => setPrevalence(Number(e.target.value))} className="h-9 w-full rounded-md border border-border bg-bg px-3 text-text focus:border-accent focus:outline-none">
                  {PREVALENCES.map((p) => (
                    <option key={p} value={p}>
                      {(p * 100).toFixed(p < 0.01 ? 1 : 0)}%
                    </option>
                  ))}
                </select>
              </label>
              <div>
                <span className="mb-1.5 block text-xs font-medium text-muted">Mode</span>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { v: false, label: 'Auto cascade' },
                    { v: true, label: 'Force full model' },
                  ].map((o) => (
                    <button
                      key={o.label}
                      type="button"
                      aria-pressed={forceFull === o.v}
                      onClick={() => setForceFull(o.v)}
                      className={cn('h-9 rounded-md border text-xs font-medium transition-colors', forceFull === o.v ? 'border-accent bg-accent/10 text-accent' : 'border-border text-muted hover:bg-surface-2')}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
              <label className="flex items-center gap-2 text-text">
                <input type="checkbox" checked={gradcam} onChange={(e) => setGradcam(e.target.checked)} className="h-4 w-4 accent-[rgb(var(--accent))]" />
                Deep explain (Grad-CAM, slower)
              </label>
              <label className="flex items-center gap-2 text-text">
                <input type="checkbox" checked={skipCache} onChange={(e) => setSkipCache(e.target.checked)} className="h-4 w-4 accent-[rgb(var(--accent))]" />
                Skip the duplicate-file cache
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-muted">External reference (optional)</span>
                <input value={externalRef} onChange={(e) => setExternalRef(e.target.value)} placeholder="post id or case number" className="h-9 w-full rounded-md border border-border bg-bg px-3 text-text placeholder:text-muted focus:border-accent focus:outline-none" />
              </label>
              {mode === 'file' && <p className="text-xs text-muted">Screening policy, Grad-CAM deep explanation, and case reference are applied to file uploads.</p>}
            </div>
          </Card>
          <Disclaimer className="px-1" />
        </div>
      </div>
    </>
  );
};

export default Analyze;
