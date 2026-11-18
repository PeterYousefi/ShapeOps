"""Tests for the /api/ready readiness probe and response contract."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.app import app
from backend.responses import ReadinessChecks, ReadinessResponse


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_readiness_endpoint_reports_ready_when_initialized(client):
    response = client.get("/api/ready")
    assert response.status_code == 200
    parsed = ReadinessResponse.model_validate(response.json())
    assert parsed.ready is True
    assert parsed.models_count >= 2
    assert parsed.samples_count == 5
    assert parsed.checks.models_loaded is True
    assert parsed.checks.samples_cached is True
    assert parsed.checks.telemetry_db is True


def test_readiness_endpoint_returns_503_when_models_missing(client):
    original_models = app.state.models
    try:
        app.state.models = {}
        response = client.get("/api/ready")
        assert response.status_code == 503
        parsed = ReadinessResponse.model_validate(response.json())
        assert parsed.ready is False
        assert parsed.models_count == 0
        assert parsed.checks.models_loaded is False
    finally:
        app.state.models = original_models


def test_readiness_contract_rejects_inconsistent_summary():
    with pytest.raises(ValidationError):
        ReadinessResponse(
            ready=True,
            models_count=0,
            samples_count=5,
            checks=ReadinessChecks(
                models_loaded=False,
                samples_cached=True,
                telemetry_db=True,
            ),
        )
