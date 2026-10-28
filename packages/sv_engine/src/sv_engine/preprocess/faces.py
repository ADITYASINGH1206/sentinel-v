from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class FaceDetection:
    bbox: np.ndarray        # [x1, y1, x2, y2]
    score: float            # detector confidence in [0, 1]
    kps5: np.ndarray        # (5, 2) keypoints: right_eye, left_eye, nose, mouth_right, mouth_left
    lmk106: np.ndarray      # (106, 2) 2D facial landmarks


class FaceDetector:
    """Wrapper around InsightFace SCRFD (buffalo_l) detector with 106-point landmarks."""

    def __init__(self, ctx_id: int = -1, det_size: Tuple[int, int] = (320, 320)):
        self.ctx_id = ctx_id
        self.det_size = det_size
        self._app = None

    def _init_app(self):
        if self._app is not None:
            return
        
        try:
            import os
            import sys
            import torch
            
            # Ensure CUDA DLLs found on Windows
            if sys.platform == "win32":
                torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
                if os.path.isdir(torch_lib):
                    try:
                        os.add_dll_directory(torch_lib)
                    except Exception:
                        pass

            from insightface.app import FaceAnalysis
            has_cuda = torch.cuda.is_available() and self.ctx_id >= 0
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if has_cuda else ["CPUExecutionProvider"]
            ctx = self.ctx_id if has_cuda else -1

            self._app = FaceAnalysis(
                name="buffalo_l",
                allowed_modules=["detection", "landmark_2d_106"],
                providers=providers
            )
            self._app.prepare(ctx_id=ctx, det_size=self.det_size)
        except Exception as e:
            # Fall back to None; callers or mock detector will handle
            self._app = None

    def detect(self, frame_bgr: np.ndarray) -> List[FaceDetection]:
        self._init_app()
        if self._app is None:
            return []

        faces = self._app.get(frame_bgr)
        detections = []
        for f in faces:
            bbox = np.asarray(f.bbox, dtype=np.float32)
            score = float(f.det_score)
            kps5 = np.asarray(f.kps, dtype=np.float32)
            lmk106 = getattr(f, "landmark_2d_106", None)
            if lmk106 is None:
                # Upcast 5 points to 106 if landmark module absent
                lmk106 = np.zeros((106, 2), dtype=np.float32)
                lmk106[:5] = kps5
            else:
                lmk106 = np.asarray(lmk106, dtype=np.float32)

            detections.append(FaceDetection(
                bbox=bbox,
                score=score,
                kps5=kps5,
                lmk106=lmk106
            ))
        return detections


class MockFaceDetector:
    """Deterministic mock detector for unit testing and CI without ONNX models.
    
    Detects faces by inspecting frame brightness / center, or returns predefined synthetic landmarks.
    """

    def __init__(self, face_present: bool = True, ioc_dist: float = 35.0):
        self.face_present = face_present
        self.ioc_dist = ioc_dist

    def detect(self, frame_bgr: np.ndarray) -> List[FaceDetection]:
        if not self.face_present:
            return []

        H, W = frame_bgr.shape[:2]
        cx, cy = W / 2.0, H / 2.0
        
        # Eyes at cx +/- ioc_dist / 2
        half_eye = self.ioc_dist / 2.0
        eye_y = cy - 20.0
        kps5 = np.array([
            [cx - half_eye, eye_y],       # right eye
            [cx + half_eye, eye_y],       # left eye
            [cx, cy],                     # nose
            [cx - half_eye * 0.8, cy + 25.0], # mouth right
            [cx + half_eye * 0.8, cy + 25.0]  # mouth left
        ], dtype=np.float32)

        bbox = np.array([
            cx - half_eye * 2.2,
            cy - half_eye * 2.0,
            cx + half_eye * 2.2,
            cy + half_eye * 2.5
        ], dtype=np.float32)

        lmk106 = np.zeros((106, 2), dtype=np.float32)
        lmk106[:5] = kps5
        # Fill remaining landmarks smoothly around face
        for idx in range(5, 106):
            angle = 2.0 * np.pi * idx / 106.0
            lmk106[idx] = [cx + np.cos(angle) * half_eye * 1.5, cy + np.sin(angle) * half_eye * 1.5]

        return [FaceDetection(
            bbox=bbox,
            score=0.98,
            kps5=kps5,
            lmk106=lmk106
        )]

