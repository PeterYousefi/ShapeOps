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
    import uuid
    from backend.app import record
    from backend.responses import RequestRecord

    # 1. Record telemetry trace directly to verify contract without exhausting rate limits
    trace_id = uuid.uuid4().hex
    record(trace_id, "sample", "surface-rf-v1", True, 15.5, parse=3.0, execution=12.5, faces=14, confidence=0.98)

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
