# Acceptance tests

Verified on the local Apple Silicon workstation, Python 3.14.7, Node/Vite toolchain pinned in package-lock.json.

- 17 backend tests pass. Includes five materially distinct samples, actual input-dependent predictions, distinct estimator identities, real STEP upload round-trip, filename sanitization, temporary cleanup, invalid/oversized uploads, live telemetry increments, model provenance, comparison correspondence, bad-quality rejection, forbidden promotion, isolated recovery, OOD shifted input, and real STEP parsing/surface-distance checks for each of the five original solids.
- 3 Chromium tests pass: complete desktop workflow, mobile six-screen workflow/no viewport-wide overflow, and WCAG 2 A/AA + 2.1 AA axe checks across all six screens in dark/light themes. The filename identity regression is included in the desktop workflow after visual review found it.
- TypeScript typecheck + Vite production build pass.
- Ruff F checks pass. MyPy baseline (missing third-party stubs ignored, silent dependency traversal) passes across backend modules. This is not strict annotation coverage.
- Helm lint/render pass. One chart-icon suggestion is informational.
- Terraform formatting and provider-schema validation pass with AzureRM 4.81.0 resolved in the lockfile. No Azure plan/apply was run.
- Runtime npm audit and pip-audit found no known vulnerabilities at scan time. Image/native security remains unverified.
- Bounded cached-sample benchmark: ten real local requests, single client/concurrency 1; measured median client latency ~20.9ms and maximum ~32.5ms. Excludes parsing and cold startup. Raw rows/conditions in artifacts/benchmark.json.
- Timed prior 15-test execution: inspect artifacts/test-resources.json for actual duration and memory; artifacts/backend-tests.txt records the current suite. These are test-process measurements, not service or container sizing guarantees.

Screenshot capture and visual inspection covered all six screens, desktop/mobile, and optional light styling. Corrections included light-theme root background, readable contrast, mobile inspector flow, camera persistence after selection, and keeping previous successful-file identity after a rejected upload.

Not verified locally: Docker build/run, Kind rollout/recovery, Grafana container rendering, container image scans, Terraform security analysis or authenticated Azure planning, production authentication/storage/rollouts/domain/TLS. GitHub hosted status is independent of local passes and must be checked against actual run conclusions.

Hosted source run [39308066260](https://github.com/PeterYousefi/ShapeOps/actions/runs/39308066260) passed application, Terraform and Kubernetes jobs, including real inference and restart recovery. Its container scan properly blocked three critical Debian base-library findings. The original report is tracked; Ubuntu runtime remediation at 993930d must pass a fresh unchanged critical scan and native smoke tests before that gate can clear.
