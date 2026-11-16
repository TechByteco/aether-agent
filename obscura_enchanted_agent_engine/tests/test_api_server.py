"""Integration tests for the FastAPI HTTP API server."""

from starlette.testclient import TestClient
from obscura_engine.api_server import app


def test_api_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "api_version" in data


def test_api_metrics():
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_tabs" in data or "uptime_seconds" in data


def test_api_sessions_lifecycle():
    client = TestClient(app)
    sid = "test-session-lifecycle"

    # Create session
    create_resp = client.post("/sessions", json={"session_id": sid})
    assert create_resp.status_code == 201
    assert create_resp.json()["session_id"] == sid

    # List sessions
    list_resp = client.get("/sessions")
    assert list_resp.status_code == 200
    assert sid in list_resp.json()["sessions"]

    # Delete session
    del_resp = client.delete(f"/sessions/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["destroyed"] is True


def test_api_snapshot_and_diff():
    client = TestClient(app)
    snap_resp = client.get("/snapshot")
    assert snap_resp.status_code == 200
    assert "markdown" in snap_resp.json()

    diff_resp = client.get("/diff")
    assert diff_resp.status_code == 200
    assert "has_changed" in diff_resp.json()
