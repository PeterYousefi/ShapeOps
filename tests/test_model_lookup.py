"""Unit tests for GET /api/registry/models/{model_id} endpoint."""
from __future__ import annotations

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client


def test_get_registered_model_by_id_success(client):
    for model_id in ["surface-rf-v1", "surface-et-v2"]:
        response = client.get(f"/api/registry/models/{model_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == model_id
        assert "checksum" in data
        assert "package_id" in data
        assert "stage" in data
        assert data["stage"] in ("stable", "candidate")
        assert isinstance(data["accuracy"], (float, int))
        assert data["accuracy"] > 0.0


def test_get_registered_model_not_found(client):
    response = client.get("/api/registry/models/non-existent-model")
    assert response.status_code == 404
    assert "not found in active registry" in response.json()["detail"]
