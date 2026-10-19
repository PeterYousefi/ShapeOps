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

Private remote: https://github.com/PeterYousefi/ShapeOps . Authenticated account PeterYousefi; configured author Pouya / yousefipouya@gmail.com was preserved, not changed. Initial five milestones on main; active redesign branch `feat/digital-engineering-lab` (PR #4). Last verified merged implementation is `8fb1f38` (PR #1 merge), with all source checks passing at `f3207c8`. The final evidence-only documentation commit follows this checkpoint. Inspect `git log`, `git status`, `git branch -vv` and actual GitHub runs for the latest state. Never count draft PRs as merged. No achievements are claimed.

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

Explicit owner authorization is still required for Azure resources/deployment, domain purchase, recurring charges, production promotion/destructive remote operations and repository visibility changes. No such approval has been given. Do not ask to approve a vague future action; complete the concrete reviewable readiness work first.

## Latest direction: Digital Engineering Lab

Active redesign branch: `feat/digital-engineering-lab`, PR #4 (attached to chat). User explicitly rejected the old dark UI. Light-first design in `src/lab.css` and docs/design-system.md supersedes older theme descriptions. The shell, all six pages and Three.js scene have been redesigned; genuine API operations remain intact. Registry selection is local UI state backed by real registry records; no historical production promotion data was invented. Navigation now has explicit accessible names/current-page state. Viewport overlays no longer intercept camera-control clicks.

The full-project target is **well over 80 meaningful commits**, still outstanding. Keep normal cohesive engineering history and continue the production roadmap; do not claim this UI milestone fulfills that target. No Azure deployment is authorized by this request.

Final local redesign validation: 17 backend tests passed (48.12s); TypeScript/Vite build passed; all 4 Chromium tests passed (27.5s), including tablet navigation, compact rail and keyboard release selection. Six-screen axe audit found zero targeted WCAG violations. Final desktop/mobile screenshots were inspected, including portrait camera fit and registry/observability hierarchy. See artifacts/redesign-validation.json. Hosted PR checks must be checked separately at the current head.

## Latest Studio refinement

The existing light design is explicitly approved; do not redesign it again. Studio now has projected-silhouette camera fitting (`src/cameraFit.ts`), occlusion-aware selection/focus, compact chrome, extracted `PredictionDetails.tsx`, real probability breakdowns and stable/candidate/disagreement layers using the completed response. Backend inference adds primary `probabilities` and alternate `comparison_confidence`; legacy `candidate` means alternate even for candidate-primary runs. Main camera scene still depends only on result and stable selection callback, preserving camera on color/selection changes.

Current local validation: 18 backend tests; 10 passing Playwright checks (six browser workflows plus four geometry/frustum cases); zero tested axe violations; production build, Ruff and MyPy pass. The Three.js bundle has a nonblocking size advisory (~500 kB uncompressed). See artifacts/studio-refinement-validation.json and before/after screenshots. PR #4 remains the review target; inspect hosted checks at the latest head rather than assuming local success implies CI success. Rate limit stays at 20 inference requests/minute: repeated full-suite runs require a clear window.

Final screenshot-driven correction: the legacy mobile block-heading rule is overridden for Studio. A targeted all-screen mobile run passes (8.5s), including a bounding-box assertion that title and Export share a row. Fullscreen outer dimensions, reset and exit also passed a separate real Chromium check.
