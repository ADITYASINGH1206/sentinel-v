from sv_receipts.crypto import generate_keypair
from sv_receipts.schema import sign_receipt, verify_receipt


def test_receipt_sign_and_verify():
    priv, pub = generate_keypair()
    
    receipt_data = {
        "receipt_version": "sv-receipt/1",
        "receipt_id": "rcpt_01JCX",
        "issued_at": "2026-10-28T21:00:00Z",
        "issuer": {
            "name": "SENTINEL-V",
            "key_id": "ed25519:test",
            "public_key_url": "/.well-known/sv-keys.json"
        },
        "content": {
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "size_bytes": 1024,
            "duration_s": 12.0,
            "container": "mp4"
        },
        "result": {
            "decision": "likely_authentic",
            "p_bal": 0.12,
            "p_prior": 0.001
        }
    }
    
    signed = sign_receipt(receipt_data, priv)
    assert "signature" in signed
    assert signed["signature"]["alg"] == "Ed25519"
    
    assert verify_receipt(signed, pub) is True
    
    # Tampering test
    tampered = dict(signed)
    tampered["result"] = {"decision": "likely_manipulated", "p_bal": 0.99}
    assert verify_receipt(tampered, pub) is False

