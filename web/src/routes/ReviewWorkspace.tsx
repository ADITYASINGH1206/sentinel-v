import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  HelpCircle,
  Clock,
  Send,
  RotateCcw,
  SkipForward,
  Keyboard,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { EvidencePlayer, TrackData } from '../components/EvidencePlayer';
import { ClipTimeline } from '../components/ClipTimeline';
import { BandChip, DecisionBand } from '../components/BandChip';
import { ScoreReadout } from '../components/ScoreReadout';
import { REQUIRED_DISCLAIMER } from '../copy/forbidden';

export interface AnalysisDetails {
  id: string;
  status: string;
  band: DecisionBand;
  p_bal: number;
  p_prior?: number;
  prior_prevalence: number;
  tau: number;
  policy_id: string;
  model_bundle_id: string;
  video_url?: string;
  duration_s: number;
  fps: number;
  tracks: TrackData[];
}

// Sample fallback mock analysis for dev/testing when API queue is empty
const MOCK_ANALYSIS_DATA: AnalysisDetails = {
  id: 'an_mock_review_7721',
  status: 'completed',
  band: 'needs_review',
  p_bal: 0.63,
  p_prior: 0.018,
  prior_prevalence: 0.01,
  tau: 0.5,
  policy_id: 'pol_strict_v3',
  model_bundle_id: 'bundle-clip-st-v2',
  duration_s: 18.5,
  fps: 30.0,
  tracks: [
    {
      track_idx: 0,
      n_frames: 180,
      u: 0.54,
      p_bal: 0.63,
      decisive: true,
      clips: [
        { k: 0, start_frame: 0, end_frame: 7, start_s: 0.0, p: 0.42 },
        { k: 1, start_frame: 15, end_frame: 22, start_s: 0.5, p: 0.48 },
        { k: 2, start_frame: 30, end_frame: 37, start_s: 1.0, p: 0.51 },
        { k: 3, start_frame: 45, end_frame: 52, start_s: 1.5, p: 0.72 },
        { k: 4, start_frame: 60, end_frame: 67, start_s: 2.0, p: 0.79 },
        { k: 5, start_frame: 75, end_frame: 82, start_s: 2.5, p: 0.68 },
        { k: 6, start_frame: 90, end_frame: 97, start_s: 3.0, p: 0.55 },
        { k: 7, start_frame: 105, end_frame: 112, start_s: 3.5, p: 0.46 },
      ],
    },
    {
      track_idx: 1,
      n_frames: 120,
      u: -0.85,
      p_bal: 0.31,
      decisive: false,
      clips: [
        { k: 0, start_frame: 0, end_frame: 7, start_s: 0.0, p: 0.28 },
        { k: 1, start_frame: 15, end_frame: 22, start_s: 0.5, p: 0.33 },
        { k: 2, start_frame: 30, end_frame: 37, start_s: 1.0, p: 0.31 },
        { k: 3, start_frame: 45, end_frame: 52, start_s: 1.5, p: 0.29 },
      ],
    },
  ],
};

const REASON_CODES = [
  { id: 'blending_seam', label: 'Blending seam / boundary artifact' },
  { id: 'mouth_teeth', label: 'Mouth, teeth, or lip synthesis anomaly' },
  { id: 'temporal_flicker', label: 'Temporal flicker or jitter across frames' },
  { id: 'lighting', label: 'Lighting, shadow, or specular reflection mismatch' },
  { id: 'identity', label: 'Facial identity morphing or structural warping' },
  { id: 'other', label: 'Other synthetic visual cue' },
];

export const ReviewWorkspace: React.FC = () => {
  const [analysis, setAnalysis] = useState<AnalysisDetails>(MOCK_ANALYSIS_DATA);
  const [selectedTrackIdx, setSelectedTrackIdx] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [seekTime, setSeekTime] = useState<number | undefined>(undefined);

  // Review decision states
  const [decision, setDecision] = useState<'likely_authentic' | 'likely_manipulated' | 'inconclusive' | null>(null);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [notes, setNotes] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submittedAlert, setSubmittedAlert] = useState<string | null>(null);

  // Telemetry trackers
  const startTimeRef = useRef<number>(Date.now());
  const [overlayToggles, setOverlayToggles] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Timer loop for review telemetry
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [analysis.id]);

  const handleToggleReason = (id: string) => {
    setSelectedReasons((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const resetForm = useCallback(() => {
    setDecision(null);
    setSelectedReasons([]);
    setNotes('');
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!decision) return;
    setSubmitting(true);
    const durationMs = Date.now() - startTimeRef.current;

    const payload = {
      decision,
      reason_codes: selectedReasons,
      notes,
      telemetry: {
        time_to_decision_ms: durationMs,
        overlay_toggled_count: overlayToggles,
      },
    };

    try {
      // POST review to API
      await fetch(`/v1/reviews/${analysis.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).catch(() => null);

      setSubmittedAlert(`Decision '${decision}' recorded! Fetching next case...`);

      // Reset for next queue item
      setTimeout(() => {
        setSubmittedAlert(null);
        resetForm();
        startTimeRef.current = Date.now();
        setOverlayToggles(0);
        // Simulate next queue item or fetch from queue
        setAnalysis({
          ...MOCK_ANALYSIS_DATA,
          id: `an_queue_${Math.floor(1000 + Math.random() * 9000)}`,
        });
      }, 750);
    } catch {
      setSubmittedAlert('Submitted (offline mode)');
    } finally {
      setSubmitting(false);
    }
  }, [decision, selectedReasons, notes, overlayToggles, analysis.id, resetForm]);

  // Keyboard triage listeners (1/2/3, Enter, S, R)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'textarea' || tag === 'input') return;

      if (e.key === '1') {
        e.preventDefault();
        setDecision('likely_authentic');
      } else if (e.key === '2') {
        e.preventDefault();
        setDecision('likely_manipulated');
      } else if (e.key === '3') {
        e.preventDefault();
        setDecision('inconclusive');
      } else if (e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        resetForm();
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        // Skip current item
        setAnalysis({
          ...MOCK_ANALYSIS_DATA,
          id: `an_skip_${Math.floor(1000 + Math.random() * 9000)}`,
        });
        resetForm();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSubmit, resetForm]);

  return (
    <div className="flex flex-col min-h-screen bg-bg text-text">
      {/* Top Header */}
      <header className="border-b border-border bg-surface px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-bold tracking-wider text-accent text-base">SENTINEL-V</span>
          <span className="text-muted text-sm">&bull;</span>
          <span className="font-mono text-xs text-text font-semibold">{analysis.id}</span>
          <BandChip band={analysis.band} size="sm" />
        </div>

        <div className="flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1 font-mono">
            <Clock className="w-3.5 h-3.5" />
            {elapsedSeconds}s elapsed
          </span>
          <span>Policy: <code className="text-text">{analysis.policy_id}</code></span>
          <span>Bundle: <code className="text-text">{analysis.model_bundle_id}</code></span>
        </div>
      </header>

      {/* Notification Toast */}
      {submittedAlert && (
        <div className="bg-emerald-50 dark:bg-emerald-950 border-b border-emerald-200 dark:border-emerald-800 px-6 py-2 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{submittedAlert}</span>
        </div>
      )}

      {/* Main Workspace Body */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Player & Timeline (7 cols) */}
        <section className="lg:col-span-8 flex flex-col gap-4">
          <EvidencePlayer
            videoUrl={analysis.video_url}
            tracks={analysis.tracks}
            selectedTrackIdx={selectedTrackIdx}
            onSelectTrack={setSelectedTrackIdx}
            currentTime={currentTime}
            seekTime={seekTime}
            onTimeUpdate={setCurrentTime}
            onOverlayToggled={() => setOverlayToggles((c) => c + 1)}
            fps={analysis.fps}
          />

          <ClipTimeline
            tracks={analysis.tracks}
            selectedTrackIdx={selectedTrackIdx}
            currentTime={currentTime}
            duration={analysis.duration_s}
            tau={analysis.tau}
            fps={analysis.fps}
            onSeek={(t) => setSeekTime(t)}
          />

          {/* Quick Metrics & Disclaimer */}
          <div className="bg-surface border border-border rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <ScoreReadout
              p_bal={analysis.p_bal}
              p_prior={analysis.p_prior}
              prior_prevalence={analysis.prior_prevalence}
            />
            <div className="text-right text-xs text-muted italic max-w-sm">
              {REQUIRED_DISCLAIMER}
            </div>
          </div>
        </section>

        {/* Right Column: Review Triage Panel (4 cols) */}
        <section className="lg:col-span-4 flex flex-col gap-4">
          <div className="bg-surface border border-border rounded-lg p-5 flex flex-col gap-5 shadow-sm">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h2 className="font-semibold text-base text-text">Reviewer Triage</h2>
              <span className="text-xs text-muted font-mono flex items-center gap-1">
                <Keyboard className="w-3.5 h-3.5" /> 1 / 2 / 3 keys
              </span>
            </div>

            {/* Decision Actions */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted">Select Determination:</label>

              <button
                type="button"
                onClick={() => setDecision('likely_authentic')}
                className={`flex items-center justify-between p-3 rounded-lg border text-sm font-medium transition-all ${
                  decision === 'likely_authentic'
                    ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 ring-1 ring-emerald-500'
                    : 'border-border hover:bg-gray-50 dark:hover:bg-gray-800/60 text-text'
                }`}
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <span>Likely Authentic</span>
                </div>
                <kbd className="px-1.5 py-0.5 text-xs bg-bg border border-border rounded font-mono text-muted">
                  [1]
                </kbd>
              </button>

              <button
                type="button"
                onClick={() => setDecision('likely_manipulated')}
                className={`flex items-center justify-between p-3 rounded-lg border text-sm font-medium transition-all ${
                  decision === 'likely_manipulated'
                    ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 ring-1 ring-rose-500'
                    : 'border-border hover:bg-gray-50 dark:hover:bg-gray-800/60 text-text'
                }`}
              >
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                  <span>Likely Manipulated</span>
                </div>
                <kbd className="px-1.5 py-0.5 text-xs bg-bg border border-border rounded font-mono text-muted">
                  [2]
                </kbd>
              </button>

              <button
                type="button"
                onClick={() => setDecision('inconclusive')}
                className={`flex items-center justify-between p-3 rounded-lg border text-sm font-medium transition-all ${
                  decision === 'inconclusive'
                    ? 'border-gray-500 bg-gray-100 dark:bg-gray-800/80 text-text ring-1 ring-gray-400'
                    : 'border-border hover:bg-gray-50 dark:hover:bg-gray-800/60 text-text'
                }`}
              >
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-gray-500" />
                  <span>Cannot Tell / Inconclusive</span>
                </div>
                <kbd className="px-1.5 py-0.5 text-xs bg-bg border border-border rounded font-mono text-muted">
                  [3]
                </kbd>
              </button>
            </div>

            {/* Checkbox Reason Codes */}
            <div className="flex flex-col gap-2 pt-2 border-t border-border">
              <label className="text-xs font-medium text-muted">Artifact Reason Codes:</label>
              <div className="space-y-1.5">
                {REASON_CODES.map((reason) => (
                  <label
                    key={reason.id}
                    className="flex items-start gap-2.5 text-xs text-text cursor-pointer hover:opacity-90 select-none"
                  >
                    <input
                      type="checkbox"
                      checked={selectedReasons.includes(reason.id)}
                      onChange={() => handleToggleReason(reason.id)}
                      className="mt-0.5 rounded border-border text-accent focus:ring-accent"
                    />
                    <span>{reason.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Reviewer Freeform Notes */}
            <div className="flex flex-col gap-1.5 pt-2 border-t border-border">
              <label className="text-xs font-medium text-muted">Review Notes (Optional):</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Observed temporal flicker on mouth area between 1.5s - 2.5s..."
                rows={3}
                className="w-full text-xs p-2.5 bg-bg border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent text-text resize-none"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2 pt-2 border-t border-border">
              <button
                type="button"
                disabled={!decision || submitting}
                onClick={handleSubmit}
                className={`w-full py-2.5 px-4 rounded-md font-medium text-xs flex items-center justify-center gap-2 transition-all ${
                  decision && !submitting
                    ? 'bg-accent text-white hover:opacity-90 shadow'
                    : 'bg-gray-200 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit & Next (Enter)</span>
              </button>

              <div className="flex items-center justify-between text-xs text-muted pt-1">
                <button
                  type="button"
                  onClick={resetForm}
                  className="flex items-center gap-1 hover:text-text transition-colors"
                >
                  <RotateCcw className="w-3 h-3" /> Reset (R)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAnalysis({
                      ...MOCK_ANALYSIS_DATA,
                      id: `an_skip_${Math.floor(1000 + Math.random() * 9000)}`,
                    });
                    resetForm();
                  }}
                  className="flex items-center gap-1 hover:text-text transition-colors"
                >
                  <SkipForward className="w-3 h-3" /> Skip Case (S)
                </button>
              </div>
            </div>

            {/* Mandatory Screening Disclaimer in Triage Panel */}
            <div className="pt-3 border-t border-border">
              <p className="text-[11px] text-muted font-medium italic text-center">
                {REQUIRED_DISCLAIMER}
              </p>
            </div>
          </div>

          {/* Keyboard Shortcuts Reference Pill */}
          <div className="bg-surface border border-border rounded-lg p-3 text-xs text-muted flex items-center gap-2">
            <Info className="w-4 h-4 shrink-0 text-accent" />
            <span>Shortcuts: <kbd className="font-mono bg-bg px-1 rounded">Space</kbd> Play/Pause &bull; <kbd className="font-mono bg-bg px-1 rounded">P</kbd> Peak Clip &bull; <kbd className="font-mono bg-bg px-1 rounded">H</kbd> Heatmap</span>
          </div>
        </section>
      </main>
    </div>
  );
};

