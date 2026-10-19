# Azure readiness — deployment not authorized

Terraform describes one Consumption Container Apps environment, one app (2 CPU / 4 GiB, minimum 0 and maximum 1 replica), private artifact storage and a managed identity with Blob Data Reader only. Images must be pinned by GHCR digest. There is no apply command in CI. `prevent_destroy` protects the app from accidental teardown; deletion requires a deliberate reviewed change after explicit owner approval.

This is a preparation template, not a deployment-ready service. The application currently uses local SQLite and local model artifacts. Azure Blob adapters, durable telemetry export, distributed rate limiting, administrator OIDC, cloud revision smoke tests, cold-start measurements and storage lifecycle policies remain release prerequisites. The application must not be promoted as durable cloud production while local ephemeral adapters remain in use.

## Validate without provisioning

```
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

No Azure account is required for syntax/provider-schema validation. Planning requires an approved subscription and credentials. A reviewed plan, security scan and explicit owner approval are required before any apply. Never run an automatic apply.

## Costs and budget

No billable resources were created. A price quote has not been verified. Before approval, obtain current Canada Central Consumption CPU/memory active/idle rates, request allowances, storage transaction/GB costs and monitoring ingestion rates from the Azure calculator. Estimate `active CPU-seconds × CPU rate + active GiB-seconds × memory rate + idle usage + requests + storage + logs`, applying free grants only if the subscription is eligible. A low-traffic portfolio is not equivalent to an always-free service, especially with a native CAD image and long cold starts. Compare scale-to-zero startup latency against visitor experience using actual container measurements.

Set owner-approved subscription/resource-group budgets with 50/80/100% email alerts after obtaining the budget amount and notification recipients. Alerts do not cap spending. Do not create a budget with invented recipients or a fictional approved budget. Configure maximum replicas, log retention and request limits as independent cost controls.

## Domain and HTTPS

`shapeops.dev` is proposed only; registration availability, ownership and price are unverified. Do not purchase. After authorization and verified ownership, configure Container Apps custom-domain DNS and managed TLS directly; Front Door is not required for the proposed single-region portfolio.

## Monitoring and rollback

Before live deployment, configure Azure Monitor diagnostic export with a bounded retention/ingestion budget and connect real telemetry. The prepared environment selects Azure Monitor as log destination but does not create a diagnostic sink. Local Compose provides Prometheus/Grafana separately.

A cloud rollback must select a previously validated immutable revision and verify health, inference, face correspondence and telemetry before traffic changes. The current local drill proves adapter isolation/recovery only; it does not prove cloud rollback. Maintain an approval-gated production environment and serialized deployment workflow. Explicit authorization remains required for promotion and infrastructure teardown.
