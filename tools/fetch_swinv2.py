#!/usr/bin/env python3
"""Download and verify local weights for the SwinV2 AI Image Detector (haywoodsloan/ai-image-detector-deploy)."""

import hashlib
import json
import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "haywoodsloan/ai-image-detector-deploy"
TARGET_DIR = Path("models/aux/swinv2_ai_image")
FILES = ["config.json", "preprocessor_config.json", "model.safetensors"]


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading SwinV2 model files from '{REPO_ID}' to '{TARGET_DIR}'...")

    checksums = {}
    for filename in FILES:
        target_path = TARGET_DIR / filename
        if target_path.exists() and target_path.stat().st_size > 0:
            print(f"  [Found] {filename} ({target_path.stat().st_size / (1024 * 1024):.2f} MB)")
        else:
            print(f"  [Downloading] {filename}...")
            downloaded = hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                local_dir=TARGET_DIR,
                local_dir_use_symlinks=False,
            )
            print(f"  [Saved] {downloaded}")

        checksums[filename] = compute_sha256(target_path)

    # Write checksums.sha256
    checksums_file = TARGET_DIR / "checksums.sha256"
    with open(checksums_file, "w", encoding="utf-8") as f:
        for fname, digest in sorted(checksums.items()):
            f.write(f"{digest}  {fname}\n")
    print(f"Wrote checksums to {checksums_file}")

    # Write manifest.json
    manifest = {
        "id": "swinv2-haywoodsloan-ai-image-detector",
        "upstream_repo": REPO_ID,
        "architecture": "Swinv2ForImageClassification",
        "input_size": [256, 256],
        "id2label": {"0": "artificial", "1": "real"},
        "threshold": 0.65,
        "files": {
            fname: {"sha256": digest, "size_bytes": (TARGET_DIR / fname).stat().st_size}
            for fname, digest in checksums.items()
        },
    }
    manifest_file = TARGET_DIR / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest to {manifest_file}")
    print("SwinV2 local model bundle successfully initialized!")


if __name__ == "__main__":
    main()

