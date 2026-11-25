import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app import app
    with TestClient(app) as test_client:
        yield test_client


def test_sample_lookup_all_valid_samples(client: TestClient):
    from backend.cad import SAMPLES
    from backend.responses import SampleEntry

    for sample in SAMPLES:
        resp = client.get(f"/api/samples/{sample['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample["id"]
        assert data["name"] == sample["name"]
        assert data["description"] == sample["description"]
        entry = SampleEntry.model_validate(data)
        assert entry.id == sample["id"]


def test_sample_lookup_not_found(client: TestClient):
    resp = client.get("/api/samples/nonexistent-part")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_sample_lookup_empty_key(client: TestClient):
    resp = client.get("/api/samples/")
    # Trailing slash either redirects to /api/samples or returns list of samples
    assert resp.status_code in (200, 307)
