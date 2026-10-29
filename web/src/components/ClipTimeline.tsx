import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  CartesianGrid,
} from 'recharts';
import { Table2, LineChart } from 'lucide-react';
import { TrackData } from './EvidencePlayer';
import { useThemeColors } from '../design/useThemeColors';
import { usePreferences } from '../design/preferences';

interface ClipTimelineProps {
  tracks: TrackData[];
  selectedTrackIdx: number;
  currentTime: number;
  duration: number;
  /** Upper band boundary (likely manipulated); null when the policy does not report one. */
  tau: number | null;
  /** Optional lower band boundary (likely authentic). */
  tauLow?: number | null;
  fps: number;
  onSeek: (timeInSeconds: number) => void;
}

export const ClipTimeline: React.FC<ClipTimelineProps> = ({
  tracks,
  selectedTrackIdx,
  currentTime,
  duration,
  tau,
  tauLow,
  fps,
  onSeek,
}) => {
  const colors = useThemeColors();
  const { reduceMotion } = usePreferences();
  const [showTable, setShowTable] = useState(false);
  const activeTrack = tracks.find((t) => t.track_idx === selectedTrackIdx) || tracks[0];

  const chartData = (activeTrack?.clips || []).map((clip) => ({
    time: parseFloat(clip.start_s.toFixed(2)),
    score: parseFloat(clip.p.toFixed(3)),
    clipIdx: clip.k,
  }));

  // Long-video protocol (> 30 s): first 8 s plus 4 spaced 32-frame windows (SPEC §6.3).
  const windowLen = 32.0 / fps;
  const isLongVideo = duration > 30.0;
  const remainingDuration = Math.max(0, duration - 8.0);
  const samplingWindows = isLongVideo
    ? [
        { start: 0, end: 8 },
        ...Array.from({ length: 4 }).map((_, i) => {
          const segmentStart = 8 + (remainingDuration / 5) * (i + 1);
          return { start: segmentStart, end: Math.min(segmentStart + windowLen, duration) };
        }),
      ]
    : [{ start: 0, end: duration }];

  const peak = chartData.reduce<{ time: number; score: number } | null>((best, d) => (!best || d.score > best.score ? d : best), null);

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-surface p-4 shadow-1">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-text">Clip Probability Timeline</span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-accent" />
            Track #{activeTrack ? activeTrack.track_idx : 0}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 font-mono text-band-manipulated">
            <span className="inline-block w-4 border-t-2 border-dashed border-band-manipulated" />
            Decision Threshold τ = {tau != null ? tau.toFixed(2) : '—'}
          </span>
          {tauLow != null && (
            <span className="flex items-center gap-1.5 font-mono text-band-authentic">
              <span className="inline-block w-4 border-t-2 border-dashed border-band-authentic" />
              {tauLow.toFixed(2)}
            </span>
          )}
          <button
            type="button"
            onClick={() => setShowTable((v) => !v)}
            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-muted hover:bg-surface-2 hover:text-text"
            aria-pressed={showTable}
          >
            {showTable ? <LineChart className="h-3.5 w-3.5" /> : <Table2 className="h-3.5 w-3.5" />}
            {showTable ? 'Chart' : 'Data table'}
          </button>
        </div>
      </div>

      {showTable ? (
        <div className="max-h-40 overflow-auto rounded border border-border">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Clip scores for track {activeTrack?.track_idx ?? 0}</caption>
            <thead className="sticky top-0 bg-surface-2 text-muted">
              <tr>
                <th className="px-3 py-1.5 font-medium">Clip</th>
                <th className="px-3 py-1.5 font-medium">Start</th>
                <th className="px-3 py-1.5 font-medium">Score</th>
                <th className="px-3 py-1.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border font-mono">
              {chartData.map((d) => (
                <tr key={d.clipIdx}>
                  <td className="px-3 py-1">#{d.clipIdx}</td>
                  <td className="px-3 py-1">{d.time.toFixed(2)} s</td>
                  <td className="px-3 py-1">{d.score.toFixed(2)}</td>
                  <td className="px-3 py-1 text-right">
                    <button type="button" className="text-accent hover:underline" onClick={() => onSeek(d.time)}>
                      Seek
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-40 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 8, right: 12, left: -20, bottom: 0 }}
              onClick={(e) => {
                if (e && e.activePayload && e.activePayload[0]) {
                  onSeek(e.activePayload[0].payload.time);
                }
              }}
            >
              <defs>
                <linearGradient id="vfScoreGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors['--accent']} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={colors['--accent']} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={colors['--border']} strokeDasharray="2 4" vertical={false} />
              {samplingWindows.map((win, idx) => (
                <ReferenceArea key={idx} x1={win.start} x2={win.end} fill={colors['--muted']} fillOpacity={0.06} />
              ))}
              <XAxis
                dataKey="time"
                type="number"
                domain={[0, Math.max(duration, 1)]}
                unit="s"
                tick={{ fontSize: 11, fill: colors['--muted'] }}
                tickLine={false}
                axisLine={{ stroke: colors['--border'] }}
              />
              <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1.0]} tick={{ fontSize: 11, fill: colors['--muted'] }} tickLine={false} axisLine={false} />
              <Tooltip
                cursor={{ stroke: colors['--border'] }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-md border border-border bg-surface p-2 text-xs shadow-2">
                        <p className="font-semibold text-text">Clip #{data.clipIdx}</p>
                        <p className="text-muted">Starts at {data.time}s</p>
                        <p className="font-mono text-accent">score {Number(data.score).toFixed(2)}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {tau != null && <ReferenceLine y={tau} stroke={colors['--band-manipulated']} strokeDasharray="4 4" strokeWidth={1.5} />}
              {tauLow != null && <ReferenceLine y={tauLow} stroke={colors['--band-authentic']} strokeDasharray="4 4" strokeWidth={1.25} />}
              {peak && <ReferenceLine x={peak.time} stroke={colors['--band-review']} strokeOpacity={0.5} strokeWidth={1} />}
              <ReferenceLine x={currentTime} stroke={colors['--text']} strokeWidth={1.5} />
              <Area
                type="monotone"
                dataKey="score"
                stroke={colors['--accent']}
                strokeWidth={2}
                fill="url(#vfScoreGradient)"
                isAnimationActive={!reduceMotion}
                animationDuration={500}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="text-[11px] text-muted">Click the chart to seek. Shaded regions are the analysed windows.</p>
    </div>
  );
};
