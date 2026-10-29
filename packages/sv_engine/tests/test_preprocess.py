import io
import os
import tempfile
import cv2
import numpy as np
import pytest

from sv_core.enums import InconclusiveReason
from sv_engine.preprocess import (
    MockFaceDetector,
    align_and_crop,
    build_track_clips,
    compute_iou,
    contiguous_starts,
    decode_video,
    evaluate_inconclusive,
    preprocess_video,
    serialize_track_npz,
    track_faces_multi,
    warp_landmarks_224,
)
from sv_engine.preprocess.faces import FaceDetection


@pytest.fixture
def synthetic_video_path():
    """Create a temporary MP4 video with 16 frames for testing."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    width, height = 320, 240
    fps = 24.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    # Generate 16 colored frames with a white rectangle simulating a face
    for i in range(16):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Shift face slightly across frames
        x1, y1 = 100 + (i % 4), 60 + (i % 2)
        cv2.rectangle(frame, (x1, y1), (x1 + 60, y1 + 80), (255, 255, 255), -1)
        writer.write(frame)

    writer.release()
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_decode_video(synthetic_video_path):
    metadata, frames = decode_video(synthetic_video_path)
    assert len(frames) == 16
    assert metadata.width == 320
    assert metadata.height == 240
    assert frames[0].bgr.shape == (240, 320, 3)
    assert frames[0].frame_idx == 0


def test_compute_iou():
    box1 = np.array([10, 10, 50, 50], dtype=np.float32)
    box2 = np.array([10, 10, 50, 50], dtype=np.float32)
    box3 = np.array([100, 100, 150, 150], dtype=np.float32)

    assert compute_iou(box1, box2) == pytest.approx(1.0)
    assert compute_iou(box1, box3) == pytest.approx(0.0)


def test_align_and_crop():
    frame = np.ones((240, 320, 3), dtype=np.uint8) * 128
    kps5 = np.array([
        [140.0, 100.0],
        [180.0, 100.0],
        [160.0, 120.0],
        [145.0, 140.0],
        [175.0, 140.0]
    ], dtype=np.float32)

    crop_224, M, M_224 = align_and_crop(frame, kps5, out_store=256, crop_size=224)
    assert crop_224 is not None
    assert crop_224.shape == (224, 224, 3)
    assert M.shape == (2, 3)
    assert M_224.shape == (2, 3)
    # Verify M_224 translates by -16 relative to 256-space matrix M
    assert np.allclose(M_224[:, 2], M[:, 2] - 16.0)

    # Warp landmark
    lmk = np.array([[160.0, 120.0]], dtype=np.float32)
    warped = warp_landmarks_224(lmk, M_224)
    assert warped.shape == (1, 2)
    # Warped nose should be near center of 224 crop
    assert 50.0 < warped[0, 0] < 174.0
    assert 50.0 < warped[0, 1] < 174.0


def test_contiguous_starts():
    fidx = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.int32)
    starts = contiguous_starts(fidx, T=8, stride=1)
    assert starts == [0, 1, 2, 3]

    broken_fidx = np.array([0, 1, 2, 5, 6, 7, 8, 9, 10], dtype=np.int32)
    starts = contiguous_starts(broken_fidx, T=8, stride=1)
    # Contiguous run of length 8 only possible after frame 5: index 3 to 8
    assert len(starts) == 0  # Only 7 frames in second run (5 to 10 is 6 frames)


def test_track_faces_multi():
    detector = MockFaceDetector(face_present=True, ioc_dist=35.0)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    
    frame_detections = []
    for i in range(12):
        dets = detector.detect(frame)
        frame_detections.append((i, frame, dets))

    tracks = track_faces_multi(frame_detections, min_track_frames=8, min_median_iod=24.0)
    assert len(tracks) == 1
    track = tracks[0]
    assert len(track.frame_indices) == 12
    assert track.median_iod == pytest.approx(35.0, abs=1.0)
    assert track.smoothed_lmk106.shape == (12, 106, 2)
    assert track.smoothed_kps5.shape == (12, 5, 2)


def test_build_track_clips_and_serialize():
    detector = MockFaceDetector(face_present=True, ioc_dist=35.0)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    
    frame_detections = [(i, frame, detector.detect(frame)) for i in range(16)]
    tracks = track_faces_multi(frame_detections)
    assert len(tracks) == 1

    clips = build_track_clips(tracks[0], K=8, T=8)
    assert clips is not None
    assert clips.batch.frames_u8.shape == (8, 8, 224, 224, 3)
    assert clips.batch.landmarks106.shape == (8, 8, 106, 2)
    assert clips.batch.conf.shape == (8, 8)
    assert clips.M_224.shape == (8, 8, 2, 3)

    # Test serialization round-trip
    npz_bytes = serialize_track_npz(clips)
    assert len(npz_bytes) > 0
    loaded = np.load(io.BytesIO(npz_bytes))
    assert "frames_u8" in loaded
    assert loaded["frames_u8"].shape == (8, 8, 224, 224, 3)


def test_inconclusive_evaluations():
    # 1. No face
    reason = evaluate_inconclusive(
        total_decoded_frames=100,
        frames_with_detections=5,  # 5% < 10%
        tracks=[],
        all_raw_iods=[]
    )
    assert reason == InconclusiveReason.NO_FACE

    # 2. Face too small
    reason = evaluate_inconclusive(
        total_decoded_frames=50,
        frames_with_detections=40,
        tracks=[],
        all_raw_iods=[15.0, 16.0, 18.0]  # < 24 px
    )
    assert reason == InconclusiveReason.FACE_TOO_SMALL

    # 3. Too few frames
    reason = evaluate_inconclusive(
        total_decoded_frames=50,
        frames_with_detections=40,
        tracks=[],
        all_raw_iods=[35.0, 40.0]  # Good IOD but track dropped for length < 8
    )
    assert reason == InconclusiveReason.TOO_FEW_FRAMES


def test_full_preprocessing_pipeline(synthetic_video_path):
    detector = MockFaceDetector(face_present=True, ioc_dist=35.0)
    result = preprocess_video(
        video_path=synthetic_video_path,
        detector=detector,
        max_tracks=4,
        K=8,
        T=8
    )

    assert result.inconclusive_reason is None
    assert len(result.tracks) == 1
    track_clip = result.tracks[0]
    assert track_clip.batch.frames_u8.shape == (8, 8, 224, 224, 3)
    assert result.metadata.total_frames == 16
    assert result.total_decoded_frames == 16



def test_corrupt_and_empty_video():
    from sv_engine.preprocess.decode import DecodeError

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"")  # 0 bytes
        empty_path = f.name

    try:
        with pytest.raises(DecodeError):
            decode_video(empty_path)
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"GARBAGE_NON_VIDEO_DATA_1234567890")
        corrupt_path = f.name

    try:
        with pytest.raises(DecodeError):
            decode_video(corrupt_path)
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_sampling_windows_boundaries():
    from sv_engine.preprocess.decode import compute_sampling_windows

    # <= 30s: returns None (decode all frames)
    assert compute_sampling_windows(duration_s=10.0, fps=30.0) is None
    assert compute_sampling_windows(duration_s=30.0, fps=30.0) is None

    # Slightly longer than 30s (e.g. 35s):
    windows_35 = compute_sampling_windows(duration_s=35.0, fps=30.0, segment_len=32)
    assert windows_35 is not None
    assert len(windows_35) >= 2
    assert windows_35[0] == (0, 240)  # 8s * 30fps

    # Long video (120s):
    windows_120 = compute_sampling_windows(duration_s=120.0, fps=30.0, segment_len=32)
    assert windows_120 is not None
    assert len(windows_120) == 5  # 1 initial + 4 spaced windows
    assert windows_120[0] == (0, 240)
    # Windows should be strictly ascending
    for i in range(len(windows_120) - 1):
        assert windows_120[i][1] <= windows_120[i + 1][0]


def test_track_length_boundaries():
    detector = MockFaceDetector(face_present=True, ioc_dist=35.0)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # 7 frames: should be dropped (< 8 frames)
    dets_7 = [(i, frame, detector.detect(frame)) for i in range(7)]
    tracks_7 = track_faces_multi(dets_7, min_track_frames=8)
    assert len(tracks_7) == 0

    # Exactly 8 frames: should be retained
    dets_8 = [(i, frame, detector.detect(frame)) for i in range(8)]
    tracks_8 = track_faces_multi(dets_8, min_track_frames=8)
    assert len(tracks_8) == 1
    assert len(tracks_8[0].frame_indices) == 8


def test_iou_and_iod_boundaries():
    # IoU = 0.30 vs 0.29
    box_base = np.array([0, 0, 100, 100], dtype=np.float32)
    # Shift box horizontally so intersection / union matches
    # Box with x1=53.8, y1=0, x2=153.8, y2=100 has intersection ~46.2*100 = 4620, union ~15380, IoU ~0.30
    box_match = np.array([53.8, 0, 153.8, 100], dtype=np.float32)
    iou = compute_iou(box_base, box_match)
    assert iou == pytest.approx(0.30, abs=0.01)

    # IOD: 23.9 (dropped) vs 24.0 (retained)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    dets_sub24 = [(i, frame, MockFaceDetector(face_present=True, ioc_dist=23.9).detect(frame)) for i in range(10)]
    assert len(track_faces_multi(dets_sub24, min_median_iod=24.0)) == 0

    dets_exact24 = [(i, frame, MockFaceDetector(face_present=True, ioc_dist=24.0).detect(frame)) for i in range(10)]
    assert len(track_faces_multi(dets_exact24, min_median_iod=24.0)) == 1


def test_affine_inversion_numerical_precision():
    frame = np.ones((240, 320, 3), dtype=np.uint8) * 128
    kps5 = np.array([
        [140.0, 100.0],
        [180.0, 100.0],
        [160.0, 120.0],
        [145.0, 140.0],
        [175.0, 140.0]
    ], dtype=np.float32)

    _, _, M_224 = align_and_crop(frame, kps5, out_store=256, crop_size=224)
    assert M_224 is not None

    # Test coordinate back-projection via affine inverse
    # Convert M_224 (2, 3) to homogeneous (3, 3)
    M_homo = np.eye(3, dtype=np.float32)
    M_homo[:2, :] = M_224
    M_inv = np.linalg.inv(M_homo)

    orig_pts = kps5  # (5, 2)
    # Forward project
    ones = np.ones((5, 1), dtype=np.float32)
    pts_homo = np.hstack([orig_pts, ones])  # (5, 3)
    warped_224 = (M_homo @ pts_homo.T).T[:, :2]

    # Invert back
    warped_homo = np.hstack([warped_224, ones])
    recovered_pts = (M_inv @ warped_homo.T).T[:, :2]

    # Difference should be under 0.05 pixels
    max_err = np.max(np.abs(orig_pts - recovered_pts))
    assert max_err < 0.05


def test_rotation_handling():
    from sv_engine.preprocess.decode import apply_rotation

    img = np.zeros((100, 200, 3), dtype=np.uint8)  # H=100, W=200
    img[0:10, 0:10] = 255  # top-left marker

    rot_90 = apply_rotation(img, 90)
    assert rot_90.shape == (200, 100, 3)

    rot_180 = apply_rotation(img, 180)
    assert rot_180.shape == (100, 200, 3)

    rot_270 = apply_rotation(img, 270)
    assert rot_270.shape == (200, 100, 3)

def test_preprocess_video_path_validation():
    # Path traversal attempt should raise ValueError
    with pytest.raises(ValueError, match="Path traversal detected"):
        preprocess_video("../secret/video.mp4")

    with pytest.raises(ValueError, match="Path traversal detected"):
        preprocess_video("storage/../../etc/passwd")

    # Non-existent file should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Video file not found"):
        preprocess_video("non_existent_video_file_99999.mp4")
