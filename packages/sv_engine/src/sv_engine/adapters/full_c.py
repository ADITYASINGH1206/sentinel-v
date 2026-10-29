from typing import Any, Optional
import torch

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter, Variant


class FullCAdapter:
    """Stage C Model Adapter: S-MSDT-Full (v3 with SRM+Haar ResidualStream and EvidenceReadoutV3).
    
    Guarded under Blocker B1 (SPEC §17): upstream v3 modules are not present in verified commit.
    """

    def __init__(self, model_id: str = "smsdt-full-c", device: Optional[Any] = None):
        self.model_id = model_id
        self.variant: Variant = "full"
        self.T: int = 8
        self.grid: int = 16
        self.device = torch.device("cpu")

    def normalize(self, frames_u8: Any) -> Any:
        raise NotImplementedError(
            "S-MSDT Stage C (v3) modules are blocked under Blocker B1 (SPEC §17). "
            "Use Stage B (ST) as active decider."
        )

    def load(self, bundle_dir: str, device: Optional[Any] = None) -> None:
        raise NotImplementedError(
            "S-MSDT Stage C (v3) modules are blocked under Blocker B1 (SPEC §17). "
            "Use Stage B (ST) as active decider."
        )

    def predict(self, batch: ClipBatch) -> ClipOutput:
        raise NotImplementedError(
            "S-MSDT Stage C (v3) modules are blocked under Blocker B1 (SPEC §17). "
            "Use Stage B (ST) as active decider."
        )

    def warmup(self) -> None:
        pass

