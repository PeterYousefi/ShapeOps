"""Tests for Prometheus /metrics exposition format and telemetry gauges."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.app import app

    with TestClient(app) as test_client:
        yield test_client


def test_metrics_exposes_quantiles_ood_rate_and_model_breakdown(client):
    inference = client.post(
        "/api/inference/sample",
        json={"sample": "bracket", "model": "surface-rf-v1", "compare": False},
    )
    assert inference.status_code == 200

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text

    assert "# TYPE shapeops_inference_requests gauge" in body
    assert "# TYPE shapeops_inference_throughput_per_minute gauge" in body
    assert "# TYPE shapeops_registered_models_total gauge" in body
    assert "shapeops_registered_models_total 2" in body
    assert "# TYPE shapeops_cached_samples_total gauge" in body
    assert "shapeops_cached_samples_total 5" in body
    assert "# TYPE shapeops_completed_drills_total gauge" in body
    assert "shapeops_completed_drills_total " in body
    assert "# TYPE shapeops_process_uptime_seconds gauge" in body
    assert "shapeops_process_uptime_seconds " in body
    assert "# TYPE shapeops_inference_latency_p50_ms gauge" in body
    assert "# TYPE shapeops_inference_latency_p95_ms gauge" in body
    assert "# TYPE shapeops_inference_ood_rate gauge" in body
    assert "# TYPE shapeops_inference_requests_by_model gauge" in body
    assert 'shapeops_inference_requests_by_model{model="surface-rf-v1"}' in body
    assert "# TYPE shapeops_last_request_latency_ms gauge" in body
