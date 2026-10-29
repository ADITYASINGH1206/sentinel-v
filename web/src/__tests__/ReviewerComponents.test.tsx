import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BandChip } from '../components/BandChip';
import { ScoreReadout } from '../components/ScoreReadout';
import { ClipTimeline } from '../components/ClipTimeline';
import Dashboard from '../pages/console/Dashboard';
import { ReviewWorkspace } from '../pages/console/ReviewWorkspace';
import { demoReviewQueue } from '../data/demo';
import { renderWithProviders, setDemoDataMode } from './helpers';

describe('Reviewer Console UI Components (SPEC §14)', () => {
  beforeEach(() => {
    setDemoDataMode();
  });

  describe('BandChip', () => {
    it.each([
      ['likely_authentic', 'Likely authentic'],
      ['needs_review', 'Needs review'],
      ['likely_manipulated', 'Likely manipulated'],
      ['inconclusive', 'Inconclusive'],
    ] as const)('renders %s as "%s"', (band, label) => {
      render(<BandChip band={band} />);
      expect(screen.getByText(label)).toBeDefined();
    });
  });

  describe('ScoreReadout', () => {
    it('formats calibrated score to exactly 2 decimal places', () => {
      render(<ScoreReadout p_bal={0.634289} prior_prevalence={0.01} />);
      expect(screen.getByText('Score 0.63')).toBeDefined();
    });

    it('displays prevalence adjustment when p_prior is supplied', () => {
      render(<ScoreReadout p_bal={0.63} p_prior={0.018} prior_prevalence={0.01} />);
      expect(screen.getByText(/≈ 1.8% at 1% prevalence/)).toBeDefined();
    });
  });

  describe('Dashboard', () => {
    it('renders KPIs and labels demo data', async () => {
      renderWithProviders(<Dashboard />);
      expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeDefined();
      await waitFor(() => expect(screen.getAllByText('DEMO DATA').length).toBeGreaterThan(0));
      expect(screen.getAllByText('Needs review').length).toBeGreaterThan(0);
      expect(screen.getByText(/Start reviewing/)).toBeDefined();
    });

    it('does not show invented triage metrics', async () => {
      renderWithProviders(<Dashboard />);
      await waitFor(() => screen.getAllByText('DEMO DATA'));
      expect(screen.queryByText(/Avg Triage Speed/i)).toBeNull();
    });
  });

  describe('ReviewWorkspace', () => {
    const caseId = demoReviewQueue()[0].id;

    it('renders the decisions the API accepts, with keyboard hints', async () => {
      renderWithProviders(<ReviewWorkspace />, { route: `/app/review/${caseId}`, path: '/app/review/:id' });
      await waitFor(() => expect(screen.getByText('Reviewer decision')).toBeDefined());
      expect(screen.getByRole('radio', { name: /Authentic/ })).toBeDefined();
      expect(screen.getByRole('radio', { name: /Manipulated/ })).toBeDefined();
      expect(screen.getByRole('radio', { name: /Can't tell/ })).toBeDefined();
      expect(screen.getByRole('button', { name: /Submit & next/ }).hasAttribute('disabled')).toBe(true);
    });

    it('selects a decision by click and by keyboard', async () => {
      renderWithProviders(<ReviewWorkspace />, { route: `/app/review/${caseId}`, path: '/app/review/:id' });
      await waitFor(() => screen.getByText('Reviewer decision'));
      fireEvent.click(screen.getByRole('radio', { name: /Manipulated/ }));
      expect(screen.getByRole('radio', { name: /Manipulated/ }).getAttribute('aria-checked')).toBe('true');
      fireEvent.keyDown(window, { key: '1', code: 'Digit1' });
      await waitFor(() => expect(screen.getByRole('radio', { name: /Authentic/ }).getAttribute('aria-checked')).toBe('true'));
      expect(screen.getByRole('button', { name: /Submit & next/ }).hasAttribute('disabled')).toBe(false);
    });
  });

  describe('ClipTimeline', () => {
    it('renders timeline with required props', () => {
      const handleSeek = vi.fn();
      render(
        <ClipTimeline
          tracks={[
            {
              track_idx: 0,
              n_frames: 900,
              u: 1.25,
              p_bal: 0.72,
              decisive: true,
              clips: [{ k: 0, start_frame: 0, end_frame: 32, start_s: 0, p: 0.72 }],
            },
          ]}
          selectedTrackIdx={0}
          currentTime={0}
          duration={30.0}
          tau={0.5}
          fps={30.0}
          onSeek={handleSeek}
        />
      );
      expect(screen.getByText('Clip Probability Timeline')).toBeDefined();
      expect(screen.getByText(/Decision Threshold/)).toBeDefined();
    });
  });
});
