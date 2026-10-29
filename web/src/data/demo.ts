/**
 * DEMO DATA — deterministic, generated in the browser. Nothing here is a real analysis.
 *
 * Scores are internally consistent: p_bal = σ(a·u + b) with the Stage B calibration from
 * content/sourced/st_calibration.json, and p_prior uses the SPEC §6.5 prior correction.
 * Bands use the `strict-low-fpr` preset thresholds mirrored from
 * packages/sv_engine/src/sv_engine/cascade.py (POLICY_PRESETS).
 */
import type { DecisionBand } from '../components/BandChip';
import type { TrackData } from '../components/EvidencePlayer';
import { platt, priorCorrect, sigmoid } from '../utils/calibration';
import type { CaseSummary, CaseView, PolicyPreset } from './types';

/** Mirror of POLICY_PRESETS in sv_engine/cascade.py (used only when the API is unreachable). */
export const DEMO_PRESETS: Record<string, PolicyPreset> = {
  'strict-low-fpr': {
    policy_id: 'strict-low-fpr',
    version: 1,
    name: 'Strict Low False-Positive Rate',
    description: 'Optimized for in-domain deployment at low base-rate (pi=1%) with two-stage cascade.',
    target_prevalence: 0.01,
    stage1_variant: 'smsdt-s-a',
    stage2_variant: 'smsdt-st-b',
    cascade_enabled: true,
    exit_below_p_bal: 0.12,
    thresholds: { tau_authentic: 0.3, tau_manipulated: 0.75 },
    audit_sample_rate: 0.02,
  },
  'transfer-calibrated': {
    policy_id: 'transfer-calibrated',
    version: 1,
    name: 'Transfer Calibrated',
    description: 'Mixed or unknown sources. Uses ST until the Full model (B1) is available.',
    target_prevalence: 0.05,
    stage1_variant: 'smsdt-s-a',
    stage2_variant: 'smsdt-st-b',
    cascade_enabled: true,
    exit_below_p_bal: 0.12,
    thresholds: { tau_authentic: 0.35, tau_manipulated: 0.7 },
    audit_sample_rate: 0.02,
  },
  'evidence-desk': {
    policy_id: 'evidence-desk',
    version: 1,
    name: 'Evidence Desk',
    description: 'Low-volume, high-stakes review; no cascade.',
    target_prevalence: 0.2,
    stage1_variant: 'smsdt-st-b',
    stage2_variant: 'smsdt-st-b',
    cascade_enabled: false,
    exit_below_p_bal: 0,
    thresholds: { tau_authentic: 0.4, tau_manipulated: 0.6 },
    audit_sample_rate: 0.02,
  },
};

const DEMO_POLICY = DEMO_PRESETS['strict-low-fpr'];
export const DEMO_VIDEO_SOURCES = [
  { src: '/demo/demo-subject.webm', type: 'video/webm' },
  { src: '/demo/demo-subject.mp4', type: 'video/mp4' },
];
const DEMO_DURATION = 18;
const DEMO_FPS = 24;
/** Normalized face box of the synthetic subject in demo-subject.mp4. */
export const DEMO_FACE_BOX = { x: 0.355, y: 0.19, w: 0.29, h: 0.62 };

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function bandFor(pBal: number, policy: PolicyPreset = DEMO_POLICY): DecisionBand {
  if (pBal < policy.thresholds.tau_authentic) return 'likely_authentic';
  if (pBal < policy.thresholds.tau_manipulated) return 'needs_review';
  return 'likely_manipulated';
}

/** Target mean logits chosen so the generated set spans every band. */
const U_TARGETS = [-3.2, -2.4, -1.8, -1.1, 0.4, 1.2, 1.66, 2.1, 2.6, 3.4, 4.2];
const SOURCES = ['upload', 'api', 'sentinel'];
const ANCHOR = Date.UTC(2026, 9, 29, 6, 0, 0);

function makeClips(rand: () => number, u: number, nClips: number, peakAt: number, durationS: number) {
  return Array.from({ length: nClips }, (_, k) => {
    const start_s = (durationS / nClips) * k;
    const bump = Math.exp(-((k - peakAt) ** 2) / 2.5) * 1.6;
    const logit = u - 0.6 + bump + (rand() - 0.5) * 0.9;
    const start_frame = Math.round(start_s * DEMO_FPS);
    return { k, start_frame, end_frame: start_frame + 7, start_s: Number(start_s.toFixed(2)), p: Number(sigmoid(logit).toFixed(3)) };
  });
}

function makeCase(index: number): CaseView {
  const rand = mulberry32(1000 + index * 7919);
  const inconclusive = index === 5 || index === 17;
  const failed = index === 11;
  const u = U_TARGETS[index % U_TARGETS.length] + (rand() - 0.5) * 0.4;
  const pBal = platt(u);
  const prior = 0.01;
  const nTracks = index % 6 === 2 ? 2 : 1;
  const tracks: TrackData[] = Array.from({ length: nTracks }, (_, j) => {
    const trackU = j === 0 ? u : u - 1.8 - rand();
    return {
      track_idx: j,
      n_frames: Math.round(DEMO_DURATION * DEMO_FPS * (j === 0 ? 0.95 : 0.55)),
      u: Number(trackU.toFixed(3)),
      p_bal: Number(platt(trackU).toFixed(4)),
      decisive: j === 0,
      clips: makeClips(rand, trackU, 8, 3 + Math.floor(rand() * 3), DEMO_DURATION),
      box: j === 0 ? DEMO_FACE_BOX : { x: 0.06, y: 0.25, w: 0.16, h: 0.34 },
    };
  });
  const id = `an_demo_${(8800 + index).toString()}`;
  const createdAt = new Date(ANCHOR - index * 37 * 60_000).toISOString();
  const band = failed ? null : inconclusive ? 'inconclusive' : bandFor(pBal);
  const exitedEarly = !inconclusive && pBal < DEMO_POLICY.exit_below_p_bal;
  return {
    id,
    status: failed ? 'failed' : 'completed',
    band,
    inconclusiveReason: inconclusive ? (index === 5 ? 'NO_FACE' : 'TOO_FEW_FRAMES') : null,
    u: inconclusive || failed ? null : Number(u.toFixed(3)),
    pBal: inconclusive || failed ? null : Number(pBal.toFixed(4)),
    pPrior: inconclusive || failed ? null : Number(priorCorrect(pBal, prior).toFixed(4)),
    priorPrevalence: prior,
    ppvEstimate: null,
    policyId: DEMO_POLICY.policy_id,
    policyVersion: DEMO_POLICY.version,
    thresholds: { tauAuthentic: DEMO_POLICY.thresholds.tau_authentic, tauManipulated: DEMO_POLICY.thresholds.tau_manipulated },
    cascade: inconclusive || failed ? null : {
      stage1Model: DEMO_POLICY.stage1_variant,
      stage1PBal: Number(platt(u - 0.4).toFixed(4)),
      stage2Model: exitedEarly ? null : DEMO_POLICY.stage2_variant,
      exitedEarly,
    },
    media: {
      sha256: Array.from({ length: 64 }, () => Math.floor(rand() * 16).toString(16)).join(''),
      durationS: DEMO_DURATION,
      width: 640,
      height: 360,
      fps: DEMO_FPS,
      codec: 'h264',
      container: 'mp4',
    },
    videoSources: DEMO_VIDEO_SOURCES,
    tracks: inconclusive || failed ? [] : tracks,
    signals: {
      c2pa: { present: index % 9 === 4, ai_disclosed: false },
      generative_image: { enabled: false },
      metadata: { encoder: 'Lavf60 (synthetic demo)' },
    },
    labels: [],
    models: [{ role: exitedEarly ? 'stage1' : 'stage2', model_id: exitedEarly ? DEMO_POLICY.stage1_variant : DEMO_POLICY.stage2_variant, weights_sha256: 'demo' }],
    timingsMs: {},
    receiptId: failed ? null : `rcpt_demo_${8800 + index}`,
    reviewStatus: band === 'needs_review' || band === 'likely_manipulated' ? (index % 4 === 0 ? 'reviewed' : 'pending_review') : 'not_required',
    cacheHit: index === 8,
    createdAt,
    completedAt: failed ? null : new Date(ANCHOR - index * 37 * 60_000 + 42_000).toISOString(),
    source: SOURCES[index % SOURCES.length],
    mockEngine: true,
    isDemo: true,
  };
}

const DEMO_CASES: CaseView[] = Array.from({ length: 24 }, (_, i) => makeCase(i));

export function demoCase(id: string): CaseView | undefined {
  return DEMO_CASES.find((c) => c.id === id);
}

export function demoCases(): CaseView[] {
  return DEMO_CASES;
}

export function toSummary(c: CaseView): CaseSummary {
  return {
    id: c.id,
    status: c.status,
    band: c.band,
    pBal: c.pBal,
    createdAt: c.createdAt,
    durationS: c.media?.durationS ?? null,
    faces: c.tracks.length,
    source: c.source,
    reviewStatus: c.reviewStatus,
    policyId: c.policyId,
    isDemo: c.isDemo,
  };
}

export function demoReviewQueue(): CaseView[] {
  return DEMO_CASES.filter((c) => c.reviewStatus === 'pending_review');
}
