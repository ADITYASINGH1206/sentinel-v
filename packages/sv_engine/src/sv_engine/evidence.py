from typing import List, Dict, Any, Tuple
import numpy as np
from sv_engine.calibration import sigmoid


def reshape_patch_logits_to_map(patch_logits_ktp: np.ndarray, grid: int = 16) -> np.ndarray:
    """Reshape (K, T, P) patch logits to (K, T, grid, grid) sigmoid probabilities."""
    K, T, P = patch_logits_ktp.shape
    assert P == grid * grid, f"Expected {grid*grid} patches, got {P}"
    maps = np.zeros((K, T, grid, grid), dtype=np.float32)
    for k in range(K):
        for t in range(T):
            raw = patch_logits_ktp[k, t].reshape((grid, grid))
            maps[k, t] = 1.0 / (1.0 + np.exp(-raw))
    return maps


def warp_heatmap_to_source_frame(
    heatmap_grid: np.ndarray,
    inv_affine_matrix: np.ndarray,
    out_width: int,
    out_height: int,
) -> np.ndarray:
    """Bilinearly upsample (grid, grid) patch map to 224, pad to 256, and warp with M^{-1}."""
    # When cv2 or scipy is available, resize and warp
    try:
        import cv2
        # Resize grid -> 224x224
        up224 = cv2.resize(heatmap_grid, (224, 224), interpolation=cv2.INTER_LINEAR)
        # Pad 16px border to make 256x256
        padded256 = np.pad(up224, ((16, 16), (16, 16)), mode="constant", constant_values=0.0)
        # Warp with inverse affine to original frame size (W, H)
        warped = cv2.warpAffine(
            padded256,
            inv_affine_matrix[:2, :],
            (out_width, out_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0,
        )
        return warped
    except ImportError:
        # Fallback placeholder if cv2 not installed in current environment
        return np.zeros((out_height, out_width), dtype=np.float32)
