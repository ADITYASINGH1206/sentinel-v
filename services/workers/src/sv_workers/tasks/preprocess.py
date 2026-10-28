import asyncio
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List
import numpy as np
from sqlalchemy import select

from sv_api.database import async_session_maker
from sv_api.models import AnalysisModel, Media
from sv_api.sse import publish_progress
from sv_core.settings import settings
from sv_engine.adapters.base import ClipBatch
from sv_engine.preprocess import MockFaceDetector, preprocess_video
from sv_engine.preprocess.clips import ProcessedTrackClips
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async


def save_tracks_npz(tracks: List[ProcessedTrackClips], npz_path: str) -> None:
    """Serialize processed tracks into NPZ archive for worker handoff."""
    data = {"num_tracks": len(tracks)}
    for i, t in enumerate(tracks):
        data[f"track_{i}_frames_u8"] = t.batch.frames_u8
        data[f"track_{i}_landmarks106"] = (
            t.batch.landmarks106 if t.batch.landmarks106 is not None else np.empty((0,), dtype=np.float32)
        )
        data[f"track_{i}_conf"] = t.batch.conf
        data[f"track_{i}_frame_numbers"] = t.frame_numbers
        data[f"track_{i}_M"] = t.M
        data[f"track_{i}_M_224"] = t.M_224
        data[f"track_{i}_median_iod"] = np.array(t.median_iod, dtype=np.float32)
        data[f"track_{i}_starts"] = np.array(t.chosen_starts, dtype=np.int32)
    np.savez_compressed(npz_path, **data)


async def _async_preprocess(analysis_id: str, media_path: str) -> Dict[str, Any]:
    """Execute preprocessing: decode, detect, track, align, and form clips."""
    detector = MockFaceDetector() if settings.ENGINE_MODE == "mock" else None
    
    # Run CPU/GPU preprocessing pipeline
    prep_res = preprocess_video(
        video_path=media_path,
        detector=detector,
        max_tracks=4,
        K=8,
        T=8
    )

    async with async_session_maker() as session:
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        res = await session.execute(stmt)
        analysis = res.scalars().first()
        if not analysis:
            return {"error": "Analysis not found"}

        # Update metadata on Media record
        if analysis.media_id:
            media_stmt = select(Media).where(Media.id == analysis.media_id)
            media_res = await session.execute(media_stmt)
            media_record = media_res.scalars().first()
            if media_record:
                media_record.duration_s = prep_res.metadata.duration_s
                media_record.width = prep_res.metadata.width
                media_record.height = prep_res.metadata.height
                media_record.fps = prep_res.metadata.fps
                media_record.codec = prep_res.metadata.codec
                await session.flush()

        if prep_res.inconclusive_reason is not None:
            # Short-circuit to finalize with inconclusive outcome
            analysis.decision = "inconclusive"
            analysis.inconclusive_reason = prep_res.inconclusive_reason.value
            await session.commit()
            
            await publish_progress(
                analysis_id,
                "preprocess",
                60,
                f"Inconclusive criteria met: {prep_res.inconclusive_reason.value}"
            )
            from sv_workers.tasks.finalize import run_finalize
            if celery_app.conf.task_always_eager:
                return run_finalize.delay(analysis_id, inconclusive=True)
            try:
                return run_finalize.delay(analysis_id, inconclusive=True)
            except Exception:
                return run_finalize(analysis_id, inconclusive=True)

        await session.commit()
        await publish_progress(
            analysis_id,
            "preprocess",
            50,
            f"Preprocessed {len(prep_res.tracks)} face tracks (K=8, T=8 clips)"
        )

    # Save NPZ archive for GPU worker
    npz_dir = Path(tempfile.gettempdir()) / "sentinel_v_preprocessed"
    npz_dir.mkdir(parents=True, exist_ok=True)
    npz_path = str(npz_dir / f"{analysis_id}.npz")
    save_tracks_npz(prep_res.tracks, npz_path)

    # Proceed to GPU inference cascade
    from sv_workers.tasks.gpu import run_gpu
    if celery_app.conf.task_always_eager:
        return run_gpu.delay(analysis_id, npz_path)
    try:
        return run_gpu.delay(analysis_id, npz_path)
    except Exception:
        return run_gpu(analysis_id, npz_path)


@celery_app.task(name="sv_workers.tasks.preprocess.run_preprocess")
def run_preprocess(analysis_id: str, media_path: str):
    """Task: Decode, detect and track faces, select <=4 tracks, align & center crop."""
    return run_async(_async_preprocess(analysis_id, media_path))
