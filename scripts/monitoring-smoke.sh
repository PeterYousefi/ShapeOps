#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
compose=(docker compose --project-name shapeops-monitoring-ci -f compose.yaml -f monitoring/compose.ci.yaml --profile monitoring)
cleanup() {
  result=$?
  trap - EXIT
  "${compose[@]}" logs --no-color > artifacts/monitoring-stack.log 2>&1 || true
  if [ "$result" -ne 0 ]; then tail -150 artifacts/monitoring-stack.log; fi
  "${compose[@]}" down --volumes --remove-orphans || true
  exit "$result"
}
trap cleanup EXIT
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build
python3 scripts/monitoring_probe.py
