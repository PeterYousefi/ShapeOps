"""Measure real cached-sample inference, deliberately bounded to ten requests."""

import json, platform, statistics, time
from pathlib import Path
import httpx

rows = []
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=40) as client:
    for model in ["surface-rf-v1", "surface-et-v2"]:
        for sample in ["bracket", "flange", "housing", "shaft", "manifold"]:
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
                    "server_ms": data["latency_ms"],
                    "execution_ms": data["execution_ms"],
                    "faces": data["face_count"],
                    "mean_confidence": data["confidence"],
                    "disagreements": data["disagreements"],
                }
            )
            time.sleep(0.1)
report = {
    "conditions": {
        "platform": platform.platform(),
        "processor": platform.machine(),
        "python": platform.python_version(),
        "concurrency": 1,
        "sample_geometry": "preprocessed and cached at startup",
        "scope": "Ten real local sample requests; not upload parsing or cloud performance.",
    },
    "requests": rows,
    "median_client_ms": statistics.median(r["client_ms"] for r in rows),
    "max_client_ms": max(r["client_ms"] for r in rows),
}
Path("artifacts/benchmark.json").write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "requests": len(rows),
            "median_client_ms": report["median_client_ms"],
            "max_client_ms": report["max_client_ms"],
        },
        indent=2,
    )
)
