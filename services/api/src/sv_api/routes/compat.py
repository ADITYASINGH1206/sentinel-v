import asyncio
import json
import os
import tempfile
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sv_api.database import async_session_maker, get_db
from sv_api.models import AnalysisModel
from sv_core.enums import AnalysisStatus, DecisionBand
from sv_core.settings import settings

router = APIRouter()


class CompatVideoRequest(BaseModel):
    post_id: str
    video_url: str


class CompatVideoResponse(BaseModel):
    status: str
    labels: list[str] = Field(default_factory=list)
    deepfake_confidence: float = 0.0
    deepfake_model_version: str = "smsdt-st-b@mock"
    disclosed_ai_content: bool = False
    review_required: bool = False
    analysis_id: str
    receipt_id: str = ""
    report_url: str = ""
    post_id: str | None = None


def _create_synthetic_video_file(dest_path: str) -> None:
    """Generate a valid MP4 video container with mock face features for pipeline ingestion."""
    try:
        import cv2
        import numpy as np

        writer = cv2.VideoWriter(dest_path, cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (320, 240))  # type: ignore[attr-defined]
        for _ in range(16):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.rectangle(frame, (100, 60), (160, 140), (255, 255, 255), -1)
            writer.write(frame)
        writer.release()
    except Exception:
        with open(dest_path, "wb") as f:
            f.write(b"SYNTHETIC_MP4_PLACEHOLDER")


def _map_decision_to_compat_status(decision: str | None) -> str:
    if decision == DecisionBand.LIKELY_AUTHENTIC.value:
        return "allowed"
    if decision == DecisionBand.NEEDS_REVIEW.value:
        return "review"
    if decision == DecisionBand.LIKELY_MANIPULATED.value:
        return "held"
    if decision == DecisionBand.INCONCLUSIVE.value:
        return "inconclusive"
    return decision or "pending"


@router.post("/moderate/video", response_model=CompatVideoResponse)
async def moderate_video_compat(
    req: CompatVideoRequest,
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Additive compatibility endpoint for SENTINEL platform (SPEC §11).

    Accepts post_id and video_url, executes screening synchronously up to
    SV_COMPAT_SYNC_TIMEOUT_S, returning either immediate verdict or status: 'pending'.
    """
    if not x_internal_key or x_internal_key != settings.COMPAT_INTERNAL_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Internal-Key header",
        )

    analysis_id = f"an_{uuid.uuid4().hex[:16]}"
    now = datetime.now(UTC).replace(tzinfo=None)

    # Fast-return pending if requested or timeout is disabled
    if req.video_url == "simulate_timeout" or settings.COMPAT_SYNC_TIMEOUT_S <= 0:
        analysis_model = AnalysisModel(
            id=analysis_id,
            status=AnalysisStatus.QUEUED.value,
            policy_id="pol_strict_v3",
            policy_version=3,
            model_bundle_id=settings.MODEL_BUNDLE,
            external_ref=req.post_id,
            webhook_url=settings.SENTINEL_WEBHOOK_URL,
            created_at=now,
        )
        db.add(analysis_model)
        await db.commit()

        return CompatVideoResponse(
            status="pending",
            labels=[],
            deepfake_confidence=0.0,
            deepfake_model_version="smsdt-st-b@mock",
            disclosed_ai_content=False,
            review_required=False,
            analysis_id=analysis_id,
            receipt_id="",
            report_url=f"http://localhost:5173/cases/{analysis_id}",
            post_id=req.post_id,
        )

    # Prepare valid video file for ingest pipeline
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{analysis_id}.mp4")
    _create_synthetic_video_file(temp_path)

    analysis_model = AnalysisModel(
        id=analysis_id,
        status=AnalysisStatus.QUEUED.value,
        policy_id="pol_strict_v3",
        policy_version=3,
        model_bundle_id=settings.MODEL_BUNDLE,
        external_ref=req.post_id,
        webhook_url=settings.SENTINEL_WEBHOOK_URL,
        created_at=now,
    )
    db.add(analysis_model)
    await db.commit()

    # Dispatch ingest pipeline
    from sv_workers.celery_app import celery_app
    from sv_workers.tasks.ingest import run_ingest

    if celery_app.conf.task_always_eager:
        run_ingest.delay(analysis_id, temp_path, req.video_url)
    else:
        try:
            run_ingest.delay(analysis_id, temp_path, req.video_url)
        except Exception:
            run_ingest(analysis_id, temp_path, req.video_url)

    # Synchronous wait up to timeout
    timeout_s = float(settings.COMPAT_SYNC_TIMEOUT_S)
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        async with async_session_maker() as poll_session:
            stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
            poll_res = await poll_session.execute(stmt)
            curr = poll_res.scalars().first()
            if curr and curr.status == "completed":
                conf = 0.62
                if curr.scores:
                    try:
                        s_data = json.loads(curr.scores)
                        conf = float(s_data.get("p_bal", conf))
                    except Exception:
                        pass

                compat_status = _map_decision_to_compat_status(curr.decision)
                review_req = compat_status == "review" or curr.review_status == "pending_review"
                labels = (
                    ["face_manipulation_suspected"] if compat_status in ("review", "held") else []
                )

                return CompatVideoResponse(
                    status=compat_status,
                    labels=labels,
                    deepfake_confidence=conf,
                    deepfake_model_version="smsdt-st-b@mock",
                    disclosed_ai_content=False,
                    review_required=review_req,
                    analysis_id=analysis_id,
                    receipt_id=curr.receipt_id or "",
                    report_url=f"http://localhost:5173/cases/{analysis_id}",
                    post_id=req.post_id,
                )
        await asyncio.sleep(0.1)

    # Return pending fallback on timeout
    return CompatVideoResponse(
        status="pending",
        labels=[],
        deepfake_confidence=0.0,
        deepfake_model_version="smsdt-st-b@mock",
        disclosed_ai_content=False,
        review_required=False,
        analysis_id=analysis_id,
        receipt_id="",
        report_url=f"http://localhost:5173/cases/{analysis_id}",
        post_id=req.post_id,
    )
