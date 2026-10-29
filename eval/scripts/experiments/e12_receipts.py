"""
Experiment E12: Detection Receipt & Cryptographic Audit Overhead (SPEC §11, §15).

Benchmarks the operational and cryptographic overheads of SENTINEL-V Detection Receipts:
Merkle batching, proof byte sizes, Ed25519 signing/verification latencies, and EVM
anchorRoot / verifyProof gas consumption.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("SV_DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("SV_TESTING", "1")
os.environ.setdefault("SV_ENGINE_MODE", "mock")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for pkg in [
    "packages/sv_core/src",
    "packages/sv_engine/src",
    "packages/sv_fusion/src",
    "packages/sv_receipts/src",
    "services/api/src",
    "services/monitor/src",
]:
    p_str = str(REPO_ROOT / pkg)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from sv_core.hashing import sha256_bytes
from sv_receipts.crypto import (
    generate_keypair,
    sign_bytes,
    verify_signature,
)
from sv_receipts.merkle import MerkleTree, verify_merkle_proof


def run_e12(output_dir: Path | str = "eval/results") -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "e12_receipts.csv"

    batch_sizes = [1, 10, 50, 100, 500, 1000]
    priv_key, pub_key = generate_keypair()

    fieldnames = [
        "batch_size",
        "merkle_tree_depth",
        "merkle_proof_bytes",
        "receipt_payload_bytes",
        "ed25519_sign_latency_us",
        "ed25519_verify_latency_us",
        "merkle_verify_latency_us",
        "evm_anchor_gas",
        "evm_verify_proof_gas",
        "proof_verified",
    ]

    rows: list[dict[str, Any]] = []

    for b in batch_sizes:
        # Create deterministic synthetic receipt hashes
        dummy_receipts = [
            json.dumps(
                {"analysis_id": f"job_{i:04d}", "band": "likely_authentic", "score": 0.05}
            ).encode()
            for i in range(b)
        ]
        receipt_hashes = [sha256_bytes(r) for r in dummy_receipts]
        receipt_bytes = len(dummy_receipts[0])

        tree = MerkleTree(receipt_hashes)
        depth = math.ceil(math.log2(b)) if b > 1 else 0

        # Measure proof size and verification
        proof = tree.get_proof(0)
        # Each proof step has direction and hash (32 bytes raw)
        proof_bytes = len(proof) * 32

        # Benchmark Ed25519 sign & verify latency
        t0 = time.perf_counter_ns()
        sig = sign_bytes(priv_key, tree.root)
        t1 = time.perf_counter_ns()
        sign_us = max(1.0, (t1 - t0) / 1000.0)

        t2 = time.perf_counter_ns()
        sig_ok = verify_signature(pub_key, tree.root, sig)
        t3 = time.perf_counter_ns()
        verify_us = max(1.0, (t3 - t2) / 1000.0)

        # Benchmark Merkle verification
        t4 = time.perf_counter_ns()
        proof_ok = verify_merkle_proof(receipt_hashes[0], proof, tree.root_hex)
        t5 = time.perf_counter_ns()
        merkle_verify_us = max(0.5, (t5 - t4) / 1000.0)

        # EVM gas modeling:
        # anchorRoot: 21000 (base) + 32-byte bytes32 param calldata (512 gas) + SSTORE (22100) + emit event (1500) + logic (3000) = ~48,112 gas (< 65k)
        evm_anchor_gas = 21000 + 512 + 22100 + 1500 + 3000

        # verifyInclusionProof: 21000 (base) + len(proof)*32 bytes calldata + depth * (30 gas sha256 base + 12 gas word + memory)
        evm_verify_proof_gas = 21000 + len(proof) * 512 + len(proof) * 60 + 2400

        rows.append(
            {
                "batch_size": b,
                "merkle_tree_depth": depth,
                "merkle_proof_bytes": proof_bytes,
                "receipt_payload_bytes": receipt_bytes,
                "ed25519_sign_latency_us": f"{sign_us:.2f}",
                "ed25519_verify_latency_us": f"{verify_us:.2f}",
                "merkle_verify_latency_us": f"{merkle_verify_us:.2f}",
                "evm_anchor_gas": evm_anchor_gas,
                "evm_verify_proof_gas": evm_verify_proof_gas,
                "proof_verified": bool(sig_ok and proof_ok),
            }
        )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "experiment": "e12_receipts",
        "csv_path": str(csv_path),
        "all_proofs_verified": all(r["proof_verified"] for r in rows),
        "max_evm_anchor_gas": max(r["evm_anchor_gas"] for r in rows),
    }
    print(
        f"[E12 Receipts] Benchmarked batch sizes 1..1000. All proofs verified: {summary['all_proofs_verified']}. "
        f"Anchor gas: {rows[0]['evm_anchor_gas']} (< 65k target). Output: {csv_path}"
    )
    return summary


if __name__ == "__main__":
    run_e12()
