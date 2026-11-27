"""Unit and response contract tests for GET /api/operations/drills/{drill_id}."""
import time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app import app
    with TestClient(app) as test_client:
        yield test_client


def _seed_drill(drill_id: str, passed: bool = True):
    from backend.app import connection
    from backend.responses import DrillResult

    checks = [
        {"name": "Injected adapter failure detected", "passed": True},
        {"name": "Stable adapter recovery inference", "passed": True},
        {"name": "Active release unchanged", "passed": True},
    ]
    result = DrillResult.model_validate({
        "id": drill_id,
        "at": time.time(),
        "passed": passed,
        "checks": checks,
        "duration_ms": 3.5,
        "scope": "Isolated adapter test. No deployment or production mutation.",
    })
    with connection() as db:
        db.execute(
            "INSERT INTO drills VALUES (?,?,?)",
            (result.id, result.at, result.model_dump_json()),
        )
    return result


def test_drill_lookup_successful(client: TestClient):
    from backend.responses import DrillResult

    drill_id = "a1b2c3d4e5f6"
    _seed_drill(drill_id, passed=True)

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

    id1 = "111122223333"
    id2 = "444455556666"
    _seed_drill(id1, passed=True)
    _seed_drill(id2, passed=True)

    resp1 = client.get(f"/api/operations/drills/{id1}")
    resp2 = client.get(f"/api/operations/drills/{id2}")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    DrillResult.model_validate(resp1.json())
    DrillResult.model_validate(resp2.json())
