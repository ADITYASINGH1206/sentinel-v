import io
from dataclasses import dataclass

import numpy as np
from sv_core.enums import InconclusiveReason

from sv_engine.adapters.base import ClipBatch
from sv_engine.preprocess.align import align_and_crop, warp_landmarks_224
from sv_engine.preprocess.tracks import SmoothedTrack


def contiguous_starts(fidx: np.ndarray, T: int = 8, stride: int = 1) -> list[int]:
    """Find start indices where fidx has a contiguous run of T consecutive frame numbers."""
    if len(fidx) < T * stride:
        return []
    span = (T - 1) * stride
    return [s for s in range(len(fidx) - span) if fidx[s + span] - fidx[s] == span]


@dataclass(frozen=True)
class ProcessedTrackClips:
    track_id: int
    batch: ClipBatch  # ClipBatch(frames_u8=(K, T, 224, 224, 3), lmk=(K, T, 106, 2), conf=(K, T))
    chosen_starts: list[int]  # K start indices
    frame_numbers: np.ndarray  # (K, T) original video frame indices
    M: np.ndarray  # (K, T, 2, 3) 256-space affine matrices
    M_224: np.ndarray  # (K, T, 2, 3) 224-space affine matrices
    median_iod: float


def build_track_clips(
    track: SmoothedTrack, K: int = 8, T: int = 8, stride: int = 1, crop_size: int = 224
) -> ProcessedTrackClips | None:
    """Build K clips of T contiguous frames from a smoothed track.

    Args:
        track: SmoothedTrack instance
        K: number of clips to extract (default 8)
        T: number of contiguous frames per clip (default 8)
        stride: frame step (default 1)
        crop_size: model input resolution (default 224)

    Returns:
        ProcessedTrackClips or None if insufficient contiguous frames
    """
    starts = contiguous_starts(track.frame_indices, T=T, stride=stride)
    if not starts:
        # If no strict contiguous starts of length T, allow sliding window over available frames
        if len(track.frame_indices) >= T:
            starts = list(range(len(track.frame_indices) - T + 1))
        else:
            return None

    # Evenly space K clip start points
    step = max(1, len(starts) // K)
    chosen_starts = [starts[min(j * step, len(starts) - 1)] for j in range(K)]

    clips_frames = np.zeros((K, T, crop_size, crop_size, 3), dtype=np.uint8)
    clips_lmk = np.zeros((K, T, 106, 2), dtype=np.float32)
    clips_conf = np.zeros((K, T), dtype=np.float32)
    clips_fidx = np.zeros((K, T), dtype=np.int32)
    clips_M = np.zeros((K, T, 2, 3), dtype=np.float32)
    clips_M_224 = np.zeros((K, T, 2, 3), dtype=np.float32)

    for k_idx, start_pos in enumerate(chosen_starts):
        for t_idx in range(T):
            frame_pos = start_pos + t_idx * stride
            bgr = track.bgr_frames[frame_pos]
            kps5 = track.smoothed_kps5[frame_pos]
            lmk106 = track.smoothed_lmk106[frame_pos]
            score = track.scores[frame_pos]
            fidx = track.frame_indices[frame_pos]

            crop_224, M, M_224 = align_and_crop(bgr, kps5, out_store=256, crop_size=crop_size)
            if crop_224 is None or M is None or M_224 is None:
                # Fallback to zero-filled crop
                crop_224 = np.zeros((crop_size, crop_size, 3), dtype=np.uint8)
                M = np.eye(2, 3, dtype=np.float32)
                M_224 = np.eye(2, 3, dtype=np.float32)

            warped_lmk = warp_landmarks_224(lmk106, M_224)

            clips_frames[k_idx, t_idx] = crop_224
            clips_lmk[k_idx, t_idx] = warped_lmk
            clips_conf[k_idx, t_idx] = score
            clips_fidx[k_idx, t_idx] = fidx
            clips_M[k_idx, t_idx] = M
            clips_M_224[k_idx, t_idx] = M_224

    batch = ClipBatch(frames_u8=clips_frames, landmarks106=clips_lmk, conf=clips_conf)

    return ProcessedTrackClips(
        track_id=track.track_id,
        batch=batch,
        chosen_starts=chosen_starts,
        frame_numbers=clips_fidx,
        M=clips_M,
        M_224=clips_M_224,
        median_iod=track.median_iod,
    )


def serialize_track_npz(processed: ProcessedTrackClips) -> bytes:
    """Serialize processed clips to in-memory compressed .npz bytes."""
    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        frames_u8=processed.batch.frames_u8,
        landmarks106=(
            processed.batch.landmarks106
            if processed.batch.landmarks106 is not None
            else np.empty(0, dtype=np.float32)
        ),
        conf=processed.batch.conf,
        frame_numbers=processed.frame_numbers,
        M=processed.M,
        M_224=processed.M_224,
        track_id=np.array(processed.track_id, dtype=np.int32),
        median_iod=np.array(processed.median_iod, dtype=np.float32),
    )
    return buf.getvalue()


def evaluate_inconclusive(
    total_decoded_frames: int,
    frames_with_detections: int,
    tracks: list[SmoothedTrack],
    all_raw_iods: list[float],
) -> InconclusiveReason | None:
    """Check if video analysis must be declared inconclusive.

    Rules:
    - >= 90% frames without faces -> NO_FACE
    - faces detected but all tracks dropped due to median IOD < 24px -> FACE_TOO_SMALL
    - faces detected with good IOD but fewer than 8 trackable frames -> TOO_FEW_FRAMES
    - no valid tracks produced -> NO_FACE
    """
    if total_decoded_frames == 0:
        return InconclusiveReason.DECODE_FAILURE

    face_ratio = frames_with_detections / total_decoded_frames
    if face_ratio < 0.10:
        return InconclusiveReason.NO_FACE

    if not tracks:
        if all_raw_iods and np.median(all_raw_iods) < 24.0:
            return InconclusiveReason.FACE_TOO_SMALL
        return InconclusiveReason.TOO_FEW_FRAMES

    return None
