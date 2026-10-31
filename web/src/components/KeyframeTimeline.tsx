import React from 'react';
import { Sparkles, Clock, AlertTriangle } from 'lucide-react';
import { Card } from '../design/ui';

export interface KeyframeSample {
  timestamp_s: number;
  frame_idx?: number;
  p_artificial: number;
  p_real?: number;
}

interface KeyframeTimelineProps {
  keyframes?: KeyframeSample[];
  threshold?: number;
  currentTime?: number;
  onSeek: (timestamp_s: number) => void;
}

export const KeyframeTimeline: React.FC<KeyframeTimelineProps> = ({
  keyframes = [],
  threshold = 0.65,
  currentTime = 0,
  onSeek,
}) => {
  if (!keyframes || keyframes.length === 0) {
    return null;
  }

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" />
          <span className="text-xs font-semibold uppercase tracking-wider text-text">
            SwinV2 Full-Frame Keyframe Timeline
          </span>
          <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-accent">
            1 fps sampling
          </span>
        </div>
        <span className="text-[11px] text-muted">
          Click any keyframe to seek video
        </span>
      </div>

      <div className="flex items-center gap-2.5 overflow-x-auto pb-1 pt-1">
        {keyframes.map((kf, i) => {
          const isFlagged = kf.p_artificial >= threshold;
          const isAmbiguous = !isFlagged && kf.p_artificial >= 0.35;
          const isActive = Math.abs(currentTime - kf.timestamp_s) < 0.6;
          const pct = (kf.p_artificial * 100).toFixed(1);

          return (
            <button
              key={`${kf.timestamp_s}-${i}`}
              type="button"
              onClick={() => onSeek(kf.timestamp_s)}
              className={`group flex min-w-[100px] flex-col items-start rounded-lg border p-2.5 text-left transition-all ${
                isActive
                  ? 'border-accent ring-1 ring-accent/50 bg-accent/5'
                  : isFlagged
                  ? 'border-band-manipulated/40 bg-band-manipulated/5 hover:border-band-manipulated'
                  : 'border-border bg-card/60 hover:border-muted hover:bg-card'
              }`}
            >
              <div className="flex w-full items-center justify-between text-[11px]">
                <span className="flex items-center gap-1 font-mono text-muted group-hover:text-text">
                  <Clock className="h-3 w-3" />
                  {kf.timestamp_s.toFixed(1)}s
                </span>
                {isFlagged && (
                  <AlertTriangle className="h-3 w-3 text-band-manipulated animate-pulse" />
                )}
              </div>

              <div className="mt-2 flex w-full items-baseline justify-between">
                <span
                  className={`font-mono text-sm font-bold ${
                    isFlagged
                      ? 'text-band-manipulated'
                      : isAmbiguous
                      ? 'text-accent'
                      : 'text-band-authentic'
                  }`}
                >
                  {pct}%
                </span>
                <span
                  className={`text-[9px] font-semibold uppercase ${
                    isFlagged
                      ? 'text-band-manipulated'
                      : isAmbiguous
                      ? 'text-accent'
                      : 'text-band-authentic'
                  }`}
                >
                  {isFlagged ? 'AI' : isAmbiguous ? 'Unsure' : 'Real'}
                </span>
              </div>

              {/* Mini visual fill gauge */}
              <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-border/60">
                <div
                  className={`h-full rounded-full transition-all ${
                    isFlagged
                      ? 'bg-band-manipulated'
                      : isAmbiguous
                      ? 'bg-accent'
                      : 'bg-band-authentic'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, kf.p_artificial * 100))}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
};

