# Inference response contract

Both sample and upload inference use the same strict Pydantic `InferenceResult` response model, documented in `/openapi.json` and `/docs`. Existing JSON field names and original CAD face IDs are preserved. Face outputs include real class probabilities, primary/alternate confidence, triangle positions and comparison flags; internal numerical feature vectors are forbidden in the public response.

Validation rejects nonfinite values, out-of-range confidences, malformed triangle arrays, reordered/missing face IDs, inconsistent probability/summary values and contradictory comparison metadata. It enforces the existing face/mesh/extent budgets. Probabilities are checked for internal numerical consistency; this does not calibrate them or establish industrial accuracy. Source labels remain sample/upload. Typed models for the remaining registry, telemetry and operations APIs are still open.

The result is validated before recording successful telemetry. Invalid internal output records an internal failure and raises a generic server error, without sending validation payload details to the client. Existing unsupported-input validation remains separate. Latency metadata retains its existing inference timing boundary; client/serialization latency is not claimed.

Implementation references: [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/), [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/) and [strict/finite/extra configuration](https://docs.pydantic.dev/latest/api/config/). Behavior is verified against the repository's pinned FastAPI/Pydantic versions; upstream latest documentation is not treated as proof that an example passed locally.
