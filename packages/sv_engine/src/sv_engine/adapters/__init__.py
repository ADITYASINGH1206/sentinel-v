from typing import Any, Optional

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter, Variant
from sv_engine.adapters.clip_s import ClipSAdapter
from sv_engine.adapters.clip_st import ClipSTAdapter
from sv_engine.adapters.cnn_p1 import CnnP1Adapter
from sv_engine.adapters.full_c import FullCAdapter
from sv_engine.adapters.mock import MockDetectorAdapter
from sv_engine.adapters.utils import (
    clean_state_dict_keys,
    load_state_dict_strict,
    load_weights_dict,
    verify_bundle_checksums,
)


def get_adapter(variant: str, model_id: Optional[str] = None, **kwargs: Any) -> DetectorAdapter:
    """Factory for instantiating model detector adapters by variant."""
    v = variant.lower().strip()
    if v in ("st", "smsdt-st-b", "smsdt_st"):
        return ClipSTAdapter(model_id=model_id or "smsdt-st-b", **kwargs)
    elif v in ("s", "smsdt-s-a", "smsdt_s"):
        return ClipSAdapter(model_id=model_id or "smsdt-s-a", **kwargs)
    elif v in ("cnn", "smsdt-cnn-p1", "cnn_p1"):
        return CnnP1Adapter(model_id=model_id or "smsdt-cnn-p1", **kwargs)
    elif v in ("full", "smsdt-full-c", "stage_c"):
        return FullCAdapter(model_id=model_id or "smsdt-full-c", **kwargs)
    elif v in ("mock", "mock-st", "mock-s"):
        return MockDetectorAdapter(model_id=model_id or f"mock-{v}", variant=v if v in ("st", "s", "cnn", "full") else "st")
    else:
        raise ValueError(f"Unknown detector adapter variant: {variant}")


__all__ = [
    "ClipBatch",
    "ClipOutput",
    "DetectorAdapter",
    "Variant",
    "MockDetectorAdapter",
    "ClipSTAdapter",
    "ClipSAdapter",
    "CnnP1Adapter",
    "FullCAdapter",
    "get_adapter",
    "load_state_dict_strict",
    "load_weights_dict",
    "verify_bundle_checksums",
    "clean_state_dict_keys",
]

