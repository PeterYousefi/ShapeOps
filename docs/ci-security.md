# CI action provenance and update policy

Workflow actions are pinned to full commit SHAs resolved from the owning repositories through GitHub API commit metadata. These are the existing version lines, not an assertion that every upstream source line has been audited. Floating tags cannot silently replace workflow action code. Checkout uses `persist-credentials: false`; workflow tokens remain `contents: read`, with no write/OIDC scopes.

| Original reference | Pinned upstream commit |
| --- | --- |
| `actions/checkout@v4` | [11d5960a326750d5838078e36cf38b85af677262](https://github.com/actions/checkout/commit/11d5960a326750d5838078e36cf38b85af677262) |
| `actions/setup-node@v7.1.0` | [949feb2413d6458794dcd2491c4babbbce0c15c1](https://github.com/actions/setup-node/commit/949feb2413d6458794dcd2491c4babbbce0c15c1) |
| `actions/setup-python@v7.0.0` | [5fda3b95a4ea91299a34e894583c3862153e4b97](https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97) |
| `actions/upload-artifact@v7.0.2` | [cf430e030ddbb5b0abf93d22962f4752f3646cd9](https://github.com/actions/upload-artifact/commit/cf430e030ddbb5b0abf93d22962f4752f3646cd9) |
| `azure/setup-helm@v4.3.0` | [b9e51907a09c216f16ebe8536097933489208112](https://github.com/Azure/setup-helm/commit/b9e51907a09c216f16ebe8536097933489208112) |
| `hashicorp/setup-terraform@v4.0.1` | [dfe3c3f87815947d99a8997f908cb6525fc44e9e](https://github.com/hashicorp/setup-terraform/commit/dfe3c3f87815947d99a8997f908cb6525fc44e9e) |
| `helm/kind-action@v1.12.0` | [a1b0e391336a6ee6713a0583f8c6240d70863de3](https://github.com/helm/kind-action/commit/a1b0e391336a6ee6713a0583f8c6240d70863de3) |

`python scripts/workflow_policy.py` runs in the application job and its tests check actual workflow files plus rejected unsafe variants. It rejects mutable/short remote references (including reusable workflows), write-token overrides, persisted checkout credentials and `pull_request_target`. It is a focused repository policy, not a full Actions linter or a substitute for reviewing shell commands and permissions. Repository-local actions execute reviewed repository code and are allowed.

Dependabot checks GitHub Actions weekly and can open up to three update PRs. Updates require review and the same exact-head application/container/kubernetes/terraform gates; no auto-merge workflow or privileged update token is configured. Pin updates must retain original-version comments and inspect upstream changes before merge.

Container base images, scanner image digests, runtime package sources and Terraform security scanning remain separate supply-chain work. The manual deployment-preparation workflow still only describes prerequisites and cannot deploy Azure resources.


## Node 24 action runtime refresh

The setup-node, setup-python, upload-artifact and setup-terraform action pins were refreshed together after reviewing upstream tag identities, action.yml runtime declarations and release/compatibility notes. All four use Node 24 internally; application toolchains remain explicit Node 22 and Python 3.14. GitHub-hosted runners are used; self-hosted runners would need separate compatibility validation. setup-python's removed pip-install input is not used, and setup-node registry authentication inputs are not configured. Artifact upload compatibility is verified through hosted evidence artifacts. No authentication scopes, application dependencies or deployment behavior change.

Upstream releases reviewed:
- [hashicorp/setup-terraform v4.0.1](https://github.com/hashicorp/setup-terraform/releases/tag/v4.0.1)
- [actions/setup-node v7.1.0](https://github.com/actions/setup-node/releases/tag/v7.1.0)
- [actions/upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2)
- [actions/setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0)

This compatibility review does not claim a complete audit of bundled upstream JavaScript. Individual Dependabot checks are preliminary evidence; the combined exact head must pass all four required jobs before merge.
