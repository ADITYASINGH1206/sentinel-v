import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Flame,
  Eye,
  EyeOff,
  Maximize2,
  Volume2,
  VolumeX,
} from 'lucide-react';

export interface ClipScoreData {
  k: number;
  start_frame: number;
  end_frame: number;
  start_s: number;
  p: number;
}

export interface TrackData {
  track_idx: number;
  n_frames: number;
  u: number;
  p_bal: number;
  decisive: boolean;
  clips: ClipScoreData[];
}

interface EvidencePlayerProps {
  videoUrl?: string;
  tracks?: TrackData[];
  selectedTrackIdx: number;
  onSelectTrack: (idx: number) => void;
  currentTime?: number;
  onTimeUpdate?: (currentTime: number) => void;
  seekTime?: number;
  onOverlayToggled?: () => void;
  fps?: number;
}

export const EvidencePlayer: React.FC<EvidencePlayerProps> = ({
  videoUrl,
  tracks = [],
  selectedTrackIdx,
  onSelectTrack,
  onTimeUpdate,
  seekTime,
  onOverlayToggled,
  fps = 30.0,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [overlayVisible, setOverlayVisible] = useState<boolean>(true);
  const [opacity, setOpacity] = useState<number>(0.65);
  const [isMuted, setIsMuted] = useState<boolean>(true);

  // Synchronize seekTime prop from parent (e.g. timeline click)
  useEffect(() => {
    if (seekTime !== undefined && videoRef.current) {
      videoRef.current.currentTime = seekTime;
      setCurrentTime(seekTime);
    }
  }, [seekTime]);

  const activeTrack = tracks.find((t) => t.track_idx === selectedTrackIdx) || tracks[0];

  // Draw overlay canvas (bounding box & heatmap representation)
  const drawOverlay = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number, time: number) => {
      ctx.clearRect(0, 0, width, height);

      if (!overlayVisible) return;

      // TODO: Integrate actual bounding box, landmark, and heatmap data from M4 evidence API. Current implementation is simulated.
      // Find current clip probability for selected track
      const currentClip = activeTrack?.clips.find(
        (c) => time >= c.start_s && time <= c.start_s + 8.0 / fps
      );
      const suspicion = currentClip ? currentClip.p : activeTrack ? activeTrack.p_bal : 0.5;

      // Draw bounding box placeholder around facial region (center region simulation)
      const boxW = width * 0.35;
      const boxH = height * 0.45;
      const boxX = (width - boxW) / 2;
      const boxY = (height - boxH) / 2.2;

      ctx.save();
      ctx.globalAlpha = opacity;

      // Heatmap glow gradient inside face bounding box
      const gradient = ctx.createRadialGradient(
        boxX + boxW / 2,
        boxY + boxH / 2,
        boxW * 0.1,
        boxX + boxW / 2,
        boxY + boxH / 2,
        boxW * 0.6
      );

      if (suspicion > 0.6) {
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.85)'); // Red/Rose
        gradient.addColorStop(0.6, 'rgba(249, 115, 22, 0.55)'); // Orange
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
      } else if (suspicion > 0.35) {
        gradient.addColorStop(0, 'rgba(234, 179, 8, 0.75)'); // Amber/Yellow
        gradient.addColorStop(0.7, 'rgba(245, 158, 11, 0.4)');
        gradient.addColorStop(1, 'rgba(234, 179, 8, 0.0)');
      } else {
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.6)'); // Emerald
        gradient.addColorStop(0.8, 'rgba(5, 150, 105, 0.25)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
      }

      ctx.fillStyle = gradient;
      ctx.fillRect(boxX, boxY, boxW, boxH);

      // Track Bounding Box Stroke
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = suspicion > 0.6 ? '#ef4444' : suspicion > 0.35 ? '#f59e0b' : '#10b981';
      ctx.strokeRect(boxX, boxY, boxW, boxH);

      // Track Label Pill
      ctx.font = 'bold 12px monospace';
      ctx.fillStyle = ctx.strokeStyle;
      ctx.fillRect(boxX, boxY - 20, 110, 20);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(
        `Track #${activeTrack ? activeTrack.track_idx : 0} (p=${suspicion.toFixed(2)})`,
        boxX + 5,
        boxY - 6
      );

      // Simulated data indicator until M4 evidence API is integrated
      ctx.fillStyle = 'rgba(234, 179, 8, 0.85)';
      ctx.fillRect(boxX + 115, boxY - 20, 75, 20);
      ctx.font = 'bold 10px monospace';
      ctx.fillStyle = '#000000';
      ctx.fillText('SIMULATED', boxX + 120, boxY - 6);

      ctx.restore();
    },
    [overlayVisible, opacity, activeTrack, fps]
  );

  // Sync canvas with video animation frames
  useEffect(() => {
    let animId: number;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const render = () => {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
          canvas.width = video.clientWidth;
          canvas.height = video.clientHeight;
        }
        drawOverlay(ctx, canvas.width, canvas.height, video.currentTime);
      }
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => {
      if (animId) {
        cancelAnimationFrame(animId);
      }
    };
  }, [drawOverlay, overlayVisible, opacity, selectedTrackIdx]);

  // Video event handlers
  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);
    onTimeUpdate?.(t);
  };

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return;
    setDuration(videoRef.current.duration || 0);
  };

  const togglePlayPause = useCallback(() => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  }, [isPlaying]);

  const stepFrame = useCallback(
    (direction: -1 | 1) => {
      if (!videoRef.current) return;
      videoRef.current.pause();
      setIsPlaying(false);
      const newTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + direction * (1 / fps)));
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
      onTimeUpdate?.(newTime);
    },
    [duration, fps, onTimeUpdate]
  );

  const jumpToPeakClip = useCallback(() => {
    if (!activeTrack || activeTrack.clips.length === 0 || !videoRef.current) return;
    // Find clip with maximum anomaly score p
    let peakClip = activeTrack.clips[0];
    for (const c of activeTrack.clips) {
      if (c.p > peakClip.p) {
        peakClip = c;
      }
    }
    videoRef.current.currentTime = peakClip.start_s;
    setCurrentTime(peakClip.start_s);
    onTimeUpdate?.(peakClip.start_s);
  }, [activeTrack, onTimeUpdate]);

  const toggleOverlay = useCallback(() => {
    setOverlayVisible((prev) => !prev);
    onOverlayToggled?.();
  }, [onOverlayToggled]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = isMuted;
    }
  }, [isMuted]);

  // Global review hotkeys listener when player is mounted
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing into an input/textarea
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

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

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden flex flex-col shadow-sm">
      {/* Video & Canvas Container */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden group">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          playsInline
          muted={isMuted}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
        />

        {/* Sync Overlay Canvas */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none w-full h-full"
        />

        {/* Overlay Status Pill Top-Right */}
        <div className="absolute top-3 right-3 flex items-center gap-2 bg-black/70 backdrop-blur-sm px-2.5 py-1 rounded text-xs text-white">
          <Flame
            className={`w-3.5 h-3.5 ${
              overlayVisible ? 'text-amber-400' : 'text-gray-500'
            }`}
          />
          <span className="font-mono">
            {overlayVisible ? `Heatmap (${Math.round(opacity * 100)}%)` : 'Overlay Hidden'}
          </span>
        </div>
      </div>

      {/* Playback Controls & Toolbars */}
      <div className="p-3 bg-surface border-t border-border flex flex-col gap-2">
        {/* Scrubber Progress Bar */}
        <div className="flex items-center gap-2 text-xs font-mono text-muted">
          <span>{currentTime.toFixed(2)}s</span>
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
            className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-accent"
          />
          <span>{duration.toFixed(2)}s</span>
        </div>

        {/* Main Control Actions */}
        <div className="flex items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => stepFrame(-1)}
              title="Step Backward (Left Arrow)"
              aria-label="Step backward 1 frame"
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              onClick={togglePlayPause}
              title="Play/Pause (Space)"
              aria-label={isPlaying ? 'Pause video' : 'Play video'}
              className="p-2 rounded-full bg-accent text-white hover:opacity-90 transition-opacity"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button
              onClick={() => stepFrame(1)}
              title="Step Forward (Right Arrow)"
              aria-label="Step forward 1 frame"
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <button
              onClick={jumpToPeakClip}
              title="Jump to Peak Suspicion (P)"
              aria-label="Jump to peak suspicion clip"
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/60 transition-colors border border-amber-200 dark:border-amber-800"
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Peak Clip (P)</span>
            </button>
          </div>

          {/* Track Selector Buttons */}
          {tracks.length > 1 && (
            <div className="flex items-center gap-1 border-x border-border px-2">
              <span className="text-xs text-muted font-medium">Track:</span>
              {tracks.map((t) => (
                <button
                  key={t.track_idx}
                  onClick={() => onSelectTrack(t.track_idx)}
                  className={`px-2 py-0.5 text-xs font-mono rounded transition-colors ${
                    selectedTrackIdx === t.track_idx
                      ? 'bg-accent text-white font-bold'
                      : 'bg-surface hover:bg-gray-100 dark:hover:bg-gray-800 text-muted'
                  }`}
                >
                  #{t.track_idx} {t.decisive && '★'}
                </button>
              ))}
            </div>
          )}

          {/* Overlay & Audio Controls */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <button
                onClick={toggleOverlay}
                title="Toggle Heatmap Overlay (H)"
                aria-label={overlayVisible ? 'Hide heatmap overlay' : 'Show heatmap overlay'}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
              >
                {overlayVisible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4 text-gray-400" />}
              </button>
              <input
                type="range"
                min={0.1}
                max={1.0}
                step={0.05}
                value={opacity}
                onChange={(e) => setOpacity(parseFloat(e.target.value))}
                aria-label="Heatmap overlay opacity"
                title={`Overlay Opacity: ${Math.round(opacity * 100)}%`}
                className="w-16 h-1 bg-gray-200 dark:bg-gray-700 rounded appearance-none cursor-pointer accent-accent"
              />
            </div>

            <button
              onClick={() => setIsMuted(!isMuted)}
              title={isMuted ? 'Unmute' : 'Mute'}
              aria-label={isMuted ? 'Unmute video audio' : 'Mute video audio'}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>

            <button
              onClick={() => videoRef.current?.requestFullscreen?.()}
              title="Toggle Fullscreen"
              aria-label="Toggle fullscreen"
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-muted hover:text-text transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
