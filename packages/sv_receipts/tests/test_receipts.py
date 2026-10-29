import hashlib

from sv_receipts.crypto import (
    export_private_key_raw,
    export_public_key_b64url,
    export_public_key_raw,
    generate_keypair,
    load_private_key_raw,
    load_public_key_b64url,
    load_public_key_raw,
)
from sv_receipts.schema import (
    build_detection_receipt,
    build_review_receipt,
    compute_receipt_hash,
    sign_receipt,
    verify_content_hash,
    verify_receipt,
)


def test_receipt_sign_and_verify():
    priv, pub = generate_keypair()

    receipt_data = {
        "receipt_version": "sv-receipt/1",
        "receipt_id": "rcpt_01JCX",
        "issued_at": "2026-10-28T21:00:00Z",
        "issuer": {
            "name": "SENTINEL-V",
            "key_id": "ed25519:test",
            "public_key_url": "/.well-known/sv-keys.json",
        },
        "content": {
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "size_bytes": 1024,
            "duration_s": 12.0,
            "container": "mp4",
        },
        "result": {"decision": "likely_authentic", "p_bal": 0.12, "p_prior": 0.001},
    }

    signed = sign_receipt(receipt_data, priv)
    assert "signature" in signed
    assert signed["signature"]["alg"] == "Ed25519"
    assert verify_receipt(signed, pub) is True


def test_tampering_fails_verification():
    priv, pub = generate_keypair()

    receipt = build_detection_receipt(
        analysis_id="an_test_123",
        content_sha256="abcd1234ef567890" * 4,
        size_bytes=50000,
        duration_s=15.5,
        container="mp4",
        decision_band="likely_authentic",
        p_bal=0.08,
        p_prior=0.002,
        prior_prevalence=0.01,
        private_key=priv,
    )

    assert verify_receipt(receipt, pub) is True

    # 1. Tamper result score
    tampered_score = dict(receipt)
    tampered_score["result"] = dict(receipt["result"])
    tampered_score["result"]["p_bal"] = 0.95
    assert verify_receipt(tampered_score, pub) is False

    # 2. Tamper decision band
    tampered_decision = dict(receipt)
    tampered_decision["result"] = dict(receipt["result"])
    tampered_decision["result"]["decision"] = "likely_manipulated"
    assert verify_receipt(tampered_decision, pub) is False

    # 3. Tamper content hash
    tampered_content = dict(receipt)
    tampered_content["content"] = dict(receipt["content"])
    tampered_content["content"]["sha256"] = "0" * 64
    assert verify_receipt(tampered_content, pub) is False

    # 4. Tamper signature bytes
    tampered_sig = dict(receipt)
    tampered_sig["signature"] = dict(receipt["signature"])
    tampered_sig["signature"]["value"] = "invalid_sig_value"
    assert verify_receipt(tampered_sig, pub) is False


def test_media_content_hash_tampering():
    original_video_data = b"synthetic video frame test bytes header payload"
    expected_sha256 = hashlib.sha256(original_video_data).hexdigest()

    priv, pub = generate_keypair()
    receipt = build_detection_receipt(
        analysis_id="an_media_test",
        content_sha256=expected_sha256,
        size_bytes=len(original_video_data),
        duration_s=2.5,
        container="mp4",
        decision_band="needs_review",
        p_bal=0.45,
        p_prior=0.02,
        prior_prevalence=0.01,
        private_key=priv,
    )

    assert verify_content_hash(receipt, original_video_data) is True

    # Altering exactly 1 byte in the media file
    corrupted_data = bytearray(original_video_data)
    corrupted_data[5] = corrupted_data[5] ^ 0xFF
    assert verify_content_hash(receipt, bytes(corrupted_data)) is False


def test_append_only_review_receipt():
    priv, pub = generate_keypair()

    original_receipt = build_detection_receipt(
        analysis_id="an_review_case",
        content_sha256="1234567890abcdef" * 4,
        size_bytes=10240,
        duration_s=8.0,
        container="mp4",
        decision_band="needs_review",
        p_bal=0.52,
        p_prior=0.03,
        prior_prevalence=0.01,
        private_key=priv,
    )
    assert verify_receipt(original_receipt, pub) is True
    assert "supersedes" not in original_receipt

    # Human reviewer reviews and determines manipulated
    review_receipt = build_review_receipt(
        original_receipt=original_receipt,
        reviewer_id="usr_reviewer_aditya",
        human_decision="likely_manipulated",
        reason_codes=["facial_texture_boundary", "lighting_mismatch"],
        notes="Temporal flicker observed around lip region.",
        private_key=priv,
    )

    # Review receipt is independently verifiable
    assert verify_receipt(review_receipt, pub) is True
    assert review_receipt["receipt_id"] != original_receipt["receipt_id"]
    assert review_receipt["supersedes"] == original_receipt["receipt_id"]
    assert review_receipt["result"]["decision"] == "likely_manipulated"
    assert review_receipt["human_review"]["reviewer_id"] == "usr_reviewer_aditya"
    assert "facial_texture_boundary" in review_receipt["human_review"]["reason_codes"]


def test_crypto_key_serialization_roundtrip():
    priv, pub = generate_keypair()

    # Public key raw and base64url export/load
    pub_raw = export_public_key_raw(pub)
    assert len(pub_raw) == 32
    pub_loaded_raw = load_public_key_raw(pub_raw)
    assert export_public_key_raw(pub_loaded_raw) == pub_raw

    pub_b64 = export_public_key_b64url(pub)
    pub_loaded_b64 = load_public_key_b64url(pub_b64)
    assert export_public_key_raw(pub_loaded_b64) == pub_raw

    # Private key raw export/load
    priv_raw = export_private_key_raw(priv)
    assert len(priv_raw) == 32
    priv_loaded = load_private_key_raw(priv_raw)

    # Signing with loaded private key and verifying with loaded public key
    msg = b"message to test roundtrip key serialization"
    sig = sign_receipt({"msg": msg.decode()}, priv_loaded)["signature"]["value"]
    receipt_to_verify = {"msg": msg.decode(), "signature": {"alg": "Ed25519", "value": sig}}
    assert verify_receipt(receipt_to_verify, pub_loaded_b64) is True


def test_compute_receipt_hash():
    priv, _ = generate_keypair()
    receipt = build_detection_receipt(
        analysis_id="an_hash_test",
        content_sha256="abcd" * 16,
        size_bytes=100,
        duration_s=1.0,
        container="mp4",
        decision_band="likely_authentic",
        p_bal=0.1,
        p_prior=0.01,
        prior_prevalence=0.01,
        private_key=priv,
    )
    h = compute_receipt_hash(receipt)
    assert len(h) == 64
    assert int(h, 16) > 0
