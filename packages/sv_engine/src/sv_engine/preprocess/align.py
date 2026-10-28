import os
import sys
from typing import Optional, Tuple
import cv2
import numpy as np

# Ensure third_party/smsdt is in sys.path if not installed
SMSDT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "third_party", "smsdt"))
if os.path.isdir(SMSDT_PATH) and SMSDT_PATH not in sys.path:
    sys.path.insert(0, SMSDT_PATH)

try:
    from smsdt.preprocess.align_crop import loose_template, crop_frame, warp_points
except ImportError:
    # Standalone fallback if submodule is not mounted
    REF_5PT = np.array([
        [38.2946, 51.6963], [73.5318, 51.5014],
        [56.0252, 71.7366], [41.5493, 92.3655],
        [70.7299, 92.2041],
    ], dtype=np.float32)

    def loose_template(out=256, margin=1.3):
        t = (REF_5PT - 56.0) / margin + 56.0
        return t * (out / 112.0)

    def crop_frame(frame_bgr, kps5, out=256, margin=1.3):
        dst = loose_template(out=out, margin=margin)
        M, _ = cv2.estimateAffinePartial2D(kps5.astype(np.float32), dst, method=cv2.LMEDS)
        if M is None:
            return None, None
        crop = cv2.warpAffine(frame_bgr, M, (out, out), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REFLECT101)
        return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), M

    def warp_points(pts, M):
        return pts @ M[:, :2].T + M[:, 2]


def align_and_crop(
    frame_bgr: np.ndarray,
    kps5: np.ndarray,
    out_store: int = 256,
    crop_size: int = 224,
    margin: float = 1.3
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """Align frame using 5 keypoints to loose template, then extract center crop.
    
    Args:
        frame_bgr: (H, W, 3) BGR uint8 input frame
        kps5: (5, 2) facial keypoint coordinates
        out_store: intermediate store resolution (default 256)
        crop_size: final model input crop resolution (default 224)
        margin: context margin around face (default 1.3)
        
    Returns:
        crop_224: (crop_size, crop_size, 3) RGB uint8 array
        M: (2, 3) affine partial matrix mapping frame coords to out_store
        M_224: (2, 3) affine matrix mapping frame coords to crop_size coords
    """
    crop_rgb_256, M = crop_frame(frame_bgr, kps5, out=out_store, margin=margin)
    if crop_rgb_256 is None or M is None:
        return None, None, None

    # Deterministic center-crop
    offset = (out_store - crop_size) // 2
    crop_224 = crop_rgb_256[offset:offset + crop_size, offset:offset + crop_size, :]
    
    # Affine matrix for crop_size: translate by -offset in both axes
    M_224 = np.copy(M)
    M_224[:, 2] -= float(offset)

    return crop_224, M, M_224


def warp_landmarks_224(lmk: np.ndarray, M_224: np.ndarray) -> np.ndarray:
    """Warp facial landmarks directly into 224 crop coordinates using M_224."""
    return warp_points(lmk, M_224)

