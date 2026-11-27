"""Unit and response contract tests for GET /api/operations/drills/{drill_id}."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app import app
    with TestClient(app) as test_client:
        yield test_client


def test_drill_lookup_successful(client: TestClient):
    from backend.responses import DrillResult

    post_resp = client.post("/api/operations/drill")
    assert post_resp.status_code == 200
    created = post_resp.json()
    drill_id = created["id"]
    assert len(drill_id) == 12

    get_resp = client.get(f"/api/operations/drills/{drill_id}")
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["id"] == drill_id
    assert retrieved["passed"] is True
    assert len(retrieved["checks"]) == 3
    assert retrieved["scope"] == "Isolated adapter test. No deployment or production mutation."

    validated = DrillResult.model_validate(retrieved)
    assert validated.id == drill_id
    assert validated.passed is True


def test_drill_lookup_not_found(client: TestClient):
    resp = client.get("/api/operations/drills/nonexistent01")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_multiple_drills_independent_lookup(client: TestClient):
    from backend.responses import DrillResult

    first = client.post("/api/operations/drill").json()
    second = client.post("/api/operations/drill").json()
    assert first["id"] != second["id"]

    resp1 = client.get(f"/api/operations/drills/{first['id']}")
    resp2 = client.get(f"/api/operations/drills/{second['id']}")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    DrillResult.model_validate(resp1.json())
    DrillResult.model_validate(resp2.json())
