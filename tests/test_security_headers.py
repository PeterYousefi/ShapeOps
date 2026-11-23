"""Unit tests verifying HTTP response security headers across endpoints."""
from __future__ import annotations

import re

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app import app

    return TestClient(app)


def test_api_endpoints_include_security_headers(client):
    endpoints = ["/api/health", "/api/version", "/api/ready"]
    hex_pattern = re.compile(r"^[a-f0-9]{32}$")

    for path in endpoints:
        response = client.get(path)
        assert response.status_code in (200, 503)

        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("referrer-policy") == "same-origin"
        assert headers.get("x-xss-protection") == "0"
        assert headers.get("cross-origin-opener-policy") == "same-origin"
        assert headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=()"

        trace_id = headers.get("x-request-id", "")
        assert hex_pattern.fullmatch(trace_id), f"Invalid trace ID format: {trace_id}"
