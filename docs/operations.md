# Operations, SLOs and recovery

## Local health

`GET /api/health` confirms that startup completed. If unavailable, inspect the local process and Uvicorn logs. Initial startup generates models and samples. The UI reports unavailable service data instead of creating substitute traffic.

Actual inference failures are classified as validation errors or processing timeouts. Match `X-Request-ID` with JSON inference events and the request explorer. Never copy private CAD into logs or bug reports. Raw upload cleanup is tested on the genuine subprocess path.

## Incident drill

Operations → Run isolated incident drill. A broken in-memory adapter raises a controlled exception; the test records detection, executes the stable estimator on real sample descriptors and checks that the stable stage remains unchanged. Results and timing persist locally in SQLite. This test is bounded, never accepts arbitrary code, and never changes a cloud revision.

## Promotion and rollback

The public/local promotion route always denies mutation. Do not relabel that as an implemented authenticated release service. Future production promotion must require identity/RBAC, explicit quality and security gates, immutable artifact/image identity, real upload smoke tests and owner authorization.

For a failed future revision: isolate traffic, identify the last verified artifact/image/revision, validate inference and face mapping against smoke solids, restore the previously approved revision, verify runtime telemetry and record the incident. No cloud revision rollback has been executed by this project. Local adapter recovery is tested; cloud traffic reversal is pending.

## Proposed SLOs, not measured guarantees

- Healthy API readiness under the selected deployment configuration.
- No raw-CAD retention after processing completion/failure.
- Every successful inference carries model identity and trace ID.
- Proposed 99% success objective for valid supported inputs over 30 days; no production traffic exists to evaluate it.
- Parsing timeout 30 seconds and application upload limit 10 MB are bounds, not latency promises.
- Latency objective and cold-start allowance must be defined after actual container sizing and cloud measurements.

Suggested alerts: sustained failed-valid-request rate, parsing timeouts, queue saturation, worker memory pressure and unavailable readiness. Avoid alerting on every invalid public upload or treating uncalibrated probabilities as ground-truth model quality. Local Prometheus/Grafana configuration is prepared; alert routing and cloud monitoring remain unfinished.
