import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { baseRate, platt, priorCorrect } from '../utils/calibration';
import paperA from '../content/sourced/paper_a_operating_points.json';
import { validateCopy } from '../copy/forbidden';
import { api, ApiError } from '../data/api';
import { computeFileSha256, bytesToHex } from '../utils/verifier';
import { bandFor, demoCases } from '../data/demo';
import Home from '../pages/marketing/Home';
import { renderWithProviders } from './helpers';

describe('calibration maths (SPEC §6.5, §7.4)', () => {
  it('reproduces the Stage B Platt example and prior correction', () => {
    const p = platt(1.66);
    expect(p).toBeCloseTo(0.62, 2);
    expect(priorCorrect(p, 0.01)).toBeCloseTo(0.016, 3);
    expect(priorCorrect(0.37, 0.5)).toBeCloseTo(0.37, 10);
  });

  it('matches the base-rate table: Full @ 1% FPR, 1% prevalence', () => {
    const r = baseRate(paperA.models.Full.fpr_1, 0.01, 0.01);
    expect((r.precision * 100).toFixed(1)).toBe('28.5');
    expect(Math.round(r.flagsPer10k)).toBe(138);
  });
});

describe('demo data is internally consistent', () => {
  it('derives every band from its own score', () => {
    for (const c of demoCases()) {
      if (c.pBal != null && c.band && c.band !== 'inconclusive') expect(c.band).toBe(bandFor(c.pBal));
      if (c.u != null && c.pBal != null) expect(c.pBal).toBeCloseTo(platt(c.u), 3);
      expect(c.isDemo).toBe(true);
    }
  });
});

describe('API client', () => {
  afterEach(() => vi.restoreAllMocks());

  it('surfaces a 422 from POST /v1/reviews instead of reporting success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: [{ loc: ['body', 'confidence'], msg: 'Field required' }] }), { status: 422, headers: { 'Content-Type': 'application/json' } })
    );
    await expect(api.submitReview('an_x', { decision: 'authentic', reasons: [], notes: null, confidence: 3, telemetry: {} })).rejects.toMatchObject({
      status: 422,
      code: 'VALIDATION_ERROR',
    });
  });

  it('reports an unreachable API as status 0', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    const err = await api.getAnalysis('an_x').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });
});

describe('streamed SHA-256', () => {
  it('matches WebCrypto across several chunks', async () => {
    const bytes = new TextEncoder().encode('VeriFrame streamed hashing test vector — three chunks or more.');
    const expected = bytesToHex(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)));
    const progress: number[] = [];
    const got = await computeFileSha256(new Blob([bytes]), (f) => progress.push(f), 16);
    expect(got).toBe(expected);
    expect(progress.length).toBeGreaterThanOrEqual(3);
    expect(progress[progress.length - 1]).toBe(1);
  });
});

describe('copy and brand guards', () => {
  it('home page copy passes the SPEC §14.13 copy rules', async () => {
    renderWithProviders(<Home />);
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toBeDefined());
    const text = document.body.textContent ?? '';
    expect(text.length).toBeGreaterThan(500);
    expect(validateCopy(text)).toEqual({ valid: true });
  });

  it('no user-facing "SENTINEL-V" remains in the web app', () => {
    const files = import.meta.glob(['../**/*.{ts,tsx}', '!../**/__tests__/**', '!../brand.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
    const offenders = Object.entries(files)
      .filter(([, src]) => /SENTINEL-V/.test(src))
      .map(([path]) => path);
    expect(Object.keys(files).length).toBeGreaterThan(20);
    expect(offenders).toEqual([]);
  });
});
