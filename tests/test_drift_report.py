import json
import sqlite3
import subprocess
import sys
import uuid
import pytest
from pydantic import ValidationError

from backend.drift import FEATURES, vector
from backend.drift_report import (
    FeatureDistribution,
    WindowDriftReport,
    analyze_distribution,
    evaluate_database,
    kolmogorov_smirnov_distance,
)
from backend.responses import DriftObservation


def test_kolmogorov_smirnov_distance_properties():
    # Empty inputs
    with pytest.raises(ValueError, match="empty"):
        kolmogorov_smirnov_distance([], [1.0])
    with pytest.raises(ValueError, match="empty"):
        kolmogorov_smirnov_distance([1.0], [])

    # Non-finite inputs
    with pytest.raises(ValueError, match="finite"):
        kolmogorov_smirnov_distance([1.0, float("nan")], [1.0])
    with pytest.raises(ValueError, match="finite"):
        kolmogorov_smirnov_distance([1.0], [float("inf")])

    # Identical samples
    s1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert kolmogorov_smirnov_distance(s1, s1) == 0.0

    # Non-overlapping samples
    assert kolmogorov_smirnov_distance([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]) == 1.0

    # Partially overlapping
    d = kolmogorov_smirnov_distance([1.0, 3.0, 5.0], [2.0, 4.0, 6.0])
    assert 0.0 < d < 1.0
    assert d == pytest.approx(1 / 3, abs=1e-6)


def _mock_reference_samples() -> dict[str, dict]:
    return {
        "part_a": {
            "face_count": 6,
            "edge_count": 12,
            "bounds": [10.0, 20.0, 30.0],
            "faces": [{"area": 10.0, "surface": "Planar"}] * 6,
        },
        "part_b": {
            "face_count": 8,
            "edge_count": 16,
            "bounds": [12.0, 22.0, 32.0],
            "faces": [{"area": 12.0, "surface": "Cylindrical"}] * 8,
        },
    }


def _make_observation(
    trace_id: str,
    at: float,
    values: list[float],
    *,
    ref_samples: dict[str, dict],
    ood: bool = False,
    ood_score: float = -0.1,
    threshold: float = 3.0,
    reference_id: str = "a" * 64,
) -> DriftObservation:
    ref_vectors = [vector(ref_samples[k]) for k in sorted(ref_samples)]
    import numpy as np

    matrix = np.asarray(ref_vectors, dtype=float)
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    scales = np.maximum(stds, np.maximum(abs(means) * 0.05, 1e-6))

    features = [
        {
            "name": name,
            "value": float(v),
            "reference_mean": float(m),
            "reference_scale": float(s),
            "deviation": float(abs(v - m) / s),
        }
        for name, v, m, s in zip(FEATURES, values, means, scales)
    ]
    warning = any(f["deviation"] >= threshold for f in features)
    return DriftObservation.model_validate(
        {
            "id": trace_id,
            "at": at,
            "source": "sample",
            "model": "surface-rf-v1",
            "reference_id": reference_id,
            "reference_scope": "Owned procedural sample geometries; screening only",
            "reference_parts": len(ref_samples),
            "threshold": threshold,
            "warning": warning,
            "ood_score": ood_score,
            "ood": ood,
            "features": features,
        }
    )


def test_schema_validators():
    # Inconsistent quantiles in FeatureDistribution
    with pytest.raises(ValidationError):
        FeatureDistribution(
            name="Face count",
            observed_count=10,
            observed_mean=5.0,
            observed_std=1.0,
            observed_min=6.0,  # min > median
            observed_q25=4.0,
            observed_median=5.0,
            observed_q75=6.0,
            observed_max=7.0,
            reference_count=2,
            reference_mean=5.0,
            reference_std=1.0,
            reference_scale=1.0,
            standardized_shift=0.0,
            ks_distance=0.1,
            alert=False,
        )

    # Inconsistent WindowDriftReport timestamps
    with pytest.raises(ValidationError):
        WindowDriftReport(
            schema_version=1,
            origin="Window-level CAD geometry distribution drift analysis; screening only",
            analyzed_at=100.0,
            total_observations=1,
            window_started_at=200.0,
            window_ended_at=100.0,  # ended < started
            reference_parts=1,
            reference_id="a" * 64,
            shift_threshold=3.0,
            ks_threshold=0.5,
            drift_detected=False,
            flagged_features=[],
            ood_count=0,
            ood_rate=0.0,
            features={},
        )


def test_analyze_distribution_baseline_and_drift():
    ref = _mock_reference_samples()
    vec_a = vector(ref["part_a"])
    vec_b = vector(ref["part_b"])

    # Baseline observations alternating between part_a and part_b
    baseline_obs = [
        _make_observation(
            uuid.uuid4().hex,
            100.0 + i,
            vec_a if i % 2 == 0 else vec_b,
            ref_samples=ref,
        )
        for i in range(10)
    ]
    result = analyze_distribution(baseline_obs, ref, shift_threshold=3.0, ks_threshold=0.5)
    assert result["total_observations"] == 10
    assert result["drift_detected"] is False
    assert result["flagged_features"] == []
    assert result["ood_count"] == 0
    assert result["ood_rate"] == 0.0

    # Shifted observations: 10x larger face count
    shifted_obs = [
        _make_observation(
            uuid.uuid4().hex,
            200.0 + i,
            [vec_a[0] * 10.0] + vec_a[1:],
            ref_samples=ref,
            ood=True,
            ood_score=0.8,
        )
        for i in range(10)
    ]
    shifted_result = analyze_distribution(shifted_obs, ref, shift_threshold=3.0, ks_threshold=0.5)
    assert shifted_result["drift_detected"] is True
    assert "Face count" in shifted_result["flagged_features"]
    assert shifted_result["ood_count"] == 10
    assert shifted_result["ood_rate"] == 1.0


def test_evaluate_database(tmp_path):
    ref = _mock_reference_samples()
    vec_a = vector(ref["part_a"])
    vec_b = vector(ref["part_b"])

    db_path = tmp_path / "telemetry.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE drift_observations (id TEXT PRIMARY KEY, at REAL NOT NULL, result TEXT NOT NULL)"
    )
    for i in range(4):
        obs = _make_observation(
            uuid.uuid4().hex,
            150.0 + i,
            vec_a if i % 2 == 0 else vec_b,
            ref_samples=ref,
        )
        conn.execute(
            "INSERT INTO drift_observations VALUES (?, ?, ?)",
            (obs.id, obs.at, obs.model_dump_json()),
        )
    conn.commit()
    conn.close()

    out_path = tmp_path / "report.json"
    summary = evaluate_database(db_path, out_path, reference_samples=ref)
    assert out_path.exists()
    assert summary["observations"] == 4
    assert summary["drift_detected"] is False
    assert "sha256" in summary
    assert summary["bytes"] > 0

    # Collision protection: target already exists
    collision_out = tmp_path / "collision.json"
    collision_out.write_text("existing")
    with pytest.raises(FileExistsError):
        evaluate_database(db_path, collision_out, reference_samples=ref)


def test_evaluate_database_failures(tmp_path):
    # Non-existent DB
    with pytest.raises(ValueError, match="regular file"):
        evaluate_database(tmp_path / "missing.sqlite", tmp_path / "report.json")

    # DB without drift_observations table
    empty_db = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(empty_db)
    conn.execute("CREATE TABLE dummy (id INT)")
    conn.commit()
    conn.close()
    with pytest.raises(ValueError, match="does not exist"):
        evaluate_database(empty_db, tmp_path / "report.json")

    # DB with drift_observations but empty
    no_rows_db = tmp_path / "no_rows.sqlite"
    conn = sqlite3.connect(no_rows_db)
    conn.execute(
        "CREATE TABLE drift_observations (id TEXT PRIMARY KEY, at REAL NOT NULL, result TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    with pytest.raises(ValueError, match="No drift observations"):
        evaluate_database(no_rows_db, tmp_path / "report.json")


def test_cli(tmp_path):
    # Note: CLI loads cad reference_samples by default, so we use genuine samples if available
    db_path = tmp_path / "telemetry.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE drift_observations (id TEXT PRIMARY KEY, at REAL NOT NULL, result TEXT NOT NULL)"
    )
    from backend.cad import SAMPLES, describe, sample_shape
    real_ref = {s["id"]: describe(sample_shape(s["id"])) for s in SAMPLES}
    v = vector(real_ref["flange"])
    obs = _make_observation(uuid.uuid4().hex, 150.0, v, ref_samples=real_ref)
    conn.execute(
        "INSERT INTO drift_observations VALUES (?, ?, ?)",
        (obs.id, obs.at, obs.model_dump_json()),
    )
    conn.commit()
    conn.close()

    out_path = tmp_path / "cli_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.drift_report",
            "--database",
            str(db_path),
            "--output",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["observations"] == 1
    assert out_path.exists()
