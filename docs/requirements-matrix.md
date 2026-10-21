# Requirements and evidence matrix

| Requirement | Current evidence | Status / limitation |
| :--- | :--- | :--- |
| Six functional engineering screens | Browser walkthroughs; `src/main.tsx` | Implemented and verified locally across all screens |
| Light-first design & accessibility | Desktop/mobile screenshots; zero axe WCAG 2.1 AA violations | Audited and verified across all 6 screens |
| Responsive accessible CAD workflow | 1440×1050, tablet, and 390×844 mobile browser tests; keyboard controls | Verified with Playwright; no horizontal overflow |
| Genuine STEP uploads | Subprocess OpenCascade parser; five real STEP round-trips | Verified closed solids within CPU/file/memory ceilings |
| Per-face viewer/prediction identity | Ordered face contract, surface-distance tests, Raycasting | Verified correspondence between geometry, predictions, and 3D viewer |
| Multiple meaningful samples | Bracket, flange, housing, shaft, manifold | Original procedural solids; downloadable STEP |
| Real input-dependent inference | Distinct numeric descriptors and trained estimators | Surface classification baseline; not manufacturing segmentation |
| Distinct model versions | RF v1 and Extra Trees v2; separate artifacts, log-loss, probabilities | Verified; distinct parameter sets and performance characteristics |
| Training/evaluation pipeline | Seeded generation, validation, group holdout, report/package | Local pipeline; candidate job task and typed run discovery |
| BRepNet/Fusion investigation | `docs/model-research.md` with upstream sources | Evaluated and documented; legally compatible clean-room alternative implemented |
| Registry metadata and model cards | Content-addressed immutable packages, training runs journal, candidate jobs discovery | Implemented with SQLite append-only journals and package checksums |
| Explicit quality/security gates | Pure gate functions, timing-safe bearer token authentication, immutable triggers | Implemented in `backend/release.py` and verified in test suite |
| Runtime observability | SQLite traces, real counters, percentiles, confidence, OOD, errors | Verified local; latest 1,000 retained requests with 7-day cutoff |
| Prometheus/Grafana | `/metrics` endpoint and dashboard-as-code | Verified; Prometheus/Grafana runtime smoke required in CI container job |
| Drift analysis & OOD screening | Isolation Forest OOD screening, standardized mean shifts, and 2-sample Kolmogorov-Smirnov distance statistics | Implemented in `backend/drift_report.py`; auditable report publication |
| Operations and isolated incident | Actual failure detection and stable inference checks | Verified isolated incident drill; no production mutation |
| Privileged-operation protection | Timing-safe operator token authentication, immutable release journal, read-only audit API and UI | Implemented in backend and integrated into Operations Center UI |
| Upload/privacy/resource controls | Size/header/face/extent/triangle bounds, pre-body admission caps, per-peer rate limits with bounded client state | Strict request limits and cancellation-safe thread slots implemented |
| Durable storage adapters | POSIX Local storage adapter (atomic rename, 0600 mode) and Azure Blob Storage via Managed Identity | Implemented in `backend/storage.py`; telemetry snapshot archival via `--archive` |
| Docker | Multi-stage nonroot image (`uid 10001`), read-only root, seccomp profile | Zero CRITICAL findings in official Aquasec Trivy scan on Ubuntu base |
| Kubernetes | Helm lint/render; Kind disposable cluster deployment, STEP upload smoke, and rollback validation | Actual Kind deployment, inference, and rollback verified in hosted CI |
| Terraform | `fmt`, `init`, `validate`, checksum-pinned security scanner with positive control | Insecure storage finding remediated in IaC; approval boundary maintained |
| CI/CD | GitHub Actions workflow with 4 parallel status checks required on PR heads | All 4 gates (`application`, `container`, `kubernetes`, `terraform`) green across 43 merged PRs |
| Git progress | 103 commits, 43 merged pull requests to `PeterYousefi/ShapeOps` | Natural cohesive commit history; no manufactured volume |
| Domain and cloud cost | `docs/azure-readiness.md` | Cost estimates and architecture documented; no billable actions without approval |
| Documentation and walkthrough | Complete documentation library and `docs/hiring-manager-walkthrough.md` | Detailed platform architecture, 5-minute tour, and requisition alignment |
| Public production deployment | None | Requires explicit approval and remaining release readiness work |
