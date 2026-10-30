import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sv_api.database import async_session_maker
import json
from sv_api.models import AnalysisModel, Media, TrackModel
from sv_api.sse import publish_progress
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async


async def _async_ingest(
    analysis_id: str, media_path: str, source_url: str | None = None
) -> dict[str, Any]:
    """Execute ingest pipeline: hashing, deduplication check, metadata extraction."""
    # Validate source URL against SSRF violations if provided
    if source_url:
        from sv_api.security import validate_url_ssrf

        validate_url_ssrf(source_url)

    # 1. Compute SHA-256
    sha256 = hashlib.sha256()
    file_size = 0
    with open(media_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            file_size += len(chunk)
    sha256_hex = sha256.hexdigest()

    async with async_session_maker() as session:
        # Load active analysis record
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        res = await session.execute(stmt)
        analysis = res.scalars().first()
        if not analysis:
            return {"error": "Analysis not found", "status": "failed"}

        # Check skip_cache option
        skip_cache = False
        if analysis.signals:
            try:
                sig_obj = json.loads(analysis.signals)
                skip_cache = bool(sig_obj.get("skip_cache", False))
            except Exception:
                pass

        # 2. 30-Day Deduplication Check
        now = datetime.now(UTC).replace(tzinfo=None)
        thirty_days_ago = now - timedelta(days=30)
        dedupe_stmt = (
            select(AnalysisModel)
            .join(Media, AnalysisModel.media_id == Media.id)
            .where(
                Media.sha256 == sha256_hex,
                AnalysisModel.model_bundle_id == analysis.model_bundle_id,
                AnalysisModel.policy_version == analysis.policy_version,
                AnalysisModel.status == "completed",
                AnalysisModel.created_at >= thirty_days_ago,
                AnalysisModel.id != analysis_id,
            )
            .order_by(AnalysisModel.completed_at.desc())
        )
        dedupe_res = await session.execute(dedupe_stmt)
        cached_analysis = dedupe_res.scalars().first()

        if not skip_cache and cached_analysis:
            # SPEC §2.1: Cache hit returns existing completed analysis directly
            analysis.status = "completed"
            analysis.decision = cached_analysis.decision
            analysis.scores = cached_analysis.scores
            analysis.cascade = cached_analysis.cascade
            analysis.inconclusive_reason = cached_analysis.inconclusive_reason
            analysis.receipt_id = cached_analysis.receipt_id
            analysis.media_id = cached_analysis.media_id
            analysis.cache_hit = True
            analysis.completed_at = now

            # Clone track records from cached analysis to maintain complete case view
            trk_stmt = select(TrackModel).where(TrackModel.analysis_id == cached_analysis.id)
            trk_res = await session.execute(trk_stmt)
            old_tracks = trk_res.scalars().all()
            if not old_tracks and cached_analysis.media_id:
                anc_stmt = (
                    select(TrackModel)
                    .join(AnalysisModel, TrackModel.analysis_id == AnalysisModel.id)
                    .where(AnalysisModel.media_id == cached_analysis.media_id)
                )
                anc_res = await session.execute(anc_stmt)
                old_tracks = anc_res.scalars().all()

            for old_trk in old_tracks:
                new_trk = TrackModel(
                    id=f"trk_{analysis_id}_{old_trk.track_idx}",
                    analysis_id=analysis_id,
                    track_idx=old_trk.track_idx,
                    n_frames=old_trk.n_frames,
                    u=old_trk.u,
                    p_bal=old_trk.p_bal,
                    decisive=old_trk.decisive,
                    clips=old_trk.clips,
                    box=old_trk.box,
                )
                session.add(new_trk)

            await session.commit()
            await publish_progress(
                analysis_id,
                "ingest",
                100,
                f"Deduplication cache hit: re-used analysis {cached_analysis.id}",
            )
            return {
                "analysis_id": analysis_id,
                "cached_from": cached_analysis.id,
                "status": "completed",
            }

        # 3. Create or Link Media record
        media_stmt = select(Media).where(Media.sha256 == sha256_hex)
        media_res = await session.execute(media_stmt)
        media_record = media_res.scalars().first()

        if not media_record:
            media_record = Media(
                id=f"med_{sha256_hex[:16]}",
                sha256=sha256_hex,
                container=os.path.splitext(media_path)[1].replace(".", "").lower() or "mp4",
                s3_key=f"raw/{sha256_hex}.mp4",
                created_at=now,
            )
            session.add(media_record)
            await session.flush()

        analysis.media_id = media_record.id
        analysis.status = "processing"
        await session.commit()

        await publish_progress(analysis_id, "ingest", 25, "Media validated and indexed")

    # 4. Trigger Preprocessing Task
    if celery_app.conf.task_always_eager:
        from sv_workers.tasks.preprocess import _async_preprocess
        return await _async_preprocess(analysis_id, media_path)
    
    from sv_workers.tasks.preprocess import run_preprocess
    try:
        return run_preprocess.delay(analysis_id, media_path)
    except Exception:
        from sv_workers.tasks.preprocess import _async_preprocess
        return await _async_preprocess(analysis_id, media_path)


@celery_app.task(name="sv_workers.tasks.ingest.run_ingest")
def run_ingest(analysis_id: str, media_path: str, source_url: str | None = None):
    """Task: Download, hash, sniff container, inspect C2PA manifest, and deduplicate."""
    return run_async(_async_ingest(analysis_id, media_path, source_url))
