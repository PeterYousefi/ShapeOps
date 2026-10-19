# Hosted CI evidence

[Run 39308066260](https://github.com/PeterYousefi/ShapeOps/actions/runs/39308066260), source ab654c2:

| Job | Actual conclusion |
| --- | --- |
| Application | Passed Python quality/audits/tests, TypeScript build and Chromium workflows |
| Terraform | Passed formatting/init/provider-schema validation; no Azure plan/apply |
| Kubernetes | Passed actual image build/load, Helm deployment, readiness, genuine model inference and single-instance Recreate restart recovery |
| Container security | Blocked on three critical Debian runtime-library findings |

The scanner report is preserved as `artifacts/container-audit-debian.json`. Findings: CVE-2025-7458 (`libsqlite3-0`), CVE-2026-6653 (`libxml2`), CVE-2023-45853 (`zlib1g`). These are image/OS findings; earlier runtime pip/npm audits did not evaluate them. No ignore rules or weakened severity threshold were added.

Primary vendor review: [Debian SQLite advisory](https://security-tracker.debian.org/tracker/CVE-2025-7458), [Debian libxml2 advisory](https://security-tracker.debian.org/tracker/CVE-2026-6653), [Debian zlib advisory](https://security-tracker.debian.org/tracker/CVE-2023-45853). Ubuntu's [libxml2 advisory](https://ubuntu.com/security/CVE-2026-6653) marks 26.04 not affected; [Python package metadata](https://packages.ubuntu.com/resolute/python3.14-full) confirms a supported Python 3.14 runtime. The Docker runtime was changed to Ubuntu 26.04 with distro Python in a venv at source commit 993930d. That change requires a fresh actual build/native smoke/Kind/scan run; selecting a newer base alone is not proof of a clean scan.

The draft PR must remain unmerged while the current source validation is blocked or pending. Refer to the current GitHub checks for the latest result. No production environment has been deployed.

## Final passing source validation

[Run 39309545540](https://github.com/PeterYousefi/ShapeOps/actions/runs/39309545540) passed all four jobs at f3207c8. Ubuntu 26.04 built successfully, the unchanged critical-vulnerability scan reports zero critical findings, and native CAD inference plus single-instance restart recovery passed in Kind. Application quality, all 17 backend tests, three Chromium/axe workflows and Terraform provider validation also passed. The final scan is artifacts/container-audit-ubuntu.json; machine-readable results are artifacts/hosted-ci-summary.json. PR #1 merged as 8fb1f38 after the exact-head checks passed. This source milestone is verified even if later documentation-only pushes create newer in-progress runs.
