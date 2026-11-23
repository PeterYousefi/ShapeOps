"""Unit tests for scripts/verify_health.py CLI utility."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

import scripts.verify_health as probe


def _mock_response(status_code: int, data: dict):
    body_bytes = json.dumps(data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = status_code
    mock_resp.read.return_value = body_bytes
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_fetch_json_success():
    payload = {"status": "healthy"}
    with patch("scripts.verify_health.urlopen", return_value=_mock_response(200, payload)):
        code, data = probe.fetch_json("http://mocked/api/health")
        assert code == 200
        assert data == payload


def test_fetch_json_http_error():
    err_body = json.dumps({"ready": False, "checks": {"models_loaded": False}}).encode("utf-8")
    fp = io.BytesIO(err_body)
    err = HTTPError("http://mocked/api/ready", 503, "Service Unavailable", {}, fp)  # type: ignore[arg-type]
    with patch("scripts.verify_health.urlopen", side_effect=err):
        code, data = probe.fetch_json("http://mocked/api/ready")
        assert code == 503
        assert isinstance(data, dict)
        assert data["ready"] is False


def test_fetch_json_url_error():
    err = URLError("Connection refused")
    with (
        patch("scripts.verify_health.urlopen", side_effect=err),
        pytest.raises(ConnectionError, match="Failed to reach"),
    ):
        probe.fetch_json("http://unreachable/api/health")


def test_verify_service_healthy_and_ready():
    def mock_fetch(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 200, {
                "ready": True,
                "models_count": 2,
                "samples_count": 5,
                "checks": {
                    "models_loaded": True,
                    "samples_cached": True,
                    "telemetry_db": True,
                },
            }
        return 404, {}

    with patch.object(probe, "fetch_json", side_effect=mock_fetch):
        report = probe.verify_service("http://mocked")
        assert report["healthy"] is True
        assert report["ready"] is True
        assert report["details"]["health"]["ok"] is True
        assert report["details"]["readiness"]["ok"] is True


def test_verify_service_degraded_readiness():
    def mock_fetch(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 503, {
                "ready": False,
                "models_count": 0,
                "samples_count": 5,
                "checks": {
                    "models_loaded": False,
                    "samples_cached": True,
                    "telemetry_db": True,
                },
            }
        return 404, {}

    with patch.object(probe, "fetch_json", side_effect=mock_fetch):
        report = probe.verify_service("http://mocked")
        assert report["healthy"] is True
        assert report["ready"] is False
        assert report["details"]["readiness"]["ok"] is False


def test_main_cli_success(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {
                "ok": True,
                "status_code": 200,
                "body": {
                    "ready": True,
                    "models_count": 2,
                    "samples_count": 5,
                    "checks": {
                        "models_loaded": True,
                        "samples_cached": True,
                        "telemetry_db": True,
                    },
                },
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--json"])
        assert code == 0
        captured = capsys.readouterr()
        out_json = json.loads(captured.out)
        assert out_json["ready"] is True
        assert out_json["healthy"] is True


def test_main_cli_unready_exit_code(capsys):
    unready_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": False,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {
                "ok": False,
                "status_code": 503,
                "body": {
                    "ready": False,
                    "models_count": 0,
                    "samples_count": 5,
                    "checks": {
                        "models_loaded": False,
                        "samples_cached": True,
                        "telemetry_db": True,
                    },
                },
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=unready_report):
        code = probe.main([])
        assert code == 1
        captured = capsys.readouterr()
        assert "NOT READY" in captured.out


def test_main_cli_ready_only_flag():
    with patch.object(probe, "verify_service") as mock_verify:
        mock_verify.return_value = {
            "base_url": "http://custom:9000",
            "healthy": True,
            "ready": True,
            "details": {},
        }
        code = probe.main(["--base-url", "http://custom:9000", "--ready-only"])
        assert code == 0
        mock_verify.assert_called_once_with(
            base_url="http://custom:9000",
            timeout=5.0,
            ready_only=True,
            check_version=False,
        )


def test_verify_service_with_version_check():
    def mock_fetch(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 200, {
                "ready": True,
                "models_count": 2,
                "samples_count": 5,
                "checks": {
                    "models_loaded": True,
                    "samples_cached": True,
                    "telemetry_db": True,
                },
            }
        if url.endswith("/api/version"):
            return 200, {
                "version": "0.1.0",
                "app_name": "ShapeOps",
                "cad_engine": "OpenCascade 7.9.3",
                "python_version": "3.14.7",
                "uptime_seconds": 12.3,
            }
        return 404, {}

    with patch.object(probe, "fetch_json", side_effect=mock_fetch):
        report = probe.verify_service("http://mocked", check_version=True)
        assert report["healthy"] is True
        assert report["ready"] is True
        assert report["details"]["version"]["ok"] is True
        assert report["details"]["version"]["body"]["version"] == "0.1.0"


def test_main_cli_quiet_mode(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {"ok": True, "status_code": 200, "body": {"ready": True}},
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--quiet"])
        assert code == 0
        captured = capsys.readouterr()
        assert captured.out == ""


def test_main_cli_check_version_flag(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {"ok": True, "status_code": 200, "body": {"ready": True}},
            "version": {
                "ok": True,
                "body": {
                    "app_name": "ShapeOps",
                    "version": "0.1.0",
                    "cad_engine": "OpenCascade 7.9.3",
                    "python_version": "3.14.7",
                    "uptime_seconds": 15.0,
                },
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--check-version"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Version   (/api/version):" in captured.out
        assert "OpenCascade 7.9.3" in captured.out

