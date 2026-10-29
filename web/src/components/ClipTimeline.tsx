import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import { TrackData } from './EvidencePlayer';

interface ClipTimelineProps {
  tracks: TrackData[];
  selectedTrackIdx: number;
  currentTime: number;
  duration?: number;
  tau?: number;
  fps?: number;
  onSeek: (timeInSeconds: number) => void;
}

export const ClipTimeline: React.FC<ClipTimelineProps> = ({
  tracks,
  selectedTrackIdx,
  currentTime,
  duration = 30.0,
  tau = 0.5,
  fps = 30.0,
  onSeek,
}) => {
  const activeTrack = tracks.find((t) => t.track_idx === selectedTrackIdx) || tracks[0];

  // Map clips to time series data points
  const chartData = (activeTrack?.clips || []).map((clip) => ({
    time: parseFloat(clip.start_s.toFixed(2)),
    score: parseFloat(clip.p.toFixed(3)),
    clipIdx: clip.k,
  }));

  // Sampling windows for long videos (> 30s): initial 8s + 4 spaced 32-frame windows (SPEC §2.3)
  const windowLen = 32.0 / fps;
  const isLongVideo = duration > 30.0;
  const samplingWindows = isLongVideo
    ? [
        { start: 0, end: 8 },
        { start: duration * 0.25, end: duration * 0.25 + windowLen },
        { start: duration * 0.5, end: duration * 0.5 + windowLen },
        { start: duration * 0.75, end: duration * 0.75 + windowLen },
        { start: Math.max(0, duration - windowLen), end: duration },
      ]
    : [{ start: 0, end: duration }];

  return (
    <div className="bg-surface border border-border rounded-lg p-4 shadow-sm flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-text">Clip Probability Timeline</span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-accent inline-block" />
            Track #{activeTrack ? activeTrack.track_idx : 0} Anomaly Curve
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-rose-500 font-mono">
            <span className="w-3 border-t-2 border-dashed border-rose-500 inline-block" />
            Decision Threshold τ = {tau.toFixed(2)}
          </span>
          <span className="text-gray-400">Click graph to seek video</span>
        </div>
      </div>

      <div className="w-full h-36">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 8, right: 12, left: -20, bottom: 0 }}
            onClick={(e) => {
              if (e && e.activePayload && e.activePayload[0]) {
                const clickedTime = e.activePayload[0].payload.time;
                onSeek(clickedTime);
              }
            }}
          >
            <defs>
              <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            {/* Shaded Sampling Windows */}
            {samplingWindows.map((win, idx) => (
              <ReferenceArea
                key={idx}
                x1={win.start}
                x2={win.end}
                fill="#888888"
                fillOpacity={0.08}
              />
            ))}

            <XAxis
              dataKey="time"
              type="number"
              domain={[0, Math.max(duration, 1)]}
              unit="s"
              tick={{ fontSize: 11, fill: '#888888' }}
              tickLine={{ stroke: '#888888' }}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1.0]}
              tick={{ fontSize: 11, fill: '#888888' }}
              tickLine={{ stroke: '#888888' }}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-surface border border-border shadow-md rounded p-2 text-xs">
                      <p className="font-semibold text-text">Clip #{data.clipIdx}</p>
                      <p className="text-muted">Timestamp: {data.time}s</p>
                      <p className="font-mono text-accent">p: {data.score}</p>
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* Horizontal Decision Threshold τ */}
            <ReferenceLine
              y={tau}
              stroke="#ef4444"
              strokeDasharray="4 4"
              strokeWidth={1.5}
            />

            {/* Vertical Video Playhead Cursor */}
            <ReferenceLine
              x={currentTime}
              stroke="#22c55e"
              strokeWidth={2}
            />

            <Area
              type="monotone"
              dataKey="score"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#scoreGradient)"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

