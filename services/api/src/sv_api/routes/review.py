import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sv_api.database import get_db
from sv_api.models import AnalysisModel, ReviewModel
from sv_api.routes.receipts import (
    _DEFAULT_KEY_ID,
    _DEFAULT_PRIV_KEY,
    get_receipt,
    register_receipt,
)
from sv_core.enums import DecisionBand
from sv_core.schemas import ReviewCreate
from sv_receipts.schema import build_review_receipt

router = APIRouter()


@router.get("/review-queue")
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """Retrieve queue of screening cases awaiting human reviewer audit."""
    stmt = (
        select(AnalysisModel)
        .where(
            or_(
                AnalysisModel.review_status == "pending_review",
                AnalysisModel.review_status == "not_required",
                AnalysisModel.decision == DecisionBand.NEEDS_REVIEW.value,
            )
        )
        .where(AnalysisModel.review_status != "reviewed")
        .where(AnalysisModel.status == "completed")
        .order_by(AnalysisModel.created_at.desc())
    )
    res = await db.execute(stmt)
    analyses = res.scalars().all()
    items = [
        {
            "id": a.id,
            "analysis_id": a.id,
            "decision": a.decision,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in analyses
    ]
    return {"items": items, "total": len(items)}


@router.post("/review-queue/claim-next")
async def claim_next(db: AsyncSession = Depends(get_db)):
    """Claim next pending case from the review backlog."""
    stmt = (
        select(AnalysisModel)
        .where(
            or_(
                AnalysisModel.review_status == "pending_review",
                AnalysisModel.review_status == "not_required",
                AnalysisModel.decision == DecisionBand.NEEDS_REVIEW.value,
            )
        )
        .where(AnalysisModel.review_status != "reviewed")
        .where(AnalysisModel.status == "completed")
        .order_by(AnalysisModel.created_at.asc())
    )
    res = await db.execute(stmt)
    analysis = res.scalars().first()
    if analysis:
        return {"analysis_id": analysis.id}
    return {"analysis_id": None}


@router.post("/reviews/{analysis_id}")
async def submit_review(
    analysis_id: str, review: ReviewCreate, db: AsyncSession = Depends(get_db)
):
    """Record human reviewer verdict, emit superseding review receipt, and update DB."""
    stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    analysis = res.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    review_id = f"rv_{uuid.uuid4().hex[:16]}"
    decision_str = (
        review.decision.value if hasattr(review.decision, "value") else str(review.decision)
    )

    # Retrieve base receipt
    orig_receipt_id = analysis.receipt_id or f"rcpt_{analysis_id.replace('an_', '')}"
    orig_receipt = await get_receipt(orig_receipt_id)

    review_receipt = build_review_receipt(
        original_receipt=orig_receipt,
        reviewer_id=getattr(review, "reviewer_id", "usr_reviewer_default"),
        human_decision=decision_str,
        reason_codes=review.reasons,
        notes=review.notes or "",
        key_id=_DEFAULT_KEY_ID,
        private_key=_DEFAULT_PRIV_KEY,
    )
    register_receipt(review_receipt)

    # Persist Review record in database
    rev_model = ReviewModel(
        id=review_id,
        analysis_id=analysis_id,
        reviewer_id=getattr(review, "reviewer_id", "usr_reviewer_default"),
        source="expert",
        decision=decision_str,
        reasons=json.dumps(review.reasons),
        notes=review.notes,
        confidence=review.confidence,
        telemetry=json.dumps(review.telemetry),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(rev_model)

    # Update analysis review_status to reviewed
    analysis.review_status = "reviewed"
    await db.commit()

    return {
        "review_id": review_id,
        "receipt_id": review_receipt["receipt_id"],
        "supersedes": review_receipt["supersedes"],
        "status": "recorded",
        "receipt": review_receipt,
    }
