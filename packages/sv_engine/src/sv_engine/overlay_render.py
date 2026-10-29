import json
import os
from typing import Any

import cv2
import numpy as np
from sv_core.hashing import sha256_file

from sv_engine.evidence import EvidenceFrame, cap_resolution_720p, compute_evidence_root

MANDATORY_DISCLAIMER = "Screening aid — not proof. Human review required for consequential action."


def save_webp_frame(
    rgba_img: np.ndarray,
    out_path: str,
    max_h: int = 720,
    max_w: int = 1280,
    quality: int = 90,
) -> str:
    """Save an RGBA heat-map frame as WebP image capped at 720p and return SHA-256."""
    h, w = rgba_img.shape[:2]
    target_w, target_h = cap_resolution_720p(w, h, max_h=max_h, max_w=max_w)

    if (target_w, target_h) != (w, h):
        resized_rgba = cv2.resize(rgba_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        resized_rgba = rgba_img

    # OpenCV expects BGRA format for 4-channel image writing
    bgra = cv2.cvtColor(resized_rgba, cv2.COLOR_RGBA2BGRA)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    success = cv2.imwrite(out_path, bgra, [cv2.IMWRITE_WEBP_QUALITY, quality])
    if not success:
        raise RuntimeError(f"Failed to write WebP image to {out_path}")

    return sha256_file(out_path)


def draw_score_banner(
    frame_bgr: np.ndarray,
    p_score: float,
    decision_band: str,
) -> np.ndarray:
    """Burn top score banner and bottom screening disclaimer onto video frame."""
    h, w = frame_bgr.shape[:2]
    annotated = frame_bgr.copy()

    # 1. Top banner: Dark transparent header bar (height 36px)
    top_bar_h = min(40, max(28, int(h * 0.06)))
    top_overlay = annotated.copy()
    cv2.rectangle(top_overlay, (0, 0), (w, top_bar_h), (20, 20, 25), -1)
    cv2.addWeighted(top_overlay, 0.85, annotated, 0.15, 0, annotated)

    band_text = decision_band.replace("_", " ").title()
    header_text = f"SENTINEL-V | Score: {p_score:.2f} | {band_text}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.4, min(0.65, w / 1200.0))
    cv2.putText(
        annotated,
        header_text,
        (12, int(top_bar_h * 0.68)),
        font,
        font_scale,
        (240, 240, 245),
        1,
        cv2.LINE_AA,
    )

    # 2. Bottom banner: Mandatory screening aid disclaimer (SPEC §14.13)
    bot_bar_h = min(32, max(22, int(h * 0.045)))
    bot_overlay = annotated.copy()
    cv2.rectangle(bot_overlay, (0, h - bot_bar_h), (w, h), (15, 15, 20), -1)
    cv2.addWeighted(bot_overlay, 0.85, annotated, 0.15, 0, annotated)

    bot_scale = max(0.32, min(0.48, w / 1600.0))
    # Replace unicode em-dash with standard hyphen for ASCII OpenCV text
    ascii_disclaimer = MANDATORY_DISCLAIMER.replace("—", "-")
    cv2.putText(
        annotated,
        ascii_disclaimer,
        (12, h - int(bot_bar_h * 0.35)),
        font,
        bot_scale,
        (190, 190, 200),
        1,
        cv2.LINE_AA,
    )

    return annotated


def _fourcc(tag: str) -> int:
    """Safely obtain OpenCV VideoWriter FourCC code across versions.

    Uses getattr fallback for compatibility with OpenCV builds where VideoWriter_fourcc
    is either a top-level function or a class method on cv2.VideoWriter.
    """
    fn = getattr(cv2, "VideoWriter_fourcc", None)
    if fn is not None:
        return int(fn(*tag))
    return int(getattr(cv2.VideoWriter, "fourcc")(*tag))  # noqa: B009


def render_overlay_video(
    source_frames: list[np.ndarray],
    evidence_frames: list[EvidenceFrame],
    output_path: str,
    fps: float = 24.0,
    p_score: float = 0.5,
    decision_band: str = "needs_review",
    max_h: int = 720,
    max_w: int = 1280,
    source_frame_indices: list[int] | None = None,
) -> str:
    """Render MP4 video with burned-in heat-maps, score banner, and disclaimer."""
    if not source_frames:
        raise ValueError("source_frames list cannot be empty")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Index evidence frames by original frame number
    evidence_by_fidx = {ef.orig_frame_idx: ef for ef in evidence_frames}

    sample_h, sample_w = source_frames[0].shape[:2]
    target_w, target_h = cap_resolution_720p(sample_w, sample_h, max_h=max_h, max_w=max_w)

    # Try H.264 codecs or fallback to mp4v
    fourcc = _fourcc("avc1")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
    if not writer.isOpened():
        fourcc = _fourcc("mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))

    if not writer.isOpened():
        raise RuntimeError(
            f"Could not open VideoWriter for {output_path} with codecs 'avc1' or 'mp4v'."
        )

    try:
        for idx, src_frame in enumerate(source_frames):
            frame_bgr = src_frame.copy()
            if frame_bgr.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_BGRA2BGR)

            # Match evidence by original frame number (handling trimmed/sampled videos)
            orig_fidx = source_frame_indices[idx] if source_frame_indices is not None else idx

            # Check if this frame has an evidence heatmap
            if orig_fidx in evidence_by_fidx:
                ef = evidence_by_fidx[orig_fidx]
                rgba = ef.heatmap_rgba
                # Alpha blending: blend RGBA heatmap onto frame_bgr
                alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                heatmap_bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)

                blended: np.ndarray = (
                    (1.0 - alpha) * frame_bgr.astype(np.float32)
                    + alpha * heatmap_bgr.astype(np.float32)
                ).astype(np.uint8)
            else:
                blended = frame_bgr

            # Resize to target resolution if needed
            if (blended.shape[1], blended.shape[0]) != (target_w, target_h):
                blended = cv2.resize(
                    blended, (target_w, target_h), interpolation=cv2.INTER_AREA
                ).astype(np.uint8)

            # Burn in header score and footer disclaimer
            final_frame = draw_score_banner(blended, p_score=p_score, decision_band=decision_band)
            writer.write(final_frame)
    finally:
        writer.release()

    return sha256_file(output_path)


def write_manifest_json(
    manifest_data: dict[str, Any],
    output_path: str,
) -> str:
    """Write artifact manifest JSON file and return its SHA-256."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True)
    return sha256_file(output_path)


def render_track_artifacts(
    track_evidence_frames: list[EvidenceFrame],
    output_dir: str,
    track_idx: int,
    source_frames: list[np.ndarray] | None = None,
    fps: float = 24.0,
    p_score: float = 0.5,
    decision_band: str = "needs_review",
    source_frame_indices: list[int] | None = None,
) -> tuple[dict[str, str], str]:
    """Render all artifacts for a single track: WebP frames, overlay MP4, and manifest.json.

    Returns:
        (manifest_dict, evidence_root)
    """
    os.makedirs(output_dir, exist_ok=True)
    manifest: dict[str, str] = {}

    # 1. Save WebP frame heatmaps
    for ef in track_evidence_frames:
        filename = f"webp/frame_k{ef.clip_k:02d}_t{ef.frame_t:02d}_idx{ef.orig_frame_idx:05d}.webp"
        full_path = os.path.join(output_dir, filename)
        sha = save_webp_frame(ef.heatmap_rgba, full_path)
        manifest[filename] = sha

    # 2. Render MP4 overlay video if source frames provided
    if source_frames:
        video_filename = f"overlay_track_{track_idx}.mp4"
        video_path = os.path.join(output_dir, video_filename)
        sha_video = render_overlay_video(
            source_frames=source_frames,
            evidence_frames=track_evidence_frames,
            output_path=video_path,
            fps=fps,
            p_score=p_score,
            decision_band=decision_band,
            source_frame_indices=source_frame_indices,
        )
        manifest[video_filename] = sha_video

    # 3. Write manifest.json including artifact hashes and frame/track metadata
    manifest_payload: dict[str, Any] = {
        "track_idx": track_idx,
        "p_score": p_score,
        "decision_band": decision_band,
        "artifacts": dict(manifest),
        "frames": [
            {
                "clip_k": ef.clip_k,
                "frame_t": ef.frame_t,
                "orig_frame_idx": ef.orig_frame_idx,
                "score": ef.score,
                "file": f"webp/frame_k{ef.clip_k:02d}_t{ef.frame_t:02d}_idx{ef.orig_frame_idx:05d}.webp",
            }
            for ef in track_evidence_frames
        ],
    }
    manifest_filename = "manifest.json"
    manifest_path = os.path.join(output_dir, manifest_filename)
    sha_manifest = write_manifest_json(manifest_payload, manifest_path)
    manifest[manifest_filename] = sha_manifest

    # 4. Compute Merkle root over all artifact hashes
    all_hashes = list(manifest.values())
    evidence_root = compute_evidence_root(all_hashes)

    return manifest, evidence_root


__all__ = [
    "MANDATORY_DISCLAIMER",
    "save_webp_frame",
    "draw_score_banner",
    "render_overlay_video",
    "write_manifest_json",
    "render_track_artifacts",
]
