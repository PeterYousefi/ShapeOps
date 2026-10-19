# Open issues

1. Public release hardening: pre-multipart transport caps are implemented. Disposable CAD workers now have CPU/file ceilings, bounded result files, discarded diagnostics and Linux address-space/data ceilings. Bound admission/wait queues, aggregate resources, filesystem/network access and distributed abuse state remain open. Local runtime is not approved for hostile public exposure.
2. Complete immutable persistent registry/run records and candidate creation/promotion history. Current model manifests and in-memory records provide truthful local provenance, not a full lifecycle governance service.
3. Add authenticated administrative OIDC/RBAC only when enabling privileged actions. Current production promotion is disabled with 403.
4. Replace ephemeral local storage with a managed-identity cloud adapter and durable minimal telemetry export before production. Add retention for drill records and true validated drift reports/history.
5. Hosted Docker image build and Kind deployment/inference/recovery now pass. Ubuntu runtime remediation is verified with zero critical image findings; the old Debian report remains historical evidence. Grafana runtime remains unverified. Local workstation lacks Docker/Kind.
6. Expand evaluation beyond original analytic synthetic solids; calibrate probabilities and validate OOD thresholds on legally usable industrial CAD. Do not market this as BRepNet manufacturing-feature inference.
7. Confirm current region-specific Azure price assumptions, budget amount, alert recipients, subscription eligibility and domain ownership/availability. No domain purchase or billable resources authorized.
8. Complete candidate publication, authenticated release, immutable revision smoke validation, rollout and rollback workflows. Manual deployment-preparation workflow does not deploy.
9. Review/pin third-party CI actions by immutable SHA and add Terraform security scanning before infrastructure approval.
10. MyPy currently runs baseline inference analysis, not strict typing of all CAD/inference contracts. Expand typed backend response models and module interfaces.
11. Browser screenshots show real local test/benchmark traffic, not production use. Maintain source labels and avoid importing generated traffic into any production environment.
12. A Starlette deprecation warning notes httpx-based TestClient will migrate to httpx2. Tests currently pass; migrate with upstream compatibility validation rather than suppressing the warning.
