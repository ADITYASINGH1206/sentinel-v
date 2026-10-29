from dataclasses import dataclass

import numpy as np
from scipy.signal import savgol_filter

from sv_engine.preprocess.faces import FaceDetection


def compute_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """Compute Intersection-over-Union between two bboxes [x1, y1, x2, y2]."""
    x1 = max(float(box1[0]), float(box2[0]))
    y1 = max(float(box1[1]), float(box2[1]))
    x2 = min(float(box1[2]), float(box2[2]))
    y2 = min(float(box1[3]), float(box2[3]))

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(0.0, float(box1[2]) - float(box1[0])) * max(0.0, float(box1[3]) - float(box1[1]))
    a2 = max(0.0, float(box2[2]) - float(box2[0])) * max(0.0, float(box2[3]) - float(box2[1]))
    union = a1 + a2 - inter
    return inter / union if union > 0.0 else 0.0


@dataclass
class RawTrack:
    track_id: int
    frame_indices: list[int]
    bgr_frames: list[np.ndarray]
    bboxes: list[np.ndarray]
    kps5: list[np.ndarray]
    lmk106: list[np.ndarray]
    scores: list[float]
    last_frame_idx: int


@dataclass(frozen=True)
class SmoothedTrack:
    track_id: int
    frame_indices: np.ndarray  # (N,) int32
    bgr_frames: list[np.ndarray]  # N frames
    bboxes: np.ndarray  # (N, 4) float32
    smoothed_kps5: np.ndarray  # (N, 5, 2) float32
    smoothed_lmk106: np.ndarray  # (N, 106, 2) float32
    scores: np.ndarray  # (N,) float32
    median_iod: float  # median inter-ocular distance in pixels


def track_faces_multi(
    frame_detections: list[tuple[int, np.ndarray, list[FaceDetection]]],
    iou_thresh: float = 0.3,
    max_gap: int = 5,
    max_tracks: int = 4,
    min_track_frames: int = 8,
    min_median_iod: float = 24.0,
) -> list[SmoothedTrack]:
    """Perform greedy multi-face tracking and Savitzky-Golay landmark smoothing.

    Args:
        frame_detections: list of (frame_idx, bgr_frame, list_of_detections)
        iou_thresh: minimum IoU to associate detection with track (default 0.3)
        max_gap: maximum consecutive frames a track can miss before closing (default 5)
        max_tracks: maximum active tracks to retain (default 4)
        min_track_frames: minimum frame length to keep track (default 8)
        min_median_iod: minimum median inter-ocular distance in pixels (default 24.0)

    Returns:
        List[SmoothedTrack] up to max_tracks, ordered by track length descending
    """
    active_tracks: list[RawTrack] = []
    closed_tracks: list[RawTrack] = []
    next_track_id = 0

    for frame_idx, bgr, detections in frame_detections:
        # Close tracks that exceeded max_gap
        still_active = []
        for t in active_tracks:
            if (frame_idx - t.last_frame_idx) > max_gap:
                closed_tracks.append(t)
            else:
                still_active.append(t)
        active_tracks = still_active

        # Greedy bipartite matching based on IoU to last box
        unmatched_detections = list(range(len(detections)))
        matched_track_indices = set()

        if active_tracks and detections:
            # Build IoU matrix: (len(active_tracks), len(detections))
            iou_matrix = np.zeros((len(active_tracks), len(detections)), dtype=np.float32)
            for t_idx, track in enumerate(active_tracks):
                for d_idx, det in enumerate(detections):
                    iou_matrix[t_idx, d_idx] = compute_iou(track.bboxes[-1], det.bbox)

            # Greedily match highest IoU >= iou_thresh
            while True:
                max_val = np.max(iou_matrix) if iou_matrix.size > 0 else 0.0
                if max_val < iou_thresh:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)

                # Assign detection to track
                det = detections[d_idx]
                track = active_tracks[t_idx]
                track.frame_indices.append(frame_idx)
                track.bgr_frames.append(bgr)
                track.bboxes.append(det.bbox)
                track.kps5.append(det.kps5)
                track.lmk106.append(det.lmk106)
                track.scores.append(det.score)
                track.last_frame_idx = frame_idx

                matched_track_indices.add(t_idx)
                if d_idx in unmatched_detections:
                    unmatched_detections.remove(d_idx)

                # Invalidate matched row and column
                iou_matrix[t_idx, :] = -1.0
                iou_matrix[:, d_idx] = -1.0

        # Create new tracks for unmatched detections
        for d_idx in unmatched_detections:
            det = detections[d_idx]
            new_track = RawTrack(
                track_id=next_track_id,
                frame_indices=[frame_idx],
                bgr_frames=[bgr],
                bboxes=[det.bbox],
                kps5=[det.kps5],
                lmk106=[det.lmk106],
                scores=[det.score],
                last_frame_idx=frame_idx,
            )
            next_track_id += 1
            active_tracks.append(new_track)

    all_tracks = closed_tracks + active_tracks

    # Filter and smooth tracks
    smoothed_tracks: list[SmoothedTrack] = []

    for t in all_tracks:
        N = len(t.frame_indices)
        if N < min_track_frames:
            continue

        kps5_arr = np.stack(t.kps5, axis=0)  # (N, 5, 2)
        lmk106_arr = np.stack(t.lmk106, axis=0)  # (N, 106, 2)
        bboxes_arr = np.stack(t.bboxes, axis=0)  # (N, 4)
        scores_arr = np.array(t.scores, dtype=np.float32)

        # Compute inter-ocular distance: Euclidean distance between eyes (kps 0 and 1)
        eye_dists = np.linalg.norm(kps5_arr[:, 0] - kps5_arr[:, 1], axis=-1)
        median_iod = float(np.median(eye_dists))

        if median_iod < min_median_iod:
            continue

        # Savitzky-Golay landmark smoothing (upstream matching constants)
        window = min(7, N)
        if window % 2 == 0:
            window -= 1

        if window >= 3:
            smoothed_kps5 = savgol_filter(
                kps5_arr, window_length=window, polyorder=2, axis=0
            ).astype(np.float32)
            smoothed_lmk106 = savgol_filter(
                lmk106_arr, window_length=window, polyorder=2, axis=0
            ).astype(np.float32)
        else:
            smoothed_kps5 = kps5_arr.astype(np.float32)
            smoothed_lmk106 = lmk106_arr.astype(np.float32)

        smoothed_tracks.append(
            SmoothedTrack(
                track_id=t.track_id,
                frame_indices=np.array(t.frame_indices, dtype=np.int32),
                bgr_frames=t.bgr_frames,
                bboxes=bboxes_arr.astype(np.float32),
                smoothed_kps5=smoothed_kps5,
                smoothed_lmk106=smoothed_lmk106,
                scores=scores_arr,
                median_iod=median_iod,
            )
        )

    # Sort tracks by length descending and take up to max_tracks
    smoothed_tracks.sort(key=lambda trk: len(trk.frame_indices), reverse=True)
    return smoothed_tracks[:max_tracks]
