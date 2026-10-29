/** Shared helpers for drawing patch-evidence heat (illustrations and DEMO evidence only). */

// Approximate magma colormap stops (perceptually uniform, colour-blind safe).
const MAGMA: Array<[number, [number, number, number]]> = [
  [0, [0, 0, 4]],
  [0.25, [81, 18, 124]],
  [0.5, [183, 55, 121]],
  [0.75, [252, 137, 97]],
  [1, [252, 253, 191]],
];

export function magma(v: number): [number, number, number] {
  const x = Math.min(1, Math.max(0, v));
  for (let i = 1; i < MAGMA.length; i++) {
    const [p1, c1] = MAGMA[i];
    const [p0, c0] = MAGMA[i - 1];
    if (x <= p1) {
      const t = (x - p0) / (p1 - p0);
      return [0, 1, 2].map((j) => Math.round(c0[j] + (c1[j] - c0[j]) * t)) as [number, number, number];
    }
  }
  return MAGMA[MAGMA.length - 1][1];
}

export const magmaCss = (v: number, alpha = 1) => {
  const [r, g, b] = magma(v);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

/** Deterministic illustrative heat field (0–1) on a 16×16 grid, concentrated on the mouth/jaw. */
export function demoHeat(gx: number, gy: number, seed = 0): number {
  const cx = 7.5;
  const cy = 11.5;
  const d = Math.hypot((gx - cx) / 3.6, (gy - cy) / 2.2);
  const noise = Math.abs(Math.sin(gx * 12.9898 + gy * 78.233 + seed * 3.1) * 43758.5453) % 1;
  return Math.max(0, Math.min(1, Math.exp(-d * d) * 0.95 + (noise - 0.5) * 0.18));
}

/** Alpha floor used by the real evidence renderer (sv_engine/evidence.py): values below are transparent. */
export const HEAT_ALPHA_FLOOR = 0.15;
