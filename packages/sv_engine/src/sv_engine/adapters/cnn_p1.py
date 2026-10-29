import os
from typing import Any, Optional
import numpy as np
import torch
import torch.nn as nn

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter, Variant
from sv_engine.adapters.utils import (
    ensure_smsdt_in_path,
    load_state_dict_strict,
    load_weights_dict,
    verify_bundle_checksums,
)

ensure_smsdt_in_path()
from smsdt.models.smsdt import SMSDT


class CnnP1Adapter:
    """Phase 1 Model Adapter: S-MSDT-CNN (EfficientNet-B4 + Haar DWT + DensePSIT 14x14)."""

    def __init__(self, model_id: str = "smsdt-cnn-p1", device: Optional[Any] = None):
        self.model_id = model_id
        self.variant: Variant = "cnn"
        self.T: int = 8
        self.grid: int = 14
        self.device = torch.device(device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model: Optional[SMSDT] = None

    def normalize(self, frames_u8: Any) -> torch.Tensor:
        """Convert uint8 (N, T, 224, 224, 3) to float32 (N, T, 3, 224, 224) in [0, 1] range (NO mean/std)."""
        if isinstance(frames_u8, np.ndarray):
            t = torch.from_numpy(frames_u8)
        else:
            t = frames_u8

        if t.ndim != 5:
            raise ValueError(f"Expected 5D tensor (N, T, 224, 224, 3), got shape {t.shape}")

        # Permute (N, T, H, W, C) -> (N, T, C, H, W) and scale to [0, 1]
        return t.permute(0, 1, 4, 2, 3).to(dtype=torch.float32) / 255.0

    def load(self, bundle_dir: str, device: Optional[Any] = None) -> None:
        """Strictly load S-MSDT-CNN weights and initialize model offline."""
        if device is not None:
            self.device = torch.device(device)

        if os.path.isdir(bundle_dir) and os.path.exists(os.path.join(bundle_dir, "checksums.sha256")):
            verify_bundle_checksums(bundle_dir)

        self.model = SMSDT(grid=self.grid, embed_dim=256, max_frames=16, use_dense_psit=True)

        weights = load_weights_dict(bundle_dir, device=self.device)
        load_state_dict_strict(self.model, weights)

        self.model.eval()
        self.model.to(self.device)

    @torch.inference_mode()
    def predict(self, batch: ClipBatch) -> ClipOutput:
        """Execute inference over batch of clips."""
        if self.model is None:
            raise RuntimeError("Model adapter is not loaded. Call adapter.load(bundle_dir) first.")

        frames_norm = self.normalize(batch.frames_u8).to(self.device)
        conf_tensor = None
        if batch.conf is not None:
            if isinstance(batch.conf, np.ndarray):
                conf_tensor = torch.from_numpy(batch.conf).to(dtype=torch.float32, device=self.device)
            else:
                conf_tensor = batch.conf.to(dtype=torch.float32, device=self.device)

        logits, patch_logits = self.model(frames_norm, conf=conf_tensor)

        logits_np = logits.detach().cpu().numpy()
        patch_np = patch_logits.detach().cpu().numpy() if patch_logits is not None else None

        return ClipOutput(
            logits=logits_np,
            patch_logits=patch_np,
            grid=self.grid
        )

    def warmup(self) -> None:
        """Execute dummy forward pass to warm up CUDA kernels."""
        if self.model is not None:
            dummy_frames = torch.zeros((1, self.T, 3, 224, 224), dtype=torch.float32, device=self.device)
            dummy_conf = torch.ones((1, self.T), dtype=torch.float32, device=self.device)
            with torch.inference_mode():
                _ = self.model(dummy_frames, conf=dummy_conf)

