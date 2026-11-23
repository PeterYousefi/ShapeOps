"""Unit and response contract tests for GET /api/version."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app import app

    return TestClient(app)


def test_version_endpoint_status_and_fields(client):
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()

    assert data["version"] == "0.1.0"
    assert data["app_name"] == "ShapeOps"
    assert "OpenCascade" in data["cad_engine"]
    assert isinstance(data["python_version"], str) and data["python_version"]
    assert isinstance(data["os_platform"], str) and data["os_platform"]
    assert isinstance(data["models_count"], int) and data["models_count"] >= 0
    assert isinstance(data["samples_count"], int) and data["samples_count"] >= 0
    assert isinstance(data["uptime_seconds"], (int, float)) and data["uptime_seconds"] >= 0
    assert data["status"] in ("operational", "degraded")


def test_version_response_model_validation():
    from backend.responses import VersionResponse

    valid_payload = {
        "version": "0.1.0",
        "app_name": "ShapeOps",
        "cad_engine": "OpenCascade 7.9.3",
        "python_version": "3.14.7",
        "os_platform": "macOS-Darwin",
        "models_count": 2,
        "samples_count": 5,
        "uptime_seconds": 42.5,
        "status": "operational",
    }
    validated = VersionResponse.model_validate(valid_payload)
    assert validated.version == "0.1.0"
    assert validated.status == "operational"

    # Strict rejection of negative uptime
    with pytest.raises(ValidationError):
        VersionResponse.model_validate({**valid_payload, "uptime_seconds": -1.0})

    # Strict rejection of invalid status
    with pytest.raises(ValidationError):
        VersionResponse.model_validate({**valid_payload, "status": "unknown"})

    # Strict rejection of extra unexpected fields
    with pytest.raises(ValidationError):
        VersionResponse.model_validate({**valid_payload, "extra_field": "disallowed"})
