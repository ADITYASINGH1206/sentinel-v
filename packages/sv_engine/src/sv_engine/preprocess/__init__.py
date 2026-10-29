from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sv_core.enums import InconclusiveReason

from sv_engine.preprocess.align import (
    align_and_crop,
    warp_landmarks_224,
)
from sv_engine.preprocess.clips import (
    ProcessedTrackClips,
    build_track_clips,
    contiguous_starts,
    evaluate_inconclusive,
    serialize_track_npz,
)
from sv_engine.preprocess.decode import (
    DecodedFrame,
    DecodeError,
    VideoMetadata,
    decode_video,
)
from sv_engine.preprocess.faces import (
    FaceDetection,
    FaceDetector,
    MockFaceDetector,
)
from sv_engine.preprocess.tracks import (
    SmoothedTrack,
    compute_iou,
    track_faces_multi,
)


@dataclass(frozen=True)
class PreprocessResult:
    tracks: list[ProcessedTrackClips]
    inconclusive_reason: InconclusiveReason | None
    metadata: VideoMetadata
    total_decoded_frames: int
    frames_with_detections: int


def preprocess_video(
    video_path: str,
    detector: Any = None,
    max_tracks: int = 4,
    K: int = 8,
    T: int = 8,
    min_median_iod: float = 24.0,
    min_track_frames: int = 8,
) -> PreprocessResult:
    """Execute end-to-end video preprocessing pipeline.

    1. Validate and sanitize video_path against traversal and non-existent targets.
    2. Decode video frames with PyAV (respecting rotation & sampling windows).
    3. Detect faces with SCRFD or Mock detector.
    4. Greedily track faces with IoU and smooth landmarks with Savitzky-Golay.
    5. Form K clips of T contiguous frames, align & crop to 224x224.
    6. Evaluate inconclusive status if no viable tracks found.
    """
    path = Path(video_path)
    if ".." in path.parts:
        raise ValueError(f"Path traversal detected in video_path: {video_path}")
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Video file not found or invalid: {video_path}")

    metadata, decoded_frames = decode_video(str(resolved))
    if detector is None:
        detector = FaceDetector()

    frame_detections = []
    frames_with_faces = 0
    all_iods = []

    for frame in decoded_frames:
        dets = detector.detect(frame.bgr)
        if dets:
            frames_with_faces += 1
            for d in dets:
                iod = float(np.linalg.norm(d.kps5[0] - d.kps5[1]))
                all_iods.append(iod)
        frame_detections.append((frame.frame_idx, frame.bgr, dets))

    smoothed_tracks = track_faces_multi(
        frame_detections=frame_detections,
        max_tracks=max_tracks,
        min_track_frames=min_track_frames,
        min_median_iod=min_median_iod,
    )

    processed_tracks = []
    for trk in smoothed_tracks:
        clips = build_track_clips(trk, K=K, T=T)
        if clips is not None:
            processed_tracks.append(clips)

    inconclusive_reason = evaluate_inconclusive(
        total_decoded_frames=len(decoded_frames),
        frames_with_detections=frames_with_faces,
        tracks=smoothed_tracks,
        all_raw_iods=all_iods,
    )

    # Ensure inconclusive if no viable track clips were produced
    if not processed_tracks and inconclusive_reason is None:
        inconclusive_reason = InconclusiveReason.TOO_FEW_FRAMES

    return PreprocessResult(
        tracks=processed_tracks,
        inconclusive_reason=inconclusive_reason,
        metadata=metadata,
        total_decoded_frames=len(decoded_frames),
        frames_with_detections=frames_with_faces,
    )


__all__ = [
    "DecodedFrame",
    "DecodeError",
    "VideoMetadata",
    "decode_video",
    "FaceDetection",
    "FaceDetector",
    "MockFaceDetector",
    "SmoothedTrack",
    "compute_iou",
    "track_faces_multi",
    "align_and_crop",
    "warp_landmarks_224",
    "ProcessedTrackClips",
    "build_track_clips",
    "contiguous_starts",
    "evaluate_inconclusive",
    "serialize_track_npz",
    "PreprocessResult",
    "preprocess_video",
]
