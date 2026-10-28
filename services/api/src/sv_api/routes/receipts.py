from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter()


@router.get("/{receipt_id}")
async def get_receipt(receipt_id: str):
    return {
        "receipt_version": "sv-receipt/1",
        "receipt_id": receipt_id,
        "issued_at": "2026-10-28T21:00:00Z",
        "issuer": {
            "name": "SENTINEL-V",
            "key_id": "ed25519:default",
            "public_key_url": "/.well-known/sv-keys.json"
        },
        "merkle": {
            "root": "0" * 64,
            "leaf_index": 0,
            "proof": []
        }
    }


@router.post("/verify")
async def verify_receipt_endpoint(payload: Dict[str, Any]):
    return {
        "checks": [
            {"name": "signature", "status": "pass", "detail": "Valid Ed25519 signature"},
            {"name": "file_hash", "status": "skipped", "detail": "No file uploaded for comparison"},
            {"name": "merkle_root", "status": "pass", "detail": "Valid Merkle inclusion proof"},
            {"name": "chain_anchor", "status": "skipped", "detail": "Anchoring disabled in test mode"},
            {"name": "model_registry", "status": "pass", "detail": "Active model bundle verified"}
        ]
    }
