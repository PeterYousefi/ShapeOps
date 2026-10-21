import tempfile, os

_TEST_DATA = tempfile.TemporaryDirectory(prefix="shapeops-test-data-")
os.environ["SHAPEOPS_DATA_DIR"] = _TEST_DATA.name
os.environ["SHAPEOPS_REPORT_DIR"] = os.path.join(_TEST_DATA.name, "reports")
from pathlib import Path
import cadquery as cq
import pytest
from fastapi.testclient import TestClient
from backend.app import app, process_step
from backend.cad import SAMPLES, sample_shape, describe, features


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_five_materially_different_solids():
    descriptors = []
    for sample in SAMPLES:
        shape = sample_shape(sample["id"])
        data = describe(shape)
        assert data["face_count"] == len(shape.Faces())
        assert [f["id"] for f in data["faces"]] == list(range(len(shape.Faces())))
        for actual, face in zip(shape.Faces(), data["faces"]):
            assert abs(actual.Area() - face["area"]) < 0.001
            assert face["positions"] and len(face["positions"]) % 9 == 0
            assert face["features"] == features(actual)
        descriptors.append((data["face_count"], data["volume"]))
    assert len(set(descriptors)) == 5


def test_actual_upload_roundtrip_and_temp_cleanup(client):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "part.step"
        cq.exporters.export(sample_shape("flange"), str(f))
        before = set(Path(tempfile.gettempdir()).glob("shapeops-*"))
        response = client.post(
            "/api/inference/upload?compare=true",
            files={"file": ("../../private.step", f.read_bytes(), "application/step")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source"] == "upload"
        assert body["name"] == "Uploaded CAD part"
        assert body["face_count"] == len(sample_shape("flange").Faces())
        assert len(body["checksum"]) == 64
        assert set(Path(tempfile.gettempdir()).glob("shapeops-*")) == before
        assert all(
            f["prediction"] in app.state.registry[0]["classes"] for f in body["faces"]
        )


def test_inference_depends_on_input_and_models_are_distinct(client):
    a = client.post(
        "/api/inference/sample", json={"sample": "bracket", "compare": True}
    ).json()
    b = client.post(
        "/api/inference/sample", json={"sample": "shaft", "model": "surface-et-v2"}
    ).json()
    assert a["face_count"] != b["face_count"]
    assert a["volume"] != b["volume"]
    assert a["checksum"] != b["checksum"]
    assert all(f["candidate"] is not None for f in a["faces"])
    assert sum(f["disagreement"] for f in a["faces"]) == a["disagreements"]
    for face in a["faces"]:
        assert sum(face["probabilities"].values()) == pytest.approx(1)
        assert max(face["probabilities"], key=face["probabilities"].get) == face["prediction"]
        assert face["probabilities"][face["prediction"]] == pytest.approx(face["confidence"])
        assert 0 <= face["comparison_confidence"] <= 1
    assert all(f["comparison_confidence"] is None for f in b["faces"])


def test_invalid_and_oversized_uploads_record_failures(client):
    before = client.get("/api/telemetry").json()["failed"]
    for name, data in [
        ("bad.exe", b"evil"),
        ("bad.step", b"not STEP"),
        ("large.step", b"ISO-10303-21;" + b" " * 10 * 1024 * 1024),
    ]:
        r = client.post("/api/inference/upload", files={"file": (name, data)})
        assert r.status_code == 422
    assert client.get("/api/telemetry").json()["failed"] == before + 3


def test_registry_gates_and_lineage(client):
    records = client.get("/api/registry").json()
    assert len(records) == 2 and records[0]["checksum"] != records[1]["checksum"]
    assert records[0]["dataset_hash"] == records[1]["dataset_hash"]
    assert records[0]["parameters"] != records[1]["parameters"]
    assert all(not r["gates"]["security"] for r in records)
    assert all(r["macro_f1"] >= 0.85 for r in records)
    assert client.post("/api/operations/promote").status_code == 403


def test_telemetry_and_prometheus_are_actual(client):
    before = client.get("/api/telemetry").json()["total"]
    client.post("/api/inference/sample", json={"sample": "housing"})
    after = client.get("/api/telemetry").json()
    assert after["total"] == before + 1
    assert after["p95"] > 0
    metrics_text = client.get("/metrics").text
    assert f'shapeops_inference_requests{{outcome="success"}} {after["successful"]}' in metrics_text
    assert f'shapeops_inference_requests{{outcome="failure"}} {after["failed"]}' in metrics_text


def test_isolated_drill_executes_recovery(client):
    before = client.get("/api/operations").json()["active"]
    result = client.post("/api/operations/drill").json()
    assert result["passed"] and len(result["checks"]) == 3
    assert client.get("/api/operations").json()["active"] == before
    assert any(
        d["id"] == result["id"] for d in client.get("/api/operations").json()["drills"]
    )


def test_reference_and_shifted_ood(client):
    reference = app.state.reference.mean(axis=0).reshape(1, -1)
    shifted = reference * 100
    assert (
        app.state.ood.decision_function(shifted)[0]
        < app.state.ood.decision_function(reference)[0]
    )


def test_unknown_samples_and_models_rejected(client):
    assert (
        client.post("/api/inference/sample", json={"sample": "unknown"}).status_code
        == 404
    )
    assert (
        client.post("/api/inference/sample", json={"model": "unknown"}).status_code
        == 422
    )


def test_bad_quality_candidate_and_missing_authorization_rejected():
    from backend.governance import evaluate_gates, eligible

    failed = evaluate_gates(0.2, True, True, True)
    assert not failed["quality"] and not eligible(failed, authorized=True)
    good = evaluate_gates(0.95, True, True, True)
    assert not eligible(good) and eligible(good, authorized=True)


@pytest.mark.parametrize("sample", [s["id"] for s in SAMPLES])
def test_all_five_samples_parse_as_genuine_step(sample):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "input.step"
        original = sample_shape(sample)
        cq.exporters.export(original, str(path))
        result = process_step(path.read_bytes())
        assert result["face_count"] == len(original.Faces())
        assert abs(result["volume"] - original.Volume()) < 0.1
        for face, actual in zip(result["faces"], original.Faces()):
            vertex = cq.Vertex.makeVertex(*face["positions"][:3])
            assert vertex.distance(actual) < 0.001


def test_transport_limit_rejects_before_multipart_spooling(client):
    before = client.get("/api/telemetry").json()["failed"]
    response = client.post(
        "/api/inference/upload",
        content=b"not parsed",
        headers={
            "Content-Length": str(12 * 1024 * 1024),
            "Content-Type": "multipart/form-data; boundary=test",
        },
    )
    assert response.status_code == 413
    assert "10 MB" in response.json()["detail"]
    assert client.get("/api/telemetry").json()["failed"] == before + 1


def test_chunked_transport_limit():
    import asyncio
    from backend.security import BodyLimitMiddleware, MAX_BODY_BYTES

    rejected = []

    async def inner(scope, receive, send):
        await receive()

    async def receive():
        return {
            "type": "http.request",
            "body": b"x" * (MAX_BODY_BYTES + 1),
            "more_body": False,
        }

    async def send(message):
        pass

    middleware = BodyLimitMiddleware(
        inner, on_reject=lambda scope: rejected.append(True)
    )
    with pytest.raises(Exception) as exc:
        asyncio.run(
            middleware(
                {"type": "http", "path": "/api/inference/upload", "headers": []},
                receive,
                send,
            )
        )
    assert getattr(exc.value, "status_code", None) == 413 and rejected == [True]


def test_comparison_confidence_matches_other_estimator(client):
    stable = client.post("/api/inference/sample", json={"sample": "manifold", "compare": True}).json()
    candidate = client.post("/api/inference/sample", json={"sample": "manifold", "model": "surface-et-v2", "compare": True}).json()
    assert stable["comparison_model"] == candidate["model"]
    for left, right in zip(stable["faces"], candidate["faces"]):
        assert left["id"] == right["id"]
        assert left["candidate"] == right["prediction"]
        assert right["candidate"] == left["prediction"]
        assert left["comparison_confidence"] == pytest.approx(right["confidence"])
        assert right["comparison_confidence"] == pytest.approx(left["confidence"])


def test_idle_api_reads_expire_persistent_records(client, tmp_path, monkeypatch):
    import json
    import importlib
    import sqlite3
    import time
    module = importlib.import_module("backend.app")
    isolated = tmp_path / "isolated.sqlite"
    with module.connection() as source, sqlite3.connect(isolated) as target:
        source.backup(target)
    monkeypatch.setattr(module, "DB", isolated)
    now = time.time()
    recent = {"id": "d" * 12, "at": now, "passed": True, "duration_ms": 1.0,
              "checks": [{"name": "Unit retention fixture", "passed": True}],
              "scope": "Isolated adapter test. No deployment or production mutation."}
    with module.connection() as db:
        db.execute("DELETE FROM requests")
        db.execute("DELETE FROM drills")
        db.execute(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("expired-request", now - 8 * 86400, "sample", "surface-rf-v1", 1, 1, 0, 1, 10, .9, 0, ""),
        )
        db.execute("INSERT INTO drills VALUES (?,?,?)", ("expired", now - 31 * 86400, '{"id":"expired"}'))
        db.execute("INSERT INTO drills VALUES (?,?,?)", (recent["id"], now, json.dumps(recent)))
    assert client.get("/api/telemetry").json()["total"] == 0
    assert client.get("/api/operations").json()["drills"] == [recent]
    with module.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        assert db.execute("SELECT id FROM drills").fetchall()[0][0] == recent["id"]


def test_registry_packages_match_real_runtime_models(client):
    import hashlib
    import json
    import joblib
    import numpy as np
    root = Path(os.environ["SHAPEOPS_DATA_DIR"]) / "models" / "packages-v2"
    for record in client.get("/api/registry").json():
        directory = root / record["package_id"]
        manifest_bytes = (directory / "manifest.json").read_bytes()
        assert hashlib.sha256(manifest_bytes).hexdigest() == record["package_id"]
        assert json.loads(manifest_bytes) == {key: value for key, value in record.items() if key not in {"package_id", "run_id"}}
        assert hashlib.sha256((directory / "trees.json").read_bytes()).hexdigest() == record["checksum"]
        assert hashlib.sha256((directory / "estimator.joblib").read_bytes()).hexdigest() == record["package_checksum"]
        # Only our internally trained fixture artifact is deserialized here.
        estimator = joblib.load(directory / "estimator.joblib")
        x = np.array([face["features"] for face in app.state.samples["bracket"]["faces"]])
        assert np.array_equal(estimator.predict_proba(x), app.state.models[record["id"]].predict_proba(x))


def test_actual_training_history_is_read_only_and_matches_current_registry(client):
    records = client.get("/api/registry").json()
    run_id = records[0]["run_id"]
    history = client.get("/api/registry/runs?limit=1").json()
    assert history["origin"] == "Actual completed local baseline training runs"
    assert history["runs"][0]["id"] == run_id
    detail = client.get(f"/api/registry/runs/{run_id}").json()
    assert detail["started_at"] <= detail["completed_at"]
    assert {m["package_id"] for m in detail["models"]} == {m["package_id"] for m in records}
    assert client.get("/api/registry/runs?limit=101").status_code == 422
    assert client.get("/api/registry/runs/missing").status_code == 404
    assert client.post("/api/registry/runs").status_code == 405


def test_openapi_exposes_shared_inference_schema(client):
    schema = client.get("/openapi.json").json()
    for path in ("/api/inference/sample", "/api/inference/upload"):
        output = schema["paths"][path]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert output == {"$ref": "#/components/schemas/InferenceResult"}
    face = schema["components"]["schemas"]["FacePrediction"]
    assert {"probabilities", "comparison_confidence", "positions", "id"} <= set(face["required"])
    assert "features" not in face["properties"]


def test_invalid_inference_output_is_not_recorded_as_success(client, monkeypatch):
    import numpy as np
    estimator = app.state.models["surface-rf-v1"]
    monkeypatch.setattr(estimator, "predict_proba", lambda x: np.full((len(x), len(estimator.classes_)), np.nan))
    before = client.get("/api/telemetry").json()
    with pytest.raises(RuntimeError, match="Inference response contract failed"):
        client.post("/api/inference/sample", json={"sample": "bracket"})
    after = client.get("/api/telemetry").json()
    assert after["successful"] == before["successful"]
    assert after["failed"] == before["failed"] + 1
    assert after["requests"][0]["error"] == "internal"


def test_evaluation_report_uses_explicit_writable_directory(client):
    import json
    report_path = Path(os.environ["SHAPEOPS_REPORT_DIR"]) / "evaluation.json"
    report = json.loads(report_path.read_text())
    current = client.get("/api/registry").json()
    assert report["models"] == current
    assert all(model["run_id"] for model in report["models"])


def test_operational_openapi_contracts_and_disabled_promotion(client):
    schema = client.get("/openapi.json").json()
    for path, method, name in (
        ("/api/telemetry", "get", "TelemetryResponse"),
        ("/api/operations", "get", "OperationsResponse"),
        ("/api/operations/drill", "post", "DrillResult"),
    ):
        output = schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert output == {"$ref": f"#/components/schemas/{name}"}
    assert schema["components"]["schemas"]["OperationsResponse"]["properties"]["release_history"]["maxItems"] == 0
    assert client.post("/api/operations/promote").status_code == 403


def test_registry_history_openapi_contracts(client):
    schemas = client.get('/openapi.json').json()
    paths = schemas['paths']
    registry_schema = paths['/api/registry']['get']['responses']['200']['content']['application/json']['schema']
    assert registry_schema['items']['$ref'].endswith('/RegisteredModel')
    for path, name in [('/api/registry/runs', 'TrainingHistory'), ('/api/registry/runs/{run_id}', 'TrainingRunDetail')]:
        assert paths[path]['get']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/' + name)


@pytest.mark.parametrize('field,value', [
    ('accuracy', float('nan')), ('macro_f1', 1.1), ('heldout_log_loss', -1.0),
    ('training_rows', 0), ('package_id', 'not-a-digest'), ('git_dirty', 'false'),
    ('classes', ['Planar', 'Planar']), ('features', ['area', 'area']),
    ('stage', 'production'), ('internal_secret', 'must-not-leak'),
])
def test_registry_rejects_invalid_internal_manifests(client, field, value):
    from copy import deepcopy
    from pydantic import ValidationError
    from fastapi.exceptions import ResponseValidationError
    from backend.responses import RegisteredModel
    invalid = deepcopy(app.state.registry[0])
    invalid[field] = value
    with pytest.raises(ValidationError):
        RegisteredModel.model_validate(invalid)
    original = app.state.registry
    try:
        app.state.registry = [invalid]
        with pytest.raises(ResponseValidationError):
            client.get('/api/registry')
    finally:
        app.state.registry = original


def test_history_rejects_inconsistent_run_relationships(client):
    from copy import deepcopy
    from pydantic import ValidationError
    from backend.responses import TrainingHistory, TrainingRunDetail, TrainingRunSummary
    history = client.get('/api/registry/runs?limit=1').json()
    run_id = history['runs'][0]['id']
    detail = client.get(f'/api/registry/runs/{run_id}').json()
    TrainingRunDetail.model_validate(detail)
    TrainingHistory.model_validate(history)
    duplicate = deepcopy(history)
    duplicate['runs'].append(deepcopy(duplicate['runs'][0]))
    with pytest.raises(ValidationError):
        TrainingHistory.model_validate(duplicate)
    for key, value in [('completed_at', detail['started_at'] - 1), ('models', []), ('id', 'invalid')]:
        invalid = {**detail, key: value}
        with pytest.raises(ValidationError):
            TrainingRunDetail.model_validate(invalid)
    for document, model in [(detail, TrainingRunDetail), (history['runs'][0], TrainingRunSummary)]:
        invalid = deepcopy(document)
        invalid['models'].append(deepcopy(invalid['models'][0]))
        with pytest.raises(ValidationError):
            model.model_validate(invalid)


def test_failed_training_history_api_is_bounded_typed_and_read_only(client, tmp_path, monkeypatch):
    import time
    import backend.app as module
    from backend.registry import record_failure
    path = tmp_path / 'failure-history.sqlite'
    monkeypatch.setattr(module, 'REGISTRY_DB', path)
    assert client.get('/api/registry/failures').json()['failures'] == []
    assert not path.exists()
    identity = record_failure(path, time.time(), 'validation')
    response = client.get('/api/registry/failures?limit=1')
    assert response.status_code == 200
    payload = response.json()
    assert payload['origin'] == 'Actual handled local baseline initialization failures'
    assert payload['failures'][0]['id'] == identity
    assert set(payload['failures'][0]) == {'id', 'started_at', 'failed_at', 'category'}
    assert client.get('/api/registry/failures?limit=101').status_code == 422
    assert client.post('/api/registry/failures').status_code == 405
    schema = client.get('/openapi.json').json()['paths']['/api/registry/failures']['get']['responses']['200']['content']['application/json']['schema']
    assert schema['$ref'].endswith('/TrainingFailureHistory')
