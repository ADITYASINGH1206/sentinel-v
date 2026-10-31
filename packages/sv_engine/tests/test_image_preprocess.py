import cv2
import numpy as np
import pytest
from sv_core.enums import InconclusiveReason
from sv_engine.preprocess import MockFaceDetector, preprocess_image


def test_preprocess_image_with_face(tmp_path):
    img_path = str(tmp_path / "face.jpg")
    img = np.ones((480, 640, 3), dtype=np.uint8) * 120
    cv2.imwrite(img_path, img)

    detector = MockFaceDetector(face_present=True)
    res = preprocess_image(img_path, detector=detector)

    assert res.inconclusive_reason is None
    assert len(res.tracks) == 1
    assert res.metadata.duration_s == 0.0
    assert res.metadata.width == 640
    assert res.metadata.height == 480
    assert res.metadata.codec == "jpg"
    track = res.tracks[0]
    assert track.batch.frames_u8.shape == (1, 8, 224, 224, 3)
    assert track.batch.landmarks106.shape == (1, 8, 106, 2)


def test_preprocess_image_no_face(tmp_path):
    img_path = str(tmp_path / "noface.png")
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.imwrite(img_path, img)

    detector = MockFaceDetector(face_present=False)
    res = preprocess_image(img_path, detector=detector)

    assert res.inconclusive_reason == InconclusiveReason.NO_FACE
    assert len(res.tracks) == 0
    assert res.metadata.codec == "png"


if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_preprocess_image_with_face(p)
        test_preprocess_image_no_face(p)
    print("ALL IMAGE PREPROCESS TESTS PASSED!")
