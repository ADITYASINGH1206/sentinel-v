import os
from typing import Any

import numpy as np
import torch

from sv_engine.adapters.base import ClipBatch, ClipOutput, Variant
from sv_engine.adapters.utils import (
    ensure_smsdt_in_path,
    load_state_dict_strict,
    load_weights_dict,
    verify_bundle_checksums,
)

ensure_smsdt_in_path()
from smsdt.models.clip_encoder import CLIP_MEAN, CLIP_STD, CLIPFrameEncoder
from smsdt.models.smsdt_v2 import SMSDTv2

try:
    from transformers import CLIPVisionConfig
except ImportError:
    CLIPVisionConfig = None  # type: ignore[no-redef,assignment,misc]


class ClipSTAdapter:
    """Stage B Model Adapter: S-MSDT-ST (Spatiotemporal Transformer over CLIP ViT-L/14)."""

    def __init__(self, model_id: str = "smsdt-st-b", device: Any | None = None):
        self.model_id = model_id
        self.variant: Variant = "st"
        self.T: int = 8
        self.grid: int = 16
        self.device = torch.device(
            device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model: SMSDTv2 | None = None

    def normalize(self, frames_u8: Any) -> torch.Tensor:
        """Convert uint8 (N, T, 224, 224, 3) to float32 (N, T, 3, 224, 224) in CLIP normalization."""
        if isinstance(frames_u8, np.ndarray):
            t = torch.from_numpy(frames_u8)
        else:
            t = frames_u8

        if t.ndim != 5:
            raise ValueError(f"Expected 5D tensor (N, T, 224, 224, 3), got shape {t.shape}")

        # Permute (N, T, H, W, C) -> (N, T, C, H, W)
        t = t.permute(0, 1, 4, 2, 3).to(dtype=torch.float32) / 255.0

        mean = torch.tensor(CLIP_MEAN, dtype=torch.float32, device=t.device).view(1, 1, 3, 1, 1)
        std = torch.tensor(CLIP_STD, dtype=torch.float32, device=t.device).view(1, 1, 3, 1, 1)
        return (t - mean) / std

    def load(self, bundle_dir: str, device: Any | None = None) -> None:
        """Strictly load S-MSDT-ST weights and initialize model offline."""
        if device is not None:
            self.device = torch.device(device)

        if os.path.isdir(bundle_dir) and os.path.exists(
            os.path.join(bundle_dir, "checksums.sha256")
        ):
            verify_bundle_checksums(bundle_dir)

        # Check for offline CLIP config
        config = None
        if os.path.isdir(bundle_dir):
            cfg_path = os.path.join(bundle_dir, "clip_config.json")
            if os.path.exists(cfg_path) and CLIPVisionConfig is not None:
                config = CLIPVisionConfig.from_json_file(cfg_path)

        encoder = CLIPFrameEncoder(tune="layernorm", grad_ckpt=False, config=config)
        self.model = SMSDTv2(encoder=encoder, grid=self.grid, max_frames=self.T)

        weights = load_weights_dict(bundle_dir, device=self.device)
        load_state_dict_strict(self.model, weights)

        self.model.set_gradient_checkpointing(False)
        self.model.eval()
        self.model.to(self.device)

    @torch.inference_mode()
    def predict(self, batch: ClipBatch) -> ClipOutput:
        """Execute inference over batch of clips."""
        if self.model is None:
            raise RuntimeError("Model adapter is not loaded. Call adapter.load(bundle_dir) first.")

        frames_norm = self.normalize(batch.frames_u8).to(self.device)
        logits, patch_logits = self.model(frames_norm)

        logits_np = logits.detach().cpu().numpy()
        patch_np = patch_logits.detach().cpu().numpy() if patch_logits is not None else None

        return ClipOutput(logits=logits_np, patch_logits=patch_np, grid=self.grid)

    def warmup(self) -> None:
        """Execute dummy forward pass to warm up CUDA kernels."""
        if self.model is not None:
            dummy = torch.zeros((1, self.T, 3, 224, 224), dtype=torch.float32, device=self.device)
            with torch.inference_mode():
                _ = self.model(dummy)
