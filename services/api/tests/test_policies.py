import os

os.environ["SV_TESTING"] = "1"
os.environ["SV_ENGINE_MODE"] = "mock"
os.environ["SV_DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"

import asyncio

import pytest
from fastapi.testclient import TestClient
from sv_api.database import Base, engine
from sv_api.main import app


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


def test_get_policy_presets(client):
    """GET /v1/policies/presets returns built-in presets."""
    response = client.get("/v1/policies/presets")
    assert response.status_code == 200
    presets = response.json()
    assert "strict-low-fpr" in presets
    assert "transfer-calibrated" in presets
    assert "evidence-desk" in presets
    assert presets["strict-low-fpr"]["target_prevalence"] == 0.01


def test_list_and_get_policies(client):
    """GET /v1/policies lists policies and GET /v1/policies/{id} retrieves specific policy."""
    # List policies (defaults to built-in presets if DB has none)
    list_resp = client.get("/v1/policies")
    assert list_resp.status_code == 200
    policies = list_resp.json()
    assert len(policies) >= 3

    # Retrieve specific policy
    get_resp = client.get("/v1/policies/strict-low-fpr")
    assert get_resp.status_code == 200
    p = get_resp.json()
    assert p["policy_id"] == "strict-low-fpr"
    assert p["cascade_enabled"] is True
    assert p["thresholds"]["tau_authentic"] == 0.30


def test_create_and_update_policy(client):
    """POST /v1/policies creates new policy and increments version on update."""
    payload = {
        "policy_id": "custom-gov-policy",
        "name": "Custom Government Screening Policy",
        "description": "High assurance screening policy for public records.",
        "target_prevalence": 0.02,
        "stage1_variant": "smsdt-s-a",
        "stage2_variant": "smsdt-st-b",
        "cascade_enabled": True,
        "exit_below_p_bal": 0.10,
        "thresholds": {"tau_authentic": 0.25, "tau_manipulated": 0.80},
        "audit_sample_rate": 0.05,
    }

    # 1. Create
    resp1 = client.post("/v1/policies", json=payload)
    assert resp1.status_code == 201
    created = resp1.json()
    assert created["policy_id"] == "custom-gov-policy"
    assert created["version"] == 1

    # Verify retrieval
    get_resp = client.get("/v1/policies/custom-gov-policy")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Custom Government Screening Policy"

    # 2. Update
    payload["name"] = "Updated Government Policy"
    resp2 = client.post("/v1/policies", json=payload)
    assert resp2.status_code == 201
    updated = resp2.json()
    assert updated["version"] == 2
    assert updated["name"] == "Updated Government Policy"


def test_simulate_policy_endpoint(client):
    """POST /v1/policies/simulate runs prevalence-aware simulation and matches SPEC §7.4."""
    # Simulate by variant
    sim_resp = client.post(
        "/v1/policies/simulate",
        json={
            "variant": "smsdt-full-c",
            "fpr": 0.01,
            "prevalence": 0.01,
            "volume_per_day": 10000,
            "sweep": True,
        },
    )
    assert sim_resp.status_code == 200
    sim = sim_resp.json()
    assert sim["per_10k"]["flags_rounded"] == 138
    assert abs(sim["ppv_pct"] - 28.47) < 0.1
    assert "prevalence_sweep" in sim
    assert len(sim["prevalence_sweep"]) > 0

    # Simulate with custom tpr/fpr
    custom_resp = client.post(
        "/v1/policies/simulate",
        json={
            "tpr": 0.80,
            "fpr": 0.02,
            "prevalence": 0.05,
            "volume_per_day": 5000,
        },
    )
    assert custom_resp.status_code == 200
    custom_sim = custom_resp.json()
    assert custom_sim["tpr"] == 0.80
    assert custom_sim["fpr"] == 0.02


def test_reject_nonpositive_policy_version(client):
    """POST /v1/policies with version <= 0 returns 422 Unprocessable Entity."""
    payload = {
        "policy_id": "invalid-version-policy",
        "version": 0,
        "name": "Invalid Version Policy",
        "target_prevalence": 0.01,
        "stage1_variant": "smsdt-s-a",
        "stage2_variant": "smsdt-st-b",
        "cascade_enabled": True,
        "exit_below_p_bal": 0.12,
        "thresholds": {"tau_authentic": 0.35, "tau_manipulated": 0.75},
        "audit_sample_rate": 0.02,
    }
    resp = client.post("/v1/policies", json=payload)
    assert resp.status_code == 422


def test_reject_long_policy_fields(client):
    """POST /v1/policies with policy_id or name > 64 chars returns 422."""
    payload = {
        "policy_id": "a" * 65,
        "version": 1,
        "name": "Standard Policy",
        "target_prevalence": 0.01,
        "stage1_variant": "smsdt-s-a",
        "stage2_variant": "smsdt-st-b",
    }
    resp = client.post("/v1/policies", json=payload)
    assert resp.status_code == 422

    payload2 = {
        "policy_id": "valid-id",
        "version": 1,
        "name": "b" * 65,
        "target_prevalence": 0.01,
        "stage1_variant": "smsdt-s-a",
        "stage2_variant": "smsdt-st-b",
    }
    resp2 = client.post("/v1/policies", json=payload2)
    assert resp2.status_code == 422


def test_simulate_invalid_variant_returns_422(client):
    """POST /v1/policies/simulate with unsupported variant returns 422."""
    resp = client.post(
        "/v1/policies/simulate",
        json={"variant": "invalid-unsupported-variant"},
    )
    assert resp.status_code == 422
