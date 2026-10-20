#!/usr/bin/env bash
set -euo pipefail
# SHA-256 values from the owning repository's v0.76.0 release checksums.
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)
    archive_name=trivy_0.76.0_Linux-64bit.tar.gz
    archive_sha=e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7
    checksum_command=(sha256sum -c -)
    ;;
  Darwin-arm64)
    archive_name=trivy_0.76.0_macOS-ARM64.tar.gz
    archive_sha=e7ec0d21fe842553f59af99aba2efbcc822369fbaed27019c575408b6d135fce
    checksum_command=(shasum -a 256 -c -)
    ;;
  *) echo 'Unsupported scanner platform' >&2; exit 1 ;;
esac
destination=${1:?Provide a temporary tool installation directory}
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 --max-time 180 \
  "https://github.com/aquasecurity/trivy/releases/download/v0.76.0/$archive_name" -o "$staging/archive.tar.gz"
printf '%s  %s\n' "$archive_sha" "$staging/archive.tar.gz" | "${checksum_command[@]}"
tar -xzf "$staging/archive.tar.gz" -C "$staging" trivy
mkdir -p "$destination"
install -m 755 "$staging/trivy" "$destination/trivy"
"$destination/trivy" --version
