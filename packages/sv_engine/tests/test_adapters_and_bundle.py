# ruff: noqa: I001
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

root_dir = str(Path(__file__).resolve().parents[3])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sv_engine.adapters.utils import ensure_smsdt_in_path

ensure_smsdt_in_path()

# fmt: off
from smsdt.models.clip_encoder import CLIP_MEAN, CLIP_STD  # noqa: E402
# fmt: on
from sv_engine.adapters import (
    ClipSAdapter,
    ClipSTAdapter,
    CnnP1Adapter,
    FullCAdapter,
    get_adapter,
    load_state_dict_strict,
    verify_bundle_checksums,
)

from tools.fit_calibration import (
    fit_calibration_and_metrics,
)
from tools.make_bundle import build_bundle
from tools.parity_check import run_parity_comparison


def test_adapter_factory_and_variants():
    """Verify factory instantiation and variant properties."""
    st_adapter = get_adapter("st")
    assert isinstance(st_adapter, ClipSTAdapter)
    assert st_adapter.T == 8
    assert st_adapter.grid == 16

    s_adapter = get_adapter("s")
    assert isinstance(s_adapter, ClipSAdapter)
    assert s_adapter.T == 1
    assert s_adapter.grid == 16

    cnn_adapter = get_adapter("cnn")
    assert isinstance(cnn_adapter, CnnP1Adapter)
    assert cnn_adapter.T == 8
    assert cnn_adapter.grid == 14

    full_adapter = get_adapter("full")
    assert isinstance(full_adapter, FullCAdapter)
    with pytest.raises(NotImplementedError) as exc_info:
        full_adapter.load("dummy_dir")
    assert "Blocker B1" in str(exc_info.value)

    with pytest.raises(ValueError):
        get_adapter("invalid_variant_name")


def test_normalization_invariants():
    """Verify normalization: CLIP uses mean/std while CNN uses pure [0, 1]."""
    st_adapter = ClipSTAdapter()
    cnn_adapter = CnnP1Adapter()

    frames_u8 = np.zeros((2, 8, 224, 224, 3), dtype=np.uint8)
    frames_u8[:, :, :, :, :] = 128

    # 1. CLIP ST Normalization
    norm_st = st_adapter.normalize(frames_u8)
    assert norm_st.shape == (2, 8, 3, 224, 224)
    expected_c0 = (128.0 / 255.0 - CLIP_MEAN[0]) / CLIP_STD[0]
    assert np.isclose(float(norm_st[0, 0, 0, 0, 0]), expected_c0, atol=1e-4)

    # 2. CNN Phase 1 Normalization: [0, 1], NO mean/std
    norm_cnn = cnn_adapter.normalize(frames_u8)
    assert norm_cnn.shape == (2, 8, 3, 224, 224)
    expected_cnn = 128.0 / 255.0
    assert np.isclose(float(norm_cnn[0, 0, 0, 0, 0]), expected_cnn, atol=1e-4)


def test_strict_weight_loading_guard():
    """Verify strict weight loading asserts missing_keys == [] and unexpected_keys == []."""

    class SimpleModule(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = torch.nn.Linear(10, 2)
            self.bias = torch.nn.Parameter(torch.zeros(2))

    module = SimpleModule()

    # Clean state dict should pass
    clean_dict = {
        "linear.weight": torch.randn(2, 10),
        "linear.bias": torch.randn(2),
        "bias": torch.randn(2),
    }
    load_state_dict_strict(module, clean_dict)

    # Missing keys should fail loudly
    incomplete_dict = {"linear.weight": torch.randn(2, 10)}
    with pytest.raises(RuntimeError) as exc_info:
        load_state_dict_strict(module, incomplete_dict)
    assert "Strict weight loading failed" in str(exc_info.value)
    assert "Missing keys" in str(exc_info.value)

    # Unexpected keys should fail loudly
    unexpected_dict = dict(clean_dict)
    unexpected_dict["extra_bogus_layer.weight"] = torch.randn(5, 5)
    with pytest.raises(RuntimeError) as exc_info:
        load_state_dict_strict(module, unexpected_dict)
    assert "Unexpected keys" in str(exc_info.value)


def test_make_bundle_and_checksum_verification():
    """Verify bundle builder produces safetensors, manifest, calibration and checksums."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock checkpoint dict
        ckpt_path = os.path.join(tmpdir, "model.pt")
        dummy_weights = {
            "proj.0.weight": torch.randn(1024),
            "proj.0.bias": torch.randn(1024),
            "proj.1.weight": torch.randn(384, 1024),
            "proj.1.bias": torch.randn(384),
        }
        torch.save(dummy_weights, ckpt_path)

        # Create mock validation scores CSV
        csv_path = os.path.join(tmpdir, "val_scores.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("u,label\n")
            for i in range(100):
                # Class 0 centered around -1.0, Class 1 centered around +1.0
                score = -1.2 + np.random.randn() * 0.5 if i < 50 else 1.2 + np.random.randn() * 0.5
                f.write(f"{score},{0 if i < 50 else 1}\n")

        bundle_dir = os.path.join(tmpdir, "bundle_out")
        build_bundle(ckpt_path=ckpt_path, variant="st", val_scores_csv=csv_path, out_dir=bundle_dir)

        assert os.path.exists(os.path.join(bundle_dir, "weights.safetensors"))
        assert os.path.exists(os.path.join(bundle_dir, "manifest.json"))
        assert os.path.exists(os.path.join(bundle_dir, "calibration.json"))
        assert os.path.exists(os.path.join(bundle_dir, "operating_points.json"))
        assert os.path.exists(os.path.join(bundle_dir, "clip_config.json"))
        assert os.path.exists(os.path.join(bundle_dir, "checksums.sha256"))

        # Checksum verification should pass
        assert verify_bundle_checksums(bundle_dir) is True

        # Tampering with any file must fail loudly
        with open(os.path.join(bundle_dir, "manifest.json"), "a", encoding="utf-8") as f:
            f.write(" ")
        with pytest.raises(ValueError) as exc_info:
            verify_bundle_checksums(bundle_dir)
        assert "Bundle checksum verification failed" in str(exc_info.value)


def test_fit_calibration_and_operating_points():
    """Verify calibration fitting and operating points computation."""
    rng = np.random.default_rng(123)
    # Synthetic well-separated scores
    u_neg = rng.normal(-1.5, 0.5, 200)
    u_pos = rng.normal(1.5, 0.5, 200)
    u_all = np.concatenate([u_neg, u_pos])
    y_all = np.concatenate([np.zeros(200, dtype=np.int32), np.ones(200, dtype=np.int32)])

    calib, op = fit_calibration_and_metrics(u_all, y_all, variant_id="smsdt-st-b")

    assert "parameters" in calib
    assert "a" in calib["parameters"] and "b" in calib["parameters"]
    assert calib["parameters"]["a"] > 0.0  # Positive scaling for logit correlation
    assert 0.0 < calib["youden_tau_star"] < 1.0

    assert op["validation_auc"] > 0.95
    assert op["expected_calibration_error"] >= 0.0
    assert len(op["fixed_fpr_points"]) == 2
    assert op["fixed_fpr_points"][0]["target_fpr"] == 0.01
    assert op["fixed_fpr_points"][1]["target_fpr"] == 0.05


def test_parity_check_comparison():
    """Verify parity comparison criteria conform to SPEC §6.9."""
    rng = np.random.default_rng(42)
    serve = rng.normal(0.0, 1.0, 50)
    research_close = serve + rng.normal(0.0, 0.01, 50)
    research_divergent = serve + rng.normal(0.5, 0.2, 50)
    labels = np.array([1 if i % 2 == 0 else 0 for i in range(50)], dtype=np.int32)

    # Within tolerance: should PASS
    passed, rep = run_parity_comparison(serve, research_close, labels)
    assert passed is True
    assert rep["median_passed"] is True
    assert rep["p95_passed"] is True
    assert rep["auc_passed"] is True

    # Exceeds tolerance: should FAIL
    failed, rep_fail = run_parity_comparison(serve, research_divergent, labels)
    assert failed is False
    assert rep_fail["median_passed"] is False
