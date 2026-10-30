import json
import os
import tempfile
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from pydantic import ValidationError
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
    request: Request,
    background_tasks: BackgroundTasks,
    req: AnalysisCreate | None = Body(None),
    file: UploadFile | None = File(None),
    policy_id: str | None = Form(None),
    source_url: str | None = Form(None),
    explain_gradcam: bool = Form(False),
    skip_cache: bool = Form(False),
    external_ref: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Submit a video for calibrated deepfake screening (multipart upload or URL)."""
    # Support both application/json body and multipart/form-data
    if req is None and "application/json" in request.headers.get("content-type", ""):
        try:
            raw_body = await request.body()
            if raw_body:
                req = AnalysisCreate.model_validate_json(raw_body)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors(),
            )
    analysis_id = f"an_{uuid.uuid4().hex[:16]}"
    chosen_policy = policy_id or (req.policy_id if req else None) or "pol_strict_v3"
    target_url = source_url or (req.source_url if req else None)

    # Validate target URL against SSRF violations (SPEC §12)
    if target_url:
        from sv_api.security import SSRFSecurityError, validate_url_ssrf

        try:
            validate_url_ssrf(target_url)
        except SSRFSecurityError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSRF security violation: {err}",
            ) from err

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
    ref_val = external_ref or (req.external_ref if req else None) or ("upload" if file else "api")
    signals_dict = {
        "explain_gradcam": bool(explain_gradcam or (req.explain_gradcam if req else False)),
        "skip_cache": bool(skip_cache or (req.skip_cache if req else False)),
    }
    analysis_model = AnalysisModel(
        id=analysis_id,
        status=AnalysisStatus.QUEUED.value,
        policy_id=chosen_policy,
        policy_version=3,
        model_bundle_id=settings.MODEL_BUNDLE,
        external_ref=ref_val,
        webhook_url=req.webhook_url if req else None,
        signals=json.dumps(signals_dict),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(analysis_model)
    await db.commit()

    # Trigger worker ingest pipeline via FastAPI BackgroundTasks
    from sv_workers.celery_app import celery_app

    if celery_app.conf.task_always_eager:
        from sv_workers.tasks.ingest import _async_ingest
        background_tasks.add_task(_async_ingest, analysis_id, temp_path, target_url)
    else:
        try:
            run_ingest.delay(analysis_id, temp_path, target_url)
        except Exception:
            from sv_workers.tasks.ingest import _async_ingest
            background_tasks.add_task(_async_ingest, analysis_id, temp_path, target_url)

    return {"analysis_id": analysis_id, "status": AnalysisStatus.QUEUED.value}


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
async def list_analyses(
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    policy_id: str | None = None,
    decision: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List screening analyses ordered chronologically with calibrated scores and summary metadata."""
    from sqlalchemy import desc, func

    stmt = (
        select(AnalysisModel)
        .options(selectinload(AnalysisModel.media), selectinload(AnalysisModel.tracks))
        .order_by(desc(AnalysisModel.created_at))
    )

    if status:
        stmt = stmt.where(AnalysisModel.status == status)
    if policy_id:
        stmt = stmt.where(AnalysisModel.policy_id == policy_id)
    if decision:
        stmt = stmt.where(AnalysisModel.decision == decision)

    # Count query
    count_stmt = select(func.count(AnalysisModel.id))
    if status:
        count_stmt = count_stmt.where(AnalysisModel.status == status)
    if policy_id:
        count_stmt = count_stmt.where(AnalysisModel.policy_id == policy_id)
    if decision:
        count_stmt = count_stmt.where(AnalysisModel.decision == decision)

    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    models = res.scalars().all()

    items = []
    for m in models:
        p_bal = None
        if m.scores:
            try:
                scores_data = json.loads(m.scores)
                p_bal = scores_data.get("p_bal")
            except Exception:
                pass

        duration_s = m.media.duration_s if m.media else None
        faces_count = len(m.tracks) if m.tracks else 0
        source_val = m.external_ref if m.external_ref in ("upload", "api", "sentinel") else "upload"

        items.append(
            {
                "id": m.id,
                "status": m.status,
                "decision": m.decision,
                "p_bal": p_bal,
                "created_at": (
                    m.created_at.isoformat() + "Z"
                    if m.created_at
                    else datetime.now(UTC).isoformat()
                ),
                "duration_s": duration_s,
                "faces": faces_count,
                "source": source_val,
                "review_status": m.review_status,
                "policy_id": m.policy_id,
                "policy": {"id": m.policy_id, "version": m.policy_version},
            }
        )

    return {"items": items, "total": total_count}


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

        box_data = None
        if getattr(trk, "box", None):
            try:
                box_data = json.loads(trk.box)
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
                box=box_data,
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
        video_url=f"/v1/analyses/{model.id}/video",
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


@router.get("/{analysis_id}/video")
async def get_analysis_video(analysis_id: str):
    """Stream or serve uploaded/processed video for browser playback in Reviewer Console."""
    temp_dir = tempfile.gettempdir()
    web_path = os.path.join(temp_dir, f"{analysis_id}_web.mp4")
    if os.path.isfile(web_path):
        return FileResponse(web_path, media_type="video/mp4")

    media_path = os.path.join(temp_dir, f"{analysis_id}.mp4")
    if os.path.isfile(media_path):
        from sv_engine.preprocess.decode import transcode_to_h264_web
        playable_path = transcode_to_h264_web(media_path, web_path)
        return FileResponse(playable_path, media_type="video/mp4")

    raise HTTPException(status_code=404, detail="Video file not found")


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


@router.get("/{analysis_id}/evidence/overlay.mp4")
async def get_analysis_evidence_overlay(analysis_id: str):
    """Stream rendered patch-evidence overlay MP4 with burnt-in scores and disclaimers."""
    overlay_path = os.path.join(
        tempfile.gettempdir(), "sv_evidence", analysis_id, "track_0", "overlay_track_0.mp4"
    )
    if os.path.isfile(overlay_path):
        return FileResponse(overlay_path, media_type="video/mp4")
    # Fallback to source video if overlay was not generated
    media_path = os.path.join(tempfile.gettempdir(), f"{analysis_id}.mp4")
    if os.path.isfile(media_path):
        return FileResponse(media_path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Evidence overlay video not found")


@router.get("/{analysis_id}/evidence/manifest.json")
async def get_analysis_evidence_manifest(analysis_id: str):
    """Retrieve cryptographic manifest of patch evidence artifacts."""
    manifest_path = os.path.join(
        tempfile.gettempdir(), "sv_evidence", analysis_id, "track_0", "evidence_manifest.json"
    )
    if os.path.isfile(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    return {"analysis_id": analysis_id, "track_idx": 0, "manifest": {}, "evidence_root": "0" * 64}


@router.get("/{analysis_id}/evidence/frames/{frame_name}")
async def get_analysis_evidence_frame(analysis_id: str, frame_name: str):
    """Serve individual WebP patch-evidence frame image."""
    frame_path = os.path.join(
        tempfile.gettempdir(), "sv_evidence", analysis_id, "track_0", "frames", frame_name
    )
    if os.path.isfile(frame_path):
        return FileResponse(frame_path, media_type="image/webp")
    raise HTTPException(status_code=404, detail="Evidence frame not found")


@router.get("/{analysis_id}/report.pdf")
async def get_analysis_report_pdf(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and download compliant PDF case audit report (SPEC §14, §16)."""
    from sv_api.reports import generate_case_report_pdf

    stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    model = res.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Analysis not found")

    pdf_bytes = generate_case_report_pdf(model)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{analysis_id}.pdf"},
    )


@router.get("/{analysis_id}/report.html", response_class=HTMLResponse)
async def get_analysis_report_html(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Generate accessible HTML case audit report for review console."""
    from sv_api.reports import generate_case_report_html

    stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
    res = await db.execute(stmt)
    model = res.scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return HTMLResponse(content=generate_case_report_html(model))
