import json
import os
import tempfile
from typing import Any

import numpy as np
from sqlalchemy import delete, select, update
from sv_api.database import async_session_maker
from sv_api.models import AnalysisModel, TrackModel
from sv_api.sse import publish_progress
from sv_core.settings import settings
from sv_engine.adapters.base import ClipBatch
from sv_engine.adapters.mock import MockDetectorAdapter
from sv_engine.evidence import generate_track_evidence
from sv_engine.overlay_render import render_track_artifacts
from sv_engine.preprocess.clips import ProcessedTrackClips
from sv_engine.preprocess.decode import decode_video
from sv_workers.celery_app import celery_app
from sv_workers.tasks.utils import run_async

_MODEL_ADAPTER: Any = None


def get_model_adapter() -> Any:
    """Retrieve model adapter matching current settings (cached singleton for real weights)."""
    global _MODEL_ADAPTER
    if settings.ENGINE_MODE == "real":
        if _MODEL_ADAPTER is None:
            import torch
            from sv_engine.adapters.full_c import FullCAdapter

            bundle_dir = os.path.join("models", settings.MODEL_BUNDLE, "smsdt-full-c")
            if not os.path.exists(bundle_dir):
                bundle_dir = os.path.join("models", settings.MODEL_BUNDLE)

            device = getattr(settings, "DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            adapter = FullCAdapter(model_id="smsdt-full-c", device=device)
            adapter.load(bundle_dir)
            _MODEL_ADAPTER = adapter
        return _MODEL_ADAPTER
    else:
        return MockDetectorAdapter(model_id="mock-st", variant="st")


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
    """Execute model cascade inference on tracks and generate patch evidence."""
    if isinstance(tracks_or_npz, str):
        tracks = load_tracks_npz(tracks_or_npz)
    else:
        tracks = tracks_or_npz

    # Check if deep explain / Grad-CAM was requested
    should_render_evidence = False
    try:
        async with async_session_maker() as session:
            stmt_sig = select(AnalysisModel.signals).where(AnalysisModel.id == analysis_id)
            res_sig = await session.execute(stmt_sig)
            sig_str = res_sig.scalar()
            if sig_str:
                sig_dict = json.loads(sig_str)
                should_render_evidence = bool(sig_dict.get("explain_gradcam", False))
    except Exception:
        pass

    media_path = os.path.join(tempfile.gettempdir(), f"{analysis_id}.mp4")
    source_frames: list[np.ndarray] | None = None
    source_frame_indices: list[int] | None = None
    vid_width = 1280
    vid_height = 720

    if os.path.exists(media_path):
        try:
            import cv2
            cap = cv2.VideoCapture(media_path)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0:
                vid_width, vid_height = w, h
        except Exception:
            pass

    # Only decode all video frames for evidence video rendering if Grad-CAM was requested
    if should_render_evidence and os.path.exists(media_path):
        try:
            v_meta, decoded = decode_video(media_path)
            source_frames = [df.bgr for df in decoded]
            source_frame_indices = [df.frame_idx for df in decoded]
        except Exception:
            pass

    adapter = get_model_adapter()
    track_records: list[dict[str, Any]] = []

    for idx, trk in enumerate(tracks):
        clip_out = adapter.predict(trk.batch)
        logits = np.asarray(clip_out.logits, dtype=np.float32)
        u_track = float(np.mean(logits))

        # Uncalibrated baseline score
        p_raw = float(1.0 / (1.0 + np.exp(-u_track)))

        # Generate patch evidence maps and artifacts if requested
        ev_root = None
        if should_render_evidence and clip_out.patch_logits is not None:
            try:
                evidence_frames = generate_track_evidence(
                    track_idx=idx,
                    patch_logits_ktp=clip_out.patch_logits,
                    affine_matrices_M=trk.M,
                    frame_numbers=trk.frame_numbers,
                    out_width=vid_width,
                    out_height=vid_height,
                    grid=clip_out.grid,
                )
                evidence_dir = os.path.join(
                    tempfile.gettempdir(), "sv_evidence", analysis_id, f"track_{idx}"
                )
                _, ev_root = render_track_artifacts(
                    track_evidence_frames=evidence_frames,
                    output_dir=evidence_dir,
                    track_idx=idx,
                    source_frames=source_frames,
                    p_score=p_raw,
                    source_frame_indices=source_frame_indices,
                )
            except Exception:
                ev_root = None

        clips_data = []
        for k in range(len(logits)):
            clip_dict = {
                "k": k,
                "start_frame": int(trk.frame_numbers[k, 0]),
                "end_frame": int(trk.frame_numbers[k, -1]),
                "start_s": float(trk.frame_numbers[k, 0] / 30.0),
                "p": float(1.0 / (1.0 + np.exp(-float(logits[k])))),
            }
            if clip_out.patch_logits is not None and clip_out.patch_logits.shape[0] > k:
                patch_mean_k = np.mean(clip_out.patch_logits[k], axis=0)  # shape (256,)
                patch_prob_k = 1.0 / (1.0 + np.exp(-patch_mean_k))
                clip_dict["patches"] = [round(float(p), 4) for p in patch_prob_k]
            clips_data.append(clip_dict)

        # Compute normalized face bounding box {x, y, w, h} from M_224 affine matrix
        track_box = None
        try:
            import cv2
            if trk.M_224 is not None and trk.M_224.size > 0:
                M_first = trk.M_224[0, 0]
                M_inv = cv2.invertAffineTransform(M_first.astype(np.float32))
                crop_pts = np.array([[0, 224, 224, 0], [0, 0, 224, 224], [1, 1, 1, 1]], dtype=np.float32)
                frame_pts = M_inv @ crop_pts
                min_x = float(np.min(frame_pts[0]))
                max_x = float(np.max(frame_pts[0]))
                min_y = float(np.min(frame_pts[1]))
                max_y = float(np.max(frame_pts[1]))
                norm_x = max(0.0, min(1.0, min_x / max(vid_width, 1)))
                norm_y = max(0.0, min(1.0, min_y / max(vid_height, 1)))
                norm_w = max(0.01, min(1.0 - norm_x, (max_x - min_x) / max(vid_width, 1)))
                norm_h = max(0.01, min(1.0 - norm_y, (max_y - min_y) / max(vid_height, 1)))
                track_box = {"x": round(norm_x, 4), "y": round(norm_y, 4), "w": round(norm_w, 4), "h": round(norm_h, 4)}
        except Exception:
            track_box = {"x": 0.35, "y": 0.2, "w": 0.3, "h": 0.5}

        track_records.append(
            {
                "track_idx": idx,
                "n_frames": int(trk.frame_numbers.size),
                "u": u_track,
                "p_bal": p_raw,
                "clips": clips_data,
                "evidence_root": ev_root,
                "box": track_box,
            }
        )

    # Find decisive track: argmax u
    decisive_ev_root = None
    if track_records:
        decisive_idx = int(np.argmax([float(t["u"]) for t in track_records]))
        for i, t in enumerate(track_records):
            t["decisive"] = i == decisive_idx
        decisive_ev_root = track_records[decisive_idx].get("evidence_root")

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
                box=json.dumps(t["box"]) if t.get("box") else None,
            )
            session.add(trk_model)

        # Store decisive evidence_root in analysis.signals if available
        if decisive_ev_root:
            stmt_curr = select(AnalysisModel.signals).where(AnalysisModel.id == analysis_id)
            res_curr = await session.execute(stmt_curr)
            curr_sig_str = res_curr.scalar()
            curr_sig = json.loads(curr_sig_str) if curr_sig_str else {}
            curr_sig["evidence_root"] = decisive_ev_root
            stmt_up = (
                update(AnalysisModel)
                .where(AnalysisModel.id == analysis_id)
                .values(signals=json.dumps(curr_sig))
            )
            await session.execute(stmt_up)

        await session.commit()

        await publish_progress(
            analysis_id, "gpu", 75, f"Evaluated {len(tracks)} face tracks on S-MSDT detector"
        )

    if celery_app.conf.task_always_eager:
        from sv_workers.tasks.finalize import _async_finalize
        return await _async_finalize(analysis_id, inconclusive=False)
    from sv_workers.tasks.finalize import run_finalize
    try:
        return run_finalize.delay(analysis_id, inconclusive=False)
    except Exception:
        from sv_workers.tasks.finalize import _async_finalize
        return await _async_finalize(analysis_id, inconclusive=False)


@celery_app.task(name="sv_workers.tasks.gpu.run_gpu")
def run_gpu(analysis_id: str, tracks_or_npz: str | list[ProcessedTrackClips]):
    """Task: S-MSDT cascade model inference and evidence generation."""
    return run_async(_async_gpu(analysis_id, tracks_or_npz))
