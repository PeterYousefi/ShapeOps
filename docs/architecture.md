# Architecture and decisions

## ADR 001 — modular monolith

React/TypeScript/Vite builds the client; FastAPI serves API routes and the compiled frontend. Three.js owns the rendering loop, per-face materials and raycasting. Native CAD and inference are modules rather than independent cloud services. This supports local development without credentials and avoids paying for unnecessary infrastructure.

`backend/cad.py` owns original solids, validation, numerical features and mesh extraction. `backend/training.py` owns deterministic generation, train/holdout grouping, estimators, OOD reference and artifact packaging. `backend/governance.py` defines explicit release decisions. `backend/app.py` binds API, SQLite telemetry, rate limits, upload lifecycle and isolated drills. `backend/worker.py` is the bounded native parsing entry point.

The uploaded file is renamed to a fixed internal path inside a TemporaryDirectory. A child Python process imports and parses it. A parent timeout kills the subprocess, then directory cleanup removes raw content. At most two parsing/inference requests enter the semaphore simultaneously. The child returns a JSON geometry contract. Model execution uses in-memory estimators trained on startup. Sample geometry is preprocessed on startup and copied before every request.

## ADR 002 — stable face identity

One `shape.Faces()` traversal supplies `id`, numeric feature rows, area/edge properties and triangles. A mesh object carries that face identifier in `userData`. Raycasting sends the identifier to the inspector and face table. Automated tests compare ordered face areas and tessellated points against the source surface. Browser tests select both rows and actual mesh surfaces. Face identity is within one parsed document; stable IDs across independently edited CAD revisions are not claimed.

## ADR 003 — owned procedural baseline

Do not silently substitute synthetic predictions for research inference. Train actual surface classifiers on original analytic solids. Numeric descriptors are model inputs; kernel surface classes are labels. Clearly distinguish this scope from manufacturing-feature segmentation. See model-research.md.

## ADR 004 — evidence-first telemetry

SQLite records only actual executions and drill checks, with seven-day request retention. Dashboard aggregates are computed from the latest 1,000 retained requests. Sample requests are real executions but remain identified as samples. Prometheus exposes retained-window gauges rather than falsely monotonic counters. Browser refreshes telemetry every fifteen seconds. Production availability, ground-truth quality and cloud release events are unavailable and not invented.

## ADR 005 — original enterprise visual system

Graphite/navy surfaces, restrained cyan interaction signals, blue planar geometry and cyan cylindrical geometry. Amber identifies disagreement/attention; red identifies failures. Default dark mode, tested light mode. Compact persistent/collapsible navigation, technical mono identifiers, dominant CAD viewport, contextual inspector and responsive stacked layouts. Camera controls and modal focus are keyboard accessible. Motion respects reduced-motion preference.

## ADR 006 — cloud approval boundary

Terraform is preparation only. Single Consumption app, bounded replica count, private storage and least-privilege identity. Local telemetry is not durable in ephemeral cloud storage; an adapter/export must precede production. No automatic apply, deployment or promotion is wired to a push. A manual deployment-preparation workflow intentionally performs no deployment. Do not infer that an authenticated cloud release system exists.
