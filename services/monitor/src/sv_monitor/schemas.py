from typing import Any, Literal

from pydantic import BaseModel, Field


class PSIBinResult(BaseModel):
    bin_index: int
    lower_bound: float
    upper_bound: float
    expected_pct: float
    actual_pct: float
    psi_contribution: float


class PSIReport(BaseModel):
    feature_name: str
    psi: float
    status: Literal["ok", "watch", "alert"]
    num_bins: int
    n_expected: int
    n_actual: int
    bins: list[PSIBinResult] = Field(default_factory=list)


class FeatureDriftSummary(BaseModel):
    timestamp: str
    overall_status: Literal["ok", "watch", "alert"]
    score_drift: PSIReport
    input_drifts: dict[str, PSIReport] = Field(default_factory=dict)


class ReliabilityBinPoint(BaseModel):
    bin_index: int
    bin_lower: float
    bin_upper: float
    bin_center: float
    sample_count: int
    weight_sum: float
    mean_confidence: float
    mean_accuracy: float
    calibration_error: float


class CalibrationReport(BaseModel):
    model_id: str
    n_samples: int
    num_bins: int
    ece: float
    brier_score: float
    log_loss: float
    reliability_curve: list[ReliabilityBinPoint] = Field(default_factory=list)


class RecalibrationProposal(BaseModel):
    proposal_id: str
    model_id: str
    created_at: str
    n_expert_reviews: int
    n_authentic: int
    n_manipulated: int
    current_parameters: tuple[float, float]
    candidate_parameters: tuple[float, float]
    current_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    delta_ece: float
    confusion_matrices: dict[str, Any]
    reliability_comparison: dict[str, Any]
    status: Literal["proposed", "promoted", "rejected"] = "proposed"


class PromotedCalibration(BaseModel):
    calibration_id: str
    proposal_id: str
    model_id: str
    promoted_at: str
    promoted_by: str
    justification: str
    bundle_version: str
    bundle_hash: str
    parameters: tuple[float, float]


class RetentionPurgeReport(BaseModel):
    executed_at: str
    media_older_than_days: int
    evidence_older_than_days: int
    media_records_scanned: int
    media_files_purged: int
    evidence_dirs_purged: int
    receipts_preserved: int
    errors: list[str] = Field(default_factory=list)
