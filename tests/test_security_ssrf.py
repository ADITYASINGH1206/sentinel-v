import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_ssrf.db"

import asyncio
import tempfile

import httpx
import pytest
from fastapi.testclient import TestClient
from sv_api.database import Base, engine
from sv_api.main import app
from sv_api.security import (
    SizeLimitExceededError,
    SSRFSecurityError,
    safe_download_file,
    validate_url_ssrf,
)


@pytest.fixture(autouse=True)
def setup_test_db():
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


def test_ssrf_rejects_loopback_and_local():
    """Verify SSRF validator blocks loopback, localhost, and 127.0.0.0/8 ranges."""
    with pytest.raises(SSRFSecurityError, match="Loopback|literal|Prohibited"):
        validate_url_ssrf("http://127.0.0.1:8080/test.mp4")

    with pytest.raises(SSRFSecurityError, match="metadata hostname|Loopback"):
        validate_url_ssrf("http://localhost:8080/test.mp4")

    with pytest.raises(SSRFSecurityError):
        validate_url_ssrf("http://127.0.0.2:9000/media")


def test_ssrf_rejects_rfc1918_private_ranges():
    """Verify SSRF validator blocks RFC 1918 private subnets (10/8, 172.16/12, 192.168/16)."""
    with pytest.raises(SSRFSecurityError, match="Private RFC 1918"):
        validate_url_ssrf("http://10.0.0.1/video.mp4")

    with pytest.raises(SSRFSecurityError, match="Private RFC 1918"):
        validate_url_ssrf("http://172.16.50.1/video.mp4")

    with pytest.raises(SSRFSecurityError, match="Private RFC 1918"):
        validate_url_ssrf("http://192.168.1.100/video.mp4")


def test_ssrf_rejects_cloud_metadata_services():
    """Verify SSRF validator blocks AWS, GCP, Azure, and Alibaba metadata endpoints."""
    # AWS / GCP / Azure 169.254.169.254
    with pytest.raises(SSRFSecurityError, match="Cloud metadata|Link-local"):
        validate_url_ssrf("http://169.254.169.254/latest/meta-data/")

    # Alibaba 100.100.100.200
    with pytest.raises(SSRFSecurityError, match="Cloud metadata"):
        validate_url_ssrf("http://100.100.100.200/latest/meta-data/")

    # GCP internal DNS
    with pytest.raises(SSRFSecurityError, match="Prohibited metadata hostname"):
        validate_url_ssrf("http://metadata.google.internal/computeMetadata/v1/")


def test_ssrf_rejects_ipv6_variants():
    """Verify SSRF validator blocks IPv6 loopback, link-local, and IPv4-mapped addresses."""
    # IPv6 loopback
    with pytest.raises(SSRFSecurityError, match="Loopback"):
        validate_url_ssrf("http://[::1]/video.mp4")

    # IPv6-mapped IPv4 loopback
    with pytest.raises(SSRFSecurityError, match="Loopback"):
        validate_url_ssrf("http://[::ffff:127.0.0.1]/video.mp4")

    # IPv6-mapped metadata
    with pytest.raises(SSRFSecurityError, match="Cloud metadata|Link-local"):
        validate_url_ssrf("http://[::ffff:169.254.169.254]/")


def test_ssrf_rejects_invalid_schemes():
    """Verify SSRF validator strictly prohibits file, ftp, gopher, and ldap schemes."""
    with pytest.raises(SSRFSecurityError, match="Unsupported scheme"):
        validate_url_ssrf("file:///etc/passwd")

    with pytest.raises(SSRFSecurityError, match="Unsupported scheme"):
        validate_url_ssrf("ftp://example.com/video.mp4")

    with pytest.raises(SSRFSecurityError, match="Unsupported scheme"):
        validate_url_ssrf("gopher://127.0.0.1/")


def test_ssrf_allows_public_urls():
    """Verify SSRF validator allows legitimate public domain names."""
    # Public DNS name
    resolved = validate_url_ssrf("https://example.com/video.mp4")
    assert len(resolved) > 0


def test_api_analyses_submission_ssrf_rejection(client):
    """Submitting an analysis with an SSRF target URL must return 400 Bad Request."""
    res = client.post(
        "/v1/analyses",
        json={"source_url": "http://169.254.169.254/metadata", "mode": "auto"},
    )
    assert res.status_code == 400
    assert "SSRF security violation" in res.json()["detail"]

    res_local = client.post(
        "/v1/analyses",
        json={"source_url": "http://127.0.0.1:5432/evil", "mode": "auto"},
    )
    assert res_local.status_code == 400
    assert "SSRF security violation" in res_local.json()["detail"]


def test_safe_download_size_limit_enforcement(monkeypatch):
    """Verify safe_download_file terminates with SizeLimitExceededError when payload exceeds max_bytes."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        dest_path = f.name

    def mock_handler(request: httpx.Request) -> httpx.Response:
        # 10 KB payload
        return httpx.Response(200, content=b"A" * 10240, headers={"Content-Length": "10240"})

    transport = httpx.MockTransport(mock_handler)
    orig_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: orig_client(transport=transport, **kwargs),
    )

    # Monkeypatch DNS to return public IP
    monkeypatch.setattr("sv_api.security.validate_url_ssrf", lambda url: ["93.184.216.34"])

    async def _run():
        # Limit max_bytes to 1024 bytes (1 KB)
        await safe_download_file(
            "https://example.com/huge.mp4",
            dest_path,
            max_bytes=1024,
        )

    with pytest.raises(SizeLimitExceededError):
        asyncio.run(_run())

    assert not os.path.exists(dest_path)
