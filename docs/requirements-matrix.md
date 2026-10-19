# Requirements and evidence matrix

| Requirement | Current evidence | Status / limitation |
| --- | --- | --- |
| Six functional engineering screens | Browser walkthroughs; src/main.tsx | Implemented locally |
| Dark-first and optional light | Desktop screenshots; 12 screen/theme axe checks | Implemented and audited |
| Responsive accessible CAD workflow | 1440×1050 and 390×844 browser checks; keyboard controls | Verified locally; broader assistive-tech testing pending |
| Genuine STEP uploads | Subprocess OpenCascade parser; five real STEP round-trips | Verified closed solids within limits |
| Per-face viewer/prediction identity | Ordered face contract, surface-distance tests, raycasting | Verified within parsed input |
| Multiple meaningful samples | Bracket, flange, housing, shaft, manifold | Original procedural solids; downloadable STEP |
| Real input-dependent inference | Distinct numeric descriptors and trained estimators | Surface classification baseline; not manufacturing segmentation |
| Distinct model versions | RF and Extra Trees; separate artifacts/log-loss/probabilities | Verified; both perfect on limited synthetic holdout |
| Training/evaluation pipeline | Seeded generation, validation, group holdout, report/package | Local pipeline; broad data validation/candidate lifecycle pending |
| BRepNet/Fusion investigation | docs/model-research.md with upstream sources | Investigated, not bundled or runtime-integrated |
| Registry metadata and model cards | Actual in-memory records and packaged manifests | Local; full historical registry/promotion service incomplete |
| Explicit quality/security gates | Pure gate functions and bad-quality rejection test | Production mutation disabled; image scan incomplete |
| Runtime observability | SQLite traces, real counters/percentiles/confidence/OOD/errors | Verified local; latest 1,000 retained requests |
| Prometheus/Grafana | /metrics and dashboard-as-code; Compose | Endpoint verified; Grafana container execution pending |
| OOD screening | Seeded Isolation Forest; reference-vs-shift test | Small procedural reference, no industrial validation/drift report pipeline |
| Operations and isolated incident | Actual failure detection and stable inference checks | Verified; not a cloud rollback |
| Privileged-operation protection | Promotion route returns 403; no cloud credentials | OIDC/RBAC and authorized administration unimplemented |
| Upload/privacy/resource controls | Size/header/face/extent/triangle/time/rate/concurrency bounds | Pre-multipart declared/chunked body cap verified; stronger worker memory isolation still needed |
| Docker | Multi-stage nonroot image and Compose | Prepared; local Docker unavailable; hosted CI must be inspected |
| Kubernetes | Helm lint/render passed; Kind smoke script | Cluster execution pending runtime/CI |
| Terraform | fmt/init/provider-schema validate passed | No Azure plan/apply/security scan performed |
| CI/CD | GitHub quality and manual preparation workflows | Read actual runs; no automatic Azure deployment |
| Git progress | Real cohesive commits pushed to private repository | No invented dates/engagement; numerical targets not artificially met |
| Domain and cloud cost | docs/azure-readiness.md | Ownership/availability/prices/budget unverified; no billable actions |
| Documentation and handoff | README and docs guides/memory files | Local implementation and remaining gaps recorded |
| Public production deployment | None | Requires explicit approval and remaining release readiness work |
