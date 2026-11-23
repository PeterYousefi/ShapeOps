"""Unit tests for scripts/benchmark.py CLI utility."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx

import scripts.benchmark as bench


def _mock_post_response(status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "latency_ms": 15.2,
        "execution_ms": 14.1,
        "face_count": 24,
        "confidence": 0.98,
        "disagreements": 0,
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_run_benchmark_collects_rows():
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = _mock_post_response(200)

    with patch("httpx.Client", return_value=mock_client):
        report = bench.run_benchmark(
            base_url="http://testserver",
            models=["surface-rf-v1"],
            samples=["bracket", "flange"],
            delay=0.0,
            timeout=5.0,
        )

    assert len(report["requests"]) == 2
    assert report["median_client_ms"] >= 0
    assert report["max_client_ms"] >= 0
    assert report["conditions"]["concurrency"] == 1
    assert "surface-rf-v1" in report["requests"][0]["model"]


def test_benchmark_cli_main_success(tmp_path, capsys):
    out_file = tmp_path / "bench.json"
    fake_report = {
        "conditions": {"platform": "test"},
        "requests": [{"client_ms": 10.0}, {"client_ms": 20.0}],
        "median_client_ms": 15.0,
        "max_client_ms": 20.0,
    }

    with patch.object(bench, "run_benchmark", return_value=fake_report):
        code = bench.main([
            "--output",
            str(out_file),
            "--json",
        ])
        assert code == 0
        assert out_file.exists()
        saved = json.loads(out_file.read_text())
        assert saved["median_client_ms"] == 15.0

        captured = capsys.readouterr()
        out_json = json.loads(captured.out)
        assert out_json["median_client_ms"] == 15.0


def test_benchmark_cli_main_handles_http_error(capsys):
    with patch.object(bench, "run_benchmark", side_effect=httpx.ConnectError("Connection refused")):
        code = bench.main(["--base-url", "http://unreachable"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Benchmark error querying http://unreachable" in captured.err
