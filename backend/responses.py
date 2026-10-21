"""Public engineering API contracts; preserve real geometry and operational state."""
import math
from typing import Annotated, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
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


Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
RunIdentity = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class ReleaseGates(OutputModel):
    quality: bool
    compatibility: bool
    license: bool
    security: bool


class ModelManifest(OutputModel):
    id: Annotated[str, Field(min_length=1)]
    stage: Literal["stable", "candidate"]
    framework: str
    runtime: str
    algorithm: str
    parameters: dict[str, JsonValue]
    checksum: Digest
    package_checksum: Digest
    heldout_log_loss: Nonnegative
    dataset_hash: Digest
    license: str
    training_rows: Annotated[int, Field(ge=1)]
    evaluation_rows: Annotated[int, Field(ge=1)]
    accuracy: Probability
    macro_f1: Probability
    git_commit: str
    source_hash: Digest
    git_dirty: bool
    environment_hash: Digest
    classes: Annotated[list[Surface], Field(min_length=1)]
    features: Annotated[list[str], Field(min_length=1)]
    limitations: str
    gates: ReleaseGates
    package_id: Digest

    @model_validator(mode="after")
    def unique_labels(self) -> Self:
        if len(set(self.classes)) != len(self.classes) or len(set(self.features)) != len(self.features):
            raise ValueError("Model class and feature labels must be unique")
        return self


class RegisteredModel(ModelManifest):
    run_id: RunIdentity


class RunModelReference(OutputModel):
    model_id: Annotated[str, Field(min_length=1)]
    package_id: Digest


class TrainingRunSummary(OutputModel):
    id: RunIdentity
    started_at: Nonnegative
    completed_at: Nonnegative
    models: Annotated[list[RunModelReference], Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def consistent_run(self) -> Self:
        if self.completed_at < self.started_at or len({m.model_id for m in self.models}) != len(self.models):
            raise ValueError("Invalid training timestamps or duplicate model references")
        return self


class TrainingHistory(OutputModel):
    origin: Literal["Actual completed local baseline training runs"]
    runs: Annotated[list[TrainingRunSummary], Field(max_length=100)]

    @model_validator(mode="after")
    def unique_runs(self) -> Self:
        if len({run.id for run in self.runs}) != len(self.runs):
            raise ValueError("Duplicate training runs")
        return self


class TrainingRunDetail(OutputModel):
    id: RunIdentity
    started_at: Nonnegative
    completed_at: Nonnegative
    models: Annotated[list[ModelManifest], Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def consistent_run(self) -> Self:
        if self.completed_at < self.started_at or len({m.id for m in self.models}) != len(self.models):
            raise ValueError("Invalid training timestamps or duplicate model manifests")
        return self


class TrainingFailure(OutputModel):
    id: RunIdentity
    started_at: Nonnegative
    failed_at: Nonnegative
    category: Literal["validation", "storage", "execution"]

    @model_validator(mode="after")
    def chronological(self) -> Self:
        if self.failed_at < self.started_at:
            raise ValueError("Invalid failed training timestamps")
        return self


class TrainingFailureHistory(OutputModel):
    origin: Literal["Actual handled local baseline initialization failures"]
    failures: Annotated[list[TrainingFailure], Field(max_length=100)]


class CandidateJob(OutputModel):
    id: RunIdentity
    started_at: Nonnegative
    finished_at: Nonnegative | None = None
    status: Literal['running', 'succeeded', 'failed', 'timed_out', 'interrupted']
    scope: Literal['Isolated local procedural baseline candidate. No serving or production mutation.']
    candidate: RegisteredModel | None = None

    @model_validator(mode='after')
    def consistent_state(self) -> Self:
        if self.status == 'running':
            if self.finished_at is not None or self.candidate is not None:
                raise ValueError('Running job cannot have a terminal result')
        elif self.finished_at is None or self.finished_at < self.started_at:
            raise ValueError('Terminal job requires chronological finish time')
        if (self.status == 'succeeded') != (self.candidate is not None):
            raise ValueError('Only a successful job may contain a candidate')
        if self.candidate is not None and self.candidate.stage != 'candidate':
            raise ValueError('Job result must reference a candidate model')
        return self


class CandidateJobHistory(OutputModel):
    origin: Literal['Actual isolated local candidate jobs']
    jobs: Annotated[list[CandidateJob], Field(max_length=100)]


class DriftFeature(OutputModel):
    name: str
    value: Nonnegative
    reference_mean: Nonnegative
    reference_scale: Annotated[float, Field(gt=0)]
    deviation: Nonnegative

    @model_validator(mode='after')
    def consistent_deviation(self) -> Self:
        if not math.isclose(self.deviation, abs(self.value - self.reference_mean) / self.reference_scale, abs_tol=1e-8):
            raise ValueError('Drift feature deviation does not match reference')
        return self


class DriftObservation(OutputModel):
    id: RunIdentity
    at: Nonnegative
    source: Literal['sample', 'upload']
    model: str
    reference_id: Digest
    reference_scope: Literal['Owned procedural sample geometries; screening only']
    reference_parts: Annotated[int, Field(ge=1, le=100)]
    threshold: Annotated[float, Field(ge=3, le=3)]
    warning: bool
    ood_score: float
    ood: bool
    features: Annotated[list[DriftFeature], Field(min_length=1, max_length=20)]

    @model_validator(mode='after')
    def consistent_warning(self) -> Self:
        if (len({feature.name for feature in self.features}) != len(self.features)
                or self.warning != any(feature.deviation >= self.threshold for feature in self.features)
                or self.ood != (self.ood_score > 0)):
            raise ValueError('Drift observation summary is inconsistent')
        return self


class DriftHistory(OutputModel):
    origin: Literal['Actual retained local inference geometry screening']
    observations: Annotated[list[DriftObservation], Field(max_length=100)]
