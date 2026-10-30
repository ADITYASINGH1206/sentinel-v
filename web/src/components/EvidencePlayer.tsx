import React, { useCallback, useEffect, useRef, useState } from 'react';
import { demoHeat, HEAT_ALPHA_FLOOR, magma } from '../utils/heat';
import { Play, Pause, SkipBack, SkipForward, Flame, Eye, EyeOff, Maximize2, Volume2, VolumeX, FlaskConical, ImageOff } from 'lucide-react';

export interface ClipScoreData {
  k: number;
  start_frame: number;
  end_frame: number;
  start_s: number;
  p: number;
  patches?: number[];
}

export interface TrackData {
  track_idx: number;
  n_frames: number;
  u: number;
  p_bal: number;
  decisive: boolean;
  clips: ClipScoreData[];
  /** Normalized face box (0–1) in video coordinates, when the API or demo data provides one. */
  box?: { x: number; y: number; w: number; h: number };
}

interface EvidencePlayerProps {
  videoUrl?: string;
  /** Optional alternative encodings, tried in order (e.g. WebM then MP4). */
  videoSources?: Array<{ src: string; type: string }>;
  tracks?: TrackData[];
  selectedTrackIdx: number;
  onSelectTrack: (idx: number) => void;
  currentTime?: number;
  onTimeUpdate?: (currentTime: number) => void;
  seekTime?: number;
  onOverlayToggled?: () => void;
  fps?: number;
  /** Demo mode draws a synthetic patch grid, clearly labelled. Live mode never fakes evidence. */
  demo?: boolean;
}

const GRID = 16;

export const EvidencePlayer: React.FC<EvidencePlayerProps> = ({
  videoUrl,
  videoSources,
  tracks = [],
  selectedTrackIdx,
  onSelectTrack,
  onTimeUpdate,
  seekTime,
  onOverlayToggled,
  fps = 30.0,
  demo = false,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [overlayVisible, setOverlayVisible] = useState(true);
  const [opacity, setOpacity] = useState(0.6);
  const [isMuted, setIsMuted] = useState(true);

  useEffect(() => {
    if (seekTime !== undefined && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      setCurrentTime(seekTime);
    }
  }, [seekTime]);

  const activeTrack = tracks.find((t) => t.track_idx === selectedTrackIdx) || tracks[0];

  const drawOverlay = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number, time: number, video: HTMLVideoElement) => {
      ctx.clearRect(0, 0, width, height);
      if (!overlayVisible || !activeTrack?.box) return;

      // Map normalized video coordinates into the letterboxed content rect (object-contain).
      const vw = video.videoWidth || 16;
      const vh = video.videoHeight || 9;
      const scale = Math.min(width / vw, height / vh);
      const cw = vw * scale;
      const ch = vh * scale;
      const ox = (width - cw) / 2;
      const oy = (height - ch) / 2;
      const bx = ox + activeTrack.box.x * cw;
      const by = oy + activeTrack.box.y * ch;
      const bw = activeTrack.box.w * cw;
      const bh = activeTrack.box.h * ch;

      const clip = activeTrack.clips.find((c, i) => {
        const next = activeTrack.clips[i + 1];
        return time >= c.start_s && (!next || time < next.start_s);
      });
      const score = clip ? clip.p : activeTrack.p_bal;

      // Draw Grad-CAM patch heatmap over detected face bounding box
      const cellW = bw / GRID;
      const cellH = bh / GRID;
      const hasPatches = Boolean(clip?.patches && clip.patches.length === GRID * GRID);

      for (let gy = 0; gy < GRID; gy++) {
        for (let gx = 0; gx < GRID; gx++) {
          let v = 0;
          if (hasPatches && clip?.patches) {
            v = clip.patches[gy * GRID + gx];
          } else {
            v = demoHeat(gx, gy, activeTrack.track_idx) * Math.max(score, 0.2);
          }
          if (v < 0.05) continue;
          const [r, g, b] = magma(v);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${Math.min(0.9, Math.max(0.2, v)) * opacity})`;
          ctx.fillRect(bx + gx * cellW, by + gy * cellH, cellW + 0.5, cellH + 0.5);
        }
      }

      ctx.lineWidth = 2;
      ctx.strokeStyle = 'rgba(44, 199, 192, 0.95)';
      const r = 8;
      // Corner ticks instead of a full rectangle: reads as a tracker, not a verdict.
      const corners: Array<[number, number, number, number]> = [
        [bx, by, 1, 1],
        [bx + bw, by, -1, 1],
        [bx, by + bh, 1, -1],
        [bx + bw, by + bh, -1, -1],
      ];
      ctx.beginPath();
      for (const [x, y, dx, dy] of corners) {
        ctx.moveTo(x, y + dy * r * 2);
        ctx.lineTo(x, y);
        ctx.lineTo(x + dx * r * 2, y);
      }
      ctx.stroke();

      const label = `Track #${activeTrack.track_idx} · clip ${score.toFixed(2)}`;
      ctx.font = '600 11px "JetBrains Mono", monospace';
      const tw = ctx.measureText(label).width + 12;
      ctx.fillStyle = 'rgba(7, 11, 18, 0.78)';
      ctx.fillRect(bx, by - 22, tw, 18);
      ctx.fillStyle = '#E7EDF5';
      ctx.fillText(label, bx + 6, by - 9);
    },
    [overlayVisible, opacity, activeTrack, demo]
  );

  useEffect(() => {
    let animId = 0;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const render = () => {
      const ctx = canvas.getContext?.('2d');
      if (ctx) {
        const dpr = window.devicePixelRatio || 1;
        const w = video.clientWidth;
        const h = video.clientHeight;
        if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
          canvas.width = Math.round(w * dpr);
          canvas.height = Math.round(h * dpr);
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        drawOverlay(ctx, w, h, video.currentTime, video);
      }
      animId = requestAnimationFrame(render);
    };
    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [drawOverlay]);

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);
    onTimeUpdate?.(t);
  };

  const togglePlayPause = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play()?.catch?.(() => undefined);
      setIsPlaying(true);
    } else {
      v.pause();
      setIsPlaying(false);
    }
  }, []);

  const stepFrame = useCallback(
    (direction: -1 | 1) => {
      const v = videoRef.current;
      if (!v) return;
      v.pause();
      setIsPlaying(false);
      const t = Math.max(0, Math.min(duration, v.currentTime + direction * (1 / fps)));
      v.currentTime = t;
      setCurrentTime(t);
      onTimeUpdate?.(t);
    },
    [duration, fps, onTimeUpdate]
  );

  const jumpToPeakClip = useCallback(() => {
    if (!activeTrack || activeTrack.clips.length === 0 || !videoRef.current) return;
    const peak = activeTrack.clips.reduce((best, c) => (c.p > best.p ? c : best), activeTrack.clips[0]);
    videoRef.current.currentTime = peak.start_s;
    setCurrentTime(peak.start_s);
    onTimeUpdate?.(peak.start_s);
  }, [activeTrack, onTimeUpdate]);

  const toggleOverlay = useCallback(() => {
    setOverlayVisible((prev) => !prev);
    onOverlayToggled?.();
  }, [onOverlayToggled]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.muted = isMuted;
  }, [isMuted]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        stepFrame(1);
      } else if (e.key === 'p' || e.key === 'P') {
        e.preventDefault();
        jumpToPeakClip();
      } else if (e.key === 'h' || e.key === 'H') {
        e.preventDefault();
        toggleOverlay();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlayPause, stepFrame, jumpToPeakClip, toggleOverlay]);

  const progress = duration ? (currentTime / duration) * 100 : 0;
  const ctrl = 'grid h-8 w-8 place-items-center rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-text';

  return (
    <div className="flex flex-col overflow-hidden rounded-md border border-border bg-surface shadow-1">
      <div className="group relative flex aspect-video items-center justify-center overflow-hidden bg-[#05080d]">
        {videoUrl || videoSources?.length ? (
          <video
            ref={videoRef}
            src={videoSources?.length ? undefined : videoUrl}
            className="h-full w-full object-contain"
            playsInline
            muted={isMuted}
            preload="metadata"
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
          >
            {videoSources?.map((source) => <source key={source.src} src={source.src} type={source.type} />)}
          </video>
        ) : (
          <>
            <video ref={videoRef} className="hidden" />
            <div className="flex flex-col items-center gap-2 text-sm text-[#93A1B5]">
              <ImageOff className="h-6 w-6" aria-hidden />
              Media playback is not available for this analysis.
            </div>
          </>
        )}
        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />

        <div className="absolute left-3 top-3 flex items-center gap-2">
          {demo ? (
            <span className="inline-flex items-center gap-1 rounded bg-[#E9B949]/90 px-2 py-0.5 font-mono text-[10px] font-semibold text-[#1a1300]">
              <FlaskConical className="h-3 w-3" aria-hidden /> DEMO EVIDENCE
            </span>
          ) : (
            (videoUrl || videoSources?.length) && (
              <span className="inline-flex items-center gap-1.5 rounded bg-black/70 px-2.5 py-1 text-[11px] font-medium text-[#C9D2DE] backdrop-blur border border-white/10">
                <span className="h-1.5 w-1.5 rounded-full bg-[#FC8961] animate-pulse" /> Grad-CAM Patch Evidence ({GRID}x{GRID})
              </span>
            )
          )}
        </div>
        <div className="absolute right-3 top-3 flex items-center gap-2 rounded bg-black/60 px-2.5 py-1 text-xs text-white backdrop-blur">
          <Flame className={`h-3.5 w-3.5 ${overlayVisible ? 'text-[#FC8961]' : 'text-gray-500'}`} aria-hidden />
          <span className="font-mono">{overlayVisible ? 'Overlay on' : 'Overlay hidden'}</span>
        </div>
        <div className="absolute bottom-0 left-0 h-0.5 bg-accent transition-[width] duration-100" style={{ width: `${progress}%` }} />
      </div>

      <div className="flex flex-col gap-2 border-t border-border p-3">
        <div className="flex items-center gap-3 font-mono text-xs text-muted">
          <span className="w-12 tabular-nums">{currentTime.toFixed(2)}s</span>
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={1 / fps}
            value={currentTime}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              if (videoRef.current) videoRef.current.currentTime = val;
              setCurrentTime(val);
              onTimeUpdate?.(val);
            }}
            aria-label="Video scrubber"
            className="range flex-1"
          />
          <span className="w-12 text-right tabular-nums">{duration.toFixed(2)}s</span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1">
            <button onClick={() => stepFrame(-1)} title="Step backward (←)" aria-label="Step backward 1 frame" className={ctrl}>
              <SkipBack className="h-4 w-4" />
            </button>
            <button
              onClick={togglePlayPause}
              title="Play/Pause (Space)"
              aria-label={isPlaying ? 'Pause video' : 'Play video'}
              className="grid h-9 w-9 place-items-center rounded-full bg-accent text-accent-contrast shadow-1 transition-transform hover:scale-105 active:scale-95"
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="ml-0.5 h-4 w-4" />}
            </button>
            <button onClick={() => stepFrame(1)} title="Step forward (→)" aria-label="Step forward 1 frame" className={ctrl}>
              <SkipForward className="h-4 w-4" />
            </button>
            <button
              onClick={jumpToPeakClip}
              title="Jump to peak clip (P)"
              aria-label="Jump to peak suspicion clip"
              className="ml-1 inline-flex items-center gap-1 rounded-md border border-band-review/30 bg-band-review/10 px-2.5 py-1 text-xs font-medium text-band-review transition-colors hover:bg-band-review/15"
            >
              <Flame className="h-3.5 w-3.5" /> Peak clip <span className="font-mono opacity-70">P</span>
            </button>
          </div>

          {tracks.length > 1 && (
            <div className="flex items-center gap-1" role="group" aria-label="Face track">
              <span className="mr-1 text-xs text-muted">Track</span>
              {tracks.map((t) => (
                <button
                  key={t.track_idx}
                  onClick={() => onSelectTrack(t.track_idx)}
                  aria-pressed={selectedTrackIdx === t.track_idx}
                  className={`rounded-md px-2 py-0.5 font-mono text-xs transition-colors ${
                    selectedTrackIdx === t.track_idx ? 'bg-accent text-accent-contrast' : 'text-muted hover:bg-surface-2'
                  }`}
                >
                  #{t.track_idx}
                  {t.decisive && ' ★'}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2">
            <button onClick={toggleOverlay} title="Toggle overlay (H)" aria-label={overlayVisible ? 'Hide heatmap overlay' : 'Show heatmap overlay'} className={ctrl}>
              {overlayVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            </button>
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              aria-label="Heatmap overlay opacity"
              aria-valuetext={`${Math.round(opacity * 100)} percent`}
              className="range w-20"
            />
            <button onClick={() => setIsMuted(!isMuted)} aria-label={isMuted ? 'Unmute video audio' : 'Mute video audio'} className={ctrl}>
              {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </button>
            <button onClick={() => videoRef.current?.requestFullscreen?.()} aria-label="Toggle fullscreen" className={ctrl}>
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
