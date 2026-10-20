# Progress — 2026-10-19

Working local ShapeOps application delivered in the shared workspace. Six screens implement the original engineering identity and a real CAD/inference workflow. Browser screenshots are genuine local execution evidence, including sample/benchmark/upload traffic. No production telemetry or release history has been fabricated.

Verified: 17 backend tests; desktop/mobile engineering walkthroughs; 12 screen/theme axe configurations with zero detected WCAG A/AA violations; TypeScript/Vite build; Ruff F checks and baseline MyPy; runtime npm/pip vulnerability audits; Helm lint/render; Terraform provider-schema validation. The complete autonomous production contract is not complete; roadmap/open issues retain the remaining work.

Original baseline RF showed composite-geometry weakness despite synthetic held-out scores; a balanced deterministic version corrects the default sample behavior. The RF and Extra Trees artifacts are distinct, with differing held-out log loss and composite inference behavior. All industrial generalization/calibration limitations stay visible.

GitHub authentication was verified with working host network access after the restricted sandbox gave a misleading failure. Created private `PeterYousefi/ShapeOps`; pushed the initial five cohesive milestones and a feature branch with UI audits, source/environment provenance and CI corrections. No existing repository visibility was changed. The intended Trivy action was initially missing its `v` tag prefix; corrected by pinning the actual published immutable action commit. Hosted runs are being inspected; local pass results do not imply hosted CI success.

No Azure resources, domain registrations or paid cloud services were created. Local workstation lacks Docker/Kind, so actual container/cluster acceptance depends on CI or a future Docker-enabled environment. Azure cost/price and domain availability are not verified. Current security and lifecycle limitations are explicit in README, model cards, Operations and docs/open-issues.md.

Hosted CI evidence: run 39308066260 passed application, Terraform and actual Kind deployment/inference/restart recovery. It blocked the original Debian runtime on three critical library findings. The original report is preserved, and source commit 993930d upgrades the runtime to Ubuntu 26.04 after primary vendor-advisory review. The critical gate remains unchanged; remediation must be verified in the next scan. Draft PR #1 and issues #2–#3 exist; no PR has been merged at this checkpoint.

Final verified source milestone: [run 39309545540](https://github.com/PeterYousefi/ShapeOps/actions/runs/39309545540) passed application, container security, Kubernetes and Terraform. Actual Ubuntu 26.04 image scan found zero critical vulnerabilities at scan time. Real Kind native CAD startup, inference and restart recovery passed. PR #1 merged as 8fb1f38; one merged PR confirmed. The complete production/lifecycle contract remains partial and no achievements are claimed. No Azure resources were created.

## Digital Engineering Lab redesign

The user rejected the original dark dashboard and explicitly selected a light, calm CAD/research-lab direction. The frontend now uses that palette, a compact lab shell, a larger light-grid CAD viewport, linked face inspection, a selectable real-artifact release explorer, candidate/event workspace sections, distinct monitoring zones, operational event timelines and readable documentation. Actual inference/upload/comparison/drift APIs are preserved. No Azure deployment occurred.

The user reiterated **well over 80 meaningful commits** for the full project. This target is outstanding. The redesign is a cohesive UI milestone, not completion of the entire production contract. Do not manufacture history to reach the target.

Final local redesign verification: 17 backend tests; 4 Chromium tests (27.5s); zero axe violations across six light screens; TypeScript/Vite build and formatting checks pass. Real screenshots inspected and corrected at desktop/mobile sizes, with extra tablet checks. PR #4 contains the redesign. Hosted checks are independent and are not assumed to pass from local results.

## Inference Studio refinement

Preserved the light lab identity and refined Studio in place. Actual-vertex perspective silhouette fitting replaces fixed camera offsets. A compact header gives more room to CAD. Selected surfaces have amber fill, visible occluded boundaries and explicit focus/navigation. Actual class breakdowns, per-face primary probabilities and alternate estimator confidence support stable/candidate layer toggling, disagreement highlighting and next-changed-face navigation. Metadata remains available in a disclosure. Previous successful CAD remains visible on processing/error, while empty/screening/upload labels reflect actual state.

Verified: 18 backend tests (52.41s), all 10 Playwright tests (51.6s: six browser workflows and four camera tests), TypeScript/Vite build, Ruff and MyPy. Real sample and uploaded STEP geometry were exercised; before/after desktop/mobile and processing/error/comparison screenshots were inspected. No Azure deployment. Build emits a nonblocking Three.js chunk-size advisory.

## Repository governance

At the owner’s request, GitHub repository visibility changed to public. Main now requires pull requests, resolved conversations and strict application/container/kubernetes/terraform checks; force pushing, deletion and admin bypass are disabled. Read-only verification reports no policy violations. PR #4 merged as daed6a7 after actual hosted checks passed, bringing main to 30 commits. The >80 meaningful commit target remains open. The owner approved hourly background engineering continuation with the same protection/test gates and no Azure deployment; this is active without routine milestone notifications. A read-only governance auditor and 13 fail-closed policy tests provide repeatable verification of the requested settings.

## Bounded disposable CAD workers

PR #5 passed application/container/kubernetes/terraform at 64709f3 and merged as cff9de9, making remote main 32 commits. This increment moves CAD results off unbounded captured stdout into private, finite, atomic result files with a 24 MiB encoder/read ceiling. Worker CPU/file/core ceilings apply before native imports; Linux also receives 2.5 GiB address-space and 1 GiB data ceilings, preserving stricter inherited limits. Full filesystem/network isolation, bounded admission and aggregate resource controls remain open.

Local validation: 42 backend tests passed and one Linux-only memory probe skipped on macOS (40.47s); CPU/file enforcement probes and genuine STEP round-trips passed. Ruff, MyPy and TypeScript/Vite build pass. The first browser suite had nine passes and a desktop total-budget timeout on its final check; a focused desktop retry passed in 51.5s. Its total walkthrough budget is now 120s to cover six screens, native processing and screenshots; per-request/action expectations and the parser's 30s wall ceiling are unchanged. Hosted CI must validate Linux enforcement before merge.

The final browser suite passed all 10 checks in 44.1s on the final API. Parent result reads now explicitly reject symlinks and FIFOs and all protocol-failure tests verify temporary cleanup. Kind smoke coverage now uploads and parses a genuine sample STEP inside the container before and after rollout restart; local Docker/Kind remains unavailable, so Linux/container enforcement awaits hosted verification. See artifacts/worker-bounds-validation.json.

Hosted Linux validation at worker source 5b85d2a passed all four required jobs in run 39333830779. All 43 Python tests passed, including real child memory enforcement; all 10 Playwright checks passed. The actual nonroot Kind container completed genuine sample STEP upload/parsing both before and after rollout restart (10 faces each). This is validated resource hardening, not a claim of full sandboxing or public-production readiness.

## Bounded request admission

PR #6 merged normally as 9d6aa98 after all four required checks passed at 5726082 (run 39334403256). Main had 35 reachable commits; the live governance audit remains clean. This increment admits four inference/drill requests per API process before reading their bodies, rejecting overload with 503/Retry-After without a wait queue. Two CAD slots remain; cancellation now waits for the bounded native worker before releasing reservations, including repeated cancellation. Read endpoints stay available. Distributed rate limits, pre-body per-address throttling and slow-client deadlines remain open.

Local validation: 45 backend tests passed, one Linux-only memory probe skipped (51.27s); Ruff, MyPy and TypeScript/Vite build passed. Browser suite: nine passed and the initial accessibility check failed because it began before API startup completed; readiness was confirmed and the accessibility retry passed (6.9s). Genuine upload/comparison and desktop/mobile workflows passed; generated Studio screenshot was inspected and the approved light workbench remains intact. No UI source changed. Hosted checks must pass on the exact PR head before merge.

## Persistent local telemetry retention

Admission PR #7 merged as 6d3528f after all four required jobs passed at 793c0fb (run 39344776718). Hosted Linux passed 46 Python tests and 10 browser checks; real Kind STEP uploads passed before/after restart. Main has 37 commits at that checkpoint and the public/protected audit passed.

This increment enforces both age and count limits: requests retain up to 1,000 rows/seven days; drills retain up to 200 rows/thirty days. Indexed deterministic cleanup runs on initialization, transactional writes and reads after idle periods. SQLite pages may remain allocated; no secure-erasure or byte-budget claim is made. Isolated tests cover excess counts, payload preservation, exact age cutoff, ties, rollback, reopening and actual idle API reads. Local validation: 51 Python tests passed, one Linux-only probe skipped (44.31s); Ruff/MyPy/build passed; all 10 browser checks passed (44.8s). Observability screenshot inspected with genuine local test traffic; no UI source changed. Hosted exact-head checks remain required before merge.

## Typed CAD worker geometry boundary

Retention PR #8 merged as 8727515 after all four required checks passed at 7843e2d (run 39345696348). Hosted Linux passed 52 Python tests and 10 browser checks; Kind uploads succeeded before/after restart. Remote main had 39 reachable commits and governance passed.

The native result boundary now has typed Geometry/GeometryFace contracts and explicit validation before inference. Exact fields, finite numeric values, six descriptors, supported surface labels, original ordered IDs, counts, bounds and complete mesh triangles are checked against existing budgets; invalid output is rejected with the generic processing error and temporary cleanup. No face IDs are reassigned. Twenty-three protocol tests cover malformed payloads, nonfinite/overflow values, count/order mismatches, mesh limits and parent cleanup. Local verification: 74 backend passes, one Linux-only memory skip (47.09s); Ruff/MyPy/build pass; all 10 browser checks pass (55.6s). Mobile Studio screenshot inspected; UI source unchanged. Hosted exact-head checks remain required before merge.

## Pre-body rate enforcement with bounded peer state

CAD contract PR #9 merged as 224a196 after all four checks passed at 7e257e3 (run 39351857210): 75 Linux Python passes, 10 browser passes and genuine Kind uploads before/after restart. Main had 41 reachable commits and live governance passed.

The existing 20/minute local rate limit now runs before admission/body consumption, shared by inference uploads/samples and drills. Peer state is capped at 4,096 peers and twenty timestamps each; idle peers expire and a full map rejects new peers without evicting active history. All protected attempts count, including malformed bodies and overloads. Rejections include Retry-After, and forwarded headers are not parsed as peer identity by this middleware. This remains per-process, restart-reset state, not distributed abuse control. Local tests: 77 passed, one Linux-only skip (51.13s); Ruff/MyPy/build pass; all 10 browser checks pass (48.6s). A real HTTP probe confirmed 429/Retry-After/request-ID on an upload before its body was sent; health remained 200. No UI source changed. Exact-head hosted checks remain required before merge.

## Immutable atomic model packages

Rate-limit PR #10 merged as beab453 after all four checks passed at fc3575f (run 39371435771): 78 Linux backend passes, 10 browser passes and genuine Kind uploads before/after restart. Main had 43 reachable commits; live governance passed.

Training no longer overwrites manifests/estimator files under a shared tree-hash directory. Complete packages publish atomically under a versioned manifest-content address, including estimator checksum and provenance. Existing identical packages are verified/reused without writes; corrupted/incomplete packages fail closed; changed provenance gets a separate identity. Legacy directories remain untouched. Tests cover concurrent publishers, corruption/missing/extra/symlink rejection, failed-write cleanup and actual packaged estimator probability equivalence. Local verification: 88 backend passes, one Linux-only memory skip (45.33s), Ruff/MyPy/build pass and all 10 browser checks pass (44.9s). Registry screenshot inspected; UI source unchanged. Full append-only run/release lifecycle and durable cloud storage remain open. Exact-head hosted checks required before merge.

## Persistent append-only completed training runs

Package PR #11 merged as 7914ee9 after all checks passed at 67ddc2e (run 39372238547): 89 Linux backend passes, 10 browser passes and genuine Kind uploads before/after restart. Main had 45 reachable commits; live governance passed.

Actual completed baseline training executions now append timestamps, unique run IDs and immutable package manifest snapshots to a separate SQLite journal in one transaction. Foreign keys and UPDATE/DELETE triggers protect ordinary journal writes. Read-only recent-run/detail endpoints expose preserved package links; current model records include their actual run_id. No historical releases or failed attempts are invented. Archival/cloud durability, signatures, failed-run records and authenticated candidate/release workflows remain open.

Local validation: 94 backend passes, one Linux-only memory skip (57.08s); Ruff/MyPy/build pass. Browser run had seven passes and three timeouts during browser actions/axe; all three failed cases passed unchanged on focused retry (45.4s). No thresholds were weakened. Actual API restart increased completed runs from one to two while preserving the prior run/package links and linking current registry to the new run. UI source unchanged. Exact-head hosted checks remain required before merge.

## Immutable CI action references and token policy

Training-journal PR #12 merged as 1d9f67c after all checks passed at 8534bed (run 39441616495): 95 Linux backend passes, all 10 browser passes and genuine Kind uploads before/after restart. Main had 47 reachable commits; live governance passed.

All seven unique workflow action references now pin full commits resolved through owning-repository GitHub metadata, retaining original-version comments. Checkout does not persist credentials. A fail-closed workflow policy and seven regression tests reject mutable/short action refs, write-token overrides, persisted checkout credentials and pull_request_target, while preserving the four required job names. Weekly Dependabot action-update PRs are configured with no auto-merge workflow. See docs/ci-security.md for upstream commit links and limits; full upstream source audits, container digest pins and Terraform security scanning remain open.

Local validation: 101 tests passed, one Linux-only memory skip (46.32s); workflow policy, Ruff across backend/scripts/tests, MyPy and TypeScript/Vite build passed. Application/UI source is unchanged. Browser and container/Kind verification for the newly pinned workflow must pass in hosted CI on the exact head before merge. No Azure deployment.

## Reviewed action runtime refresh

Policy PR #13 merged as 96b3afc after all checks passed at 30cf79f (run 39442956962): 102 Linux test passes, 10 browser passes and genuine Kind uploads before/after restart. Main had 49 reachable commits; governance passed.

Dependabot PRs #14–#17 propose setup-terraform 4.0.1, setup-node 7.1.0, upload-artifact 7.0.2 and setup-python 7.0.0, each independently green at the same base. Their upstream tags/SHAs, action.yml runtime declarations and release/compatibility notes were checked. These Node 24 action upgrades are integrated as one cohesive workflow change to test the combined configuration; application runtimes remain Node 22/Python 3.14 and permissions remain read-only. Removed setup-python pip-install input is unused; no setup-node registry authentication is configured. This compatibility review is not a full bundled-source audit.

Local verification: 101 tests passed, one Linux-only memory skip (43.37s); policy, Ruff/MyPy and frontend build passed. Runtime/UI source unchanged. Combined exact-head all-four hosted checks, including browser/Kind and produced evidence artifacts, remain required before merge. Superseded Dependabot PRs should close only after the integrated change merges. No Azure deployment.

## Typed validated inference responses

Combined action PR #18 merged as 2ca2b73 after all checks passed at 6225e1d (run 39452440882): 102 Linux tests, 10 browser checks and actual Kind uploads before/after restart. Downloaded evidence included 31 valid PNGs, two-model evaluation and a zero-critical container report. Superseded #14–#17 closed after integration. Main had 51 reachable commits; governance passed.

Sample/upload inference now share strict InferenceResult/FacePrediction response models and OpenAPI schemas. Finite numeric values, actual probability consistency, ordered face IDs, geometry/mesh bounds, comparison flags and summaries are validated without inventing data. Internal features are forbidden. Validation precedes successful telemetry; invalid internal results record an actual internal failure and raise a generic server error. Existing JSON field names and legacy alternate-prediction semantics remain intact. See docs/api-contracts.md and official reference links; remaining typed registry/telemetry/operations responses remain open.

Local validation: 120 backend passes, one Linux-only memory skip (48.52s), including schema/invalid-output telemetry and real STEP regressions; policy, Ruff/MyPy/build pass. All 10 browser checks passed (48.4s), including real upload/comparison and responsive/accessibility workflows. Uploaded-flange screenshot inspected; UI source unchanged. Exact-head hosted checks remain required before merge. No Azure deployment.

## Terraform static security gate

Inference contract PR #19 merged as bf41f68 after all checks passed at 9b4da2d (run 39464246631): 121 Linux tests, 10 browser checks and real Kind uploads before/after restart. Main had 53 reachable commits; governance passed.

The required terraform job now installs checksum-pinned Trivy 0.76.0 and runs embedded-policy HIGH/CRITICAL analysis, with an insecure positive control and fail-closed report coverage checks. Installer supports verified macOS ARM64/Linux x86-64 archives; no cloud authentication or plan/apply. Actual original IaC had one critical default-allow storage rule; explicit deny rules and disabled public storage networking remove it. Authenticated trusted Azure services retain the policy-required exception. Private endpoint/access-path design remains a deployment prerequisite. Three lower-severity findings remain documented, without ignore rules.

Local validation: same pinned policies found one baseline high/critical finding, zero in the fix and five in the deliberately insecure control. Terraform fmt/init-backend=false/validate passed with existing provider 4.81.0. 127 tests passed, one Linux-only skip (45.95s); policy/Ruff/MyPy/build pass. Report-format handling was corrected for legitimate metadata-only entries, with a regression test; no empty/skipped scan can pass. Full hosted exact-head checks and evidence upload remain required before merge. Runtime/UI source and running local services are untouched for the user's walkthrough. No Azure deployment.

## Read-only container application roots

Terraform-security PR #20 merged as 78c6d39 after all checks passed at adc9537 (run 39473341335): 128 Linux tests, 10 browser checks and genuine Kind uploads before/after restart. Downloaded scanner reports confirmed positive-control five findings and project zero high/critical findings. Main had 55 reachable commits; governance passed.

Compose and Helm now enforce read-only application roots. Container evaluation reports move via SHAPEOPS_REPORT_DIR into the runtime mount; developer defaults stay unchanged. Helm adds runtime-default seccomp and disables unnecessary service tokens. Kind runtime probes check actual EROFS, writable runtime/tmp, UID, effective capabilities, NoNewPrivs, seccomp, missing token and real report before/after restart, alongside genuine STEP uploads. Compose syntax is validated in container CI. This is not full per-worker filesystem/network isolation or durable pod storage.

Local validation: 128 tests passed, one Linux-only skip (45.08s); actual training report/registry contents match at the explicit test directory. Helm lint/render and parsed security fields, shell syntax, policy/Ruff/MyPy/build pass. Docker/Kind are unavailable locally, so actual runtime enforcement remains pending exact-head hosted checks. No UI changes or local-service restarts; the user's walkthrough remains available. No Azure deployment.

## Typed operational response contracts

Root-filesystem PR #21 merged as ed2f94a after all four checks passed at c042115 (run 39481498917): 129 Linux tests, 10 browser checks, actual read-only/security probes and native uploads before/after restart. Main had 57 reachable commits; governance passed. No unfinished changes or open PRs remained after the interrupted heartbeat.

Telemetry/Prometheus now share a strict retained-window model: actual row totals/flags, finite bounded timings/probabilities, nullable unavailable successful-request metrics and consistent OOD summaries. Operations/drill models encode local/undeployed state and empty release history; drill summaries match executed checks and validate before persistence. Existing wire fields and promotion 403 remain. The retention fixture now uses a complete explicitly labeled unit drill rather than a partial record.

The first full regression caught two old dictionary accesses in Prometheus after the typed-model conversion. They were fixed, metrics received a checked return annotation, and gauge assertions now verify exact actual totals. Final local suite: 143 passed, one Linux-only skip (42.64s); policy/Ruff/MyPy/build pass. Hosted browser/container/Kind/Terraform checks remain required at exact head. Running user-facing services and UI source remain untouched. No Azure deployment.
