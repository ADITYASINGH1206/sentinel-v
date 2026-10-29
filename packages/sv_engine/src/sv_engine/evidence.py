from dataclasses import dataclass

import cv2
import numpy as np
from sv_core.hashing import sha256_bytes
from sv_receipts.merkle import MerkleTree


def reshape_patch_logits_to_map(patch_logits_ktp: np.ndarray, grid: int = 16) -> np.ndarray:
    """Reshape (K, T, P) patch logits to (K, T, grid, grid) sigmoid probabilities."""
    K, T, P = patch_logits_ktp.shape
    if P != grid * grid:
        raise ValueError(f"Expected {grid * grid} patches, got {P}")
    raw = patch_logits_ktp.reshape((K, T, grid, grid))
    return 1.0 / (1.0 + np.exp(-raw))


def invert_affine_matrix(M: np.ndarray) -> np.ndarray:
    """Invert 2D affine transform matrix (2, 3) or (3, 3) to (2, 3) inverse."""
    if M.shape == (2, 3):
        M_homo = np.eye(3, dtype=np.float32)
        M_homo[:2, :] = M
        M_inv = np.linalg.inv(M_homo)
        return M_inv[:2, :]
    elif M.shape == (3, 3):
        M_inv = np.linalg.inv(M)
        return M_inv[:2, :]
    else:
        raise ValueError(f"Expected affine matrix with shape (2, 3) or (3, 3), got {M.shape}")


def warp_heatmap_to_source_frame(
    heatmap_grid: np.ndarray,
    inv_affine_matrix: np.ndarray,
    out_width: int,
    out_height: int,
) -> np.ndarray:
    """Bilinearly upsample (grid, grid) patch map to 224, pad to 256, and warp with M^{-1}."""
    # 1. Bilinearly upsample grid -> 224x224
    up224 = cv2.resize(heatmap_grid.astype(np.float32), (224, 224), interpolation=cv2.INTER_LINEAR)

    # 2. Pad 16px border to match 256x256 store crop coordinates with reflection padding
    padded256 = np.pad(up224, ((16, 16), (16, 16)), mode="reflect")

    # 3. Warp with inverse affine matrix back to original frame size (out_width, out_height)
    M_inv_2x3 = inv_affine_matrix[:2, :].astype(np.float32)
    warped = cv2.warpAffine(
        padded256,
        M_inv_2x3,
        (out_width, out_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    return warped.astype(np.float32)


def apply_colormap_magma(heatmap: np.ndarray, alpha_floor: float = 0.15) -> np.ndarray:
    """Apply sequential magma colormap with fixed [0, 1] scale and alpha floor.

    Args:
        heatmap: 2D float32 array with probabilities in [0.0, 1.0].
        alpha_floor: Values below this threshold are transparent (alpha = 0).

    Returns:
        (H, W, 4) uint8 RGBA array.
    """
    # Fixed scale [0, 1] — never min-max normalized per frame
    clipped = np.clip(heatmap, 0.0, 1.0)
    u8 = (clipped * 255.0).astype(np.uint8)

    # cv2.applyColorMap returns BGR
    colormap_bgr = cv2.applyColorMap(u8, cv2.COLORMAP_MAGMA)
    colormap_rgb = cv2.cvtColor(colormap_bgr, cv2.COLOR_BGR2RGB)

    # Alpha channel: transparent if below alpha_floor, otherwise proportional to score
    alpha = np.where(clipped < alpha_floor, 0, (clipped * 255.0)).astype(np.uint8)

    return np.dstack([colormap_rgb, alpha])


def cap_resolution_720p(
    width: int,
    height: int,
    max_h: int = 720,
    max_w: int = 1280,
) -> tuple[int, int]:
    """Calculate dimensions capped at 720p preserving aspect ratio with even dimensions."""
    if height <= max_h and width <= max_w:
        # Ensure even numbers for video codecs
        return (width - (width % 2), height - (height % 2))

    scale = min(max_h / float(height), max_w / float(width))
    new_w = int(round(width * scale / 2.0) * 2)
    new_h = int(round(height * scale / 2.0) * 2)
    return max(2, new_w), max(2, new_h)


def compute_evidence_root(artifact_hashes: list[str]) -> str:
    """Compute Merkle evidence root over all artifact SHA-256 digests."""
    if not artifact_hashes:
        return sha256_bytes(b"")

    # Sort hashes deterministically
    sorted_hashes = sorted(artifact_hashes)
    tree = MerkleTree(sorted_hashes)
    return tree.root_hex


@dataclass(frozen=True)
class EvidenceFrame:
    clip_k: int
    frame_t: int
    orig_frame_idx: int
    heatmap_raw: np.ndarray  # (H, W) float32 in [0, 1]
    heatmap_rgba: np.ndarray  # (H, W, 4) uint8 RGBA
    score: float  # Mean uncalibrated patch probability in [0, 1]; not calibrated p_bal


@dataclass(frozen=True)
class TrackEvidence:
    track_idx: int
    frames: list[EvidenceFrame]
    manifest: dict[str, str]  # relative filename -> sha256 hex
    evidence_root: str


@dataclass(frozen=True)
class EvidencePackage:
    analysis_id: str
    tracks: list[TrackEvidence]
    decisive_track_idx: int
    evidence_root: str
    manifest: dict[str, str]  # all artifacts: relative filename -> sha256 hex


def generate_track_evidence(
    track_idx: int,
    patch_logits_ktp: np.ndarray,
    affine_matrices_M: np.ndarray,
    frame_numbers: np.ndarray,
    out_width: int,
    out_height: int,
    grid: int = 16,
    alpha_floor: float = 0.15,
) -> list[EvidenceFrame]:
    """Generate warped evidence frames and RGBA heatmaps for a single track.

    Args:
        track_idx: index of track
        patch_logits_ktp: (K, T, P) patch logits array
        affine_matrices_M: (K, T, 2, 3) 256-space forward affine crop matrices
        frame_numbers: (K, T) original video frame numbers
        out_width: destination frame width
        out_height: destination frame height
        grid: patch grid size (16 for CLIP variants, 14 for CNN)
        alpha_floor: threshold below which heatmap is fully transparent
    """
    maps = reshape_patch_logits_to_map(patch_logits_ktp, grid=grid)
    K, T, _, _ = maps.shape

    frames: list[EvidenceFrame] = []
    for k in range(K):
        for t in range(T):
            grid_map = maps[k, t]
            frame_score = float(np.mean(grid_map))
            orig_idx = int(frame_numbers[k, t])

            M = affine_matrices_M[k, t]
            M_inv = invert_affine_matrix(M)

            warped_map = warp_heatmap_to_source_frame(
                grid_map,
                M_inv,
                out_width=out_width,
                out_height=out_height,
            )

            rgba_map = apply_colormap_magma(warped_map, alpha_floor=alpha_floor)

            frames.append(
                EvidenceFrame(
                    clip_k=k,
                    frame_t=t,
                    orig_frame_idx=orig_idx,
                    heatmap_raw=warped_map,
                    heatmap_rgba=rgba_map,
                    score=frame_score,
                )
            )

    return frames


__all__ = [
    "reshape_patch_logits_to_map",
    "invert_affine_matrix",
    "warp_heatmap_to_source_frame",
    "apply_colormap_magma",
    "cap_resolution_720p",
    "compute_evidence_root",
    "EvidenceFrame",
    "TrackEvidence",
    "EvidencePackage",
    "generate_track_evidence",
]
