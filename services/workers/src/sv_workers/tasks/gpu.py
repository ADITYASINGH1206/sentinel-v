import json
from typing import Any

import numpy as np
from sqlalchemy import delete
from sv_api.database import async_session_maker
from sv_api.models import TrackModel
from sv_api.sse import publish_progress
from sv_engine.adapters.base import ClipBatch
from sv_engine.adapters.mock import MockDetectorAdapter
from sv_engine.preprocess.clips import ProcessedTrackClips
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async


def load_tracks_npz(npz_path: str) -> list[ProcessedTrackClips]:
    """Deserialize processed tracks from an NPZ archive."""
    data = np.load(npz_path)
    num_tracks = int(data["num_tracks"])
    tracks = []
    for i in range(num_tracks):
        lmk_arr = data[f"track_{i}_landmarks106"]
        landmarks106 = lmk_arr if lmk_arr.size > 0 else None
        batch = ClipBatch(
            frames_u8=data[f"track_{i}_frames_u8"],
            landmarks106=landmarks106,
            conf=data[f"track_{i}_conf"],
        )
        tracks.append(
            ProcessedTrackClips(
                track_id=i,
                batch=batch,
                chosen_starts=list(data[f"track_{i}_starts"]),
                frame_numbers=data[f"track_{i}_frame_numbers"],
                M=data[f"track_{i}_M"],
                M_224=data[f"track_{i}_M_224"],
                median_iod=float(data[f"track_{i}_median_iod"]),
            )
        )
    return tracks


async def _async_gpu(
    analysis_id: str, tracks_or_npz: str | list[ProcessedTrackClips]
) -> dict[str, Any]:
    """Execute model cascade inference on tracks."""
    if isinstance(tracks_or_npz, str):
        tracks = load_tracks_npz(tracks_or_npz)
    else:
        tracks = tracks_or_npz

    # Use deterministic mock adapter or real adapter
    adapter = MockDetectorAdapter(model_id="mock-st", variant="st")
    track_records = []

    for idx, trk in enumerate(tracks):
        clip_out = adapter.predict(trk.batch)
        logits = np.asarray(clip_out.logits, dtype=np.float32)
        u_track = float(np.mean(logits))

        # Uncalibrated baseline score
        p_raw = float(1.0 / (1.0 + np.exp(-u_track)))

        clips_data = []
        for k in range(len(logits)):
            clips_data.append(
                {
                    "k": k,
                    "start_frame": int(trk.frame_numbers[k, 0]),
                    "end_frame": int(trk.frame_numbers[k, -1]),
                    "start_s": float(trk.frame_numbers[k, 0] / 30.0),
                    "p": float(1.0 / (1.0 + np.exp(-float(logits[k])))),
                }
            )

        track_records.append(
            {
                "track_idx": idx,
                "n_frames": int(trk.frame_numbers.size),
                "u": u_track,
                "p_bal": p_raw,
                "clips": clips_data,
            }
        )

    # Find decisive track: argmax u
    if track_records:
        decisive_idx = int(np.argmax([t["u"] for t in track_records]))
        for i, t in enumerate(track_records):
            t["decisive"] = i == decisive_idx

    # Persist Track rows to DB (ensuring idempotency on retry)
    async with async_session_maker() as session:
        del_stmt = delete(TrackModel).where(TrackModel.analysis_id == analysis_id)
        await session.execute(del_stmt)

        for t in track_records:
            trk_model = TrackModel(
                id=f"trk_{analysis_id}_{t['track_idx']}",
                analysis_id=analysis_id,
                track_idx=t["track_idx"],
                n_frames=t["n_frames"],
                u=t["u"],
                p_bal=t["p_bal"],
                decisive=t.get("decisive", False),
                clips=json.dumps(t["clips"]),
            )
            session.add(trk_model)
        await session.commit()

        await publish_progress(
            analysis_id, "gpu", 75, f"Evaluated {len(tracks)} face tracks on S-MSDT detector"
        )

    from sv_workers.tasks.finalize import run_finalize

    if celery_app.conf.task_always_eager:
        return run_finalize.delay(analysis_id, inconclusive=False)
    try:
        return run_finalize.delay(analysis_id, inconclusive=False)
    except Exception:
        return run_finalize(analysis_id, inconclusive=False)


@celery_app.task(name="sv_workers.tasks.gpu.run_gpu")
def run_gpu(analysis_id: str, tracks_or_npz: str | list[ProcessedTrackClips]):
    """Task: S-MSDT cascade model inference."""
    return run_async(_async_gpu(analysis_id, tracks_or_npz))
