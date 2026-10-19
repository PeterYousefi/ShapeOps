# Decision log

- 2026-10-19: Empty workspace; create original React/Vite/FastAPI local application rather than a hosted static site. Cloud approval boundary retained.
- 2026-10-19: Investigate BRepNet/Fusion Gallery; no research assets copied. Use a narrower actual trainable analytic-surface baseline on owned solids with explicit limitations.
- 2026-10-19: Use actual OpenCascade face iteration for descriptors and meshes. Keep one face ID contract across API/Three.js/inspector/table.
- 2026-10-19: Initial shallow baseline learned poor composite topology correlations despite good synthetic holdout. Correct RF feature selection/class weighting and retain separate Extra Trees candidate. Record actual log loss/probabilities; do not invent model disagreements.
- 2026-10-19: Replace raw structured-node bytes with canonical field hashing to avoid padding-dependent identities. Package both trees and the trained estimator locally.
- 2026-10-19: Keep telemetry and release data honest. Auto-preview is a real labeled sample inference; production history is empty because no production exists.
- 2026-10-19: Native CAD initialization in the restricted sandbox stalled; approved host execution verified real processing. Recheck GitHub outside the restricted network corrected the initial apparent invalid-auth result.
- 2026-10-19: Create private PeterYousefi/ShapeOps repository because no intended existing repository was found. No existing repository visibility changed.
- 2026-10-19: Validate desktop/mobile screenshots, correct contrast/light/mobile/camera/upload identity issues, and retain browser/axe tests as evidence.
- 2026-10-19: Prepare bounded Docker/Helm/Terraform/CI configuration; do not claim Docker/Kind/cloud validation based on syntax checks or local UI success.
- 2026-10-19: Hosted container image build succeeded, but the pinned older Trivy action failed during binary installation before scanning. Replace it with the official Trivy container at the actual published release 0.76.0; do not interpret installer failure as a vulnerability finding or a clean scan.
- 2026-10-19: Add pre-multipart content-length and chunked-body caps with failed-request telemetry; the expanded 17-test backend suite passes. Native worker resource isolation remains separate future work.
- 2026-10-19: Actual hosted Kind deployment and readiness smoke succeeded; restart rollout then timed out because a surge replacement could not fit alongside the old single-instance workload on the small cluster. Set the disposable single-instance chart to Recreate (brief downtime explicit), add failure diagnostics and genuine inference smoke, and rerun. This is local recovery testing, not zero-downtime cloud revision promotion.
- 2026-10-19: Actual Trivy scan of Debian 12 runtime identified CVE-2025-7458 (sqlite3), CVE-2026-6653 (libxml2) and CVE-2023-45853 (zlib). Keep critical gate blocking. Debian vendor records show SQLite/zlib fixed in newer stable, while libxml2 remains affected there. Ubuntu 26.04 provides Python 3.14 and its vendor advisory marks libxml2 not affected. Move the runtime to Ubuntu 26.04 with distro Python in a venv and rerun build, native inference/recovery and unchanged critical scan. No vulnerability-ignore exceptions added.

Security sources: https://security-tracker.debian.org/tracker/CVE-2025-7458 ; https://security-tracker.debian.org/tracker/CVE-2026-6653 ; https://security-tracker.debian.org/tracker/CVE-2023-45853 ; https://ubuntu.com/security/CVE-2026-6653 ; https://packages.ubuntu.com/resolute/python3.14-full .
