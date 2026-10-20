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
shapeops_filesystem_smoke() {
  kubectl exec -i deployment/shapeops -- python - <<'PYFILESYSTEM'
import errno
import json
import os
from pathlib import Path
import tempfile

assert os.getuid() == 10001
assert not Path("/var/run/secrets/kubernetes.io/serviceaccount/token").exists()
status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
assert status["NoNewPrivs"].strip() == "1"
assert status["Seccomp"].strip() == "2"
assert int(status["CapEff"].strip(), 16) == 0
try:
    with tempfile.TemporaryFile(dir="/app/artifacts"):
        pass
except OSError as error:
    assert error.errno == errno.EROFS, error
else:
    raise AssertionError("Application root was writable")
for directory in ("/tmp", "/app/.runtime"):
    with tempfile.TemporaryFile(dir=directory) as stream:
        stream.write(b"actual writable-mount probe")
        stream.flush()
report = json.loads(Path("/app/.runtime/reports/evaluation.json").read_text())
assert len(report["models"]) == 2 and all(model["run_id"] for model in report["models"])
print("Read-only root, writable mounts, nonroot/no-capabilities, seccomp and absent service token verified")
PYFILESYSTEM
}
docker build -t shapeops:local .
kind load docker-image shapeops:local --name shapeops
helm lint deploy/helm
helm upgrade --install shapeops deploy/helm --wait --timeout 300s
kubectl rollout status deployment/shapeops --timeout=300s
kubectl run smoke --image=curlimages/curl:8.16.0 --restart=Never --attach --rm -- curl --fail http://shapeops:8000/api/health
kubectl run inference-smoke --image=curlimages/curl:8.16.0 --restart=Never --attach --rm -- curl --fail --silent --output /dev/null -X POST -H "Content-Type: application/json" --data '{"sample":"bracket","compare":true}' http://shapeops:8000/api/inference/sample
shapeops_filesystem_smoke
shapeops_upload_smoke
kubectl rollout restart deployment/shapeops
kubectl rollout status deployment/shapeops --timeout=300s
shapeops_filesystem_smoke
shapeops_upload_smoke
