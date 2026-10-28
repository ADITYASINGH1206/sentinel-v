import uuid

from fastapi import APIRouter, Header
from pydantic import BaseModel

router = APIRouter()


class CompatVideoRequest(BaseModel):
    post_id: str
    video_url: str


class CompatVideoResponse(BaseModel):
    status: str
    labels: list[str]
    deepfake_confidence: float
    deepfake_model_version: str
    disclosed_ai_content: bool
    review_required: bool
    analysis_id: str
    receipt_id: str
    report_url: str


@router.post("/moderate/video", response_model=CompatVideoResponse)
async def moderate_video_compat(
    req: CompatVideoRequest,
    x_internal_key: str | None = Header(None),
):
    analysis_id = f"an_{uuid.uuid4().hex[:16]}"
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"

    # Mock response format conforming strictly to SPEC §11.1
    return CompatVideoResponse(
        status="review",
        labels=["face_manipulation_suspected"],
        deepfake_confidence=0.62,
        deepfake_model_version="smsdt-st-b@mock",
        disclosed_ai_content=False,
        review_required=True,
        analysis_id=analysis_id,
        receipt_id=receipt_id,
        report_url=f"http://localhost:5173/cases/{analysis_id}",
    )
