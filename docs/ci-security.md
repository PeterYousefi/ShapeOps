# CI action provenance and update policy

Workflow actions are pinned to full commit SHAs resolved from the owning repositories through GitHub API commit metadata. These are the existing version lines, not an assertion that every upstream source line has been audited. Floating tags cannot silently replace workflow action code. Checkout uses `persist-credentials: false`; workflow tokens remain `contents: read`, with no write/OIDC scopes.

| Original reference | Pinned upstream commit |
| --- | --- |
| `actions/checkout@v4` | [11d5960a326750d5838078e36cf38b85af677262](https://github.com/actions/checkout/commit/11d5960a326750d5838078e36cf38b85af677262) |
| `actions/setup-node@v4` | [49933ea5288caeca8642d1e84afbd3f7d6820020](https://github.com/actions/setup-node/commit/49933ea5288caeca8642d1e84afbd3f7d6820020) |
| `actions/setup-python@v5` | [a26af69be951a213d495a4c3e4e4022e16d87065](https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065) |
| `actions/upload-artifact@v4` | [ea165f8d65b6e75b540449e92b4886f43607fa02](https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02) |
| `azure/setup-helm@v4.3.0` | [b9e51907a09c216f16ebe8536097933489208112](https://github.com/Azure/setup-helm/commit/b9e51907a09c216f16ebe8536097933489208112) |
| `hashicorp/setup-terraform@v3` | [b9cd54a3c349d3f38e8881555d616ced269862dd](https://github.com/hashicorp/setup-terraform/commit/b9cd54a3c349d3f38e8881555d616ced269862dd) |
| `helm/kind-action@v1.12.0` | [a1b0e391336a6ee6713a0583f8c6240d70863de3](https://github.com/helm/kind-action/commit/a1b0e391336a6ee6713a0583f8c6240d70863de3) |

`python scripts/workflow_policy.py` runs in the application job and its tests check actual workflow files plus rejected unsafe variants. It rejects mutable/short remote references (including reusable workflows), write-token overrides, persisted checkout credentials and `pull_request_target`. It is a focused repository policy, not a full Actions linter or a substitute for reviewing shell commands and permissions. Repository-local actions execute reviewed repository code and are allowed.

Dependabot checks GitHub Actions weekly and can open up to three update PRs. Updates require review and the same exact-head application/container/kubernetes/terraform gates; no auto-merge workflow or privileged update token is configured. Pin updates must retain original-version comments and inspect upstream changes before merge.

Container base images, scanner image digests, runtime package sources and Terraform security scanning remain separate supply-chain work. The manual deployment-preparation workflow still only describes prerequisites and cannot deploy Azure resources.
