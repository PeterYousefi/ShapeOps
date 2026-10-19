#!/usr/bin/env bash
set -euo pipefail
# Local, disposable cluster only. Requires Docker, Kind, kubectl and Helm.
kind create cluster --name shapeops --wait 90s
trap 'kind delete cluster --name shapeops' EXIT
docker build -t shapeops:local .
kind load docker-image shapeops:local --name shapeops
helm lint deploy/helm
helm upgrade --install shapeops deploy/helm --wait --timeout 300s
kubectl rollout status deployment/shapeops --timeout=300s
kubectl run smoke --image=curlimages/curl:8.16.0 --restart=Never --attach --rm -- curl --fail http://shapeops:8000/api/health
kubectl rollout restart deployment/shapeops
kubectl rollout status deployment/shapeops --timeout=300s
