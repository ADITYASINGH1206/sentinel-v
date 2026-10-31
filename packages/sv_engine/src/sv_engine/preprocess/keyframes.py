import logging
import os
from typing import Any

import av
import cv2
import numpy as np

from sv_engine.preprocess.decode import apply_rotation, get_stream_rotation

logger = logging.getLogger(__name__)


def extract_video_keyframes(
    media_path: str,
    max_keyframes: int = 8,
    interval_s: float = 1.0,
) -> list[dict[str, Any]]:
    """Sample full-frame keyframes across video timeline for full-frame AI image detection.

    Args:
        media_path: Path to local video or image file.
        max_keyframes: Maximum number of keyframes to sample (default 8).
        interval_s: Target interval between sampled keyframes in seconds (default 1.0s).

    Returns:
        List of dicts:
        [
            {
                "timestamp_s": float,
                "frame_idx": int,
                "rgb": np.ndarray (H, W, 3) uint8,
            }, ...
        ]
    """
    if not os.path.isfile(media_path):
        return []

    # Check if media is a static image
    ext = os.path.splitext(media_path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        img_bgr = cv2.imread(media_path)
        if img_bgr is not None:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            return [{"timestamp_s": 0.0, "frame_idx": 0, "rgb": img_rgb}]

    keyframes = []
    try:
        container = av.open(media_path)
        video_streams = [s for s in container.streams if s.type == "video"]
        if not video_streams:
            container.close()
            return []

        stream = video_streams[0]
        stream.thread_type = "AUTO"
        rotation = get_stream_rotation(stream)

        fps = float(stream.average_rate) if stream.average_rate else 30.0
        time_base = float(stream.time_base) if stream.time_base else 1.0 / fps

        # We step through frames and capture the closest frame to 0.0s, 1.0s, 2.0s, ...
        next_target_time = 0.0
        frame_idx = 0

        for frame in container.decode(stream):
            if frame.pts is not None:
                current_time = float(frame.pts) * time_base
            else:
                current_time = frame_idx / fps

            if current_time >= next_target_time or frame_idx == 0:
                frame_rgb = frame.to_rgb().to_ndarray()
                if rotation != 0:
                    # apply_rotation works on BGR/RGB matrices identically
                    frame_rgb = apply_rotation(frame_rgb, rotation)

                keyframes.append(
                    {
                        "timestamp_s": round(current_time, 2),
                        "frame_idx": frame_idx,
                        "rgb": frame_rgb,
                    }
                )
                next_target_time += interval_s

                if len(keyframes) >= max_keyframes:
                    break

            frame_idx += 1

        container.close()
    except Exception as exc:
        logger.warning("Error extracting keyframes from %s: %s", media_path, exc)

    return keyframes

