"""SENTINEL-V Receipts and Verification Package."""

from sv_receipts.crypto import (
    export_private_key_raw,
    export_public_key_b64url,
    export_public_key_raw,
    generate_keypair,
    load_private_key_raw,
    load_public_key_b64url,
    load_public_key_raw,
    sign_bytes,
    verify_signature,
)
from sv_receipts.merkle import (
    MerkleTree,
    create_merkle_batch,
    hash_internal,
    hash_leaf,
    verify_merkle_proof,
)
from sv_receipts.schema import (
    build_detection_receipt,
    build_review_receipt,
    compute_receipt_hash,
    sign_receipt,
    verify_content_hash,
    verify_receipt,
)

__version__ = "0.1.0"

__all__ = [
    "generate_keypair",
    "sign_bytes",
    "verify_signature",
    "export_public_key_raw",
    "export_public_key_b64url",
    "load_public_key_raw",
    "load_public_key_b64url",
    "export_private_key_raw",
    "load_private_key_raw",
    "MerkleTree",
    "hash_leaf",
    "hash_internal",
    "verify_merkle_proof",
    "create_merkle_batch",
    "sign_receipt",
    "verify_receipt",
    "compute_receipt_hash",
    "verify_content_hash",
    "build_detection_receipt",
    "build_review_receipt",
]
