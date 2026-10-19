#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
shapeops_api_pid=$!
trap 'kill "$shapeops_api_pid" 2>/dev/null || true' EXIT INT TERM
npm run dev -- --port 5173
