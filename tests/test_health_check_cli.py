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
            check_metrics=False,
            check_samples=False,
            check_drills=False,
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


def test_verify_service_with_metrics_check():
    def mock_fetch_json(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 200, {"ready": True, "checks": {"models_loaded": True, "samples_cached": True, "telemetry_db": True}}
        return 404, {}

    mock_metrics_text = (
        "# HELP shapeops_registered_models_total Number of models\n"
        "# TYPE shapeops_registered_models_total gauge\n"
        "shapeops_registered_models_total 2\n"
        "# HELP shapeops_process_uptime_seconds Uptime\n"
        "shapeops_process_uptime_seconds 99.5\n"
    )

    with (
        patch.object(probe, "fetch_json", side_effect=mock_fetch_json),
        patch.object(probe, "fetch_text", return_value=(200, mock_metrics_text)),
    ):
        report = probe.verify_service("http://mocked", check_metrics=True)
        assert report["healthy"] is True
        assert report["ready"] is True
        assert report["details"]["metrics"]["ok"] is True
        m = report["details"]["metrics"]["metrics"]
        assert m["shapeops_registered_models_total"] == "2"
        assert m["shapeops_process_uptime_seconds"] == "99.5"


def test_main_cli_check_metrics_flag(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {"ok": True, "status_code": 200, "body": {"ready": True}},
            "metrics": {
                "ok": True,
                "metrics": {
                    "shapeops_registered_models_total": "2",
                    "shapeops_process_uptime_seconds": "123.45",
                },
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--check-metrics"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Metrics   (/metrics)   :" in captured.out
        assert "Active models   : 2" in captured.out
        assert "Process uptime  : 123.45s" in captured.out


def test_verify_service_with_samples_check():
    def mock_fetch(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 200, {"ready": True}
        if url.endswith("/api/samples"):
            return 200, [
                {"id": "bracket", "name": "Mounting bracket"},
                {"id": "flange", "name": "Bearing flange"},
            ]
        return 404, {}

    with patch.object(probe, "fetch_json", side_effect=mock_fetch):
        report = probe.verify_service("http://mocked", check_samples=True)
        assert report["healthy"] is True
        assert report["ready"] is True
        assert report["details"]["samples"]["ok"] is True
        samples = report["details"]["samples"]["body"]
        assert len(samples) == 2
        assert samples[0]["id"] == "bracket"


def test_main_cli_check_samples_flag(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {"ok": True, "status_code": 200, "body": {"ready": True}},
            "samples": {
                "ok": True,
                "body": [
                    {"id": "bracket", "name": "Mounting bracket"},
                    {"id": "flange", "name": "Bearing flange"},
                ],
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--check-samples"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Samples   (/api/samples):" in captured.out
        assert "- bracket: Mounting bracket" in captured.out
        assert "- flange: Bearing flange" in captured.out


def test_verify_service_with_drills_check():
    def mock_fetch(url: str, timeout: float = 5.0):
        if url.endswith("/api/health"):
            return 200, {"status": "healthy"}
        if url.endswith("/api/ready"):
            return 200, {"ready": True}
        if url.endswith("/api/operations"):
            return 200, {
                "active": "surface-rf-v1",
                "drills": [
                    {
                        "id": "abc123def456",
                        "at": 1700000000.0,
                        "passed": True,
                        "duration_ms": 4.2,
                        "checks": [{"name": "Check 1", "passed": True}],
                        "scope": "Isolated adapter test. No deployment or production mutation.",
                    }
                ],
            }
        return 404, {}

    with patch.object(probe, "fetch_json", side_effect=mock_fetch):
        report = probe.verify_service("http://mocked", check_drills=True)
        assert report["healthy"] is True
        assert report["ready"] is True
        assert report["details"]["drills"]["ok"] is True
        drills = report["details"]["drills"]["body"]["drills"]
        assert len(drills) == 1
        assert drills[0]["id"] == "abc123def456"


def test_main_cli_check_drills_flag(capsys):
    healthy_report = {
        "base_url": "http://127.0.0.1:8000",
        "healthy": True,
        "ready": True,
        "details": {
            "health": {"ok": True, "status_code": 200, "body": {"status": "healthy"}},
            "readiness": {"ok": True, "status_code": 200, "body": {"ready": True}},
            "drills": {
                "ok": True,
                "body": {
                    "drills": [
                        {
                            "id": "drill01",
                            "passed": True,
                            "duration_ms": 5.4,
                            "checks": [{"name": "Injected adapter test", "passed": True}],
                        }
                    ]
                },
            },
        },
    }
    with patch.object(probe, "verify_service", return_value=healthy_report):
        code = probe.main(["--check-drills"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Drills    (/api/operations):" in captured.out
        assert "Completed drills: 1" in captured.out
        assert "Latest drill    : PASS (5.4ms, 1 checks)" in captured.out




