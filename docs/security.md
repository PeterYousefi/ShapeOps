# Threat model and mitigations

Assets: private CAD contents, model artifacts, runtime integrity, telemetry, release state, user machine and eventual cloud account. Trust boundaries: browser → multipart API; raw bytes → native parser subprocess; numerical descriptors → estimator; runtime → local SQLite; CI → eventual deployment credentials.

| Threat | Implemented mitigation | Remaining boundary |
| --- | --- | --- |
| Filename traversal / HTML injection | Fixed temporary internal filename; React escapes display text; raw filenames excluded from logs | No uploaded-file public serving |
| Invalid/malicious STEP | Extension/header checks, OpenCascade solid validation, face/extent/tessellation limits, subprocess timeout, concurrency bound | Native libraries may contain vulnerabilities; stronger OS sandbox and memory enforcement required |
| Oversized upload | 10 MB file-read limit plus pre-multipart transport cap (bounded 64 KB envelope); content-length and chunked-body tests | Reverse-proxy request/connection limits still recommended before public exposure |
| Resource exhaustion | 20 inference/drill requests per minute per local client address; at most two active processing slots; bounded child runtime | In-memory rate state is not distributed; queue/body caps and worker resource limits remain production work |
| Raw-data leakage | TemporaryDirectory cleanup after success/failure/timeout; no contents or filenames in telemetry | Do not enable request-body logging; enforce infrastructure temporary-storage controls |
| Unauthorized production action | Promotion always denied; no cloud credentials; no deployment endpoints | Authenticated OIDC/RBAC implementation required before enabling administrative mutations |
| Unsafe artifact execution | Only internally trained estimators execute; no user model uploads | Never deserialize externally supplied joblib/pickle artifacts |
| Supply-chain compromise | Lockfiles, SHA-256 artifacts, current dependency audits, prepared CI image scan | Image scan and action pinning/security review not complete |
| UI access issues | Keyboard face table and viewport controls, visible focus, modal trap, reduced motion, audited contrast | Automated axe checks do not replace assistive-technology usability testing |

Telemetry retention: delete request records older than seven days on each inference write; dashboard displays latest 1,000. Drill records are locally stored; add bounded retention before public production. SQLite raw file access is local filesystem access; encryption at rest depends on host storage. The workstation is the developer trust boundary.

Response headers include request IDs, nosniff, same-origin referrer policy and frame denial. TLS is expected from the deployment ingress; no claim of local HTTPS is made. Logs are JSON for inference events but server access/startup logs remain the Uvicorn format. Define a full production log schema before deployment.
