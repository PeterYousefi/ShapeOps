#!/usr/bin/env bash
set -euo pipefail
# Local, disposable cluster only. Requires Docker, Kind, kubectl and Helm.
kind create cluster --name shapeops --wait 90s
trap 'kind delete cluster --name shapeops' EXIT
shapeops_diagnostics() {
  kubectl get pods -o wide || true
  kubectl describe pods || true
  kubectl logs deployment/shapeops --tail=80 || true
}
trap shapeops_diagnostics ERR
shapeops_upload_smoke() {
  kubectl exec -i deployment/shapeops -- python - <<'PYSMOKE'
import json
import urllib.request

base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/api/samples/flange/download", timeout=20) as response:
    step = response.read()
boundary = "ShapeOpsNativeSmokeBoundary"
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample-flange.step\"\r\n"
        "Content-Type: application/step\r\n\r\n").encode() + step + f"\r\n--{boundary}--\r\n".encode()
request = urllib.request.Request(
    base + "/api/inference/upload?compare=true", data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST",
)
with urllib.request.urlopen(request, timeout=40) as response:
    result = json.load(response)
assert result["source"] == "upload"
assert result["face_count"] == 10
assert [face["id"] for face in result["faces"]] == list(range(result["face_count"]))
assert result["comparison_model"] == "surface-et-v2"
assert all(face["positions"] for face in result["faces"])
print("Sample STEP native worker smoke passed:", result["face_count"], "faces")
PYSMOKE
}
docker build -t shapeops:local .
kind load docker-image shapeops:local --name shapeops
helm lint deploy/helm
helm upgrade --install shapeops deploy/helm --wait --timeout 300s
kubectl rollout status deployment/shapeops --timeout=300s
kubectl run smoke --image=curlimages/curl:8.16.0 --restart=Never --attach --rm -- curl --fail http://shapeops:8000/api/health
kubectl run inference-smoke --image=curlimages/curl:8.16.0 --restart=Never --attach --rm -- curl --fail --silent --output /dev/null -X POST -H "Content-Type: application/json" --data '{"sample":"bracket","compare":true}' http://shapeops:8000/api/inference/sample
shapeops_upload_smoke
kubectl rollout restart deployment/shapeops
kubectl rollout status deployment/shapeops --timeout=300s
shapeops_upload_smoke
