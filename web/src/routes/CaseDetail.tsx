import React from 'react';
import {
  ArrowLeft,
  FileCheck,
  Film,
  Cpu,
  Layers,
  ShieldAlert,
  Hash,
  Download,
} from 'lucide-react';
import { BandChip } from '../components/BandChip';
import { ScoreReadout } from '../components/ScoreReadout';
import { REQUIRED_DISCLAIMER } from '../copy/forbidden';

interface CaseDetailProps {
  caseId: string;
  onBack: () => void;
  onOpenReview: (id: string) => void;
}

export const CaseDetail: React.FC<CaseDetailProps> = ({ caseId, onBack, onOpenReview }) => {
  return (
    <div className="flex flex-col min-h-screen bg-bg text-text">
      {/* Header */}
      <header className="border-b border-border bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <span className="font-bold tracking-wider text-accent text-lg">SENTINEL-V</span>
          <span className="text-muted text-sm">&bull;</span>
          <span className="text-sm font-mono font-semibold text-text">{caseId}</span>
          <BandChip band="needs_review" size="sm" />
        </div>

        <button
          onClick={() => onOpenReview(caseId)}
          className="px-4 py-2 bg-accent text-white rounded-md text-xs font-semibold hover:opacity-90 shadow-sm transition-opacity"
        >
          Open Review Workspace
        </button>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 flex flex-col gap-6">
        {/* Score & Determination Summary Banner */}
        <div className="bg-surface border border-border rounded-lg p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-text">Screening Determination</h1>
            <ScoreReadout p_bal={0.63} p_prior={0.018} prior_prevalence={0.01} />
          </div>
          <div className="flex flex-col items-end gap-2">
            <BandChip band="needs_review" size="lg" />
            <span className="text-xs text-muted font-mono">Policy: pol_strict_v3 (τ = 0.50)</span>
          </div>
        </div>

        {/* Technical Audit Breakdown Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Media Provenance Card */}
          <div className="bg-surface border border-border rounded-lg p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-text font-semibold text-sm border-b border-border pb-3">
              <Film className="w-4 h-4 text-accent" />
              <span>Media Metadata & Container</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="text-muted">Resolution</p>
                <p className="font-mono font-medium">1920 &times; 1080 (1080p)</p>
              </div>
              <div>
                <p className="text-muted">Framerate</p>
                <p className="font-mono font-medium">30.0 fps</p>
              </div>
              <div>
                <p className="text-muted">Duration</p>
                <p className="font-mono font-medium">18.5 seconds</p>
              </div>
              <div>
                <p className="text-muted">Codec / Container</p>
                <p className="font-mono font-medium">H.264 / mp4</p>
              </div>
            </div>
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-muted">SHA-256 Digest</p>
              <p className="font-mono text-[11px] text-text break-all">
                e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
              </p>
            </div>
          </div>

          {/* Model Pipeline Card */}
          <div className="bg-surface border border-border rounded-lg p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-text font-semibold text-sm border-b border-border pb-3">
              <Cpu className="w-4 h-4 text-accent" />
              <span>Model Cascade Inference</span>
            </div>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-muted">Deciding Adapter</span>
                <span className="font-mono font-semibold">CLIP-ST v2 (Stage B)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted">Raw Logit u</span>
                <span className="font-mono">+0.540</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted">Platt Calibrated p_bal</span>
                <span className="font-mono font-bold text-accent">0.630</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted">Bundle Digest Verified</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">checksums.sha256 PASS</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cryptographic Detection Receipt */}
        <div className="bg-surface border border-border rounded-lg p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2 text-text font-semibold text-sm">
              <FileCheck className="w-4 h-4 text-emerald-600" />
              <span>Cryptographic Detection Receipt (RFC 8785 JCS)</span>
            </div>
            <button
              onClick={() => alert('Exporting canonical detection receipt JSON...')}
              className="flex items-center gap-1.5 px-3 py-1 text-xs border border-border rounded hover:bg-bg transition-colors text-muted hover:text-text"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Receipt</span>
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div>
              <p className="text-muted">Receipt ID</p>
              <p className="font-mono text-text">rcpt_7f99b1a0e281</p>
            </div>
            <div>
              <p className="text-muted">Digital Signature</p>
              <p className="font-mono text-text">Ed25519 (RFC 8032)</p>
            </div>
            <div>
              <p className="text-muted">Merkle Anchoring</p>
              <p className="font-mono text-muted">Batch 142 (Sepolia pending)</p>
            </div>
          </div>
        </div>

        {/* Mandatory Screening Disclaimer */}
        <div className="p-3 bg-surface border border-border rounded-lg text-xs text-muted italic text-center">
          {REQUIRED_DISCLAIMER}
        </div>
      </main>
    </div>
  );
};

