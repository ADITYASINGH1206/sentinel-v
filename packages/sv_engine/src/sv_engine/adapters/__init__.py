from typing import Any

from sv_engine.adapters.base import ClipBatch, ClipOutput, DetectorAdapter, Variant
from sv_engine.adapters.clip_s import ClipSAdapter
from sv_engine.adapters.clip_st import ClipSTAdapter
from sv_engine.adapters.cnn_p1 import CnnP1Adapter
from sv_engine.adapters.full_c import FullCAdapter
from sv_engine.adapters.mock import MockDetectorAdapter
from sv_engine.adapters.utils import (
    clean_state_dict_keys,
    ensure_smsdt_in_path,
    load_state_dict_strict,
    load_weights_dict,
    verify_bundle_checksums,
)


def get_adapter(variant: str, model_id: str | None = None, **kwargs: Any) -> DetectorAdapter:
    """Factory for instantiating model detector adapters by variant."""
    v = variant.lower().strip()
    if v in ["mock", "dummy"]:
        return MockDetectorAdapter(model_id=model_id or "mock", variant="st", **kwargs)
    elif v in ["st", "clip_st", "b"]:
        return ClipSTAdapter(model_id=model_id or "clip-st", **kwargs)
    elif v in ["s", "clip_s", "a"]:
        return ClipSAdapter(model_id=model_id or "clip-s", **kwargs)
    elif v in ["cnn", "p1", "cnn_p1"]:
        return CnnP1Adapter(model_id=model_id or "cnn-p1", **kwargs)
    elif v in ["full", "c", "full_c"]:
        return FullCAdapter(model_id=model_id or "full-c", **kwargs)
    else:
        raise ValueError(
            f"Unknown adapter variant: {variant}. Expected one of: 'st', 's', 'cnn_p1', 'full_c', 'mock'"
        )


__all__ = [
    "Variant",
    "DetectorAdapter",
    "ClipBatch",
    "ClipOutput",
    "MockDetectorAdapter",
    "ClipSTAdapter",
    "ClipSAdapter",
    "CnnP1Adapter",
    "FullCAdapter",
    "get_adapter",
    "load_weights_dict",
    "clean_state_dict_keys",
    "load_state_dict_strict",
    "verify_bundle_checksums",
    "ensure_smsdt_in_path",
]
