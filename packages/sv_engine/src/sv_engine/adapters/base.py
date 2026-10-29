from dataclasses import dataclass
from typing import Any, Literal, Protocol

Variant = Literal["cnn", "s", "st", "full"]


@dataclass(frozen=True)
class ClipBatch:
    frames_u8: Any  # (N, T, 224, 224, 3) uint8, RGB, center-cropped
    landmarks106: Any | None  # (N, T, 106, 2) float32 in 224-crop coords (Full only)
    conf: Any  # (N, T) float32 detector confidence


@dataclass(frozen=True)
class ClipOutput:
    logits: Any  # (N,) float32
    patch_logits: Any | None  # (N, T, P) float32, P = grid*grid
    grid: int  # 16 for CLIP variants, 14 for CNN


class DetectorAdapter(Protocol):
    model_id: str
    variant: Variant
    T: int
    grid: int

    def load(self, bundle_dir: str, device: Any) -> None: ...
    def normalize(self, frames_u8: Any) -> Any: ...  # -> (N,T,3,224,224) float
    def predict(self, batch: ClipBatch) -> ClipOutput: ...
    def warmup(self) -> None: ...
