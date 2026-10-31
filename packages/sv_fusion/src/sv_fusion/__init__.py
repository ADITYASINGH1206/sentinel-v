"""SENTINEL-V Multi-Signal Fusion Package."""

from sv_fusion.c2pa import inspect_c2pa
from sv_fusion.fusion import fuse_signals_v1
from sv_fusion.swinv2 import SwinV2Detector, get_swinv2_detector

__all__ = ["inspect_c2pa", "fuse_signals_v1", "SwinV2Detector", "get_swinv2_detector"]
__version__ = "0.1.0"
