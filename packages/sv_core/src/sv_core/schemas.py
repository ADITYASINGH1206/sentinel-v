from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sv_core.enums import (
    AnalysisStatus,
    DecisionBand,
    InconclusiveReason,
    ReviewDecision,
    ReviewSource,
)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MediaInfo(BaseModel):
    id: str
    sha256: str
    duration_s: float
    width: int
    height: int
    fps: float
    codec: str
    container: str
    deleted: bool = False
    media_type: str = "video"


class ClipScore(BaseModel):
    k: int
    start_frame: int
    end_frame: int
    start_s: float
    p: float
    patches: list[float] | None = None


class TrackResult(BaseModel):
    track_idx: int
    n_frames: int
    u: float
    p_bal: float
    decisive: bool
    clips: list[ClipScore] = Field(default_factory=list)
    box: dict[str, float] | None = None


class CascadeInfo(BaseModel):
    stage1_model: str
    stage1_p_bal: float
    stage2_model: str | None = None
    exited_early: bool = False


class ScoresSummary(BaseModel):
    u: float
    p_bal: float
    p_prior: float
    prior_prevalence: float
    ppv_estimate: float | None = None


class AnalysisCreate(BaseModel):
    policy_id: str | None = None
    prior_prevalence: float | None = 0.01
    mode: str = "auto"
    explain_gradcam: bool = False
    skip_cache: bool = False
    external_ref: str | None = None
    webhook_url: str | None = None
    source_url: str | None = None


class Analysis(BaseModel):
    id: str
    status: AnalysisStatus
    media: MediaInfo | None = None
    video_url: str | None = None
    media_url: str | None = None
    media_type: str = "video"
    policy: dict[str, Any]
    decision: DecisionBand | None = None
    inconclusive_reason: InconclusiveReason | None = None
    scores: ScoresSummary | None = None
    cascade: CascadeInfo | None = None
    tracks: list[TrackResult] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list)
    models: list[dict[str, str]] = Field(default_factory=list)
    timings_ms: dict[str, int] = Field(default_factory=dict)
    receipt_id: str | None = None
    review_status: str = "not_required"
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    pipeline_version: str = "unknown"
    mock: bool = False


class AnalysisSummary(BaseModel):
    id: str
    status: AnalysisStatus
    decision: DecisionBand | None = None
    p_bal: float | None = None
    created_at: datetime
    duration_s: float | None = None
    faces: int = 0
    source: str = "api"
    review_status: str = "not_required"
    media_type: str = "video"
    policy_id: str = "—"


class ReviewCreate(BaseModel):
    decision: ReviewDecision
    reasons: list[str] = Field(default_factory=list)
    notes: str | None = None
    confidence: int = Field(ge=1, le=5)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    study_id: str | None = None


class Review(BaseModel):
    id: str
    analysis_id: str
    reviewer_id: str | None = None
    source: ReviewSource
    decision: ReviewDecision
    reasons: list[str] = Field(default_factory=list)
    notes: str | None = None
    confidence: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyBand(BaseModel):
    name: str
    max_p_bal: float


class Policy(BaseModel):
    policy_id: str
    version: int
    prior_prevalence: float = 0.01
    stage1_model: str = "smsdt-s-a"
    stage2_model: str = "smsdt-st-b"
    cascade: dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "exit_below_p_bal": 0.12,
            "miss_budget_on_val": 0.01,
        }
    )
    bands: list[PolicyBand] = Field(
        default_factory=lambda: [
            PolicyBand(name="likely_authentic", max_p_bal=0.30),
            PolicyBand(name="needs_review", max_p_bal=0.751),
            PolicyBand(name="likely_manipulated", max_p_bal=1.00),
        ]
    )
    threshold_source: str = "youden_val"
    audit_sample_rate: float = 0.02
    actions: dict[str, str] = Field(
        default_factory=lambda: {
            "likely_manipulated": "hold_and_review",
            "needs_review": "review",
            "likely_authentic": "allow",
        }
    )
