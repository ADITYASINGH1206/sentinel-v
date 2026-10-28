import hashlib
import numpy as np
from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter, Variant


class MockDetectorAdapter(DetectorAdapter):
    """Deterministic Mock Adapter for CI, CPU development, and frontend testing."""

    def __init__(self, model_id: str = "mock-detector", variant: Variant = "st", T: int = 8, grid: int = 16):
        self.model_id = model_id
        self.variant = variant
        self.T = T
        self.grid = grid

    def load(self, bundle_dir: str, device: str = "cpu") -> None:
        pass

    def normalize(self, frames_u8: np.ndarray) -> np.ndarray:
        return frames_u8.astype(np.float32) / 255.0

    def predict(self, batch: ClipBatch) -> ClipOutput:
        # Compute deterministic logits from frame bytes hash
        N = getattr(batch.frames_u8, "shape", [1])[0]
        logits = []
        for i in range(N):
            raw_bytes = bytes(batch.frames_u8[i].tobytes() if hasattr(batch.frames_u8[i], "tobytes") else b"mock_frame_data")
            digest = hashlib.sha256(raw_bytes).digest()
            # Map integer to logit centered around 0 in [-3.0, 3.0]
            val = int.from_bytes(digest[:4], "big") / (2**32 - 1)
            logit = (val - 0.5) * 6.0
            logits.append(logit)

        logits_arr = np.array(logits, dtype=np.float32)
        
        # Synthetic Gaussian patch logits
        P = self.grid * self.grid
        patch_logits = np.zeros((N, self.T, P), dtype=np.float32)
        # Create a centered hot spot in the grid
        center = self.grid // 2
        for g_y in range(self.grid):
            for g_x in range(self.grid):
                dist = (g_x - center)**2 + (g_y - center)**2
                val = np.exp(-dist / 8.0) * 2.0
                patch_logits[:, :, g_y * self.grid + g_x] = val

        return ClipOutput(
            logits=logits_arr,
            patch_logits=patch_logits,
            grid=self.grid
        )

    def warmup(self) -> None:
        pass

