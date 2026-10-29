import json
import os
import tempfile
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sv_api.database import get_db
from sv_api.models import AnalysisModel
from sv_api.sse import subscribe_events
from sv_core.enums import AnalysisStatus, DecisionBand
from sv_core.schemas import (
    Analysis,
    AnalysisCreate,
    CascadeInfo,
    ClipScore,
    MediaInfo,
    ScoresSummary,
    TrackResult,
)
from sv_core.settings import settings
from sv_workers.tasks.ingest import run_ingest

router = APIRouter()


@router.post("", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    req: AnalysisCreate | None = None,
    file: UploadFile | None = File(None),
    policy_id: str | None = Form(None),
    source_url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Submit a video for calibrated deepfake screening (multipart upload or URL)."""
    analysis_id = f"an_{uuid.uuid4().hex[:16]}"
    chosen_policy = policy_id or (req.policy_id if req else None) or "pol_strict_v3"
    target_url = source_url or (req.source_url if req else None)

    # Save uploaded file or prepare placeholder
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{analysis_id}.mp4")

    if file:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
    else:
        # Create minimal synthetic placeholder for URL or mock test
        with open(temp_path, "wb") as f:
            f.write(b"SENTINEL_V_MOCK_PAYLOAD_" + analysis_id.encode("utf-8"))

    # Create Analysis record in DB
    analysis_model = AnalysisModel(
        id=analysis_id,
        status=AnalysisStatus.QUEUED.value,
        policy_id=chosen_policy,
        policy_version=3,
        model_bundle_id=settings.MODEL_BUNDLE,
        external_ref=req.external_ref if req else None,
        webhook_url=req.webhook_url if req else None,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(analysis_model)
    await db.commit()

    # Trigger worker ingest pipeline
    from sv_workers.celery_app import celery_app

    if celery_app.conf.task_always_eager:
        run_ingest.delay(analysis_id, temp_path, target_url)
    else:
        try:
            run_ingest.delay(analysis_id, temp_path, target_url)
        except Exception:
            run_ingest(analysis_id, temp_path, target_url)

    return {"analysis_id": analysis_id, "status": AnalysisStatus.QUEUED.value}


@router.get("/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve complete analysis record with calibrated scores, tracks, and receipts."""
    stmt = (
        select(AnalysisModel)
        .options(selectinload(AnalysisModel.media), selectinload(AnalysisModel.tracks))
        .where(AnalysisModel.id == analysis_id)
    )
    result = await db.execute(stmt)
    model = result.scalars().first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis {analysis_id} not found"
        )

    # Map MediaInfo
    media_info = None
    if model.media:
        media_info = MediaInfo(
            id=model.media.id,
            sha256=model.media.sha256,
            duration_s=model.media.duration_s or 0.0,
            width=model.media.width or 0,
            height=model.media.height or 0,
            fps=model.media.fps or 30.0,
            codec=model.media.codec or "unknown",
            container=model.media.container or "mp4",
            deleted=model.media.deleted,
        )

    # Map Tracks
    track_results: list[TrackResult] = []
    for trk in model.tracks or []:
        clips_list = []
        if trk.clips:
            try:
                raw_clips = json.loads(trk.clips)
                clips_list = [ClipScore(**c) for c in raw_clips]
            except Exception:
                pass

        track_results.append(
            TrackResult(
                track_idx=trk.track_idx,
                n_frames=trk.n_frames,
                u=trk.u,
                p_bal=trk.p_bal,
                decisive=trk.decisive,
                clips=clips_list,
            )
        )

    # Parse Scores
    scores_obj = None
    if model.scores:
        try:
            scores_obj = ScoresSummary(**json.loads(model.scores))
        except Exception:
            pass

    # Parse Cascade
    cascade_obj = None
    if model.cascade:
        try:
            cascade_obj = CascadeInfo(**json.loads(model.cascade))
        except Exception:
            pass

    decision_enum = None
    if model.decision:
        try:
            decision_enum = DecisionBand(model.decision)
        except Exception:
            pass

    return Analysis(
        id=model.id,
        status=AnalysisStatus(model.status),
        media=media_info,
        policy={"id": model.policy_id, "version": model.policy_version},
        decision=decision_enum,
        inconclusive_reason=model.inconclusive_reason,
        scores=scores_obj,
        cascade=cascade_obj,
        tracks=track_results,
        receipt_id=model.receipt_id,
        review_status=model.review_status,
        cache_hit=model.cache_hit,
        created_at=model.created_at,
        completed_at=model.completed_at,
        mock=(settings.ENGINE_MODE == "mock"),
    )


@router.get("/{analysis_id}/events")
async def get_analysis_events(analysis_id: str):
    """Stream real-time stage progress events over Server-Sent Events (SSE)."""
    return StreamingResponse(
        subscribe_events(analysis_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{analysis_id}/evidence")
async def get_analysis_evidence(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve presigned evidence artifacts (WebP patch maps, overlay MP4)."""
    stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    model = res.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "analysis_id": analysis_id,
        "manifest_url": f"/v1/analyses/{analysis_id}/evidence/manifest.json",
        "overlay_url": f"/v1/analyses/{analysis_id}/evidence/overlay.mp4",
        "webp_frames_url": f"/v1/analyses/{analysis_id}/evidence/frames/",
    }
