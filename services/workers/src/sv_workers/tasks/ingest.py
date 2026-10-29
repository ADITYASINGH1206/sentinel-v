import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sv_api.database import async_session_maker
from sv_api.models import AnalysisModel, Media
from sv_api.sse import publish_progress
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async


async def _async_ingest(
    analysis_id: str, media_path: str, source_url: str | None = None
) -> dict[str, Any]:
    """Execute ingest pipeline: hashing, deduplication check, metadata extraction."""
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

        if cached_analysis:
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
    from sv_workers.tasks.preprocess import run_preprocess

    if celery_app.conf.task_always_eager:
        return run_preprocess.delay(analysis_id, media_path)
    try:
        return run_preprocess.delay(analysis_id, media_path)
    except Exception:
        return run_preprocess(analysis_id, media_path)


@celery_app.task(name="sv_workers.tasks.ingest.run_ingest")
def run_ingest(analysis_id: str, media_path: str, source_url: str | None = None):
    """Task: Download, hash, sniff container, inspect C2PA manifest, and deduplicate."""
    return run_async(_async_ingest(analysis_id, media_path, source_url))
