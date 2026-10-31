import type { DecisionBand } from '../components/BandChip';
import type { CaseSummary, CaseView, PolicyPreset, ReviewPayload } from './types';

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** True when the failure means "the API is not reachable / does not offer this endpoint". */
export function isUnavailable(err: unknown): boolean {
  if (err instanceof ApiError) {
    return err.status === 0 || err.status === 404 || err.status === 405 || err.status === 502 || err.status === 503 || err.status === 504 || err.code === 'UPSTREAM_UNAVAILABLE';
  }
  return true;
}

const BASE = (import.meta.env?.VITE_API_BASE as string | undefined) ?? '';

async function parseError(res: Response): Promise<ApiError> {
  let code = `HTTP_${res.status}`;
  let message = res.statusText || 'Request failed';
  try {
    const body = await res.json();
    if (body?.error?.code) {
      code = body.error.code;
      message = body.error.message ?? message;
    } else if (typeof body?.detail === 'string') {
      message = body.detail;
    } else if (Array.isArray(body?.detail)) {
      message = body.detail.map((d: { msg?: string; loc?: unknown[] }) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`).join('; ');
      code = 'VALIDATION_ERROR';
    }
  } catch {
    // Non-JSON error bodies come from a proxy (e.g. the dev server) when the API itself is down.
    if (res.status >= 500) return new ApiError(res.status, 'UPSTREAM_UNAVAILABLE', 'The VeriFrame API is not reachable.');
  }
  return new ApiError(res.status, code, message);
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      ...init,
      headers: { Accept: 'application/json', ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    });
  } catch (e) {
    throw new ApiError(0, 'NETWORK_ERROR', 'The VeriFrame API is not reachable.');
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/* --------------------------------------------------------------- mapping */

const BANDS: DecisionBand[] = ['likely_authentic', 'needs_review', 'likely_manipulated', 'inconclusive'];
const asBand = (v: unknown): DecisionBand | null => (BANDS.includes(v as DecisionBand) ? (v as DecisionBand) : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function mapAnalysis(a: any): CaseView {
  const rawContainer = (a.media?.container || '').toLowerCase();
  const rawCodec = (a.media?.codec || '').toLowerCase();
  const isImage = Boolean(
    a.is_image ||
    a.media_type === 'image' ||
    a.media?.media_type === 'image' ||
    ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'].includes(rawContainer) ||
    ['mjpeg', 'jpeg', 'png', 'webp', 'bmp', 'gif'].includes(rawCodec) ||
    (a.media?.duration_s === 0 && !['mp4', 'webm', 'mov', 'mkv', 'avi'].includes(rawContainer))
  );

  const media = a.media
    ? {
        sha256: a.media.sha256 ?? null,
        durationS: isImage ? 0 : (a.media.duration_s ?? 0),
        width: a.media.width ?? 0,
        height: a.media.height ?? 0,
        fps: isImage ? 1 : (a.media.fps ?? 30),
        codec: isImage && rawCodec === 'mjpeg' ? 'jpeg' : (a.media.codec ?? 'unknown'),
        container: isImage && (rawContainer === 'mp4' || !rawContainer) ? 'jpg' : (a.media.container ?? 'unknown'),
        mediaType: isImage ? ('image' as const) : ('video' as const),
      }
    : null;
  const policy = a.policy ?? {};
  return {
    id: a.id,
    status: a.status,
    band: asBand(a.decision),
    inconclusiveReason: a.inconclusive_reason ?? null,
    u: num(a.scores?.u),
    pBal: num(a.scores?.p_bal),
    pPrior: num(a.scores?.p_prior),
    priorPrevalence: num(a.scores?.prior_prevalence) ?? 0.01,
    ppvEstimate: num(a.scores?.ppv_estimate),
    policyId: policy.id ?? policy.policy_id ?? policy.name ?? 'unknown',
    policyVersion: num(policy.version),
    thresholds: {
      tauAuthentic: num(policy.thresholds?.tau_authentic),
      tauManipulated: num(policy.thresholds?.tau_manipulated),
    },
    cascade: a.cascade
      ? {
          stage1Model: a.cascade.stage1_model,
          stage1PBal: num(a.cascade.stage1_p_bal),
          stage2Model: a.cascade.stage2_model ?? null,
          exitedEarly: Boolean(a.cascade.exited_early),
        }
      : null,
    media,
    mediaType: isImage ? 'image' : 'video',
    isImage,
    videoUrl: a.video_url ?? undefined,
    tracks: Array.isArray(a.tracks) ? a.tracks : [],
    signals: a.signals ?? {},
    labels: a.labels ?? [],
    models: a.models ?? [],
    timingsMs: a.timings_ms ?? {},
    receiptId: a.receipt_id ?? null,
    reviewStatus: a.review_status ?? 'not_required',
    cacheHit: Boolean(a.cache_hit),
    createdAt: a.created_at,
    completedAt: a.completed_at ?? null,
    source: a.source ?? 'api',
    mockEngine: Boolean(a.mock),
    isDemo: false,
  };
}

/* ------------------------------------------------------------- endpoints */

export const api = {
  getAnalysis: async (id: string) => mapAnalysis(await request(`/v1/analyses/${encodeURIComponent(id)}`)),

  listAnalyses: async (): Promise<CaseSummary[]> => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const res = await request<{ items: any[] }>(`/v1/analyses?limit=100`);
    return (res.items ?? []).map((a) => {
      const isImg = Boolean(
        a.is_image ||
        a.media_type === 'image' ||
        (a.duration_s === 0 && a.source !== 'api')
      );
      return {
        id: a.id,
        status: a.status,
        band: asBand(a.decision),
        pBal: num(a.p_bal),
        createdAt: a.created_at,
        durationS: isImg ? 0 : num(a.duration_s),
        faces: a.faces ?? 0,
        source: a.source ?? 'api',
        reviewStatus: a.review_status ?? 'not_required',
        policyId: a.policy?.id ?? a.policy_id ?? '—',
        isDemo: false,
        mediaType: isImg ? ('image' as const) : ('video' as const),
        isImage: isImg,
      };
    });
  },

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getReviewQueue: async () => request<{ items: any[]; total: number }>(`/v1/review-queue`),

  submitReview: async (analysisId: string, payload: ReviewPayload) =>
    request<{ review_id: string; receipt_id: string; status: string }>(`/v1/reviews/${encodeURIComponent(analysisId)}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getPresets: async () => request<Record<string, PolicyPreset>>(`/v1/policies/presets`),

  simulate: async (body: { variant: string; fpr: number; prevalence: number; volume_per_day: number }) =>
    request<{
      ppv: number;
      tpr: number;
      fpr: number;
      per_10k: { flags: number; true_positives: number; false_positives: number; missed_fakes: number };
      daily_projection: { volume: number; flags_count: number; tp_count: number; fp_count: number; missed_count: number; review_hours: number };
    }>(`/v1/policies/simulate`, { method: 'POST', body: JSON.stringify(body) }),

  health: async () => request<Record<string, unknown>>(`/readyz`),

  getReceipt: async (id: string) => request<Record<string, unknown>>(`/v1/receipts/${encodeURIComponent(id)}`),
};

/** Upload with real progress events (fetch has no upload progress). */
export function uploadAnalysis(
  form: FormData,
  onProgress: (fraction: number) => void
): { promise: Promise<{ analysis_id: string; status: string }>; abort: () => void } {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<{ analysis_id: string; status: string }>((resolve, reject) => {
    xhr.open('POST', `${BASE}/v1/analyses`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError(xhr.status, 'BAD_RESPONSE', 'Unexpected response from the API.'));
        }
      } else {
        let message = `Upload failed (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          message = body?.error?.message ?? (typeof body?.detail === 'string' ? body.detail : message);
        } catch {
          if (xhr.status >= 500) {
            reject(new ApiError(xhr.status, 'UPSTREAM_UNAVAILABLE', 'The VeriFrame API is not reachable.'));
            return;
          }
        }
        reject(new ApiError(xhr.status, `HTTP_${xhr.status}`, message));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, 'NETWORK_ERROR', 'The VeriFrame API is not reachable.'));
    xhr.onabort = () => reject(new ApiError(0, 'ABORTED', 'Upload cancelled.'));
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}
