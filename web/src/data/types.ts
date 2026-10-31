import type { DecisionBand } from '../components/BandChip';
import type { TrackData } from '../components/EvidencePlayer';

/** Reviewer decisions accepted by POST /v1/reviews/{id} (sv_core.enums.ReviewDecision). */
export type ReviewDecision = 'authentic' | 'manipulated' | 'cannot_tell';

export type AnalysisStatus = 'queued' | 'processing' | 'completed' | 'failed';

/** UI view model for one analysis, mapped from the API `Analysis` schema (sv_core.schemas). */
export interface CaseView {
  id: string;
  status: AnalysisStatus;
  band: DecisionBand | null;
  inconclusiveReason: string | null;
  u: number | null;
  pBal: number | null;
  pPrior: number | null;
  priorPrevalence: number;
  ppvEstimate: number | null;
  policyId: string;
  policyVersion: number | null;
  thresholds: { tauAuthentic: number | null; tauManipulated: number | null };
  cascade: { stage1Model: string; stage1PBal: number | null; stage2Model: string | null; exitedEarly: boolean } | null;
  media: {
    sha256: string | null;
    durationS: number;
    width: number;
    height: number;
    fps: number;
    codec: string;
    container: string;
    mediaType?: 'image' | 'video';
  } | null;
  mediaType?: 'image' | 'video';
  isImage?: boolean;
  videoUrl?: string;
  videoSources?: Array<{ src: string; type: string }>;
  tracks: TrackData[];
  signals: Record<string, unknown>;
  labels: string[];
  models: Array<Record<string, string>>;
  timingsMs: Record<string, number>;
  receiptId: string | null;
  reviewStatus: string;
  cacheHit: boolean;
  createdAt: string;
  completedAt: string | null;
  source: string;
  mockEngine: boolean;
  isDemo: boolean;
}

export interface CaseSummary {
  id: string;
  status: AnalysisStatus;
  band: DecisionBand | null;
  pBal: number | null;
  createdAt: string;
  durationS: number | null;
  faces: number;
  source: string;
  reviewStatus: string;
  policyId: string;
  isDemo: boolean;
  mediaType?: 'image' | 'video';
  isImage?: boolean;
}

export interface ReviewPayload {
  decision: ReviewDecision;
  reasons: string[];
  notes: string | null;
  confidence: number;
  telemetry: Record<string, unknown>;
}

export interface PolicyPreset {
  policy_id: string;
  version: number;
  name: string;
  description: string;
  target_prevalence: number;
  stage1_variant: string;
  stage2_variant: string;
  cascade_enabled: boolean;
  exit_below_p_bal: number;
  thresholds: { tau_authentic: number; tau_manipulated: number };
  audit_sample_rate: number;
}
