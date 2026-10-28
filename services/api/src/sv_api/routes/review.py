import uuid
from typing import List
from fastapi import APIRouter
from sv_core.schemas import Review, ReviewCreate, ReviewDecision, ReviewSource

router = APIRouter()


@router.get("/review-queue")
async def get_review_queue():
    return {
        "items": [],
        "total": 0
    }


@router.post("/review-queue/claim-next")
async def claim_next():
    return {
        "analysis_id": f"an_{uuid.uuid4().hex[:16]}"
    }


@router.post("/reviews/{analysis_id}")
async def submit_review(analysis_id: str, review: ReviewCreate):
    return {
        "review_id": f"rv_{uuid.uuid4().hex[:16]}",
        "receipt_id": f"rcpt_{uuid.uuid4().hex[:16]}",
        "status": "recorded"
    }

