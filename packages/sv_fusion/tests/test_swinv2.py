import numpy as np
import pytest
from sv_fusion.swinv2 import SwinV2Detector


def test_swinv2_mock_mode():
    detector = SwinV2Detector(mode="mock")
    detector.load()
    dummy_frame = np.zeros((256, 256, 3), dtype=np.uint8)

    p = detector.predict_frame(dummy_frame)
    assert 0.0 <= p <= 1.0

    keyframes = [
        {"timestamp_s": 0.0, "frame_idx": 0, "rgb": dummy_frame},
        {"timestamp_s": 1.0, "frame_idx": 30, "rgb": dummy_frame + 10},
    ]
    summary = detector.predict_keyframes(keyframes, threshold=0.65)
    assert summary["enabled"] is True
    assert "max" in summary
    assert "mean" in summary
    assert len(summary["keyframes"]) == 2


def test_swinv2_real_mode_if_available():
    detector = SwinV2Detector(mode="real")
    if not detector.is_available():
        pytest.skip("SwinV2 weights not found locally")

    detector.load()
    dummy_frame = np.zeros((256, 256, 3), dtype=np.uint8)
    p = detector.predict_frame(dummy_frame)
    assert 0.0 <= p <= 1.0
    assert isinstance(p, float)

