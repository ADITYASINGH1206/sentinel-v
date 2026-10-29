from fastapi.testclient import TestClient
from sv_api.main import app

client = TestClient(app)


def test_well_known_keys_endpoint():
    resp = client.get("/.well-known/sv-keys.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    key = data["keys"][0]
    assert key["kty"] == "OKP"
    assert key["crv"] == "Ed25519"
    assert "x" in key


def test_receipts_get_and_verify_endpoint():
    # 1. Fetch receipt
    resp = client.get("/v1/receipts/rcpt_test_999")
    assert resp.status_code == 200
    receipt = resp.json()
    assert receipt["receipt_id"] == "rcpt_test_999"
    assert "signature" in receipt
    assert receipt["signature"]["alg"] == "Ed25519"

    # 2. Verify receipt
    verify_resp = client.post("/v1/receipts/verify", json={"receipt": receipt})
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["valid"] is True
    checks = {c["name"]: c["status"] for c in verify_data["checks"]}
    assert checks["signature"] == "pass"

    # 3. Tamper receipt score and verify it fails
    tampered = dict(receipt)
    tampered["result"] = dict(receipt["result"])
    tampered["result"]["p_bal"] = 0.99
    bad_verify = client.post("/v1/receipts/verify", json={"receipt": tampered})
    assert bad_verify.status_code == 200
    bad_data = bad_verify.json()
    assert bad_data["valid"] is False
    bad_checks = {c["name"]: c["status"] for c in bad_data["checks"]}
    assert bad_checks["signature"] == "fail"


def test_submit_review_creates_superseding_receipt():
    review_payload = {
        "decision": "manipulated",
        "reasons": ["boundary_warping"],
        "confidence": 4,
        "notes": "Verified patch boundary warping artifacts.",
    }
    resp = client.post("/v1/reviews/an_case_for_review", json=review_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert "receipt_id" in data
    assert "supersedes" in data
    assert data["supersedes"] == "rcpt_case_for_review"
    assert data["receipt"]["human_review"]["decision"] == "manipulated"
