#!/usr/bin/env python3
"""Measure real cached-sample inference latency and execution characteristics."""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

DEFAULT_MODELS = ["surface-rf-v1", "surface-et-v2"]
DEFAULT_SAMPLES = ["bracket", "flange", "housing", "shaft", "manifold"]


def run_benchmark(
    base_url: str = "http://127.0.0.1:8000",
    models: list[str] | None = None,
    samples: list[str] | None = None,
    delay: float = 0.1,
    timeout: float = 40.0,
) -> dict[str, Any]:
    """Execute bounded inference benchmark against live or test server."""
    target_models = models or DEFAULT_MODELS
    target_samples = samples or DEFAULT_SAMPLES
    rows: list[dict[str, Any]] = []

    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        for model in target_models:
            for sample in target_samples:
                started = time.perf_counter()
                response = client.post(
                    "/api/inference/sample",
                    json={"sample": sample, "model": model, "compare": True},
                )
                response.raise_for_status()
                data = response.json()
                rows.append(
                    {
                        "model": model,
                        "sample": sample,
                        "client_ms": (time.perf_counter() - started) * 1000,
                        "server_ms": data.get("latency_ms", 0.0),
                        "execution_ms": data.get("execution_ms", 0.0),
                        "faces": data.get("face_count", 0),
                        "mean_confidence": data.get("confidence", 0.0),
                        "disagreements": data.get("disagreements", 0),
                    }
                )
                if delay > 0:
                    time.sleep(delay)

    client_times = [r["client_ms"] for r in rows]
    report: dict[str, Any] = {
        "conditions": {
            "platform": platform.platform(),
            "processor": platform.machine(),
            "python": platform.python_version(),
            "concurrency": 1,
            "sample_geometry": "preprocessed and cached at startup",
            "scope": f"{len(rows)} real local sample requests; not upload parsing or cloud performance.",
        },
        "requests": rows,
        "median_client_ms": statistics.median(client_times) if client_times else 0.0,
        "max_client_ms": max(client_times) if client_times else 0.0,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure real cached-sample inference latency."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the ShapeOps service (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model IDs to benchmark (default: surface-rf-v1 surface-et-v2)",
    )
    parser.add_argument(
        "--samples",
        nargs="+",
        default=DEFAULT_SAMPLES,
        help="Sample part IDs to benchmark (default: bracket flange housing shaft manifold)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Pause between requests in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=40.0,
        help="Per-request HTTP timeout in seconds (default: 40.0)",
    )
    parser.add_argument(
        "--output",
        default="artifacts/benchmark.json",
        help="Output JSON artifact path (default: artifacts/benchmark.json)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save benchmark report to disk",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print full report JSON to stdout",
    )

    args = parser.parse_args(argv)

    try:
        report = run_benchmark(
            base_url=args.base_url,
            models=args.models,
            samples=args.samples,
            delay=args.delay,
            timeout=args.timeout,
        )
    except (httpx.HTTPError, OSError, ValueError) as exc:
        print(f"Benchmark error querying {args.base_url}: {exc}", file=sys.stderr)
        return 1

    if not args.no_save and args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2))

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(
            json.dumps(
                {
                    "requests": len(report["requests"]),
                    "median_client_ms": report["median_client_ms"],
                    "max_client_ms": report["max_client_ms"],
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
