import uuid
from datetime import datetime

from fastapi import APIRouter
from sv_core.schemas import Analysis, AnalysisCreate, AnalysisStatus, DecisionBand, ScoresSummary
from sv_core.settings import settings

router = APIRouter()


@router.post("", response_model=dict, status_code=202)
async def create_analysis(req: AnalysisCreate):
    analysis_id = f"an_{uuid.uuid4().hex[:16]}"
    return {"analysis_id": analysis_id, "status": AnalysisStatus.QUEUED.value}


@router.get("/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str):
    # Mock analysis response for testing/dev
    return Analysis(
        id=analysis_id,
        status=AnalysisStatus.COMPLETED,
        policy={"id": "pol_strict_v3", "name": "strict-low-fpr", "version": 3},
        decision=DecisionBand.NEEDS_REVIEW,
        scores=ScoresSummary(u=1.66, p_bal=0.62, p_prior=0.016, prior_prevalence=0.01),
        receipt_id=f"rcpt_{uuid.uuid4().hex[:16]}",
        mock=(settings.ENGINE_MODE == "mock"),
        created_at=datetime.utcnow(),
    )
