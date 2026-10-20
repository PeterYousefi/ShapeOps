"""Synthetic contract fixtures; never inserted into live operational records."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from backend.responses import TelemetryResponse, DrillResult, OperationsResponse


def empty():
    return {"origin": "Unit fixture", "total": 0, "successful": 0, "failed": 0,
            "p50": None, "p95": None, "ood_rate": None, "requests": [], "throughput_per_minute": 0}


def test_unavailable_metrics_remain_null_and_failed_only_window_is_truthful():
    assert TelemetryResponse.model_validate(empty()).model_dump() == empty()
    failed = empty()
    failed.update(total=1, failed=1, throughput_per_minute=1, requests=[{
        "id": "unit-fixture", "at": 1.0, "source": "sample", "model": "unit-fixture",
        "success": 0, "latency": 2.0, "parse": 0.0, "execution": 1.0, "faces": 0,
        "confidence": 0.0, "ood": 0, "error": "validation"}])
    assert TelemetryResponse.model_validate(failed).p95 is None
    successful = deepcopy(failed)
    successful.update(successful=1, failed=0, p50=2.0, p95=2.0, ood_rate=0.0)
    successful["requests"][0].update(success=1, error="", faces=1, confidence=.9)
    assert TelemetryResponse.model_validate(successful).successful == 1
    successful["ood_rate"] = .5
    with pytest.raises(ValidationError):
        TelemetryResponse.model_validate(successful)


@pytest.mark.parametrize("field,value", [("total", 1), ("successful", 1), ("failed", 1),
    ("p50", 0.0), ("p95", float("nan")), ("ood_rate", 0.0), ("throughput_per_minute", 1),
    ("raw_cad", "must never leak")])
def test_inconsistent_or_nonfinite_telemetry_is_rejected(field, value):
    data = empty()
    data[field] = value
    with pytest.raises(ValidationError):
        TelemetryResponse.model_validate(data)


def drill():
    return {"id": "a" * 12, "at": 1.0, "passed": True, "duration_ms": 1.0,
            "checks": [{"name": "Unit fixture", "passed": True}],
            "scope": "Isolated adapter test. No deployment or production mutation."}


def test_drill_summary_matches_checks_and_operation_has_no_production_history():
    assert DrillResult.model_validate(drill()).passed
    invalid = drill()
    invalid["checks"][0]["passed"] = False
    with pytest.raises(ValidationError):
        DrillResult.model_validate(invalid)
    invalid["passed"] = False
    assert not DrillResult.model_validate(invalid).passed
    operation = {"active": "unit-primary", "candidate": "unit-alternate", "environment": "Local development",
                 "production": "Not deployed", "release_history": [], "drills": [drill()], "promotion": "Blocked"}
    assert OperationsResponse.model_validate(operation).release_history == []
    for field, value in (("production", "Deployed"), ("release_history", [{"invented": True}])):
        modified = {**operation, field: value}
        with pytest.raises(ValidationError):
            OperationsResponse.model_validate(modified)


@pytest.mark.parametrize("field,value", [("duration_ms", -1.0), ("duration_ms", float("inf")),
    ("checks", []), ("scope", "Production mutation")])
def test_invalid_drill_results_fail_before_persistence(field, value):
    data = drill()
    data[field] = value
    with pytest.raises(ValidationError):
        DrillResult.model_validate(data)
