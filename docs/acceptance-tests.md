# Acceptance tests

Verified on the local Apple Silicon workstation, Python 3.14.7, Node/Vite toolchain pinned in package-lock.json.

- 43 Python tests pass in hosted Linux CI (42 pass on macOS with the Linux-only memory probe skipped). The suite includes 18 application/CAD tests, 13 governance policy checks and 12 native-worker budget/protocol checks. Includes five materially distinct samples, actual input-dependent predictions, distinct estimator identities, real STEP upload round-trip, filename sanitization, temporary cleanup, invalid/oversized uploads, live telemetry increments, model provenance, comparison correspondence, bad-quality rejection, forbidden promotion, isolated recovery, OOD shifted input, and real STEP parsing/surface-distance checks for each of the five original solids.
- 10 Playwright tests (6 browser workflows and 4 camera geometry tests) cover the complete desktop workflow; mobile six-screen workflow/no viewport-wide overflow; WCAG 2 A/AA + 2.1 AA axe checks across all six light Digital Engineering Lab screens; and persisted light-first behavior, compact rail, keyboard release selection, tablet navigation and responsive layout. The filename identity regression remains in the desktop workflow.
- TypeScript typecheck + Vite production build pass.
- Ruff F checks pass. MyPy baseline (missing third-party stubs ignored, silent dependency traversal) passes across backend modules. This is not strict annotation coverage.
- Helm lint/render pass. One chart-icon suggestion is informational.
- Terraform formatting and provider-schema validation pass with AzureRM 4.81.0 resolved in the lockfile. No Azure plan/apply was run.
- Runtime npm audit and pip-audit found no known vulnerabilities at scan time. Current image/native validation is recorded in the hosted source result below.
- Bounded cached-sample benchmark: ten real local requests, single client/concurrency 1; measured median client latency ~20.9ms and maximum ~32.5ms. Excludes parsing and cold startup. Raw rows/conditions in artifacts/benchmark.json.
- Timed prior 15-test execution: inspect artifacts/test-resources.json for actual duration and memory; artifacts/backend-tests.txt records the current suite. These are test-process measurements, not service or container sizing guarantees.

Screenshot capture and visual inspection covered all six redesigned screens on desktop/mobile. Additional responsive checks covered 1280, 1024, 768, 600 and 390px. Corrections included contrast on mint panels, viewport overlay pointer interception, compact artifact inspector spacing, tablet navigation and portrait camera framing. Camera persistence and successful-file identity after rejected uploads are preserved.

Not verified locally: Docker build/run, Kind rollout/recovery, Grafana container rendering, container image scans, Terraform security analysis or authenticated Azure planning, production authentication/storage/rollouts/domain/TLS. GitHub hosted status is independent of local passes and must be checked against actual run conclusions.

Hosted source run [39308066260](https://github.com/PeterYousefi/ShapeOps/actions/runs/39308066260) passed application, Terraform and Kubernetes jobs, including real inference and restart recovery. Its container scan properly blocked three critical Debian base-library findings. The original report is tracked; Ubuntu runtime remediation at 993930d must pass a fresh unchanged critical scan and native smoke tests before that gate can clear.

Final source validation [39309545540](https://github.com/PeterYousefi/ShapeOps/actions/runs/39309545540) is green across application, container, Kubernetes and Terraform. The rebuilt Ubuntu 26.04 image has zero critical findings in the critical-only Trivy report, and actual native CAD inference/restart recovery passed. PR #1 is merged. Image security is a time-specific result, not proof of general production readiness.

Studio refinement adds actual shaft, housing and manifold inference; an uploaded flange; stable/candidate layer switching (including candidate as primary); per-face confidence and class probabilities; next-disagreement selection; unsupported-file retention; delayed real-response processing and injected network-failure/empty states. Selected-face comparison and unsupported-file states also receive axe checks. Camera tests assert silhouette occupancy, centering and clipping for flat, elongated, tiny and large geometry at three viewport aspects.

Worker hardening validation: [run 39333830779](https://github.com/PeterYousefi/ShapeOps/actions/runs/39333830779) passed application, container, Kubernetes and Terraform at source 5b85d2a. Linux ran all 43 Python tests without skips and all 10 Playwright checks. Kind exercised the native worker via a genuine STEP upload both before and after restart. See artifacts/worker-bounds-validation.json for the time-specific evidence and remaining isolation limits.
