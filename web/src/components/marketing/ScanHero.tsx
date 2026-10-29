import React, { useEffect, useMemo, useRef, useState } from 'react';
import { m } from 'framer-motion';
import { BandChip } from '../BandChip';
import { demoHeat, HEAT_ALPHA_FLOOR, magmaCss } from '../../utils/heat';
import { platt, priorCorrect } from '../../utils/calibration';
import hero from '../../content/sourced/hero_illustration.json';
import { bandFor, DEMO_PRESETS } from '../../data/demo';

const BOX = { x: 148, y: 72, w: 184, h: 236 };
const GRID = 16;

/**
 * Original animated illustration: an abstract geometric face scanned line by line, with a
 * patch grid lighting up behind the scan line. Not a real analysis (labelled in the UI).
 */
export const ScanHero: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const obs = new IntersectionObserver(([entry]) => setPaused(!entry.isIntersecting), { threshold: 0.05 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const cells = useMemo(() => {
    const out: Array<{ gx: number; gy: number; v: number }> = [];
    for (let gy = 0; gy < GRID; gy++) {
      for (let gx = 0; gx < GRID; gx++) {
        const v = demoHeat(gx, gy, 2);
        if (v >= HEAT_ALPHA_FLOOR) out.push({ gx, gy, v });
      }
    }
    return out;
  }, []);

  const pBal = platt(hero.u);
  const pPrior = priorCorrect(pBal, hero.prior_prevalence);
  const band = bandFor(pBal);
  const cw = BOX.w / GRID;
  const ch = BOX.h / GRID;

  const tauHigh = DEMO_PRESETS['strict-low-fpr'].thresholds.tau_manipulated;
  // Illustrative clip-score shape for the mini timeline (not data).
  const spark = [0.31, 0.36, 0.42, 0.58, 0.71, 0.64, 0.47, 0.39];
  const sparkPath = spark.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (spark.length - 1)) * 160} ${40 - v * 36}`).join(' ');

  return (
    <div ref={ref} className="relative mx-auto w-full max-w-[520px]">
      <div className="absolute -inset-10 -z-10 rounded-[40px] bg-gradient-to-br from-accent/25 via-violet/10 to-transparent blur-3xl" aria-hidden />
      <div
        className="vf-scan relative overflow-hidden rounded-lg border border-white/10 bg-[#070B12] shadow-2"
        data-paused={paused ? 'true' : 'false'}
      >
        <svg viewBox="0 0 480 400" className="block h-auto w-full" role="img" aria-labelledby="scan-hero-title">
          <title id="scan-hero-title">Illustration of a face being scanned patch by patch; brighter patches mark where a detector found evidence.</title>
          <defs>
            <linearGradient id="hero-bg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#0D1828" />
              <stop offset="1" stopColor="#0A0F1A" />
            </linearGradient>
            <linearGradient id="hero-scan" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#2CC7C0" stopOpacity="0" />
              <stop offset="0.85" stopColor="#2CC7C0" stopOpacity="0.25" />
              <stop offset="1" stopColor="#2CC7C0" stopOpacity="0.95" />
            </linearGradient>
            <pattern id="hero-dots" width="16" height="16" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="#1E2A3B" />
            </pattern>
          </defs>
          <rect width="480" height="400" fill="url(#hero-bg)" />
          <rect width="480" height="400" fill="url(#hero-dots)" opacity="0.8" />

          {/* abstract subject */}
          <ellipse cx="240" cy="420" rx="170" ry="90" fill="#1A2A3F" />
          <rect x="214" y="290" width="52" height="60" rx="16" fill="#3A4B62" />
          <ellipse cx="240" cy="190" rx="92" ry="118" fill="#54657E" />
          <path d="M148 168c4-64 44-98 92-98s88 34 92 98c-22-30-56-42-92-42s-70 12-92 42z" fill="#2A3850" />
          <path d="M196 170q12-9 24 0M260 170q12-9 24 0" stroke="#C9D2DE" strokeWidth="4" fill="none" strokeLinecap="round" />
          <path d="M240 180l-8 34 12 3" stroke="#8C9AAF" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M212 250q28 16 56 0" stroke="#C9D2DE" strokeWidth="4" fill="none" strokeLinecap="round" />

          {/* patch evidence grid */}
          <g>
            {cells.map(({ gx, gy, v }) => (
              <rect
                key={`${gx}-${gy}`}
                className="scan-cell"
                x={BOX.x + gx * cw + 0.6}
                y={BOX.y + gy * ch + 0.6}
                width={cw - 1.2}
                height={ch - 1.2}
                rx="1.5"
                fill={magmaCss(v)}
                style={{ ['--o' as string]: String(0.25 + v * 0.65), ['--row' as string]: String(gy) }}
              />
            ))}
          </g>
          <rect x={BOX.x} y={BOX.y} width={BOX.w} height={BOX.h} fill="none" stroke="#1E2A3B" strokeDasharray="2 4" />

          {/* scan line */}
          <g className="scan-line">
            <rect x={BOX.x - 24} y={BOX.y - 40} width={BOX.w + 48} height="40" fill="url(#hero-scan)" />
            <rect x={BOX.x - 24} y={BOX.y - 1} width={BOX.w + 48} height="2" fill="#2CC7C0" />
          </g>

          {/* tracker corners */}
          <path
            d={`M${BOX.x} ${BOX.y + 22}V${BOX.y}h22M${BOX.x + BOX.w - 22} ${BOX.y}h22v22M${BOX.x + BOX.w} ${BOX.y + BOX.h - 22}v22h-22M${BOX.x + 22} ${BOX.y + BOX.h}h-22v-22`}
            fill="none"
            stroke="#2CC7C0"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <rect x={BOX.x} y={BOX.y - 24} width="128" height="18" rx="3" fill="rgba(7,11,18,0.85)" />
          <text x={BOX.x + 7} y={BOX.y - 11} fill="#E7EDF5" fontFamily="JetBrains Mono, monospace" fontSize="10.5" fontWeight="600">
            track #0 · 16×16 patches
          </text>

          {/* frame corners */}
          <path d="M24 52V24h28M428 24h28v28M456 348v28h-28M52 376H24v-28" fill="none" stroke="#2A3850" strokeWidth="2" />
        </svg>

        <span className="absolute right-3 top-3 rounded bg-white/10 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-[#C9D2DE] backdrop-blur">
          ILLUSTRATION
        </span>
      </div>

      <m.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.45, ease: [0.3, 0, 0, 1] }}
        className="relative z-10 mx-auto -mt-14 w-[260px] rounded-md border border-border bg-surface/95 p-4 shadow-2 backdrop-blur sm:absolute sm:-bottom-8 sm:-left-8 sm:mt-0"
      >
        <div className="mb-2 flex items-center justify-between gap-2">
          <BandChip band={band} size="sm" />
          <span className="font-mono text-[10px] text-muted">example</span>
        </div>
        <p className="font-mono text-2xl font-semibold text-text">Score {pBal.toFixed(2)}</p>
        <p className="text-xs text-muted">
          ≈ {(pPrior * 100).toFixed(1)}% at {(hero.prior_prevalence * 100).toFixed(0)}% prevalence
        </p>
        <svg viewBox="0 0 160 44" className="mt-3 h-10 w-full" aria-hidden>
          <line x1="0" x2="160" y1={40 - tauHigh * 36} y2={40 - tauHigh * 36} stroke="rgb(var(--band-manipulated))" strokeDasharray="3 3" strokeWidth="1" />
          <m.path
            d={sparkPath}
            fill="none"
            stroke="rgb(var(--accent))"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: 0.8, duration: 0.9, ease: [0.3, 0, 0, 1] }}
          />
        </svg>
      </m.div>
      <p className="mt-3 text-center text-xs text-muted sm:text-right">Illustration — not an actual analysis.</p>
    </div>
  );
};
