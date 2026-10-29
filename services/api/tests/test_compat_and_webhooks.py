import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_compat.db"

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from sv_api.database import Base, engine
from sv_api.main import app
from sv_api.webhook import (
    dispatch_webhook,
    dispatch_webhook_sync,
    sign_webhook_payload,
    verify_webhook_signature,
)
from sv_core.settings import settings


@pytest.fixture(autouse=True)
def setup_test_env():
    """Ensure clean SQLite test database for compat tests."""

    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_compat_endpoint_auth_missing_header(client):
    """Missing X-Internal-Key header must return 401 Unauthorized."""
    res = client.post(
        "/compat/moderate/video",
        json={"post_id": "p_auth_test_1", "video_url": "https://example.com/test.mp4"},
    )
    assert res.status_code == 401
    assert "Invalid or missing X-Internal-Key header" in res.json()["detail"]


def test_compat_endpoint_auth_invalid_header(client):
    """Invalid X-Internal-Key header must return 401 Unauthorized."""
    res = client.post(
        "/compat/moderate/video",
        json={"post_id": "p_auth_test_2", "video_url": "https://example.com/test.mp4"},
        headers={"X-Internal-Key": "completely_wrong_key_xyz"},
    )
    assert res.status_code == 401
    assert "Invalid or missing X-Internal-Key header" in res.json()["detail"]


def test_compat_endpoint_valid_submission(client):
    """Valid submission executes screening and returns fully populated CompatVideoResponse."""
    res = client.post(
        "/compat/moderate/video",
        json={"post_id": "p_valid_101", "video_url": "https://example.com/legit_video.mp4"},
        headers={"X-Internal-Key": settings.COMPAT_INTERNAL_KEY},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["post_id"] == "p_valid_101"
    assert data["status"] in ("allowed", "review", "held", "inconclusive")
    assert isinstance(data["labels"], list)
    assert isinstance(data["deepfake_confidence"], float)
    assert data["deepfake_model_version"].startswith("smsdt")
    assert data["analysis_id"].startswith("an_")
    assert data["receipt_id"].startswith("rcpt_")
    assert f"/cases/{data['analysis_id']}" in data["report_url"]
    assert isinstance(data["review_required"], bool)
    assert data["disclosed_ai_content"] is False


def test_compat_endpoint_timeout_pending_fallback(client):
    """When video screening takes longer than timeout or simulation is requested,

    endpoint returns status: pending.
    """
    res = client.post(
        "/compat/moderate/video",
        json={"post_id": "p_pending_202", "video_url": "simulate_timeout"},
        headers={"X-Internal-Key": settings.COMPAT_INTERNAL_KEY},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["post_id"] == "p_pending_202"
    assert data["status"] == "pending"
    assert data["deepfake_confidence"] == 0.0
    assert data["review_required"] is False
    assert data["receipt_id"] == ""
    assert data["analysis_id"].startswith("an_")


def test_webhook_signing_and_verification():
    """Verify HMAC-SHA256 signature generation and validation with timestamp."""
    secret = "test_webhook_secret_32bytes_long"
    payload_bytes = b'{"analysis_id":"an_test123","status":"review","deepfake_confidence":0.72}'
    now = int(time.time())

    sig_header = sign_webhook_payload(payload_bytes, secret, timestamp=now)
    assert sig_header.startswith(f"t={now},v1=")

    # Exact signature verification
    assert verify_webhook_signature(sig_header, payload_bytes, secret, current_time=now) is True

    # Tampered payload fails
    tampered_bytes = b'{"analysis_id":"an_test123","status":"allowed","deepfake_confidence":0.10}'
    assert verify_webhook_signature(sig_header, tampered_bytes, secret, current_time=now) is False

    # Wrong secret fails
    assert (
        verify_webhook_signature(sig_header, payload_bytes, "wrong_secret", current_time=now)
        is False
    )

    # Expired timestamp (301 seconds ago) fails
    old_ts = now - 350
    old_sig = sign_webhook_payload(payload_bytes, secret, timestamp=old_ts)
    assert (
        verify_webhook_signature(old_sig, payload_bytes, secret, tolerance_s=300, current_time=now)
        is False
    )

    # Malformed headers fail safely
    assert verify_webhook_signature("invalid_header", payload_bytes, secret) is False
    assert verify_webhook_signature("t=123", payload_bytes, secret) is False
    assert verify_webhook_signature("", payload_bytes, secret) is False
    assert verify_webhook_signature(sig_header, payload_bytes, "") is False


def test_dispatch_webhook_async_mock(monkeypatch):
    """Test async webhook dispatch with mock HTTP transport."""
    secret = "secret_key"
    payload = {"analysis_id": "an_mock_999", "status": "held"}
    received_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        sig = request.headers.get("X-SV-Signature")
        assert sig is not None
        assert verify_webhook_signature(sig, request.content, secret) is True
        return httpx.Response(200, json={"received": True})

    transport = httpx.MockTransport(mock_handler)
    orig_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: orig_async_client(transport=transport, **kwargs),
    )

    async def _test():
        return await dispatch_webhook("http://sentinel-platform:3000/webhook", payload, secret)

    success = asyncio.run(_test())
    assert success is True
    assert len(received_requests) == 1


def test_dispatch_webhook_sync_mock(monkeypatch):
    """Test sync webhook dispatch with mock HTTP transport."""
    secret = "secret_key"
    payload = {"analysis_id": "an_mock_888", "status": "allowed"}
    received_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        sig = request.headers.get("X-SV-Signature")
        assert sig is not None
        assert verify_webhook_signature(sig, request.content, secret) is True
        return httpx.Response(200, json={"received": True})

    transport = httpx.MockTransport(mock_handler)
    orig_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: orig_client(transport=transport, **kwargs),
    )

    success = dispatch_webhook_sync("http://sentinel-platform:3000/webhook", payload, secret)
    assert success is True
    assert len(received_requests) == 1


def test_dispatch_webhook_empty_url():
    """Empty URL returns False immediately without attempting connection."""
    assert dispatch_webhook_sync("", {"test": 1}, "secret") is False
