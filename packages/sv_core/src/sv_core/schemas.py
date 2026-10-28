from datetime import datetime
from typing import Any, Dict, List, Optional
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
    details: Optional[Dict[str, Any]] = None


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


class ClipScore(BaseModel):
    k: int
    start_frame: int
    end_frame: int
    start_s: float
    p: float


class TrackResult(BaseModel):
    track_idx: int
    n_frames: int
    u: float
    p_bal: float
    decisive: bool
    clips: List[ClipScore] = Field(default_factory=list)


class CascadeInfo(BaseModel):
    stage1_model: str
    stage1_p_bal: float
    stage2_model: Optional[str] = None
    exited_early: bool = False


class ScoresSummary(BaseModel):
    u: float
    p_bal: float
    p_prior: float
    prior_prevalence: float
    ppv_estimate: Optional[float] = None


class AnalysisCreate(BaseModel):
    policy_id: Optional[str] = None
    prior_prevalence: Optional[float] = 0.01
    mode: str = "auto"
    explain_gradcam: bool = False
    skip_cache: bool = False
    external_ref: Optional[str] = None
    webhook_url: Optional[str] = None
    source_url: Optional[str] = None


class Analysis(BaseModel):
    id: str
    status: AnalysisStatus
    media: Optional[MediaInfo] = None
    policy: Dict[str, Any]
    decision: Optional[DecisionBand] = None
    inconclusive_reason: Optional[InconclusiveReason] = None
    scores: Optional[ScoresSummary] = None
    cascade: Optional[CascadeInfo] = None
    tracks: List[TrackResult] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    labels: List[str] = Field(default_factory=list)
    models: List[Dict[str, str]] = Field(default_factory=list)
    timings_ms: Dict[str, int] = Field(default_factory=dict)
    receipt_id: Optional[str] = None
    review_status: str = "not_required"
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    pipeline_version: str = "unknown"
    mock: bool = False


class AnalysisSummary(BaseModel):
    id: str
    status: AnalysisStatus
    decision: Optional[DecisionBand] = None
    p_bal: Optional[float] = None
    created_at: datetime
    duration_s: Optional[float] = None
    source: str = "api"


class ReviewCreate(BaseModel):
    decision: ReviewDecision
    reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    confidence: int = Field(ge=1, le=5)
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    study_id: Optional[str] = None


class Review(BaseModel):
    id: str
    analysis_id: str
    reviewer_id: Optional[str] = None
    source: ReviewSource
    decision: ReviewDecision
    reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
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
    cascade: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "exit_below_p_bal": 0.12,
            "miss_budget_on_val": 0.01,
        }
    )
    bands: List[PolicyBand] = Field(
        default_factory=lambda: [
            PolicyBand(name="likely_authentic", max_p_bal=0.30),
            PolicyBand(name="needs_review", max_p_bal=0.751),
            PolicyBand(name="likely_manipulated", max_p_bal=1.00),
        ]
    )
    threshold_source: str = "youden_val"
    audit_sample_rate: float = 0.02
    actions: Dict[str, str] = Field(
        default_factory=lambda: {
            "likely_manipulated": "hold_and_review",
            "needs_review": "review",
            "likely_authentic": "allow",
        }
    )
