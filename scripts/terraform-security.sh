#!/usr/bin/env bash
set -euo pipefail
trivy=${1:?Provide the verified pinned Trivy executable}
scan_temporary=$(mktemp -d)
trap 'rm -rf "$scan_temporary"' EXIT
mkdir -p artifacts
rm -f artifacts/terraform-security.json artifacts/terraform-security-positive-control.json
# A fresh cache and skip-update select checks embedded in the verified binary,
# rather than a mutable downloaded policy bundle. Trivy logs this fallback.
scan() {
  "$trivy" config --skip-check-update --cache-dir "$scan_temporary/cache" \
    --misconfig-scanners terraform --severity HIGH,CRITICAL --exit-code 1 \
    --format json --output "$2" "$1"
}
if scan tests/fixtures/insecure-terraform artifacts/terraform-security-positive-control.json; then
  echo 'Scanner failed to reject deliberately insecure Terraform' >&2
  exit 1
fi
python3 scripts/validate_iac_report.py artifacts/terraform-security-positive-control.json --positive-control
scan infra/terraform artifacts/terraform-security.json
python3 scripts/validate_iac_report.py artifacts/terraform-security.json
