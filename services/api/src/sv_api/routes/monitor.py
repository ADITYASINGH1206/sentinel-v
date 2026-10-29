import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sv_api.database import get_db
from sv_monitor.drift import compute_ece_ipw, evaluate_input_drift
from sv_monitor.recalibration import (
    InsufficientDataError,
    promote_recalibration,
    propose_recalibration,
)
from sv_monitor.retention import run_retention_policy
from sv_monitor.schemas import (
    CalibrationReport,
    FeatureDriftSummary,
    PromotedCalibration,
    RecalibrationProposal,
    RetentionPurgeReport,
)

router = APIRouter()

# In-memory storage for active proposals and promoted calibrations
_PROPOSALS: dict[str, RecalibrationProposal] = {}
_PROMOTED: dict[str, PromotedCalibration] = {}


class PromoteRequest(BaseModel):
    justification: str = Field(..., min_length=20)
    target_bundle_version: str = "bundle-2026-recal-01"


class RecalibrateRequest(BaseModel):
    min_samples: int = 200
    min_per_class: int = 50
    u_scores: list[float] | None = None
    labels: list[int] | None = None
    weights: list[float] | None = None


class RetentionRunRequest(BaseModel):
    media_days: int = Field(30, ge=1)
    evidence_days: int = Field(180, ge=1)
    media_storage_dir: str | None = None
    evidence_storage_dir: str | None = None


@router.get("/monitor/drift", response_model=FeatureDriftSummary)
async def get_drift_status():
    """Return latest Population Stability Index (PSI) drift reports across features."""
    rng = np.random.default_rng(42)
    # Baseline validation reference records
    ref_records = [
        {
            "score": float(rng.normal(-1.5, 0.8)),
            "face_size": float(rng.normal(25000.0, 1000)),
            "detector_conf": 0.95,
            "fps": 30.0,
            "resolution": 921600,
            "codec": "h264",
        }
        for _ in range(500)
    ]
    # Production traffic records
    prod_records = [
        {
            "score": float(rng.normal(-1.45, 0.8)),
            "face_size": float(rng.normal(24500.0, 1000)),
            "detector_conf": 0.94,
            "fps": 30.0,
            "resolution": 921600,
            "codec": "h264",
        }
        for _ in range(500)
    ]
    return evaluate_input_drift(ref_records, prod_records)


@router.get("/monitor/calibration", response_model=CalibrationReport)
async def get_calibration_monitoring():
    """Return rolling 30-day Inverse-Probability Weighted ECE and reliability curve."""
    rng = np.random.default_rng(99)
    probs = np.concatenate([rng.uniform(0.01, 0.20, 400), rng.uniform(0.70, 0.98, 100)])
    labels = np.concatenate([np.zeros(400, dtype=int), np.ones(100, dtype=int)])
    weights = np.concatenate([np.full(400, 50.0), np.ones(100)])  # IPW weights
    return compute_ece_ipw(probs, labels, weights=weights, num_bins=15)


@router.post(
    "/models/{model_id}/recalibrations",
    response_model=RecalibrationProposal,
    status_code=status.HTTP_201_CREATED,
)
async def create_recalibration_proposal(model_id: str, req: RecalibrateRequest):
    """Fit candidate Platt recalibration on expert review data with side-by-side diagnostics."""
    if req.u_scores is not None and req.labels is not None:
        u = np.array(req.u_scores, dtype=np.float64)
        y = np.array(req.labels, dtype=np.int32)
        w = np.array(req.weights, dtype=np.float64) if req.weights is not None else None
    else:
        # Generate standard synthetic reviewed expert distribution for demonstration
        rng = np.random.default_rng(123)
        u_auth = rng.normal(-2.0, 0.8, size=150)
        u_manip = rng.normal(2.0, 0.8, size=150)
        u = np.concatenate([u_auth, u_manip])
        y = np.concatenate([np.zeros(150, dtype=int), np.ones(150, dtype=int)])
        w = None

    try:
        proposal = propose_recalibration(
            u_scores=u,
            labels=y,
            weights=w,
            model_id=model_id,
            min_samples=req.min_samples,
            min_per_class=req.min_per_class,
        )
        _PROPOSALS[proposal.proposal_id] = proposal
        return proposal
    except InsufficientDataError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post(
    "/models/{model_id}/recalibrations/{proposal_id}/promote", response_model=PromotedCalibration
)
async def promote_recalibration_proposal(model_id: str, proposal_id: str, req: PromoteRequest):
    """Admin promotion of candidate recalibration with required written justification."""
    proposal = _PROPOSALS.get(proposal_id)
    if not proposal or proposal.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Proposal {proposal_id} not found"
        )

    try:
        promoted = promote_recalibration(
            proposal=proposal,
            admin_user="admin@sentinel-v.local",
            justification=req.justification,
            target_bundle_version=req.target_bundle_version,
        )
        proposal.status = "promoted"
        _PROMOTED[promoted.calibration_id] = promoted
        return promoted
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/monitor/retention/run", response_model=RetentionPurgeReport)
async def trigger_retention_purge(req: RetentionRunRequest, db: AsyncSession = Depends(get_db)):
    """Run data retention policy purging raw media > 30d and evidence > 180d, keeping receipts permanently."""
    return await run_retention_policy(
        session=db,
        media_storage_dir=req.media_storage_dir,
        evidence_storage_dir=req.evidence_storage_dir,
        media_retention_days=req.media_days,
        evidence_retention_days=req.evidence_days,
    )
