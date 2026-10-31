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


def preprocess_image(
    image_path: str,
    detector: Any = None,
    K: int = 1,
    T: int = 8,
) -> PreprocessResult:
    """Execute end-to-end static image preprocessing pipeline.

    1. Validate path and load image with OpenCV.
    2. Detect faces with SCRFD or MockFaceDetector.
    3. Align & crop face detections to 224x224 and form T-repetition clip batches.
    4. If no faces detected, flag inconclusive_reason=NO_FACE while enabling full-frame SwinV2 evaluation.
    """
    path = Path(image_path)
    if ".." in path.parts:
        raise ValueError(f"Path traversal detected in image_path: {image_path}")
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Image file not found or invalid: {image_path}")

    import cv2

    img_bgr = cv2.imread(str(resolved))
    if img_bgr is None:
        raise DecodeError(f"Failed to decode image file: {image_path}")

    h, w = img_bgr.shape[:2]
    ext = resolved.suffix.replace(".", "").lower() or "jpg"
    metadata = VideoMetadata(
        duration_s=0.0,
        fps=1.0,
        width=w,
        height=h,
        codec=ext,
        rotation=0,
        total_frames=1,
    )

    if detector is None:
        detector = FaceDetector()

    dets = detector.detect(img_bgr)
    processed_tracks = []
    inconclusive_reason = None

    if not dets:
        inconclusive_reason = InconclusiveReason.NO_FACE
    else:
        dets = sorted(dets, key=lambda d: d.score, reverse=True)
        for track_idx, det in enumerate(dets[:4]):
            iod = float(np.linalg.norm(det.kps5[0] - det.kps5[1]))
            crop_224, M, M_224 = align_and_crop(img_bgr, det.kps5, out_store=256, crop_size=224)
            if crop_224 is None or M is None or M_224 is None:
                continue

            warped_lmk = warp_landmarks_224(det.lmk106, M_224)

            # Replicate the aligned frame T times for S-MSDT spatial batch compatibility
            frames_batch = np.repeat(crop_224[np.newaxis, np.newaxis, ...], T, axis=1)
            lmk_batch = np.repeat(warped_lmk[np.newaxis, np.newaxis, ...], T, axis=1)
            conf_batch = np.full((K, T), det.score, dtype=np.float32)

            from sv_engine.adapters.base import ClipBatch

            clip_batch = ClipBatch(frames_u8=frames_batch, landmarks106=lmk_batch, conf=conf_batch)
            M_batch = np.repeat(M[np.newaxis, np.newaxis, ...], T, axis=1)
            M_224_batch = np.repeat(M_224[np.newaxis, np.newaxis, ...], T, axis=1)
            frame_nums = np.zeros((K, T), dtype=np.int32)

            processed_tracks.append(
                ProcessedTrackClips(
                    track_id=track_idx,
                    batch=clip_batch,
                    chosen_starts=[0],
                    frame_numbers=frame_nums,
                    M=M_batch,
                    M_224=M_224_batch,
                    median_iod=iod,
                )
            )

    return PreprocessResult(
        tracks=processed_tracks,
        inconclusive_reason=inconclusive_reason,
        metadata=metadata,
        total_decoded_frames=1,
        frames_with_detections=1 if dets else 0,
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
    "preprocess_image",
]
