"""Tests for GET /api/samples/{key}/metadata and SampleMetadata contract."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.app import app
from backend.cad import SAMPLES
from backend.responses import SampleMetadata


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_sample_metadata_returns_valid_geometry_summary_for_all_samples(client):
    before_telemetry = client.get("/api/telemetry").json()["total"]
    for sample in SAMPLES:
        response = client.get(f"/api/samples/{sample['id']}/metadata")
        assert response.status_code == 200
        parsed = SampleMetadata.model_validate(response.json())
        assert parsed.id == sample["id"]
        assert parsed.name == sample["name"]
        assert parsed.face_count == sum(parsed.surface_distribution.values())
        assert parsed.volume > 0
        assert parsed.total_surface_area > 0
    # Metadata inspection must be strictly read-only and never inflate inference telemetry.
    assert client.get("/api/telemetry").json()["total"] == before_telemetry


def test_sample_metadata_returns_404_for_unknown_sample(client):
    assert client.get("/api/samples/nonexistent/metadata").status_code == 404


def test_sample_metadata_rejects_mismatched_surface_distribution():
    with pytest.raises(ValidationError):
        SampleMetadata.model_validate(
            {
                "id": "fixture",
                "name": "Fixture",
                "description": "Test",
                "face_count": 10,
                "edge_count": 20,
                "volume": 100.0,
                "total_surface_area": 50.0,
                "bounds": [10.0, 10.0, 10.0],
                "surface_distribution": {"Planar": 4},
            }
        )
