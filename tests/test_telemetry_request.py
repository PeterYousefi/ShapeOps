"""Unit and response contract tests for GET /api/telemetry/requests/{trace_id}."""
from __future__ import annotations

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client


def test_get_telemetry_request_by_trace_id_success(client):
    from backend.responses import RequestRecord

    # 1. Execute real sample inference to generate actual telemetry trace
    inference_resp = client.post(
        "/api/inference/sample",
        json={"sample": "bracket", "model": "surface-rf-v1", "compare": False},
    )
    assert inference_resp.status_code == 200
    trace_id = inference_resp.json()["trace_id"]
    assert trace_id

    # 2. Query individual telemetry trace by ID
    response = client.get(f"/api/telemetry/requests/{trace_id}")
    assert response.status_code == 200
    data = response.json()

    # 3. Verify RequestRecord contract
    record = RequestRecord.model_validate(data)
    assert record.id == trace_id
    assert record.source == "sample"
    assert record.model == "surface-rf-v1"
    assert record.success == 1
    assert record.faces > 0
    assert record.latency > 0


def test_get_telemetry_request_not_found(client):
    non_existent = "f" * 32
    response = client.get(f"/api/telemetry/requests/{non_existent}")
    assert response.status_code == 404
    assert "not found in retained telemetry" in response.json()["detail"]
