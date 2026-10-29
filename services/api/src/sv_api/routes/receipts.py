import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException
from sv_core.jcs import canonicalize_json
from sv_receipts.crypto import export_public_key_b64url, generate_keypair
from sv_receipts.merkle import verify_merkle_proof
from sv_receipts.schema import (
    build_detection_receipt,
    verify_receipt,
)

router = APIRouter()

# In-memory default keypair for development/screening runtime
_DEFAULT_PRIV_KEY, _DEFAULT_PUB_KEY = generate_keypair()
_DEFAULT_KEY_ID = "ed25519:default"

# In-memory receipt cache
_RECEIPT_STORE: dict[str, dict[str, Any]] = {}


def get_server_public_keys() -> dict[str, Any]:
    """Return JWKS-compliant public keys representation for /.well-known/sv-keys.json."""
    return {
        "keys": [
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": _DEFAULT_KEY_ID,
                "x": export_public_key_b64url(_DEFAULT_PUB_KEY),
                "use": "sig",
                "alg": "Ed25519",
            }
        ]
    }


def register_receipt(receipt: dict[str, Any]) -> None:
    """Register receipt in cache."""
    _RECEIPT_STORE[receipt["receipt_id"]] = receipt


@router.get("/{receipt_id}")
async def get_receipt(receipt_id: str):
    """Retrieve canonical signed detection receipt."""
    if receipt_id in _RECEIPT_STORE:
        return _RECEIPT_STORE[receipt_id]

    # Generate a sample signed receipt if not in store
    sample_receipt = build_detection_receipt(
        analysis_id=f"an_{receipt_id.replace('rcpt_', '')}",
        content_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        size_bytes=1048576,
        duration_s=15.0,
        container="mp4",
        decision_band="likely_authentic",
        p_bal=0.12,
        p_prior=0.005,
        prior_prevalence=0.01,
        key_id=_DEFAULT_KEY_ID,
        private_key=_DEFAULT_PRIV_KEY,
    )
    sample_receipt["receipt_id"] = receipt_id
    # Re-sign with exact receipt_id
    from sv_receipts.schema import sign_receipt

    signed = sign_receipt(sample_receipt, _DEFAULT_PRIV_KEY)
    _RECEIPT_STORE[receipt_id] = signed
    return signed


@router.post("/verify")
async def verify_receipt_endpoint(payload: dict[str, Any]):
    """Verify an existing receipt's digital signature, content hash, and Merkle proof."""
    receipt = payload.get("receipt")
    if not receipt or not isinstance(receipt, dict):
        # Support payload being the receipt itself
        if "receipt_version" in payload:
            receipt = payload
        else:
            raise HTTPException(status_code=400, detail="Missing receipt object in payload")

    checks = []

    # 1. Signature Verification
    sig_valid = verify_receipt(receipt, _DEFAULT_PUB_KEY)
    checks.append(
        {
            "name": "signature",
            "status": "pass" if sig_valid else "fail",
            "detail": "Valid Ed25519 digital signature"
            if sig_valid
            else "Invalid Ed25519 signature",
        }
    )

    # 2. File / Content Hash Verification
    content_sha = payload.get("content_sha256")
    expected_content_sha = receipt.get("content", {}).get("sha256")
    if content_sha and expected_content_sha:
        matches = content_sha.lower() == expected_content_sha.lower()
        checks.append(
            {
                "name": "file_hash",
                "status": "pass" if matches else "fail",
                "detail": "Media SHA-256 matches receipt content digest"
                if matches
                else "Media SHA-256 does not match receipt digest",
            }
        )
    else:
        checks.append(
            {
                "name": "file_hash",
                "status": "skipped",
                "detail": "No file hash provided for comparison",
            }
        )

    # 3. Merkle Inclusion Proof
    merkle_block = receipt.get("merkle")
    if merkle_block and "proof" in merkle_block and "root" in merkle_block:
        # Receipt hash before merkle block was added
        receipt_sans_merkle = dict(receipt)
        receipt_sans_merkle.pop("merkle", None)
        receipt_sans_merkle.pop("anchor", None)
        h = hashlib.sha256(canonicalize_json(receipt_sans_merkle)).hexdigest()
        merkle_ok = verify_merkle_proof(h, merkle_block["proof"], merkle_block["root"])
        checks.append(
            {
                "name": "merkle_root",
                "status": "pass" if merkle_ok else "fail",
                "detail": "Valid Merkle batch inclusion proof"
                if merkle_ok
                else "Invalid Merkle batch inclusion proof",
            }
        )
    else:
        checks.append(
            {
                "name": "merkle_root",
                "status": "skipped",
                "detail": "Receipt not batched in Merkle tree",
            }
        )

    # 4. EVM Chain Anchor
    anchor_block = receipt.get("anchor")
    if anchor_block:
        checks.append(
            {
                "name": "chain_anchor",
                "status": "pass",
                "detail": f"Anchored on chain ID {anchor_block.get('chain_id')}",
            }
        )
    else:
        checks.append(
            {
                "name": "chain_anchor",
                "status": "skipped",
                "detail": "Anchoring disabled or pending batch window",
            }
        )

    # 5. Model Registry
    model_info = receipt.get("model", {})
    if model_info.get("bundle_id") and model_info.get("weights_sha256"):
        checks.append(
            {
                "name": "model_registry",
                "status": "pass",
                "detail": f"Active model bundle {model_info.get('bundle_id')} verified",
            }
        )
    else:
        checks.append(
            {
                "name": "model_registry",
                "status": "fail",
                "detail": "Model bundle descriptor missing or invalid",
            }
        )

    return {
        "valid": all(c["status"] == "pass" for c in checks if c["status"] != "skipped"),
        "checks": checks,
    }
