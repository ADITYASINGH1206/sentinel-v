from typing import Dict, Any, Optional
import copy
from sv_core.jcs import canonicalize_json
from sv_core.hashing import sha256_bytes
from sv_receipts.crypto import sign_bytes, verify_signature


def sign_receipt(receipt_dict: Dict[str, Any], private_key: Any) -> Dict[str, Any]:
    """Canonicalize receipt without signature, sign with Ed25519, and attach signature."""
    receipt = copy.deepcopy(receipt_dict)
    receipt.pop("signature", None)
    
    canonical_bytes = canonicalize_json(receipt)
    sig_b64 = sign_bytes(private_key, canonical_bytes)
    
    receipt["signature"] = {
        "alg": "Ed25519",
        "value": sig_b64
    }
    return receipt


def verify_receipt(receipt_dict: Dict[str, Any], public_key: Any) -> bool:
    """Verify Ed25519 signature over canonical JSON of receipt."""
    receipt = copy.deepcopy(receipt_dict)
    sig_info = receipt.pop("signature", None)
    if not sig_info or sig_info.get("alg") != "Ed25519":
        return False
    
    canonical_bytes = canonicalize_json(receipt)
    return verify_signature(public_key, canonical_bytes, sig_info["value"])
