import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

root_dir = str(Path(__file__).resolve().parents[3])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sv_engine.adapters.base import ClipBatch
from sv_engine.adapters.full_c import FullCAdapter
from sv_engine.adapters.utils import verify_bundle_checksums


def test_real_weights_bundle_checksums():
    """Verify that models/bundle-2026-11-default/smsdt-full-c has valid signed checksums."""
    bundle_dir = "models/bundle-2026-11-default/smsdt-full-c"
    if not os.path.exists(bundle_dir):
        pytest.skip("Full C bundle not present on disk")
    assert verify_bundle_checksums(bundle_dir) is True


def test_real_weights_forward_pass_cpu():
    """Verify that FullCAdapter loads safetensors and executes forward pass with real weights."""
    bundle_dir = "models/bundle-2026-11-default/smsdt-full-c"
    if not os.path.exists(bundle_dir):
        pytest.skip("Full C bundle not present on disk")

    adapter = FullCAdapter(device="cpu")
    adapter.load(bundle_dir)

    dummy_frames = np.zeros((1, 8, 224, 224, 3), dtype=np.uint8)
    batch = ClipBatch(frames_u8=dummy_frames, landmarks106=None, conf=None)

    out = adapter.predict(batch)
    assert out.logits.shape == (1,)
    assert np.isfinite(out.logits[0])
    assert out.patch_logits is not None
    assert out.patch_logits.shape == (1, 8, 256)
    assert np.all(np.isfinite(out.patch_logits))

