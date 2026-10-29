import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_monitor.db"

import asyncio

import pytest
from fastapi.testclient import TestClient
from sv_api.database import Base, engine
from sv_api.main import app


@pytest.fixture(scope="module")
def client():
    async def prepare_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(prepare_db())
    with TestClient(app) as c:
        yield c


def test_get_drift_endpoint(client):
    """GET /v1/monitor/drift returns PSI drift summary."""
    resp = client.get("/v1/monitor/drift")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "score_drift" in data
    assert data["score_drift"]["feature_name"] == "score"
    assert "input_drifts" in data
    assert "face_size" in data["input_drifts"]


def test_get_calibration_endpoint(client):
    """GET /v1/monitor/calibration returns IPW ECE and 15-bin reliability diagram."""
    resp = client.get("/v1/monitor/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert "ece" in data
    assert "brier_score" in data
    assert len(data["reliability_curve"]) == 15


def test_recalibration_lifecycle_endpoints(client):
    """POST /v1/models/{id}/recalibrations and promote workflow."""
    # 1. Propose recalibration with default demo expert reviews
    prop_resp = client.post("/v1/models/smsdt-st-b/recalibrations", json={})
    assert prop_resp.status_code == 201
    prop_data = prop_resp.json()
    proposal_id = prop_data["proposal_id"]
    assert proposal_id.startswith("prop_")
    assert prop_data["n_expert_reviews"] == 300
    assert "candidate_parameters" in prop_data
    assert "delta_ece" in prop_data

    # 2. Rejection on short justification (<20 chars)
    bad_promote = client.post(
        f"/v1/models/smsdt-st-b/recalibrations/{proposal_id}/promote",
        json={"justification": "short"},
    )
    assert bad_promote.status_code == 422

    # 3. Successful promotion
    good_promote = client.post(
        f"/v1/models/smsdt-st-b/recalibrations/{proposal_id}/promote",
        json={
            "justification": "Recalibrated on 300 expert labels after observed mobile phone compression shifts.",
            "target_bundle_version": "bundle-2026-recal-03",
        },
    )
    assert good_promote.status_code == 200
    promoted = good_promote.json()
    assert promoted["proposal_id"] == proposal_id
    assert promoted["bundle_version"] == "bundle-2026-recal-03"
    assert len(promoted["bundle_hash"]) == 64

    # 4. 404 for unknown proposal
    not_found = client.post(
        "/v1/models/smsdt-st-b/recalibrations/prop_nonexistent/promote",
        json={"justification": "Valid length justification string here."},
    )
    assert not_found.status_code == 404


def test_recalibration_insufficient_samples(client):
    """POST /v1/models/{id}/recalibrations with insufficient reviews returns 422."""
    resp = client.post(
        "/v1/models/smsdt-st-b/recalibrations",
        json={"u_scores": [0.1, -0.2], "labels": [1, 0], "min_samples": 200},
    )
    assert resp.status_code == 422
    assert "at least 200" in resp.json()["detail"]


def test_retention_purge_endpoint(client):
    """POST /v1/monitor/retention/run triggers retention policy."""
    resp = client.post(
        "/v1/monitor/retention/run",
        json={"media_days": 30, "evidence_days": 180},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "media_files_purged" in data
    assert "receipts_preserved" in data
