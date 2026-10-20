"""Public engineering API contracts; preserve real geometry and operational state."""
import math
from typing import Annotated, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.contracts import Surface

Nonnegative = Annotated[float, Field(ge=0)]
Probability = Annotated[float, Field(ge=0, le=1)]


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class FacePrediction(OutputModel):
    id: Annotated[int, Field(ge=0)]
    surface: Surface
    prediction: Surface
    confidence: Probability
    probabilities: Annotated[dict[Surface, Probability], Field(min_length=1)]
    comparison_confidence: Probability | None
    area: Nonnegative
    edges: Annotated[int, Field(ge=0)]
    positions: Annotated[list[float], Field(min_length=9, max_length=900000)]
    candidate: Surface | None
    disagreement: bool

    @model_validator(mode="after")
    def consistent_prediction(self) -> Self:
        if (len(self.positions) % 9
                or not math.isclose(sum(self.probabilities.values()), 1, abs_tol=1e-6)
                or self.prediction not in self.probabilities
                or not math.isclose(self.confidence, max(self.probabilities.values()), abs_tol=1e-8)
                or not math.isclose(self.confidence, self.probabilities[self.prediction], abs_tol=1e-8)):
            raise ValueError("Inconsistent face mesh or primary probabilities")
        if ((self.candidate is None) != (self.comparison_confidence is None)
                or self.disagreement != (self.candidate is not None and self.candidate != self.prediction)):
            raise ValueError("Inconsistent alternate prediction")
        return self


class OODContribution(OutputModel):
    feature: str
    deviation: Nonnegative


class InferenceResult(OutputModel):
    faces: Annotated[list[FacePrediction], Field(min_length=1, max_length=600)]
    face_count: Annotated[int, Field(ge=1, le=600)]
    edge_count: Annotated[int, Field(ge=0)]
    volume: Nonnegative
    bounds: Annotated[list[Annotated[float, Field(ge=0, le=10000)]], Field(min_length=3, max_length=3)]
    name: str
    source: Literal["sample", "upload"]
    trace_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    model: str
    checksum: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    latency_ms: Nonnegative
    parse_ms: Nonnegative
    execution_ms: Nonnegative
    confidence: Probability
    ood: bool
    ood_score: float
    ood_contributions: list[OODContribution]
    disagreements: Annotated[int, Field(ge=0)]
    comparison_model: str | None

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if (len(self.faces) != self.face_count
                or [face.id for face in self.faces] != list(range(self.face_count))
                or sum(len(face.positions) for face in self.faces) > 4500000
                or self.disagreements != sum(face.disagreement for face in self.faces)
                or not math.isclose(self.confidence, sum(face.confidence for face in self.faces) / self.face_count, abs_tol=1e-6)
                or self.ood != (self.ood_score > 0)):
            raise ValueError("Inconsistent inference geometry or summary")
        compared = self.comparison_model is not None
        if (self.comparison_model == self.model
                or any((face.candidate is not None) != compared for face in self.faces)):
            raise ValueError("Inconsistent comparison model metadata")
        return self


class RequestRecord(OutputModel):
    id: str
    at: Nonnegative
    source: Literal["sample", "upload"]
    model: str
    success: Annotated[int, Field(ge=0, le=1)]
    latency: Nonnegative
    parse: Nonnegative
    execution: Nonnegative
    faces: Annotated[int, Field(ge=0, le=600)]
    confidence: Probability
    ood: Annotated[int, Field(ge=0, le=1)]
    error: str


class TelemetryResponse(OutputModel):
    origin: str
    total: Annotated[int, Field(ge=0, le=1000)]
    successful: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    p50: Nonnegative | None
    p95: Nonnegative | None
    ood_rate: Probability | None
    requests: Annotated[list[RequestRecord], Field(max_length=1000)]
    throughput_per_minute: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def consistent_window(self) -> Self:
        successes = sum(row.success for row in self.requests)
        if (self.total != len(self.requests) or self.successful != successes
                or self.failed != self.total - successes or self.throughput_per_minute > self.total):
            raise ValueError("Telemetry totals do not match retained requests")
        if successes == 0:
            if any(value is not None for value in (self.p50, self.p95, self.ood_rate)):
                raise ValueError("Unavailable successful-request metrics must be null")
        elif (self.p50 is None or self.p95 is None or self.ood_rate is None
                or self.p50 > self.p95
                or not math.isclose(self.ood_rate, sum(row.ood for row in self.requests if row.success) / successes, abs_tol=1e-8)):
            raise ValueError("Inconsistent successful-request metrics")
        return self


class DrillCheck(OutputModel):
    name: str
    passed: bool


class DrillResult(OutputModel):
    id: Annotated[str, Field(pattern=r"^[a-f0-9]{12}$")]
    at: Nonnegative
    passed: bool
    checks: Annotated[list[DrillCheck], Field(min_length=1, max_length=32)]
    duration_ms: Nonnegative
    scope: Literal["Isolated adapter test. No deployment or production mutation."]

    @model_validator(mode="after")
    def consistent_checks(self) -> Self:
        if self.passed != all(check.passed for check in self.checks):
            raise ValueError("Drill summary does not match executed checks")
        return self


class OperationsResponse(OutputModel):
    active: str
    candidate: str
    environment: Literal["Local development"]
    production: Literal["Not deployed"]
    release_history: Annotated[list[dict], Field(max_length=0)]
    drills: Annotated[list[DrillResult], Field(max_length=20)]
    promotion: str
