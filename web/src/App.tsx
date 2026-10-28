import React from 'react';
import { BandChip } from './components/BandChip';
import { ScoreReadout } from './components/ScoreReadout';
import { REQUIRED_DISCLAIMER } from './copy/forbidden';

export function App() {
  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold tracking-wider text-accent text-lg">SENTINEL-V</span>
          <span className="bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 text-xs px-2 py-0.5 rounded font-mono font-medium">
            MOCK MODE
          </span>
        </div>
        <div className="text-xs text-muted">
          Policy: strict-low-fpr v3
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 max-w-5xl mx-auto w-full space-y-6">
        <div className="bg-surface border border-border rounded-lg p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold">Video Deepfake Screening Workspace</h1>
            <BandChip band="needs_review" />
          </div>

          <ScoreReadout p_bal={0.62} p_prior={0.016} prior_prevalence={0.01} />

          <div className="pt-4 border-t border-border">
            <p className="text-xs text-muted font-medium italic">
              {REQUIRED_DISCLAIMER}
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-4 text-center text-xs text-muted bg-surface">
        SENTINEL-V Reviewer Console &bull; Research Use Only &bull; S-MSDT Detector Family
      </footer>
    </div>
  );
}

export default App;

