# Inference response contract

Both sample and upload inference use the same strict Pydantic `InferenceResult` response model, documented in `/openapi.json` and `/docs`. Existing JSON field names and original CAD face IDs are preserved. Face outputs include real class probabilities, primary/alternate confidence, triangle positions and comparison flags; internal numerical feature vectors are forbidden in the public response.

Validation rejects nonfinite values, out-of-range confidences, malformed triangle arrays, reordered/missing face IDs, inconsistent probability/summary values and contradictory comparison metadata. It enforces the existing face/mesh/extent budgets. Probabilities are checked for internal numerical consistency; this does not calibrate them or establish industrial accuracy. Source labels remain sample/upload. Registry/history, telemetry and operations contracts are described below.

The result is validated before recording successful telemetry. Invalid internal output records an internal failure and raises a generic server error, without sending validation payload details to the client. Existing unsupported-input validation remains separate. Latency metadata retains its existing inference timing boundary; client/serialization latency is not claimed.

Implementation references: [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/), [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/) and [strict/finite/extra configuration](https://docs.pydantic.dev/latest/api/config/). Behavior is verified against the repository's pinned FastAPI/Pydantic versions; upstream latest documentation is not treated as proof that an example passed locally.


## Telemetry and isolated operations

Telemetry and Prometheus now share a validated TelemetryResponse window. Counts must match the retained rows, flags/probabilities/timings must be finite and bounded, and successful-request percentile/OOD metrics remain null when no successful requests exist. Populated windows require consistent percentile ordering and OOD rate. Existing retained-window gauges and JSON field names remain unchanged; this is not lifetime production telemetry.

OperationsResponse and DrillResult document the actual local-only state and isolated check results. Drill summaries must match their executed checks and validate before SQLite persistence. The current response contract allows no production release history and retains Not deployed status; promotion remains independently blocked with HTTP 403. This schema is not an implementation of authenticated administrative controls. Stored drill results are validated when read; corrupt/partial records fail instead of being silently filled with fabricated defaults. The old retention test fixture was updated to a complete, explicitly labeled unit drill record.


## Model registry and completed training history

Registry entries now expose RegisteredModel, and completed history exposes TrainingHistory/TrainingRunDetail in OpenAPI. The manifest contract preserves every existing field, including runtime parameters as JSON values, package/tree/estimator/dataset/source/environment digests, real evaluation metrics, limitations and pure release gates. It checks finite bounded metrics, positive evaluation/training row counts, unique supported class/feature labels and strict gate booleans. Stable/candidate describes local model roles, not authorization to release.

History validates UUID-format run identities, finite chronological timestamps, one to sixteen unique model references/manifests per completed run and at most one hundred unique summary runs. Current registry entries carry run_id; immutable historical manifests retain their original shape without that later association field. Both history summary and detail verify journal manifest hashes and model identity bindings through read-only SQLite transactions. Invalid internal records fail response validation rather than receiving invented defaults. Missing run details still return 404 and invalid query limits return 422. This work adds no failed-run lifecycle, cloud durability, external estimator loading or production promotion.
