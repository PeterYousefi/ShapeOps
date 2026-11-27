#!/usr/bin/env python3
"""CLI tool to verify ShapeOps operational health, readiness, and metrics."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_json(url: str, timeout: float = 5.0) -> tuple[int, dict[str, Any] | str]:
    """Fetch JSON from a GET endpoint, returning (status_code, parsed_body)."""
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "ShapeOps-HealthCheck/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:
            status = response.getcode()
            raw = response.read().decode("utf-8")
            try:
                return status, json.loads(raw)
            except json.JSONDecodeError:
                return status, raw
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, raw
    except URLError as e:
        raise ConnectionError(f"Failed to reach {url}: {e.reason}") from e


def fetch_text(url: str, timeout: float = 5.0) -> tuple[int, str]:
    """Fetch raw text from a GET endpoint, returning (status_code, body)."""
    req = Request(url, headers={"Accept": "text/plain", "User-Agent": "ShapeOps-HealthCheck/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.getcode(), response.read().decode("utf-8")
    except HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        return e.code, raw
    except URLError as e:
        raise ConnectionError(f"Failed to reach {url}: {e.reason}") from e


def verify_service(
    base_url: str = "http://127.0.0.1:8000",
    timeout: float = 5.0,
    ready_only: bool = False,
    check_version: bool = False,
    check_metrics: bool = False,
    check_samples: bool = False,
    check_drills: bool = False,
) -> dict[str, Any]:
    """Execute operational health and readiness checks against a running ShapeOps server."""
    base = base_url.rstrip("/")
    results: dict[str, Any] = {
        "base_url": base,
        "healthy": False,
        "ready": False,
        "details": {},
    }

    # 1. Health probe (liveness)
    if not ready_only:
        try:
            status, body = fetch_json(f"{base}/api/health", timeout=timeout)
            results["details"]["health"] = {
                "status_code": status,
                "body": body,
                "ok": status == 200 and isinstance(body, dict) and body.get("status") == "healthy",
            }
            results["healthy"] = results["details"]["health"]["ok"]
        except ConnectionError as err:
            results["details"]["health"] = {"error": str(err), "ok": False}
            results["healthy"] = False
    else:
        results["healthy"] = True

    # 2. Readiness probe
    try:
        status, body = fetch_json(f"{base}/api/ready", timeout=timeout)
        is_ready = status == 200 and isinstance(body, dict) and body.get("ready") is True
        results["details"]["readiness"] = {
            "status_code": status,
            "body": body,
            "ok": is_ready,
        }
        results["ready"] = is_ready
    except ConnectionError as err:
        results["details"]["readiness"] = {"error": str(err), "ok": False}
        results["ready"] = False

    # 3. Optional version probe
    if check_version:
        try:
            status, body = fetch_json(f"{base}/api/version", timeout=timeout)
            results["details"]["version"] = {
                "status_code": status,
                "body": body,
                "ok": status == 200 and isinstance(body, dict),
            }
        except ConnectionError as err:
            results["details"]["version"] = {"error": str(err), "ok": False}

    # 4. Optional metrics probe
    if check_metrics:
        try:
            status, raw_text = fetch_text(f"{base}/metrics", timeout=timeout)
            parsed_metrics: dict[str, str] = {}
            for line in raw_text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) >= 2:
                        parsed_metrics[parts[0]] = parts[1]
            results["details"]["metrics"] = {
                "status_code": status,
                "metrics": parsed_metrics,
                "ok": status == 200 and "shapeops_process_uptime_seconds" in parsed_metrics,
            }
        except ConnectionError as err:
            results["details"]["metrics"] = {"error": str(err), "ok": False}

    # 5. Optional samples probe
    if check_samples:
        try:
            status, body = fetch_json(f"{base}/api/samples", timeout=timeout)
            results["details"]["samples"] = {
                "status_code": status,
                "body": body,
                "ok": status == 200 and isinstance(body, list) and len(body) > 0,
            }
        except ConnectionError as err:
            results["details"]["samples"] = {"error": str(err), "ok": False}

    # 6. Optional drills probe
    if check_drills:
        try:
            status, body = fetch_json(f"{base}/api/operations", timeout=timeout)
            is_dict = status == 200 and isinstance(body, dict)
            results["details"]["drills"] = {
                "status_code": status,
                "body": body,
                "ok": is_dict and "drills" in body,
            }
        except ConnectionError as err:
            results["details"]["drills"] = {"error": str(err), "ok": False}

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ShapeOps operational health and readiness probe status."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the ShapeOps service (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP request timeout in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--ready-only",
        action="store_true",
        help="Only check readiness (/api/ready), skipping liveness check",
    )
    parser.add_argument(
        "--check-version",
        action="store_true",
        help="Inspect application version and runtime metadata (/api/version)",
    )
    parser.add_argument(
        "--check-metrics",
        action="store_true",
        help="Scrape and inspect Prometheus exposition metrics (/metrics)",
    )
    parser.add_argument(
        "--check-samples",
        action="store_true",
        help="Inspect procedural reference CAD sample catalog (/api/samples)",
    )
    parser.add_argument(
        "--check-drills",
        action="store_true",
        help="Inspect operations incident drills (/api/operations)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode; suppress successful diagnostic output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON format",
    )

    args = parser.parse_args(argv)

    try:
        report = verify_service(
            base_url=args.base_url,
            timeout=args.timeout,
            ready_only=args.ready_only,
            check_version=args.check_version,
            check_metrics=args.check_metrics,
            check_samples=args.check_samples,
            check_drills=args.check_drills,
        )
    except (ConnectionError, OSError, ValueError) as exc:
        if args.json_output:
            print(json.dumps({"error": str(exc), "healthy": False, "ready": False}, indent=2))
        elif not args.quiet:
            print(f"ERROR: Connection failure querying {args.base_url}: {exc}", file=sys.stderr)
        return 2

    is_ok = report["ready"] and (args.ready_only or report["healthy"])

    if args.json_output:
        print(json.dumps(report, indent=2))
    elif not (args.quiet and is_ok):
        print("=== ShapeOps Service Health Report ===")
        print(f"Target URL: {report['base_url']}")
        if not args.ready_only:
            h_ok = report["healthy"]
            h_stat = "PASS (200 OK)" if h_ok else "FAIL"
            print(f"Liveness  (/api/health): {h_stat}")
        r_ok = report["ready"]
        r_stat = "READY (200 OK)" if r_ok else "NOT READY"
        print(f"Readiness (/api/ready) : {r_stat}")

        r_body = report["details"].get("readiness", {}).get("body")
        if isinstance(r_body, dict):
            checks = r_body.get("checks", {})
            models_n = r_body.get("models_count", 0)
            samples_n = r_body.get("samples_count", 0)
            print(f"  - Models loaded   : {checks.get('models_loaded', False)} ({models_n} active)")
            print(f"  - Samples cached  : {checks.get('samples_cached', False)} ({samples_n} cached)")
            print(f"  - Telemetry SQLite: {checks.get('telemetry_db', False)}")

        v_body = report["details"].get("version", {}).get("body")
        if isinstance(v_body, dict):
            print("Version   (/api/version):")
            print(f"  - Application     : {v_body.get('app_name')} v{v_body.get('version')}")
            print(f"  - CAD Engine      : {v_body.get('cad_engine')}")
            print(f"  - Python Runtime  : {v_body.get('python_version')}")
            print(f"  - Uptime          : {v_body.get('uptime_seconds', 0.0):.1f}s")

        m_details = report["details"].get("metrics")
        if isinstance(m_details, dict) and m_details.get("ok"):
            m_data = m_details.get("metrics", {})
            print("Metrics   (/metrics)   :")
            print(f"  - Active models   : {m_data.get('shapeops_registered_models_total', 'N/A')}")
            print(f"  - Process uptime  : {m_data.get('shapeops_process_uptime_seconds', 'N/A')}s")

        s_details = report["details"].get("samples")
        if isinstance(s_details, dict) and s_details.get("ok"):
            s_list = s_details.get("body", [])
            print("Samples   (/api/samples):")
            for item in s_list:
                if isinstance(item, dict):
                    print(f"  - {item.get('id')}: {item.get('name')}")

        d_details = report["details"].get("drills")
        if isinstance(d_details, dict) and d_details.get("ok"):
            d_body = d_details.get("body", {})
            d_list = d_body.get("drills", [])
            print("Drills    (/api/operations):")
            print(f"  - Completed drills: {len(d_list)}")
            if d_list:
                latest = d_list[0]
                stat = "PASS" if latest.get("passed") else "FAIL"
                dur = latest.get("duration_ms", 0.0)
                print(f"  - Latest drill    : {stat} ({dur:.1f}ms, {len(latest.get('checks', []))} checks)")

    if not is_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
