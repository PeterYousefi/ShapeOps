# Roadmap — preserve completed work

This is a working local application milestone. The complete autonomous engineering contract is **not fully satisfied**. Do not mark a phase complete when its remaining acceptance criteria are unresolved.

| Phase | Implemented milestone | Remaining acceptance |
| --- | --- | --- |
| 1 Foundation | Local repo, specification, AGENTS, public GitHub remote, protected main and passing CI | Continue substantive issue/review history |
| 2 CAD | Real STEP parsing, topology validation, typed worker result validation, tessellation, five upload round-trips | Broader corpus and pathological inputs; transport body cap now implemented |
| 3 Inference | Trained analytic baselines, face-aware runtime and validated inference API responses | Industrial data/generalization and calibration |
| 4 Frontend | Six screens, upload workflow, interactive viewer, responsive themes | Additional device/assistive-technology checks |
| 5 Comparison | Distinct model versions, probabilities, disagreements and coloring | Broader regression corpus |
| 6 Registry/governance | Atomic immutable local packages, append-only completed training journal, provenance, cards, pure gate evaluation | Archival/cloud durability, failed-attempt history, approvals and release lineage |
| 7 Training/evaluation | Reproducible procedural pipeline, holdout report, regression checks | External dataset contracts, bounded candidate task and publication workflow |
| 8 Monitoring/drift | Actual request metrics and OOD screening, bounded local request/drill retention, local dashboard config | Durable cloud telemetry, validated drift history/reports, alert routing |
| 9 Operations | Isolated injected adapter failure and recovery checks | Authorized release state and tested revision rollback |
| 10 Security/reliability | Upload/runtime limits, bounded worker output, native CPU/file budgets, Linux memory ceilings, pre-body admission/rate caps with bounded local peer state, cancellation-safe worker slots, cleanup, forbidden promotion, dependency audits | Full worker filesystem/network isolation, aggregate budgets, distributed abuse controls, OIDC |
| 11 Containers/Kubernetes | Docker/Compose, Helm lint/render and Kind smoke script | Actual build/Kind inference/recovery/critical scan now pass; broader image sizing and Grafana verification remain |
| 12 CI/CD | Quality workflow, immutable action pins/policy, dependency update PRs and deployment-preparation boundary | All four source CI jobs now green; protected production environment and full publication/release/rollback pipeline remain |
| 13 Terraform/Azure readiness | Validated provider schema, pinned static security gate/positive control and bounded architecture | Lower-severity findings, private storage networking, approved plan/cost/budget and durable adapters |
| 14 Product audit | Backend/browser tests, screenshots, axe, benchmark, fixes | Full acceptance, container scans and full adversarial corpus |
| 15 Azure | No resources provisioned | Explicit approval plus readiness before any deployment or purchase |

Next: preserve the passing CI/container/Kind baseline, harden public input boundaries, complete persistent governance and cloud adapters, then obtain an approved costed deployment plan. Continue with natural cohesive commits and reviewable PRs; never manufacture 80–120 commits or sixteen PRs by trivial splitting.
