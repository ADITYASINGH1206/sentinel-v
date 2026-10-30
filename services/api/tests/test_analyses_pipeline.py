import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"

import asyncio
import tempfile

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sv_api.auth import (
    create_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    record_audit_log,
    verify_password,
)
from sv_api.database import Base, async_session_maker, engine, init_db
from sv_api.main import app
from sv_api.models import AuditLog


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def setup_test_env():
    """Configure environment for SQLite and reset tables before each test."""
    os.environ["SV_TESTING"] = "1"
    os.environ["SV_ENGINE_MODE"] = "mock"
    os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"

    async def _reset_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset_tables())
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_video_bytes():
    """Generate in-memory 16-frame MP4 video."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    width, height = 320, 240
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 24.0, (width, height))
    for i in range(16):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (100, 60), (160, 140), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()

    with open(path, "rb") as f:
        content = f.read()

    os.remove(path)
    return content


def test_auth_utilities():
    # 1. Argon2id password hashing
    password = "StrongPassword123!"
    hashed = hash_password(password)
    assert verify_password(hashed, password) is True
    assert verify_password(hashed, "WrongPassword") is False

    # 2. JWT Access Token
    token = create_access_token({"sub": "usr_test123", "role": "admin"})
    assert isinstance(token, str)
    assert len(token) > 20

    # 3. Live API Key
    api_key = generate_api_key()
    assert api_key.startswith("sv_live_")
    hashed_key = hash_api_key(api_key)
    assert len(hashed_key) == 64


def test_audit_logging():
    import asyncio

    async def _run():
        await init_db()
        async with async_session_maker() as session:
            await record_audit_log(
                db=session,
                action="policy.update",
                resource_type="policy",
                resource_id="pol_strict_v3",
                user_id="usr_admin",
                details={"changed": "threshold"},
            )

            stmt = select(AuditLog).where(AuditLog.action == "policy.update")
            res = await session.execute(stmt)
            entry = res.scalars().first()
            assert entry is not None
            assert entry.user_id == "usr_admin"
            assert "threshold" in entry.details

    asyncio.run(_run())


def test_analysis_creation_and_pipeline(client, test_video_bytes):
    # 1. Submit video via multipart POST /v1/analyses
    files = {"file": ("test_clip.mp4", test_video_bytes, "video/mp4")}
    resp = client.post("/v1/analyses", files=files, data={"policy_id": "pol_strict_v3"})
    assert resp.status_code == 202
    data = resp.json()
    assert "analysis_id" in data
    analysis_id = data["analysis_id"]
    assert data["status"] == "queued"

    # 2. Fetch completed analysis via GET /v1/analyses/{id}
    get_resp = client.get(f"/v1/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    res_data = get_resp.json()
    assert res_data["id"] == analysis_id
    assert res_data["status"] == "completed"
    assert res_data["decision"] in (
        "likely_authentic",
        "needs_review",
        "likely_manipulated",
        "inconclusive",
    )
    assert res_data["scores"] is not None
    assert "p_bal" in res_data["scores"]
    assert "p_prior" in res_data["scores"]
    assert res_data["receipt_id"] is not None
    assert res_data["cache_hit"] is False

    # 3. Test Deduplication Cache (Submit identical bytes again)
    files2 = {"file": ("test_clip_dup.mp4", test_video_bytes, "video/mp4")}
    resp2 = client.post("/v1/analyses", files=files2, data={"policy_id": "pol_strict_v3"})
    assert resp2.status_code == 202
    analysis_id_2 = resp2.json()["analysis_id"]

    get_resp2 = client.get(f"/v1/analyses/{analysis_id_2}")
    assert get_resp2.status_code == 200
    res_data_2 = get_resp2.json()
    assert res_data_2["status"] == "completed"
    assert res_data_2["cache_hit"] is True
    # Should match decision of first analysis
    assert res_data_2["decision"] == res_data["decision"]


def test_evidence_endpoint(client, test_video_bytes):
    files = {"file": ("evidence_test.mp4", test_video_bytes, "video/mp4")}
    resp = client.post("/v1/analyses", files=files)
    analysis_id = resp.json()["analysis_id"]

    ev_resp = client.get(f"/v1/analyses/{analysis_id}/evidence")
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert "manifest_url" in ev_data
    assert "overlay_url" in ev_data


def test_sse_stream_endpoint(client):
    with client.stream("GET", "/v1/analyses/an_mock_stream/events") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


def test_list_analyses_endpoint(client, test_video_bytes):
    # Submit analysis
    files = {"file": ("list_test.mp4", test_video_bytes, "video/mp4")}
    resp = client.post("/v1/analyses", files=files, data={"policy_id": "pol_strict_v3", "external_ref": "upload"})
    assert resp.status_code == 202
    analysis_id = resp.json()["analysis_id"]

    # Call GET /v1/analyses
    list_resp = client.get("/v1/analyses?limit=10")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "items" in list_data
    assert "total" in list_data
    assert list_data["total"] >= 1

    first = next(item for item in list_data["items"] if item["id"] == analysis_id)
    assert first["id"] == analysis_id
    assert first["status"] == "completed"
    assert first["source"] == "upload"
    assert "decision" in first
    assert "faces" in first


def test_track_bounding_box_and_evidence(client, test_video_bytes):
    files = {"file": ("bbox_test.mp4", test_video_bytes, "video/mp4")}
    resp = client.post("/v1/analyses", files=files, data={"policy_id": "pol_strict_v3", "explain_gradcam": "true"})
    assert resp.status_code == 202
    analysis_id = resp.json()["analysis_id"]

    get_resp = client.get(f"/v1/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    tracks = data.get("tracks", [])
    if tracks:
        for t in tracks:
            assert "box" in t
            if t["box"]:
                assert 0.0 <= t["box"]["x"] <= 1.0
                assert 0.0 <= t["box"]["y"] <= 1.0
                assert 0.0 <= t["box"]["w"] <= 1.0
                assert 0.0 <= t["box"]["h"] <= 1.0

    # Evidence overlay route
    ov_resp = client.get(f"/v1/analyses/{analysis_id}/evidence/overlay.mp4")
    assert ov_resp.status_code in (200, 404)


def test_review_queue_and_submission(client, test_video_bytes):
    # Submit video
    files = {"file": ("review_test.mp4", test_video_bytes, "video/mp4")}
    resp = client.post("/v1/analyses", files=files)
    analysis_id = resp.json()["analysis_id"]

    # Manually check review queue
    q_resp = client.get("/v1/review-queue")
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    assert "items" in q_data
    assert "total" in q_data

    # Submit review
    review_payload = {
        "decision": "manipulated",
        "reasons": ["blending_seam"],
        "notes": "Verified manipulation seam on face border",
        "confidence": 4,
        "telemetry": {"triage_ms": 1250},
    }
    rev_resp = client.post(f"/v1/reviews/{analysis_id}", json=review_payload)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert "review_id" in rev_data
    assert rev_data["status"] == "recorded"
    assert "receipt" in rev_data

    # Verify analysis is marked as reviewed in DB
    get_resp = client.get(f"/v1/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["review_status"] == "reviewed"
