import copy
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sv_core.jcs import canonicalize_json

from sv_receipts.crypto import sign_bytes, verify_signature


def sign_receipt(receipt_dict: dict[str, Any], private_key: Any) -> dict[str, Any]:
    """Canonicalize receipt without signature, sign with Ed25519, and attach signature."""
    receipt = copy.deepcopy(receipt_dict)
    receipt.pop("signature", None)

    canonical_bytes = canonicalize_json(receipt)
    sig_b64 = sign_bytes(private_key, canonical_bytes)

    receipt["signature"] = {"alg": "Ed25519", "value": sig_b64}
    return receipt


def verify_receipt(receipt_dict: dict[str, Any], public_key: Any) -> bool:
    """Verify Ed25519 signature over canonical JSON of receipt."""
    receipt = copy.deepcopy(receipt_dict)
    sig_info = receipt.pop("signature", None)
    if not sig_info or sig_info.get("alg") != "Ed25519":
        return False

    canonical_bytes = canonicalize_json(receipt)
    return verify_signature(public_key, canonical_bytes, sig_info["value"])


def compute_receipt_hash(receipt_dict: dict[str, Any]) -> str:
    """Compute SHA-256 of canonical JSON representation of receipt."""
    canonical_bytes = canonicalize_json(receipt_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()


def verify_content_hash(receipt_dict: dict[str, Any], content_bytes: bytes) -> bool:
    """Verify that media content bytes match the content sha256 declared in receipt."""
    content_info = receipt_dict.get("content", {})
    expected_hash = content_info.get("sha256")
    if not expected_hash:
        return False
    actual_hash = hashlib.sha256(content_bytes).hexdigest()
    return actual_hash.lower() == expected_hash.lower()


def build_detection_receipt(
    *,
    analysis_id: str,
    content_sha256: str,
    size_bytes: int,
    duration_s: float,
    container: str,
    decision_band: str,
    p_bal: float,
    p_prior: float,
    prior_prevalence: float,
    tau: float = 0.50,
    model_bundle_id: str = "smsdt_st_v1",
    model_weights_sha256: str = "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    policy_id: str = "standard_screening_v1",
    policy_version: str = "1.0.0",
    key_id: str = "ed25519:default",
    private_key: Any = None,
    tracks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct and sign a canonical detection receipt conforming to SPEC §10."""
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    receipt: dict[str, Any] = {
        "receipt_version": "sv-receipt/1",
        "receipt_id": receipt_id,
        "analysis_id": analysis_id,
        "issued_at": now_iso,
        "issuer": {
            "name": "SENTINEL-V",
            "key_id": key_id,
            "public_key_url": "/.well-known/sv-keys.json",
        },
        "content": {
            "sha256": content_sha256,
            "size_bytes": size_bytes,
            "duration_s": round(duration_s, 2),
            "container": container,
        },
        "model": {
            "bundle_id": model_bundle_id,
            "weights_sha256": model_weights_sha256,
            "variant": "st",
        },
        "policy": {
            "policy_id": policy_id,
            "policy_version": policy_version,
            "tau": round(tau, 3),
            "prior_prevalence": round(prior_prevalence, 4),
        },
        "result": {
            "decision": decision_band,
            "p_bal": round(p_bal, 4),
            "p_prior": round(p_prior, 4),
        },
        "tracks": tracks or [],
    }

    if private_key is not None:
        return sign_receipt(receipt, private_key)
    return receipt


def build_review_receipt(
    *,
    original_receipt: dict[str, Any],
    reviewer_id: str,
    human_decision: str,
    reason_codes: list[str],
    notes: str = "",
    key_id: str = "ed25519:default",
    private_key: Any = None,
) -> dict[str, Any]:
    """Construct and sign an append-only human review receipt superseding an earlier receipt."""
    review_receipt_id = f"rcpt_rev_{uuid.uuid4().hex[:16]}"
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_receipt: dict[str, Any] = copy.deepcopy(original_receipt)
    new_receipt.pop("signature", None)
    new_receipt.pop("merkle", None)
    new_receipt.pop("anchor", None)

    new_receipt["receipt_id"] = review_receipt_id
    new_receipt["issued_at"] = now_iso
    new_receipt["supersedes"] = original_receipt["receipt_id"]
    new_receipt["issuer"]["key_id"] = key_id

    new_receipt["human_review"] = {
        "reviewer_id": reviewer_id,
        "decision": human_decision,
        "reason_codes": reason_codes,
        "notes": notes,
        "reviewed_at": now_iso,
    }

    # Result decision is updated to the human verified conclusion
    new_receipt["result"]["decision"] = human_decision

    if private_key is not None:
        return sign_receipt(new_receipt, private_key)
    return new_receipt
