import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, isUnavailable } from './api';
import { DEMO_PRESETS, demoCase, demoCases, demoReviewQueue, toSummary } from './demo';
import { baseRate } from '../utils/calibration';
import paperA from '../content/sourced/paper_a_operating_points.json';
import type { CaseSummary, CaseView, PolicyPreset, ReviewPayload } from './types';

export interface WithSource<T> {
  data: T;
  isDemo: boolean;
}

function forceDemo(): boolean {
  if (import.meta.env?.VITE_DATA_MODE === 'demo') return true;
  try {
    return window.localStorage.getItem('vf.dataMode') === 'demo';
  } catch {
    return false;
  }
}

/** Cases list. The API has no list endpoint yet, so this falls back to labelled demo data. */
export function useCases() {
  return useQuery<WithSource<CaseSummary[]>>({
    queryKey: ['cases'],
    queryFn: async () => {
      if (forceDemo()) return { data: demoCases().map(toSummary), isDemo: true };
      try {
        return { data: await api.listAnalyses(), isDemo: false };
      } catch (err) {
        if (isUnavailable(err)) return { data: demoCases().map(toSummary), isDemo: true };
        throw err;
      }
    },
  });
}

/** One analysis. Demo ids resolve locally; real ids always come from the API (no silent fallback). */
export function useCase(id: string | undefined) {
  return useQuery<CaseView>({
    queryKey: ['case', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const demo = id ? demoCase(id) : undefined;
      if (demo) return demo;
      return api.getAnalysis(id as string);
    },
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === 'queued' || s === 'processing' ? 1500 : false;
    },
  });
}

export function useReviewQueue() {
  return useQuery<WithSource<CaseView[]>>({
    queryKey: ['review-queue'],
    queryFn: async () => {
      if (forceDemo()) return { data: demoReviewQueue(), isDemo: true };
      try {
        const res = await api.getReviewQueue();
        const ids: string[] = (res.items ?? []).map((i: { id?: string; analysis_id?: string }) => i.id ?? i.analysis_id ?? '');
        const cases = await Promise.all(ids.filter(Boolean).map((i) => api.getAnalysis(i)));
        return { data: cases, isDemo: false };
      } catch (err) {
        if (isUnavailable(err)) return { data: demoReviewQueue(), isDemo: true };
        throw err;
      }
    },
  });
}

export function useSubmitReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ analysisId, payload, isDemo }: { analysisId: string; payload: ReviewPayload; isDemo: boolean }) => {
      if (isDemo) {
        await new Promise((r) => setTimeout(r, 250));
        return { review_id: `rv_demo_${Date.now().toString(36)}`, receipt_id: `rcpt_demo_review_${analysisId.slice(-4)}`, status: 'demo', demo: true };
      }
      const res = await api.submitReview(analysisId, payload);
      return { ...res, demo: false };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] });
    },
  });
}

export function usePresets() {
  return useQuery<WithSource<Record<string, PolicyPreset>>>({
    queryKey: ['presets'],
    queryFn: async () => {
      if (forceDemo()) return { data: DEMO_PRESETS, isDemo: true };
      try {
        return { data: await api.getPresets(), isDemo: false };
      } catch (err) {
        if (isUnavailable(err)) return { data: DEMO_PRESETS, isDemo: true };
        throw err;
      }
    },
    staleTime: 5 * 60_000,
  });
}

export type ModelKey = keyof typeof paperA.models;
const VARIANT: Record<ModelKey, string> = { S: 'smsdt-s-a', ST: 'smsdt-st-b', Full: 'smsdt-full-c' };

export interface SimulationView {
  precision: number;
  tpr: number;
  fpr: number;
  per10k: { flags: number; caught: number; falseAlarms: number; missed: number };
  daily: { flags: number; caught: number; falseAlarms: number; missed: number; reviewHours: number | null };
  computedBy: 'api' | 'browser';
}

/** Policy simulator: POST /v1/policies/simulate, computed in the browser if the API is unreachable. */
export function useSimulation(model: ModelKey, fpr: 0.01 | 0.05, prevalence: number, volume: number) {
  return useQuery<SimulationView>({
    queryKey: ['simulate', model, fpr, prevalence, volume],
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const local = (): SimulationView => {
        const tpr = fpr === 0.01 ? paperA.models[model].fpr_1 : paperA.models[model].fpr_5;
        const r = baseRate(tpr, fpr, prevalence);
        const scale = volume / 10_000;
        return {
          precision: r.precision,
          tpr,
          fpr,
          per10k: { flags: r.flagsPer10k, caught: r.caughtPer10k, falseAlarms: r.flagsPer10k - r.caughtPer10k, missed: r.missedPer10k },
          daily: {
            flags: r.flagsPer10k * scale,
            caught: r.caughtPer10k * scale,
            falseAlarms: (r.flagsPer10k - r.caughtPer10k) * scale,
            missed: r.missedPer10k * scale,
            reviewHours: null,
          },
          computedBy: 'browser',
        };
      };
      if (forceDemo()) return local();
      try {
        const s = await api.simulate({ variant: VARIANT[model], fpr, prevalence, volume_per_day: volume });
        return {
          precision: s.ppv,
          tpr: s.tpr,
          fpr: s.fpr,
          per10k: { flags: s.per_10k.flags, caught: s.per_10k.true_positives, falseAlarms: s.per_10k.false_positives, missed: s.per_10k.missed_fakes },
          daily: {
            flags: s.daily_projection.flags_count,
            caught: s.daily_projection.tp_count,
            falseAlarms: s.daily_projection.fp_count,
            missed: s.daily_projection.missed_count,
            reviewHours: s.daily_projection.review_hours,
          },
          computedBy: 'api',
        };
      } catch (err) {
        if (isUnavailable(err)) return local();
        throw err;
      }
    },
  });
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.status ? `${err.message} (${err.code})` : err.message;
  if (err instanceof Error) return err.message;
  return 'Something went wrong.';
}
