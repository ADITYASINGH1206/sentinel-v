import json
import os
import tempfile

import cv2
import numpy as np
import pytest
from sv_core.hashing import sha256_bytes, sha256_file
from sv_engine.evidence import (
    EvidenceFrame,
    apply_colormap_magma,
    cap_resolution_720p,
    compute_evidence_root,
    generate_track_evidence,
    invert_affine_matrix,
    reshape_patch_logits_to_map,
)
from sv_engine.overlay_render import (
    MANDATORY_DISCLAIMER,
    draw_score_banner,
    render_overlay_video,
    render_track_artifacts,
    save_webp_frame,
    write_manifest_json,
)


def test_reshape_patch_logits_to_map():
    # 1. Standard grid 16 (CLIP variants: P=256)
    K, T, P = 8, 8, 256
    logits = np.random.randn(K, T, P).astype(np.float32)
    maps = reshape_patch_logits_to_map(logits, grid=16)

    assert maps.shape == (8, 8, 16, 16)
    assert np.all(maps >= 0.0)
    assert np.all(maps <= 1.0)

    # 2. CNN grid 14 (P=196)
    logits_cnn = np.random.randn(K, T, 196).astype(np.float32)
    maps_cnn = reshape_patch_logits_to_map(logits_cnn, grid=14)
    assert maps_cnn.shape == (8, 8, 14, 14)

    # 3. Shape mismatch raises ValueError
    with pytest.raises(ValueError, match="Expected 256 patches"):
        reshape_patch_logits_to_map(np.zeros((8, 8, 100)), grid=16)


def test_colormap_magma_alpha_floor():
    # Create test heatmap with known values
    heatmap = np.zeros((10, 10), dtype=np.float32)
    heatmap[0:5, :] = 0.10  # Below floor 0.15 -> must be transparent
    heatmap[5:10, :] = 0.80  # Above floor 0.15 -> must be opaque

    rgba = apply_colormap_magma(heatmap, alpha_floor=0.15)
    assert rgba.shape == (10, 10, 4)
    assert rgba.dtype == np.uint8

    # Sub-floor regions must have alpha == 0
    assert np.all(rgba[0:5, :, 3] == 0)

    # Above-floor regions must have positive alpha
    assert np.all(rgba[5:10, :, 3] > 0)
    assert np.isclose(rgba[5, 5, 3], int(0.80 * 255), atol=2)


def test_colormap_fixed_scale():
    # Verify fixed [0, 1] scaling is applied (no min-max stretching)
    low_heatmap = np.ones((5, 5), dtype=np.float32) * 0.30
    high_heatmap = np.ones((5, 5), dtype=np.float32) * 0.90

    low_rgba = apply_colormap_magma(low_heatmap, alpha_floor=0.15)
    high_rgba = apply_colormap_magma(high_heatmap, alpha_floor=0.15)

    # If min-max scaling were mistakenly applied, both would map to 255
    assert not np.array_equal(low_rgba[:, :, :3], high_rgba[:, :, :3])
    assert np.mean(low_rgba[:, :, :3]) < np.mean(high_rgba[:, :, :3])
    assert low_rgba[0, 0, 3] < high_rgba[0, 0, 3]


def test_geometric_back_projection_roundtrip():
    # Affine matrix mapping (140, 100) -> 256 crop
    # Forward affine: scale by 1.2, translate (50, 40)
    M = np.array([[1.2, 0.0, 50.0], [0.0, 1.2, 40.0]], dtype=np.float32)
    M_inv = invert_affine_matrix(M)

    orig_pt = np.array([120.0, 80.0], dtype=np.float32)

    # Forward project
    pt_crop = M @ np.array([orig_pt[0], orig_pt[1], 1.0], dtype=np.float32)

    # Invert back
    pt_recovered = M_inv @ np.array([pt_crop[0], pt_crop[1], 1.0], dtype=np.float32)

    # Precision error must be < 0.5 px
    dist = float(np.linalg.norm(orig_pt - pt_recovered))
    assert dist < 0.001


def test_cap_resolution_720p():
    # 1. 1080p video (1920x1080) -> capped to 720p
    w, h = cap_resolution_720p(1920, 1080, max_h=720, max_w=1280)
    assert h == 720
    assert w == 1280
    assert w % 2 == 0 and h % 2 == 0

    # 2. 4K video (3840x2160) -> capped to 720p
    w_4k, h_4k = cap_resolution_720p(3840, 2160, max_h=720, max_w=1280)
    assert h_4k <= 720
    assert w_4k <= 1280
    assert w_4k % 2 == 0 and h_4k % 2 == 0

    # 3. Small video (640x480) -> untouched (even dimensions preserved)
    w_small, h_small = cap_resolution_720p(640, 480, max_h=720, max_w=1280)
    assert w_small == 640
    assert h_small == 480


def test_save_webp_frame():
    rgba = np.zeros((100, 150, 4), dtype=np.uint8)
    rgba[:, :, 0] = 255  # Red
    rgba[:, :, 3] = 200  # Semi-transparent

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test.webp")
        sha = save_webp_frame(rgba, out_path)

        assert os.path.exists(out_path)
        assert len(sha) == 64
        assert sha == sha256_file(out_path)

        # Check readable by OpenCV
        loaded = cv2.imread(out_path, cv2.IMREAD_UNCHANGED)
        assert loaded is not None
        assert loaded.shape == (100, 150, 4)


def test_render_overlay_video():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 16 dummy frames (240x320 BGR)
        src_frames = [np.ones((240, 320, 3), dtype=np.uint8) * 100 for _ in range(16)]

        # Create one evidence frame for frame idx 5
        ef_rgba = np.zeros((240, 320, 4), dtype=np.uint8)
        ef_rgba[50:150, 50:150] = [255, 50, 50, 200]
        ef = [
            EvidenceFrame(
                clip_k=0,
                frame_t=5,
                orig_frame_idx=5,
                heatmap_raw=np.zeros((240, 320), dtype=np.float32),
                heatmap_rgba=ef_rgba,
                score=0.88,
            )
        ]

        mp4_path = os.path.join(tmpdir, "overlay.mp4")
        sha = render_overlay_video(
            source_frames=src_frames,
            evidence_frames=ef,
            output_path=mp4_path,
            fps=24.0,
            p_score=0.88,
            decision_band="likely_manipulated",
        )

        assert os.path.exists(mp4_path)
        assert len(sha) == 64
        assert os.path.getsize(mp4_path) > 0

        # Verify readable and frame count matches
        cap = cv2.VideoCapture(mp4_path)
        assert cap.isOpened()
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        assert count == 16
        cap.release()


def test_draw_score_banner_disclaimer_compliance():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    banner = draw_score_banner(frame, p_score=0.78, decision_band="needs_review")
    assert banner.shape == (240, 320, 3)
    # Ensure disclaimer string is present without bare forbidden words
    assert "proof" in MANDATORY_DISCLAIMER
    assert "Screening aid" in MANDATORY_DISCLAIMER


def test_manifest_and_evidence_root_integrity():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy artifacts
        f1 = os.path.join(tmpdir, "frame1.webp")
        f2 = os.path.join(tmpdir, "frame2.webp")
        with open(f1, "wb") as f:
            f.write(b"WEBP_DATA_1")
        with open(f2, "wb") as f:
            f.write(b"WEBP_DATA_2")

        manifest = {"frame1.webp": sha256_file(f1), "frame2.webp": sha256_file(f2)}
        manifest_path = os.path.join(tmpdir, "manifest.json")
        sha_m = write_manifest_json(manifest, manifest_path)
        manifest["manifest.json"] = sha_m

        # Verify file contents match manifest SHA-256
        for name, expected_sha in manifest.items():
            actual_sha = sha256_file(os.path.join(tmpdir, name))
            assert actual_sha == expected_sha

        # Verify deterministic evidence root
        root1 = compute_evidence_root(list(manifest.values()))
        root2 = compute_evidence_root(list(manifest.values()))
        assert root1 == root2
        assert len(root1) == 64

        # Modified artifact changes evidence root
        tampered_manifest = list(manifest.values())
        tampered_manifest[0] = sha256_bytes(b"tampered")
        tampered_root = compute_evidence_root(tampered_manifest)
        assert tampered_root != root1


def test_generate_track_evidence_and_render_artifacts_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        K, T, P = 2, 4, 256
        patch_logits = np.random.randn(K, T, P).astype(np.float32)

        # Affine matrices (2, 4, 2, 3)
        affine_M = np.zeros((K, T, 2, 3), dtype=np.float32)
        affine_M[:, :, 0, 0] = 1.0
        affine_M[:, :, 1, 1] = 1.0

        # Frame numbers (2, 4)
        frame_numbers = np.array([[0, 1, 2, 3], [4, 5, 6, 7]], dtype=np.int32)

        # 1. Generate evidence frames
        evidence_frames = generate_track_evidence(
            track_idx=0,
            patch_logits_ktp=patch_logits,
            affine_matrices_M=affine_M,
            frame_numbers=frame_numbers,
            out_width=320,
            out_height=240,
            grid=16,
            alpha_floor=0.15,
        )
        assert len(evidence_frames) == 8
        assert evidence_frames[0].heatmap_rgba.shape == (240, 320, 4)
        assert evidence_frames[0].orig_frame_idx == 0

        # 2. Render track artifacts
        src_frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(8)]
        manifest, evidence_root = render_track_artifacts(
            track_evidence_frames=evidence_frames,
            output_dir=tmpdir,
            track_idx=0,
            source_frames=src_frames,
            fps=24.0,
            p_score=0.45,
            decision_band="needs_review",
        )

        assert "manifest.json" in manifest
        assert "overlay_track_0.mp4" in manifest
        assert len(evidence_root) == 64
        manifest_file_path = os.path.join(tmpdir, "manifest.json")
        assert os.path.exists(manifest_file_path)
        assert os.path.exists(os.path.join(tmpdir, "overlay_track_0.mp4"))

        # 3. Verify manifest.json contains track and frame metadata
        with open(manifest_file_path, encoding="utf-8") as f:
            manifest_json = json.load(f)
        assert manifest_json["track_idx"] == 0
        assert manifest_json["p_score"] == 0.45
        assert manifest_json["decision_band"] == "needs_review"
        assert "artifacts" in manifest_json
        assert len(manifest_json["frames"]) == 8
        assert manifest_json["frames"][0]["orig_frame_idx"] == 0
