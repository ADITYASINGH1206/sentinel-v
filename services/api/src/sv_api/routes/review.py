import uuid

from fastapi import APIRouter
from sv_api.routes.receipts import (
    _DEFAULT_KEY_ID,
    _DEFAULT_PRIV_KEY,
    get_receipt,
    register_receipt,
)
from sv_core.schemas import ReviewCreate
from sv_receipts.schema import build_review_receipt

router = APIRouter()


@router.get("/review-queue")
async def get_review_queue():
    return {"items": [], "total": 0}


@router.post("/review-queue/claim-next")
async def claim_next():
    return {"analysis_id": f"an_{uuid.uuid4().hex[:16]}"}


@router.post("/reviews/{analysis_id}")
async def submit_review(analysis_id: str, review: ReviewCreate):
    review_id = f"rv_{uuid.uuid4().hex[:16]}"

    # Retrieve base receipt or generate default
    orig_receipt_id = f"rcpt_{analysis_id.replace('an_', '')}"
    orig_receipt = await get_receipt(orig_receipt_id)

    decision_str = (
        review.decision.value if hasattr(review.decision, "value") else str(review.decision)
    )

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

    return {
        "review_id": review_id,
        "receipt_id": review_receipt["receipt_id"],
        "supersedes": review_receipt["supersedes"],
        "status": "recorded",
        "receipt": review_receipt,
    }
