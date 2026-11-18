"""Tests for /api/telemetry/export.csv and CSV formula-injection neutralization."""
import csv
import io
import pytest
from fastapi.testclient import TestClient
from backend.app import app, _sanitize_csv_cell


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("=CMD()|'/C calc'!A0", "'=CMD()|'/C calc'!A0"),
        ("+1+2", "'+1+2"),
        ("-10", "'-10"),
        ("@SUM(A1:A2)", "'@SUM(A1:A2)"),
        ("\tpayload", "'\tpayload"),
        ("normal-value", "normal-value"),
        ("", ""),
        (None, ""),
    ],
)
def test_csv_cell_sanitization_neutralizes_formula_prefixes(raw, expected):
    assert _sanitize_csv_cell(raw) == expected


def test_telemetry_csv_export_returns_bounded_valid_csv(client):
    res = client.post(
        "/api/inference/sample",
        json={"sample": "bracket", "model": "surface-rf-v1", "compare": False},
    )
    assert res.status_code == 200

    export = client.get("/api/telemetry/export.csv?limit=5")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert 'filename="shapeops-telemetry.csv"' in export.headers["content-disposition"]
    assert export.headers["cache-control"] == "no-store"

    rows = list(csv.reader(io.StringIO(export.text)))
    assert rows[0] == [
        "id",
        "at",
        "source",
        "model",
        "success",
        "latency_ms",
        "parse_ms",
        "execution_ms",
        "faces",
        "confidence",
        "ood",
        "error",
    ]
    assert 1 <= len(rows) - 1 <= 5
    assert rows[1][2] in ("sample", "upload")


def test_telemetry_csv_export_rejects_out_of_bounds_limit(client):
    assert client.get("/api/telemetry/export.csv?limit=0").status_code == 422
    assert client.get("/api/telemetry/export.csv?limit=1001").status_code == 422
