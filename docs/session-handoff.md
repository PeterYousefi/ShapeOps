# Session handoff — 2026-10-19

Read AGENTS.md and this file first. Do not restart or replace completed work.

## Current milestone

A real local CAD surface-inference platform with six functional screens is implemented. Current work is product audit/CI preparation across roadmap phases 10–14, with earlier full-lifecycle requirements still partial. This is not a completed production platform and has not been deployed to Azure.

## Architecture

React/TypeScript/Vite + direct Three.js/OrbitControls. FastAPI modular monolith. CadQuery/OpenCascade parses and tessellates genuine STEP in a bounded subprocess. One ordered face ID maps numerical descriptors, predictions and viewer surfaces. Seeded procedural training creates RF/Extra Trees and Isolation Forest OOD screening. Content-addressed local model packages, SQLite request/drill telemetry, real Prometheus gauges. Production mutation is disabled.

## Local running services

Frontend http://127.0.0.1:5173; API http://127.0.0.1:8000. Native CAD initialization needs approved host execution if restricted sandbox initialization stalls. Start both using `./scripts/dev.sh` if sessions have ended. `.venv` and `node_modules` exist. Runtime state is ignored under `.runtime`; tests use an isolated temporary database. Browser checks/benchmark call the live local API, so their real requests appear in local telemetry. Raw uploads are temporary and not retained.

## Verified test state

17 backend tests pass. Four browser tests now cover the light Digital Engineering Lab: complete desktop flow, mobile all-screen/no full-page overflow, zero axe WCAG A/AA violations across all six screens, and light-first/keyboard/release/tablet regression. Screenshots captured/visually inspected. Final upload-identity regression received an additional passing desktop/mobile run. TypeScript production build, Ruff F checks, baseline MyPy, dependency audits, Helm lint/render and Terraform provider-schema validation pass. See artifacts and acceptance-tests.md for limits and exact records. No Azure plan/apply occurred.

Prior 15-test local process: 46.95s wall, maximum resident set ~648 MB, peak memory footprint ~439 MB (macOS time output). This is a test process measurement, not container memory sizing. Ten-request cached-sample benchmark median client latency ~20.9ms, max ~32.5ms; not parsing/cold-start/cloud latency.

## Git/GitHub

Public remote: https://github.com/PeterYousefi/ShapeOps . Authenticated account PeterYousefi; configured author Pouya / yousefipouya@gmail.com was preserved, not changed. Initial five milestones on main; active redesign branch `feat/digital-engineering-lab` (PR #4). Last verified merged implementation is `8fb1f38` (PR #1 merge), with all source checks passing at `f3207c8`. The final evidence-only documentation commit follows this checkpoint. Inspect `git log`, `git status`, `git branch -vv` and actual GitHub runs for the latest state. Never count draft PRs as merged. No achievements are claimed.

PR #1 is merged and attached to this chat: https://github.com/PeterYousefi/ShapeOps/pull/1 . Do not create duplicates. There are two substantive open issues (#2 public-input/worker hardening and #3 persistent governance/cloud adapters), one confirmed merged PR as of this checkpoint, and no claimed achievements.

Hosted CI run 39309545540 passed all four jobs at source f3207c8: application (17 backend tests, three browser/axe workflows, lint/type/audits/build), container build and zero-CRITICAL Trivy scan on Ubuntu 26.04, real Kind deployment/inference/Recreate restart recovery, and Terraform formatting/provider-schema validation. The report is artifacts/container-audit-ubuntu.json, with structured summary artifacts/hosted-ci-summary.json. The previous Debian report is preserved as remediation evidence; its findings are not the current image result. No ignore rules or reduced threshold were used. PR #1 merged on 2026-10-19 at 19:23:20 UTC as 8fb1f38. Main receives only a documentation/evidence follow-up after this source verification.

## Pending engineering

See open-issues.md, roadmap.md and requirements-matrix.md. Highest priorities: stronger native worker resource isolation and distributed abuse controls; long-lived immutable registry/candidate/history; OIDC/RBAC before enabling privileged actions; durable cloud adapters and telemetry export; industrial evaluation/calibration and validated drift. Prepare an approved costed Azure plan only after those prerequisites. The YAML preparation workflow performs no deployment.

## Next executable steps

1. Inspect `gh pr list` and `gh run list`; read failed job logs and correct actual errors.
2. Run `npm run build`, `.venv/bin/python -m pytest -q`, `npm exec playwright test` only after relevant changes; avoid repeating completed checks without a reason.
3. Use `.venv/bin/ruff check backend tests/test_platform.py --select F` and `.venv/bin/mypy backend --ignore-missing-imports --follow-imports=silent` for baseline Python checks.
4. Terraform and Helm binaries were downloaded to `/private/tmp/shapeops-tools`; those paths are ephemeral. Validate only, never apply without approval.
5. Maintain the original design and genuine geometry pipeline; keep all unavailable production metrics/releases explicit.

## Approval boundary

The owner explicitly authorized public repository visibility and hourly engineering/test/push/CI-gated-merge continuation until main exceeds 80 meaningful commits. Azure resources/deployment, domain purchase, recurring cloud charges and production promotion/destructive remote operations still require separate approval. Do not ask to approve a vague future action; complete the concrete reviewable readiness work first.

## Latest direction: Digital Engineering Lab

Active redesign branch: `feat/digital-engineering-lab`, PR #4 (attached to chat). User explicitly rejected the old dark UI. Light-first design in `src/lab.css` and docs/design-system.md supersedes older theme descriptions. The shell, all six pages and Three.js scene have been redesigned; genuine API operations remain intact. Registry selection is local UI state backed by real registry records; no historical production promotion data was invented. Navigation now has explicit accessible names/current-page state. Viewport overlays no longer intercept camera-control clicks.

The full-project target is **well over 80 meaningful commits**, still outstanding. Keep normal cohesive engineering history and continue the production roadmap; do not claim this UI milestone fulfills that target. No Azure deployment is authorized by this request.

Final local redesign validation: 17 backend tests passed (48.12s); TypeScript/Vite build passed; all 4 Chromium tests passed (27.5s), including tablet navigation, compact rail and keyboard release selection. Six-screen axe audit found zero targeted WCAG violations. Final desktop/mobile screenshots were inspected, including portrait camera fit and registry/observability hierarchy. See artifacts/redesign-validation.json. Hosted PR checks must be checked separately at the current head.

## Latest Studio refinement

The existing light design is explicitly approved; do not redesign it again. Studio now has projected-silhouette camera fitting (`src/cameraFit.ts`), occlusion-aware selection/focus, compact chrome, extracted `PredictionDetails.tsx`, real probability breakdowns and stable/candidate/disagreement layers using the completed response. Backend inference adds primary `probabilities` and alternate `comparison_confidence`; legacy `candidate` means alternate even for candidate-primary runs. Main camera scene still depends only on result and stable selection callback, preserving camera on color/selection changes.

Current local validation: 18 backend tests; 10 passing Playwright checks (six browser workflows plus four geometry/frustum cases); zero tested axe violations; production build, Ruff and MyPy pass. The Three.js bundle has a nonblocking size advisory (~500 kB uncompressed). See artifacts/studio-refinement-validation.json and before/after screenshots. PR #4 remains the review target; inspect hosted checks at the latest head rather than assuming local success implies CI success. Rate limit stays at 20 inference requests/minute: repeated full-suite runs require a clear window.

Final screenshot-driven correction: the legacy mobile block-heading rule is overridden for Studio. A targeted all-screen mobile run passes (8.5s), including a bounding-box assertion that title and Export share a row. Fullscreen outer dimensions, reset and exit also passed a separate real Chromium check.

## Public repository and protected main

Owner explicitly authorized public visibility and branch protection, then separately approved hourly background engineering runs that implement/test/push and merge only CI-passing PRs until main exceeds 80 meaningful commits. The former milestone-only notification was replaced with that approved continuation; routine notifications are disabled. It must never deploy to Azure, fabricate history or bypass protection.

GitHub visibility is PUBLIC. Main requires PRs, resolved conversations and up-to-date application/container/kubernetes/terraform checks. Force pushes/deletion are prohibited and admins are included. Independent approvals are not mandatory in this solo-maintainer setup. PR #4 merged as daed6a7 after all four checks passed in run 39317110196. Remote main has 30 reachable commits at that checkpoint; the >80 target is not yet achieved. New governance verification work is on chore/repository-governance; inspect its PR/checks before starting competing work. Run python3 scripts/repository_governance.py for a read-only audit. Thirteen new policy tests pass locally. See docs/repository-governance.md and artifacts/repository-governance.json.

## CAD worker hardening — current background increment

PR #5 passed all four required checks at 64709f3 in run 39318471748 and merged as cff9de9. Main has 32 reachable commits at that checkpoint. Live read-only governance audit still passes and visibility remains public. Current work is on feat/bounded-cad-worker; inspect its PR before starting competing work.

Native CAD parsing now applies CPU/file/core budgets before CAD imports, plus Linux mapped-address-space/data ceilings. Native output is discarded; finite result JSON is atomically written and bounded to 24 MiB, and the parent performs a capped read. Existing face IDs, temporary cleanup, geometry/inference APIs and the light UI are preserved. Local backend validation: 42 passed, 1 Linux-only memory probe skipped on macOS (40.47s). Ruff, MyPy and frontend build pass. Browser checks and hosted Linux verification are recorded in the final evidence for this increment. Full filesystem/network isolation, bounded admission queues and aggregate worker limits remain open; this is not a complete public-service sandbox.

Final local browser validation passed all 10 checks (44.1s) on the final API. Result reads are regular-file-only and nonblocking; symlink/FIFO and cleanup failures are tested. Native worker resource probes and all five STEP round-trips pass on macOS except the explicitly skipped Linux memory probe. Kind smoke now tests real native-worker STEP upload before and after restart. Do not merge until hosted Linux application/container/kubernetes/terraform checks pass on the exact head. No source UI styling changed; regenerated unrelated baseline screenshots were not included in this security increment. Local API pid 79644 serves current code at 8000; Vite remains at 5173.

Hosted verification for the worker implementation at 5b85d2a is complete: run 39333830779 passed all four checks. Linux reported 43 Python tests passed (17.51s, memory probe included) and all 10 Playwright checks. Actual Kind container STEP upload returned 10 flange faces before restart and again after restart. Container security and Terraform checks also passed. Evidence is in artifacts/worker-bounds-validation.json and PR #6. This evidence-only follow-up must itself pass required checks at its current head before merge; never bypass protection.

## Current increment — request admission

Worker PR #6 merged as 9d6aa98 after all required checks passed at 5726082 (run 39334403256); remote main has 35 reachable commits. Public/protected governance audit passes. Current feature branch is feat/bounded-request-admission: zero-wait ASGI admission caps inference/sample/upload/drill requests at four per process, before body consumption. Existing two CAD slots remain. Cancellation-safe run_worker retains slots until the native thread finishes, even after repeated cancellations; overload is 503 with Retry-After: 2. No rate/distributed/slow-client completeness claim is made.

Local checks: 45 backend passes, one Linux-only skip; Ruff/MyPy/build pass. Nine browser checks passed, with the initial accessibility check launched prematurely during API startup; confirmed readiness and retry passed (6.9s). Real uploads, comparison, responsive workflows and current Studio screenshot were checked. No UI styling changed. Current local API pid 81415 uses this implementation; Vite stays on 5173. Inspect the PR/head/CI before further edits; only merge when all four required jobs are green on the exact head, current base and resolved conversations. Do not deploy to Azure.

## Current increment — persistent retention

PR #7 merged as 6d3528f after all required checks passed at 793c0fb (run 39344776718): 46 Linux Python passes, 10 browser passes and actual Kind uploads before/after restart. Remote main reached 37 commits; live governance passed. Current branch feat/bounded-telemetry-retention adds backend/retention.py: request rows capped at 1,000/seven days; drills at 200/thirty days; indexed deterministic cleanup on initialization, writes and reads. No cloud export, secure erasure or SQLite byte-size guarantee is claimed. Full immutable registry governance and other roadmap requirements remain open.

Local validation: 51 backend passes, one Linux-only memory skip (44.31s), Ruff/MyPy/build pass and all 10 browser tests pass (44.8s), including real uploads/comparison and responsive/accessibility workflows. Observability screenshot was inspected; source UI unchanged and generated unrelated baseline artifacts were restored. Local API pid 82700 runs the updated code. Inspect current PR/head/remote before further edits and merge only after all four exact-head required checks pass on a current branch with resolved conversations. No Azure deployment.

## Current increment — typed native geometry

PR #8 merged as 8727515 after all four checks passed at 7843e2d (run 39345696348): 52 Linux Python passes, 10 browser passes, Kind STEP uploads before/after restart. Main reached 39 commits and live governance passed. Current branch feat/validated-cad-contract adds backend/contracts.py TypedDict geometry contracts plus runtime validation in process_step before inference. Exact keys, finite numbers, feature length, known labels, ordered original face IDs, count/bounds and mesh budgets are checked. Zero rounded volume/area remains supported for small solids. Invalid results use the generic failure path with temporary cleanup; no new inference or telemetry is fabricated.

Local checks: 74 backend passes, one Linux-only memory skip (47.09s), Ruff/MyPy/build pass, all 10 browser tests pass (55.6s). Real STEP uploads and mobile face inspection remain functional; mobile Studio screenshot inspected. No UI source changed; unrelated generated artifacts restored. Local API pid 84451 serves this implementation. Inspect open PR/head before further edits; require all four exact-head checks, current base and resolved conversations for normal merge. Full typed API response models, immutable registry lifecycle and remaining security controls are still open. No Azure deployment.

## Current increment — pre-body rate limits

PR #9 merged as 224a196 after all checks passed at 7e257e3 (run 39351857210): 75 Linux backend passes, 10 browser passes, genuine Kind uploads before/after restart. Main reached 41 commits; governance passed. Branch feat/prebody-rate-limits moves route-level throttling into ASGI middleware before admission and body parsing. Twenty protected POST attempts per sixty seconds per ASGI peer are allowed; 4,096-peer state cap with idle expiration fails closed for new peers without evicting active histories. Shared sample/upload/drill quotas include invalid bodies and admission overload; health/read endpoints bypass the gate. No distributed quota, trusted proxy configuration or restart-persistent abuse state is claimed.

Local verification: 77 Python passes, one Linux-only memory skip (51.13s); Ruff/MyPy/build pass; all 10 browser checks pass (48.6s). Real HTTP upload headers without a body received 429/Retry-After/request-ID after quota exhaustion; health stayed 200. Local API pid 86710 has a temporarily exhausted loopback rate window (expires after sixty seconds); do not weaken it for tests. No UI source changed; unrelated generated artifacts restored. Inspect PR/head before edits and merge only after all four checks pass at the exact head, base is current and conversations resolved. No Azure deployment.

## Current increment — immutable model packages

PR #10 merged as beab453 after all checks passed at fc3575f (run 39371435771): 78 Linux backend passes, 10 browser passes, actual Kind uploads before/after restart. Main reached 43 commits; live governance passed. Branch feat/immutable-model-packages adds backend/packages.py and integrates training with atomic immutable packages-v2/<manifest-sha256> publication. Manifest bytes include actual provenance and estimator checksum; API package_id identifies the manifest without a recursive field inside it. Identical packages are verified/reused without rewriting, changes get a new identity, corrupt packages fail closed, and legacy tree-hash directories are untouched. No external estimator loading was enabled; startup still trains owned baselines. Append-only runs, release history, signatures, storage quotas and power-loss durability remain open.

Local checks: 88 backend passes, one Linux-only memory skip (45.33s); Ruff/MyPy/build pass; all 10 browser checks pass (44.9s). Actual internally packaged estimators exactly match live probabilities. Registry screenshot inspected; no UI source changed and unrelated generated artifacts restored. Local API pid 87974 serves current code. Inspect PR/head before edits and require all four exact-head checks, current base and resolved conversations before normal merge. No Azure deployment.

## Current increment — persistent training runs

PR #11 merged as 7914ee9 after all checks passed at 67ddc2e (run 39372238547): 89 Linux backend passes, 10 browser passes, real Kind uploads before/after restart. Main reached 45 commits and governance passed. Branch feat/persistent-training-runs adds backend/registry.py: actual completed run timestamps/UUIDs and package manifest snapshots commit together to registry.sqlite. FK constraints and UPDATE/DELETE triggers enforce ordinary append-only writes; read-only GET /api/registry/runs (limit 1–100) and /api/registry/runs/{id} expose history and verify detail manifest digests. Current registry adds run_id; package manifests exclude execution IDs. Startup still trains owned baselines. No fabricated/backfilled history, authenticated promotions, failed-run journal, archival/storage budget or cloud durability is claimed.

Local verification: 94 backend passes, one Linux-only memory skip (57.08s), Ruff/MyPy/build pass. Browser suite: seven passes and three browser-action/axe timeouts; focused retry of all three passed unchanged (45.4s). No timeout/assertion weakening. Actual API restart preserved prior history/package links and added a second distinct completed run; current registry links the new run. API pid 90128 serves current code. UI source unchanged and unrelated generated artifacts restored. Inspect PR/head before edits; require all four exact-head checks, current base and resolved conversations for normal merge. No Azure deployment.

## Current increment — immutable action pins

PR #12 merged as 1d9f67c after all four checks passed at 8534bed (run 39441616495): 95 Linux backend passes, 10 browser passes and actual Kind STEP uploads before/after restart. Main reached 47 commits; live governance passed. Branch ci/pin-reviewed-actions pins all seven unique GitHub Actions references to full upstream commits resolved from GitHub metadata; original tags remain comments. Checkout persist-credentials is false; contents:read tokens remain. scripts/workflow_policy.py runs early in application CI; tests reject floating/short refs, write permissions, persisted credentials and pull_request_target, and preserve required job names. Weekly Dependabot action PRs do not auto-merge. docs/ci-security.md records source links and explicit remaining source-audit/container/Terraform limits.

Local validation: 101 test passes, one Linux-only memory skip (46.32s), workflow policy, Ruff/backend/scripts/tests, MyPy and frontend build pass. Runtime/UI source unchanged; generated evaluation artifact restored. Hosted all-four checks, including browser/Kind verification under pinned actions, remain required on exact head before normal merge with current base/resolved conversations. No Azure deployment.

## Current increment — action runtime refresh

PR #13 merged as 96b3afc after all checks passed at 30cf79f (run 39442956962): 102 Linux tests, 10 browser checks and real Kind uploads before/after restart. Main reached 49 commits; governance passed. Dependabot opened #14–#17 at the same base; each is independently green. Branch ci/refresh-action-runtimes integrates their four compatible pinned action updates into one combined configuration. Upstream tags match exact SHAs; action.yml/release/compatibility notes confirm Node 24 action runtimes. Application Node 22/Python 3.14 and read-only permissions stay explicit. setup-python removed pip-install input is unused; setup-node registry auth is not configured. docs/ci-security.md links reviewed releases. No full upstream source audit is claimed.

Local checks: 101 test passes, one Linux-only skip (43.37s), workflow policy, Ruff/MyPy and frontend build pass. UI/application source unchanged; generated evaluation restored. Require all four checks at the integrated exact head, current base and resolved conversations before normal merge. Verify evidence artifacts work under upload-artifact v7; only then close superseded #14–#17 if still open. No Azure deployment.

## Current increment — inference API response contracts

PR #18 merged as 2ca2b73 after all checks passed at 6225e1d (run 39452440882): 102 Linux tests, 10 browser checks, Kind uploads before/after restart and downloaded usable evidence artifacts. Superseded dependency #14–#17 closed. Main reached 51 commits; governance passed. Branch feat/typed-inference-responses adds backend/responses.py strict Pydantic output models shared by both inference endpoints and OpenAPI. It validates finite probabilities, confidence/summary consistency, original ordered IDs, mesh/extent budgets and comparison metadata. Features are forbidden in public output. Validation occurs before success telemetry; invalid internal output records internal failure and raises a generic server error without exposing the payload. Existing JSON fields and candidate-as-alternate semantics stay intact.

Local verification: 120 backend passes, one Linux-only memory skip (48.52s); policy/Ruff/MyPy/build pass; all 10 browser checks pass (48.4s). Real STEP and schema/invalid-result telemetry checks passed; uploaded-flange screenshot inspected with approved light UI intact. Local API pid 93859 serves this code. Generated unrelated artifacts restored. docs/api-contracts.md records official FastAPI/Pydantic references and limits; remaining response models and industrial validation remain open. Require all four exact-head checks, current base and resolved conversations before normal merge. No Azure deployment.

## Current increment — Terraform security analysis

PR #19 merged as bf41f68 after all checks passed at 9b4da2d (run 39464246631): 121 Linux tests, 10 browser checks and real Kind uploads before/after restart. Main reached 53 commits; governance passed. Branch ci/terraform-security-gate adds checksum-pinned Trivy installation, embedded-policy Terraform HIGH/CRITICAL gating, insecure positive control and fail-closed scan-report validation inside the required terraform job. Raw reports upload to terraform-security-evidence; tracked artifacts/terraform-security-validation.json records actual local outcomes. Original default-allow storage rule was critical; undeployed IaC now denies unmatched access and disables public storage networking, with authenticated trusted Azure services bypass. Private storage connectivity, lower findings and costed deployment approval remain open.

Local verification: actual pinned-policy baseline 1 high/critical, fixed 0, positive control 5. Terraform fmt/init-backend=false/validate passed (existing provider 4.81.0). 127 test passes, one Linux-only skip (45.95s), policy/Ruff/MyPy/build pass. Empty/missing coverage fails closed; metadata-only Trivy entries are supported by a regression test. Trivy deliberately logs embedded-check fallback for its fresh cache; positive control/report checks independently prove execution. User is trying the local UI: do not restart API pid 93859 or Vite for this CI-only task. No application/UI source changed; generated evaluation restored. Hosted exact-head all-four checks and scanner evidence remain required before normal merge. No Azure login, plan, apply or deployment.

## Current increment — read-only container roots

PR #20 merged as 78c6d39 after all checks passed at adc9537 (run 39473341335): 128 Linux tests, 10 browser checks, native Kind uploads and downloaded scanner proof. Main reached 55 commits; governance passed. Branch security/read-only-container-root hardens Compose/Helm root filesystems and redirects container evaluation output to /app/.runtime/reports through SHAPEOPS_REPORT_DIR. Developer default remains ROOT/artifacts. Helm adds runtime-default seccomp and no service-token mount. Kind probes actual read-only/writable boundaries, UID/no-caps/NoNewPrivs/seccomp/token absence and actual trained reports before/after restart, plus native STEP uploads. Container CI checks Compose configuration.

Local verification: 128 passes, one Linux-only skip (45.08s), actual report-directory integration, Helm lint/render/parsed controls, shell syntax, policy/Ruff/MyPy/build pass. Runtime enforcement awaits hosted Docker/Kind at exact head. Do not claim full child filesystem/network isolation or durable emptyDir state. User is trying local UI; API pid 93859 and Vite remain untouched, no UI source changed. docs/container-security.md covers controls/official references and limits. Require all four exact-head checks, current base and resolved conversations before normal merge. No Azure deployment.

## Current increment — typed telemetry and operations

PR #21 merged as ed2f94a after all checks passed at c042115 (run 39481498917): 129 Linux tests, 10 browser checks, actual runtime hardening probes and native uploads before/after restart. Main reached 57 commits; governance passed. Interrupted heartbeat had no leftover changes/open PRs. Branch feat/typed-operational-responses adds strict TelemetryResponse/RequestRecord, OperationsResponse and DrillResult contracts. Telemetry and Prometheus share validated rows/summaries; empty or failed-only windows retain null success metrics. Drill validation precedes persistence; operations remains explicitly local/undeployed with empty release history and promotion 403. Existing fields remain compatible. Registry/history response contracts are still open.

Initial full suite exposed leftover dictionary access in metrics after model conversion; fixed it and annotated metrics for MyPy plus stronger exact gauge assertions. Final local verification: 143 passes, one Linux-only skip (42.64s), policy/Ruff/MyPy/build pass. Fourteen focused contract cases plus actual OpenAPI/Prometheus/drill/retention integrations exercise the change. Hosted browser/current-head all-four checks remain required before normal merge. Do not restart API pid 93859 or Vite while user tries the UI; source UI unchanged and live services untouched. No Azure deployment.
