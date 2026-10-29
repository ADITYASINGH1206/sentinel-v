from dataclasses import dataclass

import av
import cv2
import numpy as np
from sv_core.errors import SentinelVError


class DecodeError(SentinelVError):
    """Raised when video container or stream cannot be decoded."""

    def __init__(self, message: str):
        super().__init__(code="DECODE_FAILURE", message=message)


@dataclass(frozen=True)
class DecodedFrame:
    frame_idx: int
    pts_s: float
    bgr: np.ndarray


@dataclass(frozen=True)
class VideoMetadata:
    duration_s: float
    fps: float
    width: int
    height: int
    codec: str
    rotation: int
    total_frames: int


def get_stream_rotation(stream: av.video.VideoStream) -> int:
    """Extract rotation angle in degrees from stream metadata."""
    rotate = stream.metadata.get("rotate")
    if rotate:
        try:
            return int(float(rotate)) % 360
        except ValueError:
            pass

    for side_data in getattr(stream, "side_data", []):
        if getattr(side_data, "type", None) == "DISPLAYMATRIX":
            matrix = getattr(side_data, "matrix", None)
            if matrix is not None:
                # Calculate angle from display matrix
                angle = -int(round(np.arctan2(matrix[1], matrix[0]) * 180 / np.pi))
                return (angle + 360) % 360
    return 0


def apply_rotation(frame_bgr: np.ndarray, rotation: int) -> np.ndarray:
    """Rotate BGR frame by specified degrees (0, 90, 180, 270)."""
    if rotation == 90:
        return cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        return cv2.rotate(frame_bgr, cv2.ROTATE_180)
    elif rotation == 270:
        return cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame_bgr


def compute_sampling_windows(
    duration_s: float, fps: float, segment_len: int = 32
) -> list[tuple[int, int]] | None:
    """Compute frame ranges [start_frame, end_frame) to decode.

    If duration <= 30s:
        Returns None (meaning decode all contiguous frames).
    If duration > 30s:
        Returns first 8 seconds + 4 evenly spaced windows of segment_len frames.
    """
    if duration_s <= 30.0:
        return None

    windows: list[tuple[int, int]] = []
    # 1. First 8 seconds
    first_8s_frames = int(round(8.0 * fps))
    windows.append((0, first_8s_frames))

    # 2. 4 windows evenly spaced across remaining timeline
    total_estimated_frames = int(round(duration_s * fps))
    remaining_start = first_8s_frames
    remaining_span = max(0, total_estimated_frames - remaining_start - segment_len)

    if remaining_span > 0:
        step = max(1, remaining_span // 4)
        for i in range(4):
            w_start = remaining_start + (i * step)
            w_end = min(total_estimated_frames, w_start + segment_len)
            windows.append((w_start, w_end))
    else:
        if total_estimated_frames > remaining_start:
            windows.append(
                (remaining_start, min(total_estimated_frames, remaining_start + segment_len))
            )

    return windows


def decode_video(
    video_path: str, max_frames_short: int = 250, segment_len: int = 32
) -> tuple[VideoMetadata, list[DecodedFrame]]:
    """Decode video with frame accuracy using PyAV, respecting rotation and sampling.

    Args:
        video_path: path to video file
        max_frames_short: maximum frames to decode if video <= 30s
        segment_len: frame count per sampling window if video > 30s

    Returns:
        (VideoMetadata, List[DecodedFrame])
    """
    try:
        container = av.open(video_path)
    except Exception as e:
        raise DecodeError(f"Failed to open video container {video_path}: {e}")

    if not container.streams.video:
        container.close()
        raise DecodeError(f"No video streams found in {video_path}")

    stream = container.streams.video[0]
    stream.thread_type = "AUTO"

    # Metadata extraction
    fps = float(stream.average_rate or stream.guessed_rate or 30.0)
    if fps <= 0:
        fps = 30.0

    duration_s = float(stream.duration * stream.time_base) if stream.duration else 0.0
    if duration_s <= 0 and container.duration:
        duration_s = float(container.duration) / float(av.time_base)

    rotation = get_stream_rotation(stream)
    width = stream.codec_context.width
    height = stream.codec_context.height
    codec = stream.codec_context.name or "unknown"

    if rotation in (90, 270):
        width, height = height, width

    windows = compute_sampling_windows(duration_s, fps, segment_len)
    if windows is not None:
        max_target_frame = max(end for _, end in windows)
    else:
        max_target_frame = int(round(min(30.0, duration_s if duration_s > 0 else 30.0) * fps))
        if max_frames_short is not None:
            max_target_frame = min(max_target_frame, max_frames_short)

    decoded_frames: list[DecodedFrame] = []
    frame_counter = 0

    try:
        for packet in container.demux(stream):
            for frame in packet.decode():
                curr_idx = frame_counter
                frame_counter += 1

                if curr_idx >= max_target_frame:
                    break

                # If sampling windows active, filter frames
                if windows is not None:
                    in_window = any(start <= curr_idx < end for start, end in windows)
                    if not in_window:
                        continue

                pts_s = (
                    float(frame.pts * stream.time_base)
                    if frame.pts is not None
                    else (curr_idx / fps)
                )

                # Convert to BGR uint8
                bgr = frame.to_ndarray(format="bgr24")
                if rotation != 0:
                    bgr = apply_rotation(bgr, rotation)

                decoded_frames.append(DecodedFrame(frame_idx=curr_idx, pts_s=pts_s, bgr=bgr))

            if frame_counter >= max_target_frame:
                break
    except Exception as e:
        container.close()
        raise DecodeError(f"Error during video decoding: {e}")
    finally:
        container.close()

    if not decoded_frames:
        raise DecodeError(f"Zero frames decoded from {video_path}")

    metadata = VideoMetadata(
        duration_s=duration_s if duration_s > 0 else (len(decoded_frames) / fps),
        fps=fps,
        width=width,
        height=height,
        codec=codec,
        rotation=rotation,
        total_frames=frame_counter,
    )

    return metadata, decoded_frames
