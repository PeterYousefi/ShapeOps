import tempfile, os

_TEST_DATA = tempfile.TemporaryDirectory(prefix="shapeops-test-data-")
os.environ["SHAPEOPS_DATA_DIR"] = _TEST_DATA.name
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
    assert "shapeops_inference_requests" in client.get("/metrics").text


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
    import importlib
    import sqlite3
    import time
    module = importlib.import_module("backend.app")
    isolated = tmp_path / "isolated.sqlite"
    with module.connection() as source, sqlite3.connect(isolated) as target:
        source.backup(target)
    monkeypatch.setattr(module, "DB", isolated)
    now = time.time()
    with module.connection() as db:
        db.execute("DELETE FROM requests")
        db.execute("DELETE FROM drills")
        db.execute(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("expired-request", now - 8 * 86400, "sample", "surface-rf-v1", 1, 1, 0, 1, 10, .9, 0, ""),
        )
        db.execute("INSERT INTO drills VALUES (?,?,?)", ("expired", now - 31 * 86400, '{"id":"expired"}'))
        db.execute("INSERT INTO drills VALUES (?,?,?)", ("recent", now, '{"id":"recent"}'))
    assert client.get("/api/telemetry").json()["total"] == 0
    assert client.get("/api/operations").json()["drills"] == [{"id": "recent"}]
    with module.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        assert db.execute("SELECT id FROM drills").fetchall()[0][0] == "recent"


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
        assert json.loads(manifest_bytes) == {key: value for key, value in record.items() if key != "package_id"}
        assert hashlib.sha256((directory / "trees.json").read_bytes()).hexdigest() == record["checksum"]
        assert hashlib.sha256((directory / "estimator.joblib").read_bytes()).hexdigest() == record["package_checksum"]
        # Only our internally trained fixture artifact is deserialized here.
        estimator = joblib.load(directory / "estimator.joblib")
        x = np.array([face["features"] for face in app.state.samples["bracket"]["faces"]])
        assert np.array_equal(estimator.predict_proba(x), app.state.models[record["id"]].predict_proba(x))
