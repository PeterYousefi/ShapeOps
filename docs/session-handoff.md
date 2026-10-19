# Session handoff — 2026-10-19

Read AGENTS.md and this file first. Do not restart or replace completed work.

## Current milestone

A real local CAD surface-inference platform with six functional screens is implemented. Current work is product audit/CI preparation across roadmap phases 10–14, with earlier full-lifecycle requirements still partial. This is not a completed production platform and has not been deployed to Azure.

## Architecture

React/TypeScript/Vite + direct Three.js/OrbitControls. FastAPI modular monolith. CadQuery/OpenCascade parses and tessellates genuine STEP in a bounded subprocess. One ordered face ID maps numerical descriptors, predictions and viewer surfaces. Seeded procedural training creates RF/Extra Trees and Isolation Forest OOD screening. Content-addressed local model packages, SQLite request/drill telemetry, real Prometheus gauges. Production mutation is disabled.

## Local running services

Frontend http://127.0.0.1:5173; API http://127.0.0.1:8000. Native CAD initialization needs approved host execution if restricted sandbox initialization stalls. Start both using `./scripts/dev.sh` if sessions have ended. `.venv` and `node_modules` exist. Runtime state is ignored under `.runtime`; tests use an isolated temporary database. Browser checks/benchmark call the live local API, so their real requests appear in local telemetry. Raw uploads are temporary and not retained.

## Verified test state

17 backend tests pass. Three browser tests cover complete desktop flow, mobile all-screen flow/no full-page overflow, and zero axe WCAG A/AA violations across six screens × two themes. Screenshots captured/visually inspected. Final upload-identity regression received an additional passing desktop/mobile run. TypeScript production build, Ruff F checks, baseline MyPy, dependency audits, Helm lint/render and Terraform provider-schema validation pass. See artifacts and acceptance-tests.md for limits and exact records. No Azure plan/apply occurred.

Prior 15-test local process: 46.95s wall, maximum resident set ~648 MB, peak memory footprint ~439 MB (macOS time output). This is a test process measurement, not container memory sizing. Ten-request cached-sample benchmark median client latency ~20.9ms, max ~32.5ms; not parsing/cold-start/cloud latency.

## Git/GitHub

Private remote: https://github.com/PeterYousefi/ShapeOps . Authenticated account PeterYousefi; configured author Pouya / yousefipouya@gmail.com was preserved, not changed. Initial five milestones on main; active branch `feat/verified-interface`. Last verified pushed source milestone is `993930d` (Ubuntu runtime remediation); previous milestones include `b5528a7` (transport caps) and `ab654c2` (Kind restart recovery). Inspect `git log`, `git status`, `git branch -vv` and actual GitHub runs for the latest state. Never count draft PRs as merged. No achievements are claimed.

Draft PR #1 exists and is attached to this chat: https://github.com/PeterYousefi/ShapeOps/pull/1 . Do not create duplicates. There are two substantive open issues (#2 public-input/worker hardening and #3 persistent governance/cloud adapters), zero merged PRs as of this checkpoint, and no claimed achievements.

Hosted CI run 39308066260 completed: application success (tests/build/browser), Terraform success, Kubernetes success (actual image load/deployment, readiness, genuine inference and Recreate restart recovery), container scan failure. The scan identified three critical Debian 12 base-library CVEs, preserved in artifacts/container-audit-debian.json. Do not ignore or downgrade that gate. Source commit 993930d changes the runtime to Ubuntu 26.04 with Python 3.14 in a venv after vendor-advisory review; its actual fresh scan/native/Kind validation is pending. See docs/ci-results.md and current GitHub runs. Merge only after the current source checks pass.

## Pending engineering

See open-issues.md, roadmap.md and requirements-matrix.md. Highest priorities: finish the Ubuntu image remediation and current hosted validation; stronger native worker resource isolation and distributed abuse controls; long-lived immutable registry/candidate/history; OIDC/RBAC before enabling privileged actions; durable cloud adapters and telemetry export; industrial evaluation/calibration and validated drift. Prepare an approved costed Azure plan only after those prerequisites. The YAML preparation workflow performs no deployment.

## Next executable steps

1. Inspect `gh pr list` and `gh run list`; read failed job logs and correct actual errors.
2. Run `npm run build`, `.venv/bin/python -m pytest -q`, `npm exec playwright test` only after relevant changes; avoid repeating completed checks without a reason.
3. Use `.venv/bin/ruff check backend tests/test_platform.py --select F` and `.venv/bin/mypy backend --ignore-missing-imports --follow-imports=silent` for baseline Python checks.
4. Terraform and Helm binaries were downloaded to `/private/tmp/shapeops-tools`; those paths are ephemeral. Validate only, never apply without approval.
5. Maintain the original design and genuine geometry pipeline; keep all unavailable production metrics/releases explicit.

## Approval boundary

Explicit owner authorization is still required for Azure resources/deployment, domain purchase, recurring charges, production promotion/destructive remote operations and repository visibility changes. No such approval has been given. Do not ask to approve a vague future action; complete the concrete reviewable readiness work first.
