import hashlib
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple
import torch
from safetensors.torch import load_file as load_safetensors


def ensure_smsdt_in_path() -> None:
    """Ensure third_party/smsdt is in sys.path without modifying upstream code."""
    curr = Path(__file__).resolve()
    for parent in [curr] + list(curr.parents):
        candidate = parent / "third_party" / "smsdt"
        if candidate.is_dir() and (candidate / "smsdt").is_dir():
            cand_str = str(candidate)
            if cand_str not in sys.path:
                sys.path.insert(0, cand_str)
            return


def clean_state_dict_keys(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Strip common wrapper prefixes ('module.', '_orig_mod.') from state dict keys."""
    cleaned = {}
    for k, v in state_dict.items():
        new_k = k
        if new_k.startswith("module."):
            new_k = new_k[7:]
        if new_k.startswith("_orig_mod."):
            new_k = new_k[10:]
        cleaned[new_k] = v
    return cleaned


def load_weights_dict(bundle_dir_or_file: str, device: torch.device = torch.device("cpu")) -> Dict[str, Any]:
    """Load weights dictionary from either .safetensors or .pt checkpoint."""
    if os.path.isdir(bundle_dir_or_file):
        st_path = os.path.join(bundle_dir_or_file, "weights.safetensors")
        pt_path = os.path.join(bundle_dir_or_file, "weights.pt")
        if os.path.exists(st_path):
            path = st_path
        elif os.path.exists(pt_path):
            path = pt_path
        else:
            raise FileNotFoundError(f"Neither weights.safetensors nor weights.pt found in {bundle_dir_or_file}")
    else:
        path = bundle_dir_or_file

    if path.endswith(".safetensors"):
        return load_safetensors(path, device=str(device))
    else:
        try:
            ckpt = torch.load(path, map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(path, map_location=device)

        if isinstance(ckpt, dict):
            for key in ["ema_state_dict", "model_state_dict", "model_ema", "model", "state_dict"]:
                if key in ckpt and isinstance(ckpt[key], dict):
                    return ckpt[key]
        return ckpt


def load_state_dict_strict(model: torch.nn.Module, state_dict: Dict[str, Any]) -> None:
    """Strictly load state dict into model; assert missing_keys == [] and unexpected_keys == []."""
    cleaned = clean_state_dict_keys(state_dict)
    missing_keys, unexpected_keys = model.load_state_dict(cleaned, strict=False)
    if missing_keys or unexpected_keys:
        raise RuntimeError(
            f"Strict weight loading failed:\n"
            f"  Missing keys ({len(missing_keys)}): {missing_keys[:5]}...\n"
            f"  Unexpected keys ({len(unexpected_keys)}): {unexpected_keys[:5]}..."
        )


def verify_bundle_checksums(bundle_dir: str) -> bool:
    """Verify all bundle assets against checksums.sha256; raise ValueError on mismatch."""
    checksums_path = os.path.join(bundle_dir, "checksums.sha256")
    if not os.path.exists(checksums_path):
        raise FileNotFoundError(f"Missing checksums.sha256 in bundle directory {bundle_dir}")

    with open(checksums_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        expected_hash = parts[0]
        filename = parts[1].lstrip("*")
        file_path = os.path.join(bundle_dir, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Bundle asset '{filename}' listed in checksums.sha256 not found on disk")

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f_asset:
            while chunk := f_asset.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()

        if actual_hash != expected_hash:
            raise ValueError(
                f"Bundle checksum verification failed for {filename}!\n"
                f"  Expected: {expected_hash}\n"
                f"  Actual:   {actual_hash}"
            )

    return True

