import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BandChip } from '../components/BandChip';
import { ScoreReadout } from '../components/ScoreReadout';
import { Dashboard } from '../routes/Dashboard';
import { ReviewWorkspace } from '../routes/ReviewWorkspace';

describe('Reviewer Console UI Components (SPEC §14)', () => {
  describe('BandChip', () => {
    it('renders Likely authentic with correct label', () => {
      render(<BandChip band="likely_authentic" />);
      expect(screen.getByText('Likely authentic')).toBeDefined();
    });

    it('renders Needs review with correct label', () => {
      render(<BandChip band="needs_review" />);
      expect(screen.getByText('Needs review')).toBeDefined();
    });

    it('renders Likely manipulated with correct label', () => {
      render(<BandChip band="likely_manipulated" />);
      expect(screen.getByText('Likely manipulated')).toBeDefined();
    });

    it('renders Inconclusive with correct label', () => {
      render(<BandChip band="inconclusive" />);
      expect(screen.getByText('Inconclusive')).toBeDefined();
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
    it('renders review queue with triage metrics and actions', () => {
      const handleStart = vi.fn();
      const handleView = vi.fn();
      render(<Dashboard onStartReview={handleStart} onViewCase={handleView} />);

      expect(screen.getByText('Reviewer Console')).toBeDefined();
      expect(screen.getByText(/Start Review Queue/)).toBeDefined();
      expect(screen.getByText('an_queue_8841')).toBeDefined();
    });

    it('triggers review callback on button click', () => {
      const handleStart = vi.fn();
      const handleView = vi.fn();
      render(<Dashboard onStartReview={handleStart} onViewCase={handleView} />);

      const reviewButtons = screen.getAllByRole('button', { name: /Review/i });
      fireEvent.click(reviewButtons[0]);
      expect(handleStart).toHaveBeenCalled();
    });
  });

  describe('ReviewWorkspace', () => {
    it('renders triage options with keyboard shortcut hints', () => {
      render(<ReviewWorkspace />);

      expect(screen.getByText('Reviewer Triage')).toBeDefined();
      expect(screen.getByText('Likely Authentic')).toBeDefined();
      expect(screen.getByText('Likely Manipulated')).toBeDefined();
      expect(screen.getByText('Cannot Tell / Inconclusive')).toBeDefined();
      expect(screen.getByText(/Submit & Next/)).toBeDefined();
    });

    it('allows selecting determination via button click', () => {
      render(<ReviewWorkspace />);

      const manipulatedBtn = screen.getByRole('button', { name: /Likely Manipulated/i });
      fireEvent.click(manipulatedBtn);

      const submitBtn = screen.getByRole('button', { name: /Submit & Next/i });
      expect(submitBtn.hasAttribute('disabled')).toBe(false);
    });
  });
});

