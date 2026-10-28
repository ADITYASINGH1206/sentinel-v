from fastapi.testclient import TestClient
from sv_api.main import app

client = TestClient(app)


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "engine_mode" in data


def test_readyz():
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_compat_endpoint():
    res = client.post(
        "/compat/moderate/video",
        json={"post_id": "test_post_1", "video_url": "https://example.com/test.mp4"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "deepfake_confidence" in data
    assert "analysis_id" in data

