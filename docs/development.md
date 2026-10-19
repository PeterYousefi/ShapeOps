# Development and verification

## Setup

Python 3.14 and Node 22+ are the verified local toolchain families. Install pinned Python dependencies into `.venv` and run `npm ci`. Start API and Vite using `./scripts/dev.sh`. If a restricted desktop sandbox stalls native CAD initialization, execute the native tests/server with the host's approved local execution capability. Do not silently replace CAD with canned geometry.

`npm run build` typechecks TypeScript and builds the client. FastAPI serves `dist` when it exists at startup; restart the API after the first frontend build. Development Vite proxies `/api`, `/metrics`, `/docs`, `/redoc` and `/openapi.json` to port 8000.

## Checks

```
.venv/bin/python -m pytest -q
npm run build
npm exec playwright install chromium
npm exec playwright test
```

Optional quality tools: install `ruff`, `mypy` and `pip-audit` into the developer environment. Run `ruff check backend tests/test_platform.py --select F`, `ruff format --check backend`, and `mypy backend --ignore-missing-imports --follow-imports=silent`. MyPy's current pass is a baseline analysis, not strict annotation coverage of all CAD/native calls.

Runtime audits: `npm audit --omit=dev` and `pip-audit -r requirements.txt`. These are time-specific dependency checks, not a guarantee that native or container vulnerabilities are absent.

Browser tests use a real Chromium desktop viewport at 1440×1050 and mobile at 390×844, including all six screens, actual upload/rejection, raycast/table selection, comparison, model cards, incident drill, light mode and overflow checks. Axe checks WCAG 2 A/AA and 2.1 AA rules in dark and light. Screenshots are in `artifacts`. Reduced-motion mode makes captured interface states deterministic; interactive CSS respects the same user preference.

Tests use a temporary telemetry directory, avoiding pollution of the running developer API. Browser tests and benchmark intentionally call the real developer API; their requests appear as actual local telemetry. Tracked screenshots are evidence of those actual executions.

## Containers and Kubernetes

`docker compose up --build` starts the built single-container app. `docker compose --profile monitoring up --build` adds Prometheus and Grafana, bound to loopback. Grafana anonymous access is Viewer only and suitable for local use; do not expose this Compose configuration publicly. Open http://127.0.0.1:3000 for the provisioned dashboard.

`helm lint deploy/helm` and `helm template shapeops deploy/helm` validate/render manifests. `./scripts/kind-smoke.sh` creates a disposable local Kind cluster, builds/loads the image, verifies rollout and health, restarts the deployment and cleans up the cluster. It requires Docker, Kind, kubectl and Helm; execution has not been verified on this workstation because Docker/Kind are unavailable.

## CI

The prepared quality workflow runs application tests/build/browser checks, a container build/critical-vulnerability scan, disposable Kubernetes smoke tests and Terraform format/provider validation. GitHub execution outcomes must be read from actual runs. No workflow applies Terraform or deploys Azure automatically. Production environment protection must be configured by the owner before eventual release workflows; a YAML environment name alone does not establish an approval policy.
