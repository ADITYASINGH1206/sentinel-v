/**
 * Single source of truth for product naming in the web app.
 * The product was previously called "SENTINEL-V" (see docs/DECISIONS.md, ADR 007).
 * Internal identifiers (sv_* packages, SV_ env vars, sv-receipt/1) are intentionally unchanged.
 */
export const BRAND = {
  name: 'VeriFrame',
  slug: 'veriframe',
  short: 'VF',
  tagline: 'Calibrated, explainable, verifiable video deepfake screening.',
  consoleName: 'VeriFrame Console',
  detectorFamily: 'S-MSDT',
  repoUrl: 'https://github.com/ADITYASINGH1206/sentinel-v',
} as const;
