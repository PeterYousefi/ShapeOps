"""Window-level CAD geometry distribution drift analysis and auditable report generation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time
from typing import Annotated, Literal, Self, Sequence
import numpy as np
from pydantic import Field, model_validator

from backend.drift import FEATURES, vector, reference_identity
from backend.responses import Digest, Nonnegative, OutputModel, Probability, DriftObservation
from backend.retention import REQUEST_MAX_AGE_SECONDS

MAX_REPORT_BYTES = 256 * 1024
MAX_OBSERVATIONS = 1000
MAX_OBSERVATION_BYTES = 16 * 1024


def kolmogorov_smirnov_distance(sample1: Sequence[float], sample2: Sequence[float]) -> float:
    """Compute the two-sample Kolmogorov-Smirnov distance statistic between two 1D samples."""
    n1, n2 = len(sample1), len(sample2)
    if n1 == 0 or n2 == 0:
        raise ValueError("Samples must not be empty for KS distance")
    s1 = np.sort(np.asarray(sample1, dtype=float))
    s2 = np.sort(np.asarray(sample2, dtype=float))
    if not np.isfinite(s1).all() or not np.isfinite(s2).all():
        raise ValueError("Samples must contain only finite numbers")
    all_points = np.unique(np.concatenate([s1, s2]))
    cdf1 = np.searchsorted(s1, all_points, side="right") / n1
    cdf2 = np.searchsorted(s2, all_points, side="right") / n2
    d = float(np.max(np.abs(cdf1 - cdf2)))
    return max(0.0, min(1.0, d))


class FeatureDistribution(OutputModel):
    name: str
    observed_count: Annotated[int, Field(ge=1)]
    observed_mean: float
    observed_std: Nonnegative
    observed_min: float
    observed_q25: float
    observed_median: float
    observed_q75: float
    observed_max: float
    reference_count: Annotated[int, Field(ge=1)]
    reference_mean: float
    reference_std: Nonnegative
    reference_scale: Annotated[float, Field(gt=0)]
    standardized_shift: Nonnegative
    ks_distance: Annotated[float, Field(ge=0, le=1)]
    alert: bool

    @model_validator(mode="after")
    def consistent_quantiles(self) -> Self:
        if any(value < 0 or not math.isfinite(value) for value in (
            self.observed_mean, self.observed_min, self.observed_q25, self.observed_median,
            self.observed_q75, self.observed_max, self.reference_mean, self.reference_std,
            self.reference_scale, self.standardized_shift, self.ks_distance,
        )):
            raise ValueError(f"Invalid nonnegative geometry statistics for feature {self.name}")
        if not (self.observed_min <= self.observed_q25 <= self.observed_median <= self.observed_q75 <= self.observed_max):
            raise ValueError(f"Inconsistent observed quantiles for feature {self.name}")
        return self


class WindowDriftReport(OutputModel):
    schema_version: Literal[1]
    origin: Literal["Window-level CAD geometry distribution drift analysis; screening only"]
    analyzed_at: Nonnegative
    window_cutoff_at: Nonnegative
    total_observations: Annotated[int, Field(ge=1, le=MAX_OBSERVATIONS)]
    window_started_at: Nonnegative
    window_ended_at: Nonnegative
    reference_parts: Annotated[int, Field(ge=1, le=100)]
    reference_id: Digest
    shift_threshold: Annotated[float, Field(gt=0)]
    ks_threshold: Annotated[float, Field(ge=0, le=1)]
    drift_detected: bool
    flagged_features: list[str]
    sample_count: Annotated[int, Field(ge=0)]
    upload_count: Annotated[int, Field(ge=0)]
    ood_count: Annotated[int, Field(ge=0)]
    ood_rate: Probability
    features: dict[str, FeatureDistribution]

    @model_validator(mode="after")
    def consistent_summary(self) -> Self:
        if set(self.features) != set(FEATURES) or any(self.features[name].name != name for name in self.features):
            raise ValueError("Feature names do not match the CAD drift contract")
        if self.window_cutoff_at > self.analyzed_at:
            raise ValueError("Window cutoff is after analysis time")
        if self.window_started_at < self.window_cutoff_at:
            raise ValueError("Window contains observations older than its declared cutoff")
        if self.window_ended_at > self.analyzed_at:
            raise ValueError("Window contains observations newer than analysis time")
        if self.window_ended_at < self.window_started_at:
            raise ValueError("Window end timestamp precedes window start timestamp")
        if self.sample_count + self.upload_count != self.total_observations:
            raise ValueError("Source counts do not match total observations")
        if self.ood_count > self.total_observations:
            raise ValueError("OOD count exceeds total observations")
        expected_ood_rate = self.ood_count / self.total_observations
        if not math.isclose(self.ood_rate, expected_ood_rate, abs_tol=1e-8):
            raise ValueError("OOD rate is inconsistent with OOD count and total observations")
        expected_flagged = [name for name, f in self.features.items() if f.alert]
        if self.flagged_features != expected_flagged:
            raise ValueError("Flagged features list does not match feature alert states")
        if self.drift_detected != (len(self.flagged_features) > 0):
            raise ValueError("drift_detected must equal boolean presence of flagged features")
        for f in self.features.values():
            if f.observed_count != self.total_observations:
                raise ValueError("Feature observation count does not match total observations")
            if f.reference_count != self.reference_parts:
                raise ValueError("Feature reference count does not match reference parts")
        return self


def analyze_distribution(
    observations: Sequence[DriftObservation],
    reference_samples: dict[str, dict] | None = None,
    *,
    shift_threshold: float = 3.0,
    ks_threshold: float = 0.5,
    analyzed_at: float | None = None,
    window_cutoff_at: float | None = None,
) -> dict:
    if not observations:
        raise ValueError("Observations sequence must not be empty")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValueError(f"Observations count {len(observations)} exceeds maximum budget {MAX_OBSERVATIONS}")
    if not math.isfinite(shift_threshold) or shift_threshold <= 0:
        raise ValueError("Shift threshold must be a finite positive number")
    if not math.isfinite(ks_threshold) or not 0 <= ks_threshold <= 1:
        raise ValueError("KS threshold must be a finite probability between 0 and 1")

    now = time.time() if analyzed_at is None else analyzed_at
    if not math.isfinite(now) or now < 0:
        raise ValueError("Invalid analyzed_at timestamp")

    if reference_samples is None:
        from backend.cad import SAMPLES, describe, sample_shape
        reference_samples = {s["id"]: describe(sample_shape(s["id"])) for s in SAMPLES}

    if not reference_samples:
        raise ValueError("Reference samples dictionary must not be empty")

    ref_keys = sorted(reference_samples)
    ref_vectors = [vector(reference_samples[k]) for k in ref_keys]
    expected_reference_id = reference_identity(reference_samples)
    if any(obs.reference_id != expected_reference_id for obs in observations):
        raise ValueError("Saved observation reference identity does not match the analysis reference")
    if any(obs.reference_parts != len(reference_samples) for obs in observations):
        raise ValueError("Saved observation reference population does not match the analysis reference")
    ref_matrix = np.asarray(ref_vectors, dtype=float)
    if ref_matrix.ndim != 2 or not len(ref_matrix) or not np.isfinite(ref_matrix).all():
        raise ValueError("Reference geometry matrix must be finite and non-empty")

    ref_means = ref_matrix.mean(axis=0)
    ref_stds = ref_matrix.std(axis=0)
    ref_scales = np.maximum(ref_stds, np.maximum(abs(ref_means) * 0.05, 1e-6))

    reference_id = expected_reference_id

    reference_ids = {obs.reference_id for obs in observations}
    reference_counts = {obs.reference_parts for obs in observations}
    feature_sets = [tuple(feature.name for feature in obs.features) for obs in observations]
    if len(reference_ids) != 1 or len(reference_counts) != 1:
        raise ValueError("Observations use incompatible reference identities or populations")
    if any(names != tuple(FEATURES) for names in feature_sets):
        raise ValueError("Observation features do not match the analyzed CAD feature contract")
    if any(obs.threshold != 3 for obs in observations):
        raise ValueError("Observation screening methods have incompatible thresholds")
    timestamps = [obs.at for obs in observations]
    cutoff = min(timestamps) if window_cutoff_at is None else window_cutoff_at
    if not math.isfinite(cutoff) or cutoff < 0 or cutoff > now:
        raise ValueError("Invalid window cutoff timestamp")
    if min(timestamps) < cutoff or max(timestamps) > now:
        raise ValueError("Observations fall outside the declared seven-day analysis window")
    ood_flags = [obs.ood for obs in observations]

    feature_results: dict[str, dict] = {}
    flagged: list[str] = []

    for idx, name in enumerate(FEATURES):
        obs_vals = [obs.features[idx].value for obs in observations]
        obs_arr = np.asarray(obs_vals, dtype=float)
        if not np.isfinite(obs_arr).all():
            raise ValueError(f"Observed values for {name} contain non-finite numbers")

        obs_mean = float(obs_arr.mean())
        obs_std = float(obs_arr.std())
        obs_min = float(obs_arr.min())
        obs_q25 = float(np.percentile(obs_arr, 25))
        obs_median = float(np.median(obs_arr))
        obs_q75 = float(np.percentile(obs_arr, 75))
        obs_max = float(obs_arr.max())

        ref_vals = ref_matrix[:, idx].tolist()
        r_mean = float(ref_means[idx])
        r_std = float(ref_stds[idx])
        r_scale = float(ref_scales[idx])

        shift = abs(obs_mean - r_mean) / r_scale
        if not math.isfinite(shift):
            raise ValueError(f"Standardized shift for {name} is not finite")
        ks_d = kolmogorov_smirnov_distance(obs_vals, ref_vals)
        alert = bool(shift >= shift_threshold or ks_d >= ks_threshold)
        if alert:
            flagged.append(name)

        feature_results[name] = {
            "name": name,
            "observed_count": len(observations),
            "observed_mean": obs_mean,
            "observed_std": obs_std,
            "observed_min": obs_min,
            "observed_q25": obs_q25,
            "observed_median": obs_median,
            "observed_q75": obs_q75,
            "observed_max": obs_max,
            "reference_count": len(ref_keys),
            "reference_mean": r_mean,
            "reference_std": r_std,
            "reference_scale": r_scale,
            "standardized_shift": float(shift),
            "ks_distance": float(ks_d),
            "alert": alert,
        }

    ood_count = sum(ood_flags)
    report_dict = {
        "schema_version": 1,
        "origin": "Window-level CAD geometry distribution drift analysis; screening only",
        "analyzed_at": now,
        "window_cutoff_at": cutoff,
        "total_observations": len(observations),
        "window_started_at": min(timestamps),
        "window_ended_at": max(timestamps),
        "reference_parts": len(ref_keys),
        "reference_id": reference_id,
        "shift_threshold": shift_threshold,
        "ks_threshold": ks_threshold,
        "drift_detected": len(flagged) > 0,
        "flagged_features": flagged,
        "sample_count": sum(obs.source == "sample" for obs in observations),
        "upload_count": sum(obs.source == "upload" for obs in observations),
        "ood_count": ood_count,
        "ood_rate": float(ood_count / len(observations)),
        "features": feature_results,
    }

    # Validate against strict OutputModel contract
    validated = WindowDriftReport.model_validate(report_dict)
    return validated.model_dump()


def evaluate_database(
    database: Path,
    output: Path,
    *,
    limit: int = MAX_OBSERVATIONS,
    shift_threshold: float = 3.0,
    ks_threshold: float = 0.5,
    reference_samples: dict[str, dict] | None = None,
    now: float | None = None,
) -> dict:
    try:
        mode = database.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError("Database path must be an existing regular file")
    except OSError:
        raise ValueError("Database path must be an existing regular file") from None
    if not 1 <= limit <= MAX_OBSERVATIONS:
        raise ValueError(f"Limit must be between 1 and {MAX_OBSERVATIONS}")

    captured_at = time.time() if now is None else now
    if not math.isfinite(captured_at) or captured_at < 0:
        raise ValueError("Invalid analysis timestamp")

    db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        table_exists = bool(
            db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='drift_observations'").fetchone()
        )
        if not table_exists:
            raise ValueError("Table drift_observations does not exist in database")
        rows = db.execute(
            "SELECT id, at, CASE WHEN length(CAST(result AS BLOB)) <= ? THEN result ELSE NULL END AS bounded_result "
            "FROM drift_observations WHERE at >= ? AND at <= ? ORDER BY at DESC, id DESC LIMIT ?",
            (MAX_OBSERVATION_BYTES, max(0.0, captured_at - REQUEST_MAX_AGE_SECONDS), captured_at, limit),
        ).fetchall()
        if not rows:
            raise ValueError("No drift observations recorded in the seven-day window")
        if any(row["bounded_result"] is None for row in rows):
            raise ValueError("Saved drift observation exceeds the 16 KiB input budget")
        observations = [DriftObservation.model_validate_json(row["bounded_result"]) for row in rows]
        if any(row["id"] != obs.id or row["at"] != obs.at for row, obs in zip(rows, observations)):
            raise ValueError("Saved drift observation does not match its indexed identity and timestamp")
    finally:
        db.close()

    report = analyze_distribution(
        observations,
        reference_samples=reference_samples,
        shift_threshold=shift_threshold,
        ks_threshold=ks_threshold,
        analyzed_at=captured_at,
        window_cutoff_at=max(0.0, captured_at - REQUEST_MAX_AGE_SECONDS),
    )
    payload = json.dumps(report, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Drift report exceeds maximum byte budget of 256 KiB")

    output_dir = output.parent
    if not output_dir.exists():
        raise ValueError("Output directory does not exist")

    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            staging.unlink(missing_ok=True)
            raise

    try:
        os.link(staging, output)
    finally:
        staging.unlink(missing_ok=True)

    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "observations": len(observations),
        "drift_detected": report["drift_detected"],
        "flagged_features": report["flagged_features"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="SQLite database path")
    parser.add_argument("--output", type=Path, required=True, help="Destination report JSON path")
    parser.add_argument("--limit", type=int, default=MAX_OBSERVATIONS, help="Max observations (1..1000)")
    parser.add_argument("--shift-threshold", type=float, default=3.0, help="Standardized shift threshold")
    parser.add_argument("--ks-threshold", type=float, default=0.5, help="KS distance threshold (0..1)")
    args = parser.parse_args()

    try:
        result = evaluate_database(
            args.database,
            args.output,
            limit=args.limit,
            shift_threshold=args.shift_threshold,
            ks_threshold=args.ks_threshold,
        )
    except (OSError, sqlite3.Error, ValueError) as err:
        parser.exit(1, f"Drift analysis failed: {err}\n")

    print(json.dumps(result))


if __name__ == "__main__":
    main()
